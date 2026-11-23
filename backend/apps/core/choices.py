from django.db import models


class EstadoProyecto(models.TextChoices):
    BORRADOR = "BORRADOR", "Borrador"
    PLANEACION = "PLANEACION", "Planeación"
    EJECUCION = "EJECUCION", "Ejecución"
    SUSPENDIDO = "SUSPENDIDO", "Suspendido"
    CERRADO = "CERRADO", "Cerrado"
    CANCELADO = "CANCELADO", "Cancelado"
    PRODUCCION_SOPORTE = "PRODUCCION_SOPORTE", "Producción y soporte"


class Prioridad(models.TextChoices):
    BAJA = "BAJA", "Baja"
    MEDIA = "MEDIA", "Media"
    ALTA = "ALTA", "Alta"
    CRITICA = "CRITICA", "Crítica"


class EstadoTarea(models.TextChoices):
    PENDIENTE = "PENDIENTE", "Pendiente"
    EN_PROGRESO = "EN_PROGRESO", "En progreso"
    BLOQUEADA = "BLOQUEADA", "Bloqueada"
    EN_REVISION = "EN_REVISION", "En revisión"
    COMPLETADA = "COMPLETADA", "Completada"
    CANCELADA = "CANCELADA", "Cancelada"


class TipoTarea(models.TextChoices):
    ACTIVIDAD = "ACTIVIDAD", "Actividad"
    TAREA = "TAREA", "Tarea"
    INCIDENCIA = "INCIDENCIA", "Incidencia"
    CAMBIO = "CAMBIO", "Cambio"
    REUNION = "REUNION", "Reunión"
    HISTORIA = "HISTORIA", "Historia de usuario"


class EstadoSprint(models.TextChoices):
    """Mismos tres estados que Jira (`future`, `active`, `closed`)."""

    FUTURO = "FUTURO", "Futuro"
    ACTIVO = "ACTIVO", "Activo"
    CERRADO = "CERRADO", "Cerrado"


class Periodicidad(models.TextChoices):
    DIARIA = "DIARIA", "Diaria"
    SEMANAL = "SEMANAL", "Semanal"
    MENSUAL = "MENSUAL", "Mensual"


class EstadoAprobacion(models.TextChoices):
    BORRADOR = "BORRADOR", "Borrador"
    ENVIADO = "ENVIADO", "Enviado"
    APROBADO = "APROBADO", "Aprobado"
    RECHAZADO = "RECHAZADO", "Rechazado"


class OrigenRegistro(models.TextChoices):
    MANUAL = "MANUAL", "Manual"
    JIRA = "JIRA", "Jira/Tempo"


class Semaforo(models.TextChoices):
    VERDE = "VERDE", "Verde"
    AMARILLO = "AMARILLO", "Amarillo"
    ROJO = "ROJO", "Rojo"


class CategoriaRubro(models.TextChoices):
    PERSONAL = "PERSONAL", "Personal"
    LICENCIAS = "LICENCIAS", "Licencias"
    INFRAESTRUCTURA = "INFRAESTRUCTURA", "Infraestructura"
    SERVICIOS = "SERVICIOS", "Servicios"
    CAPACITACION = "CAPACITACION", "Capacitación"
    OTROS = "OTROS", "Otros"


class TipoRecurso(models.TextChoices):
    INTERNO = "INTERNO", "Interno"
    CONTRATISTA = "CONTRATISTA", "Contratista"
    PROVEEDOR = "PROVEEDOR", "Proveedor"


class CategoriaDocumento(models.TextChoices):
    ACTA = "ACTA", "Acta"
    INFORME = "INFORME", "Informe"
    CONTRATO = "CONTRATO", "Contrato"
    DISENO = "DISENO", "Diseño"
    EVIDENCIA = "EVIDENCIA", "Evidencia"
    SOPORTE = "SOPORTE", "Soporte"
    OTRO = "OTRO", "Otro"


class TipoEvento(models.TextChoices):
    CREACION = "CREACION", "Creación"
    ACTUALIZACION = "ACTUALIZACION", "Actualización"
    CAMBIO_ESTADO = "CAMBIO_ESTADO", "Cambio de estado"
    APROBACION = "APROBACION", "Aprobación"
    RECHAZO = "RECHAZO", "Rechazo"
    PUBLICACION = "PUBLICACION", "Publicación"
    CARGA_DOCUMENTO = "CARGA_DOCUMENTO", "Carga de documento"
    NUEVA_VERSION = "NUEVA_VERSION", "Nueva versión"
    LOGIN = "LOGIN", "Inicio de sesión"
    ASIGNACION = "ASIGNACION", "Asignación"
    IMPORTACION = "IMPORTACION", "Importación"


class EstadoCompromiso(models.TextChoices):
    ABIERTO = "ABIERTO", "Abierto"
    CUMPLIDO = "CUMPLIDO", "Cumplido"
    VENCIDO = "VENCIDO", "Vencido"
    CANCELADO = "CANCELADO", "Cancelado"


class EstadoHito(models.TextChoices):
    PENDIENTE = "PENDIENTE", "Pendiente"
    CUMPLIDO = "CUMPLIDO", "Cumplido"
    INCUMPLIDO = "INCUMPLIDO", "Incumplido"
    REPROGRAMADO = "REPROGRAMADO", "Reprogramado"


class EstadoEntregable(models.TextChoices):
    PENDIENTE = "PENDIENTE", "Pendiente"
    ENTREGADO = "ENTREGADO", "Entregado"
    APROBADO = "APROBADO", "Aprobado"


class EstadoFase(models.TextChoices):
    PENDIENTE = "PENDIENTE", "Pendiente"
    EN_PROGRESO = "EN_PROGRESO", "En progreso"
    COMPLETADA = "COMPLETADA", "Completada"


class TipoDependencia(models.TextChoices):
    FI = "FI", "Fin–inicio"
    II = "II", "Inicio–inicio"
    FF = "FF", "Fin–fin"
    IF = "IF", "Inicio–fin"


class ProveedorAuth(models.TextChoices):
    LOCAL = "LOCAL", "Local"
    GOOGLE = "GOOGLE", "Google"


class EstadoSeguimiento(models.TextChoices):
    """No está en la lista explícita de fase-01 §1.1; se añade porque
    Seguimiento.estado (modelo-datos.md §7) necesita sus propias opciones y
    ninguna enumeración existente las cubre."""

    BORRADOR = "BORRADOR", "Borrador"
    PUBLICADO = "PUBLICADO", "Publicado"
