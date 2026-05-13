from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend
from .models import Eleitor, Eleicao, Candidato, AptidaoEleitor, RegistroVotacao, Voto
from .serializers import (
    EleitorSerializer, EleicaoSerializer, CandidatoSerializer,
    AptidaoEleitorSerializer, RegistroVotacaoSerializer, VotoSerializer
)

class EleitorViewSet(viewsets.ModelViewSet):
    queryset = Eleitor.objects.all()
    serializer_class = EleitorSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['ativo']
    search_fields = ['nome', 'email', 'cpf']

class EleicaoViewSet(viewsets.ModelViewSet):
    queryset = Eleicao.objects.all()
    serializer_class = EleicaoSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'tipo', 'criada_por']
    search_fields = ['titulo']
    ordering_fields = ['data_inicio']

class CandidatoViewSet(viewsets.ModelViewSet):
    # Otimização: select_related carrega a eleição em uma única consulta
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
    """
    Questão 3.22: Apenas leitura. 
    Escrita de votos só será permitida via action customizada na Q04.
    """
    queryset = Voto.objects.all()
    serializer_class = VotoSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['eleicao']