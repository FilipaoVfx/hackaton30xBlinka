import { useCallback, useState } from "react";
import { ArrowLeft, Ban, Check, ChevronDown, FileDown, PenLine, ShieldCheck } from "lucide-react";
import { api, avisarCambio, dinero, fecha, puede, useApi, useCambios, type FacturaDetalle, type Regla, type Usuario } from "../api";
import { EstadoCarga,
  Aviso, Boton, Campo, Cargando, claseEntrada, cx, Dato, EstadoChip, Hash, LineaTiempo, Panel, resumenReglas, Sello, TiraReglas,
  useToast, Validaciones, Vacio,
} from "../ui";
import ReciboFactura from "./ReciboFactura";
import { CANALES } from "./Facturas";

const METODO: Record<string, string> = {
  xml_fiscal: "XML fiscal, lectura exacta sin IA", referencia: "Extracción verificada del set de prueba", ia: "IA con visión (Claude)",
  simulador: "Datos del simulador (sin IA)", rechazado: "Archivo rechazado por seguridad",
};

export default function Detalle({ id, usuario }: { id: string; usuario: Usuario }) {
  const { datos: f, cargando, error, recargar } = useApi<FacturaDetalle>(`/facturas/${id}`, [id]);
  const rec = useCallback(() => recargar(), [recargar]);
  useCambios(rec);
  if (error || !f) return <EstadoCarga cargando={cargando} error={error} datos={f} reintentar={recargar} />;
  const ext = f.extraccion ?? {};
  const C = CANALES[f.canal] ?? CANALES.pdf;
  const [primera, ...resto] = f.motivo.split(/(?<=\.)\s+(?=[A-ZÁÉÍÓÚ«])/);

  return (
    <div className="space-y-6">
      <div>
        <a href="#/facturas" className="inline-flex items-center gap-1.5 text-[13px] font-semibold text-pizarra hover:text-noche"><ArrowLeft className="h-4 w-4" /> Facturas</a>
        <div className="mt-3 flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0">
            <p className="font-mono text-[13px] text-pizarra">{f.id} · {f.numero ?? "sin número"}</p>
            <h1 className="mt-1 text-[26px] font-extrabold leading-tight tracking-[-0.025em] sm:text-[30px]">{f.beneficiario}</h1>
            <p className="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-[13px] text-pizarra">
              <span className="inline-flex items-center gap-1.5"><C.i className="h-4 w-4" />{C.t}</span>
              <span>Recibida {fecha(f.recibida_en)}</span>
              <span>{METODO[ext.metodo_lectura] ?? f.modelo}</span>
            </p>
          </div>
          <div className="text-left sm:text-right">
            <p className="text-[28px] font-extrabold tracking-[-0.03em] num">{dinero(f.monto, f.moneda ?? "USD")}</p>
            {f.moneda !== "USD" && f.monto_usd != null && <p className="text-[13px] text-pizarra num">≈ {dinero(f.monto_usd)}</p>}
            <EstadoChip estado={f.estado} className="mt-2" />
          </div>
        </div>
      </div>

      {/* El porqué, en una sola vista */}
      <section className={cx("rounded-[18px] border p-5 sm:p-6", f.decision === "pagar" ? "border-menta/40 bg-menta-s/60" : f.decision === "frenar" ? "border-coral/40 bg-coral-s/60" : "border-ambar/50 bg-ambar-s/70")}>
        <div className="flex flex-col gap-5 sm:flex-row sm:items-start">
          <Sello decision={f.estado === "rechazada" ? "frenar" : f.decision} className="self-start" />
          <div className="min-w-0 flex-1">
            <p className="text-[17px] font-bold leading-snug">{primera}</p>
            {resto.length > 0 && <p className="mt-1.5 text-[14px] leading-relaxed text-noche/80">{resto.join(" ")}</p>}
            <div className="mt-4 flex flex-wrap items-center gap-3">
              <TiraReglas reglas={f.reglas} grande />
              <span className="text-[13px] text-pizarra">{resumenReglas(f.reglas)} · reglas v{f.version_reglas}</span>
            </div>
          </div>
        </div>
      </section>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[minmax(0,1.15fr)_minmax(0,0.85fr)]">
        <div className="min-w-0 space-y-6">
          {f.estado === "pendiente" && <Decidir f={f} usuario={usuario} alTerminar={recargar} />}
          {f.pago_detalle && <PanelPago f={f} />}
          <PanelReglas reglas={f.reglas} />
          <Panel titulo="Validaciones del documento" subtitulo="Dígitos de verificación, identificadores fiscales y QR, sin IA">
            <Validaciones lista={ext.validaciones ?? []} />
          </Panel>
          <PanelDatos ext={ext} />
          {f.aprobaciones.length > 0 && (
            <Panel titulo="Decisiones humanas" subtitulo="Cada firma es HMAC-SHA256 sobre el monto, la cuenta y la huella del documento">
              <ul className="space-y-3">
                {f.aprobaciones.map((a, i) => (
                  <li key={i} className="flex gap-3">
                    <span className={cx("mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full", a.accion === "aprobar" ? "bg-menta-s text-menta-t" : "bg-coral-s text-coral-t")}>
                      {a.accion === "aprobar" ? <Check className="h-4 w-4" /> : <Ban className="h-4 w-4" />}
                    </span>
                    <div className="min-w-0 text-[14px]">
                      <p><strong>{a.usuario}</strong> {a.accion === "aprobar" ? `firmó la aprobación ${a.nivel}` : "rechazó"} · <span className="text-pizarra">{fecha(a.creada_en)}</span></p>
                      <p className="text-noche/80">«{a.comentario}»</p>
                      <p className="mt-1 flex flex-wrap items-center gap-2 text-xs text-pizarra">Firma <Hash valor={a.firma} />{a.con_mfa ? <span className="inline-flex items-center gap-1 text-menta-t"><ShieldCheck className="h-3.5 w-3.5" /> con segundo factor</span> : <span>sin segundo factor (demo)</span>}
                        {Object.keys(a.correcciones ?? {}).length > 0 && <span>· corrigió {Object.entries(a.correcciones).map(([k, v]) => `${k} = ${v}`).join(", ")}</span>}</p>
                    </div>
                  </li>
                ))}
              </ul>
            </Panel>
          )}
          {f.motivo_inicial !== f.motivo && (
            <Panel titulo="Primera decisión de Kauta" subtitulo="Lo que decidió sola al llegar la factura (cuenta para medir autonomía)">
              <p className="text-[14px] text-noche/85">{f.motivo_inicial}</p>
              <TiraReglas reglas={f.reglas_iniciales} className="mt-3" />
            </Panel>
          )}
        </div>

        <div className="min-w-0 space-y-6">
          <ReciboFactura id={f.id} />
          <Panel titulo="Documento" subtitulo={f.archivo} cuerpo="p-0">
            <VistaDocumento f={f} />
          </Panel>
          <Panel titulo="Huella y trazabilidad">
            <dl className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <Dato etiqueta="Huella SHA-256 del documento"><Hash valor={f.hash_documento} /></Dato>
              <Dato etiqueta="Identificador fiscal único">{f.id_fiscal_unico ? <Hash valor={f.id_fiscal_unico} largo={16} /> : "—"}</Dato>
              <Dato etiqueta="Lectura">{f.modelo}</Dato>
              <Dato etiqueta="Cargada por">{f.cargada_por}</Dato>
              <Dato etiqueta="Periodo">{f.periodo}</Dato>
              <Dato etiqueta="Vence">{f.fecha_vencimiento ? fecha(f.fecha_vencimiento, false) : "—"}</Dato>
            </dl>
          </Panel>
        </div>
      </div>
    </div>
  );
}

