import { useCallback, useEffect, useState, type ReactNode } from "react";
import {
  Building2, Ellipsis, FlaskConical, LayoutDashboard, LogOut, MessageCircleQuestion, ReceiptText, ScrollText,
  ShieldCheck, SlidersHorizontal, UserRound, Users, Wallet,
} from "lucide-react";
import { alPerderSesion, api, avisarCambio, fijarCsrf, PERIODO, puede, useCambios, useRuta, type Usuario } from "./api";
import { Aviso, Cargando, cx, Logo, Modal, useToast } from "./ui";
import Login from "./pages/Login";
import Resumen from "./pages/Resumen";
import Facturas from "./pages/Facturas";
import Detalle from "./pages/Detalle";
import Pregunta from "./pages/Pregunta";
import Simulador from "./pages/Simulador";
import WalletPagina from "./pages/Wallet";
import Proveedores from "./pages/Proveedores";
import Reglas from "./pages/Reglas";
import Auditoria from "./pages/Auditoria";
import Seguridad from "./pages/Seguridad";
import Personas from "./pages/Personas";


const NAV = [
  { ruta: "resumen", nombre: "Resumen", icono: LayoutDashboard, movil: true },
  { ruta: "facturas", nombre: "Facturas", icono: ReceiptText, movil: true },
  { ruta: "pregunta", nombre: "Kauta pregunta", corto: "Pregunta", icono: MessageCircleQuestion, movil: true },
  { ruta: "simulador", nombre: "Simulador de pagos", corto: "Simulador", icono: FlaskConical, movil: true },
  { ruta: "wallet", nombre: "Wallet y pagos", icono: Wallet },
  { ruta: "proveedores", nombre: "Proveedores", icono: Building2 },
  { ruta: "reglas", nombre: "Reglas", icono: SlidersHorizontal },
  { ruta: "auditoria", nombre: "Auditoría", icono: ScrollText },
  { ruta: "seguridad", nombre: "Seguridad", icono: ShieldCheck },
  { ruta: "personas", nombre: "Personas y roles", corto: "Personas", icono: Users, permiso: "usuarios.ver" },
];

export default function App() {
  const [usuario, setUsuario] = useState<Usuario | null>(null);
  const [modo, setModo] = useState("demo");
  const [listo, setListo] = useState(false);
  const cargarYo = useCallback(async () => {
    try {
      const r = await api<{ usuario: Usuario; modo: string }>("/auth/yo");
      fijarCsrf(r.usuario.csrf);
      setUsuario(r.usuario);
      setModo(r.modo);
    } catch {
      setUsuario(null);
    } finally {
      setListo(true);
    }
  }, []);
  useEffect(() => {
    alPerderSesion(() => setUsuario(null));
    cargarYo();
  }, [cargarYo]);

  if (!listo) return <div className="mx-auto max-w-md p-10"><Cargando filas={3} /></div>;
  if (!usuario) return <Login alEntrar={(u) => { fijarCsrf(u.csrf); setUsuario(u); avisarCambio(); }} />;
  return <Marco usuario={usuario} modo={modo} setUsuario={setUsuario} recargarUsuario={cargarYo} />;
}

