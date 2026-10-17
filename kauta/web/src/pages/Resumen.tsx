import { useCallback } from "react";
import { ArrowRight, CheckCheck, MessageCircleQuestion, ShieldCheck, Upload } from "lucide-react";
import { dinero, useApi, useCambios, type FacturaResumen, type Usuario } from "../api";
import InspectorReglas from "../components/InspectorReglas";
import { Boton, Encabezado, EstadoCarga, EstadoChip, Panel, TarjetasMetricas, TiraReglas } from "../ui";

export default function Resumen({ usuario }: { usuario: Usuario }) {
  const { datos, cargando, error, recargar } = useApi<any>("/resumen");
  const rec = useCallback(() => { recargar(); }, [recargar]);
  useCambios(rec);
  if (error || !datos) return <EstadoCarga cargando={cargando} datos={datos} error={error} reintentar={recargar} />;
  const lente = datos.lente;
  const firmas: FacturaResumen[] = [...(datos.necesitan_firma ?? [])].sort((a, b) => (["F10", "F12"].includes(a.id) ? 0 : 1) - (["F10", "F12"].includes(b.id) ? 0 : 1));
  return <div className="resumen-pagina space-y-8">
    <Encabezado titulo="Resumen" texto={lente.pregunta} accion={<a href={usuario.rol === "cto" ? "#/facturas" : "#/pregunta"}><Boton variante="primario" icono={usuario.rol === "cto" ? <Upload className="h-4 w-4" /> : <MessageCircleQuestion className="h-4 w-4" />}>{usuario.rol === "cto" ? "Revisar facturas" : "Revisar pendientes"}</Boton></a>} />
    <TarjetasMetricas tarjetas={lente.tarjetas} />
    {lente.frase && <p className="flex max-w-3xl items-start gap-3 text-[15px] leading-relaxed"><ShieldCheck className="mt-0.5 h-5 w-5 shrink-0 text-menta-t" />{lente.frase}</p>}
    <div className="resumen-operacion">
      <Panel className="panel-decisiones" titulo={usuario.rol === "cto" ? "Últimas decisiones" : "Necesita tu firma"} subtitulo={usuario.rol === "cto" ? "El motivo, la decisión y sus 13 reglas." : "Kauta ya hizo su parte. Estas decisiones necesitan una persona."} cuerpo="p-0" accion={<a className="enlace" href={usuario.rol === "cto" ? "#/facturas" : "#/pregunta"}>Ver todas <ArrowRight className="h-3.5 w-3.5" /></a>}>
        {(usuario.rol === "cto" ? datos.ultimas : firmas).slice(0, 3).length ? <ul className="divide-y divide-bruma">{(usuario.rol === "cto" ? datos.ultimas : firmas).slice(0, 3).map((f: FacturaResumen) => <li key={f.id}>
          <a href={`#/facturas/${f.id}`} className="decision-fila">
            <span className="decision-documento" aria-hidden="true">{f.id}</span><div className="min-w-0 flex-1"><p className="text-xs text-pizarra">{f.id} · {f.numero ?? "Sin número"}</p><p className="mt-1 text-[14px] font-semibold">{f.beneficiario}</p><p className="mt-1 text-xs text-pizarra">{f.aprobaciones_hechas ? `${f.aprobaciones_hechas} de ${f.aprobaciones_requeridas} firmas` : f.motivo.split(/\.\s+(?=[A-ZÁÉÍÓÚ])/)[0]}</p>{f.reglas && <div className="mt-3"><TiraReglas reglas={f.reglas} /></div>}</div>
            <div className="shrink-0 text-right"><p className="text-[14px] font-semibold num">{dinero(f.monto_usd)}</p><EstadoChip estado={f.estado} className="mt-2" /></div>
          </a>
        </li>)}</ul> : <div className="px-5 py-12 text-center"><CheckCheck className="mx-auto mb-3 h-7 w-7 text-menta-t" /><p className="font-semibold">Estás al día</p><p className="mt-1 text-sm text-pizarra">No hay facturas que necesiten tu firma.</p></div>}
      </Panel>
      <InspectorReglas />
    </div>
    <section aria-label="Recorrido de demostración" className="border-t border-bruma pt-6">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2"><h2 className="text-[14px] font-semibold">Cuatro decisiones para conocer Kauta</h2><span className="text-xs text-pizarra">Documentos y pagos ficticios</span></div>
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">{[["F01", "Se paga sola", "Nube Clara"], ["F07", "Frena un duplicado", "Nube Clara"], ["F12", "Protege la cuenta", "Andrés Felipe Rojas"], ["F10", "Pide una segunda firma", "Datos del Sur"]].map(([id, titulo, proveedor]) => <a href={`#/facturas/${id}`} key={id} className={`grupo-recorrido recorrido-${id}`}><span className="text-xs text-pizarra">{id} · {proveedor}</span><span className="mt-2 flex items-center justify-between gap-3 text-[13px] font-semibold">{titulo}<ArrowRight className="h-4 w-4 shrink-0 text-pizarra" /></span></a>)}</div>
    </section>
  </div>;
}
