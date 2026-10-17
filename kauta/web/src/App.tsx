import { useCallback, useEffect, useState, type ReactNode } from "react";
import { Building2, ChevronDown, Ellipsis, FlaskConical, LayoutDashboard, MessageCircleQuestion, ReceiptText, ScrollText, ShieldCheck, SlidersHorizontal, Users, Wallet, ChartNoAxesCombined, ArrowRight, Search, Command } from "lucide-react";
import { alPerderSesion, alRenovarSesion, api, avisarCambio, elegirPersona, fijarCsrf, guardarPersona, ultimaPersona, PERIODO, useCambios, useRuta, type Usuario } from "./api";
import { Aviso, Boton, Cargando, cx, EstadoCarga, Logo, Modal } from "./ui";
import PaletaComandos from "./components/PaletaComandos";
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
import Rendimiento from "./pages/Rendimiento";

const NAV = [
  { ruta: "resumen", nombre: "Resumen", icono: LayoutDashboard, grupo: "Operar", movil: true },
  { ruta: "facturas", nombre: "Facturas", icono: ReceiptText, grupo: "Operar", movil: true },
  { ruta: "pregunta", nombre: "Kauta pregunta", corto: "Pregunta", icono: MessageCircleQuestion, grupo: "Operar", movil: true },
  { ruta: "simulador", nombre: "Simulador de pagos", icono: FlaskConical, grupo: "Operar" },
  { ruta: "wallet", nombre: "Wallet y pagos", icono: Wallet, grupo: "Dinero" },
  { ruta: "rendimiento", nombre: "Rendimiento y costos", corto: "Costos", icono: ChartNoAxesCombined, grupo: "Dinero", movil: true },
  { ruta: "proveedores", nombre: "Proveedores", icono: Building2, grupo: "Control" },
  { ruta: "reglas", nombre: "Reglas", icono: SlidersHorizontal, grupo: "Control" },
  { ruta: "auditoria", nombre: "Auditoría", icono: ScrollText, grupo: "Control" },
  { ruta: "seguridad", nombre: "Seguridad", icono: ShieldCheck, grupo: "Control" },
];

