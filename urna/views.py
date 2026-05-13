import hashlib
import secrets
import qrcode
from io import BytesIO
from django.http import HttpResponse
from django.db import transaction, IntegrityError
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action, api_view
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from .models import Eleitor, Eleicao, Candidato, AptidaoEleitor, RegistroVotacao, Voto
from .serializers import (
    EleitorSerializer, EleicaoSerializer, CandidatoSerializer,
    AptidaoEleitorSerializer, RegistroVotacaoSerializer, VotoSerializer,
    VotacaoInputSerializer
)

class EleicaoViewSet(viewsets.ModelViewSet):
    queryset = Eleicao.objects.all()
    serializer_class = EleicaoSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'tipo', 'criada_por']
    search_fields = ['titulo']
    ordering_fields = ['data_inicio']

    @action(detail=True, methods=['post'], url_path='votar')
    def votar(self, request, pk=None):
        eleicao = self.get_object()
        serializer = VotacaoInputSerializer(data={**request.data, 'eleicao_id': eleicao.id})
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        eleitor_id = data['eleitor_id']
        candidato_id = data.get('candidato_id')
        em_branco = data.get('em_branco', False)

        try:
            with transaction.atomic():
                RegistroVotacao.objects.create(eleitor_id=eleitor_id, eleicao=eleicao)
                token = secrets.token_urlsafe(32)
                token_hash = hashlib.sha256(token.encode()).hexdigest()
                candidato = Candidato.objects.get(pk=candidato_id) if candidato_id else None
                voto = Voto.objects.create(
                    eleicao=eleicao,
                    candidato=candidato,
                    em_branco=em_branco,
                    comprovante_hash=token_hash
                )
                qr_url = request.build_absolute_uri(f'/eleicoes_api/comprovantes/qr/?token={token}')
                return Response({
                    "mensagem": "Voto registrado com sucesso. Guarde o seu comprovante.",
                    "comprovante": {
                        "token": token,
                        "eleicao": eleicao.titulo,
                        "candidato": candidato.nome_urna if candidato else "BRANCO",
                        "data_hora": voto.data_hora.isoformat(),
                        "qr_code_url": qr_url
                    }
                }, status=status.HTTP_201_CREATED)
        except IntegrityError:
            return Response({"detail": "Eleitor já votou nesta eleição."}, status=status.HTTP_409_CONFLICT)

    @action(detail=True, methods=['post'])
    def abrir(self, request, pk=None):
        eleicao = self.get_object()
        if eleicao.status != 'rascunho':
            return Response({'error': 'Apenas rascunhos podem ser abertos.'}, status=400)
        if eleicao.candidatos.count() < 2:
            return Response({'error': 'Mínimo de 2 candidatos exigido.'}, status=400)
        if eleicao.aptos.count() < 1:
            return Response({'error': 'Mínimo de 1 eleitor apto exigido.'}, status=400)
        eleicao.status = 'aberta'
        eleicao.save()
        return Response(EleicaoSerializer(eleicao).data)

    @action(detail=True, methods=['post'])
    def encerrar(self, request, pk=None):
        eleicao = self.get_object()
        if eleicao.status != 'aberta':
            return Response({'error': 'Só pode encerrar eleições abertas.'}, status=400)
        eleicao.status = 'encerrada'
        eleicao.save()
        return Response(EleicaoSerializer(eleicao).data)

    @action(detail=True, methods=['get'])
    def apuracao(self, request, pk=None):
        eleicao = self.get_object()
        if eleicao.status not in ['encerrada', 'apurada']:
            return Response({'error': 'Apuração disponível apenas após o encerramento.'}, status=403)
        total_aptos = eleicao.aptos.count()
        total_votantes = eleicao.registros_votacao.count()
        votos_brancos = eleicao.votos.filter(em_branco=True).count()
        votos_validos_total = eleicao.votos.filter(em_branco=False).count()
        resultado = []
        max_votos = -1
        vencedores = []
        for c in eleicao.candidatos.all():
            votos_c = c.votos.count()
            percentual = (votos_c / votos_validos_total * 100) if votos_validos_total > 0 else 0
            resultado.append({
                "candidato": c.nome_urna,
                "numero": c.numero,
                "votos": votos_c,
                "percentual": round(percentual, 2)
            })
            if votos_c > max_votos:
                max_votos = votos_c
                vencedores = [c.nome_urna]
            elif votos_c == max_votos and max_votos > 0:
                vencedores.append(c.nome_urna)
        resultado.sort(key=lambda x: x['votos'], reverse=True)
        for i, item in enumerate(resultado): item['posicao'] = i + 1
        if eleicao.status == 'encerrada':
            eleicao.status = 'apurada'
            eleicao.save()
        return Response({
            "eleicao": eleicao.titulo,
            "total_aptos": total_aptos,
            "total_votantes": total_votantes,
            "total_abstencoes": total_aptos - total_votantes,
            "votos_validos": votos_validos_total,
            "votos_brancos": votos_brancos,
            "resultado": resultado,
            "vencedores": vencedores,
            "houve_empate": len(vencedores) > 1
        })

    @action(detail=True, methods=['get'])
    def votantes(self, request, pk=None):
        eleicao = self.get_object()
        compareceu = request.query_params.get('compareceu', 'true').lower() == 'true'
        if compareceu:
            regs = eleicao.registros_votacao.all()
            data = [{"nome": r.eleitor.nome, "cpf": f"***.{r.eleitor.cpf[4:11]}-**", "data_hora": r.data_hora} for r in regs]
        else:
            aptos_ids = eleicao.aptos.values_list('eleitor_id', flat=True)
            votou_ids = eleicao.registros_votacao.values_list('eleitor_id', flat=True)
            abstencoes = Eleitor.objects.filter(id__in=aptos_ids).exclude(id__in=votou_ids)
            data = [{"nome": e.nome, "cpf": f"***.{e.cpf[4:11]}-**"} for e in abstencoes]
        return Response(data)

    @action(detail=True, methods=['post'], url_path='cadastrar-aptos')
    def cadastrar_aptos(self, request, pk=None):
        eleicao = self.get_object()
        if eleicao.status != 'rascunho': return Response({'error': 'Apenas em rascunho.'}, status=400)
        ids = request.data.get('eleitores_ids', [])
        for eid in ids: AptidaoEleitor.objects.get_or_create(eleicao=eleicao, eleitor_id=eid)
        return Response({"total_cadastrados": len(ids)})

