import django_filters

from .models import DocumentoExpediente, EntradaBitacora


class FiltroDocumentoExpediente(django_filters.FilterSet):
    class Meta:
        model = DocumentoExpediente
        fields = ["proyecto", "categoria", "seguimiento", "tarea"]


class FiltroBitacora(django_filters.FilterSet):
    desde = django_filters.DateFilter(field_name="ocurrido_en", lookup_expr="date__gte")
    hasta = django_filters.DateFilter(field_name="ocurrido_en", lookup_expr="date__lte")

    class Meta:
        model = EntradaBitacora
        fields = ["proyecto", "tipo_evento", "entidad", "entidad_id", "usuario"]