function Marco({ usuario, modo, setUsuario, recargarUsuario }: { usuario: Usuario; modo: string; setUsuario: (u: Usuario | null) => void; recargarUsuario: () => void }) {
  const [partes] = useRuta();
  const visibles = NAV.filter((n) => !n.permiso || puede(usuario, n.permiso));
  const [pendientes, setPendientes] = useState(0);
  const [periodo, setPeriodo] = useState("2026-10");
  const [mas, setMas] = useState(false);
  const [personas, setPersonas] = useState(false);
  const toast = useToast();
  const contar = useCallback(() => {
    api<any[]>("/aprobaciones").then((l) => setPendientes(l.length)).catch(() => {});
    api<any>("/reglas").then((r) => setPeriodo(r.vigente.periodo_actual)).catch(() => {});
  }, []);
  useEffect(contar, [contar, partes.join("/")]);
  useCambios(contar);

  const salir = async () => {
    await api("/auth/logout", { metodo: "POST", cuerpo: {} }).catch(() => {});
    fijarCsrf(null);
    setUsuario(null);
  };
  const pagina = partes[0];
  let contenido: ReactNode;
  switch (pagina) {
    case "facturas": contenido = partes[1] ? <Detalle id={partes[1]} usuario={usuario} /> : <Facturas usuario={usuario} />; break;
    case "pregunta": contenido = <Pregunta usuario={usuario} />; break;
    case "simulador": contenido = <Simulador usuario={usuario} />; break;
    case "wallet": contenido = <WalletPagina usuario={usuario} />; break;
    case "proveedores": contenido = <Proveedores usuario={usuario} />; break;
    case "reglas": contenido = <Reglas usuario={usuario} />; break;
    case "auditoria": contenido = <Auditoria usuario={usuario} />; break;
    case "seguridad": contenido = <Seguridad usuario={usuario} recargarUsuario={recargarUsuario} />; break;
    case "personas": contenido = <Personas usuario={usuario} />; break;
    default: contenido = <Resumen usuario={usuario} />;
  }

  return (
    <div className="min-h-dvh lg:pl-[248px]">
      {/* Barra lateral (escritorio y tableta horizontal) */}
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-[248px] flex-col bg-noche text-white lg:flex">
        <div className="px-5 pt-6 pb-5"><a href="#/resumen" aria-label="Kauta, inicio"><Logo claro /></a></div>
        <nav className="flex-1 space-y-0.5 overflow-y-auto px-3" aria-label="Secciones">
          {visibles.map((n) => {
            const activo = pagina === n.ruta || (!pagina && n.ruta === "resumen");
            return (
              <a key={n.ruta} href={`#/${n.ruta}`} aria-current={activo ? "page" : undefined}
                className={cx("flex items-center gap-3 rounded-[10px] px-3 py-2.5 text-[14px] font-medium transition-colors",
                  activo ? "bg-white text-noche" : "text-[#C9D2E8] hover:bg-noche-2 hover:text-white")}>
                <n.icono className="h-[18px] w-[18px]" strokeWidth={2} />
                <span className="flex-1">{n.nombre}</span>
                {n.ruta === "pregunta" && pendientes > 0 && (
                  <span className={cx("rounded-full px-2 py-0.5 text-[11px] font-bold num", activo ? "bg-ambar text-noche" : "bg-ambar text-noche")}>{pendientes}</span>
                )}
              </a>
            );
          })}
        </nav>
        <div className="m-3 rounded-[12px] bg-noche-2 p-3">
          <p className="truncate text-[13px] font-semibold">{usuario.nombre}</p>
          <p className="truncate text-xs text-[#AAB6D3]">{usuario.cargo} · {usuario.rol_nombre}</p>
          <div className="mt-3 flex gap-2">
            {modo === "demo" && (
              <button onClick={() => setPersonas(true)} className="flex flex-1 items-center justify-center gap-1.5 rounded-lg bg-noche-3 px-2 py-1.5 text-xs font-semibold hover:bg-[#28407f]">
                <Users className="h-3.5 w-3.5" /> Cambiar de persona
              </button>
            )}
            <button onClick={salir} className="rounded-lg bg-noche-3 px-2.5 py-1.5 hover:bg-[#28407f]" aria-label="Cerrar sesión" title="Cerrar sesión"><LogOut className="h-3.5 w-3.5" /></button>
          </div>
        </div>
      </aside>

      {/* Barra superior */}
      <header className="sticky top-0 z-20 border-b border-bruma bg-white/90 backdrop-blur supports-[backdrop-filter]:bg-white/75">
        <div className="mx-auto flex h-14 max-w-[1240px] items-center gap-3 px-4 sm:px-6">
          <a href="#/resumen" className="lg:hidden" aria-label="Inicio"><Logo /></a>
          <div className="hidden min-w-0 items-center gap-2 text-[13px] sm:flex">
            <span className="font-semibold">Brisamar Labs Inc.</span>
            <span className="text-bruma">/</span>
            <span className="text-pizarra">Periodo de {PERIODO(periodo)}</span>
          </div>
          <div className="ml-auto flex items-center gap-2">
            {modo === "demo" && <span className="hidden rounded-full bg-ambar-s px-2.5 py-1 text-xs font-semibold text-ambar-t sm:inline">Demo · datos ficticios</span>}
            <button onClick={() => (modo === "demo" ? setPersonas(true) : null)} className="flex items-center gap-2 rounded-full bg-niebla py-1 pl-1 pr-3 text-[13px] font-semibold lg:hidden">
              <span className="flex h-7 w-7 items-center justify-center rounded-full bg-noche text-[11px] font-bold text-white">{usuario.nombre.split(" ").map((p) => p[0]).slice(0, 2).join("")}</span>
              <span className="max-w-[110px] truncate">{usuario.nombre.split(" ")[0]}</span>
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-[1240px] px-4 pb-28 pt-6 sm:px-6 lg:pb-12">{contenido}</main>

      {/* Navegación inferior (celular y tableta vertical) */}
      <nav className="fixed inset-x-0 bottom-0 z-30 border-t border-bruma bg-white pb-[env(safe-area-inset-bottom)] lg:hidden" aria-label="Secciones">
        <div className="mx-auto grid max-w-xl grid-cols-5">
          {visibles.filter((n) => n.movil).map((n) => {
            const activo = pagina === n.ruta || (!pagina && n.ruta === "resumen");
            return (
              <a key={n.ruta} href={`#/${n.ruta}`} aria-current={activo ? "page" : undefined}
                className={cx("relative flex flex-col items-center gap-1 py-2.5 text-[11px] font-semibold", activo ? "text-azul" : "text-pizarra")}>
                <n.icono className="h-5 w-5" />
                {n.corto ?? n.nombre}
                {n.ruta === "pregunta" && pendientes > 0 && <span className="absolute right-[22%] top-1.5 rounded-full bg-ambar px-1.5 text-[10px] font-bold text-noche num">{pendientes}</span>}
              </a>
            );
          })}
          <button onClick={() => setMas(true)} className={cx("flex flex-col items-center gap-1 py-2.5 text-[11px] font-semibold", visibles.some((n) => !n.movil && n.ruta === pagina) ? "text-azul" : "text-pizarra")}>
            <Ellipsis className="h-5 w-5" /> Más
          </button>
        </div>
      </nav>

      <Modal abierto={mas} titulo="Más secciones" onCerrar={() => setMas(false)}>
        <div className="grid grid-cols-2 gap-2">
          {visibles.filter((n) => !n.movil).map((n) => (
            <a key={n.ruta} href={`#/${n.ruta}`} onClick={() => setMas(false)} className="flex items-center gap-2.5 rounded-[12px] border border-bruma p-3.5 text-[14px] font-semibold hover:bg-niebla">
              <n.icono className="h-5 w-5 text-azul" /> {n.nombre}
            </a>
          ))}
          <button onClick={salir} className="col-span-2 flex items-center justify-center gap-2 rounded-[12px] border border-bruma p-3 text-[14px] font-semibold text-coral-t">
            <LogOut className="h-4 w-4" /> Cerrar sesión
          </button>
        </div>
      </Modal>
      <CambiarPersona abierto={personas} onCerrar={() => setPersonas(false)} actual={usuario}
        alCambiar={(u) => { fijarCsrf(u.csrf); setUsuario(u); setPersonas(false); avisarCambio(); toast(`Ahora eres ${u.nombre} (${u.rol_nombre})`, "info"); }} />
    </div>
  );
}

