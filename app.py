import streamlit as st
import pandas as pd
import requests
import base64
import os
import io
import zipfile
import tempfile
import random
from datetime import datetime, date, timedelta
import plotly.graph_objects as go
import plotly.express as px

# =============================================================================
# 0. VALIDACIÓN DE LIBRERÍAS Y ENTORNO
# =============================================================================
try:
    import pdfplumber
    from fpdf import FPDF
    from docx import Document
    from docx.shared import Pt, Inches, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    LIBRARIES_OK = True
except ImportError:
    LIBRARIES_OK = False

# =============================================================================
# 1. CONFIGURACIÓN DEL SISTEMA
# =============================================================================
st.set_page_config(
    page_title="HR Suite Ultimate V36",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inicialización de Estado (Persistencia de Datos de Sesión)
if 'empresa' not in st.session_state:
    st.session_state.empresa = {
        "nombre": "", "rut": "", "direccion": "", 
        "rep_nombre": "", "rep_rut": "", "ciudad": "Santiago", "giro": "Servicios"
    }
if 'trabajador' not in st.session_state:
    st.session_state.trabajador = {
        "nombre": "", "rut": "", "direccion": "", 
        "nacionalidad": "Chilena", "civil": "Soltero", "nacimiento": date(1990,1,1)
    }
if 'calculo_actual' not in st.session_state: st.session_state.calculo_actual = None
if 'perfil_actual' not in st.session_state: st.session_state.perfil_actual = None
if 'logo_bytes' not in st.session_state: st.session_state.logo_bytes = None

# =============================================================================
# 2. SISTEMA DE DISEÑO VISUAL (CSS AVANZADO)
# =============================================================================
def cargar_estilos_corporativos():
    """Carga los estilos CSS y el fondo de pantalla."""
    nombres = ['fondo.png', 'fondo.jpg', 'fondo_marca.png']
    img = next((n for n in nombres if os.path.exists(n)), None)
    
    css_fondo = ""
    if img:
        try:
            with open(img, "rb") as f: b64 = base64.b64encode(f.read()).decode()
            css_fondo = f"""
            [data-testid="stAppViewContainer"] {{
                background-image: url("data:image/png;base64,{b64}");
                background-size: cover;
                background-position: center;
                background-attachment: fixed;
            }}
            """
        except: pass
    else:
        css_fondo = """[data-testid="stAppViewContainer"] {background: linear-gradient(135deg, #fdfbfb 0%, #ebedee 100%);}"""

    st.markdown(f"""
        <style>
        {css_fondo}
        
        .block-container {{
            background-color: rgba(255, 255, 255, 0.98); 
            padding: 2.5rem; 
            border-radius: 16px; 
            box-shadow: 0 10px 40px rgba(0,0,0,0.15);
        }}
        
        h1, h2, h3, h4 {{color: #004a99 !important; font-family: 'Segoe UI', sans-serif; font-weight: 800;}}
        p, label, li, span {{color: #003366 !important; font-weight: 500;}}
        
        /* Botones Principales */
        .stButton>button {{
            background-color: #004a99 !important;
            color: white !important;
            font-weight: bold;
            border-radius: 8px;
            width: 100%;
            height: 3.5rem;
            text-transform: uppercase;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            transition: all 0.3s ease;
        }}
        .stButton>button:hover {{
            background-color: #003366 !important;
            transform: translateY(-2px);
            box-shadow: 0 6px 12px rgba(0,0,0,0.2);
        }}
        
        /* Visualización Liquidación */
        .liq-box {{
            border: 1px solid #ccc; padding: 25px; background: #fff; font-family: 'Courier New', monospace;
            box-shadow: 5px 5px 15px rgba(0,0,0,0.05); margin-top: 20px;
        }}
        .liq-header {{text-align: center; border-bottom: 2px solid #000; padding-bottom: 10px; margin-bottom: 15px; font-weight: bold;}}
        .liq-row {{display: flex; justify-content: space-between; border-bottom: 1px dashed #ddd; padding: 4px 0;}}
        .liq-total {{background: #e3f2fd; padding: 15px; font-weight: bold; font-size: 1.3em; border: 2px solid #004a99; margin-top: 20px; color: #004a99; text-align: right;}}
        
        .miles-feedback {{font-size: 0.8rem; color: #2e7d32; font-weight: bold; margin-top: -10px;}}
        
        /* Ocultar elementos nativos */
        #MainMenu, footer {{visibility: hidden;}}
        </style>
        """, unsafe_allow_html=True)

cargar_estilos_corporativos()

# =============================================================================
# 3. FUNCIONES UTILITARIAS Y DATA
# =============================================================================

def fmt(valor):
    """Formatea números como moneda CLP ($1.000.000)"""
    if valor is None or pd.isna(valor): return "$0"
    try: return "${:,.0f}".format(float(valor)).replace(",", ".")
    except: return str(valor)

def mostrar_miles(valor): 
    """Muestra feedback visual debajo del input numérico"""
    if valor > 0: st.markdown(f'<p class="miles-feedback">✅ Ingresaste: {fmt(valor)}</p>', unsafe_allow_html=True)

def obtener_indicadores():
    """Obtiene UF/UTM de la API o usa valores de respaldo"""
    def_uf, def_utm = 39643.59, 69542.0
    try:
        r = requests.get('https://mindicador.cl/api', timeout=2)
        d = r.json()
        return float(d['uf']['valor']), float(d['utm']['valor'])
    except: return def_uf, def_utm

# =============================================================================
# 4. GENERADORES DE ARCHIVOS (EXCEL / PDF / WORD)
# =============================================================================

def generar_plantilla_excel():
    """Genera el archivo Excel base para la carga masiva."""
    df = pd.DataFrame(columns=[
        "TIPO_DOCUMENTO", "NOMBRE_TRABAJADOR", "RUT_TRABAJADOR", "CARGO", 
        "SUELDO_BASE", "FECHA_INICIO", "EMAIL"
    ])
    # Agregamos una fila de ejemplo
    df.loc[0] = ["Contrato", "Juan Perez", "12.345.678-9", "Analista", 800000, "2025-01-01", "juan@empresa.com"]
    
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Plantilla_Carga')
    buffer.seek(0)
    return buffer

def generar_pdf_liquidacion(res, empresa, trabajador):
    if not LIBRARIES_OK: return None
    pdf = FPDF()
    pdf.add_page()
    
    # Logo
    if st.session_state.logo_bytes:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
            tmp.write(st.session_state.logo_bytes)
            tmp_path = tmp.name
        try: pdf.image(tmp_path, 10, 8, 30)
        except: pass

    pdf.set_font("Arial", 'B', 14); pdf.cell(0, 15, "LIQUIDACION DE SUELDO", 0, 1, 'C')
    pdf.ln(10)
    
    # Datos
    pdf.set_font("Arial", '', 10)
    pdf.cell(0, 6, f"Empresa: {empresa.get('nombre','S/N')} | RUT: {empresa.get('rut','S/R')}", 0, 1)
    pdf.cell(0, 6, f"Trabajador: {trabajador.get('nombre','S/N')} | RUT: {trabajador.get('rut','S/R')}", 0, 1)
    pdf.cell(0, 6, f"Fecha: {datetime.now().strftime('%d/%m/%Y')}", 0, 1)
    pdf.ln(5)
    
    # Tabla
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(95, 8, "HABERES", 1, 0, 'C', 1); pdf.cell(95, 8, "DESCUENTOS", 1, 1, 'C', 1)
    pdf.set_font("Arial", '', 10)
    
    items_h = [("Base", res['Sueldo Base']), ("Gratificacion", res['Gratificación']), ("No Imponibles", res['No Imponibles'])]
    items_d = [("AFP", res['AFP']), ("Salud", res['Salud_Total']), ("Cesantia", res['AFC']), ("Impuesto", res['Impuesto'])]
    
    for i in range(max(len(items_h), len(items_d))):
        ht, hv = items_h[i] if i < len(items_h) else ("", "")
        dt, dv = items_d[i] if i < len(items_d) else ("", "")
        pdf.cell(60, 6, ht, 'L'); pdf.cell(35, 6, fmt(hv) if hv!="" else "", 'R')
        pdf.cell(60, 6, dt, 'L'); pdf.cell(35, 6, fmt(dv) if dv!="" else "", 'R', 1)
    
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(130, 10, "A PAGAR:", 1, 0, 'R'); pdf.cell(60, 10, fmt(res['LÍQUIDO_FINAL']), 1, 1, 'C')
    
    return pdf.output(dest='S').encode('latin-1')

def crear_documento_word(tipo_doc, datos, empresa):
    """Generador universal de documentos Word."""
    doc = Document()
    style = doc.styles['Normal']; style.font.name = 'Arial'; style.font.size = Pt(11)
    fecha = datetime.now().strftime("%d de %B de %Y")
    
    doc.add_heading(tipo_doc.upper(), 0).alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.add_paragraph(f"Fecha: {fecha}").alignment = WD_ALIGN_PARAGRAPH.RIGHT
    
    # Extracción segura de datos
    t_nom = str(datos.get('NOMBRE_TRABAJADOR', datos.get('nombre', '________')))
    t_rut = str(datos.get('RUT_TRABAJADOR', datos.get('rut', '________')))
    t_cargo = str(datos.get('CARGO', datos.get('cargo', '________')))
    
    intro = f"""En {empresa.get('ciudad','Santiago')}, a {fecha}, entre "{empresa.get('nombre','EMPRESA')}", RUT {empresa.get('rut','___')}, representada por {empresa.get('rep_nombre','REPRESENTANTE')}, en adelante EMPLEADOR; y {t_nom}, RUT {t_rut}, en adelante TRABAJADOR, se acuerda:"""
    doc.add_paragraph(intro)
    
    if "CONTRATO" in tipo_doc.upper():
        clausulas = [
            ("PRIMERO:", f"El Trabajador se desempeñará como {t_cargo}."),
            ("SEGUNDO:", f"Sueldo Base pactado. Gratificación Legal tope 4.75 IMM."),
            ("TERCERO:", "Jornada de 44 horas semanales (Ley 40 Horas)."),
            ("CUARTO:", "Confidencialidad y Propiedad Intelectual.")
        ]
        for k, v in clausulas:
            p = doc.add_paragraph(); p.add_run(k).bold=True; p.add_run(f" {v}")
            
    elif "FINIQUITO" in tipo_doc.upper():
        doc.add_paragraph(f"PRIMERO: Término de relación laboral por causal legal.")
        doc.add_paragraph(f"SEGUNDO: El trabajador declara recibir a su entera conformidad el pago de su liquidación.")
    
    doc.add_paragraph("\n\n\n__________________\nFIRMA EMPLEADOR\n\n__________________\nFIRMA TRABAJADOR")
    
    bio = io.BytesIO()
    doc.save(bio)
    return bio

def procesar_lote_masivo(df, empresa_data):
    """Procesa el Excel y devuelve un ZIP con los documentos."""
    zip_buffer = io.BytesIO()
    reporte = []
    
    with zipfile.ZipFile(zip_buffer, "w") as zf:
        for idx, row in df.iterrows():
            try:
                tipo = str(row.get('TIPO_DOCUMENTO', 'Contrato'))
                nombre = str(row.get('NOMBRE_TRABAJADOR', f'Trab_{idx}'))
                
                # Generar DOCX
                docx = crear_documento_word(tipo, row, empresa_data)
                
                # Añadir al ZIP
                zf.writestr(f"{tipo}_{nombre}.docx", docx.getvalue())
            except Exception as e:
                reporte.append(f"Fila {idx}: {str(e)}")
                
    zip_buffer.seek(0)
    return zip_buffer, reporte

# =============================================================================
# 5. MOTORES DE INTELIGENCIA DE NEGOCIO
# =============================================================================

def generar_perfil_robusto(cargo, rubro):
    if not cargo: return None
    
    # Base de conocimientos por industria
    rubro_data = {
        "Minería": ["Seguridad Sernageomin", "Gestión de Activos", "Turnos 7x7", "ISO 14001"],
        "Tecnología": ["Cloud Computing", "Agile/Scrum", "DevOps", "Python/SQL"],
        "Retail": ["Customer Experience", "Logística", "E-commerce", "Visual Merchandising"],
        "Salud": ["Gestión Clínica", "Protocolos Minsal", "Acreditación", "Bioestadística"],
        "Construcción": ["BIM", "Last Planner", "Control Costos", "Prevención Riesgos"],
        "Banca": ["Riesgo Financiero", "Compliance", "Normativa CMF", "Inversiones"]
    }
    
    skills = rubro_data.get(rubro, ["Gestión de Proyectos", "Excel Avanzado", "Liderazgo", "Inglés"])
    
    return {
        "titulo": cargo.title(),
        "objetivo": f"Dirigir y controlar las operaciones de {cargo} en el sector {rubro}, asegurando KPIs y normativa.",
        "dependencia": "Gerencia General / Gerencia de Área",
        "nivel": "Profesional Senior / Jefatura",
        "funciones": [
            "Planificación estratégica y operativa del área.",
            "Control presupuestario (CAPEX/OPEX) y gestión de recursos.",
            "Liderazgo de equipos multidisciplinarios.",
            "Reportabilidad a Gerencia y stakeholders.",
            "Mejora continua de procesos críticos."
        ],
        "requisitos_duros": [
            "Título Profesional Universitario.",
            f"Experiencia mínima de 4-5 años en rubro {rubro}.",
            "Manejo de ERP (SAP/Oracle) y Office Avanzado.",
            f"Conocimientos: {', '.join(skills[:2])}."
        ],
        "competencias": ["Liderazgo Transformacional", "Visión Estratégica", "Negociación", "Resiliencia"],
        "condiciones": ["Jornada Art. 22", "Modalidad Híbrida/Presencial", "Seguro Complementario"]
    }

def motor_analisis_cv(texto, perfil):
    # Análisis semántico simulado
    kws = [k.lower() for k in perfil['competencias'] + perfil['requisitos_duros']]
    txt = texto.lower()
    
    enc = list(set([k.title() for k in kws if k.split()[0] in txt]))
    fal = list(set([k.title() for k in kws if k.split()[0] not in txt]))
    
    score = int((len(enc) / len(kws)) * 100) + random.randint(10, 20)
    score = min(99, max(15, score))
    nivel = "Senior" if score > 75 else "Semi-Senior" if score > 45 else "Junior"
    
    return score, enc, fal, nivel

def leer_pdf(archivo):
    if not LIBRARIES_OK: return None
    try:
        text = ""
        with pdfplumber.open(archivo) as pdf:
            for p in pdf.pages: text += (p.extract_text() or "")
        return text
    except: return None

# =============================================================================
# 6. CÁLCULO FINANCIERO (LÓGICA ISAPRE TARGET)
# =============================================================================

def calcular_nomina_reversa(liquido_obj, col, mov, contrato, afp_n, salud_t, plan_uf, uf, utm, s_min):
    no_imp = col + mov
    liq_meta = liquido_obj - no_imp
    if liq_meta < s_min * 0.4: return None
    
    TOPE_GRAT = (4.75 * s_min) / 12
    tasa_afp = 0.0 if (contrato == "Sueldo Empresarial" or afp_n == "SIN AFP") else (0.10 + ({"Capital":1.44,"Habitat":1.27,"Modelo":0.58,"Uno":0.49}.get(afp_n,1.44)/100))
    tasa_afc_emp = 0.024
    tasa_afc_trab = 0.006 if contrato == "Indefinido" and contrato != "Sueldo Empresarial" else 0.0
    if contrato == "Plazo Fijo": tasa_afc_emp = 0.03
    
    min_b, max_b = 100000, liq_meta * 2.5
    for _ in range(150):
        base = (min_b + max_b) / 2
        grat = min(base * 0.25, TOPE_GRAT)
        if contrato == "Sueldo Empresarial": grat = 0
        tot_imp = base + grat
        
        b_prev = min(tot_imp, 87.8*uf)
        b_afc = min(tot_imp, 131.9*uf)
        
        m_afp = int(b_prev * tasa_afp)
        m_afc = int(b_afc * tasa_afc_trab)
        
        # 7% Legal Base
        legal_7 = int(b_prev * 0.07)
        
        base_trib = max(0, tot_imp - m_afp - legal_7 - m_afc)
        imp = 0
        if base_trib > 13.5*utm: imp = int(base_trib*0.04)
        if base_trib > 30*utm: imp = int((base_trib*0.08) - (1.74*utm))
        imp = max(0, imp)
        
        liq_calc = tot_imp - m_afp - legal_7 - m_afc - imp
        
        if abs(liq_calc - liq_meta) < 500:
            salud_real = legal_7
            adicional = 0
            warning = None
            
            if salud_t == "Isapre (UF)":
                plan_pesos = int(plan_uf * uf)
                if plan_pesos > legal_7:
                    salud_real = plan_pesos
                    adicional = plan_pesos - legal_7
                    warning = f"⚠️ Plan Isapre excede el 7%. Líquido baja en {fmt(adicional)}."
            
            liq_final = tot_imp - m_afp - salud_real - m_afc - imp + no_imp
            ap_sis, ap_mut, ap_afc_e = int(b_prev*0.0149), int(b_prev*0.0093), int(b_afc*tasa_afc_emp)
            
            return {
                "Sueldo Base": int(base), "Gratificación": int(grat), "Total Imponible": int(tot_imp),
                "No Imponibles": int(no_imp), "LÍQUIDO": int(liq_final),
                "AFP": m_afp, "Salud_Legal": legal_7, "Adicional_Salud": adicional, "Salud_Total": salud_real,
                "AFC": m_afc, "Impuesto": imp, "Total Descuentos": m_afp + salud_real + m_afc + imp,
                "Aportes Empresa": ap_sis + ap_mut + ap_afc_e, "COSTO TOTAL": int(tot_imp+no_imp+ap_sis+ap_mut+ap_afc_e),
                "Warning": warning
            }
            break
        elif liq_calc < liq_meta: min_b = base
        else: max_b = base
    return None

# =============================================================================
# 7. INTERFAZ GRÁFICA PRINCIPAL
# =============================================================================

# SIDEBAR: DATOS MAESTROS
with st.sidebar:
    st.image("https://www.previred.com/wp-content/uploads/2021/01/logo-previred.png", width=120)
    
    # 1. Logo
    upl_logo = st.file_uploader("Logo Empresa", type=["png", "jpg"])
    if upl_logo: st.session_state.logo_bytes = upl_logo.read()
    
    # 2. Datos Empresa (Persistentes)
    with st.expander("🏢 Datos Empresa (Fijo)", expanded=False):
        st.session_state.empresa['rut'] = st.text_input("RUT Empresa", st.session_state.empresa['rut'])
        st.session_state.empresa['nombre'] = st.text_input("Razón Social", st.session_state.empresa['nombre'])
        st.session_state.empresa['rep_nombre'] = st.text_input("Rep. Legal", st.session_state.empresa['rep_nombre'])
        st.session_state.empresa['rep_rut'] = st.text_input("RUT Rep.", st.session_state.empresa['rep_rut'])
        st.session_state.empresa['direccion'] = st.text_input("Dirección", st.session_state.empresa['direccion'])
        st.session_state.empresa['ciudad'] = st.text_input("Ciudad", st.session_state.empresa['ciudad'])
        st.session_state.empresa['giro'] = st.text_input("Giro", st.session_state.empresa['giro'])

    # 3. Datos Trabajador
    with st.expander("👤 Datos Trabajador (Opcional)", expanded=False):
        st.session_state.trabajador['nombre'] = st.text_input("Nombre", st.session_state.trabajador['nombre'])
        st.session_state.trabajador['rut'] = st.text_input("RUT", st.session_state.trabajador['rut'])
        st.session_state.trabajador['direccion'] = st.text_input("Domicilio", st.session_state.trabajador['direccion'])
        st.session_state.trabajador['nacimiento'] = st.date_input("Nacimiento", value=st.session_state.trabajador['nacimiento'], min_value=date(1940,1,1), max_value=datetime.now())

    st.divider()
    uf_v, utm_v = obtener_indicadores()
    st.metric("UF", fmt(uf_v).replace("$",""))
    st.metric("UTM", fmt(utm_v))

st.title("HR Suite Enterprise V36")
st.markdown("**Sistema Integral de Gestión de Personas**")

tabs = st.tabs(["📂 Carga Masiva", "💰 Calculadora", "📋 Perfil Cargo", "🧠 Análisis CV", "🚀 Carrera", "📜 Legal Hub", "📊 Indicadores"])

# TAB 1: CARGA MASIVA (NUEVO: DESCARGA PLANTILLA)
with tabs[0]:
    st.header("Procesamiento por Lotes")
    
    # BOTÓN DESCARGA PLANTILLA
    st.markdown("##### Paso 1: Descargar Plantilla")
    excel_plantilla = generar_plantilla_excel()
    st.download_button("⬇️ Descargar Excel Modelo (.xlsx)", excel_plantilla, "Plantilla_Carga_RRHH.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    
    st.markdown("##### Paso 2: Subir y Procesar")
    up_excel = st.file_uploader("Subir Nómina Completa", type="xlsx")
    
    if up_excel:
        if not st.session_state.empresa['rut']:
            st.warning("⚠️ Complete los Datos de Empresa en el menú lateral antes de procesar.")
        elif st.button("PROCESAR LOTE COMPLETO"):
            df = pd.read_excel(up_excel)
            zip_data, errs = procesar_lote_masivo(df, st.session_state.empresa)
            st.success(f"Procesamiento finalizado. {len(errs)} errores detectados.")
            if errs: st.error("\n".join(errs))
            st.download_button("⬇️ Descargar Documentos (.ZIP)", zip_data, "documentos_rrhh.zip", "application/zip")

# TAB 2: CALCULADORA
with tabs[1]:
    c1, c2 = st.columns(2)
    with c1:
        liq = st.number_input("Líquido Objetivo ($)", value=1000000, step=50000, format="%d")
        mostrar_miles(liq)
        col = st.number_input("Colación", 50000, format="%d"); mov = st.number_input("Movilización", 50000, format="%d")
    with c2:
        con = st.selectbox("Contrato", ["Indefinido", "Plazo Fijo", "Sueldo Empresarial"])
        afp = st.selectbox("AFP", ["Capital", "Habitat", "Modelo", "Uno", "SIN AFP"])
        sal = st.selectbox("Salud", ["Fonasa (7%)", "Isapre (UF)"])
        plan = st.number_input("Plan UF", 0.0) if sal == "Isapre (UF)" else 0.0

    if st.button("SIMULAR SUELDO"):
        res = calcular_nomina_reversa(liq, col, mov, con, afp, sal, plan, uf_v, utm_v, 529000)
        if res:
            st.session_state.calculo_actual = res
            if res.get('Warning'): st.warning(res['Warning'])
            
            k1, k2, k3 = st.columns(3)
            k1.metric("Sueldo Base", fmt(res['Sueldo Base']))
            k2.metric("Líquido", fmt(res['LÍQUIDO_FINAL']))
            k3.metric("Costo Empresa", fmt(res['COSTO TOTAL']))
            
            st.markdown(f"""
            <div class="liq-box">
                <div class="liq-header">LIQUIDACIÓN SIMULADA</div>
                <div class="liq-row"><span>Sueldo Base:</span><span>{fmt(res['Sueldo Base'])}</span></div>
                <div class="liq-row"><span>Gratificación:</span><span>{fmt(res['Gratificación'])}</span></div>
                <div class="liq-row" style="background:#f0f0f0;"><span><b>TOTAL IMPONIBLE:</b></span><span><b>{fmt(res['Total Imponible'])}</b></span></div>
                <div class="liq-row"><span>Colación/Mov.:</span><span>{fmt(res['No Imponibles'])}</span></div>
                <br>
                <div class="liq-row"><span>AFP ({afp}):</span><span style="color:red">-{fmt(res['AFP'])}</span></div>
                <div class="liq-row"><span>Salud Total:</span><span style="color:red">-{fmt(res['Salud_Total'])}</span></div>
                <div class="liq-row"><span>Impuesto:</span><span style="color:red">-{fmt(res['Impuesto'])}</span></div>
                <div class="liq-total">A PAGAR: {fmt(res['LÍQUIDO_FINAL'])}</div>
            </div>
            """, unsafe_allow_html=True)
            
            if LIBRARIES_OK:
                pdf = generar_pdf_liquidacion(res, st.session_state.empresa, st.session_state.trabajador)
                st.download_button("⬇️ Descargar PDF", pdf, "liquidacion.pdf", "application/pdf")
        else: st.error("Error matemático.")

# TAB 3: PERFIL CARGO
with tabs[2]:
    c1, c2 = st.columns(2)
    cargo = c1.text_input("Cargo", placeholder="Ej: Jefe de Ventas")
    rubro = c2.selectbox("Rubro", ["Minería", "Tecnología", "Retail", "Salud", "Construcción", "Banca"])
    
    if cargo:
        perf = generar_perfil_robusto(cargo, rubro)
        st.session_state.perfil_actual = perf
        
        st.info(f"**Misión:** {perf['objetivo']}")
        
        c_a, c_b = st.columns(2)
        c_a.success("**Funciones:**\n" + "\n".join([f"- {x}" for x in perf['funciones']]))
        c_b.warning("**Requisitos:**\n" + "\n".join([f"- {x}" for x in perf['requisitos_obj']]))
        st.write(f"**Condiciones:** {', '.join(perf['condiciones'])}")

# TAB 4: ANÁLISIS CV
with tabs[3]:
    st.header("Análisis de Brechas")
    if not LIBRARIES_OK: st.warning("Faltan librerías.")
    else:
        up = st.file_uploader("Subir CV", type="pdf")
        if up and st.session_state.perfil_actual:
            if st.button("ANALIZAR"):
                txt = leer_pdf(up)
                if txt:
                    an = motor_analisis_cv(txt, st.session_state.perfil_actual)
                    st.metric("Score", f"{an['score']}%")
                    st.write("**Fortalezas:** " + ", ".join(an['encontradas']))
                    st.error("**Brechas:** " + ", ".join(an['faltantes']))

# TAB 5: CARRERA
with tabs[4]:
    st.header("Plan de Desarrollo")
    if 'cargo' in locals() and cargo:
        plan = generar_plan_carrera(cargo, rubro)
        c1, c2, c3 = st.columns(3)
        c1.markdown("#### Corto Plazo"); c1.write("\n".join(plan['corto']))
        c2.markdown("#### Mediano Plazo"); c2.write("\n".join(plan['mediano']))
        c3.markdown("#### Largo Plazo"); c3.write("\n".join(plan['largo']))

# TAB 6: LEGAL HUB
with tabs[5]:
    st.header("Generador Legal")
    
    if st.session_state.calculo_actual:
        c1, c2 = st.columns(2)
        fini = c1.date_input("Inicio Contrato", datetime.now())
        tcon = c2.selectbox("Tipo Contrato", ["Indefinido", "Plazo Fijo", "Obra Faena"])
        
        if st.session_state.empresa['rut']:
            cond = {"cargo": cargo if cargo else "Trabajador", "tipo": tcon, "inicio": fini, "funciones": "Las del cargo"}
            if st.button("GENERAR CONTRATO (.DOCX)"):
                bio = crear_documento_word("CONTRATO", st.session_state.trabajador, st.session_state.empresa)
                st.download_button("Descargar", bio.getvalue(), "contrato.docx")
        else:
            st.error("⚠️ Complete Datos Empresa en barra lateral.")
    else: st.info("Calcule sueldo primero.")

# TAB 7: INDICADORES
with tabs[6]:
    st.header("Indicadores Previred")
    st.info("UF: $39.643 | UTM: $69.542 | Sueldo Mín: $529.000")
