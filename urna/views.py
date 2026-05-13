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
        
        # 1. Validar a entrada com o VotacaoInputSerializer
        serializer = VotacaoInputSerializer(data={**request.data, 'eleicao_id': eleicao.id})
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        eleitor_id = data['eleitor_id']
        candidato_id = data.get('candidato_id')
        em_branco = data.get('em_branco', False)

        try:
            # 2. Transação Atómica para garantir o sigilo e integridade
            with transaction.atomic():
                # Registro de Presença (O "Caderno")
                RegistroVotacao.objects.create(eleitor_id=eleitor_id, eleicao=eleicao)

                # Gerar Token aleatório e seu Hash
                token = secrets.token_urlsafe(32)
                token_hash = hashlib.sha256(token.encode()).hexdigest()

                # Criar o Voto (ANÔNIMO)
                candidato = Candidato.objects.get(pk=candidato_id) if candidato_id else None
                voto = Voto.objects.create(
                    eleicao=eleicao,
                    candidato=candidato,
                    em_branco=em_branco,
                    comprovante_hash=token_hash
                )

                # URL do QR Code
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

# --- Funções Auxiliares (Públicas) ---

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

# --- Outras ViewSets ---

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