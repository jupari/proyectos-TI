import secrets

from django.contrib.auth.models import Group
from django.contrib.auth.password_validation import validate_password
from django.db.models import Q
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from apps.accounts.models import RolMeta, Usuario
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

    class Meta:
        model = Usuario
        fields = ["email", "nombres", "apellidos", "cargo", "telefono", "is_active", "roles"]

    def create(self, validated_data):
        codigos_roles = validated_data.pop("roles", [])
        clave_temporal = secrets.token_urlsafe(12)
        usuario = Usuario.objects.create(**validated_data)
        usuario.set_password(clave_temporal)
        usuario.debe_cambiar_clave = True
        usuario.save(update_fields=["password", "debe_cambiar_clave"])
        self._asignar_roles(usuario, codigos_roles)
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


class LoginSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["roles"] = list(
            user.groups.filter(rol_meta__isnull=False).values_list("rol_meta__codigo", flat=True)
        )
        token["nombre_completo"] = user.nombre_completo
        return token

    def validate(self, attrs):
        email = attrs.get(self.username_field)
        usuario = Usuario.objects.filter(email=email).first()
        if usuario is not None and usuario.proveedor_auth == ProveedorAuth.GOOGLE:
            raise AuthenticationFailed("Esta cuenta inicia sesión con Google.")
        return super().validate(attrs)


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
