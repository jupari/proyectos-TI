from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser, Group
from django.db import models
from django.utils import timezone

from apps.core.choices import ProveedorAuth
from apps.core.models import ModeloBase


class UsuarioManager(BaseUserManager):
    use_in_migrations = True

    def _crear_usuario(self, email, password, **extra_fields):
        if not email:
            raise ValueError("El usuario debe tener un email.")
        email = self.normalize_email(email)
        usuario = self.model(email=email, **extra_fields)
        usuario.set_password(password)
        usuario.save(using=self._db)
        return usuario

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._crear_usuario(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("nombres", "Admin")
        extra_fields.setdefault("apellidos", "Sistema")
        return self._crear_usuario(email, password, **extra_fields)


class Usuario(AbstractUser, ModeloBase):
    username = None
    first_name = None
    last_name = None

    email = models.EmailField("correo electrónico", unique=True)
    nombres = models.CharField(max_length=120)
    apellidos = models.CharField(max_length=120)
    cargo = models.CharField(max_length=120, blank=True)
    telefono = models.CharField(max_length=40, blank=True)
    proveedor_auth = models.CharField(
        max_length=20, choices=ProveedorAuth.choices, default=ProveedorAuth.LOCAL
    )
    google_sub = models.CharField(max_length=64, unique=True, null=True, blank=True)
    avatar_url = models.URLField(null=True, blank=True)  # noqa: DJ001
    ultimo_acceso_en = models.DateTimeField(null=True, blank=True)
    debe_cambiar_clave = models.BooleanField(default=False)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["nombres", "apellidos"]

    objects = UsuarioManager()

    class Meta:
        verbose_name = "usuario"
        verbose_name_plural = "usuarios"
        ordering = ["nombres", "apellidos"]

    def __str__(self):
        return f"{self.nombre_completo} <{self.email}>"

    @property
    def nombre_completo(self):
        return f"{self.nombres} {self.apellidos}"


class CodigoAccesoDobleFactor(ModeloBase):
    """Código de 6 dígitos enviado por correo para completar un login local
    (fase 13). Su `id` (UUID heredado de `ModeloBase`) hace de `login_token`
    que el frontend pasa junto con el código: es impredecible y de un solo
    registro, no hace falta firmarlo."""

    usuario = models.ForeignKey(
        "accounts.Usuario", on_delete=models.CASCADE, related_name="codigos_2fa"
    )
    codigo_hash = models.CharField(max_length=128)
    expira_en = models.DateTimeField()
    intentos = models.PositiveSmallIntegerField(default=0)
    usado_en = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "código de doble factor"
        verbose_name_plural = "códigos de doble factor"

    def vigente(self):
        return self.usado_en is None and self.expira_en > timezone.now()


class RolMeta(ModeloBase):
    grupo = models.OneToOneField(Group, on_delete=models.CASCADE, related_name="rol_meta")
    codigo = models.CharField(max_length=20)
    descripcion = models.CharField(max_length=255)
    es_sistema = models.BooleanField(default=False)
    orden = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "rol"
        verbose_name_plural = "roles"
        ordering = ["orden"]
        constraints = [
            models.UniqueConstraint(fields=["codigo"], name="rolmeta_codigo_unico"),
        ]

    def __str__(self):
        return f"{self.codigo} — {self.descripcion}"
