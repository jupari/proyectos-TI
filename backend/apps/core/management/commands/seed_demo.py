import datetime
import random
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.accounts.models import Usuario
from apps.accounts.tests.factories import sembrar_roles
from apps.catalogos.models import Area, PerfilRecurso, Portafolio
from apps.catalogos.tests.factories import AreaFactory, PerfilRecursoFactory, PortafolioFactory
from apps.core.choices import (
    CategoriaDocumento,
    CategoriaRubro,
    EstadoAprobacion,
    EstadoProyecto,
    EstadoSeguimiento,
    Periodicidad,
    Semaforo,
)
from apps.ejecucion.tests.factories import GastoEjecutadoFactory, RegistroEjecucionFactory
from apps.expediente.tests.factories import DocumentoExpedienteFactory, EntradaBitacoraFactory
from apps.proyectos.models import Proyecto
from apps.proyectos.tests.factories import (
    FaseProyectoFactory,
    HitoFactory,
    ProyectoFactory,
    RubroPresupuestoFactory,
)
from apps.recursos.models import Recurso
from apps.recursos.tests.factories import (
    AsignacionRecursoFactory,
    RecursoFactory,
    TarifaRecursoFactory,
)
from apps.seguimiento.tests.factories import CompromisoSeguimientoFactory, SeguimientoFactory
from apps.tareas.tests.factories import TareaFactory

SEMILLA = 42

CONTRASENA_DEMO = "Seguimiento2026!"

USUARIOS_DEMO = [
    ("admin@seguimiento.local", "ADMIN", "Ana", "Dirección"),
    ("pmo@seguimiento.local", "PMO", "Pedro", "Molano"),
    ("lider@seguimiento.local", "LIDER", "Laura", "Idárraga"),
    ("recurso@seguimiento.local", "RECURSO", "Ricardo", "Campos"),
    ("consulta@seguimiento.local", "CONSULTA", "Carla", "Soto"),
]

NOMBRES_RECURSOS = [
    "Recurso Demo 01",
    "Recurso Demo 02",
    "Recurso Demo 03",
    "Recurso Demo 04",
    "Recurso Demo 05",
    "Recurso Demo 06",
    "Recurso Demo 07",
    "Recurso Demo 08",
]

CODIGOS_PROYECTOS_DEMO = [
    "PRY-2026-001",
    "PRY-2026-002",
    "PRY-2026-003",
    "PRY-2026-004",
]


