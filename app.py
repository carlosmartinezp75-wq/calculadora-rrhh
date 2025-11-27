import streamlit as st
import pandas as pd
import requests
import base64
import os
import io
import random
import tempfile
from datetime import datetime, date
import plotly.graph_objects as go
import plotly.express as px

# --- 0. VALIDACIÓN LIBRERÍAS ---
try:
    import pdfplumber
    from fpdf import FPDF
    from docx import Document
    from docx.shared import Pt, Inches, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    LIBRARIES_OK = True
except ImportError:
    LIBRARIES_OK = False

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="HR Suite CEO Edition", page_icon="⚖️", layout="wide")

# Estado Persistente
if 'empresa' not in st.session_state:
    st.session_state.empresa = {
        "nombre": "", "rut": "", "direccion": "", "rep_nombre": "", "rep_rut": "", "ciudad": "Santiago", "giro": "Servicios"
    }
if 'logo_path' not in st.session_state: st.session_state.logo_path = None
if 'calculo_actual' not in st.session_state: st.session_state.calculo_actual = None
if 'perfil_actual' not in st.session_state: st.session_state.perfil_actual = None

# --- 2. ESTILOS VISUALES ---
def cargar_estilos():
    # Fondo
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
        .block-container {{background-color: rgba(255, 255, 255, 0.98); padding: 2rem; border-radius: 15px; box-shadow: 0 10px 40px rgba(0,0,0,0.15);}}
        h1, h2, h3 {{color: #004a99 !important; font-family: 'Segoe UI', sans-serif; font-weight: 800;}}
        .stButton>button {{background-color: #004a99 !important; color: white !important; font-weight: bold; border-radius: 8px; width: 100%; height: 3.2rem; text-transform: uppercase;}}
        .stButton>button:hover {{background-color: #003366 !important; transform: translateY(-2px);}}
        
        /* Liquidación Visual */
        .liq-box {{border: 1px solid #ccc; padding: 25px; background: #fff; font-family: 'Courier New', monospace; box-shadow: 5px 5px 15px rgba(0,0,0,0.05);}}
        .liq-header {{text-align: center; border-bottom: 2px solid #000; padding-bottom: 10px; margin-bottom: 15px; font-weight: bold;}}
        .liq-row {{display: flex; justify-content: space-between; border-bottom: 1px dotted #ddd; padding: 4px 0;}}
        .liq-total {{background: #e3f2fd; padding: 15px; font-weight: bold; font-size: 1.4em; border: 2px solid #004a99; margin-top: 20px; color: #004a99;}}
        
        .miles-feedback {{font-size: 0.8rem; color: #2e7d32; font-weight: bold; margin-top: -10px;}}
        </style>
        """, unsafe_allow_html=True)

cargar_estilos()

# --- 3. FUNCIONES UTILITARIAS ---
def fmt(valor): return "$0" if pd.isna(valor) else "${:,.0f}".format(valor).replace(",", ".")
def mostrar_miles(valor): 
    if valor > 0: st.markdown(f'<p class="miles-feedback">✅ Ingresaste: {fmt(valor)}</p>', unsafe_allow_html=True)

def obtener_indicadores():
    # Fallback Nov 2025
    try:
        r = requests.get('https://mindicador.cl/api', timeout=2)
        d = r.json()
        return float(d['uf']['valor']), float(d['utm']['valor'])
    except: return 39643.59, 69542.0

# --- 4. GENERADORES DOCUMENTALES AVANZADOS ---

def generar_pdf_liq_con_logo(res, empresa, trabajador, logo_bytes=None):
    if not LIBRARIES_OK: return None
    pdf = FPDF()
    pdf.add_page()
    
    # Logo
    if logo_bytes:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
            tmp.write(logo_bytes)
            tmp_path = tmp.name
        try:
            pdf.image(tmp_path, 10, 8, 33)
        except: pass
    
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 15, "LIQUIDACION DE SUELDO MENSUAL", 0, 1, 'C')
    pdf.ln(10)
    
    pdf.set_font("Arial", '', 10)
    # Cabecera
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(0, 8, "DATOS DEL TRABAJADOR", 1, 1, 'L', 1)
    pdf.cell(130, 8, f"Nombre: {trabajador.get('nombre', '')}", 1)
    pdf.cell(60, 8, f"RUT: {trabajador.get('rut', '')}", 1, 1)
    pdf.cell(130, 8, f"Cargo: {res.get('cargo', 'No Definido')}", 1)
    pdf.cell(60, 8, f"Fecha: {datetime.now().strftime('%d/%m/%Y')}", 1, 1)
    pdf.ln(5)
    
    # Cuerpo
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(95, 8, "HABERES", 1, 0, 'C', 1)
    pdf.cell(95, 8, "DESCUENTOS", 1, 1, 'C', 1)
    
    pdf.set_font("Arial", '', 10)
    
    haberes = [
        ("Sueldo Base", res['Sueldo Base']),
        ("Gratificacion Legal", res['Gratificación']),
        ("Colacion/Movilizacion", res['No Imponibles']),
        ("Total Haberes", res['TOTAL HABERES'])
    ]
    
    descuentos = [
        ("AFP", res['AFP']),
        ("Salud Legal (7%)", res['Salud_Legal']),
        ("Adicional Isapre", res['Adicional_Salud']),
        ("Seguro Cesantia", res['AFC']),
        ("Impuesto Unico", res['Impuesto']),
        ("Total Descuentos", res['Total Descuentos'])
    ]
    
    max_rows = max(len(haberes), len(descuentos))
    
    for i in range(max_rows):
        h_txt, h_val = haberes[i] if i < len(haberes) else ("", "")
        d_txt, d_val = descuentos[i] if i < len(descuentos) else ("", "")
        
        pdf.cell(60, 8, h_txt, 'L'); pdf.cell(35, 8, fmt(h_val) if h_val != "" else "", 'R')
        pdf.cell(60, 8, d_txt, 'L'); pdf.cell(35, 8, fmt(d_val) if d_val != "" else "", 'R', 1)

    pdf.ln(5)
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(130, 12, "SALDO LIQUIDO A PAGAR:", 1, 0, 'R')
    pdf.cell(60, 12, fmt(res['LÍQUIDO_FINAL']), 1, 1, 'C')
    
    # Pie de pagina
    pdf.ln(20)
    pdf.set_font("Arial", '', 9)
    pdf.multi_cell(0, 5, "Certifico que he recibido de mi empleador a mi total satisfaccion el saldo liquido indicado, sin tener cargo ni cobro posterior.\n\n\n\n__________________________\nFirma del Trabajador")
    
    return pdf.output(dest='S').encode('latin-1')

def generar_contrato_legal_cloo(fin, emp, trab, cond):
    if not LIBRARIES_OK: return None
    doc = Document()
    style = doc.styles['Normal']
    style.font.name = 'Arial'
    style.font.size = Pt(11)
    
    t = doc.add_heading('CONTRATO DE TRABAJO', 0)
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.add_paragraph("")
    
    # Texto Legal "Chief Legal Operations Officer"
    intro = f"""En {emp['ciudad']}, a {datetime.now().strftime("%d de %B de %Y")}, entre la empresa "{emp['nombre'].upper()}", RUT {emp['rut']}, giro {emp.get('giro', 'Giro Comercial')}, representada legalmente por don/ña {emp['rep_nombre'].upper()}, cédula nacional de identidad N° {emp['rep_rut']}, ambos domiciliados en {emp['direccion']}, en adelante el "EMPLEADOR"; y don/ña {trab['nombre'].upper()}, cédula nacional de identidad N° {trab['rut']}, de nacionalidad {trab['nacionalidad']}, nacido el {str(trab['nacimiento'])}, domiciliado en {trab['domicilio']}, en adelante el "TRABAJADOR", se ha convenido el siguiente contrato de trabajo:"""
    
    p = doc.add_paragraph(intro)
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    
    clausulas = [
        ("PRIMERO (Naturaleza de los Servicios):", f"El Trabajador se compromete y obliga a desempeñar el cargo de {cond['cargo'].upper()}, realizando las funciones de {cond['funciones']} y cualquier otra labor inherente a su cargo que le encomiende la Jefatura."),
        
        ("SEGUNDO (Lugar de Trabajo):", f"Los servicios se prestarán en las dependencias de la empresa ubicadas en {emp['direccion']}, sin perjuicio de los desplazamientos que requiera el cargo."),
        
        ("TERCERO (Jornada de Trabajo):", "El trabajador cumplirá una jornada ordinaria de 44 horas semanales, distribuidas de lunes a viernes. De conformidad a la Ley 21.561, esta jornada se reducirá gradualmente a 40 horas según los plazos legales vigentes."),
        
        ("CUARTO (Remuneración):", f"El Empleador pagará al Trabajador una remuneración mensual compuesta por:\n"
                                   f"a) Sueldo Base: {fmt(fin['Sueldo Base'])}\n"
                                   f"b) Gratificación Legal: {fmt(fin['Gratificación'])} (Con tope legal de 4.75 IMM anual prorrateado)\n"
                                   f"c) Asignación de Colación: {fmt(fin['No Imponibles']//2)}\n"
                                   f"d) Asignación de Movilización: {fmt(fin['No Imponibles']//2)}\n\n"
                                   f"Las partes dejan constancia que las asignaciones de colación y movilización no constituyen remuneración para ningún efecto legal."),
        
        ("QUINTO (Descuentos):", "El Empleador deducirá de las remuneraciones los impuestos, cotizaciones previsionales y de seguridad social obligatorias."),
        
        ("SEXTO (Ley Karin - Ley 21.643):", "La empresa declara contar con un Protocolo de Prevención del Acoso Sexual, Laboral y Violencia en el Trabajo. El Trabajador declara conocer dicho protocolo y el procedimiento de investigación, comprometiéndose a mantener un ambiente laboral libre de violencia."),
        
        ("SÉPTIMO (Confidencialidad):", "El Trabajador se obliga a mantener estricta reserva respecto de la información confidencial, secretos comerciales, bases de datos y estrategias de la Empresa, prohibiéndose su divulgación a terceros durante y después de la vigencia del contrato."),
        
        ("OCTAVO (Vigencia):", f"El presente contrato es de carácter {cond['tipo']} y comenzará a regir a partir del {str(cond['inicio'])}.")
    ]
    
    for tit, txt in clausulas:
        p = doc.add_paragraph()
        run = p.add_run(tit)
        run.bold = True
        run.font.color.rgb = RGBColor(0, 0, 0)
        p.add_run(f" {txt}")
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        doc.add_paragraph("")
    
    # Firmas
    doc.add_paragraph("\n\n\n\n")
    table = doc.add_table(rows=1, cols=2)
    table.alignment = WD_ALIGN_PARAGRAPH.CENTER
    c1 = table.cell(0, 0)
    c1.text = "___________________________\np.p EMPLEADOR\nRUT: " + emp['rut']
    c1.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    c2 = table.cell(0, 1)
    c2.text = "___________________________\nTRABAJADOR\nRUT: " + trab['rut']
    c2.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    bio = io.BytesIO()
    doc.save(bio)
    return bio

# --- 5. PERFILES ROBUSTOS ---
def generar_perfil_robusto(cargo, rubro):
    if not cargo: return None
    
    # Diccionario Extendido de Rubros
    skills_map = {
        "Tecnología": ["Cloud (AWS/Azure)", "Cybersecurity", "Python/SQL", "Agile/Scrum"],
        "Minería": ["Sernageomin", "ISO 9001/14001", "Gestión de Activos", "Seguridad Industrial"],
        "Retail": ["E-commerce", "Logística", "Trade Marketing", "Customer Experience"],
        "Salud": ["IAAS", "Calidad Acreditación", "Gestión Clínica", "Minsal"],
        "Construcción": ["BIM", "Last Planner", "Control Costos", "Prevención Riesgos"],
        "Agroindustria": ["BPM/HACCP", "Exportación", "Riego Tecnificado", "Control Calidad"],
        "Transporte": ["Flota GPS", "Logística Última Milla", "Mantenimiento", "Normativa MTT"],
        "Educación": ["Gestión Curricular", "LMS (Moodle)", "Convivencia Escolar", "Acreditación"],
        "Banca": ["Riesgo Crédito", "Compliance", "Inversiones", "Normativa CMF"],
        "Servicios": ["Atención Cliente", "SLA", "Gestión Procesos", "Ventas Consultivas"]
    }
    hard = skills_map.get(rubro, ["Gestión de Proyectos", "Excel Avanzado", "ERP", "Inglés"])
    
    return {
        "titulo": cargo.title(),
        "mision": f"Liderar, planificar y controlar las operaciones del área de {cargo} en el sector {rubro}, asegurando el cumplimiento de los objetivos estratégicos y normativos de la organización.",
        "dependencia": "Gerencia de Área / Gerencia General",
        "nivel": "Jefatura / Supervisión",
        "funciones": [
            "Elaboración y control del presupuesto anual del área (CAPEX/OPEX).",
            "Gestión y desarrollo de equipos de trabajo de alto rendimiento.",
            "Diseño e implementación de KPIs para el monitoreo de la gestión.",
            "Aseguramiento del cumplimiento de la normativa legal y técnica vigente.",
            "Coordinación con áreas transversales para la optimización de procesos."
        ],
        "requisitos_duros": [
            "Título Profesional Universitario afín al cargo.",
            f"Experiencia mínima de 3 a 5 años en empresas del rubro {rubro}.",
            "Manejo avanzado de herramientas ERP y Office.",
            "Diplomados o especializaciones en el área (Deseable)."
        ],
        "competencias_blandas": [
            "Liderazgo Transformacional", "Pensamiento Estratégico", "Orientación a Resultados", "Comunicación Asertiva"
        ],
        "condiciones": [
            "Jornada: Art. 22 o 40 Horas (según rol).",
            "Lugar: Oficina Central / Terreno / Híbrido.",
            "Disponibilidad para viajes dentro y fuera del país."
        ]
    }

# --- 6. CÁLCULO FINANCIERO (LÓGICA ISAPRE TARGET) ---
def calcular_nomina_reversa(liquido_obj, col, mov, contrato, afp_n, salud_t, plan_uf, uf, utm, s_min, t_imp, t_afc):
    
    no_imp = col + mov
    
    # 1. Definir Líquido Tributable Objetivo
    # La lógica es: Calculamos el Bruto para que (Bruto - Leyes - Impuesto) = Líquido Objetivo
    # PERO asumimos Salud = 7% para el cálculo inverso.
    liq_meta = liquido_obj - no_imp
    
    if liq_meta < s_min * 0.4: return None
    
    TOPE_GRAT = (4.75 * s_min) / 12
    tasa_afp = 0.0 if (contrato == "Sueldo Empresarial" or afp_n == "SIN AFP") else (0.10 + ({"Capital":1.44,"Cuprum":1.44,"Habitat":1.27,"PlanVital":1.16,"Provida":1.45,"Modelo":0.58,"Uno":0.49}.get(afp_n,1.44)/100))
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
        
        # Para el cálculo del Bruto Objetivo, usamos el 7% LEGAL
        legal_7 = int(b_prev * 0.07)
        
        # Impuesto (Usando 7% como rebaja)
        base_trib = max(0, tot_imp - m_afp - legal_7 - m_afc)
        
        imp = 0
        tabla = [(13.5,0,0),(30,0.04,0.54),(50,0.08,1.74),(70,0.135,4.49),(90,0.23,11.14),(120,0.304,17.80),(310,0.35,23.32),(99999,0.40,38.82)]
        for l, f, r in tabla:
            if (base_trib/utm) <= l:
                imp = int((base_trib * f) - (r * utm))
                break
        imp = max(0, imp)
        
        # Líquido calculado con 7%
        liq_calc_base = tot_imp - m_afp - legal_7 - m_afc - imp
        
        if abs(liq_calc_base - liq_meta) < 500:
            # ENCONTRADO EL BRUTO. AHORA APLICAMOS EL PLAN REAL DE ISAPRE
            
            m_salud_real = legal_7
            adicional_salud = 0
            warning_msg = ""
            
            if salud_t == "Isapre (UF)":
                valor_plan_pesos = int(plan_uf * uf)
                if valor_plan_pesos > legal_7:
                    m_salud_real = valor_plan_pesos
                    adicional_salud = valor_plan_pesos - legal_7
                    warning_msg = f"⚠️ El Plan Isapre excede el 7% legal. El líquido final será menor al objetivo en ${fmt(adicional_salud)}."
            
            # Líquido Final Real (Descontando el adicional)
            liquido_final_real = tot_imp - m_afp - m_salud_real - m_afc - imp + no_imp
            
            ap_sis = int(b_prev*0.0149)
            ap_mut = int(b_prev*0.0093)
            ap_afc_e = int(b_afc*tasa_afc_emp)
            
            return {
                "Sueldo Base": int(base), "Gratificación": int(grat), "Total Imponible": int(tot_imp),
                "No Imponibles": int(no_imp), "LÍQUIDO_OBJETIVO": int(liquido_obj),
                "LÍQUIDO_FINAL": int(liquido_final_real),
                "AFP": m_afp, "Salud_Legal": legal_7, "Adicional_Salud": adicional_salud, "Salud": m_salud_real,
                "AFC": m_afc, "Impuesto": imp, "Total Descuentos": m_afp + m_salud_real + m_afc + imp,
                "Aportes Empresa": ap_sis + ap_mut + ap_afc_e, 
                "COSTO TOTAL": int(tot_imp+no_imp+ap_sis+ap_mut+ap_afc_e),
                "Warning": warning_msg
            }
            break
        elif liq_calc_base < liq_meta: min_b = base
        else: max_b = base
    return None

# --- 7. INTERFAZ GRÁFICA ---

# SIDEBAR
with st.sidebar:
    st.image("https://www.previred.com/wp-content/uploads/2021/01/logo-previred.png", width=120)
    
    st.markdown("### 🏢 Configuración Empresa")
    # Logo Uploader
    uploaded_logo = st.file_uploader("Logo Empresa", type=["png", "jpg"])
    if uploaded_logo:
        st.session_state.logo_bytes = uploaded_logo.read()
        st.success("Logo cargado")
    
    with st.expander("Datos Empresa (Fijos)", expanded=False):
        st.session_state.empresa['rut'] = st.text_input("RUT Empresa", st.session_state.empresa['rut'])
        st.session_state.empresa['nombre'] = st.text_input("Razón Social", st.session_state.empresa['nombre'])
        st.session_state.empresa['rep_nombre'] = st.text_input("Rep. Legal", st.session_state.empresa['rep_nombre'])
        st.session_state.empresa['rep_rut'] = st.text_input("RUT Rep.", st.session_state.empresa['rep_rut'])
        st.session_state.empresa['direccion'] = st.text_input("Dirección", st.session_state.empresa['direccion'])
        st.session_state.empresa['ciudad'] = st.text_input("Ciudad", st.session_state.empresa['ciudad'])
        st.session_state.empresa['giro'] = st.text_input("Giro", st.session_state.empresa['giro'])

    with st.expander("👤 Datos Trabajador (Opcional)", expanded=False):
        st.session_state.trabajador['nombre'] = st.text_input("Nombre", st.session_state.trabajador['nombre'])
        st.session_state.trabajador['rut'] = st.text_input("RUT", st.session_state.trabajador['rut'])
        st.session_state.trabajador['direccion'] = st.text_input("Domicilio", st.session_state.trabajador['direccion'])
        st.session_state.trabajador['nacimiento'] = st.date_input("Nacimiento", value=st.session_state.trabajador['nacimiento'], min_value=date(1940,1,1), max_value=datetime.now())

    st.divider()
    uf_v, utm_v = obtener_indicadores()
    st.metric("UF", fmt(uf_v).replace("$",""))
    st.metric("UTM", fmt(utm_v))

st.title("HR Suite CEO Edition")
st.markdown("**Sistema Legal y Financiero de Gestión de Personas**")

tabs = st.tabs(["💰 Calculadora & Liquidación", "📋 Perfil de Cargo", "🧠 Análisis CV", "🚀 Carrera", "📝 Contratos", "📊 Indicadores"])

# TAB 1: CALCULADORA
with tabs[0]:
    c1, c2 = st.columns(2)
    with c1:
        liq = st.number_input("Líquido Objetivo ($)", value=1000000, step=50000, format="%d")
        mostrar_miles(liq)
        col = st.number_input("Colación ($)", value=50000, format="%d")
        mov = st.number_input("Movilización ($)", value=50000, format="%d")
    with c2:
        con = st.selectbox("Contrato", ["Indefinido", "Plazo Fijo", "Sueldo Empresarial"])
        afp = st.selectbox("AFP", ["Capital", "Cuprum", "Habitat", "Modelo", "PlanVital", "Uno", "SIN AFP"])
        sal = st.selectbox("Salud", ["Fonasa (7%)", "Isapre (UF)"])
        plan = st.number_input("Plan UF", 0.0) if sal == "Isapre (UF)" else 0.0

    if st.button("SIMULAR SUELDO"):
        res = calcular_nomina_reversa(liq, col, mov, con, afp, sal, plan, uf_v, utm_v, 529000, 87.8, 131.9)
        if res:
            st.session_state.calculo_actual = res
            
            if res['Warning']:
                st.warning(res['Warning'])
            
            k1, k2, k3 = st.columns(3)
            k1.metric("Sueldo Base", fmt(res['Sueldo Base']))
            k2.metric("Líquido Final", fmt(res['LÍQUIDO_FINAL']), delta=f"Objetivo: {fmt(liq)}")
            k3.metric("Costo Empresa", fmt(res['COSTO TOTAL']), delta="Total", delta_color="inverse")
            
            # Liquidación Visual
            st.markdown(f"""
            <div class="liq-box">
                <div class="liq-header">LIQUIDACIÓN DE SUELDO (Simulación)</div>
                <div class="liq-row"><span>Sueldo Base:</span><span>{fmt(res['Sueldo Base'])}</span></div>
                <div class="liq-row"><span>Gratificación Legal:</span><span>{fmt(res['Gratificación'])}</span></div>
                <div class="liq-row" style="background:#f0f0f0;"><span><b>TOTAL IMPONIBLE:</b></span><span><b>{fmt(res['Total Imponible'])}</b></span></div>
                <div class="liq-row"><span>Colación y Movilización:</span><span>{fmt(res['No Imponibles'])}</span></div>
                <br>
                <div class="liq-row"><span>AFP ({afp}):</span><span style="color:#d32f2f;">-{fmt(res['AFP'])}</span></div>
                <div class="liq-row"><span>Salud Legal (7%):</span><span style="color:#d32f2f;">-{fmt(res['Salud_Legal'])}</span></div>
                <div class="liq-row"><span>Adicional Isapre:</span><span style="color:#d32f2f;">-{fmt(res['Adicional_Salud'])}</span></div>
                <div class="liq-row"><span>Seguro Cesantía:</span><span style="color:#d32f2f;">-{fmt(res['AFC'])}</span></div>
                <div class="liq-row"><span>Impuesto Único:</span><span style="color:#d32f2f;">-{fmt(res['Impuesto'])}</span></div>
                
                <div class="liq-total" style="display:flex; justify-content:space-between;">
                    <span>LÍQUIDO A PAGAR:</span><span>{fmt(res['LÍQUIDO_FINAL'])}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
    # Botón de Descarga PDF (Fuera del flujo lógico principal para persistencia)
    if st.session_state.calculo_actual:
        logo_data = st.session_state.get('logo_bytes', None)
        pdf_bytes = generar_pdf_liq_con_logo(st.session_state.calculo_actual, st.session_state.empresa, st.session_state.trabajador, logo_data)
        if pdf_bytes:
            st.download_button("⬇️ Descargar Liquidación (PDF)", pdf_bytes, "liquidacion.pdf", "application/pdf")

# TAB 2: PERFIL (ROBUSTO)
with tabs[1]:
    c1, c2 = st.columns(2)
    cargo = c1.text_input("Cargo", placeholder="Ej: Analista Contable")
    rubros = ["Minería", "Tecnología", "Retail", "Banca", "Salud", "Construcción", "Agroindustria", "Transporte", "Educación", "Servicios"]
    rubro = c2.selectbox("Rubro", rubros)
    
    if cargo:
        st.session_state.cargo_actual = cargo
        perf = generar_perfil_robusto(cargo, rubro)
        
        st.markdown(f"### 📋 {perf['titulo']}")
        st.info(f"**Misión:** {perf['mision']}")
        
        cc1, cc2 = st.columns(2)
        with cc1:
            st.markdown("**🔹 Funciones Principales**")
            for f in perf['funciones']: st.write(f"- {f}")
            st.markdown("**🔹 Competencias**")
            for c in perf['competencias']: st.write(f"- {c}")
        with cc2:
            st.markdown("**🔸 Requisitos**")
            for r in perf['requisitos_duros']: st.write(f"- {r}")
            st.markdown("**🔸 Condiciones**")
            for k in perf['condiciones']: st.write(f"- {k}")

# TAB 3: ANÁLISIS CV (Simulado)
with tabs[2]:
    st.header("Análisis de Brechas")
    st.info("Módulo de demostración. Sube un PDF para ver el score.")
    up = st.file_uploader("Subir CV", type="pdf")
    if up:
        st.success("CV Analizado. Score: 85% - Nivel Senior.")
        st.write("Fortalezas: Excel, ERP, Liderazgo.")
        st.warning("Brechas: Inglés Avanzado.")

# TAB 4: CARRERA
with tabs[3]:
    st.header("Plan de Desarrollo (Cursos)")
    if st.session_state.cargo_actual:
        st.markdown(f"#### Hoja de Ruta para {st.session_state.cargo_actual}")
        st.write("1. **Corto Plazo:** Diplomado en Gestión (6 meses).")
        st.write("2. **Mediano Plazo:** Certificación de Industria.")
        st.write("3. **Largo Plazo:** MBA o Magíster.")
    else: st.warning("Defina cargo en Pestaña 2")

# TAB 5: CONTRATOS
with tabs[4]:
    st.header("Generador Legal (Agent Powered)")
    
    if st.session_state.calculo_actual:
        if not st.session_state.empresa['rut']:
            st.error("⚠️ Complete los datos de la Empresa en la Barra Lateral.")
        else:
            fini = st.date_input("Inicio Contrato", datetime.now())
            tcon = st.selectbox("Tipo Contrato", ["Indefinido", "Plazo Fijo", "Obra Faena"])
            func = st.text_area("Funciones Específicas", "Las propias del cargo.")
            
            condiciones = {"cargo": st.session_state.cargo_actual or "Trabajador", "tipo": tcon, "inicio": fini, "funciones": func}
            
            bio = generar_contrato_legal_cloo(st.session_state.calculo_actual, st.session_state.empresa, st.session_state.trabajador, condiciones)
            st.download_button("⬇️ Descargar Contrato Legal (.DOCX)", bio.getvalue(), "contrato_trabajo.docx")
    else:
        st.info("Primero calcule un sueldo en Pestaña 1.")

# TAB 6: INDICADORES
with tabs[5]:
    st.header("Indicadores Oficiales Previred (Nov 2025)")
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Rentas Topes")
        st.write(f"- Tope AFP/Salud: **87,8 UF**")
        st.write(f"- Tope Seguro Cesantía: **131,9 UF**")
        st.write(f"- Sueldo Mínimo: **$529.000**")
        st.subheader("Tasas AFP")
        st.table(pd.DataFrame({
            "AFP": ["Capital", "Cuprum", "Habitat", "PlanVital", "Provida", "Modelo", "Uno"],
            "Tasa": ["11,44%", "11,44%", "11,27%", "11,16%", "11,45%", "10,58%", "10,46%"]
        }))
    with c2:
        st.subheader("Asignación Familiar")
        st.table(pd.DataFrame({
            "Tramo": ["A", "B", "C", "D"],
            "Renta Tope": ["$620.251", "$905.941", "$1.412.957", "Superior"],
            "Monto": ["$22.007", "$13.505", "$4.267", "$0"]
        }))
        st.subheader("Impuesto 2da Categoría")
        st.image("https://www.sii.cl/valores_y_fechas/impuesto_2da_categoria/img/imp_2da_cat_2025.png", caption="Tabla Oficial SII")
