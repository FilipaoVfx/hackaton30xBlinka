import { useEffect, useState } from "react";
import { KeyRound, LogIn, UserPlus } from "lucide-react";
import { api, type Regla, type Usuario } from "../api";
import { Aviso, Boton, Campo, claseEntrada, Logo, TiraReglas } from "../ui";

const MUESTRA: Regla[] = "cumple cumple cumple cumple cumple cumple falla cumple cumple cumple cumple cumple cumple".split(" ")
  .map((estado, i) => ({ id: `R${String(i + 1).padStart(2, "0")}`, nombre: "", efecto: "escalar", estado: estado as Regla["estado"], detalle: "" }));

export default function Login({ alEntrar }: { alEntrar: (u: Usuario) => void }) {
  const [vista, setVista] = useState<"entrar" | "crear">("entrar");
  const [correo, setCorreo] = useState("");
  const [contrasena, setContrasena] = useState("");
  const [codigo, setCodigo] = useState("");
  const [pideCodigo, setPideCodigo] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);
  const [demo, setDemo] = useState<{ contrasena: string; usuarios: any[] } | null>(null);
  useEffect(() => { api("/auth/demo").then(setDemo).catch(() => setDemo(null)); }, []);

  const entrar = async (c = correo, p = contrasena) => {
    setEnviando(true);
    setError(null);
    try {
      const r = await api<any>("/auth/login", { cuerpo: { correo: c, contrasena: p, codigo: pideCodigo ? codigo : undefined } });
      if (r.mfa_requerido) {
        setPideCodigo(true);
        setCorreo(c);
        setContrasena(p);
        return;
      }
      alEntrar(r.usuario);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setEnviando(false);
    }
  };

  return (
    <div className="grid grid-cols-1 min-h-dvh lg:grid-cols-[minmax(0,1.05fr)_minmax(0,1fr)]">
      <section className="relative flex flex-col justify-between overflow-hidden bg-noche px-6 py-8 text-white sm:px-10 lg:px-14 lg:py-12">
        <Logo claro />
        <div className="my-10 max-w-xl lg:my-0">
          <h1 className="text-[34px] font-extrabold leading-[1.08] tracking-[-0.03em] sm:text-[44px]">
            Kauta paga lo que cumple, frena lo que no y te pregunta el resto.
          </h1>
          <p className="mt-5 max-w-lg text-[16px] leading-relaxed text-[#C9D2E8]">
            Un agente de cuentas por pagar: lee facturas en cualquier formato, las revisa contra 13 reglas de la empresa y paga desde la wallet. La IA solo lee; las decisiones las toma código que se puede auditar.
          </p>
          <div className="mt-9 rounded-[16px] bg-noche-2 p-5">
            <div className="flex items-center justify-between gap-4">
              <div>
                <p className="text-[13px] text-[#AAB6D3]">F12 · Andrés Felipe Rojas · COP 4.800.000</p>
                <p className="mt-1 text-[15px] font-semibold">Pide pagar a otra cuenta: ···0093 en lugar de ···8152</p>
              </div>
              <span className="hidden rounded-md border-2 border-ambar px-2.5 py-0.5 text-sm font-extrabold uppercase tracking-[0.08em] text-ambar sm:inline">Escalar</span>
            </div>
            <TiraReglas reglas={MUESTRA} grande className="mt-4" />
            <p className="mt-3 text-[13px] text-[#AAB6D3]">12 reglas cumplen; la de la cuenta registrada (R07) no. Kauta no paga y le pregunta a una persona.</p>
          </div>
        </div>
        <p className="text-xs text-[#8D9AC0]">Hackathon 30X · Reto Blinka · todos los datos son ficticios y ningún dinero real se mueve.</p>
      </section>

      <section className="flex items-center justify-center px-6 py-10 sm:px-10">
        <div className="w-full max-w-[400px]">
          <div className="mb-6 grid grid-cols-2 gap-1 rounded-[12px] bg-niebla p-1" role="tablist" aria-label="Acceso">
            {([["entrar", "Iniciar sesión"], ["crear", "Crear cuenta"]] as const).map(([v, t]) => (
              <button key={v} role="tab" aria-selected={vista === v} type="button" onClick={() => { setVista(v); setError(null); }}
                className={"rounded-[9px] px-3 py-2 text-[14px] font-semibold transition-colors " +
                  (vista === v ? "bg-white text-noche shadow-sm" : "text-pizarra hover:text-noche")}>{t}</button>
            ))}
          </div>
          {vista === "crear" ? <Registro alVolver={() => setVista("entrar")} /> : <>
          <h2 className="text-[24px] font-extrabold tracking-[-0.02em]">Iniciar sesión</h2>
          <p className="mt-1 text-[14px] text-pizarra">Brisamar Labs Inc. · cuentas por pagar</p>
          <form className="mt-7 space-y-4" onSubmit={(e) => { e.preventDefault(); entrar(); }}>
            <Campo etiqueta="Correo">
              <input className={claseEntrada} type="email" autoComplete="username" value={correo} onChange={(e) => setCorreo(e.target.value)} required />
            </Campo>
            <Campo etiqueta="Contraseña">
              <input className={claseEntrada} type="password" autoComplete="current-password" value={contrasena} onChange={(e) => setContrasena(e.target.value)} required />
            </Campo>
            {pideCodigo && (
              <Campo etiqueta="Código de verificación" ayuda="Los 6 dígitos de su app de autenticación.">
                <input className={claseEntrada + " text-center text-[18px] tracking-[0.4em] num"} inputMode="numeric" autoComplete="one-time-code" maxLength={6} value={codigo} onChange={(e) => setCodigo(e.target.value.replace(/\D/g, ""))} autoFocus />
              </Campo>
            )}
            {error && <Aviso tono="error">{error}</Aviso>}
            <Boton variante="primario" type="submit" cargando={enviando} icono={<LogIn className="h-4 w-4" />} className="w-full">Entrar</Boton>
          </form>

          {demo && (
            <div className="mt-9">
              <div className="flex items-baseline justify-between gap-3">
                <h3 className="text-[15px] font-bold">Entrar con una persona de prueba</h3>
              </div>
              <p className="mt-1 text-[13px] text-pizarra">
                Contraseña de la demo: <span className="inline-flex items-center gap-1 rounded bg-niebla px-1.5 py-0.5 font-mono text-[12px] text-noche"><KeyRound className="h-3 w-3" />{demo.contrasena}</span>
              </p>
              <div className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-2">
                {demo.usuarios.map((u) => (
                  <button key={u.correo} type="button" onClick={() => entrar(u.correo, demo.contrasena)} disabled={enviando}
                    className="rounded-[12px] border border-bruma bg-white p-3 text-left transition-colors hover:border-azul/50 hover:bg-azul-s/40">
                    <span className="block text-[14px] font-semibold">{u.nombre}</span>
                    <span className="block text-xs text-pizarra">{u.cargo}</span>
                  </button>
                ))}
              </div>
            </div>
          )}
          </>}
        </div>
      </section>
    </div>
  );
}

