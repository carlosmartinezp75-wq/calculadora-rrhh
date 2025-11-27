import streamlit as st
import pandas as pd
import requests
import base64
import os
import io
import zipfile
import tempfile
from datetime import datetime, date

# --- 0. VALIDACIÓN DE LIBRERÍAS ---
try:
    from fpdf import FPDF
    from docx import Document
    from docx.shared import Pt
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    LIBRARIES_OK = True
except ImportError:
    LIBRARIES_OK = False

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="HR Suite Ultimate V34", page_icon="🏢", layout="wide")

# Inicialización de Estado
if 'empresa' not in st.session_state:
    st.session_state.empresa = {
        "nombre": "", "rut": "", "direccion": "", 
        "rep_nombre": "", "rep_rut": "", "ciudad": "Santiago", "giro": "Servicios"
    }

# --- 2. ESTILOS VISUALES ---
def cargar_estilos():
    nombres = ['fondo.png', 'fondo.jpg', 'fondo_marca.png']
    img = next((n for n in nombres if os.path.exists(n)), None)
    
    css_fondo = ""
    if img:
        try:
            with open(img, "rb") as f: b64 = base64.b64encode(f.read()).decode()
            css_fondo = f"""[data-testid="stAppViewContainer"] {{background-image: url("data:image/png;base64,{b64}"); background-size: cover;}}"""
        except: pass
    else:
        css_fondo = """[data-testid="stAppViewContainer"] {background: linear-gradient(135deg, #fdfbfb 0%, #ebedee 100%);}"""

    st.markdown(f"""
        <style>
        {css_fondo}
        .block-container {{background-color: rgba(255, 255, 255, 0.98); padding: 2rem; border-radius: 15px; box-shadow: 0 10px 40px rgba(0,0,0,0.1);}}
        h1, h2, h3 {{color: #004a99 !important; font-family: 'Segoe UI', sans-serif; font-weight: 800;}}
        .stButton>button {{background-color: #004a99 !important; color: white !important; font-weight: bold; border-radius: 8px; width: 100%; height: 3rem;}}
        .stButton>button:hover {{background-color: #003366 !important;}}
        .success-box {{padding:15px; background-color:#d4edda; color:#155724; border-radius:5px; margin-bottom:10px;}}
        .error-box {{padding:15px; background-color:#f8d7da; color:#721c24; border-radius:5px; margin-bottom:10px;}}
        </style>
        """, unsafe_allow_html=True)

cargar_estilos()

# --- 3. FUNCIONES UTILITARIAS ---
def fmt(valor): 
    if pd.isna(valor) or valor == "": return "$0"
    try: return "${:,.0f}".format(float(valor)).replace(",", ".")
    except: return str(valor)

def obtener_indicadores():
    # Valores fijos Nov 2025 para estabilidad
    return 39643.59, 69542.0

