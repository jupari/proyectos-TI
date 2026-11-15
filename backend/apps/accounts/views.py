import datetime
import secrets

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import Group
from django.contrib.auth.tokens import default_token_generator
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import SAFE_METHODS, AllowAny, BasePermission, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from apps.core.choices import ProveedorAuth, TipoEvento
from apps.core.exceptions import ErrorConflicto
from apps.core.permissions import EsAdminOSoloLectura
from apps.core.roles import codigos_roles_de
from apps.core.services import registrar_evento
from apps.core.views import ViewSetBase

from .correo import enviar_codigo_2fa, enviar_enlace_recuperacion
from .models import CodigoAccesoDobleFactor, RolMeta, Usuario
from .oauth import (
    canjear_codigo,
    construir_url_autorizacion,
    obtener_o_crear_usuario,
    validar_state,
    verificar_id_token,
)
from .serializers import (
    CambiarClaveSerializer,
    ReenviarCodigoSerializer,
    RestablecerClaveSerializer,
    RolMetaSerializer,
    SolicitarCodigoSerializer,
    SolicitarRecuperacionSerializer,
    UsuarioActualizarSerializer,
    UsuarioActualSerializer,
    UsuarioAdminEscrituraSerializer,
    UsuarioSerializer,
    VerificarCodigoSerializer,
)
from .throttling import CodigoRateThrottle, LoginRateThrottle


def _tokens_de(usuario):
    """Emite el par de tokens propios con los claims de rol, para que login
    local y login con Google devuelvan exactamente la misma forma."""
    refresh = RefreshToken.for_user(usuario)
    refresh["roles"] = list(
        usuario.groups.filter(rol_meta__isnull=False).values_list("rol_meta__codigo", flat=True)
    )
    refresh["nombre_completo"] = usuario.nombre_completo

    usuario.ultimo_acceso_en = timezone.now()
    usuario.save(update_fields=["ultimo_acceso_en"])

    return {
        "access": str(refresh.access_token),
        "refresh": str(refresh),
        "usuario": UsuarioSerializer(usuario).data,
    }


def _generar_y_enviar_codigo(usuario):
    codigo = f"{secrets.randbelow(1_000_000):06d}"
    registro = CodigoAccesoDobleFactor.objects.create(
        usuario=usuario,
        codigo_hash=make_password(codigo),
        expira_en=timezone.now() + datetime.timedelta(minutes=settings.OTP_LIFETIME_MINUTES),
    )
    enviar_codigo_2fa(usuario, codigo)
    return registro


class LoginView(APIView):
    """Primer paso del login local (fase 13): valida email+clave y, si son
    correctas, envía el código de verificación por correo en vez de emitir
    tokens — eso lo hace `VerificarCodigoView` una vez confirmado el código."""

    permission_classes = [AllowAny]
    throttle_classes = [LoginRateThrottle]
    throttle_scope = "login"

    @extend_schema(
        summary="Paso 1 del login local: valida credenciales y envía el código por correo",
        request=SolicitarCodigoSerializer,
        responses={200: {"type": "object", "properties": {
            "requiere_codigo": {"type": "boolean"},
            "login_token": {"type": "string", "format": "uuid"},
        }}},
    )
    def post(self, request):
        serializer = SolicitarCodigoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        registro = _generar_y_enviar_codigo(serializer.validated_data["usuario"])
        return Response({"requiere_codigo": True, "login_token": str(registro.id)})


class VerificarCodigoView(APIView):
    """Segundo paso del login local (fase 13): confirma el código enviado
    por correo y, si es correcto, emite los tokens reales."""

    permission_classes = [AllowAny]
    throttle_classes = [CodigoRateThrottle]
    throttle_scope = "verificar-codigo"

    @extend_schema(
        summary="Paso 2 del login local: verifica el código y emite los tokens",
        request=VerificarCodigoSerializer,
        responses={200: {
            "type": "object",
            "properties": {
                "access": {"type": "string"},
                "refresh": {"type": "string"},
                "usuario": {"$ref": "#/components/schemas/Usuario"},
            },
        }},
    )
    def post(self, request):
        serializer = VerificarCodigoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        usuario = serializer.validated_data["usuario"]

        datos = _tokens_de(usuario)
        registrar_evento(
            tipo_evento=TipoEvento.LOGIN,
            entidad="Usuario",
            entidad_id=usuario.id,
            descripcion=f"Inicio de sesión de {usuario.email}.",
            usuario=usuario,
        )
        return Response(datos)


