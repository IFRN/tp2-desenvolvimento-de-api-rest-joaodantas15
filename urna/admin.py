from django.contrib import admin
from .models import Eleitor, Eleicao, Candidato, AptidaoEleitor, RegistroVotacao, Voto

@admin.register(Eleitor)
class EleitorAdmin(admin.ModelAdmin):
    list_display = ('nome', 'cpf', 'email', 'ativo')

@admin.register(Eleicao)
class EleicaoAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'status', 'data_inicio', 'data_fim')

@admin.register(Candidato)
class CandidatoAdmin(admin.ModelAdmin):
    list_display = ('nome_urna', 'numero', 'eleicao')

admin.site.register(AptidaoEleitor)
admin.site.register(RegistroVotacao)
admin.site.register(Voto)