from apps.core.permissions import EsPmoOAdminOSoloLectura
from apps.core.views import ViewSetBase

from .filters import FiltroArea, FiltroPerfilRecurso, FiltroPortafolio
from .models import Area, PerfilRecurso, Portafolio
from .serializers import AreaSerializer, PerfilRecursoSerializer, PortafolioSerializer
from .services import validar_desactivacion


class AreaViewSet(ViewSetBase):
    queryset = Area.objects.select_related("responsable")
    serializer_lectura_class = AreaSerializer
    serializer_escritura_class = AreaSerializer
    permission_classes = [EsPmoOAdminOSoloLectura]
    filterset_class = FiltroArea
    search_fields = ["codigo", "nombre"]
    ordering_fields = ["codigo", "nombre"]

    def perform_destroy(self, instance):
        validar_desactivacion(instance)
        super().perform_destroy(instance)


class PortafolioViewSet(ViewSetBase):
    queryset = Portafolio.objects.select_related("responsable")
    serializer_lectura_class = PortafolioSerializer
    serializer_escritura_class = PortafolioSerializer
    permission_classes = [EsPmoOAdminOSoloLectura]
    filterset_class = FiltroPortafolio
    search_fields = ["codigo", "nombre"]
    ordering_fields = ["codigo", "nombre"]

    def perform_destroy(self, instance):
        validar_desactivacion(instance)
        super().perform_destroy(instance)


class PerfilRecursoViewSet(ViewSetBase):
    queryset = PerfilRecurso.objects.all()
    serializer_lectura_class = PerfilRecursoSerializer
    serializer_escritura_class = PerfilRecursoSerializer
    permission_classes = [EsPmoOAdminOSoloLectura]
    filterset_class = FiltroPerfilRecurso
    search_fields = ["codigo", "nombre"]
    ordering_fields = ["codigo", "nombre"]

    def perform_destroy(self, instance):
        validar_desactivacion(instance)
        super().perform_destroy(instance)