class ReenviarCodigoView(APIView):
    """Reenvía un código nuevo para un login local pendiente (fase 13), por
    si el primero no llegó o venció, sin reiniciar el login desde cero."""

    permission_classes = [AllowAny]
    throttle_classes = [CodigoRateThrottle]
    throttle_scope = "reenviar-codigo"

    @extend_schema(
        summary="Reenvía el código de verificación de un login pendiente",
        request=ReenviarCodigoSerializer,
        responses={204: None},
    )
    def post(self, request):
        serializer = ReenviarCodigoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        registro = serializer.validated_data["registro"]

        codigo = f"{secrets.randbelow(1_000_000):06d}"
        registro.codigo_hash = make_password(codigo)
        registro.expira_en = timezone.now() + datetime.timedelta(
            minutes=settings.OTP_LIFETIME_MINUTES
        )
        registro.intentos = 0
        registro.save(update_fields=["codigo_hash", "expira_en", "intentos"])
        enviar_codigo_2fa(registro.usuario, codigo)
        return Response(status=status.HTTP_204_NO_CONTENT)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Cierra la sesión",
        description="Pone el refresh token en la blacklist. Responde 204 incluso si el "
        "token ya estaba vencido o es inválido: el cliente nunca debe quedar bloqueado.",
        request=None,
        responses={204: None},
    )
    def post(self, request):
        refresh = request.data.get("refresh")
        if refresh:
            try:
                RefreshToken(refresh).blacklist()
            except TokenError:
                pass

        registrar_evento(
            tipo_evento=TipoEvento.LOGIN,
            entidad="Usuario",
            entidad_id=request.user.id,
            descripcion=f"Cierre de sesión de {request.user.email}.",
            usuario=request.user,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class YoView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user

    def get_serializer_class(self):
        if self.request.method == "PATCH":
            return UsuarioActualizarSerializer
        return UsuarioActualSerializer

    def update(self, request, *args, **kwargs):
        super().update(request, *args, **kwargs)
        return Response(UsuarioActualSerializer(request.user).data)


class CambiarClaveView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Cambia la clave del usuario autenticado",
        request=CambiarClaveSerializer,
        responses={204: None},
    )
    def post(self, request):
        serializer = CambiarClaveSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class SolicitarRecuperacionView(APIView):
    """Fase 13. Siempre responde 200, exista o no el correo — nunca revela
    si una cuenta existe. Solo envía el enlace si existe y es `LOCAL`
    (una cuenta `GOOGLE` no tiene clave propia que recuperar)."""

    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "recuperar-clave"

    @extend_schema(
        summary="Pide el enlace de recuperación de clave por correo",
        request=SolicitarRecuperacionSerializer,
        responses={200: None},
    )
    def post(self, request):
        serializer = SolicitarRecuperacionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        usuario = Usuario.objects.filter(
            email__iexact=serializer.validated_data["email"], proveedor_auth=ProveedorAuth.LOCAL
        ).first()
        if usuario is not None:
            uid = urlsafe_base64_encode(force_bytes(usuario.pk))
            token = default_token_generator.make_token(usuario)
            enlace = f"{settings.FRONTEND_URL}/auth/restablecer?uid={uid}&token={token}"
            enviar_enlace_recuperacion(usuario, enlace)

        mensaje = "Si el correo existe, llegará un enlace para recuperar la clave."
        return Response({"mensaje": mensaje})


class RestablecerClaveView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "recuperar-clave"

    @extend_schema(
        summary="Cambia la clave usando el enlace de recuperación",
        request=RestablecerClaveSerializer,
        responses={204: None},
    )
    def post(self, request):
        serializer = RestablecerClaveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        usuario = serializer.save()
        registrar_evento(
            tipo_evento=TipoEvento.LOGIN,
            entidad="Usuario",
            entidad_id=usuario.id,
            descripcion=f"Recuperación de clave de {usuario.email}.",
            usuario=usuario,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class GoogleAutorizarView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Construye la URL de autorización de Google (PKCE)",
        description="El frontend genera `code_verifier`, calcula `code_challenge` "
        "(S256) y lo envía aquí; el backend construye la URL de Google y devuelve "
        "también `state`. Responde 503 con `OAUTH_NO_CONFIGURADO` si el entorno no "
        "tiene configuradas las credenciales de Google.",
        parameters=[],
        responses={200: {"type": "object", "properties": {
            "url_autorizacion": {"type": "string"},
            "state": {"type": "string"},
        }}},
    )
    def get(self, request):
        code_challenge = request.query_params.get("code_challenge")
        if not code_challenge:
            raise ValidationError({"code_challenge": ["Este parámetro es obligatorio."]})
        url, state = construir_url_autorizacion(code_challenge)
        return Response({"url_autorizacion": url, "state": state})


