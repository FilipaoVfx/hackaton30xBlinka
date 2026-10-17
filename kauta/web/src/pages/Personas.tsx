import { useState } from "react";
import { Ban, CircleCheck, Copy, KeyRound, LockOpen, ShieldCheck, UserPlus, Users } from "lucide-react";
import { api, fecha, puede, useApi, type Usuario } from "../api";
import { Aviso, Boton, Campo, Cargando, claseEntrada, cx, Dato, Encabezado, Hash, Modal, Panel, useToast, Vacio } from "../ui";

type Persona = {
  id: number; correo: string; nombre: string; cargo: string; rol: string; rol_nombre: string; rol_descripcion: string;
  activo: boolean; mfa_activo: boolean; creado_en: string | null; ultimo_acceso: string | null; bloqueado: boolean;
  intentos_fallidos: number; facturas_cargadas: number; firmas: number; sesiones_abiertas: number;
};
type Invitacion = {
  id: number; correo: string; nombre: string; cargo: string; rol: string; rol_nombre: string; prefijo: string;
  estado: "pendiente" | "usada" | "revocada" | "vencida"; creada_por: string; creada_en: string | null;
  expira_en: string | null; usada_en: string | null; intentos: number;
};
type Rol = { id: string; nombre: string; descripcion: string; permisos: string[]; personas: number };
type Datos = { usuarios: Persona[]; invitaciones: Invitacion[]; roles: Rol[]; dias_invitacion: number;
  politica_contrasena: { largo_minimo: number; texto: string } };

const COLOR_ROL: Record<string, string> = {
  admin: "bg-noche text-white", aprobador: "bg-menta-s text-menta-t", tesoreria: "bg-azul-s text-azul-t",
  analista: "bg-niebla text-pizarra", auditor: "bg-ambar-s text-ambar-t", jurado: "bg-coral-s text-coral-t",
};
const ESTADO_INV: Record<string, [string, string]> = {
  pendiente: ["Pendiente", "bg-ambar-s text-ambar-t"], usada: ["Usada", "bg-menta-s text-menta-t"],
  revocada: ["Revocada", "bg-niebla text-pizarra"], vencida: ["Vencida", "bg-coral-s text-coral-t"],
};

export function Etiqueta({ texto, clase }: { texto: string; clase: string }) {
  return <span className={cx("inline-flex shrink-0 items-center rounded-full px-2.5 py-0.5 text-[12px] font-bold", clase)}>{texto}</span>;
}