export default function App() {
  const [usuario, setUsuario] = useState<Usuario | null>(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const cargar = useCallback(async () => {
    setCargando(true); setError(null);
    try {
      try {
        const r = await api<{ usuario: Usuario }>("/auth/yo");
        fijarCsrf(r.usuario.csrf); guardarPersona(r.usuario.correo); setUsuario(r.usuario);
      } catch (e: any) {
        if (e.estado !== 401) throw e;
        setUsuario(await elegirPersona(ultimaPersona()));
      }
    } catch (e) { setError((e as Error).message); }
    finally { setCargando(false); }
  }, []);
  useEffect(() => {
    alPerderSesion(() => { setError("No se pudo recuperar tu sesión. Vuelve a intentar."); });
    alRenovarSesion(setUsuario);
    cargar();
  }, [cargar]);
  if (error || !usuario) return <div className="mx-auto max-w-lg px-6 py-20"><Logo /><div className="mt-10"><EstadoCarga cargando={cargando} datos={usuario} error={error} reintentar={cargar} /></div></div>;
  return <Marco usuario={usuario} setUsuario={setUsuario} />;
}

function Marco({ usuario, setUsuario }: { usuario: Usuario; setUsuario: (u: Usuario) => void }) {
  const [partes] = useRuta();
  const [pendientes, setPendientes] = useState(0);
  const [periodo, setPeriodo] = useState("2026-10");
  const [mas, setMas] = useState(false);
  const [buscar, setBuscar] = useState(false);
  useEffect(() => {
    const atajo = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") { e.preventDefault(); setBuscar(b => !b); }
    };
    document.addEventListener("keydown", atajo);
    return () => document.removeEventListener("keydown", atajo);
  }, []);
  const [personas, setPersonas] = useState(false);
  const contar = useCallback(() => {
    api<any[]>("/aprobaciones").then((l) => setPendientes(l.filter((f) => !f.ya_aprobe && !f.cargue_yo).length)).catch(() => {});
    api<any>("/reglas").then((r) => setPeriodo(r.vigente.periodo_actual)).catch(() => {});
  }, []);
  useEffect(contar, [contar, partes.join("/"), usuario.correo]);
  useCambios(contar);
  const pagina = partes[0];
  let contenido: ReactNode;
  switch (pagina) {
    case "facturas": contenido = partes[1] ? <Detalle key={partes[1]} id={partes[1]} usuario={usuario} /> : <Facturas usuario={usuario} />; break;
    case "pregunta": contenido = <Pregunta usuario={usuario} />; break;
    case "simulador": contenido = <Simulador usuario={usuario} />; break;
    case "wallet": contenido = <WalletPagina usuario={usuario} />; break;
    case "rendimiento": contenido = <Rendimiento />; break;
    case "proveedores": contenido = <Proveedores usuario={usuario} />; break;
    case "reglas": contenido = <Reglas usuario={usuario} />; break;
    case "auditoria": contenido = <Auditoria usuario={usuario} />; break;
    case "seguridad": contenido = <Seguridad />; break;
    default: contenido = <Resumen usuario={usuario} />;
  }
  return <div className="kauta-app min-h-dvh lg:pl-[232px]">
    <a href="#contenido" className="sr-only focus:not-sr-only focus:fixed focus:z-50 focus:bg-white focus:p-4">Saltar al contenido</a>
    <aside className="kauta-sidebar fixed inset-y-0 left-0 z-30 hidden w-[232px] flex-col text-white lg:flex">
      <div className="sidebar-brand px-6 pb-7 pt-8"><a href="#/resumen" aria-label="Kauta, inicio"><Logo claro /></a><p className="mt-3 text-xs text-[#aab6d3]">Autonomía, pero cauta.</p></div>
      <a className="sidebar-empresa" href="#/resumen"><span className="empresa-avatar">K</span><span><strong>Kauta</strong><small>Espacio de demostración</small></span></a>
      <nav className="sidebar-nav flex-1 px-3" aria-label="Secciones">
        {["Operar", "Dinero", "Control"].map((grupo) => <div className="sidebar-grupo mb-6" key={grupo}>
          <p className="mb-2 px-3 text-[10px] font-semibold uppercase tracking-[0.16em] text-[#aab6d3]">{grupo}</p>
          {NAV.filter((n) => n.grupo === grupo).map((n) => <a key={n.ruta} href={`#/${n.ruta}`} aria-current={pagina === n.ruta ? "page" : undefined}
            className={cx("kauta-nav-item", pagina === n.ruta && "activo")}>
            <n.icono className="h-[18px] w-[18px] shrink-0" strokeWidth={1.7} /><span className="flex-1">{n.nombre}</span>
            {n.ruta === "pregunta" && pendientes > 0 && <span className="rounded-md bg-ambar px-1.5 py-0.5 text-[10px] font-bold text-noche num">{pendientes}</span>}
          </a>)}
        </div>)}
      </nav>
      <div className="sidebar-persona border-t border-white/10 p-4"><p className="px-2 text-xs text-[#aab6d3]">Demo sin autenticación</p><button onClick={() => setPersonas(true)} className="mt-2 flex min-h-14 w-full items-center gap-3 rounded-xl px-2 text-left hover:bg-white/10" aria-label="Cambiar de persona">
        <span className="flex h-9 w-9 items-center justify-center rounded-full bg-white/10 text-xs font-bold">{usuario.rol.toUpperCase()}</span>
        <span className="min-w-0 flex-1"><span className="block truncate text-[13px] font-semibold">{usuario.nombre}</span><span className="block text-xs text-[#aab6d3]">Cambiar persona</span></span><ChevronDown className="h-4 w-4" />
      </button></div>
    </aside>
    <header className="kauta-topbar border-b border-bruma bg-white">
      <div className="mx-auto flex min-h-[72px] max-w-[1280px] items-center gap-3 px-5 sm:px-9">
        <a href="#/resumen" className="lg:hidden" aria-label="Inicio"><Logo /></a>
        <div className="hidden text-[13px] sm:block"><span className="font-semibold">Kauta</span><span className="mx-3 text-bruma">/</span><span className="text-pizarra">{NAV.find(n => n.ruta === pagina)?.nombre ?? "Resumen"}</span></div>
        <div className="ml-auto flex items-center gap-3"><button className="abrir-comandos" onClick={() => setBuscar(true)} aria-label="Buscar en Kauta"><Search size={16} /><span>Buscar</span><kbd><Command size={11} />K</kbd></button><span className="hidden items-center gap-2 text-xs text-pizarra sm:flex"><span className="h-1.5 w-1.5 rounded-full bg-menta" />Demo · sin dinero real</span>
          <button onClick={() => setPersonas(true)} className="flex min-h-11 items-center gap-2 rounded-lg border border-bruma px-3 text-[13px] font-semibold" aria-label="Elegir persona"><span className="text-pizarra">Vista</span> {usuario.rol_nombre}<ChevronDown className="h-3.5 w-3.5" /></button>
        </div>
      </div>
    </header>
    <main id="contenido" key={usuario.correo} className="kauta-contenido mx-auto max-w-[1280px] px-5 pb-28 pt-8 sm:px-9 lg:pb-12"><div className="contexto-periodo"><span><span className="contexto-punto" />Demo · sin dinero real</span><span>{PERIODO(periodo)}</span></div>{contenido}</main>
    <footer className="mx-auto hidden max-w-[1280px] items-center justify-between border-t border-bruma px-9 py-5 text-xs text-pizarra lg:flex"><span>Kauta · La IA lee, el código decide.</span><span>Datos y costos simulados · Hackathon 30X</span></footer>
    <nav className="fixed inset-x-0 bottom-0 z-30 border-t border-bruma bg-white pb-[env(safe-area-inset-bottom)] lg:hidden" aria-label="Navegación móvil"><div className="grid grid-cols-5">
      {NAV.filter((n) => n.movil).map((n) => <a key={n.ruta} href={`#/${n.ruta}`} aria-current={pagina === n.ruta ? "page" : undefined} className={cx("flex min-h-16 flex-col items-center justify-center gap-1 text-[10px] font-semibold", pagina === n.ruta ? "text-azul" : "text-pizarra")}><n.icono className="h-5 w-5" />{n.corto ?? n.nombre}</a>)}
      <button onClick={() => setMas(true)} className="flex min-h-16 flex-col items-center justify-center gap-1 text-[10px] font-semibold text-pizarra"><Ellipsis className="h-5 w-5" />Más</button>
    </div></nav>
    <Modal abierto={mas} titulo="Más secciones" onCerrar={() => setMas(false)}><div className="space-y-2">{NAV.filter((n) => !n.movil).map((n) => <a key={n.ruta} href={`#/${n.ruta}`} onClick={() => setMas(false)} className="flex min-h-12 items-center gap-3 rounded-lg border border-bruma px-4 font-semibold"><n.icono className="h-4 w-4 text-pizarra" />{n.nombre}<ArrowRight className="ml-auto h-4 w-4" /></a>)}</div></Modal>
    <PaletaComandos abierto={buscar} cerrar={() => setBuscar(false)} secciones={NAV} />
    <CambiarPersona abierto={personas} onCerrar={() => setPersonas(false)} actual={usuario} alCambiar={(u) => { setUsuario(u); setPersonas(false); avisarCambio(); }} />
  </div>;
}

