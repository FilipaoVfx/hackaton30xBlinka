import { useCallback } from "react";
import { useApi, useCambios } from "../api";
import { Aviso, cx, Encabezado, EstadoCarga, Panel } from "../ui";
const ESTADO: Record<string, string> = { activo: "bg-menta-s text-menta-t", disponible: "bg-azul-s text-azul-t", demo: "bg-ambar-s text-ambar-t", alerta: "bg-coral-s text-coral-t" };
export default function Seguridad() {
  const s = useApi<any>("/seguridad");
  const rec = useCallback(() => { s.recargar(); }, [s.recargar]); useCambios(rec);
  if (s.error || !s.datos) return <EstadoCarga cargando={s.cargando} error={s.error} datos={s.datos} reintentar={s.recargar} />;
  const grupos = s.datos.controles.filter((c: any) => c.categoria !== "Identidad").reduce((acc: Record<string, any[]>, c: any) => ((acc[c.categoria] ??= []).push(c), acc), {});
  return <div className="space-y-6"><Encabezado titulo="Seguridad" texto="¿Qué controles protegen cada decisión y cada pago?" />
    <Aviso tono="alerta" titulo="Esta demo no autentica identidad">El selector permite actuar como CEO, CFO o CTO. Los permisos, el doble control y las firmas se comprueban en el servidor. Todos los documentos y pagos son ficticios.</Aviso>
    {Object.entries<any[]>(grupos).map(([cat, lista]) => <Panel key={cat} titulo={cat} cuerpo="p-0"><ul className="divide-y divide-bruma">{lista.map((c) => <li key={c.control} className="grid gap-2 px-5 py-4 sm:grid-cols-[minmax(0,1fr)_auto] sm:gap-4"><div className="min-w-0"><p className="text-[14px] font-semibold">{c.control}</p><p className="mt-1 max-w-3xl text-[13px] leading-relaxed text-pizarra">{c.detalle}</p></div><span className={cx("self-start rounded-full px-2.5 py-1 text-xs font-semibold", ESTADO[c.estado] ?? ESTADO.alerta)}>{c.estado === "activo" ? "Activo" : c.estado === "disponible" ? "Disponible" : c.estado === "demo" ? "Modo demo" : "Revisar"}</span></li>)}</ul></Panel>)}
    <details className="rounded-xl border border-bruma bg-white p-5"><summary className="cursor-pointer text-[14px] font-semibold">Detalle técnico de la protección web</summary><p className="mt-4 break-words font-mono text-xs text-pizarra">{s.datos.csp}</p><p className="mt-4 text-xs text-pizarra">Kauta {s.datos.versiones.kauta} · Python {s.datos.versiones.python} · FastAPI {s.datos.versiones.fastapi}</p></details>
  </div>;
}