export function CambiarPersona({ abierto, onCerrar, actual, alCambiar }: { abierto: boolean; onCerrar: () => void; actual: Usuario; alCambiar: (u: Usuario) => void }) {
  const [demo, setDemo] = useState<{ contrasena: string; usuarios: any[] } | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { if (abierto) api("/auth/demo").then(setDemo).catch((e) => setError(e.message)); }, [abierto]);
  const entrar = async (correo: string) => {
    try {
      await api("/auth/logout", { metodo: "POST", cuerpo: {} }).catch(() => {});
      fijarCsrf(null);
      const r = await api<{ usuario: Usuario }>("/auth/login", { cuerpo: { correo, contrasena: demo!.contrasena } });
      alCambiar(r.usuario);
    } catch (e) {
      setError((e as Error).message);
    }
  };
  return (
    <Modal abierto={abierto} titulo="Entrar como otra persona" onCerrar={onCerrar}>
      <p className="mb-4 text-[14px] text-pizarra">Cada persona tiene un rol distinto. Para la doble aprobación, aprueba con una y luego con otra: Kauta no deja que la misma persona firme dos veces.</p>
      {error && <Aviso tono="error" className="mb-3">{error}</Aviso>}
      <div className="space-y-2">
        {demo?.usuarios.map((u) => (
          <button key={u.correo} disabled={u.correo === actual.correo} onClick={() => entrar(u.correo)}
            className="flex w-full items-center gap-3 rounded-[12px] border border-bruma p-3 text-left hover:border-azul/40 hover:bg-azul-s/40 disabled:opacity-50">
            <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-noche text-xs font-bold text-white"><UserRound className="h-4 w-4" /></span>
            <span className="min-w-0 flex-1">
              <span className="block text-[14px] font-semibold">{u.nombre} {u.correo === actual.correo && <span className="text-pizarra">(actual)</span>}</span>
              <span className="block truncate text-xs text-pizarra">{u.cargo} · {u.rol_nombre}</span>
            </span>
          </button>
        ))}
      </div>
    </Modal>
  );
}
