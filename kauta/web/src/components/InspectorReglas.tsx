import { useState } from "react";
import { ArrowUpRight, Check, Minus, X } from "lucide-react";
import { dinero, useApi, type FacturaResumen } from "../api";
import { cx, resumenReglas } from "../ui";

const EJEMPLOS = ["F01", "F07", "F12", "F10"];
const RESULTADO = { cumple: "Cumple", falla: "Requiere atención", no_aplica: "No aplica" };

/** Las reglas son los resultados de la API, no una animación de evaluación ficticia. */
export default function InspectorReglas() {
  const [id, setId] = useState("F12");
  const { datos, error, recargar } = useApi<FacturaResumen>(`/facturas/${id}`);
  const [seleccion, setSeleccion] = useState<string | null>(null);
  const factura = datos?.id === id ? datos : null;
  const reglas = [...(factura?.reglas ?? [])].sort((a, b) => a.id.localeCompare(b.id));
  const regla = reglas.find(r => r.id === seleccion) ?? reglas.find(r => r.estado === "falla") ?? reglas[0];
  return <section className="inspector-reglas" aria-labelledby="inspector-titulo">
    <div className="inspector-titulo"><h2 id="inspector-titulo">Cada pago pasa<br />por 13 reglas.</h2><span className="inspector-demo">Demo</span></div>
    <p className="inspector-intro">Explora una decisión. Cada señal tiene un motivo.</p>
    <div className="inspector-ejemplos" role="group" aria-label="Factura para explorar">
      {EJEMPLOS.map(e => <button key={e} aria-pressed={id === e} onClick={() => { setId(e); setSeleccion(null); }}>{e}</button>)}
    </div>
    {error ? <div className="inspector-vacio"><p>No pudimos cargar las reglas.</p><button onClick={recargar}>Reintentar</button></div> : !factura ? <p className="inspector-vacio" role="status">Cargando la decisión…</p> : <>
      <div className="inspector-documento"><span><strong>{factura.beneficiario}</strong><small>{factura.numero ?? factura.id}</small></span><span className="num">{dinero(factura.monto_usd)}</span></div>
      <div className="inspector-matriz" role="group" aria-label={`13 reglas de ${id}. ${resumenReglas(reglas)}`}>
        {reglas.map(r => <button key={r.id} className={cx("inspector-regla", `regla-${r.estado}`, r.estado === "falla" && `efecto-${r.efecto}`)} aria-pressed={regla?.id === r.id} aria-label={`${r.id}: ${r.nombre}. ${RESULTADO[r.estado]}`} onClick={() => setSeleccion(r.id)} title={`${r.id} · ${r.nombre}`}>
          <span className="regla-id">{r.id.replace("R", "")}</span><span className="regla-senal">{r.estado === "cumple" ? <Check size={12} /> : r.estado === "falla" ? <X size={12} /> : <Minus size={12} />}</span>
        </button>)}
      </div>
      {regla && <div className="inspector-detalle" aria-live="polite"><p><span className="font-mono">{regla.id}</span><strong>{regla.nombre}</strong></p><p>{regla.detalle || RESULTADO[regla.estado]}</p></div>}
      <a className="inspector-abrir" href={`#/facturas/${id}`}>Abrir decisión completa <ArrowUpRight size={17} /></a>
    </>}
  </section>;
}