export default function Personas({ usuario }: { usuario: Usuario }) {
  const d = useApi<Datos>("/personas");
  const toast = useToast();
  const gestiona = puede(usuario, "usuarios.gestionar");
  const [invitando, setInvitando] = useState(false);
  const [codigo, setCodigo] = useState<{ inv: Invitacion; codigo: string } | null>(null);

  const accion = async (ruta: string, metodo: string, cuerpo?: unknown, mensaje?: string) => {
    try {
      await api(ruta, { metodo, cuerpo });
      toast(mensaje ?? "Listo");
      d.recargar();
    } catch (e) {
      toast((e as Error).message, "error");
    }
  };

  if (!d.datos) return <Cargando filas={6} />;
  const pendientes = d.datos.invitaciones.filter((i) => i.estado === "pendiente");

  return (
    <div className="space-y-6">
      <Encabezado titulo="Personas y roles"
        texto="Quién entra a Kauta, con qué rol y qué puede hacer. Las cuentas se crean por invitación: nadie se da de alta solo ni elige su propio rol."
        accion={gestiona && <Boton variante="primario" icono={<UserPlus className="h-4 w-4" />} onClick={() => setInvitando(true)}>Invitar persona</Boton>} />

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {d.datos.roles.map((r) => (
          <div key={r.id} className="rounded-[16px] border border-bruma bg-white p-4">
            <div className="flex items-center justify-between gap-2">
              <Etiqueta texto={r.nombre} clase={COLOR_ROL[r.id] ?? "bg-niebla text-pizarra"} />
              <span className="num text-[20px] font-extrabold">{r.personas}</span>
            </div>
            <p className="mt-2 text-[13px] leading-relaxed text-pizarra">{r.descripcion}</p>
            <ul className="mt-3 space-y-1">
              {r.permisos.map((x) => (
                <li key={x} className="flex gap-1.5 text-[12.5px] leading-snug text-pizarra"><CircleCheck className="mt-[2px] h-3.5 w-3.5 shrink-0 text-menta-t" />{x}</li>
              ))}
            </ul>
          </div>
        ))}
      </div>

      <Panel titulo={`Cuentas (${d.datos.usuarios.length})`} subtitulo="Rol, estado y actividad de cada persona" cuerpo="p-0">
        <ul className="divide-y divide-bruma">
          {d.datos.usuarios.map((u) => (
            <li key={u.id} className="flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:gap-4">
              <div className="flex min-w-0 flex-1 items-start gap-3">
                <span className="grid h-10 w-10 shrink-0 place-items-center rounded-full bg-noche text-[13px] font-bold text-white">
                  {u.nombre.split(" ").slice(0, 2).map((x) => x[0]).join("")}
                </span>
                <div className="min-w-0">
                  <p className="truncate text-[15px] font-semibold">
                    {u.nombre}
                    {u.id === usuario.id && <span className="ml-2 text-[12px] font-normal text-pizarra">(usted)</span>}
                  </p>
                  <p className="truncate text-[13px] text-pizarra">{u.cargo} · {u.correo}</p>
                  <p className="mt-1 text-[12px] text-pizarra/90">
                    {u.ultimo_acceso ? `Último acceso ${fecha(u.ultimo_acceso)}` : "Nunca ha entrado"}
                    {u.sesiones_abiertas > 0 && ` · ${u.sesiones_abiertas} sesión${u.sesiones_abiertas > 1 ? "es" : ""} abierta${u.sesiones_abiertas > 1 ? "s" : ""}`}
                    {u.facturas_cargadas > 0 && ` · ${u.facturas_cargadas} facturas cargadas`}
                    {u.firmas > 0 && ` · ${u.firmas} firmas`}
                  </p>
                </div>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                {u.mfa_activo && <Etiqueta texto="2FA" clase="bg-menta-s text-menta-t" />}
                {u.bloqueado && <Etiqueta texto="Bloqueada" clase="bg-coral-s text-coral-t" />}
                {!u.activo && <Etiqueta texto="Inactiva" clase="bg-niebla text-pizarra" />}
                {gestiona && u.id !== usuario.id ? (
                  <select className={claseEntrada + " h-9 w-auto min-h-9 py-1 text-[13px]"} value={u.rol} aria-label={`Rol de ${u.nombre}`}
                    onChange={(e) => accion(`/personas/${u.id}/rol`, "PUT", { rol: e.target.value }, `${u.nombre}: rol actualizado`)}>
                    {d.datos!.roles.map((r) => <option key={r.id} value={r.id}>{r.nombre}</option>)}
                  </select>
                ) : <Etiqueta texto={u.rol_nombre} clase={COLOR_ROL[u.rol] ?? "bg-niebla text-pizarra"} />}
                {gestiona && u.bloqueado && (
                  <Boton icono={<LockOpen className="h-4 w-4" />} onClick={() => accion(`/personas/${u.id}/desbloquear`, "POST", {}, "Cuenta desbloqueada")}>Desbloquear</Boton>
                )}
                {gestiona && u.id !== usuario.id && (
                  <Boton icono={u.activo ? <Ban className="h-4 w-4" /> : <CircleCheck className="h-4 w-4" />}
                    onClick={() => accion(`/personas/${u.id}/activo`, "PUT", { activo: !u.activo },
                      u.activo ? `${u.nombre}: cuenta desactivada y sesiones cerradas` : `${u.nombre}: cuenta activada`)}>
                    {u.activo ? "Desactivar" : "Activar"}
                  </Boton>
                )}
              </div>
            </li>
          ))}
        </ul>
      </Panel>

      <Panel titulo="Invitaciones" subtitulo={`El código sirve una sola vez y caduca a los ${d.datos.dias_invitacion} días`} cuerpo="p-0">
        {d.datos.invitaciones.length === 0 ? (
          <div className="p-5"><Vacio titulo="Todavía no hay invitaciones" texto="Cuando invite a alguien, aquí verá el estado de su código." /></div>
        ) : (
          <ul className="divide-y divide-bruma">
            {d.datos.invitaciones.map((i) => (
              <li key={i.id} className="flex flex-col gap-2 p-4 sm:flex-row sm:items-center sm:gap-4">
                <div className="min-w-0 flex-1">
                  <p className="truncate text-[14px] font-semibold">{i.nombre} · {i.correo}</p>
                  <p className="text-[13px] text-pizarra">
                    {i.rol_nombre} · código {i.prefijo}··· · invitó {i.creada_por}
                    {i.estado === "pendiente" && i.expira_en && ` · vence ${fecha(i.expira_en, false)}`}
                    {i.estado === "usada" && i.usada_en && ` · usada ${fecha(i.usada_en)}`}
                    {i.intentos > 0 && ` · ${i.intentos} intentos fallidos`}
                  </p>
                </div>
                <Etiqueta texto={ESTADO_INV[i.estado][0]} clase={ESTADO_INV[i.estado][1]} />
                {gestiona && i.estado === "pendiente" && (
                  <Boton onClick={() => accion(`/personas/invitaciones/${i.id}`, "DELETE", undefined, "Invitación revocada")}>Revocar</Boton>
                )}
              </li>
            ))}
          </ul>
        )}
      </Panel>

      <Panel titulo="Cómo entra una persona nueva" subtitulo="Lo mismo que vería alguien de su empresa el primer día">
        <ol className="space-y-3 text-[14px] leading-relaxed">
          {[["Administración la invita", "Define correo, nombre, cargo y rol. Kauta genera un código de un solo uso."],
            ["Se le entrega el código", "Por un canal distinto al correo de la invitación: una llamada o un chat interno."],
            ["La persona crea su cuenta", `En «Crear cuenta» escribe el código y elige su contraseña (mínimo ${d.datos.politica_contrasena.largo_minimo} caracteres). El rol ya viene dado.`],
            ["Entra con su rol", "Puede activar el segundo factor desde «Seguridad». Todo queda en la auditoría."]].map(([t, x], n) => (
            <li key={t} className="flex gap-3">
              <span className="grid h-6 w-6 shrink-0 place-items-center rounded-full bg-azul text-[12px] font-bold text-white">{n + 1}</span>
              <span><b>{t}.</b> {x}</span>
            </li>
          ))}
        </ol>
        <p className="mt-4 flex gap-2 text-[13px] text-pizarra"><ShieldCheck className="h-4 w-4 shrink-0 text-menta-t" />{d.datos.politica_contrasena.texto} Del código solo se guarda su hash, igual que de una contraseña.</p>
      </Panel>

      {pendientes.length > 0 && gestiona && (
        <Aviso tono="info"><b>{pendientes.length} invitación{pendientes.length > 1 ? "es" : ""} sin usar.</b> Si alguien no la necesita, revóquela: una invitación abierta es una puerta abierta.</Aviso>
      )}

      <Invitar abierto={invitando} roles={d.datos.roles} onCerrar={() => setInvitando(false)}
        alCrear={(r) => { setInvitando(false); setCodigo(r); d.recargar(); }} />
      <Modal abierto={!!codigo} titulo="Código de invitación" onCerrar={() => setCodigo(null)}>
        {codigo && (
          <div className="space-y-4">
            <p className="text-[14px] leading-relaxed">
              Entréguele este código a <b>{codigo.inv.nombre}</b> ({codigo.inv.correo}). Entrará con el rol <b>{codigo.inv.rol_nombre}</b>.
            </p>
            <div className="rounded-[12px] border border-bruma bg-niebla p-4 text-center">
              <p className="font-mono text-[22px] font-bold tracking-[0.14em] text-noche">{codigo.codigo}</p>
              <button type="button" className="mt-2 inline-flex items-center gap-1.5 text-[13px] font-semibold text-azul"
                onClick={() => { navigator.clipboard?.writeText(codigo.codigo); toast("Código copiado", "info"); }}>
                <Copy className="h-3.5 w-3.5" />Copiar
              </button>
            </div>
            <Aviso tono="alerta">No se vuelve a mostrar: de aquí en adelante solo queda guardado su hash. Si se pierde, revoque la invitación y haga otra.</Aviso>
            <Boton variante="primario" className="w-full" onClick={() => setCodigo(null)}>Entendido</Boton>
          </div>
        )}
      </Modal>
    </div>
  );
}

