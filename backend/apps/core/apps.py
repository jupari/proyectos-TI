from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.core"

    def ready(self):
        from django.db.models.signals import post_delete, post_save, pre_save

        from apps.core import signals

        pre_save.connect(signals.auditar_pre_save)
        post_save.connect(signals.auditar_post_save)
        post_delete.connect(signals.auditar_post_delete)
