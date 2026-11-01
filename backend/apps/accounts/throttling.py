from rest_framework.throttling import ScopedRateThrottle


class LoginRateThrottle(ScopedRateThrottle):
    """5/min por IP + email (`settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]["login"]`).

    `ScopedRateThrottle.allow_request()` toma el scope de `view.throttle_scope`
    (no de un atributo de esta clase): cada vista que use este throttle debe
    declarar `throttle_scope = "login"`.
    """

    def get_cache_key(self, request, view):
        email = (request.data.get("email") or "").strip().lower()
        ident = self.get_ident(request)
        identificador = f"{ident}:{email}" if email else ident
        return self.cache_format % {"scope": self.scope, "ident": identificador}