function Invitar({ abierto, roles, onCerrar, alCrear }: {
  abierto: boolean; roles: Rol[]; onCerrar: () => void; alCrear: (r: { inv: Invitacion; codigo: string }) => void;
}) {
  const [correo, setCorreo] = useState("");
  const [nombre, setNombre] = useState("");
  const [cargo, setCargo] = useState("");
  const [rol, setRol] = useState("analista");
  const [error, setError] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);
  const elegido = roles.find((r) => r.id === rol);

  const enviar = async () => {
    setEnviando(true);
    setError(null);
    try {
      const r = await api<any>("/personas/invitar", { cuerpo: { correo, nombre, cargo, rol } });
      alCrear({ inv: r.invitacion, codigo: r.codigo });
      setCorreo(""); setNombre(""); setCargo(""); setRol("analista");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setEnviando(false);
    }
  };

  return (
    <Modal abierto={abierto} titulo="Invitar a una persona" onCerrar={onCerrar}>
      <form className="space-y-4" onSubmit={(e) => { e.preventDefault(); enviar(); }}>
        <Campo etiqueta="Nombre y apellido">
          <input className={claseEntrada} value={nombre} onChange={(e) => setNombre(e.target.value)} required />
        </Campo>
        <Campo etiqueta="Correo de la empresa">
          <input className={claseEntrada} type="email" value={correo} onChange={(e) => setCorreo(e.target.value)} required />
        </Campo>
        <Campo etiqueta="Cargo">
          <input className={claseEntrada} value={cargo} onChange={(e) => setCargo(e.target.value)} placeholder="Analista de cuentas por pagar" />
        </Campo>
        <Campo etiqueta="Rol" ayuda={elegido?.descripcion}>
          <select className={claseEntrada} value={rol} onChange={(e) => setRol(e.target.value)}>
            {roles.map((r) => <option key={r.id} value={r.id}>{r.nombre}</option>)}
          </select>
        </Campo>
        {elegido && (
          <div className="rounded-[12px] bg-niebla p-3 text-[13px] text-pizarra">
            <p className="flex gap-2"><Users className="h-4 w-4 shrink-0" />Podrá: {elegido.permisos.join(" · ").toLowerCase()}</p>
          </div>
        )}
        {error && <Aviso tono="error">{error}</Aviso>}
        <div className="flex flex-col gap-2 sm:flex-row sm:justify-end">
          <Boton type="button" onClick={onCerrar}>Cancelar</Boton>
          <Boton variante="primario" type="submit" cargando={enviando} icono={<KeyRound className="h-4 w-4" />}>Generar código</Boton>
        </div>
      </form>
    </Modal>
  );
}
