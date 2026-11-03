"""Invalida la caché del tablero (`apps/tablero/cache.py`) cuando cambia
algo que sus agregaciones resumen: un registro de ejecución o un gasto
(crear, enviar, aprobar, rechazar o reabrir pasan todos por `.save()`) o un
seguimiento (precargar/publicar/reabrir), docs/plan/fase-10-tablero-
control.md §10.1.3.

Se conecta explícitamente desde `TableroConfig.ready()`, no con
`@receiver`, siguiendo la misma convención que `apps.core.signals`
(auditoría): la conexión queda bajo control del `AppConfig`."""

from django.db.models.signals import post_save

from apps.tablero.cache import invalidar


def _invalidar_cache_tablero(sender, instance, **kwargs):
    invalidar()


def conectar():
    from apps.ejecucion.models import GastoEjecutado, RegistroEjecucion
    from apps.seguimiento.models import Seguimiento

    post_save.connect(
        _invalidar_cache_tablero, sender=RegistroEjecucion, dispatch_uid="tablero_cache_registro"
    )
    post_save.connect(
        _invalidar_cache_tablero, sender=GastoEjecutado, dispatch_uid="tablero_cache_gasto"
    )
    post_save.connect(
        _invalidar_cache_tablero, sender=Seguimiento, dispatch_uid="tablero_cache_seguimiento"
    )
