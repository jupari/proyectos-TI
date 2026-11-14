import re

from django.core.exceptions import ValidationError


class ValidadorComplejidadClave:
    """Exige al menos una mayúscula, una minúscula y un dígito.

    Complementa a `MinimumLengthValidator`/`CommonPasswordValidator`: estos
    revisan longitud y claves comunes, pero ninguno revisa variedad de
    caracteres.
    """

    def validate(self, password, user=None):
        if not re.search(r"[A-Z]", password):
            raise ValidationError(
                "La contraseña debe tener al menos una letra mayúscula.",
                code="password_sin_mayuscula",
            )
        if not re.search(r"[a-z]", password):
            raise ValidationError(
                "La contraseña debe tener al menos una letra minúscula.",
                code="password_sin_minuscula",
            )
        if not re.search(r"\d", password):
            raise ValidationError(
                "La contraseña debe tener al menos un número.",
                code="password_sin_numero",
            )

    def get_help_text(self):
        return "La contraseña debe tener al menos una mayúscula, una minúscula y un número."