# --- 4. MOTOR GENERADOR DE DOCUMENTOS (WORD) ---
def crear_documento_word(tipo_doc, datos_fila, empresa_data):
    doc = Document()
    style = doc.styles['Normal']
    style.font.name = 'Arial'
    style.font.size = Pt(11)
    
    fecha_hoy = datetime.now().strftime("%d de %B de %Y")
    
    # Encabezado General
    t = doc.add_heading(f'{tipo_doc.upper()}', 0)
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.add_paragraph(f"Fecha: {fecha_hoy}").alignment = WD_ALIGN_PARAGRAPH.RIGHT
    
    # Extracción segura de datos (Evita KeyError)
    def get_val(key, default="________________"):
        # Busca la key en el excel ignorando mayúsculas
        key_lower = key.lower()
        for col in datos_fila.index:
            if key_lower in col.lower():
                val = datos_fila[col]
                return str(val) if pd.notna(val) else default
        return default

    # Datos básicos
    trab_nombre = get_val("nombre")
    trab_rut = get_val("rut")
    trab_cargo = get_val("cargo")
    
    # INTRODUCCIÓN ESTÁNDAR
    intro = f"""En {empresa_data['ciudad']}, a {fecha_hoy}, la empresa "{empresa_data['nombre']}", RUT {empresa_data['rut']}, representada por {empresa_data['rep_nombre']}, en adelante el EMPLEADOR, y don/ña {trab_nombre}, RUT {trab_rut}, en adelante el TRABAJADOR, proceden a emitir el presente documento:"""
    doc.add_paragraph(intro)
    
    # LÓGICA SEGÚN TIPO DE DOCUMENTO
    if "CONTRATO" in tipo_doc.upper():
        sueldo = get_val("sueldo", "0")
        try: sueldo_fmt = fmt(float(sueldo))
        except: sueldo_fmt = sueldo
        
        clausulas = [
            ("PRIMERO:", f"El Trabajador prestará servicios como {trab_cargo}."),
            ("SEGUNDO:", f"Sueldo Base Mensual: {sueldo_fmt}. Gratificación Legal: Tope 4.75 IMM."),
            ("TERCERO:", "Jornada de 44 horas semanales distribuidas de lunes a viernes."),
            ("CUARTO:", "El presente contrato es de plazo indefinido/fijo según corresponda.")
        ]
        for k, v in clausulas:
            p = doc.add_paragraph(); p.add_run(k).bold=True; p.add_run(f" {v}")
            
    elif "AMONESTACION" in tipo_doc.upper():
        hechos = get_val("hechos", "Incumplimiento de obligaciones contractuales.")
        texto = f"Por medio de la presente, se amonesta al trabajador por los siguientes hechos: {hechos}. Esta conducta infringe el Reglamento Interno de Orden, Higiene y Seguridad."
        doc.add_paragraph(texto)
        
    elif "FINIQUITO" in tipo_doc.upper():
        causal = get_val("causal", "Necesidades de la Empresa")
        monto = get_val("total_finiquito", "0")
        try: monto_fmt = fmt(float(monto))
        except: monto_fmt = monto
        
        texto = f"Las partes ponen término al contrato de trabajo por la causal de {causal}. El empleador paga en este acto la suma única y total de {monto_fmt}, que el trabajador recibe a su entera satisfacción."
        doc.add_paragraph(texto)
    
    # FIRMAS
    doc.add_paragraph("\n\n\n")
    table = doc.add_table(rows=1, cols=2)
    table.cell(0,0).text = "_____________________\nEMPLEADOR"
    table.cell(0,1).text = "_____________________\nTRABAJADOR"
    
    # Guardar en memoria
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# --- 5. LOGICA DE PROCESAMIENTO MASIVO ---
def procesar_lote_excel(df, empresa_data):
    zip_buffer = io.BytesIO()
    reporte_errores = []
    procesados = 0
    
    with zipfile.ZipFile(zip_buffer, "w") as zf:
        for index, row in df.iterrows():
            try:
                # Detectar tipo documento
                tipo_bruto = str(row.get('TIPO_DOCUMENTO', 'Contrato')).upper()
                nombre_trab = str(row.get('NOMBRE_TRABAJADOR', f'Trabajador_{index}'))
                
                # Generar DOCX
                docx_buffer = crear_documento_word(tipo_bruto, row, empresa_data)
                
                # Nombre archivo limpio
                filename = f"{tipo_bruto}_{nombre_trab}.docx".replace(" ", "_")
                
                # Agregar al ZIP
                zf.writestr(filename, docx_buffer.getvalue())
                procesados += 1
                
            except Exception as e:
                reporte_errores.append(f"Fila {index+2}: {str(e)}")
    
    zip_buffer.seek(0)
    return zip_buffer, procesados, reporte_errores

# --- 6. CÁLCULO INDIVIDUAL (Simulador) ---
def calcular_individual(liq, col, mov, con, afp, sal, plan):
    # Motor simple para la vista rápida
    uf, utm = obtener_indicadores()
    base_aprox = liq * 0.8
    grat = min(base_aprox * 0.25, 209395) # Tope Nov 2025
    imp = base_aprox + grat
    costo = imp * 1.05 # Aprox costo empresa
    return {"Base": int(base_aprox), "Grat": int(grat), "Liq": int(liq), "Costo": int(costo)}

# --- 7. INTERFAZ GRÁFICA ---

