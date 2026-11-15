import secrets

from django.conf import settings
from django.contrib.auth.hashers import check_password
from django.contrib.auth.models import Group
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.db.models import Q
from django.utils import timezone
from django.utils.encoding import DjangoUnicodeDecodeError, force_str
from django.utils.http import urlsafe_base64_decode
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed, ValidationError

from apps.accounts.models import CodigoAccesoDobleFactor, RolMeta, Usuario
from apps.accounts.permisos_ui import permisos_de
from apps.core.choices import ProveedorAuth


class UsuarioSerializer(serializers.ModelSerializer):
    roles = serializers.SerializerMethodField()
    permisos_ui = serializers.SerializerMethodField()

    class Meta:
        model = Usuario
        fields = [
            "id",
            "email",
            "nombres",
            "apellidos",
            "cargo",
            "telefono",
            "avatar_url",
            "proveedor_auth",
            "debe_cambiar_clave",
            "is_active",
            "roles",
            "permisos_ui",
        ]
        read_only_fields = fields

    def get_roles(self, obj) -> list[str]:
        return list(
            obj.groups.filter(rol_meta__isnull=False).values_list("rol_meta__codigo", flat=True)
        )

    def get_permisos_ui(self, obj) -> list[str]:
        return permisos_de(obj)


class UsuarioActualSerializer(UsuarioSerializer):
    proyectos_liderados = serializers.SerializerMethodField()

    class Meta(UsuarioSerializer.Meta):
        fields = [*UsuarioSerializer.Meta.fields, "proyectos_liderados"]
        read_only_fields = fields

    def get_proyectos_liderados(self, obj) -> list[dict]:
        from apps.proyectos.models import Proyecto

        proyectos = Proyecto.objects.filter(
            Q(gerente=obj) | Q(lider_tecnico=obj), activo=True
        ).values("id", "codigo", "nombre")
        return list(proyectos)


class UsuarioActualizarSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = ["nombres", "apellidos", "cargo", "telefono"]


class UsuarioAdminEscrituraSerializer(serializers.ModelSerializer):
    roles = serializers.ListField(child=serializers.CharField(), write_only=True, required=False)
    # No es un campo del modelo: solo viaja en la respuesta de creación (ver
    # `create`), que es la única vez que existe en texto plano. No hay envío
    # de correo en esta versión (PLAN.md §10), así que es la única forma de
    # que quien crea la cuenta pueda comunicar la clave inicial.
    clave_temporal = serializers.SerializerMethodField()

    class Meta:
        model = Usuario
        fields = [
            "email",
            "nombres",
            "apellidos",
            "cargo",
            "telefono",
            "is_active",
            "roles",
            "clave_temporal",
        ]

    def get_clave_temporal(self, obj) -> str | None:
        return getattr(obj, "_clave_temporal", None)

    def create(self, validated_data):
        codigos_roles = validated_data.pop("roles", [])
        clave_temporal = secrets.token_urlsafe(12)
        usuario = Usuario.objects.create(**validated_data)
        usuario.set_password(clave_temporal)
        usuario.debe_cambiar_clave = True
        usuario.save(update_fields=["password", "debe_cambiar_clave"])
        self._asignar_roles(usuario, codigos_roles)
        usuario._clave_temporal = clave_temporal
        return usuario

    def update(self, instance, validated_data):
        codigos_roles = validated_data.pop("roles", None)
        for campo, valor in validated_data.items():
            setattr(instance, campo, valor)
        instance.save()
        if codigos_roles is not None:
            self._asignar_roles(instance, codigos_roles)
        return instance

    def _asignar_roles(self, usuario, codigos_roles):
        if codigos_roles:
            grupos = Group.objects.filter(rol_meta__codigo__in=codigos_roles)
            usuario.groups.set(grupos)


class RolMetaSerializer(serializers.ModelSerializer):
    class Meta:
        model = RolMeta
        fields = ["id", "codigo", "descripcion", "es_sistema", "orden", "activo"]
        read_only_fields = ["es_sistema"]


