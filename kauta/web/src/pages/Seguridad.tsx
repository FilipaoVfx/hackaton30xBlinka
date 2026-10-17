import { useCallback, useState } from "react";
import { Fingerprint, KeyRound, LogOut, MonitorSmartphone, ShieldCheck } from "lucide-react";
import { api, avisarCambio, fecha, useApi, useCambios, type Usuario } from "../api";
import { Aviso, Boton, Campo, Cargando, claseEntrada, cx, Encabezado, Hash, Panel, useToast } from "../ui";

const ESTADO: Record<string, string> = {
  activo: "bg-menta-s text-menta-t", disponible: "bg-azul-s text-azul-t", demo: "bg-ambar-s text-ambar-t", alerta: "bg-coral-s text-coral-t",
};

export default function Seguridad({ usuario, recargarUsuario }: { usuario: Usuario; recargarUsuario: () => void }) {
  const s = useApi<any>("/seguridad");
  const ses = useApi<any[]>("/auth/sesiones");
  const rec = useCallback(() => { s.recargar(); ses.recargar(); }, [s.recargar, ses.recargar]);
  useCambios(rec);
  const toast = useToast();
  const revocar = async (id: string) => {
    try { await api(`/auth/sesiones/${id}`, { metodo: "DELETE" }); toast("Sesión cerrada"); ses.recargar(); } catch (e) { toast((e as Error).message, "error"); }
  };
  if (!s.datos) return <Cargando filas={6} />;
  const grupos = s.datos.controles.reduce((acc: Record<string, any[]>, c: any) => ((acc[c.categoria] ??= []).push(c), acc), {});

  return (
    <div className="space-y-6">
      <Encabezado titulo="Seguridad" texto="Los controles que protegen el dinero, los datos y al propio agente de IA, con el estándar al que responde cada uno." />
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
        <SegundoFactor usuario={usuario} alCambiar={() => { recargarUsuario(); avisarCambio(); }} />
        <Panel titulo="Tus sesiones abiertas" subtitulo="Cierra las que no reconozcas" cuerpo="p-0">
          {!ses.datos ? <div className="p-5"><Cargando filas={2} /></div> : (
            <ul className="divide-y divide-bruma">
              {ses.datos.map((x) => (
                <li key={x.id} className="flex items-center gap-3 px-5 py-3 text-[13.5px]">
                  <MonitorSmartphone className="h-5 w-5 shrink-0 text-pizarra" />
                  <div className="min-w-0 flex-1">
                    <p className="truncate font-medium">{x.navegador || "Navegador desconocido"}</p>
                    <p className="text-xs text-pizarra">IP {x.ip} · activa {fecha(x.ultima_actividad)}{x.actual && " · esta sesión"}</p>
                  </div>
                  {!x.actual && <Boton variante="fantasma" icono={<LogOut className="h-4 w-4" />} onClick={() => revocar(x.id)}>Cerrar</Boton>}
                </li>
              ))}
            </ul>
          )}
        </Panel>
      </div>

      {Object.entries<any[]>(grupos).map(([cat, lista]) => (
        <Panel key={cat} titulo={cat} cuerpo="p-0">
          <ul className="divide-y divide-bruma">
            {lista.map((c) => (
              <li key={c.control} className="grid grid-cols-1 gap-1 px-5 py-3.5 sm:grid-cols-[minmax(0,1fr)_auto] sm:gap-4">
                <div className="min-w-0">
                  <p className="text-[14px] font-semibold">{c.control}</p>
                  <p className="text-[13px] text-noche/75">{c.detalle}</p>
                  {c.referencia && <p className="mt-0.5 text-xs text-pizarra">{c.referencia}</p>}
                </div>
                <span className={cx("self-start rounded-full px-2.5 py-0.5 text-xs font-semibold", ESTADO[c.estado] ?? ESTADO.activo)}>
                  {c.estado === "activo" ? "Activo" : c.estado === "disponible" ? "Disponible" : c.estado === "demo" ? "Modo demo" : "Revisar"}
                </span>
              </li>
            ))}
          </ul>
        </Panel>
      ))}

      <Panel titulo="Política de seguridad de contenido (CSP)" subtitulo="Solo se ejecuta código propio del servidor; nada de scripts de terceros ni iframes">
        <p className="break-words font-mono text-[12px] text-noche/80">{s.datos.csp}</p>
        <p className="mt-3 text-xs text-pizarra">Python {s.datos.versiones.python} · FastAPI {s.datos.versiones.fastapi} · SQLAlchemy {s.datos.versiones.sqlalchemy} · Kauta {s.datos.versiones.kauta} · modo {s.datos.modo}</p>
      </Panel>
    </div>
  );
}

