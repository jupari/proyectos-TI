<#
Respaldo diario de la base de datos de desarrollo (dev). Pensado para
ejecutarse como tarea programada de Windows mientras se cargan datos reales,
antes de que exista el entorno de producción (fase 11, pendiente).
Conserva los últimos 14 respaldos; los más viejos se borran.
#>

$ErrorActionPreference = "Stop"

$raiz = Split-Path -Parent $PSScriptRoot
$carpetaBackups = Join-Path $raiz "backups"
$archivoLog = Join-Path $carpetaBackups "respaldar_bd.log"
$diasARetener = 14

if (-not (Test-Path $carpetaBackups)) {
    New-Item -ItemType Directory -Path $carpetaBackups -Force | Out-Null
}

function Escribir-Log($mensaje) {
    $linea = "[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $mensaje
    Add-Content -Path $archivoLog -Value $linea -Encoding utf8
}

try {
    Push-Location $raiz

    $composeArgs = @("compose", "-f", "infra/docker-compose.yml", "-f", "infra/docker-compose.override.yml")
    $estadoDb = docker @composeArgs ps db --format json 2>$null
    if (-not $estadoDb -or $estadoDb -notmatch '"State":"running"') {
        Escribir-Log "El contenedor 'db' no está corriendo; se omite el respaldo de hoy."
        exit 0
    }

    $marca = Get-Date -Format "yyyyMMdd_HHmmss"
    $nombreArchivo = "respaldo_$marca.dump"
    $destino = Join-Path $carpetaBackups $nombreArchivo

    $env:MSYS_NO_PATHCONV = "1"
    docker @composeArgs exec -T db pg_dump -U seguimiento -d seguimiento -F c -f "/tmp/$nombreArchivo"
    docker @composeArgs cp "db:/tmp/$nombreArchivo" $destino
    docker @composeArgs exec -T db rm -f "/tmp/$nombreArchivo"

    Escribir-Log "Respaldo creado: $nombreArchivo"

    Get-ChildItem -Path $carpetaBackups -Filter "respaldo_*.dump" |
        Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-$diasARetener) } |
        ForEach-Object {
            Remove-Item $_.FullName -Force
            Escribir-Log "Respaldo antiguo eliminado: $($_.Name)"
        }
}
catch {
    Escribir-Log "ERROR: $($_.Exception.Message)"
    throw
}
finally {
    Pop-Location
}
