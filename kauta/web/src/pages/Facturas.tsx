import { useCallback, useMemo, useRef, useState } from "react";
import { FileArchive, FileCode, FileText, Image, Mail, MessageSquare, Search, Upload, FlaskConical } from "lucide-react";
import { api, avisarCambio, dinero, fecha, ir, puede, useApi, useCambios, type FacturaResumen, type Usuario } from "../api";
import { EstadoCarga, Aviso, Boton, Cargando, claseEntrada, cx, Encabezado, EstadoChip, TiraReglas, useToast, Vacio } from "../ui";
import BandejaCorreo from "../components/BandejaCorreo";

const FILTROS = [
  { v: "", t: "Todas" }, { v: "pagada", t: "Pagadas" }, { v: "pendiente", t: "Pendientes" },
  { v: "frenada", t: "Frenadas" }, { v: "rechazada", t: "Rechazadas" }, { v: "devuelta", t: "Devueltas" },
];
export const CANALES: Record<string, { t: string; i: any }> = {
  pdf: { t: "PDF", i: FileText }, imagen: { t: "Imagen", i: Image }, correo: { t: "Correo", i: Mail }, chat: { t: "Chat", i: MessageSquare },
  xml: { t: "XML fiscal", i: FileCode }, zip: { t: "ZIP DIAN", i: FileArchive }, simulador: { t: "Simulador", i: FlaskConical },
};

