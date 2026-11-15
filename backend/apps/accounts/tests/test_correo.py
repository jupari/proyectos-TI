from unittest.mock import patch

import pytest
from django.core import mail

from apps.accounts.correo import ErrorEnvioCorreo, enviar_codigo_2fa, enviar_enlace_recuperacion
from apps.accounts.tests.factories import UsuarioFactory

pytestmark = pytest.mark.django_db


def test_enviar_codigo_2fa_llega_al_correo_del_usuario():
    usuario = UsuarioFactory(email="persona@demo.local", nombres="Ana")

    enviar_codigo_2fa(usuario, "123456")

    assert len(mail.outbox) == 1
    enviado = mail.outbox[0]
    assert enviado.to == ["persona@demo.local"]
    assert "123456" in enviado.body


def test_enviar_enlace_recuperacion_llega_al_correo_del_usuario():
    usuario = UsuarioFactory(email="persona@demo.local", nombres="Ana")

    enviar_enlace_recuperacion(usuario, "https://app.local/auth/restablecer?uid=1&token=abc")

    assert len(mail.outbox) == 1
    enviado = mail.outbox[0]
    assert enviado.to == ["persona@demo.local"]
    assert "https://app.local/auth/restablecer?uid=1&token=abc" in enviado.body


def test_enviar_codigo_2fa_si_el_smtp_falla_lanza_error_claro_en_vez_de_colgarse():
    usuario = UsuarioFactory(email="persona@demo.local", nombres="Ana")

    with patch("apps.accounts.correo.send_mail", side_effect=TimeoutError("smtp colgado")):
        with pytest.raises(ErrorEnvioCorreo):
            enviar_codigo_2fa(usuario, "123456")
