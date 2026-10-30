param(
    [Parameter(Position = 0)]
    [ValidateSet("up", "down", "logs", "migrate", "shell", "test", "seed")]
    [string]$Comando = "up"
)

$ComposeFile = Join-Path $PSScriptRoot "..\infra\docker-compose.yml"

switch ($Comando) {
    "up" {
        docker compose -f $ComposeFile up -d --build
    }
    "down" {
        docker compose -f $ComposeFile down
    }
    "logs" {
        docker compose -f $ComposeFile logs -f
    }
    "migrate" {
        docker compose -f $ComposeFile exec backend python manage.py migrate
    }
    "shell" {
        docker compose -f $ComposeFile exec backend python manage.py shell
    }
    "test" {
        docker compose -f $ComposeFile exec backend pytest -q
    }
    "seed" {
        docker compose -f $ComposeFile exec backend python manage.py seed_demo
    }
}