export default function Facturas({ usuario }: { usuario: Usuario }) {
  const { datos, cargando, error, recargar } = useApi<FacturaResumen[]>("/facturas");
  const rec = useCallback(() => recargar(), [recargar]);
  useCambios(rec);
  const [filtro, setFiltro] = useState("");
  const [q, setQ] = useState("");
  const [subiendo, setSubiendo] = useState(false);
  const [arrastre, setArrastre] = useState(false);
  const [errorCarga, setErrorCarga] = useState<string | null>(null);
  const input = useRef<HTMLInputElement>(null);
  const toast = useToast();

  const lista = useMemo(() => (datos ?? []).filter((f) => (!filtro || f.estado === filtro) &&
    (!q || `${f.id} ${f.beneficiario} ${f.numero ?? ""} ${f.archivo}`.toLowerCase().includes(q.toLowerCase()))), [datos, filtro, q]);
  const conteo = (v: string) => (datos ?? []).filter((f) => !v || f.estado === v).length;

  const subir = async (archivo: File) => {
    setSubiendo(true);
    setErrorCarga(null);
    try {
      const fd = new FormData();
      fd.append("archivo", archivo);
      const f = await api<FacturaResumen>("/facturas/cargar", { formulario: fd });
      toast(`${f.id}: ${f.estado === "pagada" ? "pagada" : f.estado === "pendiente" ? "Kauta te pregunta" : f.estado}`, f.estado === "frenada" ? "error" : "exito");
      avisarCambio();
      ir(`facturas/${f.id}`);
    } catch (e) {
      setErrorCarga((e as Error).message);
    } finally {
      setSubiendo(false);
    }
  };
  const sorpresa = async () => {
    try {
      const r = await api<FacturaResumen[]>("/facturas/sorpresa", { cuerpo: {} });
      toast(r.length ? `${r.length} archivos XML/ZIP procesados sin IA` : "Los archivos sorpresa ya estaban procesados", "info");
      avisarCambio();
      recargar();
    } catch (e) {
      toast((e as Error).message, "error");
    }
  };

  return (
    <div className="facturas-pagina">
      <Encabezado titulo="Facturas" texto="Todo lo que llegó por correo, chat, PDF, foto o XML fiscal, con la decisión de Kauta y su motivo."
        accion={puede(usuario, "facturas.cargar") && <>
          <Boton onClick={sorpresa} icono={<FileCode className="h-4 w-4" />}>Procesar XML sorpresa</Boton>
          <Boton variante="primario" onClick={() => input.current?.click()} cargando={subiendo} icono={<Upload className="h-4 w-4" />}>Cargar factura</Boton>
        </>} />
      <input ref={input} type="file" className="hidden" accept=".pdf,.png,.jpg,.jpeg,.webp,.eml,.txt,.xml,.zip"
        onChange={(e) => { const f = e.target.files?.[0]; if (f) subir(f); e.target.value = ""; }} />

      <BandejaCorreo usuario={usuario} />

      {puede(usuario, "facturas.cargar") && (
        <div onDragOver={(e) => { e.preventDefault(); setArrastre(true); }} onDragLeave={() => setArrastre(false)}
          onDrop={(e) => { e.preventDefault(); setArrastre(false); const f = e.dataTransfer.files?.[0]; if (f) subir(f); }}
          className={cx("mb-5 hidden items-center justify-between gap-4 rounded-[14px] border-2 border-dashed px-5 py-4 text-[14px] md:flex",
            arrastre ? "border-azul bg-azul-s" : "border-bruma bg-white")}>
          <span className="text-pizarra">Arrastra aquí un PDF, foto, correo (.eml), chat (.txt), CFDI o factura DIAN en XML, o el ZIP que envía la DIAN. Máximo 10 MB.</span>
          <span className="shrink-0 text-xs text-pizarra">El XML fiscal se lee exacto, sin IA</span>
        </div>
      )}
      {errorCarga && <Aviso tono="error" className="mb-4" titulo="No se procesó el archivo">{errorCarga}</Aviso>}

      <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="facturas-filtros -mx-1 flex gap-1 overflow-x-auto px-1 pb-1" role="tablist" aria-label="Filtrar por estado">
          {FILTROS.map((f) => (
            <button key={f.v} role="tab" aria-selected={filtro === f.v} onClick={() => setFiltro(f.v)}
              className={cx("shrink-0 rounded-full px-3.5 py-1.5 text-[13px] font-semibold", filtro === f.v ? "bg-noche text-white" : "bg-white text-pizarra ring-1 ring-bruma hover:text-noche")}>
              {f.t} <span className="num opacity-70">{conteo(f.v)}</span>
            </button>
          ))}
        </div>
        <label className="relative sm:w-72">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-pizarra" />
          <input className={claseEntrada + " pl-9"} placeholder="Buscar por proveedor, número o ID" value={q} onChange={(e) => setQ(e.target.value)} aria-label="Buscar facturas" />
        </label>
      </div>

      {error || !datos ? <EstadoCarga cargando={cargando} error={error} datos={datos} reintentar={recargar} /> : lista.length === 0 ? (
        <div className="rounded-[14px] border border-bruma bg-white"><Vacio titulo="No hay facturas con ese filtro" texto="Carga un documento o crea uno en el simulador para ver a Kauta decidir." /></div>
      ) : (
        <div className="tabla-facturas overflow-hidden rounded-[14px] border border-bruma bg-white">
          <table className="hidden w-full text-left text-[14px] md:table">
            <thead className="border-b border-bruma bg-niebla/60 text-xs text-pizarra">
              <tr><th className="px-5 py-3 font-semibold">Factura</th><th className="px-3 py-3 font-semibold">Beneficiario</th><th className="px-3 py-3 font-semibold">Canal</th>
                <th className="px-3 py-3 text-right font-semibold">Monto</th><th className="px-3 py-3 font-semibold">13 reglas</th><th className="px-3 py-3 font-semibold">Estado</th><th className="px-5 py-3 font-semibold">Recibida</th></tr>
            </thead>
            <tbody className="divide-y divide-bruma">
              {lista.map((f) => {
                const C = CANALES[f.canal] ?? CANALES.pdf;
                return (
                  <tr key={f.id} onClick={() => ir(`facturas/${f.id}`)} className="cursor-pointer hover:bg-niebla">
                    <td className="px-5 py-3"><a href={`#/facturas/${f.id}`} className="font-mono text-[13px] font-semibold text-noche hover:text-azul" onClick={(e) => e.stopPropagation()}>{f.id}</a>
                      <span className="block text-xs text-pizarra">{f.numero ?? "sin número"}</span></td>
                    <td className="max-w-[260px] px-3 py-3"><span className="block truncate font-semibold">{f.beneficiario}</span><span className="block truncate text-xs text-pizarra">{f.regla !== "—" ? f.motivo.split(":")[0] : "Cumple las 13 reglas"}</span></td>
                    <td className="px-3 py-3 text-pizarra"><span className="inline-flex items-center gap-1.5 text-[13px]"><C.i className="h-4 w-4" />{C.t}</span></td>
                    <td className="px-3 py-3 text-right font-semibold num whitespace-nowrap">{dinero(f.monto, f.moneda ?? "USD")}{f.moneda && f.moneda !== "USD" && f.monto_usd != null && <span className="block text-xs font-normal text-pizarra">{dinero(f.monto_usd)}</span>}</td>
                    <td className="px-3 py-3"><TiraReglas reglas={(f as any).reglas ?? []} /></td>
                    <td className="px-3 py-3"><EstadoChip estado={f.estado} />
                      {f.estado === "pendiente" && f.aprobaciones_requeridas > 1 && <span className="mt-1 block text-xs text-ambar-t">{f.aprobaciones_hechas} de {f.aprobaciones_requeridas} firmas</span>}</td>
                    <td className="px-5 py-3 text-[13px] text-pizarra whitespace-nowrap">{fecha(f.recibida_en)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          <ul className="divide-y divide-bruma md:hidden">
            {lista.map((f) => (
              <li key={f.id}>
                <a href={`#/facturas/${f.id}`} className="block px-4 py-3.5 active:bg-niebla">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="truncate text-[14px] font-semibold">{f.beneficiario}</p>
                      <p className="text-xs text-pizarra"><span className="font-mono">{f.id}</span> · {CANALES[f.canal]?.t ?? f.canal} · {fecha(f.recibida_en)}</p>
                    </div>
                    <EstadoChip estado={f.estado} />
                  </div>
                  <div className="mt-2 flex items-center justify-between gap-3">
                    <TiraReglas reglas={(f as any).reglas ?? []} />
                    <span className="text-[14px] font-bold num">{dinero(f.monto, f.moneda ?? "USD")}</span>
                  </div>
                </a>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
