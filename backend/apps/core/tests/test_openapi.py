from io import StringIO

from django.core.management import call_command


def test_spectacular_valida_sin_advertencias():
    """Un endpoint mal documentado (sin @extend_schema, sin serializer
    inferible, etc.) debe romper esta prueba."""
    call_command("spectacular", "--validate", "--fail-on-warn", stdout=StringIO())
