from django.contrib import admin
from django.urls import path, include
from rest_framework import routers
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from urna import views

# Configuração do Router (Questão 3.23)
router = routers.DefaultRouter()
router.register(r'eleitores', views.EleitorViewSet)
router.register(r'eleicoes', views.EleicaoViewSet)
router.register(r'candidatos', views.CandidatoViewSet)
router.register(r'aptidoes', views.AptidaoEleitorViewSet)
router.register(r'registros-votacao', views.RegistroVotacaoViewSet)
router.register(r'votos', views.VotoViewSet)

# Configuração do Swagger (Questão 3.24)
schema_view = get_schema_view(
   openapi.Info(
      title="API Gerenciamento de Eleições",
      default_version='v1',
      description="Documentação da API de Urna Eletrônica - IFRN",
   ),
   public=True,
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('eleicoes_api/', include(router.urls)), # Prefixo solicitado no PDF
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]