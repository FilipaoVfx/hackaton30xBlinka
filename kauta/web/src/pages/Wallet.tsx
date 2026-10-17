import { useCallback, useState } from "react";
import { ArrowRight, CircleCheck, CircleX, Landmark, Plus, RotateCcw } from "lucide-react";
import { api, avisarCambio, dinero, fecha, PERIODO, puede, useApi, useCambios, type Pago, type Usuario } from "../api";
import { Aviso, BarraPresupuesto, Boton, Campo, Cargando, claseEntrada, cx, Encabezado, Modal, Panel, useToast } from "../ui";

const FLUJO = [
  { c: "operativa", t: "Cuenta operativa", d: "Dólares de la empresa" },
  { c: "cxp", t: "Sub-wallet de pagos", d: "Presupuesto del periodo" },
  { c: "reservas", t: "Reservado", d: "Pagos aprobados por salir" },
  { c: "transito", t: "En tránsito", d: "Enviados al riel" },
  { c: "proveedores", t: "Pagado", d: "Llegó al beneficiario" },
];

export default function WalletPagina({ usuario }: { usuario: Usuario }) {
  const w = useApi<any>("/wallet");
  const pagos = useApi<Pago[]>("/pagos");
  const rieles = useApi<any[]>("/rieles");
  const rec = useCallback(() => { w.recargar(); pagos.recargar(); }, [w.recargar, pagos.recargar]);
  useCambios(rec);
  const [fondear, setFondear] = useState(false);
  const [monto, setMonto] = useState("25000");
  const toast = useToast();
  if (!w.datos) return <Cargando filas={5} />;
  const d = w.datos;
  const saldo = (c: string) => d.cuentas.find((x: any) => x.codigo === c)?.saldo ?? 0;

  const hacerFondeo = async () => {
    try {
      await api("/wallet/fondear", { cuerpo: { monto: Number(monto) } });
      toast(`Depósito simulado de ${dinero(Number(monto))} a la cuenta operativa`);
      setFondear(false);
      avisarCambio();
      rec();
    } catch (e) { toast((e as Error).message, "error"); }
  };
  const reintentar = async (id: string) => {
    try {
      const p = await api<Pago>(`/pagos/${id}/reintentar`, { cuerpo: {} });
      toast(`Reintento ${p.id}: ${p.estado}`);
      avisarCambio();
      rec();
    } catch (e) { toast((e as Error).message, "error"); }
  };

  return (
    <div className="space-y-6">
      <Encabezado titulo="Wallet y pagos"
        texto="La cuenta digital en dólares desde la que Kauta paga a proveedores en cinco países. Cada movimiento es un asiento de doble partida: nada aparece ni desaparece."
        accion={puede(usuario, "wallet.fondear") && <Boton icono={<Plus className="h-4 w-4" />} onClick={() => setFondear(true)}>Depositar en la cuenta operativa</Boton>} />

      {/* El recorrido del dinero */}
      <section className="rounded-[18px] bg-noche p-5 text-white sm:p-6">
        <div className="flex flex-col gap-3 md:flex-row md:items-stretch">
          {FLUJO.map((x, i) => (
            <div key={x.c} className="flex items-center gap-3 md:flex-1 md:flex-col md:items-stretch">
              <div className={cx("flex-1 rounded-[14px] p-4", x.c === "cxp" ? "bg-white text-noche" : "bg-noche-2")}>
                <p className={cx("text-[13px] font-semibold", x.c === "cxp" ? "text-pizarra" : "text-[#AAB6D3]")}>{x.t}</p>
                <p className="mt-1 text-[20px] font-extrabold tracking-[-0.02em] num">{dinero(saldo(x.c), "USD", 0)}</p>
                <p className={cx("text-xs", x.c === "cxp" ? "text-pizarra" : "text-[#8D9AC0]")}>{x.d}</p>
              </div>
              {i < FLUJO.length - 1 && <ArrowRight className="hidden h-5 w-5 shrink-0 self-center text-[#5D6F9E] md:block md:rotate-0" />}
            </div>
          ))}
        </div>
        <p className="mt-4 flex items-center gap-2 text-[13px] text-[#C9D2E8]">
          {d.libro.ok ? <CircleCheck className="h-4 w-4 text-menta" /> : <CircleX className="h-4 w-4 text-coral" />} {d.libro.mensaje}
          <span className="hidden sm:inline">· Comisiones y cambio pagados: {dinero(d.costos)}</span>
        </p>
      </section>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[minmax(0,0.8fr)_minmax(0,1.2fr)]">
        <Panel titulo="Presupuesto por periodo" subtitulo="La sub-wallet se fondea una vez por mes; es el saldo que vigila la regla R12">
          <ul className="space-y-5">
            {d.periodos.map((p: any) => (
              <li key={p.periodo}>
                <div className="flex items-baseline justify-between gap-3 text-[14px]">
                  <span className="font-semibold first-letter:uppercase">{PERIODO(p.periodo)}</span>
                  <span className="num text-pizarra">{dinero(p.pagado, "USD", 0)} de {dinero(p.presupuesto, "USD", 0)}</span>
                </div>
                <BarraPresupuesto usado={p.pagado} total={p.presupuesto} className="mt-2" />
                <p className="mt-1 text-xs text-pizarra num">Disponible: {dinero(p.disponible)}</p>
              </li>
            ))}
          </ul>
        </Panel>
        <Panel titulo="Pagos" subtitulo="Cada orden va firmada y con clave de idempotencia" cuerpo="p-0">
          {!pagos.datos ? <div className="p-5"><Cargando /></div> : (
            <ul className="divide-y divide-bruma">
              {pagos.datos.slice(0, 14).map((p) => (
                <li key={p.id} className="flex items-center gap-3 px-5 py-3">
                  <span className={cx("flex h-8 w-8 shrink-0 items-center justify-center rounded-full", p.estado === "devuelto" ? "bg-coral-s text-coral-t" : "bg-menta-s text-menta-t")}>
                    {p.estado === "devuelto" ? <RotateCcw className="h-4 w-4" /> : <Landmark className="h-4 w-4" />}
                  </span>
                  <a href={`#/facturas/${p.factura_id}`} className="min-w-0 flex-1">
                    <span className="block truncate text-[14px] font-semibold">{p.beneficiario}</span>
                    <span className="block truncate text-xs text-pizarra">{p.id} · {p.riel_nombre} · {fecha(p.creado_en)}</span>
                  </a>
                  <span className="text-right">
                    <span className="block text-[14px] font-bold num">{dinero(p.monto_destino, p.moneda_destino)}</span>
                    {p.estado === "devuelto" && puede(usuario, "pagos.reintentar")
                      ? <button onClick={() => reintentar(p.id)} className="text-xs font-semibold text-azul hover:underline">Reintentar</button>
                      : <span className={cx("block text-xs", p.estado === "devuelto" ? "text-coral-t font-semibold" : "text-pizarra")}>{p.estado === "liquidado" ? "Liquidado" : p.estado === "devuelto" ? "Devuelto" : p.estado}</span>}
                  </span>
                </li>
              ))}
              {pagos.datos.length === 0 && <li className="px-5 py-8 text-center text-[14px] text-pizarra">Aún no hay pagos.</li>}
            </ul>
          )}
        </Panel>
      </div>

      <Panel titulo="Libro mayor" subtitulo="Últimos asientos: débitos a la izquierda, créditos a la derecha, siempre iguales" cuerpo="p-0">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[640px] text-[13px]">
            <thead className="bg-niebla/60 text-left text-xs text-pizarra">
              <tr><th className="px-5 py-2.5 font-semibold">#</th><th className="px-2 py-2.5 font-semibold">Asiento</th><th className="px-2 py-2.5 font-semibold">Débito</th><th className="px-2 py-2.5 font-semibold">Crédito</th><th className="px-5 py-2.5 text-right font-semibold">Monto</th></tr>
            </thead>
            <tbody className="divide-y divide-bruma">
              {d.asientos.slice(0, 18).map((a: any) => {
                const deb = a.movimientos.find((m: any) => m.debito > 0);
                const cre = a.movimientos.find((m: any) => m.credito > 0);
                return (
                  <tr key={a.id}>
                    <td className="px-5 py-2.5 font-mono text-pizarra">{a.id}</td>
                    <td className="max-w-[380px] px-2 py-2.5"><span className="block truncate">{a.descripcion}</span><span className="text-xs text-pizarra">{a.tipo} · {fecha(a.fecha)}</span></td>
                    <td className="px-2 py-2.5 font-medium">{deb?.cuenta}</td>
                    <td className="px-2 py-2.5 font-medium">{cre?.cuenta}</td>
                    <td className="px-5 py-2.5 text-right font-semibold num">{dinero(deb?.debito ?? 0)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </Panel>

      <Panel titulo="Rieles de pago" subtitulo="Valores de referencia del simulador: tiempos, comisiones y datos que exige cada riel">
        {!rieles.datos ? <Cargando /> : (
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
            {rieles.datos.map((r) => (
              <div key={r.codigo} className="rounded-[12px] border border-bruma p-4">
                <p className="text-[14px] font-bold">{r.nombre}</p>
                <p className="text-xs text-pizarra">{r.region} · {r.moneda}</p>
                <p className="mt-2 text-[13px]">{r.liquidacion}</p>
                <p className="mt-1 text-[13px] text-pizarra">Comisión simulada: {dinero(Number(r.comision))}{Number(r.spread) > 0 && ` + ${(Number(r.spread) * 100).toLocaleString("es-CO")} % de cambio`}</p>
                <p className="mt-2 text-xs text-pizarra">Exige: {r.requisitos}</p>
              </div>
            ))}
          </div>
        )}
      </Panel>

      <Modal abierto={fondear} titulo="Depositar en la cuenta operativa" onCerrar={() => setFondear(false)}>
        <Aviso tono="info" className="mb-4">Es un depósito simulado: solo crea un asiento en el libro mayor.</Aviso>
        <Campo etiqueta="Monto en USD"><input className={claseEntrada + " num"} inputMode="decimal" value={monto} onChange={(e) => setMonto(e.target.value)} /></Campo>
        <div className="mt-5 flex justify-end gap-2"><Boton onClick={() => setFondear(false)}>Cancelar</Boton><Boton variante="primario" onClick={hacerFondeo}>Depositar</Boton></div>
      </Modal>
    </div>
  );
}