class SolicitarCodigoSerializer(serializers.Serializer):
    """Primer paso del login local (fase 13): valida email+clave pero no
    emite tokens todavía — eso lo hace `VerificarCodigoSerializer` una vez
    confirmado el código que se envía por correo tras este paso.

    No hereda de `TokenObtainPairSerializer`: ese serializer emite un
    `RefreshToken` real como efecto secundario de `validate()` (y con
    `BLACKLIST_AFTER_ROTATION` activo, cada uno deja un `OutstandingToken` en
    la base aunque nunca se use) — más simple verificar credenciales a mano
    sin ese efecto secundario.
    """

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        usuario = Usuario.objects.filter(email__iexact=attrs["email"]).first()
        if usuario is not None and usuario.proveedor_auth == ProveedorAuth.GOOGLE:
            raise AuthenticationFailed("Esta cuenta inicia sesión con Google.")
        # Mismo mensaje y código que usaba `TokenObtainPairSerializer` por
        # defecto, para no cambiarle el contrato de error al frontend.
        clave_valida = usuario is not None and usuario.check_password(attrs["password"])
        if usuario is None or not usuario.is_active or not clave_valida:
            raise AuthenticationFailed(
                "No active account found with the given credentials",
                code="no_active_account",
            )
        attrs["usuario"] = usuario
        return attrs


class VerificarCodigoSerializer(serializers.Serializer):
    login_token = serializers.UUIDField()
    codigo = serializers.CharField()

    def validate(self, attrs):
        registro = (
            CodigoAccesoDobleFactor.objects.select_related("usuario")
            .filter(id=attrs["login_token"])
            .first()
        )
        if registro is None or not registro.vigente():
            raise AuthenticationFailed("El código es inválido o ya venció.")

        if not check_password(attrs["codigo"], registro.codigo_hash):
            registro.intentos += 1
            if registro.intentos >= settings.OTP_MAX_INTENTOS:
                registro.usado_en = timezone.now()
            registro.save(update_fields=["intentos", "usado_en"])
            raise AuthenticationFailed("El código no es correcto.")

        registro.usado_en = timezone.now()
        registro.save(update_fields=["usado_en"])
        attrs["usuario"] = registro.usuario
        return attrs


class ReenviarCodigoSerializer(serializers.Serializer):
    login_token = serializers.UUIDField()

    def validate(self, attrs):
        registro = CodigoAccesoDobleFactor.objects.filter(id=attrs["login_token"]).first()
        if registro is None or registro.usado_en is not None:
            raise AuthenticationFailed("El código es inválido o ya venció.")
        attrs["registro"] = registro
        return attrs


class CambiarClaveSerializer(serializers.Serializer):
    clave_actual = serializers.CharField(write_only=True)
    clave_nueva = serializers.CharField(write_only=True)

    def validate_clave_actual(self, value):
        usuario = self.context["request"].user
        if not usuario.check_password(value):
            raise serializers.ValidationError("La clave actual no es correcta.")
        return value

    def validate_clave_nueva(self, value):
        validate_password(value, user=self.context["request"].user)
        return value

    def save(self):
        usuario = self.context["request"].user
        usuario.set_password(self.validated_data["clave_nueva"])
        usuario.debe_cambiar_clave = False
        usuario.save(update_fields=["password", "debe_cambiar_clave"])
        return usuario


class SolicitarRecuperacionSerializer(serializers.Serializer):
    """Fase 13. Solo valida el formato del correo: la vista decide en
    silencio si existe un usuario y si corresponde enviarle algo — este
    endpoint nunca revela si una cuenta existe."""

    email = serializers.EmailField()


class RestablecerClaveSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    clave_nueva = serializers.CharField(write_only=True)

    def validate(self, attrs):
        try:
            pk = force_str(urlsafe_base64_decode(attrs["uid"]))
            usuario = Usuario.objects.get(pk=pk)
        except (
            TypeError,
            ValueError,
            OverflowError,
            DjangoUnicodeDecodeError,
            Usuario.DoesNotExist,
        ):
            raise ValidationError({"uid": ["El enlace de recuperación no es válido."]}) from None

        if not default_token_generator.check_token(usuario, attrs["token"]):
            raise ValidationError(
                {"token": ["El enlace de recuperación no es válido o ya venció."]}
            )

        validate_password(attrs["clave_nueva"], user=usuario)
        attrs["usuario"] = usuario
        return attrs

    def save(self):
        usuario = self.validated_data["usuario"]
        usuario.set_password(self.validated_data["clave_nueva"])
        usuario.debe_cambiar_clave = False
        usuario.save(update_fields=["password", "debe_cambiar_clave"])
        return usuario