class GoogleCallbackView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [LoginRateThrottle]
    throttle_scope = "login"

    @extend_schema(
        summary="Canjea el código de Google por tokens propios",
        description="Recibe `{code, state, code_verifier}`, valida el `state`, canjea "
        "el código con Google, verifica el id_token y resuelve (o crea) el usuario. "
        "Devuelve tokens propios con la misma forma que `/auth/login/`.",
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "code": {"type": "string"},
                    "state": {"type": "string"},
                    "code_verifier": {"type": "string"},
                },
                "required": ["code", "state", "code_verifier"],
            }
        },
        responses={200: {
            "type": "object",
            "properties": {
                "access": {"type": "string"},
                "refresh": {"type": "string"},
                "usuario": {"$ref": "#/components/schemas/Usuario"},
            },
        }},
    )
    def post(self, request):
        campos = ("code", "state", "code_verifier")
        faltantes = [campo for campo in campos if not request.data.get(campo)]
        if faltantes:
            raise ValidationError({campo: ["Este campo es obligatorio."] for campo in faltantes})

        validar_state(request.data["state"])
        id_token_str = canjear_codigo(request.data["code"], request.data["code_verifier"])
        info = verificar_id_token(id_token_str)
        usuario = obtener_o_crear_usuario(info)

        datos = _tokens_de(usuario)
        registrar_evento(
            tipo_evento=TipoEvento.LOGIN,
            entidad="Usuario",
            entidad_id=usuario.id,
            descripcion=f"Inicio de sesión con Google de {usuario.email}.",
            usuario=usuario,
        )
        return Response(datos)


class _EsAdminOLecturaPmo(BasePermission):
    """docs/api-contrato.md §8: `usuarios` es `ADMIN: L C E B`, `PMO: L`.
    PMO necesita poder listar usuarios para elegir gerente/líder técnico al
    crear o editar un proyecto (fase 05), aunque no pueda administrarlos."""

    def has_permission(self, request, view):
        codigos = codigos_roles_de(request.user)
        if request.method in SAFE_METHODS:
            return bool(codigos & {"ADMIN", "PMO"})
        return "ADMIN" in codigos


class UsuarioViewSet(ViewSetBase):
    queryset = Usuario.objects.all()
    serializer_lectura_class = UsuarioSerializer
    serializer_escritura_class = UsuarioAdminEscrituraSerializer
    permission_classes = [_EsAdminOLecturaPmo]
    search_fields = ["email", "nombres", "apellidos"]
    ordering_fields = ["email", "nombres", "apellidos", "creado_en"]
    filterset_fields = ["is_active", "proveedor_auth"]

    @extend_schema(summary="Activa un usuario", request=None, responses=UsuarioSerializer)
    @action(detail=True, methods=["post"])
    def activar(self, request, pk=None):
        usuario = self.get_object()
        usuario.is_active = True
        usuario.save(update_fields=["is_active"])
        return Response(UsuarioSerializer(usuario).data)

    @extend_schema(summary="Desactiva un usuario", request=None, responses=UsuarioSerializer)
    @action(detail=True, methods=["post"])
    def desactivar(self, request, pk=None):
        usuario = self.get_object()
        usuario.is_active = False
        usuario.save(update_fields=["is_active"])
        return Response(UsuarioSerializer(usuario).data)

    @extend_schema(summary="Reemplaza los roles del usuario", responses=UsuarioSerializer)
    @action(detail=True, methods=["post"], url_path="asignar-roles")
    def asignar_roles(self, request, pk=None):
        usuario = self.get_object()
        codigos = request.data.get("roles", [])
        grupos = Group.objects.filter(rol_meta__codigo__in=codigos)
        usuario.groups.set(grupos)
        return Response(UsuarioSerializer(usuario).data)


class RolViewSet(ViewSetBase):
    queryset = RolMeta.objects.all()
    serializer_lectura_class = RolMetaSerializer
    serializer_escritura_class = RolMetaSerializer
    permission_classes = [EsAdminOSoloLectura]
    search_fields = ["codigo", "descripcion"]
    ordering_fields = ["orden", "codigo"]

    def perform_destroy(self, instance):
        if instance.es_sistema:
            raise ErrorConflicto("No se puede borrar un rol del sistema.")
        super().perform_destroy(instance)
