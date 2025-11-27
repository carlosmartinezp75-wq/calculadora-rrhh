import streamlit as st
import pandas as pd
import requests
import base64
import os
import io
import zipfile
import tempfile
import random
from datetime import datetime, date
import plotly.graph_objects as go
import plotly.express as px

# =============================================================================
# 0. VALIDACIÓN DE ENTORNO
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
# 1. CONFIGURACIÓN E INICIALIZACIÓN
# =============================================================================
st.set_page_config(page_title="HR Suite Ultimate V35", page_icon="💎", layout="wide")

# Inicialización de Estado (Persistencia de Datos)
if 'empresa' not in st.session_state:
    st.session_state.empresa = {
        "nombre": "", "rut": "", "direccion": "", 
        "rep_nombre": "", "rep_rut": "", "ciudad": "Santiago", "giro": "Servicios Profesionales"
    }
if 'trabajador' not in st.session_state:
    st.session_state.trabajador = {
        "nombre": "", "rut": "", "direccion": "", 
        "nacionalidad": "Chilena", "civil": "Soltero", "nacimiento": date(1990,1,1),
        "cargo": "", "fecha_ingreso": date.today()
    }
if 'calculo_actual' not in st.session_state: st.session_state.calculo_actual = None
if 'perfil_actual' not in st.session_state: st.session_state.perfil_actual = None
if 'logo_bytes' not in st.session_state: st.session_state.logo_bytes = None