function Decidir({ f, usuario, alTerminar }: { f: FacturaDetalle; usuario: Usuario; alTerminar: () => void }) {
  const [comentario, setComentario] = useState("");
  const [codigo, setCodigo] = useState("");
  const [corregir, setCorregir] = useState(false);
  const [corr, setCorr] = useState<{ monto?: string; moneda?: string; numero_factura?: string; horas?: string; fecha_vencimiento?: string }>({});
  const [enviando, setEnviando] = useState<"aprobar" | "rechazar" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const toast = useToast();
  const yaFirme = f.aprobaciones.some((a) => a.usuario === usuario.nombre && a.accion === "aprobar");
  const cargueYo = f.cargada_por === usuario.correo;
  const hechas = f.aprobaciones.filter((a) => a.accion === "aprobar").length;
  const ultima = hechas + 1 >= f.aprobaciones_requeridas;
  const puedeAprobar = puede(usuario, "facturas.aprobar");

  const enviar = async (accion: "aprobar" | "rechazar") => {
    setEnviando(accion);
    setError(null);
    try {
      const correcciones = corregir ? Object.fromEntries(Object.entries(corr).filter(([, v]) => v).map(([k, v]) => [k, ["monto", "horas"].includes(k) ? Number(v) : v])) : undefined;
      const r = await api<any>(`/facturas/${f.id}/${accion}`, { cuerpo: accion === "aprobar" ? { comentario, correcciones: { ...correcciones, ...(!f.fecha_vencimiento && corr.fecha_vencimiento ? { fecha_vencimiento: corr.fecha_vencimiento } : {}) }, codigo_totp: codigo || undefined } : { comentario } });
      toast(accion === "rechazar" ? "Factura rechazada" : r.completa ? (r.pago ? `Aprobada y pagada (${r.pago})` : "Aprobada") : "Firma registrada: falta otra persona");
      avisarCambio();
      alTerminar();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setEnviando(null);
    }
  };

  return (
    <Panel titulo="Kauta te pregunta" subtitulo={f.aprobaciones_requeridas > 1 ? `Doble control: se necesitan ${f.aprobaciones_requeridas} personas distintas (${hechas} de ${f.aprobaciones_requeridas} firmas)` : "Responde para que la factura avance"}
      className="border-ambar/60 ring-4 ring-ambar-s">
      {!f.fecha_vencimiento && f.extraccion.metodo_lectura !== "xml_fiscal" && <Campo etiqueta="Fecha de vencimiento confirmada" ayuda="Confirma el plazo con el proveedor antes de aprobar." className="mb-4"><input type="date" className={claseEntrada} value={corr.fecha_vencimiento ?? ""} onChange={(e) => setCorr({ ...corr, fecha_vencimiento: e.target.value })} /></Campo>}
      <ul className="space-y-3">
        {f.preguntas.map((p) => (
          <li key={p.regla} className="rounded-[12px] bg-ambar-s/70 p-3.5">
            <p className="text-[13px] font-semibold text-ambar-t">{p.regla} · {p.titulo}</p>
            <p className="mt-1 text-[14.5px] font-semibold leading-snug">{p.pregunta}</p>
          </li>
        ))}
      </ul>
      {f.plazo && (
        <p className="mt-3 text-[13px] text-pizarra">
          Vence {fecha(f.plazo.vence, false)} ({f.plazo.dias >= 0 ? `en ${f.plazo.dias} días` : `hace ${-f.plazo.dias} días`}).
          {f.plazo.riel && ` El pago sale por ${f.plazo.riel}${f.plazo.dias_riel ? ` y tarda ${f.plazo.dias_riel} día${f.plazo.dias_riel > 1 ? "s" : ""}` : " y llega el mismo día"}.`}
        </p>
      )}
      {!puedeAprobar ? (
        <Aviso tono="info" className="mt-4">Tu rol ({usuario.rol_nombre}) no aprueba pagos. Entra como Mariana o Carlos para responder.</Aviso>
      ) : cargueYo ? (
        <Aviso tono="info" className="mt-4">Tú cargaste esta factura: por segregación de funciones, la aprueba otra persona.</Aviso>
      ) : yaFirme ? (
        <Aviso tono="info" className="mt-4">Ya firmaste. Falta la aprobación de otra persona: usa «Cambiar de persona».</Aviso>
      ) : (
        <div className="mt-5 space-y-4">
          <Campo etiqueta="Tu respuesta" ayuda="Queda en el registro de auditoría junto con tu firma.">
            <textarea className={claseEntrada + " min-h-[84px]"} value={comentario} onChange={(e) => setComentario(e.target.value)}
              placeholder="Ej.: Llamé al número registrado y el proveedor confirmó el trabajo adicional." />
          </Campo>
          <button type="button" onClick={() => setCorregir(!corregir)} className="inline-flex items-center gap-1.5 text-[13px] font-semibold text-azul">
            <PenLine className="h-4 w-4" /> Corregir un dato antes de aprobar <ChevronDown className={cx("h-4 w-4 transition-transform", corregir && "rotate-180")} />
          </button>
          {corregir && (
            <div className="grid grid-cols-2 gap-3 rounded-[12px] bg-niebla p-3 sm:grid-cols-4">
              <Campo etiqueta="Monto"><input className={claseEntrada} inputMode="decimal" value={corr.monto ?? ""} placeholder={String(f.monto ?? "")} onChange={(e) => setCorr({ ...corr, monto: e.target.value })} /></Campo>
              <Campo etiqueta="Moneda"><input className={claseEntrada} maxLength={3} value={corr.moneda ?? ""} placeholder={f.moneda ?? ""} onChange={(e) => setCorr({ ...corr, moneda: e.target.value.toUpperCase() })} /></Campo>
              <Campo etiqueta="Número"><input className={claseEntrada} value={corr.numero_factura ?? ""} placeholder={f.numero ?? ""} onChange={(e) => setCorr({ ...corr, numero_factura: e.target.value })} /></Campo>
              <Campo etiqueta="Horas"><input className={claseEntrada} inputMode="decimal" value={corr.horas ?? ""} placeholder={String(f.extraccion?.horas ?? "")} onChange={(e) => setCorr({ ...corr, horas: e.target.value })} /></Campo>
            </div>
          )}
          {usuario.mfa_activo && (
            <Campo etiqueta="Código de verificación" ayuda="Se pide de nuevo para mover dinero (step-up).">
              <input className={claseEntrada + " max-w-[180px] text-center tracking-[0.3em] num"} inputMode="numeric" maxLength={6} value={codigo} onChange={(e) => setCodigo(e.target.value.replace(/\D/g, ""))} />
            </Campo>
          )}
          {error && <Aviso tono="error">{error}</Aviso>}
          <div className="flex flex-wrap gap-2">
            <Boton variante="exito" icono={<Check className="h-4 w-4" />} cargando={enviando === "aprobar"} disabled={!comentario.trim() || !!enviando} onClick={() => enviar("aprobar")}>
              {ultima ? "Aprobar y pagar" : `Firmar aprobación ${hechas + 1} de ${f.aprobaciones_requeridas}`}
            </Boton>
            <Boton variante="peligro" icono={<Ban className="h-4 w-4" />} cargando={enviando === "rechazar"} disabled={!comentario.trim() || !!enviando} onClick={() => enviar("rechazar")}>Rechazar</Boton>
          </div>
          <p className="text-xs text-pizarra">Al aprobar, Kauta vuelve a revisar las reglas duras (saldo, duplicados, bloqueos y máximo por pago). Ninguna aprobación las salta.</p>
        </div>
      )}
    </Panel>
  );
}

