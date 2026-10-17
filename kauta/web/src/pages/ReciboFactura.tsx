import { useCallback } from "react";
import { ReceiptText, ShieldCheck } from "lucide-react";
import { dinero, useApi, useCambios } from "../api";
import { EstadoCarga, Panel } from "../ui";

export default function ReciboFactura({ id }: { id: string }) {
  const { datos: d, cargando, error, recargar } = useApi<any>(`/facturas/${id}/recibo`);
  const rec = useCallback(() => { recargar(); }, [recargar]); useCambios(rec);
  return <Panel titulo={<span className="flex items-center gap-2"><ReceiptText className="h-4 w-4 text-pizarra" />Lo que costó esta factura</span>} subtitulo="Recibo de costos · simulado">
    {error || !d ? <EstadoCarga cargando={cargando} datos={d} error={error} reintentar={recargar} /> : <>
      <dl className="divide-y divide-bruma">{d.lineas.map((l: any, i: number) => <div className="py-3 first:pt-0" key={i}><div className="flex items-start justify-between gap-3 text-[13px]"><dt className="min-w-0">{l.titulo}</dt><dd className="shrink-0 font-semibold num">{dinero(l.importe_usd, "USD", 4)}</dd></div>{l.fuente === "infraestructura" && <p className="mt-1 text-xs text-pizarra">{l.detalle}</p>}<details className="mt-1"><summary className="cursor-pointer py-1 text-xs text-pizarra">Ver detalle</summary><p className="mt-1 text-xs leading-relaxed text-pizarra">{l.detalle}</p></details></div>)}</dl>
      <div className="mt-3 flex items-center justify-between gap-3 border-t border-noche/20 pt-4 text-sm font-semibold"><span>{d.total_completo ? "Total conocido" : "Total parcial"}</span><span className="num">{dinero(d.total_usd, "USD", 4)}</span></div>
      {!d.total_completo && <p className="mt-2 text-xs text-ambar-t">Hay costos desconocidos. “—” no significa cero.</p>}
      {d.protegido && <div className="mt-5 flex gap-2 border-t border-bruma pt-4 text-[13px] leading-relaxed"><ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-menta-t" /><p>{d.protegido.texto}</p></div>}
      <p className="mt-4 text-[11px] leading-relaxed text-pizarra">Tarifas simuladas. Revisión humana estimada. La parte de infraestructura es provisional durante el mes abierto.</p>
    </>}
  </Panel>;
}
