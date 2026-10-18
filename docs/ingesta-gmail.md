# Escucha de Gmail para Kauta

El servidor consulta cada 60 segundos la bandeja de `felipearango306@gmail.com` con
`in:inbox subject:kauta`. No depende del navegador ni de que esta conversación siga
abierta. Solo lee mensajes: no envía correos, no los marca como leídos y no los archiva.
El asunto puede ser `kauta` o contener esa palabra, sin distinguir mayúsculas.
El filtro acepta `kauta`, `Kauta`, `KAUTA` y combinaciones de mayúsculas; `kauda` queda fuera.

## Activar la cuenta

La conexión Gmail de este chat no entrega su credencial al servidor. El remoto
`gdrive:` de rclone tiene permiso de Drive, que tampoco habilita Gmail.
Hace falta un cliente OAuth propio con **Gmail API habilitada** y el permiso
`https://www.googleapis.com/auth/gmail.readonly`.

1. En Google Cloud, habilitar Gmail API y crear un cliente OAuth de tipo
   **Aplicación de escritorio**. Si la aplicación está en pruebas, añadir la cuenta
   destinataria como usuario de prueba. Descargar el JSON del cliente y guardarlo
   fuera del repositorio. Los permisos de prueba de Google pueden expirar; revisar
   el estado de publicación de la aplicación para una operación sostenida.
2. En el equipo donde se abrirá el navegador, ejecutar:

   ```bash
   python3 kauta/scripts/conectar_gmail.py --cliente /ruta/privada/oauth-client.json --destino /ruta/privada/gmail-oauth.json
   ```

   El script usa callback local, `state` y PKCE, pide solo lectura y verifica que
   la cuenta sea `felipearango306@gmail.com`. No imprime tokens. Si se ejecuta en
   un servidor remoto, hace falta un túnel SSH local para su puerto 8765, o bien
   autorizar en el equipo local y copiar el JSON resultante de forma privada.
3. Configurar el proceso del servidor:

   ```dotenv
   KAUTA_GMAIL_ACTIVO=1
   KAUTA_GMAIL_CUENTA=felipearango306@gmail.com
   KAUTA_GMAIL_CREDENCIALES=/root/.config/kauta/gmail-oauth.json
   KAUTA_GMAIL_INTERVALO=60
   ```

   Guardar la credencial con permisos `600` y reiniciar el servidor con esas
   variables. Si el archivo aparece posteriormente en la ruta configurada, el
   siguiente ciclo intenta conectarse sin necesitar otro reinicio.
4. Abrir **Facturas → Recepción por Gmail**. Solo aparece **Escuchando** tras
   verificar la cuenta y completar una consulta real. Una conexión sin respuestas
   exitosas recientes deja de mostrarse como activa.

Por defecto recibe mensajes desde la primera ejecución del recolector. Para
recuperar correos anteriores, establecer `KAUTA_GMAIL_DESDE` en ISO UTC **antes de
la primera ejecución**. La fecha queda guardada en la base de datos. Se usa la
fecha interna de recepción de Gmail, no la fecha declarada por el remitente.

## Qué ocurre con cada correo

- Guarda el `.eml` completo fuera de la carpeta pública, con su huella SHA-256,
  identificador de Gmail, asunto, remitente y fecha. No sigue enlaces del correo.
- Lee los adjuntos compatibles: PDF, imágenes, XML fiscal, ZIP, texto y EML.
  Un mensaje puede contener varias facturas. PDF y XML con el mismo nombre base
  se agrupan: se procesa el XML y se conserva el PDF de soporte. Otros pares de
  formatos pasan por los controles de duplicados del motor.
- Si no hay adjuntos, intenta leer la cuenta de cobro en el cuerpo del correo.
- Cada documento pasa por el extractor real y las reglas vigentes del agente.
  El nombre de un archivo enviado por correo nunca habilita una extracción
  ficticia de referencia. Los pagos del entorno de hackathon siguen simulados.
- Los formatos no compatibles y los archivos demasiado grandes quedan para
  revisión. Límite del correo: 25 MB; límite de cada documento: 10 MB. Para un
  correo que supera 25 MB se conserva un registro de recepción, sin descargarlo.
- Un error de extracción aparece en la recepción, sin crear una decisión de
  pago. La vista CTO puede reintentar después de corregir la disponibilidad del
  lector. No se repite automáticamente una llamada de IA fallida en cada ciclo.

La combinación cuenta + identificador Gmail evita volver a ingerir un mensaje.
La huella del documento detecta archivos idénticos. Los controles financieros
del motor siguen detectando duplicados por número de factura, proveedor o
identificador fiscal. El enlace al documento, la factura, la decisión y su
auditoría se confirman en una única transacción: un fallo o reinicio no produce
una segunda decisión para el mismo documento.

La consulta admite paginación y recupera una ventana de dos días desde la última
consulta completa, sin avanzar el cursor si falla la sincronización. No se usa
`is:unread`: leer el correo en Gmail no impide recibirlo. Los correos archivados
antes de la consulta no entran, porque el alcance solicitado es la bandeja.

El despliegue actual usa un proceso de servidor. Un candado de archivo evita
que dos procesos en el mismo host ejecuten el recolector simultáneamente. Para
varias réplicas en hosts distintos se requiere un worker único o un candado
distribuido. Restablecer la demo conserva los registros de recepción para no
volver a procesar correos; los enlaces a facturas eliminadas quedan vacíos.

## Eliminar documentos de recepción

En **Facturas → Ver recepción**, la vista CTO ofrece **Eliminar de recepción**
en cada documento. Se pide confirmación antes de quitarlo. La acción queda
registrada en auditoría y el registro de Gmail se conserva para que ese mismo
correo no lo vuelva a importar. La factura vinculada, sus decisiones y sus
pagos se conservan. La acción no modifica Gmail.

## Verificación

Enviar desde una cuenta de prueba una factura **ficticia** con asunto
`kauta · prueba de recepción`. En un ciclo debe aparecer en la recepción con
su resultado o error explicable. Volver a consultar no debe crear otra factura;
reenviar el mismo adjunto debe quedar como duplicado. Un mensaje con otro
asunto queda fuera de esta fuente.

Pruebas automatizadas, sin acceso a Gmail ni a la base de la demo:

```bash
cd kauta
python -m pytest tests/test_ingesta.py
```

Documentación oficial: [Listado y paginación de mensajes](https://developers.google.com/workspace/gmail/api/guides/list-messages),
[autorización permanente del servidor](https://developers.google.com/workspace/gmail/api/auth/web-server),
[permisos de Gmail](https://developers.google.com/workspace/gmail/api/auth/scopes).
