"""Cliente HTTP async de la API de Kauta.

Un solo ``httpx.AsyncClient`` persistente (keep-alive, pool de conexiones) para toda
la sesión de la TUI: nunca se abre un cliente nuevo por request. Reproduce el mismo
contrato que ``web/src/api.ts`` (cookie de sesión HttpOnly + token CSRF sincronizado
en la cabecera ``X-CSRF-Token`` para todo método que cambia datos).
"""
from __future__ import annotations

import httpx


class ErrorKauta(Exception):
    """Error de negocio o de validación devuelto por la API (detail del backend)."""

    def __init__(self, status: int, detail: str):
        super().__init__(detail)
        self.status = status
        self.detail = detail


class KautaClient:
    def __init__(self, base_url: str, timeout: float = 10.0):
        self._csrf: str | None = None
        self._cliente = httpx.AsyncClient(base_url=base_url.rstrip("/"), timeout=timeout)

    async def aclose(self) -> None:
        await self._cliente.aclose()

    async def __aenter__(self) -> "KautaClient":
        return self

    async def __aexit__(self, *exc) -> None:
        await self.aclose()

    @property
    def autenticado(self) -> bool:
        return self._csrf is not None

    async def _pedir(self, metodo: str, ruta: str, **kw):
        cabeceras = kw.pop("headers", None) or {}
        if metodo not in ("GET", "HEAD", "OPTIONS") and self._csrf:
            cabeceras["X-CSRF-Token"] = self._csrf
        r = await self._cliente.request(metodo, ruta, headers=cabeceras, **kw)
        if r.status_code >= 400:
            detalle = r.text
            try:
                detalle = r.json().get("detail", detalle)
            except ValueError:
                pass
            raise ErrorKauta(r.status_code, detalle)
        if r.status_code == 204 or not r.content:
            return {}
        return r.json()

    def _fijar_usuario(self, usuario: dict) -> dict:
        if usuario.get("csrf"):
            self._csrf = usuario["csrf"]
        return usuario

    # ------------------------------------------------------------ identidad
    async def personas_demo(self) -> dict:
        return await self._pedir("GET", "/api/auth/demo")

    async def entrar_como(self, correo: str) -> dict:
        datos = await self._pedir("POST", "/api/auth/persona", json={"correo": correo})
        return self._fijar_usuario(datos["usuario"])

    async def iniciar_sesion(self, correo: str, contrasena: str, codigo: str | None = None) -> dict:
        cuerpo = {"correo": correo, "contrasena": contrasena}
        if codigo:
            cuerpo["codigo"] = codigo
        datos = await self._pedir("POST", "/api/auth/login", json=cuerpo)
        if datos.get("mfa_requerido"):
            return datos
        return self._fijar_usuario(datos["usuario"])

    async def cerrar_sesion(self) -> None:
        try:
            await self._pedir("POST", "/api/auth/logout")
        finally:
            self._csrf = None

    async def yo(self) -> dict:
        return await self._pedir("GET", "/api/auth/yo")

    # ------------------------------------------------------------ resumen / rendimiento / auditoría
    async def resumen(self) -> dict:
        return await self._pedir("GET", "/api/resumen")

    async def rendimiento(self, periodo: str | None = None) -> dict:
        return await self._pedir("GET", "/api/rendimiento", params={"periodo": periodo} if periodo else None)

    async def auditoria(self, limite: int = 200, tipo: str | None = None) -> dict:
        params = {"limite": limite}
        if tipo:
            params["tipo"] = tipo
        return await self._pedir("GET", "/api/auditoria", params=params)

    async def seguridad(self) -> dict:
        return await self._pedir("GET", "/api/seguridad")

    # ------------------------------------------------------------ facturas
    async def facturas(self, estado: str | None = None, q: str | None = None) -> list[dict]:
        params = {k: v for k, v in (("estado", estado), ("q", q)) if v}
        return await self._pedir("GET", "/api/facturas", params=params or None)

    async def factura(self, fid: str) -> dict:
        return await self._pedir("GET", f"/api/facturas/{fid}")

    async def aprobar_factura(self, fid: str, comentario: str, codigo_totp: str | None = None) -> dict:
        cuerpo = {"comentario": comentario}
        if codigo_totp:
            cuerpo["codigo_totp"] = codigo_totp
        return await self._pedir("POST", f"/api/facturas/{fid}/aprobar", json=cuerpo)

    async def rechazar_factura(self, fid: str, comentario: str) -> dict:
        return await self._pedir("POST", f"/api/facturas/{fid}/rechazar", json={"comentario": comentario})

    async def aprobaciones_pendientes(self) -> list[dict]:
        return await self._pedir("GET", "/api/aprobaciones")

    async def proveedores(self) -> list[dict]:
        return await self._pedir("GET", "/api/proveedores")

    # ------------------------------------------------------------ dinero
    async def wallet(self) -> dict:
        return await self._pedir("GET", "/api/wallet")

    async def fondear_wallet(self, monto: float) -> dict:
        return await self._pedir("POST", "/api/wallet/fondear", json={"monto": monto})

    async def pagos(self) -> list[dict]:
        return await self._pedir("GET", "/api/pagos")

    async def reintentar_pago(self, pid: str, riel: str | None = None) -> dict:
        return await self._pedir("POST", f"/api/pagos/{pid}/reintentar", json={"riel": riel} if riel else {})

    async def rieles(self) -> list[dict]:
        return await self._pedir("GET", "/api/rieles")

    # ------------------------------------------------------------ simulador
    async def escenarios(self) -> dict:
        return await self._pedir("GET", "/api/simulador/escenarios")

    async def simular_anio(self, meses: int = 12, trampas_pct: int = 30, semilla: int = 7) -> dict:
        return await self._pedir(
            "POST", "/api/simulador/anio",
            json={"meses": meses, "trampas_pct": trampas_pct, "semilla": semilla},
        )

    # ------------------------------------------------------------ personas
    async def personas(self) -> dict:
        return await self._pedir("GET", "/api/personas")