function PanelReglas({ reglas }: { reglas: Regla[] }) {
  const [todas, setTodas] = useState(false);
  const orden = [...reglas].sort((a, b) => (a.estado === "falla" ? 0 : 1) - (b.estado === "falla" ? 0 : 1) || a.id.localeCompare(b.id));
  const mostradas = todas ? orden : orden.slice(0, Math.max(4, orden.filter((r) => r.estado === "falla").length));
  return (
    <Panel titulo="Las 13 reglas" subtitulo="Código determinista: misma factura y mismas reglas, misma decisión" cuerpo="p-0">
      <ul className="divide-y divide-bruma">
        {mostradas.map((r) => (
          <li key={r.id} className="flex gap-3 px-5 py-3">
            <span className={cx("mt-1 h-3 w-3 shrink-0 rounded-[3px]", r.estado === "cumple" ? "bg-menta" : r.estado === "no_aplica" ? "bg-bruma" : r.efecto === "frenar" ? "bg-coral" : "bg-ambar")} />
            <div className="min-w-0 text-[14px]">
              <p><span className="font-mono text-[12px] text-pizarra">{r.id}</span> <strong>{r.nombre}</strong>{" "}
                <span className={cx("text-xs font-semibold", r.estado === "cumple" ? "text-menta-t" : r.estado === "no_aplica" ? "text-pizarra" : r.efecto === "frenar" ? "text-coral-t" : "text-ambar-t")}>
                  {r.estado === "cumple" ? "cumple" : r.estado === "no_aplica" ? "no aplica" : r.efecto === "frenar" ? "falla · frena" : "falla · escala"}</span></p>
              <p className="text-[13px] text-noche/75">{r.detalle}</p>
            </div>
          </li>
        ))}
      </ul>
      {orden.length > mostradas.length || todas ? (
        <button onClick={() => setTodas(!todas)} className="w-full border-t border-bruma px-5 py-3 text-[13px] font-semibold text-azul hover:bg-niebla">
          {todas ? "Ver menos" : `Ver las ${orden.length} reglas`}
        </button>
      ) : null}
    </Panel>
  );
}

