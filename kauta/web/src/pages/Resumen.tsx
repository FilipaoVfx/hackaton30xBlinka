import { useCallback } from "react";
import { ArrowRight, FlaskConical, MessageCircleQuestion, ScanText } from "lucide-react";
import { dinero, ir, numero, PERIODO, useApi, useCambios, type FacturaResumen, type Usuario } from "../api";
import { BarraPresupuesto, Boton, Cargando, cx, EstadoChip, GraficoSaldo, Panel, Vacio } from "../ui";

const NOMBRES: Record<string, string> = {
  R01: "Datos legibles, completos y válidos", R02: "Moneda permitida", R03: "No duplicada", R04: "Un cobro por periodo",
  R05: "Beneficiario no bloqueado", R06: "Beneficiario registrado", R07: "Cuenta registrada", R08: "Cuadra con el contrato",
  R09: "Máximo por pago", R10: "Umbral de aprobación", R11: "Límite por beneficiario", R12: "Saldo del periodo", R13: "Sin instrucciones ocultas",
};

export default function Resumen({ usuario }: { usuario: Usuario }) {
  const { datos, cargando, error, recargar } = useApi<any>("/resumen");
  const rec = useCallback(() => recargar(), [recargar]);
  useCambios(rec);
  if (cargando && !datos) return <Cargando filas={6} />;
  if (error || !datos) return <Vacio titulo="No se pudo cargar el resumen" texto={error ?? ""} />;
  const m = datos.metricas;
  const w = datos.wallet;
  const usado = datos.serie.length ? datos.serie[datos.serie.length - 1].acumulado : 0;
  const maxFalla = Math.max(1, ...Object.values<number>(datos.fallas_por_regla));

  return (
    <div className="space-y-6">
      {/* Lo más característico: cómo se fue gastando el periodo, factura por factura */}
      <section className="overflow-hidden rounded-[18px] border border-bruma bg-white">
        <div className="grid grid-cols-1 gap-6 p-5 sm:p-7 lg:grid-cols-[minmax(0,330px)_minmax(0,1fr)]">
          <div className="flex flex-col">
            <p className="text-[14px] font-semibold text-pizarra">Periodo de {PERIODO(datos.periodo)}</p>
            <p className="mt-2 text-[40px] font-extrabold leading-none tracking-[-0.035em] num sm:text-[46px]">{dinero(usado, "USD", 0)}</p>
            <p className="mt-2 text-[15px] text-pizarra">pagados de {dinero(datos.presupuesto, "USD", 0)} del presupuesto mensual, sin un solo pago fuera de las reglas.</p>
            <BarraPresupuesto usado={usado} total={datos.presupuesto} className="mt-5" />
            <dl className="mt-5 grid grid-cols-3 gap-3 text-[13px]">
              <div><dt className="text-pizarra">Pagadas</dt><dd className="text-[20px] font-bold text-menta-t num">{m.pagadas}</dd></div>
              <div><dt className="text-pizarra">Pendientes</dt><dd className="text-[20px] font-bold text-ambar-t num">{m.pendientes}</dd></div>
              <div><dt className="text-pizarra">Frenadas</dt><dd className="text-[20px] font-bold text-coral-t num">{m.frenadas}</dd></div>
            </dl>
            <div className="mt-auto flex flex-wrap gap-2 pt-6">
              <Boton variante="primario" icono={<FlaskConical className="h-4 w-4" />} onClick={() => ir("simulador")}>Probar el simulador</Boton>
              {m.pendientes > 0 && <Boton icono={<MessageCircleQuestion className="h-4 w-4" />} onClick={() => ir("pregunta")}>Responder a Kauta ({m.pendientes})</Boton>}
            </div>
          </div>
          <div className="min-w-0">
            <div className="hidden sm:block"><GraficoSaldo serie={datos.serie} presupuesto={datos.presupuesto} /></div>
            <div className="sm:hidden"><GraficoSaldo compacto serie={datos.serie} presupuesto={datos.presupuesto} /></div>
            <p className="mt-1 flex flex-wrap gap-x-4 gap-y-1 text-xs text-pizarra">
              <Leyenda c="bg-menta" t="Pagada sola o con aprobación" /><Leyenda c="bg-ambar" t="Espera a una persona" /><Leyenda c="bg-coral" t="Frenada por una regla dura" />
            </p>
          </div>
        </div>
      </section>

      {/* Los tres criterios del jurado */}
      <section className="grid grid-cols-1 overflow-hidden rounded-[18px] bg-noche text-white md:grid-cols-3">
        {datos.criterios.map((c: any, i: number) => (
          <div key={c.criterio} className={cx("p-6", i > 0 && "border-t border-noche-3 md:border-l md:border-t-0")}>
            <p className="text-[14px] font-semibold text-[#AAB6D3]">{c.criterio}</p>
            <p className={cx("mt-1 text-[32px] font-extrabold tracking-[-0.03em] num", i === 0 ? "text-white" : i === 1 ? "text-menta" : "text-ambar")}>{c.valor}</p>
            <p className="mt-2 text-[13.5px] leading-relaxed text-[#C9D2E8]">{c.detalle}</p>
          </div>
        ))}
      </section>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-[minmax(0,1.25fr)_minmax(0,1fr)]">
        <Panel titulo="Últimas decisiones" subtitulo="Cada barra de colores son las 13 reglas de la factura" cuerpo="p-0"
          accion={<a href="#/facturas" className="inline-flex items-center gap-1 text-[13px] font-semibold text-azul hover:underline">Ver todas <ArrowRight className="h-3.5 w-3.5" /></a>}>
          <ul className="divide-y divide-bruma">
            {datos.ultimas.map((f: FacturaResumen) => (
              <li key={f.id}>
                <a href={`#/facturas/${f.id}`} className="flex items-center gap-3 px-5 py-3.5 hover:bg-niebla">
                  <span className="w-14 shrink-0 font-mono text-[12px] text-pizarra">{f.id}</span>
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-[14px] font-semibold">{f.beneficiario}</span>
                    <span className="block truncate text-xs text-pizarra">{f.motivo}</span>
                  </span>
                  <span className="hidden text-right text-[13px] font-semibold num sm:block">{dinero(f.monto, f.moneda ?? "USD")}</span>
                  <EstadoChip estado={f.estado} />
                </a>
              </li>
            ))}
          </ul>
        </Panel>

        <div className="space-y-6">
          <Panel titulo="Dónde fallan las reglas" subtitulo="Veces que cada regla detuvo o escaló una factura">
            <ul className="space-y-2.5">
              {Object.entries<number>(datos.fallas_por_regla).sort((a, b) => b[1] - a[1]).slice(0, 8).map(([r, n]) => (
                <li key={r} className="grid grid-cols-[2.6rem_minmax(0,1fr)_2rem] items-center gap-3 text-[13px]">
                  <span className="font-mono text-pizarra">{r}</span>
                  <span>
                    <span className="block truncate font-medium">{NOMBRES[r]}</span>
                    <span className="mt-1 block h-1.5 rounded-full bg-bruma"><span className={cx("block h-full rounded-full", ["R03", "R04", "R05", "R09", "R12"].includes(r) ? "bg-coral" : "bg-ambar")} style={{ width: `${(n / maxFalla) * 100}%` }} /></span>
                  </span>
                  <span className="text-right font-bold num">{n}</span>
                </li>
              ))}
            </ul>
          </Panel>
          <Panel titulo="Wallet" subtitulo="Saldos simulados en dólares"
            accion={<a href="#/wallet" className="inline-flex items-center gap-1 text-[13px] font-semibold text-azul hover:underline">Abrir <ArrowRight className="h-3.5 w-3.5" /></a>}>
            <dl className="grid grid-cols-2 gap-4">
              <div><dt className="text-xs text-pizarra">Disponible para pagar</dt><dd className="text-[19px] font-bold num">{dinero(w.disponible_cxp)}</dd></div>
              <div><dt className="text-xs text-pizarra">Pagado a proveedores</dt><dd className="text-[19px] font-bold num">{dinero(w.pagado)}</dd></div>
              <div><dt className="text-xs text-pizarra">Cuenta operativa</dt><dd className="text-[15px] font-semibold num">{dinero(w.operativa)}</dd></div>
              <div><dt className="text-xs text-pizarra">Comisiones y cambio</dt><dd className="text-[15px] font-semibold num">{dinero(w.costos)}</dd></div>
            </dl>
            <p className="mt-4 flex items-center gap-2 rounded-[10px] bg-niebla px-3 py-2 text-xs text-pizarra">
              <ScanText className="h-4 w-4 shrink-0" /> Lectura de documentos: {datos.extractor}
            </p>
          </Panel>
        </div>
      </div>
      <p className="text-center text-xs text-pizarra">Dinero protegido en trampas detenidas: <strong className="text-noche num">{dinero(m.dinero_protegido_usd)}</strong> · {numero(m.total)} facturas procesadas · reglas v{datos.version_reglas}</p>
    </div>
  );
}

function Leyenda({ c, t }: { c: string; t: string }) {
  return <span className="inline-flex items-center gap-1.5"><span className={cx("h-2.5 w-2.5 rounded-full", c)} />{t}</span>;
}