# SIDEBAR: DATOS EMPRESA OBLIGATORIOS
with st.sidebar:
    st.image("https://www.previred.com/wp-content/uploads/2021/01/logo-previred.png", width=120)
    st.header("Datos de la Empresa")
    st.info("Complete estos datos para que aparezcan en los documentos generados.")
    
    st.session_state.empresa['rut'] = st.text_input("RUT Empresa", st.session_state.empresa['rut'])
    st.session_state.empresa['nombre'] = st.text_input("Razón Social", st.session_state.empresa['nombre'])
    st.session_state.empresa['rep_nombre'] = st.text_input("Representante Legal", st.session_state.empresa['rep_nombre'])
    st.session_state.empresa['direccion'] = st.text_input("Dirección", st.session_state.empresa['direccion'])
    st.session_state.empresa['ciudad'] = st.text_input("Ciudad", st.session_state.empresa['ciudad'])

st.title("HR Suite Enterprise V34")
st.markdown("**Sistema de Gestión Masiva de Documentos y Cálculo de Remuneraciones**")

tabs = st.tabs(["📂 Carga Masiva (Excel)", "💰 Calculadora Rápida", "📜 Documento Individual"])

# --- TAB 1: CARGA MASIVA (NUEVO CORE) ---
with tabs[0]:
    st.header("Generación Masiva de Documentos")
    st.markdown("""
    **Instrucciones:**
    1. Suba su archivo Excel con la nómina.
    2. Asegúrese de tener columnas como: `TIPO_DOCUMENTO`, `NOMBRE_TRABAJADOR`, `RUT`, `SUELDO`, `CARGO`.
    3. El sistema generará automáticamente los contratos, cartas o finiquitos según corresponda.
    """)
    
    uploaded_file = st.file_uploader("Subir Excel (.xlsx)", type="xlsx")
    
    if uploaded_file:
        try:
            df = pd.read_excel(uploaded_file)
            st.dataframe(df.head())
            st.caption(f"Se detectaron {len(df)} registros para procesar.")
            
            if st.session_state.empresa['rut'] == "":
                st.warning("⚠️ Por favor, complete los datos de la EMPRESA en el menú lateral antes de procesar.")
            else:
                if st.button("🚀 PROCESAR LOTE Y GENERAR ZIP"):
                    with st.spinner("Generando documentos legales..."):
                        zip_data, count, errors = procesar_lote_excel(df, st.session_state.empresa)
                        
                        st.success(f"✅ Se generaron correctamente {count} documentos.")
                        if errors:
                            st.error(f"Hubo errores en {len(errors)} filas:")
                            for e in errors: st.write(e)
                        
                        st.download_button(
                            label="⬇️ DESCARGAR TODOS LOS DOCUMENTOS (.ZIP)",
                            data=zip_data,
                            file_name="Documentacion_RRHH_Masiva.zip",
                            mime="application/zip"
                        )
        except Exception as e:
            st.error(f"Error al leer el Excel: {e}")

# --- TAB 2: CALCULADORA INDIVIDUAL ---
with tabs[1]:
    st.header("Simulador de Sueldo")
    c1, c2 = st.columns(2)
    l = c1.number_input("Líquido ($)", 1000000, step=50000)
    col = c1.number_input("Colación", 50000)
    
    if st.button("Calcular"):
        r = calcular_individual(l, col, 0, "", "", "", 0)
        st.metric("Sueldo Base", fmt(r['Base']))
        st.metric("Costo Empresa", fmt(r['Costo']))

# --- TAB 3: DOCUMENTO INDIVIDUAL ---
with tabs[2]:
    st.header("Generador Manual")
    tipo = st.selectbox("Tipo", ["Contrato", "Amonestación", "Finiquito"])
    nombre = st.text_input("Nombre Trabajador")
    rut = st.text_input("RUT Trabajador")
    
    if st.button("Generar Documento"):
        if st.session_state.empresa['rut']:
            # Creamos una "fila falsa" para usar la misma función del masivo
            dummy_row = pd.Series({"nombre": nombre, "rut": rut, "cargo": "Trabajador", "sueldo": 500000})
            docx = crear_documento_word(tipo, dummy_row, st.session_state.empresa)
            st.download_button("Descargar .docx", docx, f"{tipo}_{nombre}.docx")
        else:
            st.error("Faltan datos de empresa en el menú lateral.")