const TIPOS_DOC: Record<string, string> = {
  factura: "Factura", cuenta_cobro: "Cuenta de cobro", nota_credito: "Nota crédito (no es un cobro)", nota_debito: "Nota débito",
  recibo_pago: "Recibo o complemento de pago (no es un cobro)", documento_soporte: "Documento soporte",
  otro: "Otro comprobante (no es un cobro)", desconocido: "Tipo no reconocido",
};

function PanelDatos({ ext }: { ext: Record<string, any> }) {
  const conf = ext.confianza ?? {};
  const filas: [string, string, any][] = [
    ["beneficiario", "Beneficiario", ext.beneficiario?.nombre], ["id_fiscal", "Identificación fiscal", ext.beneficiario?.id_fiscal],
    ["numero_factura", "Número", ext.numero_factura], ["moneda", "Moneda", ext.moneda], ["monto", "Total a pagar", ext.monto != null ? dinero(ext.monto, ext.moneda ?? "USD") : null],
    ["fecha_vencimiento", "Vencimiento", ext.fecha_vencimiento],
  ];
  return (
    <Panel titulo="Datos leídos" subtitulo="Con la confianza de la lectura por campo (mínimo 0,85 para pagar sola)">
      <dl className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        {filas.map(([k, et, v]) => (
          <div key={k} className="min-w-0">
            <dt className="flex items-center justify-between text-xs text-pizarra"><span>{et}</span>{conf[k] != null && <span className={cx("num", conf[k] < 0.85 ? "font-bold text-coral-t" : "")}>{Number(conf[k]).toFixed(2).replace(".", ",")}</span>}</dt>
            <dd className="mt-0.5 truncate text-[14px] font-semibold">{v ?? "—"}</dd>
            {conf[k] != null && <div className="mt-1 h-1 rounded-full bg-bruma"><div className={cx("h-full rounded-full", conf[k] < 0.85 ? "bg-coral" : "bg-menta")} style={{ width: `${conf[k] * 100}%` }} /></div>}
          </div>
        ))}
      </dl>
      {(ext.concepto || ext.cuenta_destino || ext.horas || ext.tipo_documento) && (
        <dl className="mt-4 grid grid-cols-1 gap-3 border-t border-bruma pt-4 sm:grid-cols-3">
          <Dato etiqueta="Concepto" className="sm:col-span-2">{ext.concepto ?? "—"}</Dato>
          <Dato etiqueta="Cuenta pedida en la factura">{ext.cuenta_destino ? `···${ext.cuenta_destino}` : "No indica"}</Dato>
          {ext.tipo_documento && <Dato etiqueta="Tipo de documento">{TIPOS_DOC[ext.tipo_documento] ?? ext.tipo_documento}</Dato>}
          {ext.horas != null && <Dato etiqueta="Horas">{ext.horas}</Dato>}
        </dl>
      )}
      {ext.impuestos?.length > 0 && (
        <p className="mt-4 text-[13px] text-pizarra">Impuestos del XML: {ext.impuestos.map((i: any) => `${i.tipo}${i.tasa != null ? ` ${i.tasa} %` : ""} ${dinero(i.monto, ext.moneda)}`).join(" · ")}</p>
      )}
    </Panel>
  );
}

