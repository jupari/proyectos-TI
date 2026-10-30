from datetime import UTC, datetime

from django.db import connection
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

VERSION = "0.1.0"


class SaludView(APIView):
    """Endpoint público de verificación de vida y conexión a base de datos."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        try:
            connection.ensure_connection()
            estado_base_datos = "ok"
        except Exception:
            estado_base_datos = "error"

        return Response(
            {
                "estado": "ok",
                "version": VERSION,
                "base_datos": estado_base_datos,
                "hora": datetime.now(UTC).isoformat(),
            }
        )