# =============================================================================
# 2. ESTILOS VISUALES (CSS CORPORATIVO)
# =============================================================================
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
        .block-container {{background-color: rgba(255, 255, 255, 0.98); padding: 2.5rem; border-radius: 15px; box-shadow: 0 10px 40px rgba(0,0,0,0.1);}}
        h1, h2, h3, h4 {{color: #004a99 !important; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; font-weight: 800;}}
        .stButton>button {{background-color: #004a99 !important; color: white !important; font-weight: bold; border-radius: 8px; width: 100%; height: 3rem; text-transform: uppercase;}}
        .stButton>button:hover {{background-color: #003366 !important; transform: translateY(-2px);}}
        
        /* Liquidación Visual */
        .liq-box {{border: 1px solid #ccc; padding: 25px; background: #fff; font-family: 'Courier New', monospace; margin-top: 15px; box-shadow: 5px 5px 15px #eee;}}
        .liq-header {{text-align: center; border-bottom: 2px solid #000; padding-bottom: 10px; margin-bottom: 15px; font-weight: bold;}}
        .liq-row {{display: flex; justify-content: space-between; border-bottom: 1px dashed #ddd; padding: 4px 0;}}
        .liq-total {{background: #e3f2fd; padding: 15px; font-weight: bold; font-size: 1.3em; border: 2px solid #004a99; margin-top: 20px; color: #004a99;}}
        
        .miles-feedback {{font-size: 0.8rem; color: #2e7d32; font-weight: bold; margin-top: -10px;}}
        
        /* Tablas */
        thead tr th:first-child {{display:none}}
        tbody th {{display:none}}
        </style>
        """, unsafe_allow_html=True)

cargar_estilos()

# =============================================================================
# 3. FUNCIONES UTILITARIAS Y DATA
# =============================================================================
def fmt(valor): 
    if pd.isna(valor) or valor == "": return "$0"
    try: return "${:,.0f}".format(float(valor)).replace(",", ".")
    except: return str(valor)

def mostrar_miles(valor): 
    if valor > 0: st.markdown(f'<p class="miles-feedback">✅ Ingresaste: {fmt(valor)}</p>', unsafe_allow_html=True)

def obtener_indicadores():
    # Valores fijos Nov 2025 para estabilidad
    return 39643.59, 69542.0

# =============================================================================
# 4. MOTORES DE INTELIGENCIA DE NEGOCIO
# =============================================================================

def generar_perfil_word_style(cargo, rubro):
    """Genera perfil detallado basado en el formato Word subido"""
    if not cargo: return None
    
    # Diccionarios de Conocimiento por Rubro
    skills_map = {
        "Tecnología": ["Cloud Computing (AWS/Azure)", "Scrum/Agile", "Python/SQL", "Cybersecurity"],
        "Minería": ["Normativa Sernageomin", "Gestión de Activos", "Seguridad Industrial", "Lean Mining"],
        "Retail": ["E-commerce", "Logística Última Milla", "Customer Experience", "Visual Merchandising"],
        "Salud": ["Gestión Clínica", "Calidad Acreditación", "Bioestadística", "Normativa Minsal"],
        "Construcción": ["Autocad/BIM", "Control de Costos", "Prevención de Riesgos", "Gestión de Obras"],
        "Servicios": ["Atención Cliente", "SLA", "Gestión Procesos", "Ventas Consultivas"]
    }
    
    hard_skills = skills_map.get(rubro, ["Gestión de Proyectos", "Excel Avanzado", "ERP", "Inglés"])
    
    return {
        "titulo": cargo.title(),
        "objetivo": f"Coordinar, gestionar y controlar los procesos críticos del área de {cargo} en el sector {rubro}, asegurando eficiencia y cumplimiento normativo.",
        "dependencia": "Gerencia General / Gerencia de Área",
        "nivel_resp": "Jefatura / Supervisión Senior",
        "funciones": [
            "Coordinación y supervisión de equipos de trabajo multidisciplinarios.",
            "Control presupuestario y gestión eficiente de recursos (CAPEX/OPEX).",
            "Reportabilidad de estados de avance y KPIs críticos a la Gerencia.",
            "Aseguramiento de la calidad y cumplimiento de normativa vigente.",
            "Optimización continua de procedimientos para mejorar la productividad."
        ],
        "requisitos_obj": [
            "Título Profesional Universitario afín al cargo.",
            f"Experiencia mínima de 4-5 años en empresas del rubro {rubro}.",
            "Manejo avanzado de herramientas ERP y Office.",
            f"Conocimientos específicos: {', '.join(hard_skills)}."
        ],
        "competencias": ["Liderazgo Transformacional", "Autonomía", "Orientación al Resultado", "Trabajo bajo presión", "Visión Estratégica"],
        "condiciones": [
            "Jornada: Art. 22 o 44 Horas (según rol).",
            "Lugar: Oficina Central / Terreno / Híbrido.",
            "Disponibilidad para viajes dentro y fuera del país."
        ],
        "fisicos": "Salud compatible con el cargo. Capacidad para trabajo en altura geográfica (si aplica)."
    }

def motor_analisis_cv(texto, perfil):
    """Analiza match entre CV y Perfil"""
    kws = [k.lower() for k in perfil['competencias'] + perfil['requisitos_obj']]
    txt = texto.lower()
    
    enc = list(set([k.title() for k in kws if k.split()[0] in txt])) 
    fal = list(set([k.title() for k in kws if k.split()[0] not in txt]))
    
    score = int((len(enc) / len(kws)) * 100) + random.randint(10, 20)
    score = min(98, max(15, score))
    
    nivel = "Senior" if score > 75 else "Semi-Senior" if score > 45 else "Junior"
    
    return {"score": score, "nivel": nivel, "encontradas": enc, "faltantes": fal}

def generar_plan_carrera(cargo, rubro):
    """Genera hoja de ruta de desarrollo"""
    return {
        "corto": ["Inducción corporativa y normativa.", "Certificación en herramientas internas.", "Cumplimiento de metas iniciales."],
        "mediano": ["Liderazgo de proyectos transversales.", f"Especialización técnica en {rubro}.", "Mentoring a pares."],
        "largo": ["Asumir Jefatura/Gerencia de Área.", "Participación en comité estratégico.", "Desarrollo de nuevos negocios."]
    }

def leer_pdf(archivo):
    if not LIBRARIES_OK: return None
    try:
        text = ""
        with pdfplumber.open(archivo) as pdf:
            for p in pdf.pages: text += (p.extract_text() or "")
        return text
    except: return None

# =============================================================================
# 5. MOTORES FINANCIEROS (CÁLCULO EXACTO)
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
        m_afc_t = int(b_afc * tasa_afc_trab)
        
        # TARGET ISAPRE: Usamos 7% legal para encontrar el bruto objetivo
        legal_7 = int(b_prev * 0.07)
        base_trib = max(0, tot_imp - m_afp - legal_7 - m_afc_t)
        
        imp = 0
        if base_trib > 13.5*utm: imp = int(base_trib*0.04)
        if base_trib > 30*utm: imp = int((base_trib*0.08) - (1.74*utm))
        imp = max(0, imp)
        
        liq_calc_base = tot_imp - m_afp - legal_7 - m_afc_t - imp
        
        if abs(liq_calc_base - liq_meta) < 500:
            # APLICAR PLAN REAL ISAPRE
            salud_real = legal_7
            adicional = 0
            warning = None
            
            if salud_t == "Isapre (UF)":
                plan_pesos = int(plan_uf * uf)
                if plan_pesos > legal_7:
                    salud_real = plan_pesos
                    adicional = plan_pesos - legal_7
                    warning = f"⚠️ Plan Isapre excede el 7%. Líquido baja en {fmt(adicional)}."
            
            liq_final = tot_imp - m_afp - salud_real - m_afc_t - imp + no_imp
            ap_sis = int(b_prev*0.0149)
            ap_mut = int(b_prev*0.0093)
            ap_afc_e = int(b_afc*tasa_afc_emp)
            
            return {
                "Sueldo Base": int(base), "Gratificación": int(grat), "Total Imponible": int(tot_imp),
                "No Imponibles": int(no_imp), "LÍQUIDO_OBJETIVO": int(liquido_obj),
                "LÍQUIDO_FINAL": int(liq_final),
                "AFP": m_afp, "Salud_Legal": legal_7, "Adicional_Salud": adicional, "Salud_Total": salud_real,
                "AFC": m_afc_t, "Impuesto": imp, "Total Descuentos": m_afp + salud_real + m_afc_t + imp,
                "Aportes Empresa": ap_sis + ap_mut + ap_afc_e, 
                "COSTO TOTAL": int(tot_imp+no_imp+ap_sis+ap_mut+ap_afc_e),
                "Warning": warning
            }
            break
        elif liq_calc_base < liq_meta: min_b = base
        else: max_b = base
    return None

def calcular_finiquito(f_ini, f_fin, sueldo_base, causal, vac_pend):
    dias = (f_fin - f_ini).days
    anos = int(dias / 365.25)
    if (dias/365.25 - anos)*12 >= 6: anos += 1
    anos = min(anos, 11)
    
    tope_uf = 90 * 39643.59
    base = min(sueldo_base, tope_uf)
    
    indem = int(base * anos) if causal == "Necesidades de la Empresa" else 0
    aviso = int(base) if causal in ["Necesidades de la Empresa", "Desahucio"] else 0
    vacas = int(vac_pend * 1.25 * (sueldo_base/30))
    
    return {"indem_anos": indem, "aviso": aviso, "vacaciones": vacas, "total": indem+aviso+vacas}

# =============================================================================
# 6. GENERADORES DOCUMENTALES (PDF/WORD/ZIP)
# =============================================================================

def generar_pdf_liquidacion(res, empresa, trabajador):
    if not LIBRARIES_OK: return None
    pdf = FPDF()
    pdf.add_page()
    
    if st.session_state.logo_bytes:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
            tmp.write(st.session_state.logo_bytes)
            tmp_path = tmp.name
        try: pdf.image(tmp_path, 10, 8, 30)
        except: pass

    pdf.set_font("Arial", 'B', 14); pdf.cell(0, 15, "LIQUIDACION DE SUELDO", 0, 1, 'C')
    pdf.ln(5)
    pdf.set_font("Arial", '', 10)
    pdf.cell(0, 6, f"Empresa: {empresa['nombre']} | RUT: {empresa['rut']}", 0, 1)
    pdf.cell(0, 6, f"Trabajador: {trabajador['nombre']} | RUT: {trabajador['rut']}", 0, 1)
    pdf.ln(5)
    
    # Tabla
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(95, 8, "HABERES", 1, 0, 'C', 1); pdf.cell(95, 8, "DESCUENTOS", 1, 1, 'C', 1)
    
    h = [("Base", res['Sueldo Base']), ("Gratificacion", res['Gratificación']), ("No Imp.", res['No Imponibles'])]
    d = [("AFP", res['AFP']), ("Salud", res['Salud_Total']), ("AFC", res['AFC']), ("Impuesto", res['Impuesto'])]
    
    for i in range(max(len(h), len(d))):
        ht, hv = h[i] if i < len(h) else ("", "")
        dt, dv = d[i] if i < len(d) else ("", "")
        pdf.cell(60, 6, ht, 'L'); pdf.cell(35, 6, fmt(hv) if hv!="" else "", 'R')
        pdf.cell(60, 6, dt, 'L'); pdf.cell(35, 6, fmt(dv) if dv!="" else "", 'R', 1)
    
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(130, 10, "A PAGAR:", 1, 0, 'R'); pdf.cell(60, 10, fmt(res['LÍQUIDO_FINAL']), 1, 1, 'C')
    return pdf.output(dest='S').encode('latin-1')

def crear_documento_word(tipo_doc, datos_fila, empresa_data):
    # Generador Genérico para Masivo e Individual
    doc = Document()
    style = doc.styles['Normal']; style.font.name = 'Arial'; style.font.size = Pt(11)
    fecha = datetime.now().strftime("%d de %B de %Y")
    
    doc.add_heading(tipo_doc.upper(), 0).alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.add_paragraph(f"Fecha: {fecha}").alignment = WD_ALIGN_PARAGRAPH.RIGHT
    
    # Datos seguros
    def g(k): return str(datos_fila.get(k, "________"))
    
    intro = f"""En {empresa_data['ciudad']}, a {fecha}, entre "{empresa_data['nombre']}", RUT {empresa_data['rut']}, representada por {empresa_data['rep_nombre']}, en adelante EMPLEADOR; y {g('nombre')}, RUT {g('rut')}, en adelante TRABAJADOR, se acuerda:"""
    doc.add_paragraph(intro)
    
    if "CONTRATO" in tipo_doc.upper():
        doc.add_paragraph(f"PRIMERO: El trabajador se desempeñará como {g('cargo')}.")
        doc.add_paragraph(f"SEGUNDO: Sueldo Base {fmt(g('sueldo'))}. Gratificación Legal tope 4.75 IMM.")
        doc.add_paragraph("TERCERO: Jornada de 44 horas semanales. (Ley 40 Horas)")
        doc.add_paragraph("CUARTO: Obligación de confidencialidad y propiedad intelectual.")
    
    elif "FINIQUITO" in tipo_doc.upper():
        doc.add_paragraph(f"PRIMERO: Las partes ponen término al contrato por causal: {g('causal')}.")
        doc.add_paragraph(f"SEGUNDO: El empleador paga indemnización por {fmt(g('total'))}.")
        
    doc.add_paragraph("\n\n\n__________________\nFIRMA EMPLEADOR\n\n__________________\nFIRMA TRABAJADOR")
    
    bio = io.BytesIO()
    doc.save(bio)
    return bio

def procesar_lote_excel(df, empresa_data):
    zip_buffer = io.BytesIO()
    reporte = []
    with zipfile.ZipFile(zip_buffer, "w") as zf:
        for idx, row in df.iterrows():
            try:
                tipo = str(row.get('TIPO_DOCUMENTO', 'Contrato'))
                nombre = str(row.get('NOMBRE', f'Trabajador_{idx}'))
                # Lógica de cálculo interna si es finiquito
                if "FINIQUITO" in tipo.upper():
                    # Simulación cálculo rápido para masivo
                    base = float(row.get('SUELDO', 0))
                    fin = calcular_finiquito(date(2020,1,1), date.today(), base, "Necesidades", 0)
                    row['total'] = fin['total']
                
                docx = crear_documento_word(tipo, row, empresa_data)
                zf.writestr(f"{tipo}_{nombre}.docx", docx.getvalue())
            except Exception as e:
                reporte.append(f"Error fila {idx}: {e}")
    zip_buffer.seek(0)
    return zip_buffer, reporte

# =============================================================================
# 7. INTERFAZ GRÁFICA (TABS)
# =============================================================================

# SIDEBAR
with st.sidebar:
    st.image("https://www.previred.com/wp-content/uploads/2021/01/logo-previred.png", width=120)
    
    # 1. Logo
    upl_logo = st.file_uploader("Logo Empresa", type=["png", "jpg"])
    if upl_logo: st.session_state.logo_bytes = upl_logo.read()
    
    # 2. Datos Empresa
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
        st.session_state.trabajador['nacimiento'] = st.date_input("Nacimiento", value=date(1990,1,1), min_value=date(1940,1,1), max_value=date.today())

st.title("HR Suite Enterprise V35")
st.markdown("**Sistema Integral de Gestión de Personas**")

tabs = st.tabs(["📂 Carga Masiva", "💰 Calculadora", "📋 Perfil", "🧠 Análisis CV", "🚀 Carrera", "📜 Legal Hub", "📊 Indicadores"])

# TAB 1: CARGA MASIVA (EXCEL)
with tabs[0]:
    st.header("Procesamiento por Lotes")
    st.info("Sube un Excel con columnas: TIPO_DOCUMENTO, NOMBRE, RUT, CARGO, SUELDO")
    up_excel = st.file_uploader("Subir Nómina (.xlsx)", type="xlsx")
    
    if up_excel:
        if not st.session_state.empresa['rut']:
            st.warning("⚠️ Complete los Datos de Empresa en el menú lateral.")
        elif st.button("PROCESAR LOTE"):
            df = pd.read_excel(up_excel)
            zip_data, errs = procesar_lote_excel(df, st.session_state.empresa)
            st.success("Procesamiento completado.")
            if errs: st.error(f"Errores: {len(errs)}")
            st.download_button("⬇️ Descargar Todo (.ZIP)", zip_data, "documentos_rrhh.zip", "application/zip")

# TAB 2: CALCULADORA
with tabs[1]:
    c1, c2 = st.columns(2)
    with c1:
        liq = st.number_input("Líquido Objetivo", 1000000, step=50000)
        mostrar_miles(liq)
        col = st.number_input("Colación", 50000); mov = st.number_input("Movilización", 50000)
    with c2:
        con = st.selectbox("Contrato", ["Indefinido", "Plazo Fijo", "Empresarial"])
        afp = st.selectbox("AFP", ["Capital", "Habitat", "Modelo", "Uno", "SIN AFP"])
        sal = st.selectbox("Salud", ["Fonasa (7%)", "Isapre (UF)"])
        plan = st.number_input("Plan UF", 0.0) if sal == "Isapre (UF)" else 0.0

    if st.button("CALCULAR"):
        res = calcular_nomina_reversa(liq, col, mov, con, afp, sal, plan, 39643.59, 69542.0, 529000)
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
                <div class="liq-row"><span>Colación/Mov.:</span><span>{fmt(res['No Imponibles'])}</span></div>
                <br>
                <div class="liq-row"><span>AFP / Salud / Cesantía:</span><span style="color:red">-{fmt(res['AFP']+res['Salud_Total']+res['AFC'])}</span></div>
                <div class="liq-row"><span>Adicional Isapre:</span><span style="color:red">-{fmt(res['Adicional_Salud'])}</span></div>
                <div class="liq-row"><span>Impuesto:</span><span style="color:red">-{fmt(res['Impuesto'])}</span></div>
                <div class="liq-total">A PAGAR: {fmt(res['LÍQUIDO_FINAL'])}</div>
            </div>
            """, unsafe_allow_html=True)
            
            if LIBRARIES_OK:
                pdf = generar_pdf_liquidacion(res, st.session_state.empresa, st.session_state.trabajador)
                st.download_button("⬇️ Descargar PDF", pdf, "liquidacion.pdf", "application/pdf")

# TAB 3: PERFIL CARGO
with tabs[2]:
    c1, c2 = st.columns(2)
    cargo = c1.text_input("Cargo", "Jefe de Ventas")
    rubro = c2.selectbox("Rubro", ["Minería", "Tecnología", "Retail", "Salud", "Construcción"])
    
    if cargo:
        perf = generar_perfil_word_style(cargo, rubro)
        st.session_state.perfil_actual = perf
        st.info(f"**Misión:** {perf['objetivo']}")
        
        c_a, c_b = st.columns(2)
        c_a.success("**Funciones:**\n" + "\n".join([f"- {x}" for x in perf['funciones']]))
        c_b.warning("**Requisitos:**\n" + "\n".join([f"- {x}" for x in perf['requisitos_obj']]))
        st.write(f"**Físicos/Ambientales:** {perf['fisicos']}")

# TAB 4: ANÁLISIS CV
with tabs[3]:
    if LIBRARIES_OK:
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
    if cargo:
        plan = generar_plan_carrera(cargo, rubro)
        c1, c2, c3 = st.columns(3)
        c1.markdown("#### Corto Plazo"); c1.write("\n".join(plan['corto']))
        c2.markdown("#### Mediano Plazo"); c2.write("\n".join(plan['mediano']))
        c3.markdown("#### Largo Plazo"); c3.write("\n".join(plan['largo']))

# TAB 6: LEGAL HUB
with tabs[5]:
    tipo = st.radio("Documento", ["Contrato", "Finiquito", "Amonestación"], horizontal=True)
    
    if tipo == "Contrato":
        if st.session_state.calculo_actual:
            if st.button("Generar Contrato"):
                docx = crear_documento_word("Contrato", {"nombre": st.session_state.trabajador['nombre'], "cargo": cargo}, st.session_state.empresa)
                st.download_button("Descargar", docx, "contrato.docx")
        else: st.warning("Calcule sueldo primero")
        
    elif tipo == "Finiquito":
        fi = st.date_input("Inicio", date(2020,1,1)); ft = st.date_input("Fin", date.today())
        base = st.number_input("Base", 1000000); vac = st.number_input("Vacaciones", 0)
        if st.button("Calcular Finiquito"):
            res = calcular_finiquito(fi, ft, base, "Necesidades", vac)
            st.write(res)

# TAB 7: INDICADORES
with tabs[6]:
    st.header("Indicadores Previred")
    st.info("UF: $39.643 | UTM: $69.542 | Sueldo Mín: $529.000")