export function CambiarPersona({ abierto, onCerrar, actual, alCambiar }: { abierto: boolean; onCerrar: () => void; actual: Usuario; alCambiar: (u: Usuario) => void }) {
  const [lista, setLista] = useState<any[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [ocupado, setOcupado] = useState(false);
  const cargar = useCallback(() => { setError(null); api<any>("/auth/demo").then((r) => setLista(r.usuarios)).catch((e) => setError(e.message)); }, []);
  useEffect(() => { if (abierto) cargar(); }, [abierto, cargar]);
  const entrar = async (correo: string) => {
    setOcupado(true); setError(null);
    try { alCambiar(await elegirPersona(correo)); } catch (e) { setError((e as Error).message); } finally { setOcupado(false); }
  };
  return <Modal abierto={abierto} titulo="Elige desde dónde mirar" onCerrar={onCerrar}>
    <p className="mb-5 text-[14px] text-pizarra">Tres personas, los mismos números. Esta demo no autentica identidad: permite explorar los permisos de cada rol.</p>
    {error && <div className="mb-4"><Aviso tono="error">{error}</Aviso><Boton className="mt-3" onClick={cargar}>Reintentar</Boton></div>}
    {!lista && !error && <Cargando filas={3} />}
    <div className="space-y-3">{lista?.map((u) => <button key={u.correo} disabled={ocupado || u.correo === actual.correo} onClick={() => entrar(u.correo)} className={cx("flex min-h-24 w-full items-center gap-4 rounded-xl border p-4 text-left hover:border-azul disabled:cursor-default", actual.correo === u.correo ? "border-azul bg-azul-s/40" : "border-bruma")}>
      <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-noche text-xs font-bold text-white">{u.rol_nombre}</span><span><span className="block text-[15px] font-bold">{u.nombre}</span><span className="mt-1 block text-[13px] text-pizarra">{u.rol === "cfo" ? "Dinero, firmas y políticas" : u.rol === "ceo" ? "Resultados y segunda firma" : "Eficiencia y operación del agente"}{actual.correo === u.correo && " · actual"}</span></span>
    </button>)}</div>
  </Modal>;
}
