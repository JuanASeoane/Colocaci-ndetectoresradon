# Detectores de Radón — versión Streamlit

Migración de la app de escritorio (Tkinter + OpenCV) a una app web con
Streamlit. Conserva **todas** las funciones originales:

- Alta, edición y borrado de **Centros** (nombre, zona, fecha, imagen exterior).
- Alta, edición y borrado de **Detectores** por centro (planta, sala, fecha, código).
- **Plano con marcador de posición**: subes o fotografías el plano y tocas
  sobre él para marcar dónde está el detector (punto rojo, igual que en la
  app de Windows).
- **Fotos "lado a lado"** (situación y detector), con opción de subir
  archivo o hacer la foto con la cámara.
- **Ajustes** (técnico/empresa que aparece en el PDF).
- **Generación del informe PDF**, con el mismo diseño, logotipo, tablas,
  plano con el punto marcado y fotos que la versión de escritorio.
- **Nuevo:** botón "📲 Enviar por WhatsApp" tras generar el PDF, que abre
  el panel nativo de compartir de Android con el PDF ya adjunto.

## 1. Instalación

```bash
pip install -r requirements.txt
```

## 2. Ejecutar en local

```bash
streamlit run app.py
```

Se abrirá en `http://localhost:8501`. Los datos (base de datos SQLite e
imágenes) se guardan en una carpeta `RadonApp_data/` junto al script.

## 3. Cámara

La cámara ya **no usa OpenCV/`cv2.VideoCapture`** (eso abría una ventana
de escritorio, que no existe en un navegador). En su lugar se usa
`st.camera_input`, que pide permiso al navegador y abre la cámara nativa
del dispositivo — funciona igual en un PC con webcam que en el móvil.

## 4. Marcar el punto en el plano

Se usa el componente `streamlit-image-coordinates`, que captura el clic o
el toque sobre la imagen del plano y calcula la posición relativa (igual
que hacía el `Canvas` de Tkinter). Si ese paquete no está instalado, la
app sigue funcionando pero sin la posibilidad de marcar el punto (se
avisa en pantalla).

## 5. Enviar el PDF por WhatsApp desde Android

El botón "Enviar por WhatsApp" usa la **Web Share API** del navegador
(`navigator.share` con archivos adjuntos). Esto abre el panel nativo de
"Compartir" de Android, donde eliges WhatsApp (o cualquier otra app).

**Requisito importante:** los navegadores solo permiten esta función en un
*contexto seguro*, es decir:

- `https://...` (cualquier despliegue con certificado válido), o
- `http://localhost` (solo en el propio PC, no sirve para el móvil).

Si accedes desde el móvil a la IP local de tu PC
(`http://192.168.x.x:8501`) el navegador **bloqueará** la función por no
ser HTTPS, y solo podrás descargar el PDF y compartirlo manualmente.
Para tenerlo funcionando desde el móvil tienes dos opciones sencillas:

1. **Desplegar la app en Streamlit Community Cloud** (gratis, HTTPS
   automático): sube este proyecto a un repositorio de GitHub y
   despliega desde https://share.streamlit.io.
2. **Túnel HTTPS temporal** desde tu PC, por ejemplo con
   [Cloudflare Tunnel](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/do-more-with-tunnels/trycloudflare/)
   o `ngrok`:
   ```bash
   cloudflared tunnel --url http://localhost:8501
   ```
   y abres desde el móvil la URL `https://algo.trycloudflare.com` que te da.

Si el navegador del móvil no soporta adjuntar archivos con la Web Share
API, la app te avisa y siempre tienes disponible el botón
"⬇️ Descargar PDF" para compartirlo manualmente desde la app de archivos
o desde WhatsApp.

## 6. Dónde se guardan los datos

Por defecto, en una carpeta `RadonApp_data/` junto al script (útil para
que funcione igual en local, en un servidor propio o en Streamlit Cloud).
Si prefieres el comportamiento de la app de Windows (guardar en el
perfil del usuario), edita la función `get_data_dir()` al principio de
`app.py`:

```python
data_dir = os.path.join(os.path.expanduser("~"), "RadonApp")
```

⚠️ Nota sobre Streamlit Community Cloud: el almacenamiento no es
persistente entre reinicios/despliegues (se borra el disco). Para uso
en producción real con datos que deban conservarse, lo recomendable es
desplegar en un servidor propio (VPS, Docker, etc.) con disco persistente.
