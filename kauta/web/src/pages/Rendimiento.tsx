import { useCallback } from "react";
import { ArrowUpRight, Info } from "lucide-react";
import { dinero, fecha, PERIODO, useApi, useCambios } from "../api";
import { Encabezado, EstadoCarga, Panel, TarjetasMetricas } from "../ui";

const FUENTES = [{ id: "lectura", nombre: "Lectura", color: "bg-azul" }, { id: "revision", nombre: "Revisión humana", color: "bg-ambar" }, { id: "pago", nombre: "Pago", color: "bg-menta" }, { id: "infraestructura", nombre: "Infraestructura", color: "bg-noche" }];
const LECTORES: Record<string, string> = { xml: "XML fiscal", texto: "Texto", ocr: "OCR local", ia: "IA simulada" };
export default function Rendimiento() {
  const { datos: d, cargando, error, recargar } = useApi<any>("/rendimiento");
  const rec = useCallback(() => { recargar(); }, [recargar]); useCambios(rec);
  if (error || !d) return <EstadoCarga cargando={cargando} error={error} datos={d} reintentar={recargar} />;
  const conocidos = FUENTES.filter((f) => d.fuentes_usd[f.id] != null);
  const total = conocidos.reduce((s, f) => s + d.fuentes_usd[f.id], 0);
  return <div className="space-y-8">
    <Encabezado titulo="Rendimiento y costos" texto="¿Cuánto cuesta resolver una factura y dónde se va el dinero?" />
    <TarjetasMetricas tarjetas={d.tarjetas} />
    <Panel titulo="Dónde se va el costo" subtitulo={`Todo lo registrado en ${PERIODO(d.periodo)}: facturas resueltas y abiertas.`} accion={<span className="text-[14px] font-semibold num">{dinero(total)} conocidos</span>}>
      <div className="mt-2 flex h-4 gap-1 overflow-hidden rounded-full bg-niebla" role="img" aria-label={FUENTES.map((f) => `${f.nombre}: ${dinero(d.fuentes_usd[f.id], "USD", 4)}`).join("; ")}>
        {conocidos.filter((f) => d.fuentes_usd[f.id] > 0).map((f) => <div key={f.id} className={f.color} style={{ flexGrow: d.fuentes_usd[f.id], minWidth: 5 }} />)}
      </div>
      <dl className="mt-6 divide-y divide-bruma">{FUENTES.map((f) => <div className="flex items-center gap-3 py-3 text-sm" key={f.id}><span className={`h-2.5 w-2.5 shrink-0 rounded-sm ${f.color}`} /><dt className="flex-1">{f.nombre}</dt><dd className="font-semibold num">{dinero(d.fuentes_usd[f.id], "USD", 4)}</dd></div>)}</dl>
      <details className="mt-4 border-t border-bruma pt-4"><summary className="cursor-pointer py-2 text-[13px] font-semibold text-azul">Desglosar lectura: XML, texto, OCR e IA</summary><dl className="mt-2 divide-y divide-bruma">{Object.entries<number | null>(d.lectura_usd).map(([k, v]) => <div className="flex justify-between gap-4 py-3 pl-5 text-[13px]" key={k}><dt>{LECTORES[k] ?? k}</dt><dd className="num">{dinero(v, "USD", 4)}</dd></div>)}</dl><p className="mt-3 text-xs leading-relaxed text-pizarra">La lectura empieza por XML y texto, sigue por OCR y usa IA simulada cuando la confianza es insuficiente. Los tokens están incluidos en el costo de IA.</p></details>
    </Panel>
    <div className="grid gap-7 lg:grid-cols-2">
      <section className="px-1"><h2 className="text-[15px] font-semibold">Lo resuelto y lo que sigue en curso</h2><p className="mt-3 text-[14px] leading-relaxed text-pizarra">El costo por factura resuelta usa {dinero(d.numerador_usd)} entre {d.denominador} facturas finales. Otras {d.abiertas} facturas siguen abiertas, con {dinero(d.en_curso_usd)} conocidos que aún no entran en esa métrica.</p><a href="#/facturas" className="enlace mt-4">Abrir facturas<ArrowUpRight className="h-4 w-4" /></a></section>
      <section className="rounded-xl border border-bruma p-5"><h2 className="flex items-center gap-2 text-[14px] font-semibold"><Info className="h-4 w-4 text-pizarra" />Cómo leer estas cifras</h2><p className="mt-3 text-[13px] leading-relaxed text-pizarra">Tarifas y tiempos simulados; la revisión humana es estimada. “—” significa costo desconocido. La infraestructura del mes se reparte entre facturas finales y es provisional hasta el cierre.</p><p className="mt-3 text-xs text-pizarra">Cálculo actual · {fecha(d.calculado_en)} · igual para CEO, CFO y CTO</p></section>
    </div>
  </div>;
}