@api_view(['GET'])
def verificar_comprovante(request):
    token = request.query_params.get('token')
    if not token:
        return Response({"valido": False, "mensagem": "Token ausente"}, status=400)
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    voto = Voto.objects.filter(comprovante_hash=token_hash).first()
    if voto:
        return Response({
            "eleicao": voto.eleicao.titulo,
            "candidato": voto.candidato.nome_urna if voto.candidato else "BRANCO",
            "data_hora": voto.data_hora,
            "valido": True
        })
    return Response({"valido": False, "mensagem": "Comprovante inválido"}, status=404)

@api_view(['GET'])
def gerar_qr_code(request):
    token = request.query_params.get('token')
    verificacao_url = request.build_absolute_uri(f'/eleicoes_api/verificar-comprovante/?token={token}')
    img = qrcode.make(verificacao_url)
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    return HttpResponse(buffer.getvalue(), content_type="image/png")

class EleitorViewSet(viewsets.ModelViewSet):
    queryset = Eleitor.objects.all()
    serializer_class = EleitorSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['ativo']
    search_fields = ['nome', 'email', 'cpf']

class CandidatoViewSet(viewsets.ModelViewSet):
    queryset = Candidato.objects.select_related('eleicao').all()
    serializer_class = CandidatoSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['eleicao']
    search_fields = ['nome', 'nome_urna', 'partido_ou_chapa']

class AptidaoEleitorViewSet(viewsets.ModelViewSet):
    queryset = AptidaoEleitor.objects.select_related('eleitor', 'eleicao').all()
    serializer_class = AptidaoEleitorSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['eleitor', 'eleicao']

class RegistroVotacaoViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = RegistroVotacao.objects.select_related('eleitor', 'eleicao').all()
    serializer_class = RegistroVotacaoSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['eleicao']
    ordering = ['-data_hora']

class VotoViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Voto.objects.all()
    serializer_class = VotoSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['eleicao']