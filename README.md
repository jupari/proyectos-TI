# Seguimiento de Proyectos de TI

Panel administrativo para el seguimiento de proyectos de TI: control de la ejecución
presupuestal en horas y dinero, ingesta periódica de la ejecución de recursos, gestión de
tareas y su programación, y expediente digital por proyecto.

**Stack:** Django + DRF · PostgreSQL 16 · Angular + Tailwind (componentes propios) ·
Docker Compose · JWT propio + Google OAuth 2.0.

## Estado

Fase 00 (infraestructura y andamiaje) en ejecución. Ver [docs/STACK-LOCK.md](docs/STACK-LOCK.md)
para las versiones reales instaladas.

| Documento | Para qué sirve |
|-----------|----------------|
| [PLAN.md](PLAN.md) | Plan maestro: stack, estructura, convenciones, roles, mapa de fases |
| [docs/modelo-datos.md](docs/modelo-datos.md) | Las 22 entidades con sus campos, reglas y fórmulas de control |
| [docs/api-contrato.md](docs/api-contrato.md) | Endpoints, payloads, matriz de permisos, formato de errores |
| [docs/plan/](docs/plan/) | Un archivo ejecutable por fase, de la 00 a la 11 |
| [docs/STACK-LOCK.md](docs/STACK-LOCK.md) | Versiones reales instaladas |

## Cómo se ejecuta el plan

Cada fase se lanza por separado, en orden, con este prompt:

```
Lee PLAN.md, docs/modelo-datos.md y docs/api-contrato.md.
Luego ejecuta docs/plan/fase-NN-<nombre>.md completo, paso por paso, sin saltarte ninguno
y sin adelantar trabajo de fases posteriores.
Al terminar: corre los comandos de verificación de la fase, pega su salida en la sección
"Evidencia" de ese archivo, marca los criterios de aceptación cumplidos y haz commit en la
rama fase-NN-<nombre>. Si algo falla dos veces, detente y repórtalo con el log completo.
```

Ninguna fase empieza si la anterior no cumple su definición de terminado
([PLAN.md §8](PLAN.md)).

## Puesta en marcha

1. Copia las variables de entorno y ajusta las claves:

   ```bash
   cp .env.example .env
   ```

2. Levanta el entorno completo (Postgres + Django + Angular):

   ```bash
   docker compose -f infra/docker-compose.yml up -d
   ```

   En Windows, con PowerShell, también puedes usar los atajos de `scripts/dev.ps1`:

   ```powershell
   ./scripts/dev.ps1 up       # levanta el entorno
   ./scripts/dev.ps1 migrate  # aplica migraciones
   ./scripts/dev.ps1 seed     # carga datos de demostración
   ./scripts/dev.ps1 test     # corre pytest en el backend
   ./scripts/dev.ps1 logs     # sigue los logs de los tres servicios
   ./scripts/dev.ps1 down     # detiene el entorno
   ```

3. URLs disponibles:

   - Panel (Angular): http://localhost:4200
   - API: http://localhost:8000/api/v1/salud/
   - Swagger: http://localhost:8000/api/schema/swagger/
   - ReDoc: http://localhost:8000/api/schema/redoc/

## Pruebas y lint

```bash
docker compose -f infra/docker-compose.yml exec backend pytest -q
docker compose -f infra/docker-compose.yml exec backend ruff check .
cd frontend && npm run build && npm run lint
```
