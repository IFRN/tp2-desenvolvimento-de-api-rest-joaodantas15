import re
from rest_framework import serializers
from django.utils import timezone
from .models import Eleitor, Eleicao, Candidato, AptidaoEleitor, RegistroVotacao, Voto

class EleitorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Eleitor
        fields = '__all__'

    def validate_cpf(self, value):
        if not re.match(r'^\d{3}\.\d{3}\.\d{3}-\d{2}$', value):
            raise serializers.ValidationError("O CPF deve estar no formato 000.000.000-00")
        return value

class EleicaoSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    total_candidatos = serializers.SerializerMethodField()
    total_aptos = serializers.SerializerMethodField()

    class Meta:
        model = Eleicao
        fields = '__all__'

    def get_total_candidatos(self, obj):
        return obj.candidatos.count()

    def get_total_aptos(self, obj):
        return obj.aptos.count()

class CandidatoSerializer(serializers.ModelSerializer):
    eleicao_titulo = serializers.ReadOnlyField(source='eleicao.titulo')

    class Meta:
        model = Candidato
        fields = '__all__'

    def validate_numero(self, value):
        if value == 0:
            raise serializers.ValidationError("O número zero é reservado para votos em branco.")
        return value

class AptidaoEleitorSerializer(serializers.ModelSerializer):
    eleitor_nome = serializers.ReadOnlyField(source='eleitor.nome')
    eleicao_titulo = serializers.ReadOnlyField(source='eleicao.titulo')

    class Meta:
        model = AptidaoEleitor
        fields = '__all__'

class RegistroVotacaoSerializer(serializers.ModelSerializer):
    eleitor_nome = serializers.ReadOnlyField(source='eleitor.nome')
    eleicao_titulo = serializers.ReadOnlyField(source='eleicao.titulo')

    class Meta:
        model = RegistroVotacao
        fields = '__all__'
        read_only_fields = fields

class VotoSerializer(serializers.ModelSerializer):
    candidato_nome_urna = serializers.ReadOnlyField(source='candidato.nome_urna', allow_null=True)
    em_branco_display = serializers.SerializerMethodField()

    class Meta:
        model = Voto
        fields = ['id', 'eleicao', 'candidato', 'candidato_nome_urna', 'em_branco', 'em_branco_display', 'data_hora']
        read_only_fields = fields

    def get_em_branco_display(self, obj):
        return "BRANCO" if obj.em_branco else None

class VotacaoInputSerializer(serializers.Serializer):
    eleitor_id = serializers.IntegerField()
    eleicao_id = serializers.IntegerField()
    candidato_id = serializers.IntegerField(required=False, allow_null=True)
    em_branco = serializers.BooleanField(default=False)

    def validate(self, data):
        try:
            eleicao = Eleicao.objects.get(pk=data['eleicao_id'])
            eleitor = Eleitor.objects.get(pk=data['eleitor_id'])
        except (Eleicao.DoesNotExist, Eleitor.DoesNotExist):
            raise serializers.ValidationError("Eleição ou Eleitor não encontrado.")

        # (a) Eleição aberta
        if eleicao.status != 'aberta':
            raise serializers.ValidationError("Esta eleição não está aberta para votação.")

        # (b) Data atual entre início e fim
        agora = timezone.now()
        if not (eleicao.data_inicio <= agora <= eleicao.data_fim):
            raise serializers.ValidationError("A eleição não está no período de votação.")

        # (c) Eleitor apto
        if not AptidaoEleitor.objects.filter(eleitor=eleitor, eleicao=eleicao).exists():
            raise serializers.ValidationError("O eleitor não está apto para esta eleição.")

        # (d) Já votou?
        if RegistroVotacao.objects.filter(eleitor=eleitor, eleicao=eleicao).exists():
            raise serializers.ValidationError("Este eleitor já registrou seu voto nesta eleição.")

        # (e) Candidato pertence à eleição?
        candidato_id = data.get('candidato_id')
        if candidato_id:
            if not Candidato.objects.filter(pk=candidato_id, eleicao=eleicao).exists():
                raise serializers.ValidationError("O candidato informado não pertence a esta eleição.")

        # (f) Exatamente um entre candidato ou branco
        em_branco = data.get('em_branco')
        if em_branco and candidato_id:
            raise serializers.ValidationError("Escolha apenas uma opção: Candidato ou Branco.")
        if not em_branco and not candidato_id:
            raise serializers.ValidationError("Você deve escolher um candidato ou votar em branco.")

        return data