function SegundoFactor({ usuario, alCambiar }: { usuario: Usuario; alCambiar: () => void }) {
  const [alta, setAlta] = useState<{ qr: string; secreto: string } | null>(null);
  const [codigo, setCodigo] = useState("");
  const [error, setError] = useState<string | null>(null);
  const toast = useToast();
  const iniciar = async () => {
    setError(null);
    try { setAlta(await api("/auth/mfa/iniciar", { cuerpo: {} })); } catch (e) { setError((e as Error).message); }
  };
  const confirmar = async () => {
    setError(null);
    try { await api("/auth/mfa/confirmar", { cuerpo: { codigo } }); toast("Segundo factor activo: se pedirá al entrar y al aprobar pagos"); setAlta(null); setCodigo(""); alCambiar(); }
    catch (e) { setError((e as Error).message); }
  };
  const desactivar = async () => {
    setError(null);
    try { await api("/auth/mfa/desactivar", { cuerpo: { codigo } }); toast("Segundo factor desactivado", "info"); setCodigo(""); alCambiar(); }
    catch (e) { setError((e as Error).message); }
  };
  return (
    <Panel titulo="Segundo factor (TOTP)" subtitulo="Se pide al entrar y otra vez al aprobar un pago">
      {usuario.mfa_activo ? (
        <div className="space-y-4">
          <Aviso tono="exito" titulo="Activo en tu cuenta">Para mover dinero se te pedirá un código nuevo cada vez.</Aviso>
          <div className="flex flex-wrap items-end gap-2">
            <Campo etiqueta="Código para desactivar"><input className={claseEntrada + " w-40 text-center tracking-[0.3em] num"} maxLength={6} inputMode="numeric" value={codigo} onChange={(e) => setCodigo(e.target.value.replace(/\D/g, ""))} /></Campo>
            <Boton variante="peligro" onClick={desactivar} disabled={codigo.length !== 6}>Desactivar</Boton>
          </div>
        </div>
      ) : alta ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-[180px_minmax(0,1fr)]">
          <img src={alta.qr} alt="Código QR para la app de autenticación" className="h-[180px] w-[180px] rounded-[12px] border border-bruma" />
          <div className="space-y-3">
            <p className="text-[14px]">Escanéalo con Google Authenticator, Microsoft Authenticator o 1Password. Si no puedes, escribe esta clave:</p>
            <Hash valor={alta.secreto} largo={32} />
            <Campo etiqueta="Código de 6 dígitos"><input className={claseEntrada + " w-40 text-center tracking-[0.3em] num"} maxLength={6} inputMode="numeric" value={codigo} onChange={(e) => setCodigo(e.target.value.replace(/\D/g, ""))} /></Campo>
            <Boton variante="primario" icono={<ShieldCheck className="h-4 w-4" />} onClick={confirmar} disabled={codigo.length !== 6}>Activar</Boton>
          </div>
        </div>
      ) : (
        <div className="space-y-4">
          <p className="flex gap-3 text-[14px] text-noche/85"><KeyRound className="mt-0.5 h-5 w-5 shrink-0 text-azul" />Con el segundo factor, una contraseña robada no basta para entrar ni para aprobar pagos.</p>
          <p className="flex gap-3 text-[14px] text-noche/85"><Fingerprint className="mt-0.5 h-5 w-5 shrink-0 text-azul" />La hoja de ruta cambia TOTP por passkeys (WebAuthn), que resisten el phishing.</p>
          <Boton variante="primario" onClick={iniciar}>Activar segundo factor</Boton>
        </div>
      )}
      {error && <Aviso tono="error" className="mt-4">{error}</Aviso>}
    </Panel>
  );
}
