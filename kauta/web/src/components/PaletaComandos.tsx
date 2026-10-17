import { useEffect, useMemo, useRef, useState } from "react";
import { ArrowUpRight, CornerDownLeft, Search, X, type LucideIcon } from "lucide-react";
import { api, dinero, type FacturaResumen } from "../api";

type Seccion = { ruta: string; nombre: string; icono: LucideIcon; grupo: string };
export default function PaletaComandos({ abierto, cerrar, secciones }: { abierto: boolean; cerrar: () => void; secciones: Seccion[] }) {
  const dialogo = useRef<HTMLDialogElement>(null);
  const [q, setQ] = useState("");
  const [indice, setIndice] = useState(0);
  const [facturas, setFacturas] = useState<FacturaResumen[]>([]);
  const [error, setError] = useState(false);
  const [cargando, setCargando] = useState(false);
  useEffect(() => {
    if (!abierto) { dialogo.current?.close(); return; }
    setQ(""); setIndice(0); setError(false); setFacturas([]); setCargando(true);
    dialogo.current?.showModal();
    let vigente = true;
    api<FacturaResumen[]>("/facturas").then(r => { if (vigente) setFacturas(r); }).catch(() => { if (vigente) setError(true); }).finally(() => { if (vigente) setCargando(false); });
    return () => { vigente = false; };
  }, [abierto]);
  const resultados = useMemo(() => {
    const normalizar = (s: string) => s.toLocaleLowerCase("es").normalize("NFD").replace(/[\u0300-\u036f]/g, "");
    const consulta = normalizar(q.trim());
    const paginas = secciones.filter(s => normalizar(`${s.nombre} ${s.grupo}`).includes(consulta)).map(s => ({ ruta: s.ruta, nombre: s.nombre, detalle: s.grupo, icono: s.icono }));
    const documentos = consulta ? facturas.filter(f => normalizar(`${f.id} ${f.beneficiario} ${f.numero}`).includes(consulta)).slice(0, 8).map(f => ({ ruta: `facturas/${f.id}`, nombre: `${f.id} · ${f.beneficiario}`, detalle: dinero(f.monto_usd), icono: ArrowUpRight })) : [];
    return [...paginas, ...documentos];
  }, [q, facturas, secciones]);
  const activo = Math.min(indice, Math.max(0, resultados.length - 1));
  useEffect(() => { dialogo.current?.querySelector(`#comando-${activo}`)?.scrollIntoView({ block: "nearest" }); }, [activo]);
  const navegar = (ruta: string) => { location.hash = `#/${ruta}`; cerrar(); };
  return <dialog ref={dialogo} className="paleta-comandos" aria-labelledby="paleta-titulo" onCancel={cerrar} onClick={e => { if (e.target === e.currentTarget) { const b = e.currentTarget.getBoundingClientRect(); if (e.clientX < b.left || e.clientX > b.right || e.clientY < b.top || e.clientY > b.bottom) cerrar(); } }}>
    <h2 id="paleta-titulo" className="sr-only">Buscar en Kauta</h2>
    <div className="paleta-busqueda"><Search size={21} /><input autoFocus role="combobox" aria-label="Buscar secciones o facturas" aria-expanded="true" aria-controls="comandos" aria-activedescendant={resultados.length ? `comando-${activo}` : undefined} placeholder="¿A dónde quieres ir?" value={q} onChange={e => { setQ(e.target.value); setIndice(0); }} onKeyDown={e => {
      if (e.key === "ArrowDown") { e.preventDefault(); setIndice((activo + 1) % Math.max(1, resultados.length)); }
      if (e.key === "ArrowUp") { e.preventDefault(); setIndice((activo - 1 + resultados.length) % Math.max(1, resultados.length)); }
      if (e.key === "Enter" && resultados[activo]) { e.preventDefault(); navegar(resultados[activo].ruta); }
    }} /><button onClick={cerrar} aria-label="Cerrar búsqueda"><X size={18} /></button></div>
    <div className="paleta-resultados" id="comandos" role="listbox" aria-label="Resultados">
      {resultados.map((r, i) => <div key={r.ruta} id={`comando-${i}`} role="option" aria-selected={activo === i} className="paleta-opcion" onMouseMove={() => setIndice(i)} onClick={() => navegar(r.ruta)}><r.icono size={18} /><span>{r.nombre}<small>{r.detalle}</small></span><CornerDownLeft size={15} /></div>)}
      {!resultados.length && <p className="paleta-sin-resultados" role="status">{cargando ? "Buscando facturas…" : error ? "No pudimos consultar las facturas. Cierra y vuelve a abrir la búsqueda para reintentar." : <>No encontramos «{q}». Prueba con un proveedor, una factura o una sección.</>}</p>}
    </div>
    <div className="paleta-pie"><span>{error ? "No pudimos consultar facturas. Puedes navegar por secciones." : "Secciones y facturas, en un solo lugar."}</span><kbd>Esc</kbd><span>cerrar</span></div>
  </dialog>;
}