/** Alta de una persona con el código de invitación que entrega administración. El rol viene en la invitación. */
function Registro({ alVolver }: { alVolver: () => void }) {
  const [correo, setCorreo] = useState("");
  const [codigo, setCodigo] = useState("");
  const [clave, setClave] = useState("");
  const [clave2, setClave2] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [listo, setListo] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);
  const corta = clave.length > 0 && clave.length < 15;
  const distinta = clave2.length > 0 && clave !== clave2;

  const crear = async () => {
    setEnviando(true);
    setError(null);
    try {
      const r = await api<any>("/personas/registro", { cuerpo: { correo, codigo: codigo.trim().toUpperCase(), contrasena: clave } });
      setListo(`${r.nombre}: cuenta creada con el rol ${r.rol}. Ya puede iniciar sesión.`);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setEnviando(false);
    }
  };

  if (listo) {
    return (
      <div>
        <h2 className="text-[24px] font-extrabold tracking-[-0.02em]">Cuenta creada</h2>
        <Aviso tono="exito" className="mt-4">{listo}</Aviso>
        <Boton variante="primario" className="mt-5 w-full" onClick={alVolver}>Iniciar sesión</Boton>
      </div>
    );
  }
  return (
    <div>
      <h2 className="text-[24px] font-extrabold tracking-[-0.02em]">Crear cuenta</h2>
      <p className="mt-1 text-[14px] leading-relaxed text-pizarra">
        Las cuentas se crean por invitación: administración le entrega un código y ese código ya trae su rol.
      </p>
      <form className="mt-7 space-y-4" onSubmit={(e) => { e.preventDefault(); crear(); }}>
        <Campo etiqueta="Correo de la empresa">
          <input className={claseEntrada} type="email" autoComplete="username" value={correo} onChange={(e) => setCorreo(e.target.value)} required />
        </Campo>
        <Campo etiqueta="Código de invitación" ayuda="Tiene la forma KAUT-XXXX-XXXX y sirve una sola vez.">
          <input className={claseEntrada + " font-mono uppercase tracking-[0.12em]"} value={codigo} maxLength={20}
            onChange={(e) => setCodigo(e.target.value.toUpperCase())} placeholder="KAUT-XXXX-XXXX" required />
        </Campo>
        <Campo etiqueta="Contraseña" ayuda="Mínimo 15 caracteres. Una frase propia es más segura y más fácil de recordar.">
          <input className={claseEntrada} type="password" autoComplete="new-password" value={clave} onChange={(e) => setClave(e.target.value)} required />
        </Campo>
        <Campo etiqueta="Repetir contraseña">
          <input className={claseEntrada} type="password" autoComplete="new-password" value={clave2} onChange={(e) => setClave2(e.target.value)} required />
        </Campo>
        {corta && <p className="text-[13px] text-coral-t">Le faltan {15 - clave.length} caracteres.</p>}
        {distinta && <p className="text-[13px] text-coral-t">Las dos contraseñas no coinciden.</p>}
        {error && <Aviso tono="error">{error}</Aviso>}
        <Boton variante="primario" type="submit" cargando={enviando} disabled={corta || distinta || !clave}
          icono={<UserPlus className="h-4 w-4" />} className="w-full">Crear mi cuenta</Boton>
      </form>
      <p className="mt-5 text-[13px] leading-relaxed text-pizarra">
        ¿No tiene código? Pídalo a quien administra Kauta en su empresa. Nadie puede darse de alta por su cuenta ni elegir su propio rol.
      </p>
    </div>
  );
}
