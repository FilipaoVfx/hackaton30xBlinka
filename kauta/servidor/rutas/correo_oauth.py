"""La cuenta se conecta desde un enlace privado; los perfiles ficticios de la demo no pueden generarlo."""
from html import escape

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field

from ..servicios import gmail_oauth as oauth
from ..servicios.gmail import ErrorGmail

r = APIRouter(prefix="/api/correo/oauth", tags=["Conexión Gmail"])


def pagina(titulo: str, contenido: str):
    return HTMLResponse('<!doctype html><html lang="es"><meta charset="utf-8">'
                        '<meta name="viewport" content="width=device-width,initial-scale=1">'
                        '<title>Kauta · Gmail</title><link rel="stylesheet" href="/api/correo/oauth/interfaz.css">'
                        '<main><p>Kauta · Autónoma, pero cauta.</p><h1>' + escape(titulo) + '</h1>' + contenido + '</main></html>')


@r.get("/conectar", include_in_schema=False)
def conectar():
    return pagina("Conectar Gmail", '<p>Autoriza la lectura de facturas para ' + escape(oauth.CONFIG_GMAIL.cuenta) +
                  '.</p><p>Google regresará a Kauta al terminar.</p><button id="conectar">Autorizar en Google</button>'
                  '<p id="estado" role="status"></p><script src="/api/correo/oauth/interfaz.js" defer></script>')


@r.get("/interfaz.css", include_in_schema=False)
def css():
    return Response('body{font:16px/1.6 system-ui,sans-serif;background:#F5F7FB;color:#0B1736;margin:0;padding:24px}'
                    'main{max-width:520px;margin:8vh auto;background:white;padding:32px;border:1px solid #E3E8F2;border-radius:16px}'
                    'h1{font-size:28px}button{background:#3B5BFD;color:white;border:0;border-radius:8px;padding:14px 20px;'
                    'font:inherit;cursor:pointer}button:disabled{opacity:.6}a{color:#3B5BFD}#estado{overflow-wrap:anywhere}',
                    media_type="text/css")


@r.get("/interfaz.js", include_in_schema=False)
def js():
    return Response('const clave=location.hash.slice(1);history.replaceState(null,"",location.pathname);'
                    'const boton=document.getElementById("conectar"),estado=document.getElementById("estado");'
                    'if(!clave){boton.disabled=true;estado.textContent="Abre el enlace privado de conexión que te compartió el administrador.";}'
                    'boton.onclick=async()=>{boton.disabled=true;estado.textContent="Preparando autorización…";try{'
                    'const r=await fetch("/api/correo/oauth/iniciar",{method:"POST",headers:{"Content-Type":"application/json"},'
                    'body:JSON.stringify({clave})});const d=await r.json();if(!r.ok)throw new Error(d.detail||"No se pudo conectar.");'
                    'location.assign(d.url);}catch(e){estado.textContent=e.message;boton.disabled=false;}};',
                    media_type="application/javascript")


class Inicio(BaseModel):
    clave: str = Field(min_length=1, max_length=200)


@r.post("/iniciar")
def iniciar(datos: Inicio):
    try:
        url, cookie = oauth.iniciar(datos.clave)
    except ErrorGmail as e:
        raise HTTPException(400, str(e))
    respuesta = JSONResponse({"url": url})
    respuesta.set_cookie(oauth.COOKIE, cookie, max_age=600, httponly=True, secure=True,
                         samesite="lax", path="/api/correo/oauth")
    return respuesta


@r.get("/callback", include_in_schema=False)
def callback(request: Request):
    p = dict(request.query_params)
    # Uvicorn registra la respuesta después de ejecutarnos: nunca guardar el código en su access log.
    request.scope["query_string"] = b""
    try:
        oauth.completar(p.get("state", ""), request.cookies.get(oauth.COOKIE, ""), p.get("code", ""), p.get("error", ""))
        respuesta = pagina("Gmail conectado", '<p>La autorización se guardó. La recepción consultará el buzón en el próximo minuto.</p>'
                           '<a href="/#/facturas">Volver a las facturas</a>')
    except ErrorGmail as e:
        respuesta = pagina("No se completó la autorización", '<p>' + escape(str(e)) + '</p>')
        respuesta.status_code = 400
    respuesta.delete_cookie(oauth.COOKIE, path="/api/correo/oauth", secure=True, httponly=True, samesite="lax")
    return respuesta
