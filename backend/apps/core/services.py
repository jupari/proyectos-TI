def registrar_evento(
    *,
    tipo_evento,
    entidad,
    entidad_id,
    descripcion,
    proyecto=None,
    antes=None,
    despues=None,
    usuario=None,
):
    """Escribe una entrada de bitácora.

    La usan `apps.core.signals` para los eventos genéricos de creación y
    actualización, y los servicios de negocio de las fases siguientes
    (aprobar, publicar, cambiar estado) para eventos con significado propio
    (`APROBACION`, `PUBLICACION`, `CAMBIO_ESTADO`, ...).
    """
    from apps.expediente.models import EntradaBitacora

    return EntradaBitacora.objects.create(
        proyecto=proyecto,
        tipo_evento=tipo_evento,
        entidad=entidad,
        entidad_id=entidad_id,
        descripcion=descripcion,
        datos_antes=antes,
        datos_despues=despues,
        usuario=usuario,
    )
