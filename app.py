# -*- coding: utf-8 -*-
"""
APP DE RADON PARA STREAMLIT - CON SLIDERS DIRECTOS
===================================================
"""

import os
import shutil
import sqlite3
import io
import re
from datetime import datetime
from PIL import Image, ImageDraw
import streamlit as st
import pandas as pd

# ============================================================
# CONFIGURACIÓN DE PÁGINA
# ============================================================

st.set_page_config(
    page_title="Detectores Rn",
    page_icon="📊",
    layout="wide"
)

# ============================================================
# BASE DE DATOS
# ============================================================

DB_NAME = "radon_data.db"

def get_data_dir():
    data_dir = os.path.join(os.path.expanduser("~"), "RadonApp")
    os.makedirs(data_dir, exist_ok=True)
    return data_dir

def get_db_path():
    return os.path.join(get_data_dir(), DB_NAME)

def init_db():
    conn = sqlite3.connect(get_db_path())
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS centros
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  nombre TEXT, zona TEXT, fecha_medicion TEXT, imagen_exterior_path TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS detectores
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  centro_id INTEGER,
                  planta TEXT, sala TEXT, fecha TEXT, detector_codigo TEXT,
                  plano_path TEXT, punto_x REAL, punto_y REAL,
                  foto_situacion_path TEXT, foto_detector_path TEXT,
                  fecha_creacion TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS settings
                 (id INTEGER PRIMARY KEY CHECK (id=1), tecnico TEXT)''')
    c.execute("INSERT OR IGNORE INTO settings (id, tecnico) VALUES (1, '')")
    conn.commit()
    conn.close()

def crear_centro(nombre):
    conn = sqlite3.connect(get_db_path())
    c = conn.cursor()
    c.execute("INSERT INTO centros (nombre, zona, fecha_medicion, imagen_exterior_path) VALUES (?, '', ?, NULL)",
              (nombre, datetime.now().strftime("%d/%m/%Y")))
    rowid = c.lastrowid
    conn.commit()
    conn.close()
    return rowid

def fetch_centros():
    conn = sqlite3.connect(get_db_path())
    c = conn.cursor()
    c.execute("SELECT id, nombre, zona, fecha_medicion, imagen_exterior_path FROM centros ORDER BY id DESC")
    rows = c.fetchall()
    conn.close()
    return rows

def get_centro(centro_id):
    conn = sqlite3.connect(get_db_path())
    c = conn.cursor()
    c.execute("SELECT id, nombre, zona, fecha_medicion, imagen_exterior_path FROM centros WHERE id=?", (centro_id,))
    row = c.fetchone()
    conn.close()
    return row

def update_centro(centro_id, nombre, zona, fecha, imagen_path):
    conn = sqlite3.connect(get_db_path())
    c = conn.cursor()
    c.execute("UPDATE centros SET nombre=?, zona=?, fecha_medicion=?, imagen_exterior_path=? WHERE id=?",
              (nombre, zona, fecha, imagen_path, centro_id))
    conn.commit()
    conn.close()

def delete_centro(centro_id):
    conn = sqlite3.connect(get_db_path())
    c = conn.cursor()
    c.execute("DELETE FROM detectores WHERE centro_id=?", (centro_id,))
    c.execute("DELETE FROM centros WHERE id=?", (centro_id,))
    conn.commit()
    conn.close()

def insert_detector(data):
    conn = sqlite3.connect(get_db_path())
    c = conn.cursor()
    c.execute('''INSERT INTO detectores
                 (centro_id, planta, sala, fecha, detector_codigo, plano_path,
                  punto_x, punto_y, foto_situacion_path, foto_detector_path, fecha_creacion)
                 VALUES (?,?,?,?,?,?,?,?,?,?,?)''', data)
    rowid = c.lastrowid
    conn.commit()
    conn.close()
    return rowid

def update_detector(detector_id, data):
    conn = sqlite3.connect(get_db_path())
    c = conn.cursor()
    c.execute('''UPDATE detectores SET
                 centro_id=?, planta=?, sala=?, fecha=?, detector_codigo=?, plano_path=?,
                 punto_x=?, punto_y=?, foto_situacion_path=?, foto_detector_path=?, fecha_creacion=?
                 WHERE id=?''', data + (detector_id,))
    conn.commit()
    conn.close()

def fetch_detectores(centro_id):
    conn = sqlite3.connect(get_db_path())
    c = conn.cursor()
    c.execute("SELECT * FROM detectores WHERE centro_id=? ORDER BY id ASC", (centro_id,))
    rows = c.fetchall()
    conn.close()
    return rows

def get_detector(detector_id):
    conn = sqlite3.connect(get_db_path())
    c = conn.cursor()
    c.execute("SELECT * FROM detectores WHERE id=?", (detector_id,))
    row = c.fetchone()
    conn.close()
    return row

def delete_detector(detector_id):
    conn = sqlite3.connect(get_db_path())
    c = conn.cursor()
    c.execute("DELETE FROM detectores WHERE id=?", (detector_id,))
    conn.commit()
    conn.close()

def get_tecnico():
    conn = sqlite3.connect(get_db_path())
    c = conn.cursor()
    c.execute("SELECT tecnico FROM settings WHERE id=1")
    row = c.fetchone()
    conn.close()
    return row[0] if row else ""

def set_tecnico(valor):
    conn = sqlite3.connect(get_db_path())
    c = conn.cursor()
    c.execute("UPDATE settings SET tecnico=? WHERE id=1", (valor,))
    conn.commit()
    conn.close()

def _slug(texto):
    texto = (texto or "centro").lower()
    texto = re.sub(r"[^a-z0-9]+", "_", texto).strip("_")
    return texto or "centro"

def guardar_imagen_subida(uploaded_file, prefijo):
    if uploaded_file is None:
        return None
    data_dir = get_data_dir()
    ext = os.path.splitext(uploaded_file.name)[1] or ".jpg"
    destino = os.path.join(data_dir, f"{prefijo}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}{ext}")
    with open(destino, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return destino

def mostrar_imagen(path, width=300):
    if path and os.path.exists(path):
        try:
            img = Image.open(path)
            st.image(img, width=width)
            return True
        except Exception:
            st.text("Error al cargar imagen")
            return False
    else:
        st.text("Sin imagen")
        return False

# ============================================================
# GENERAR PDF - SIN LOGO
# ============================================================

def generar_pdf(centro_id, output_path):
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import cm
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_CENTER
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
        from reportlab.lib import colors
        from reportlab.platypus import Image as RLImage
        from PIL import Image as PILImage, ImageDraw
        
        centro = get_centro(centro_id)
        if not centro:
            raise ValueError("Centro no encontrado")
        
        _, nombre, zona, fecha, img_ext = centro
        detectores = fetch_detectores(centro_id)
        tecnico = get_tecnico()
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        doc = SimpleDocTemplate(output_path, pagesize=A4,
                               leftMargin=2*cm, rightMargin=2*cm,
                               topMargin=2*cm, bottomMargin=2*cm)
        styles = getSampleStyleSheet()
        centrado = ParagraphStyle('Centrado', parent=styles['Normal'], alignment=TA_CENTER)
        nombre_style = ParagraphStyle('NombreCentro', parent=styles['Normal'],
                                       fontName='Helvetica-Bold', fontSize=20, leading=24,
                                       alignment=TA_CENTER, spaceAfter=4)
        zona_style = ParagraphStyle('ZonaCentro', parent=styles['Normal'],
                                     fontName='Helvetica', fontSize=20, leading=24,
                                     alignment=TA_CENTER, textColor=colors.HexColor('#444444'),
                                     spaceAfter=10)
        story = []
        
        story.append(Paragraph("Informe de colocación de detectores de Rn", styles["Title"]))
        story.append(Spacer(1, 0.6*cm))
        story.append(Paragraph(nombre or '-', nombre_style))
        if zona:
            story.append(Paragraph(zona, zona_style))
        story.append(Spacer(1, 0.3*cm))
        
        if img_ext and os.path.exists(img_ext):
            try:
                with PILImage.open(img_ext) as im_ext:
                    w, h = im_ext.size
                r = min(20*cm/w, 15*cm/h)
                img_portada = RLImage(img_ext, width=w*r, height=h*r)
                img_portada.hAlign = 'CENTER'
                story.append(img_portada)
                story.append(Spacer(1, 0.5*cm))
            except Exception:
                pass
        
        story.append(Paragraph(f"<b>Fecha:</b> {fecha or '-'}", centrado))
        if tecnico:
            story.append(Paragraph(f"<b>Técnico:</b> {tecnico}", centrado))
        story.append(Paragraph(f"<b>Detectores:</b> {len(detectores)}", centrado))
        story.append(Spacer(1, 0.5*cm))
        
        for idx, d in enumerate(detectores, 1):
            (did, _, planta, sala, fecha_det, codigo, plano, px, py, foto_sit, foto_det, _) = d
            story.append(PageBreak())
            
            titulo_partes = [codigo or "-", nombre or "-"]
            if zona:
                titulo_partes.append(zona)
            titulo_detector = f"Detector {idx}: " + " - ".join(titulo_partes)
            story.append(Paragraph(titulo_detector, styles["Heading2"]))
            
            tabla = Table([
                ["Planta", planta or "-"],
                ["Sala", sala or "-"],
                ["Código", codigo or "-"],
                ["Fecha", fecha_det or "-"],
            ], colWidths=[5*cm, 10*cm])
            tabla.setStyle(TableStyle([
                ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
                ("BACKGROUND", (0,0), (0,-1), colors.whitesmoke),
            ]))
            story.append(tabla)
            story.append(Spacer(1, 0.4*cm))
            
            if plano and os.path.exists(plano):
                story.append(Paragraph("Ubicación en el plano:", styles["Heading4"]))
                try:
                    with PILImage.open(plano) as im_plano:
                        im_plano = im_plano.convert("RGB")
                        w, h = im_plano.size
                        if px is not None and py is not None and px >= 0 and py >= 0:
                            draw = ImageDraw.Draw(im_plano)
                            cx, cy = px * w, py * h
                            r = max(6, int(min(w, h) * 0.012))
                            draw.ellipse([cx - r, cy - r, cx + r, cy + r],
                                         fill=(220, 20, 20), outline=(120, 0, 0), width=2)
                        tmp_plano_path = os.path.join(get_data_dir(), f"_tmp_plano_{did}.jpg")
                        im_plano.save(tmp_plano_path, quality=90)
                    r = min(14*cm/w, 9*cm/h)
                    story.append(RLImage(tmp_plano_path, width=w*r, height=h*r))
                    story.append(Spacer(1, 0.4*cm))
                except Exception:
                    pass
            
            if foto_sit and os.path.exists(foto_sit) and foto_det and os.path.exists(foto_det):
                story.append(Paragraph("Fotos:", styles["Heading4"]))
                try:
                    with PILImage.open(foto_sit) as im:
                        w, h = im.size
                    r = min(7*cm/w, 7*cm/h)
                    img1 = RLImage(foto_sit, width=w*r, height=h*r)
                except:
                    img1 = Paragraph("(no disponible)", styles["Normal"])
                try:
                    with PILImage.open(foto_det) as im:
                        w, h = im.size
                    r = min(7*cm/w, 7*cm/h)
                    img2 = RLImage(foto_det, width=w*r, height=h*r)
                except:
                    img2 = Paragraph("(no disponible)", styles["Normal"])
                story.append(Table([[img1, img2]], colWidths=[8*cm, 8*cm]))
        
        doc.build(story)
        return True
        
    except Exception as e:
        raise Exception(f"Error al generar PDF: {str(e)}")

# ============================================================
# FUNCIONES DE NAVEGACIÓN
# ============================================================

def init_session_state():
    if 'page' not in st.session_state:
        st.session_state.page = 'inicio'
    if 'centro_actual' not in st.session_state:
        st.session_state.centro_actual = None
    if 'detector_actual' not in st.session_state:
        st.session_state.detector_actual = None
    if 'selected_centro_id' not in st.session_state:
        st.session_state.selected_centro_id = None
    if 'editando_detector' not in st.session_state:
        st.session_state.editando_detector = False
    # Variables para el plano
    if 'punto_x' not in st.session_state:
        st.session_state.punto_x = -1
    if 'punto_y' not in st.session_state:
        st.session_state.punto_y = -1
    if 'plano_path' not in st.session_state:
        st.session_state.plano_path = None

# ============================================================
# FUNCIÓN PARA DIBUJAR PLANO CON PUNTO
# ============================================================

def dibujar_plano_con_punto(plano_path, punto_x, punto_y):
    """Dibuja el plano con el punto rojo en la posición indicada"""
    if not plano_path or not os.path.exists(plano_path):
        return None
    
    try:
        img = Image.open(plano_path)
        w, h = img.size
        
        if punto_x >= 0 and punto_y >= 0:
            draw = ImageDraw.Draw(img)
            cx, cy = punto_x * w, punto_y * h
            r = max(10, int(min(w, h) * 0.02))
            draw.ellipse([cx - r, cy - r, cx + r, cy + r],
                        fill=(255, 0, 0), outline=(200, 0, 0), width=3)
            draw.ellipse([cx - r - 6, cy - r - 6, cx + r + 6, cy + r + 6],
                        outline=(255, 100, 100), width=2)
        
        return img
    except Exception as e:
        st.error(f"Error al dibujar plano: {str(e)}")
        return None

# ============================================================
# PÁGINA DE INICIO
# ============================================================

def page_inicio():
    st.title("🏢 Centros Registrados")
    
    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
    with col1:
        centros = fetch_centros()
        nombres = [f"{c[1]} (ID: {c[0]})" if c[1] else f"Centro {c[0]}" for c in centros]
        if nombres:
            selected = st.selectbox("Seleccionar centro", nombres, key="select_centro")
            if selected:
                match = re.search(r"ID: (\d+)", selected)
                if match:
                    st.session_state.selected_centro_id = int(match.group(1))
    with col2:
        if st.button("📂 Abrir", use_container_width=True):
            if st.session_state.selected_centro_id:
                st.session_state.centro_actual = st.session_state.selected_centro_id
                st.session_state.page = 'centro'
                st.rerun()
    with col3:
        if st.button("➕ Nuevo", use_container_width=True):
            st.session_state.page = 'nuevo_centro'
            st.rerun()
    with col4:
        if st.button("⚙️ Ajustes", use_container_width=True):
            st.session_state.page = 'ajustes'
            st.rerun()
    
    if centros:
        data = []
        for c in centros:
            data.append({
                "ID": c[0],
                "Nombre": c[1] or "",
                "Zona": c[2] or "",
                "Fecha": c[3] or "",
            })
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        col1, col2 = st.columns([3, 1])
        with col2:
            if st.button("🗑️ Eliminar", use_container_width=True):
                if st.session_state.selected_centro_id:
                    if st.checkbox("Confirmar eliminación"):
                        delete_centro(st.session_state.selected_centro_id)
                        st.success("Centro eliminado")
                        st.rerun()
                else:
                    st.warning("Selecciona un centro")

# ============================================================
# PÁGINA DE NUEVO CENTRO
# ============================================================

def page_nuevo_centro():
    st.title("➕ Nuevo Centro")
    
    with st.form("nuevo_centro_form"):
        nombre = st.text_input("Nombre del centro *")
        zona = st.text_input("Zona")
        fecha = st.date_input("Fecha de medición", datetime.now())
        
        st.subheader("📷 Imagen exterior")
        
        uso_camara = st.checkbox("📸 Usar cámara", value=False)
        
        if uso_camara:
            foto_camara = st.camera_input("Tomar foto con la cámara")
            if foto_camara:
                st.image(foto_camara, width=300)
        else:
            imagen = st.file_uploader("Seleccionar imagen", type=['png', 'jpg', 'jpeg'])
            if imagen:
                st.image(imagen, width=300)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.form_submit_button("Crear Centro", use_container_width=True):
                if nombre and nombre.strip():
                    cid = crear_centro(nombre.strip())
                    
                    if uso_camara and 'foto_camara' in locals() and foto_camara:
                        img_path = guardar_imagen_subida(foto_camara, "centro_exterior")
                    elif not uso_camara and 'imagen' in locals() and imagen:
                        img_path = guardar_imagen_subida(imagen, "centro_exterior")
                    else:
                        img_path = None
                    
                    update_centro(cid, nombre.strip(), zona, fecha.strftime("%d/%m/%Y"), img_path)
                    st.session_state.centro_actual = cid
                    st.session_state.page = 'centro'
                    st.success("Centro creado")
                    st.rerun()
                else:
                    st.error("El nombre es obligatorio")
        with col2:
            if st.form_submit_button("Cancelar", use_container_width=True):
                st.session_state.page = 'inicio'
                st.rerun()

# ============================================================
# PÁGINA DE CENTRO
# ============================================================

def page_centro():
    centro = get_centro(st.session_state.centro_actual)
    if not centro:
        st.error("Centro no encontrado")
        st.session_state.page = 'inicio'
        st.rerun()
        return
    
    cid, nombre, zona, fecha, img_path = centro
    
    col1, col2 = st.columns([4, 1])
    with col1:
        st.title(f"🏢 {nombre}")
    with col2:
        if st.button("← Volver", use_container_width=True):
            st.session_state.page = 'inicio'
            st.rerun()
    
    with st.expander("📋 Datos del Centro", expanded=True):
        col1, col2 = st.columns([1, 1])
        with col1:
            st.text_input("Nombre", value=nombre, disabled=True)
            st.text_input("Zona", value=zona or "", disabled=True)
            st.text_input("Fecha", value=fecha or "", disabled=True)
        with col2:
            st.subheader("Imagen exterior")
            if img_path and os.path.exists(img_path):
                mostrar_imagen(img_path, width=300)
            else:
                st.text("Sin imagen")
    
    with st.expander("✏️ Editar Centro"):
        with st.form("editar_centro_form"):
            nuevo_nombre = st.text_input("Nombre", value=nombre)
            nueva_zona = st.text_input("Zona", value=zona or "")
            nueva_fecha = st.date_input("Fecha", 
                                       value=datetime.strptime(fecha, "%d/%m/%Y") if fecha else datetime.now())
            
            st.subheader("Cambiar imagen exterior")
            uso_camara_editar = st.checkbox("📸 Usar cámara", key="editar_camara")
            
            if uso_camara_editar:
                foto_camara_editar = st.camera_input("Tomar foto", key="editar_camara_input")
                if foto_camara_editar:
                    st.image(foto_camara_editar, width=300)
            else:
                nueva_imagen = st.file_uploader("Seleccionar imagen", type=['png', 'jpg', 'jpeg'], key="editar_imagen")
                if nueva_imagen:
                    st.image(nueva_imagen, width=300)
            
            if st.form_submit_button("Guardar Cambios"):
                if nuevo_nombre and nuevo_nombre.strip():
                    img_final = img_path
                    if uso_camara_editar and 'foto_camara_editar' in locals() and foto_camara_editar:
                        img_final = guardar_imagen_subida(foto_camara_editar, "centro_exterior")
                    elif not uso_camara_editar and 'nueva_imagen' in locals() and nueva_imagen:
                        img_final = guardar_imagen_subida(nueva_imagen, "centro_exterior")
                    update_centro(cid, nuevo_nombre.strip(), nueva_zona, 
                                 nueva_fecha.strftime("%d/%m/%Y"), img_final)
                    st.success("Centro actualizado")
                    st.rerun()
                else:
                    st.error("El nombre es obligatorio")
    
    st.subheader("📊 Detectores")
    
    detectores = fetch_detectores(cid)
    
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        if st.button("➕ Nuevo Detector", use_container_width=True):
            # Resetear estado del plano
            st.session_state.plano_path = None
            st.session_state.punto_x = -1
            st.session_state.punto_y = -1
            st.session_state.detector_actual = None
            st.session_state.editando_detector = False
            st.session_state.page = 'detector'
            st.rerun()
    with col2:
        if st.button("📄 Generar PDF", use_container_width=True):
            if detectores:
                try:
                    nombre_limpio = _slug(nombre)
                    pdf_path = os.path.join(
                        get_data_dir(), 
                        f"informe_{nombre_limpio}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
                    )
                    
                    with st.spinner("Generando PDF..."):
                        generar_pdf(cid, pdf_path)
                    
                    if os.path.exists(pdf_path):
                        st.success("✅ PDF generado correctamente")
                        with open(pdf_path, "rb") as f:
                            pdf_bytes = f.read()
                        st.download_button(
                            label="📥 Descargar PDF",
                            data=pdf_bytes,
                            file_name=os.path.basename(pdf_path),
                            mime="application/pdf",
                            use_container_width=True
                        )
                    else:
                        st.error("❌ Error: El PDF no se generó correctamente")
                        
                except Exception as e:
                    st.error(f"❌ Error al generar PDF: {str(e)}")
            else:
                st.warning("⚠️ No hay detectores para generar el informe")
    
    if detectores:
        data = []
        for d in detectores:
            data.append({
                "ID": d[0],
                "Planta": d[2] or "",
                "Sala": d[3] or "",
                "Código": d[5] or "",
                "Fecha": d[4] or "",
            })
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        detector_options = [f"{d[5]} - {d[3]} (ID: {d[0]})" for d in detectores]
        if detector_options:
            selected = st.selectbox("Seleccionar detector", detector_options, key="select_detector")
            if selected:
                match = re.search(r"ID: (\d+)", selected)
                if match:
                    st.session_state.detector_actual = int(match.group(1))
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✏️ Editar", use_container_width=True):
                if st.session_state.detector_actual:
                    d = get_detector(st.session_state.detector_actual)
                    if d:
                        st.session_state.plano_path = d[6]
                        st.session_state.punto_x = d[7] if d[7] is not None and d[7] >= 0 else -1
                        st.session_state.punto_y = d[8] if d[8] is not None and d[8] >= 0 else -1
                    st.session_state.editando_detector = True
                    st.session_state.page = 'detector'
                    st.rerun()
                else:
                    st.warning("Selecciona un detector")
        with col2:
            if st.button("🗑️ Eliminar", use_container_width=True):
                if st.session_state.detector_actual:
                    delete_detector(st.session_state.detector_actual)
                    st.success("Detector eliminado")
                    st.rerun()
                else:
                    st.warning("Selecciona un detector")
    else:
        st.info("No hay detectores registrados en este centro.")

# ============================================================
# PÁGINA DE DETECTOR CON SLIDERS - SIMPLIFICADA
# ============================================================

def page_detector():
    st.title("📌 Detector")
    
    # Obtener datos del detector si estamos editando
    if st.session_state.detector_actual and st.session_state.editando_detector:
        d = get_detector(st.session_state.detector_actual)
        if d:
            (did, _, planta, sala, fecha, codigo, plano, px, py, foto_sit, foto_det, _) = d
            es_edicion = True
            if st.session_state.plano_path is None:
                st.session_state.plano_path = plano
            if st.session_state.punto_x == -1:
                st.session_state.punto_x = px if px is not None and px >= 0 else -1
            if st.session_state.punto_y == -1:
                st.session_state.punto_y = py if py is not None and py >= 0 else -1
        else:
            st.error("Detector no encontrado")
            st.session_state.page = 'centro'
            st.rerun()
            return
    else:
        centro = get_centro(st.session_state.centro_actual)
        planta = sala = codigo = ""
        fecha = centro[3] if centro else datetime.now().strftime("%d/%m/%Y")
        foto_sit = None
        foto_det = None
        es_edicion = False
        if st.session_state.plano_path is None:
            st.session_state.plano_path = None
        if st.session_state.punto_x == -1:
            st.session_state.punto_x = -1
        if st.session_state.punto_y == -1:
            st.session_state.punto_y = -1
    
    st.subheader("Editar Detector" if es_edicion else "Nuevo Detector")
    
    # --- PLANO (fuera del formulario) ---
    st.subheader("📐 Plano y Ubicación")
    st.caption("🖱️ **Arrastra los sliders** para mover el punto rojo en el plano")
    
    # Subir nuevo plano
    plano_file = st.file_uploader("Subir plano", type=['png', 'jpg', 'jpeg'], key="plano_upload")
    if plano_file:
        # Guardar el plano
        plano_path = guardar_imagen_subida(plano_file, "plano")
        st.session_state.plano_path = plano_path
        st.success("✅ Plano subido correctamente")
        st.rerun()
    
    # Verificar si hay un plano
    plano_actual = st.session_state.plano_path
    
    if plano_actual and os.path.exists(plano_actual):
        # Mostrar el plano con el punto rojo (o sin él)
        img_con_punto = dibujar_plano_con_punto(
            plano_actual, 
            st.session_state.punto_x, 
            st.session_state.punto_y
        )
        if img_con_punto:
            st.image(img_con_punto, caption="📍 Arrastra los sliders para mover el punto rojo", use_container_width=True)
        
        # --- SLIDERS - DIRECTAMENTE EN LA PÁGINA ---
        st.subheader("🎯 Ajustar posición del punto")
        
        # Valores por defecto
        valor_x = st.session_state.punto_x if st.session_state.punto_x >= 0 else 0.5
        valor_y = st.session_state.punto_y if st.session_state.punto_y >= 0 else 0.5
        
        col1, col2 = st.columns(2)
        with col1:
            nuevo_x = st.slider(
                "Posición X (izquierda → derecha)", 
                0.0, 1.0, valor_x, 0.01,
                key="slider_x"
            )
        with col2:
            nuevo_y = st.slider(
                "Posición Y (arriba → abajo)", 
                0.0, 1.0, valor_y, 0.01,
                key="slider_y"
            )
        
        # Actualizar el punto en session_state
        st.session_state.punto_x = nuevo_x
        st.session_state.punto_y = nuevo_y
        
        # Mostrar coordenadas y botones de ayuda
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("📍 X", f"{nuevo_x:.3f}")
        with col2:
            st.metric("📍 Y", f"{nuevo_y:.3f}")
        with col3:
            if st.button("🎯 Centrar"):
                st.session_state.punto_x = 0.5
                st.session_state.punto_y = 0.5
                st.rerun()
        with col4:
            if st.button("🗑️ Quitar punto"):
                st.session_state.punto_x = -1
                st.session_state.punto_y = -1
                st.rerun()
        
        # Botón para eliminar plano
        if st.button("🗑️ Eliminar plano", key="delete_plano"):
            # Eliminar el archivo físico
            if st.session_state.plano_path and os.path.exists(st.session_state.plano_path):
                try:
                    os.remove(st.session_state.plano_path)
                except:
                    pass
            st.session_state.plano_path = None
            st.session_state.punto_x = -1
            st.session_state.punto_y = -1
            st.rerun()
    
    else:
        st.info("📋 Sube un plano para poder marcar la ubicación del detector")
    
    st.divider()
    
    # --- FORMULARIO PRINCIPAL ---
    with st.form("detector_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            planta_input = st.text_input("Planta", value=planta if 'planta' in locals() else "")
            sala_input = st.text_input("Sala *", value=sala if 'sala' in locals() else "")
            fecha_input = st.date_input(
                "Fecha", 
                value=datetime.strptime(fecha, "%d/%m/%Y") if fecha else datetime.now()
            )
            codigo_input = st.text_input("Código *", value=codigo if 'codigo' in locals() else "")
        
        with col2:
            st.subheader("📷 Foto de Situación")
            uso_camara_sit = st.checkbox("📸 Usar cámara", key="camara_sit")
            
            if uso_camara_sit:
                foto_sit_camara = st.camera_input("Tomar foto", key="camara_sit_input")
                if foto_sit_camara:
                    st.image(foto_sit_camara, width=200)
            else:
                foto_sit_file = st.file_uploader("Subir foto", type=['png', 'jpg', 'jpeg'], key="foto_sit")
                if foto_sit_file:
                    st.image(foto_sit_file, width=200)
                elif 'foto_sit' in locals() and foto_sit and os.path.exists(foto_sit):
                    st.caption("Actual:")
                    mostrar_imagen(foto_sit, width=150)
            
            st.subheader("📷 Foto del Detector")
            uso_camara_det = st.checkbox("📸 Usar cámara", key="camara_det")
            
            if uso_camara_det:
                foto_det_camara = st.camera_input("Tomar foto", key="camara_det_input")
                if foto_det_camara:
                    st.image(foto_det_camara, width=200)
            else:
                foto_det_file = st.file_uploader("Subir foto", type=['png', 'jpg', 'jpeg'], key="foto_det")
                if foto_det_file:
                    st.image(foto_det_file, width=200)
                elif 'foto_det' in locals() and foto_det and os.path.exists(foto_det):
                    st.caption("Actual:")
                    mostrar_imagen(foto_det, width=150)
        
        # Mostrar coordenadas actuales dentro del formulario
        st.divider()
        col1, col2 = st.columns(2)
        with col1:
            if st.session_state.punto_x >= 0:
                st.info(f"📍 Posición X seleccionada: **{st.session_state.punto_x:.3f}**")
            else:
                st.warning("⚠️ Sin ubicación seleccionada en el plano")
        with col2:
            if st.session_state.punto_y >= 0:
                st.info(f"📍 Posición Y seleccionada: **{st.session_state.punto_y:.3f}**")
            else:
                st.warning("⚠️ Sin ubicación seleccionada en el plano")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.form_submit_button("💾 Guardar Detector", use_container_width=True):
                if not sala_input.strip():
                    st.error("La sala es obligatoria")
                elif not codigo_input.strip():
                    st.error("El código es obligatorio")
                else:
                    sit_final = None
                    det_final = None
                    plano_final = st.session_state.plano_path
                    
                    # Foto situación
                    if uso_camara_sit and 'foto_sit_camara' in locals() and foto_sit_camara:
                        sit_final = guardar_imagen_subida(foto_sit_camara, "foto_situacion")
                    elif not uso_camara_sit and 'foto_sit_file' in locals() and foto_sit_file:
                        sit_final = guardar_imagen_subida(foto_sit_file, "foto_situacion")
                    elif 'foto_sit' in locals() and foto_sit and isinstance(foto_sit, str) and os.path.exists(foto_sit):
                        sit_final = foto_sit
                    
                    # Foto detector
                    if uso_camara_det and 'foto_det_camara' in locals() and foto_det_camara:
                        det_final = guardar_imagen_subida(foto_det_camara, "foto_detector")
                    elif not uso_camara_det and 'foto_det_file' in locals() and foto_det_file:
                        det_final = guardar_imagen_subida(foto_det_file, "foto_detector")
                    elif 'foto_det' in locals() and foto_det and isinstance(foto_det, str) and os.path.exists(foto_det):
                        det_final = foto_det
                    
                    data = (
                        st.session_state.centro_actual,
                        planta_input.strip(),
                        sala_input.strip(),
                        fecha_input.strftime("%d/%m/%Y"),
                        codigo_input.strip(),
                        plano_final,
                        st.session_state.punto_x,
                        st.session_state.punto_y,
                        sit_final,
                        det_final,
                        datetime.now().strftime("%Y-%m-%d %H:%M")
                    )
                    
                    if es_edicion:
                        update_detector(st.session_state.detector_actual, data)
                        st.success("Detector actualizado")
                    else:
                        insert_detector(data)
                        st.success("Detector creado")
                    
                    # Limpiar estado del plano
                    st.session_state.plano_path = None
                    st.session_state.punto_x = -1
                    st.session_state.punto_y = -1
                    
                    st.session_state.page = 'centro'
                    st.rerun()
        with col2:
            if st.form_submit_button("Cancelar", use_container_width=True):
                st.session_state.plano_path = None
                st.session_state.punto_x = -1
                st.session_state.punto_y = -1
                st.session_state.page = 'centro'
                st.rerun()

# ============================================================
# PÁGINA DE AJUSTES
# ============================================================

def page_ajustes():
    st.title("⚙️ Ajustes")
    
    tecnico_actual = get_tecnico()
    
    with st.form("ajustes_form"):
        tecnico = st.text_input("Técnico / Empresa (aparece en el PDF)", value=tecnico_actual)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.form_submit_button("Guardar", use_container_width=True):
                set_tecnico(tecnico.strip())
                st.success("Configuración guardada")
                st.rerun()
        with col2:
            if st.form_submit_button("Volver", use_container_width=True):
                st.session_state.page = 'inicio'
                st.rerun()

# ============================================================
# MAIN
# ============================================================

def main():
    init_db()
    init_session_state()
    
    if st.session_state.page == 'inicio':
        page_inicio()
    elif st.session_state.page == 'nuevo_centro':
        page_nuevo_centro()
    elif st.session_state.page == 'centro':
        page_centro()
    elif st.session_state.page == 'detector':
        page_detector()
    elif st.session_state.page == 'ajustes':
        page_ajustes()
    else:
        st.session_state.page = 'inicio'
        st.rerun()

if __name__ == "__main__":
    main()