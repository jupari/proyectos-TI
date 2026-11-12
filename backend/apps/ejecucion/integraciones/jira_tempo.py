"""Cliente de solo lectura contra Jira Cloud y Tempo Cloud
(docs/plan/fase-12-integracion-jira.md §12.2). Son dos sistemas con tokens
separados: Jira (`JIRA_BASE_URL`/`JIRA_EMAIL`/`JIRA_API_TOKEN`, Basic Auth,
API v3) para resolver proyectos, claves de issue y correos de usuario, y
Tempo (`TEMPO_API_TOKEN`, Bearer, siempre contra `https://api.tempo.io/4`)
para los worklogs. Nunca escribe nada en ninguno de los dos: toda la
integración es unidireccional hacia esta app."""

import requests
from django.conf import settings

from apps.core.exceptions import ErrorApi

TEMPO_BASE_URL = "https://api.tempo.io/4"
TIMEOUT_SEGUNDOS = 15
TAMANO_LOTE_ISSUES = 100


class ErrorIntegracionJira(ErrorApi):
    status_code = 502
    codigo = "INTEGRACION_JIRA"
    default_detail = "No se pudo completar la operación contra Jira/Tempo."


class ClienteJiraTempo:
    def __init__(self):
        self.base_url = (settings.JIRA_BASE_URL or "").rstrip("/")
        self.email = settings.JIRA_EMAIL
        self.jira_token = settings.JIRA_API_TOKEN
        self.tempo_token = settings.TEMPO_API_TOKEN
        self._cache_correos = {}

    def _exigir_configurado(self):
        faltantes = [
            nombre
            for nombre, valor in (
                ("JIRA_BASE_URL", self.base_url),
                ("JIRA_EMAIL", self.email),
                ("JIRA_API_TOKEN", self.jira_token),
                ("TEMPO_API_TOKEN", self.tempo_token),
            )
            if not valor
        ]
        if faltantes:
            raise ErrorIntegracionJira(
                f"Faltan las variables de entorno: {', '.join(faltantes)}."
            )

    def _get_jira(self, ruta, **parametros):
        self._exigir_configurado()
        try:
            respuesta = requests.get(
                f"{self.base_url}{ruta}",
                params=parametros,
                auth=(self.email, self.jira_token),
                headers={"Accept": "application/json"},
                timeout=TIMEOUT_SEGUNDOS,
            )
        except requests.RequestException as exc:
            raise ErrorIntegracionJira(f"No se pudo conectar con Jira: {exc}") from exc
        if respuesta.status_code != 200:
            raise ErrorIntegracionJira(
                f"Jira respondió {respuesta.status_code} en {ruta}: {respuesta.text[:300]}"
            )
        return respuesta.json()

    def _post_jira(self, ruta, cuerpo):
        self._exigir_configurado()
        try:
            respuesta = requests.post(
                f"{self.base_url}{ruta}",
                json=cuerpo,
                auth=(self.email, self.jira_token),
                headers={"Accept": "application/json", "Content-Type": "application/json"},
                timeout=TIMEOUT_SEGUNDOS,
            )
        except requests.RequestException as exc:
            raise ErrorIntegracionJira(f"No se pudo conectar con Jira: {exc}") from exc
        if respuesta.status_code != 200:
            raise ErrorIntegracionJira(
                f"Jira respondió {respuesta.status_code} en {ruta}: {respuesta.text[:300]}"
            )
        return respuesta.json()

    def _get_tempo(self, ruta, **parametros):
        self._exigir_configurado()
        try:
            respuesta = requests.get(
                f"{TEMPO_BASE_URL}{ruta}",
                params=parametros,
                headers={
                    "Authorization": f"Bearer {self.tempo_token}",
                    "Accept": "application/json",
                },
                timeout=TIMEOUT_SEGUNDOS,
            )
        except requests.RequestException as exc:
            raise ErrorIntegracionJira(f"No se pudo conectar con Tempo: {exc}") from exc
        if respuesta.status_code != 200:
            raise ErrorIntegracionJira(
                f"Tempo respondió {respuesta.status_code} en {ruta}: {respuesta.text[:300]}"
            )
        return respuesta.json()

    def listar_proyectos(self):
        """`[{clave, nombre}]` de todos los proyectos visibles para la
        cuenta del token, paginando `/rest/api/3/project/search`."""
        proyectos = []
        inicio = 0
        tamano_pagina = 50
        while True:
            datos = self._get_jira(
                "/rest/api/3/project/search", startAt=inicio, maxResults=tamano_pagina
            )
            for valor in datos.get("values", []):
                proyectos.append({"clave": valor["key"], "nombre": valor["name"]})
            if datos.get("isLast", True):
                break
            inicio += tamano_pagina
        return proyectos

    def obtener_worklogs(self, desde, hasta):
        """Worklogs de Tempo en `[desde, hasta]` (fechas, inclusive), de
        todos los usuarios y proyectos: el filtrado por proyecto/recurso
        mapeado lo hace el servicio de importación, no este cliente."""
        worklogs = []
        desplazamiento = 0
        tamano_pagina = 50
        while True:
            datos = self._get_tempo(
                "/worklogs",
                **{
                    "from": desde.isoformat(),
                    "to": hasta.isoformat(),
                    "limit": tamano_pagina,
                    "offset": desplazamiento,
                },
            )
            resultados = datos.get("results", [])
            worklogs.extend(resultados)
            metadatos = datos.get("metadata", {})
            if not metadatos.get("next") or not resultados:
                break
            desplazamiento += tamano_pagina
        return worklogs

    def resolver_claves_issue(self, issue_ids):
        """`{issue_id: clave}` para varios ids de una sola vez (nunca uno por
        uno): `POST /rest/api/3/search/jql` con `jql=id in (...)`, en lotes
        de `TAMANO_LOTE_ISSUES` ids por llamada. Dos cosas confirmadas
        contra el Jira real al probar esta fase, no solo documentación: un
        `GET` con muchos ids revienta el límite de longitud de URL de Jira
        (414) — por eso es `POST` con el cuerpo en JSON; y el endpoint
        clásico `/rest/api/3/search` ya no existe (410, migrado a
        `/search/jql`), que pagina por `nextPageToken`, no por `startAt`."""
        ids = sorted({str(i) for i in issue_ids})
        if not ids:
            return {}

        resultado = {}
        for inicio in range(0, len(ids), TAMANO_LOTE_ISSUES):
            lote = ids[inicio : inicio + TAMANO_LOTE_ISSUES]
            jql = f"id in ({','.join(lote)})"
            token = None
            while True:
                cuerpo = {"jql": jql, "fields": ["key"], "maxResults": len(lote)}
                if token:
                    cuerpo["nextPageToken"] = token
                datos = self._post_jira("/rest/api/3/search/jql", cuerpo)
                for issue in datos.get("issues", []):
                    resultado[str(issue["id"])] = issue["key"]
                token = datos.get("nextPageToken")
                if not token or datos.get("isLast", True):
                    break
        return resultado

    def resolver_correo_usuario(self, account_id):
        """`{"correo": ..., "nombre": ...}` del `accountId` dado, cacheado en
        memoria durante la vida de esta instancia (una corrida del comando).
        Cualquiera de los dos puede venir en `None` si Jira no lo devuelve
        (cuenta sin permiso de verlo, o inexistente); `nombre` (el
        `displayName` de Jira) es solo para que un omitido por correo sea
        identificable por una persona, nunca se usa para resolver el
        `Recurso` (eso es siempre por correo)."""
        if account_id in self._cache_correos:
            return self._cache_correos[account_id]
        datos = self._get_jira("/rest/api/3/user", accountId=account_id)
        resultado = {"correo": datos.get("emailAddress"), "nombre": datos.get("displayName")}
        self._cache_correos[account_id] = resultado
        return resultado
