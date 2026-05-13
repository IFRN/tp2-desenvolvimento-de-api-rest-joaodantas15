from django.contrib import admin
from django.urls import path, include
from rest_framework import routers, permissions
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
   permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    path('admin/', admin.site.urls),
    # Rotas da Questão 04
    path('eleicoes_api/verificar-comprovante/', views.verificar_comprovante),
    path('eleicoes_api/comprovantes/qr/', views.gerar_qr_code),
    # Rotas automáticas do router
    path('eleicoes_api/', include(router.urls)),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
]