class Command(BaseCommand):
    help = "Crea datos de demostración idempotentes para el panel de seguimiento."

    def add_arguments(self, parser):
        parser.add_argument(
            "--limpiar",
            action="store_true",
            help="Borra los datos de demostración antes de recrearlos.",
        )

    def handle(self, *args, **options):
        random.seed(SEMILLA)

        if options["limpiar"]:
            self._limpiar()

        with transaction.atomic():
            resumen = self._crear_datos()

        self._imprimir_resumen(resumen)

    def _limpiar(self):
        """Borra solo los datos de demostración (nunca usuarios reales ni is_superuser)."""
        self.stdout.write("Limpiando datos de demostración previos...")
        Proyecto.objects.filter(codigo__in=CODIGOS_PROYECTOS_DEMO).delete()
        Recurso.objects.filter(nombre__in=NOMBRES_RECURSOS).delete()
        Area.objects.filter(codigo__startswith="AREA-DEMO").delete()
        Portafolio.objects.filter(codigo__startswith="PORT-DEMO").delete()
        PerfilRecurso.objects.filter(codigo__startswith="PERFIL-DEMO").delete()
        # Los usuarios de demostración nunca se borran aquí: get_or_create los reutiliza.

    def _crear_datos(self):
        resumen = {}

        roles = sembrar_roles()
        usuarios = {}
        for email, codigo_rol, nombres, apellidos in USUARIOS_DEMO:
            usuario, _ = Usuario.objects.get_or_create(
                email=email,
                defaults={
                    "nombres": nombres,
                    "apellidos": apellidos,
                    "is_staff": codigo_rol in ("ADMIN", "PMO"),
                    "is_superuser": codigo_rol == "ADMIN",
                },
            )
            usuario.set_password(CONTRASENA_DEMO)
            usuario.save()
            usuario.groups.add(roles[codigo_rol].grupo)
            usuarios[codigo_rol] = usuario
        resumen["usuarios"] = len(usuarios)

        areas = [
            AreaFactory(codigo=f"AREA-DEMO-{i:02d}", nombre=nombre, responsable=usuarios["PMO"])
            for i, nombre in enumerate(["Tecnología", "Operaciones", "Finanzas"], start=1)
        ]
        resumen["areas"] = len(areas)

        portafolios = [
            PortafolioFactory(
                codigo=f"PORT-DEMO-{i:02d}", nombre=nombre, responsable=usuarios["PMO"]
            )
            for i, nombre in enumerate(["Transformación Digital", "Eficiencia Operativa"], start=1)
        ]
        resumen["portafolios"] = len(portafolios)

        perfiles = [
            PerfilRecursoFactory(
                codigo=f"PERFIL-DEMO-{i:02d}", nombre=nombre, tarifa_hora_referencia=valor
            )
            for i, (nombre, valor) in enumerate(
                [
                    ("Desarrollador Junior", 45000),
                    ("Desarrollador Senior", 85000),
                    ("Analista Funcional", 65000),
                    ("Líder Técnico", 110000),
                    ("QA", 55000),
                    ("Arquitecto", 130000),
                ],
                start=1,
            )
        ]
        resumen["perfiles"] = len(perfiles)

        hoy = datetime.date.today()
        recursos = []
        for i, nombre in enumerate(NOMBRES_RECURSOS):
            recurso = RecursoFactory(
                nombre=nombre,
                perfil=perfiles[i % len(perfiles)],
                capacidad_horas_mes=160,
                fecha_ingreso=datetime.date(2024, 1, 1),
            )
            TarifaRecursoFactory(
                recurso=recurso,
                valor_hora=perfiles[i % len(perfiles)].tarifa_hora_referencia,
                vigente_desde=datetime.date(2024, 1, 1),
            )
            recursos.append(recurso)
        resumen["recursos"] = len(recursos)

        proyectos = self._crear_proyectos(usuarios, areas, portafolios, recursos, hoy)
        resumen["proyectos"] = len(proyectos)

        resumen["tareas"] = self._crear_tareas(proyectos)
        resumen["registros_ejecucion"] = self._crear_registros_ejecucion(proyectos, recursos, hoy)
        resumen["gastos_ejecutados"] = self._crear_gastos(proyectos)
        resumen["seguimientos"] = self._crear_seguimientos(proyectos, usuarios)
        resumen["documentos_expediente"] = self._crear_documentos(proyectos)

        return resumen

    def _crear_proyectos(self, usuarios, areas, portafolios, recursos, hoy):
        definiciones = [
            {
                "codigo": "PRY-2026-001",
                "nombre": "Modernización ERP (en riesgo)",
                "estado": EstadoProyecto.EJECUCION,
                "semaforo": Semaforo.ROJO,
                "presupuesto_dinero": 50_000_000,
            },
            {
                "codigo": "PRY-2026-002",
                "nombre": "Portal de Autoservicio",
                "estado": EstadoProyecto.EJECUCION,
                "semaforo": Semaforo.VERDE,
                "presupuesto_dinero": 120_000_000,
            },
            {
                "codigo": "PRY-2026-003",
                "nombre": "Migración a la Nube (cerrado)",
                "estado": EstadoProyecto.CERRADO,
                "semaforo": Semaforo.VERDE,
                "presupuesto_dinero": 90_000_000,
            },
            {
                "codigo": "PRY-2026-004",
                "nombre": "Analítica Avanzada (borrador)",
                "estado": EstadoProyecto.BORRADOR,
                "semaforo": Semaforo.VERDE,
                "presupuesto_dinero": 60_000_000,
            },
        ]

        proyectos = []
        for i, datos in enumerate(definiciones):
            proyecto = ProyectoFactory(
                codigo=datos["codigo"],
                nombre=datos["nombre"],
                area_solicitante=areas[i % len(areas)],
                portafolio=portafolios[i % len(portafolios)],
                gerente=usuarios["PMO"],
                lider_tecnico=usuarios["LIDER"],
                estado=datos["estado"],
                fecha_inicio_plan=hoy - datetime.timedelta(days=180),
                fecha_fin_plan=hoy + datetime.timedelta(days=180),
                fecha_inicio_real=hoy - datetime.timedelta(days=170)
                if datos["estado"] != EstadoProyecto.BORRADOR
                else None,
                fecha_fin_real=hoy - datetime.timedelta(days=5)
                if datos["estado"] == EstadoProyecto.CERRADO
                else None,
                presupuesto_horas=2000,
                presupuesto_dinero=datos["presupuesto_dinero"],
                avance_reportado=80 if datos["estado"] == EstadoProyecto.CERRADO else 40,
            )
            proyecto.semaforo = datos["semaforo"]
            proyecto.save(update_fields=["semaforo"])

            for orden in range(4):
                FaseProyectoFactory(
                    proyecto=proyecto,
                    orden=orden,
                    nombre=f"Fase {orden + 1}",
                    peso=25,
                    fecha_inicio_plan=hoy - datetime.timedelta(days=180 - orden * 45),
                    fecha_fin_plan=hoy - datetime.timedelta(days=135 - orden * 45),
                )

            for n in range(2):
                HitoFactory(
                    proyecto=proyecto,
                    nombre=f"Hito {n + 1} — {proyecto.codigo}",
                    fecha_plan=hoy + datetime.timedelta(days=30 * (n + 1)),
                )

            presupuesto_dinero = Decimal(datos["presupuesto_dinero"])
            rubro_personal = RubroPresupuestoFactory(
                proyecto=proyecto,
                categoria=CategoriaRubro.PERSONAL,
                descripcion="Personal del proyecto",
                monto_planeado=presupuesto_dinero * Decimal("0.6"),
            )
            RubroPresupuestoFactory(
                proyecto=proyecto,
                categoria=CategoriaRubro.LICENCIAS,
                descripcion="Licencias de software",
                monto_planeado=presupuesto_dinero * Decimal("0.4"),
            )
            proyecto._rubro_personal = rubro_personal

            for n in range(2):
                recurso = recursos[(i * 2 + n) % len(recursos)]
                AsignacionRecursoFactory(
                    proyecto=proyecto,
                    recurso=recurso,
                    rol_en_proyecto="Desarrollador",
                    fecha_desde=hoy - datetime.timedelta(days=170),
                    fecha_hasta=hoy + datetime.timedelta(days=170),
                    porcentaje_dedicacion=50,
                    horas_planeadas=500,
                    valor_hora_plan=70000,
                )

            proyectos.append(proyecto)

        # Sobrecosto deliberado en el primer proyecto para que su GastoEjecutado
        # supere el rubro planeado y el semáforo rojo quede justificado.
        rubro_sobrecosto = proyectos[0]._rubro_personal
        GastoEjecutadoFactory(
            proyecto=proyectos[0],
            rubro=rubro_sobrecosto,
            fecha=hoy - datetime.timedelta(days=10),
            monto=rubro_sobrecosto.monto_planeado * Decimal("1.3"),
            proveedor="Proveedor Sobrecosto S.A.S.",
            numero_documento="FAC-SOBRECOSTO-01",
            estado_aprobacion=EstadoAprobacion.APROBADO,
        )

        return proyectos

    def _crear_tareas(self, proyectos):
        total = 0
        for proyecto in proyectos:
            for n in range(10):
                TareaFactory(
                    proyecto=proyecto,
                    nombre=f"Tarea {n + 1} de {proyecto.nombre}",
                    horas_estimadas=40,
                    fecha_inicio_plan=proyecto.fecha_inicio_plan,
                    fecha_fin_plan=proyecto.fecha_fin_plan,
                )
                total += 1
        return total

    def _crear_registros_ejecucion(self, proyectos, recursos, hoy):
        periodicidades = [Periodicidad.DIARIA, Periodicidad.SEMANAL, Periodicidad.MENSUAL]
        total = 0
        for i, proyecto in enumerate(proyectos):
            for n in range(30):
                recurso = recursos[(i + n) % len(recursos)]
                periodicidad = periodicidades[n % len(periodicidades)]
                inicio = hoy - datetime.timedelta(days=(n + 1) * 2)
                if periodicidad == Periodicidad.DIARIA:
                    fin = inicio
                elif periodicidad == Periodicidad.SEMANAL:
                    fin = inicio + datetime.timedelta(days=6)
                else:
                    fin = inicio + datetime.timedelta(days=27)
                RegistroEjecucionFactory(
                    proyecto=proyecto,
                    recurso=recurso,
                    periodicidad=periodicidad,
                    periodo_inicio=inicio,
                    periodo_fin=fin,
                    horas=8,
                    valor_hora_aplicado=70000,
                    estado_aprobacion=EstadoAprobacion.APROBADO,
                )
                total += 1
        return total

    def _crear_gastos(self, proyectos):
        total = 0
        for proyecto in proyectos:
            rubro = proyecto.rubros.first()
            if rubro is None:
                continue
            GastoEjecutadoFactory(
                proyecto=proyecto,
                rubro=rubro,
                fecha=datetime.date.today() - datetime.timedelta(days=20),
                monto=2_000_000,
                proveedor="Proveedor Regular S.A.S.",
                numero_documento=f"FAC-{proyecto.codigo}-01",
                estado_aprobacion=EstadoAprobacion.APROBADO,
            )
            total += 1
        return total

    def _crear_seguimientos(self, proyectos, usuarios):
        total = 0
        hoy = datetime.date.today()
        for i, proyecto in enumerate(proyectos):
            cantidad = 2 if i < 2 else 1
            for n in range(cantidad):
                periodo_inicio = hoy.replace(day=1) - datetime.timedelta(days=30 * (n + 1))
                periodo_inicio = periodo_inicio.replace(day=1)
                if periodo_inicio.month == 12:
                    siguiente_mes = periodo_inicio.replace(year=periodo_inicio.year + 1, month=1)
                else:
                    siguiente_mes = periodo_inicio.replace(month=periodo_inicio.month + 1)
                periodo_fin = siguiente_mes.replace(day=1) - datetime.timedelta(days=1)
                seguimiento = SeguimientoFactory(
                    proyecto=proyecto,
                    periodicidad=Periodicidad.MENSUAL,
                    periodo_inicio=periodo_inicio,
                    periodo_fin=periodo_fin,
                    fecha_corte=periodo_fin,
                    avance_reportado=40,
                    semaforo=proyecto.semaforo,
                    estado=EstadoSeguimiento.PUBLICADO,
                    publicado_por=usuarios["LIDER"],
                    publicado_en=datetime.datetime.combine(
                        periodo_fin, datetime.time(17, 0), tzinfo=datetime.UTC
                    ),
                )
                descripcion_compromiso = (
                    f"Compromiso de seguimiento {seguimiento.periodo_inicio} — {proyecto.codigo}"
                )
                CompromisoSeguimientoFactory(
                    seguimiento=seguimiento,
                    descripcion=descripcion_compromiso,
                    responsable=usuarios["LIDER"],
                    fecha_compromiso=periodo_fin + datetime.timedelta(days=15),
                )
                total += 1
        return total

    def _crear_documentos(self, proyectos):
        total = 0
        for i, proyecto in enumerate(proyectos):
            cantidad = 3 if i < 2 else 2
            for n in range(cantidad):
                DocumentoExpedienteFactory(
                    proyecto=proyecto,
                    categoria=CategoriaDocumento.INFORME,
                    nombre=f"Informe {n + 1} — {proyecto.codigo}",
                    nombre_original=f"informe-{n + 1}.txt",
                )
                total += 1
            EntradaBitacoraFactory(
                proyecto=proyecto,
                descripcion=f"Entrada de bitácora de demostración para {proyecto.codigo}",
            )
        return total

    def _imprimir_resumen(self, resumen):
        self.stdout.write(self.style.SUCCESS("Datos de demostración listos:"))
        for clave, cantidad in resumen.items():
            self.stdout.write(f"  {clave}: {cantidad}")

        self.stdout.write("")
        self.stdout.write("Credenciales de demostración (todas con la misma contraseña):")
        for email, codigo_rol, *_ in USUARIOS_DEMO:
            self.stdout.write(f"  [{codigo_rol}] {email} / {CONTRASENA_DEMO}")
