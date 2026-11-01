from django.conf import settings
from django.core.exceptions import ValidationError


def validar_porcentaje(valor):
    if valor < 0 or valor > 100:
        raise ValidationError("El porcentaje debe estar entre 0 y 100.")


def validar_positivo(valor):
    if valor <= 0:
        raise ValidationError("El valor debe ser mayor que cero.")


def validar_extension_archivo(archivo):
    extension = archivo.name.rsplit(".", 1)[-1].lower() if "." in archivo.name else ""
    permitidas = settings.EXTENSIONES_PERMITIDAS
    if extension not in permitidas:
        raise ValidationError(
            f"Extensión «{extension}» no permitida. Use una de: {', '.join(permitidas)}."
        )


def validar_tamano_archivo(archivo):
    limite_bytes = settings.MAX_UPLOAD_MB * 1024 * 1024
    if archivo.size > limite_bytes:
        raise ValidationError(
            f"El archivo pesa {archivo.size / 1024 / 1024:.1f} MB; el máximo permitido es "
            f"{settings.MAX_UPLOAD_MB} MB."
        )
