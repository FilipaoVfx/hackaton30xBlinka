import { useEffect, useRef, useState } from "react";
import { Mail, RefreshCw, Trash2 } from "lucide-react";
import { api, avisarCambio, fecha, puede, type Usuario } from "../api";
import { Aviso, Boton, Modal, useToast } from "../ui";

type Fuente = {
  estado: string; cuenta: string; asunto: string; intervalo_segundos: number;
  desde: string | null; ultimo_exito: string | null; error: string | null;
  documentos: Record<string, number>;
};
type Documento = {
  id: number; nombre: string; estado: string; motivo: string; factura_id: string | null;
  asunto: string; remitente: string; recibida_en: string;
};
const ESTADOS: Record<string, string> = {
  escuchando: "Escuchando", requiere_autorizacion: "Falta conectar Gmail", desactivada: "Escucha desactivada",
  error: "Conexión interrumpida", sin_senal: "Esperando conexión",
};
const DOCUMENTOS: Record<string, string> = {
  recibido: "En cola", procesado: "Procesado", duplicado: "Duplicado", error_lectura: "Error de lectura",
  revision: "Requiere revisión", soporte: "Documento de soporte",
};

export default function BandejaCorreo({ usuario }: { usuario: Usuario }) {
  const [fuente, setFuente] = useState<Fuente | null>(null);
  const [docs, setDocs] = useState<Documento[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [cargando, setCargando] = useState(true);
  const activo = useRef(false);
  const consulta = useRef(0);
  const enVuelo = useRef(0);
  const [abierto, setAbierto] = useState(false);
  const [ocupado, setOcupado] = useState<number | null>(null);
  const [porEliminar, setPorEliminar] = useState<Documento | null>(null);
  const [eliminando, setEliminando] = useState(false);
  const [errorEliminar, setErrorEliminar] = useState<string | null>(null);
  const toast = useToast();
  const ultima = useRef<string | null>(null);

  const cargar = async () => {
    if (!activo.current) return;
    const version = ++consulta.current;
    enVuelo.current++;
    setCargando(true);
    try {
      const [f, d] = await Promise.all([api<Fuente>("/correo/estado"), api<Documento[]>("/correo/documentos")]);
      if (!activo.current || version !== consulta.current) return;
      setFuente(f); setDocs(d); setError(null);
      const firma = JSON.stringify(d.map(x => [x.id, x.estado, x.factura_id]));
      if (ultima.current && firma !== ultima.current) avisarCambio();
      ultima.current = firma;
    } catch (e) { if (activo.current && version === consulta.current) setError((e as Error).message); }
    finally { enVuelo.current--; if (activo.current && version === consulta.current) setCargando(false); }
  };
  useEffect(() => {
    activo.current = true;
    // La consulta al buzón la hace el servidor aunque esta pantalla esté cerrada.
    cargar();
    const t = window.setInterval(() => { if (activo.current && !document.hidden && enVuelo.current === 0) cargar(); }, 15000);
    return () => { activo.current = false; consulta.current++; window.clearInterval(t); };
  }, []);

  const reintentar = async (id: number) => {
    consulta.current++; setCargando(false);
    setOcupado(id);
    try {
      await api(`/correo/documentos/${id}/reintentar`, { cuerpo: {} });
      await cargar(); avisarCambio();
    } catch (e) { setError((e as Error).message); }
    finally { setOcupado(null); }
  };
  const pendientes = (fuente?.documentos.error_lectura ?? 0) + (fuente?.documentos.revision ?? 0);
  const eliminar = async () => {
    if (!porEliminar) return;
    consulta.current++; setCargando(false);
    setEliminando(true); setErrorEliminar(null);
    try {
      await api(`/correo/documentos/${porEliminar.id}`, { metodo: "DELETE" });
      setDocs(actuales => actuales.filter(d => d.id !== porEliminar.id));
      setPorEliminar(null);
      toast("Documento eliminado de recepción", "exito");
      await cargar(); avisarCambio();
    } catch (e) { setErrorEliminar((e as Error).message); }
    finally { setEliminando(false); }
  };

  return <section aria-label="Recepción automática de correo" className="mb-5 overflow-hidden rounded-[14px] border border-bruma bg-white">
    <div className="grid grid-cols-[20px_minmax(0,1fr)] items-center gap-x-3 gap-y-2 px-5 py-4 sm:grid-cols-[20px_minmax(0,1fr)_auto]">
      <Mail className="h-5 w-5 shrink-0 text-azul" />
      <div className="min-w-0 flex-1">
        <p className="text-sm font-semibold">Recepción por Gmail <span className={`block sm:ml-2 sm:inline ${fuente?.estado === "escuchando" ? "text-menta-t" : "text-ambar-t"}`}>{fuente ? ESTADOS[fuente.estado] : "Consultando estado…"}</span></p>
        {fuente && <p className="mt-1 break-words text-xs text-pizarra">{fuente.cuenta} · Asunto: «{fuente.asunto}» · Consulta cada {fuente.intervalo_segundos} s · Última conexión: {fuente.ultimo_exito ? fecha(fuente.ultimo_exito) : "pendiente"}</p>}
      </div>
      <button onClick={() => setAbierto(!abierto)} aria-expanded={abierto} className="col-start-2 min-h-11 justify-self-start text-sm font-semibold text-azul sm:col-start-auto">{abierto ? "Ocultar recepción" : `Ver recepción${pendientes ? ` · ${pendientes} por revisar` : ""}`}</button>
    </div>
    {error && <div className="px-5 pb-4"><Aviso tono="error">{error}<button className="ml-2 underline" onClick={cargar}>Reintentar</button></Aviso></div>}
    {fuente?.estado === "requiere_autorizacion" && <p className="border-t border-bruma px-5 py-3 text-sm text-pizarra">Falta autorizar esta cuenta de Gmail para el servidor. La conexión de Drive no incluye el acceso al correo.</p>}
    {fuente?.error && fuente.estado !== "requiere_autorizacion" && <p role="status" className="border-t border-bruma px-5 py-3 text-sm text-coral">{fuente.error}</p>}
    {abierto && <div className="border-t border-bruma px-5 py-4">
      <p className="mb-3 text-xs text-pizarra">{fuente?.desde && `Desde ${fecha(fuente.desde)} · `}Conserva el original y sus adjuntos. Los errores de lectura requieren revisión antes de decidir un pago.</p>
      {!docs.length ? <p className="py-4 text-sm text-pizarra" role="status">{error ? "No se pudo cargar la recepción. Reintenta la consulta." : cargando ? "Cargando recepción…" : "No hay documentos en recepción."}</p> : <ul className="divide-y divide-bruma">{docs.map(d => <li key={d.id} className="flex flex-wrap items-center gap-3 py-3">
        <div className="min-w-0 flex-1"><p className="break-words text-sm font-semibold">{d.nombre}</p><p className="break-words text-xs text-pizarra">{d.asunto} · {d.remitente}</p><p className="mt-1 text-xs text-pizarra">{d.motivo}</p></div>
        <span className="text-xs font-semibold">{DOCUMENTOS[d.estado] ?? d.estado}</span>
        {d.factura_id && <a className="min-h-11 content-center text-sm font-semibold text-azul" href={`#/facturas/${d.factura_id}`}>Ver {d.factura_id}</a>}
        {d.estado === "error_lectura" && puede(usuario, "facturas.cargar") && <Boton cargando={ocupado === d.id} onClick={() => reintentar(d.id)} icono={<RefreshCw className="h-3 w-3" />}>Reintentar lectura</Boton>}
        {puede(usuario, "facturas.cargar") && <Boton variante="peligro" disabled={ocupado === d.id} onClick={() => { setErrorEliminar(null); setPorEliminar(d); }} icono={<Trash2 className="h-4 w-4" />} aria-label={`Eliminar de recepción: ${d.nombre}`}>Eliminar de recepción</Boton>}
      </li>)}</ul>}
    </div>}
    <Modal abierto={porEliminar !== null} titulo="Eliminar de recepción" onCerrar={() => { if (!eliminando) setPorEliminar(null); }}>
      <p className="break-words text-sm font-semibold">{porEliminar?.nombre}</p>
      <p className="mt-3 text-sm text-pizarra">Este documento se quitará de la recepción de Kauta y no reaparecerá al sincronizar el mismo correo. El correo original permanece en Gmail.</p>
      {porEliminar?.factura_id && <p className="mt-3 text-sm text-pizarra">La factura {porEliminar.factura_id}, sus decisiones y su historial financiero se conservan.</p>}
      {errorEliminar && <Aviso tono="error" className="mt-4">{errorEliminar}</Aviso>}
      <div className="mt-5 flex flex-wrap justify-end gap-3">
        <Boton disabled={eliminando} onClick={() => setPorEliminar(null)}>Cancelar</Boton>
        <Boton variante="peligro" cargando={eliminando} onClick={eliminar} icono={<Trash2 className="h-4 w-4" />}>Eliminar de recepción</Boton>
      </div>
    </Modal>
  </section>;
}