function PanelPago({ f }: { f: FacturaDetalle }) {
  const p = f.pago_detalle!;
  return (
    <Panel titulo={`Pago ${p.id}`} subtitulo={`${p.riel_nombre} · ${p.liquidacion}`}
      accion={<a href={`/api/pagos/${p.id}/comprobante`} target="_blank" rel="noopener" className="inline-flex items-center gap-1.5 text-[13px] font-semibold text-azul hover:underline"><FileDown className="h-4 w-4" /> Comprobante</a>}>
      <dl className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <Dato etiqueta="Recibe el beneficiario">{dinero(p.monto_destino, p.moneda_destino)}</Dato>
        <Dato etiqueta="Cuenta">{p.cuenta}</Dato>
        <Dato etiqueta="Comisión + cambio">{dinero(p.comision_usd + p.costo_fx_usd)}</Dato>
        <Dato etiqueta="Costo total">{dinero(p.costo_total_usd)}</Dato>
      </dl>
      {p.moneda_destino !== "USD" && <p className="mt-3 text-[13px] text-pizarra">Tasa de referencia {p.tasa_referencia.toLocaleString("es-CO")} {p.moneda_destino}/USD; aplicada {p.tasa_aplicada.toLocaleString("es-CO", { maximumFractionDigits: 4 })} (incluye el diferencial cambiario).</p>}
      <div className="mt-5"><LineaTiempo pasos={p.linea_tiempo} /></div>
      {p.motivo_devolucion && <Aviso tono="error" className="mt-4" titulo="El banco devolvió el pago">{p.motivo_devolucion}. Los fondos volvieron a la sub-wallet y nada se pagó dos veces.</Aviso>}
    </Panel>
  );
}

function VistaDocumento({ f }: { f: FacturaDetalle }) {
  const [fallo, setFallo] = useState(false);
  if (f.tiene_vista && !fallo) {
    return <img src={`/api/facturas/${f.id}/vista`} alt={`Vista previa de ${f.archivo}`} className="block w-full rounded-b-[14px]" loading="lazy" onError={() => setFallo(true)} />;
  }
  return <pre className="max-h-[560px] overflow-auto whitespace-pre-wrap break-words p-5 font-mono text-[12px] leading-relaxed text-noche/85">{f.texto || "Sin vista previa."}</pre>;
}
