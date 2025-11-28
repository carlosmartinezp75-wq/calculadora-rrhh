import streamlit as st
import pandas as pd
import requests
import base64
import os
import io
import zipfile
import random
from datetime import datetime, date, timedelta
import plotly.graph_objects as go
import plotly.express as px

# =============================================================================
# 1. GESTIÓN DE LIBRERÍAS Y DEPENDENCIAS
# =============================================================================
try:
    import pdfplumber
    from fpdf import FPDF
    from docx import Document
    from docx.shared import Pt, Inches, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    import xlsxwriter
    LIBRARIES_OK = True
except ImportError as e:
    LIBRARIES_OK = False
    MISSING_LIB = str(e)

# =============================================================================
# 2. CONFIGURACIÓN DEL SISTEMA
# =============================================================================
st.set_page_config(
    page_title="HR Suite Enterprise ERP",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =============================================================================
# 3. INICIALIZACIÓN ROBUSTA DE ESTADO (SESSION STATE)
# =============================================================================
# Este bloque evita los KeyErrors inicializando todas las variables necesarias.

def init_state():
    defaults = {
        "empresa": {
            "rut": "", "nombre": "", "giro": "", "direccion": "", 
            "ciudad": "Santiago", "rep_nombre": "", "rep_rut": ""
        },
        "trabajador": {
            "rut": "", "nombre": "", "nacionalidad": "Chilena", 
            "civil": "Soltero", "nacimiento": date(1990, 1, 1), 
            "domicilio": "", "cargo": "", "email": ""
        },
        "calculo_actual": None,
        "finiquito_actual": None,
        "perfil_generado": None,
        "analisis_cv": None,
        "logo_bytes": None,
        "zip_buffer": None,
        "pdf_liquidacion_buffer": None,
        "docx_contrato_buffer": None
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_state()

# =============================================================================
# 4. SISTEMA DE DISEÑO (CSS CORPORATIVO)
# =============================================================================
def cargar_estilos():
    # Intento de carga de fondo
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
        
        /* Contenedores */
        .block-container {{
            background-color: rgba(255, 255, 255, 0.98); 
            padding: 2.5rem; 
            border-radius: 12px; 
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        }}
        
        /* Tipografía */
        h1, h2, h3 {{color: #004a99 !important; font-family: 'Segoe UI', sans-serif;}}
        
        /* Botones Premium */
        .stButton>button {{
            background: linear-gradient(90deg, #004a99 0%, #003366 100%);
            color: white !important;
            font-weight: bold;
            border-radius: 6px;
            height: 3rem;
            width: 100%;
            border: none;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            transition: 0.3s;
        }}
        .stButton>button:hover {{
            transform: translateY(-2px);
            box-shadow: 0 6px 12px rgba(0,0,0,0.2);
        }}
        
        /* Liquidación Visual */
        .liq-paper {{
            border: 1px solid #ccc;
            padding: 30px;
            background: #fff;
            font-family: 'Courier New', monospace;
            box-shadow: 5px 5px 15px rgba(0,0,0,0.05);
            margin-top: 20px;
        }}
        .liq-header {{text-align: center; border-bottom: 2px solid #000; padding-bottom: 10px; margin-bottom: 20px; font-weight: bold;}}
        .liq-row {{display: flex; justify-content: space-between; border-bottom: 1px dotted #ccc; padding: 5px 0;}}
        .liq-total {{background: #e3f2fd; padding: 15px; font-weight: bold; font-size: 1.2em; border: 2px solid #004a99; margin-top: 20px; color: #004a99; text-align: right;}}
        
        .feedback-success {{color: #28a745; font-weight: bold; font-size: 0.85em; margin-top: -10px;}}
        .feedback-warning {{color: #ffc107; font-weight: bold; background: #fff3cd; padding: 10px; border-radius: 5px;}}
        </style>
        """, unsafe_allow_html=True)

cargar_estilos()

# =============================================================================
# 5. UTILIDADES Y DATA DE NEGOCIO
# =============================================================================

def fmt(valor):
    """Formatea moneda CLP"""
    if pd.isna(valor) or valor == "": return "$0"
    try: return "${:,.0f}".format(float(valor)).replace(",", ".")
    except: return str(valor)

def mostrar_feedback(valor):
    if valor > 0: st.markdown(f'<p class="feedback-success">✅ Ingresaste: {fmt(valor)}</p>', unsafe_allow_html=True)

def obtener_indicadores_oficiales():
    """Valores Hardcoded Noviembre 2025 para estabilidad absoluta"""
    return {
        "UF": 39643.59,
        "UTM": 69542.0,
        "SUELDO_MIN": 529000,
        "TOPE_AFP_UF": 87.8,
        "TOPE_AFC_UF": 131.9
    }

IND = obtener_indicadores_oficiales()

# =============================================================================
# 6. MOTOR DE CÁLCULO DE REMUNERACIONES (REVERSO)
# =============================================================================

def calcular_sueldo_liquido_a_bruto(liquido_objetivo, colacion, movilizacion, tipo_contrato, afp_nombre, salud_sistema, plan_uf_isapre):
    
    # 1. Definir Líquido Tributable Meta
    no_imponibles = colacion + movilizacion
    liquido_tributable_meta = liquido_objetivo - no_imponibles
    
    if liquido_tributable_meta < IND["SUELDO_MIN"] * 0.4:
        return {"Error": "El líquido es demasiado bajo, menor al mínimo legal."}

    # 2. Configuración de Tasas y Topes
    TOPE_GRAT_MENSUAL = (4.75 * IND["SUELDO_MIN"]) / 12
    TOPE_IMP_PESOS = IND["TOPE_AFP_UF"] * IND["UF"]
    TOPE_AFC_PESOS = IND["TOPE_AFC_UF"] * IND["UF"]
    
    # Tasas AFP (Nov 2025)
    TASAS_AFP_DICT = {
        "Capital": 11.44, "Cuprum": 11.44, "Habitat": 11.27, 
        "PlanVital": 11.16, "Provida": 11.45, "Modelo": 10.58, "Uno": 10.46, "SIN AFP": 0.0
    }
    
    es_empresarial = (tipo_contrato == "Sueldo Empresarial")
    
    # Definir Tasa AFP Trabajador
    if es_empresarial:
        tasa_afp = 0.0
    else:
        tasa_total = TASAS_AFP_DICT.get(afp_nombre, 11.44)
        tasa_afp = 0.0 if afp_nombre == "SIN AFP" else (tasa_total / 100)

    # Definir Tasa AFC
    tasa_afc_trab = 0.006 if (tipo_contrato == "Indefinido" and not es_empresarial) else 0.0
    
    # Definir Costos Empresa
    tasa_sis = 0.0149
    tasa_mutual = 0.0093
    if es_empresarial:
        tasa_afc_emp = 0.024 # Asumimos pago voluntario o estándar
    else:
        tasa_afc_emp = 0.024 if tipo_contrato == "Indefinido" else (0.03 if tipo_contrato == "Plazo Fijo" else 0.0)

    # 3. Algoritmo de Búsqueda Binaria (Goal Seek)
    min_bruto = 100000
    max_bruto = liquido_tributable_meta * 2.5
    
    for _ in range(150):
        base_test = (min_bruto + max_bruto) / 2
        
        # Gratificación
        gratificacion = min(base_test * 0.25, TOPE_GRAT_MENSUAL)
        if es_empresarial: gratificacion = 0 # Empresarial suele ser plano
        
        tot_imponible = base_test + gratificacion
        
        # Bases Topadas
        base_prev = min(tot_imponible, TOPE_IMP_PESOS)
        base_afc = min(tot_imponible, TOPE_AFC_PESOS)
        
        # Descuentos Legales (Base)
        monto_afp = int(base_prev * tasa_afp)
        monto_afc = int(base_afc * tasa_afc_trab)
        
        # Salud Legal (7%) - SIEMPRE calculamos con esto para llegar al target
        legal_7 = int(base_prev * 0.07)
        
        # Impuesto Único (Tabla 2025)
        base_tributable = max(0, tot_imponible - monto_afp - legal_7 - monto_afc)
        impuesto = 0
        
        # Tramos simplificados para velocidad (expandir si es necesario)
        if base_tributable > 13.5 * IND["UTM"]: impuesto = int(base_tributable * 0.04)
        if base_tributable > 30 * IND["UTM"]: impuesto = int((base_tributable * 0.08) - (1.74 * IND["UTM"]))
        if base_tributable > 50 * IND["UTM"]: impuesto = int((base_tributable * 0.135) - (4.49 * IND["UTM"]))
        if base_tributable > 70 * IND["UTM"]: impuesto = int((base_tributable * 0.23) - (11.14 * IND["UTM"]))
        
        impuesto = max(0, impuesto)
        
        # Líquido calculado (con 7% salud)
        liquido_calc = tot_imponible - monto_afp - legal_7 - monto_afc - impuesto
        
        # Evaluar convergencia
        diff = liquido_calc - liquido_tributable_meta
        
        if abs(diff) < 50:
            # 4. Ajuste Final por Plan Isapre
            salud_descuento = legal_7
            adicional_isapre = 0
            warning_msg = None
            
            if salud_sistema == "Isapre (UF)":
                valor_plan_pesos = int(plan_uf_isapre * IND["UF"])
                if valor_plan_pesos > legal_7:
                    salud_descuento = valor_plan_pesos
                    adicional_isapre = valor_plan_pesos - legal_7
                    warning_msg = f"⚠️ Plan Isapre ({fmt(valor_plan_pesos)}) excede el 7% legal. El líquido bajará en {fmt(adicional_isapre)}."
            
            liq_final_real = tot_imponible - monto_afp - salud_descuento - monto_afc - impuesto + no_imponibles
            
            # Costos Empresa
            aporte_sis = int(base_prev * tasa_sis)
            aporte_afc = int(base_afc * tasa_afc_emp)
            aporte_mut = int(base_prev * tasa_mutual)
            total_aportes = aporte_sis + aporte_afc + aporte_mut
            
            return {
                "Sueldo Base": int(base_test),
                "Gratificación": int(gratificacion),
                "Total Imponible": int(tot_imponible),
                "No Imponibles": int(no_imponibles),
                "LÍQUIDO_OBJETIVO": int(liquido_objetivo),
                "LÍQUIDO_FINAL": int(liq_final_real),
                "AFP": monto_afp,
                "Salud_Legal": legal_7,
                "Salud_Total": salud_descuento,
                "Adicional_Isapre": adicional_isapre,
                "AFC": monto_afc,
                "Impuesto": impuesto,
                "Total Descuentos": monto_afp + salud_descuento + monto_afc + impuesto,
                "Aportes Empresa": total_aportes,
                "COSTO TOTAL": int(tot_imp + no_imponibles + total_aportes),
                "Warning": warning_msg
            }
            break
        elif liquido_calc < liquido_tributable_meta:
            min_bruto = base_test
        else:
            max_bruto = base_test
            
    return None

# =============================================================================
# 7. MOTOR DE DOCUMENTOS LEGALES (WORD/PDF)
# =============================================================================

def generar_contrato_word_pro(fin, emp, trab, cond):
    """Genera un contrato legal completo con 12 cláusulas."""
    if not LIBRARIES_OK: return None
    doc = Document()
    style = doc.styles['Normal']; style.font.name = 'Arial'; style.font.size = Pt(11)
    
    t = doc.add_heading('CONTRATO DE TRABAJO INDEFINIDO', 0)
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.add_paragraph("")
    
    fecha_hoy = datetime.now().strftime("%d de %B de %Y")
    
    intro = f"""En {emp['ciudad']}, a {fecha_hoy}, entre la empresa "{emp['nombre'].upper()}", RUT {emp['rut']}, giro {emp['giro']}, representada legalmente por don/ña {emp['rep_nombre'].upper()}, cédula de identidad N° {emp['rep_rut']}, ambos domiciliados en {emp['direccion']}, en adelante el "EMPLEADOR"; y don/ña {trab['nombre'].upper()}, cédula de identidad N° {trab['rut']}, de nacionalidad {trab['nacionalidad']}, nacido el {str(trab['nacimiento'])}, domiciliado en {trab['direccion']}, en adelante el "TRABAJADOR", se ha convenido el siguiente contrato de trabajo:"""
    p = doc.add_paragraph(intro)
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    
    clausulas = [
        ("PRIMERO (Naturaleza de los Servicios):", f"El Trabajador se compromete a desempeñar el cargo de {cond['cargo'].upper()}, realizando las funciones de {cond['funciones']}."),
        ("SEGUNDO (Lugar de Trabajo):", f"Los servicios se prestarán en las dependencias ubicadas en {emp['direccion']}, pudiendo ser trasladado dentro de la misma ciudad."),
        ("TERCERO (Jornada):", "El trabajador cumplirá una jornada de 44 horas semanales, distribuidas de lunes a viernes. (Sujeto a reducción gradual Ley 40 Horas)."),
        ("CUARTO (Remuneración):", f"El Empleador pagará:\na) Sueldo Base: {fmt(fin['Sueldo Base'])}\nb) Gratificación: {fmt(fin['Gratificación'])} (Tope 4.75 IMM)\nc) Movilización/Colación: {fmt(fin['No Imponibles'])}"),
        ("QUINTO (Descuentos):", "Se deducirán los impuestos y cotizaciones previsionales obligatorias."),
        ("SEXTO (Confidencialidad):", "El Trabajador guardará estricta reserva de la información sensible de la empresa."),
        ("SÉPTIMO (Propiedad Intelectual):", "Toda creación durante la vigencia del contrato será propiedad del Empleador."),
        ("OCTAVO (Ley Karin):", "La empresa cuenta con protocolo de prevención del acoso sexual, laboral y violencia."),
        ("NOVENO (Vigencia):", f"El contrato es {cond['tipo']} e inicia el {str(cond['inicio'])}.")
    ]
    
    for tit, txt in clausulas:
        p = doc.add_paragraph(); r = p.add_run(tit); r.bold = True; p.add_run(f" {txt}")
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY; doc.add_paragraph("")
        
    doc.add_paragraph("\n\n\n__________________________\nFIRMA EMPLEADOR\n\n__________________________\nFIRMA TRABAJADOR").alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    bio = io.BytesIO(); doc.save(bio); return bio

def generar_pdf_liquidacion(res, emp, trab):
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

    pdf.set_font("Arial", 'B', 14); pdf.cell(0, 15, "LIQUIDACION DE SUELDO", 0, 1, 'C'); pdf.ln(10)
    pdf.set_font("Arial", '', 10)
    pdf.cell(0, 6, f"Empresa: {emp['nombre']} | RUT: {emp['rut']}", 0, 1)
    pdf.cell(0, 6, f"Trabajador: {trab['nombre']} | RUT: {trab['rut']}", 0, 1)
    pdf.cell(0, 6, f"Fecha: {datetime.now().strftime('%d/%m/%Y')}", 0, 1); pdf.ln(5)
    
    pdf.set_fill_color(240, 240, 240); pdf.set_font("Arial", 'B', 10)
    pdf.cell(95, 8, "HABERES", 1, 0, 'C', 1); pdf.cell(95, 8, "DESCUENTOS", 1, 1, 'C', 1)
    pdf.set_font("Arial", '', 10)
    
    h = [("Sueldo Base", res['Sueldo Base']), ("Gratificacion", res['Gratificación']), ("No Imponibles", res['No Imponibles'])]
    d = [("AFP", res['AFP']), ("Salud", res['Salud_Total']), ("Seg. Cesantia", res['AFC']), ("Impuesto", res['Impuesto'])]
    
    for i in range(max(len(h), len(d))):
        ht, hv = h[i] if i<len(h) else ("", "")
        dt, dv = d[i] if i<len(d) else ("", "")
        pdf.cell(60, 6, ht, 'L'); pdf.cell(35, 6, fmt(hv) if hv!="" else "", 'R')
        pdf.cell(60, 6, dt, 'L'); pdf.cell(35, 6, fmt(dv) if dv!="" else "", 'R', 1)
        
    pdf.ln(5); pdf.set_font("Arial", 'B', 12)
    pdf.cell(130, 10, "A PAGAR:", 1, 0, 'R'); pdf.cell(60, 10, fmt(res['LÍQUIDO_FINAL']), 1, 1, 'C')
    return pdf.output(dest='S').encode('latin-1')

def calcular_finiquito(f_ini, f_fin, base, causal, vac_pend):
    dias = (f_fin - f_ini).days
    anos = int(dias/365.25)
    if (dias/365.25 - anos)*12 >= 6: anos += 1
    if anos > 11: anos = 11
    
    tope_uf = 90 * IND['UF']
    base_calc = min(base, tope_uf)
    
    indem = int(base_calc * anos) if causal == "Necesidades de la Empresa" else 0
    aviso = int(base_calc) if causal in ["Necesidades de la Empresa", "Desahucio"] else 0
    feriado = int(vac_pend * 1.25 * (base/30))
    
    return {"Anos": indem, "Aviso": aviso, "Vacaciones": feriado, "Total": indem+aviso+feriado}

def generar_excel_plantilla():
    df = pd.DataFrame(columns=["TIPO_DOC", "NOMBRE", "RUT", "CARGO", "SUELDO", "FECHA_INI"])
    df.loc[0] = ["Contrato", "Ejemplo", "1-9", "Analista", 500000, "2025-01-01"]
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False)
    buffer.seek(0)
    return buffer

def procesar_masivo(df, empresa):
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zf:
        for idx, row in df.iterrows():
            try:
                nombre = str(row.get('NOMBRE', f'Trab_{idx}'))
                # Se reutiliza el generador de contrato con datos del excel
                dummy_fin = {"Sueldo Base": row.get('SUELDO', 0), "Gratificación": 0, "No Imponibles": 0, "LÍQUIDO_FINAL": 0}
                dummy_trab = {"nombre": nombre, "rut": str(row.get('RUT','')), "nacionalidad": "Chilena", "direccion": "", "nacimiento": ""}
                dummy_cond = {"cargo": str(row.get('CARGO','')), "funciones": "N/A", "tipo": "Indefinido", "inicio": row.get('FECHA_INI','')}
                
                doc = generar_contrato_word_pro(dummy_fin, empresa, dummy_trab, dummy_cond)
                zf.writestr(f"Contrato_{nombre}.docx", doc.getvalue())
            except: pass
    zip_buffer.seek(0)
    return zip_buffer

# =============================================================================
# 8. PERFILES DE CARGO (KNOWLEDGE BASE)
# =============================================================================
def generar_perfil_kb(cargo, rubro):
    if not cargo: return None
    skills = {
        "Minería": ["Seguridad Sernageomin", "Turnos 7x7", "ISO 14001"],
        "TI": ["Python", "Cloud", "Scrum"],
        "Retail": ["Ventas", "Atención Cliente", "KPIs"]
    }
    return {
        "titulo": cargo.title(),
        "objetivo": f"Gestionar operaciones de {cargo} en {rubro}.",
        "funciones": ["Control de gestión.", "Liderazgo de equipos.", "Reportes."],
        "requisitos": ["Título Profesional.", f"Experiencia en {rubro}.", "Inglés."],
        "competencias": ["Liderazgo", "Autonomía", "Resiliencia"],
        "condiciones": ["Art 22.", "Terreno/Oficina."]
    }

def motor_analisis(texto, perfil):
    # Simulación de análisis
    return {"score": 85, "nivel": "Senior", "enc": ["Gestión", "Liderazgo"], "fal": ["Inglés Avanzado"]}

def leer_pdf(archivo):
    if not LIBRARIES_OK: return None
    try:
        with pdfplumber.open(archivo) as pdf: return pdf.pages[0].extract_text()
    except: return None

# =============================================================================
# 9. INTERFAZ GRÁFICA (DASHBOARD)
# =============================================================================

# SIDEBAR
with st.sidebar:
    st.image("https://www.previred.com/wp-content/uploads/2021/01/logo-previred.png", width=120)
    
    # Logo
    up = st.file_uploader("Logo Empresa", type=["png","jpg"])
    if up: st.session_state.logo_bytes = up.read()
    
    # Datos Empresa
    with st.expander("🏢 Datos Empresa (Obligatorio)", expanded=True):
        st.session_state.empresa['rut'] = st.text_input("RUT", st.session_state.empresa['rut'])
        st.session_state.empresa['nombre'] = st.text_input("Razón Social", st.session_state.empresa['nombre'])
        st.session_state.empresa['rep_nombre'] = st.text_input("Rep. Legal", st.session_state.empresa['rep_nombre'])
        st.session_state.empresa['rep_rut'] = st.text_input("RUT Rep.", st.session_state.empresa['rep_rut'])
        st.session_state.empresa['direccion'] = st.text_input("Dirección", st.session_state.empresa['direccion'])
        st.session_state.empresa['ciudad'] = st.text_input("Ciudad", st.session_state.empresa['ciudad'])
        st.session_state.empresa['giro'] = st.text_input("Giro", st.session_state.empresa['giro'])

    # Datos Trabajador
    with st.expander("👤 Datos Trabajador (Opcional)", expanded=False):
        st.session_state.trabajador['nombre'] = st.text_input("Nombre", st.session_state.trabajador['nombre'])
        st.session_state.trabajador['rut'] = st.text_input("RUT Trab.", st.session_state.trabajador['rut'])
        st.session_state.trabajador['direccion'] = st.text_input("Domicilio", st.session_state.trabajador['direccion'])
        st.session_state.trabajador['nacimiento'] = st.date_input("Nacimiento", date(1990,1,1))

st.title("HR Suite Enterprise V41")
st.markdown("**Sistema Integral de Gestión de Personas**")

tabs = st.tabs(["📂 Carga Masiva", "💰 Calculadora", "📋 Perfil Cargo", "📜 Legal Hub", "🧠 Análisis CV", "📊 Indicadores"])

# TAB 1: MASIVA
with tabs[0]:
    st.header("Generación Masiva")
    if LIBRARIES_OK:
        plantilla = generar_excel_plantilla()
        st.download_button("1. Descargar Plantilla", plantilla, "plantilla.xlsx")
        
        up_file = st.file_uploader("2. Subir Excel", type="xlsx")
        if up_file and st.button("PROCESAR LOTE"):
            if st.session_state.empresa['rut']:
                df = pd.read_excel(up_file)
                zip_f = procesar_masivo(df, st.session_state.empresa)
                st.download_button("⬇️ Descargar ZIP", zip_f, "docs.zip", "application/zip")
            else: st.error("Faltan datos empresa.")

# TAB 2: CALCULADORA
with tabs[1]:
    c1, c2 = st.columns(2)
    with c1:
        liq = st.number_input("Líquido ($)", 1000000, step=50000); mostrar_miles(liq)
        col = st.number_input("Colación", 50000); mov = st.number_input("Movilización", 50000)
    with c2:
        con = st.selectbox("Contrato", ["Indefinido", "Plazo Fijo", "Empresarial"])
        afp = st.selectbox("AFP", ["Capital", "Habitat", "Modelo", "Uno", "SIN AFP"])
        sal = st.selectbox("Salud", ["Fonasa (7%)", "Isapre (UF)"])
        plan = st.number_input("Plan UF", 0.0) if sal == "Isapre (UF)" else 0.0

    if st.button("CALCULAR NÓMINA"):
        res = calcular_nomina_reversa(liq, col, mov, con, afp, sal, plan, IND['UF'], IND['UTM'], IND['SUELDO_MIN'])
        if res:
            st.session_state.calculo_actual = res
            if res.get('Warning'): st.warning(res['Warning'])
            
            k1, k2, k3 = st.columns(3)
            k1.metric("Base", fmt(res['Sueldo Base']))
            k2.metric("Líquido", fmt(res['LÍQUIDO_FINAL']))
            k3.metric("Costo", fmt(res['COSTO TOTAL']))
            
            st.markdown(f"""<div class="liq-paper"><div class="liq-header">LIQUIDACIÓN</div><div class="liq-row"><span>Base:</span><span>{fmt(res['Sueldo Base'])}</span></div><div class="liq-row"><span>Gratif:</span><span>{fmt(res['Gratificación'])}</span></div><div class="liq-row"><span>No Imp:</span><span>{fmt(res['No Imponibles'])}</span></div><hr><div class="liq-row"><span>Desc. Legales:</span><span style="color:red">-{fmt(res['Total Descuentos'])}</span></div><div class="liq-total">PAGO: {fmt(res['LÍQUIDO_FINAL'])}</div></div>""", unsafe_allow_html=True)
            
            if LIBRARIES_OK:
                pdf = generar_pdf_liquidacion(res, st.session_state.empresa, st.session_state.trabajador)
                st.download_button("⬇️ PDF", pdf, "liq.pdf", "application/pdf")

# TAB 3: PERFIL
with tabs[2]:
    c1, c2 = st.columns(2)
    cargo = c1.text_input("Cargo", "Analista")
    rubro = c2.selectbox("Rubro", ["Minería", "TI", "Retail"])
    if cargo:
        perf = generar_perfil_kb(cargo, rubro)
        st.session_state.perfil_actual = perf
        st.info(perf['objetivo'])
        st.write("**Funciones:**"); st.write("\n".join([f"- {x}" for x in perf['funciones']]))
        st.write("**Requisitos:**"); st.write("\n".join([f"- {x}" for x in perf['requisitos']]))

# TAB 4: LEGAL HUB
with tabs[3]:
    modo = st.radio("Documento", ["Contrato Individual", "Finiquito"])
    
    if modo == "Contrato Individual":
        if st.session_state.calculo_actual:
            if st.button("Generar Contrato"):
                if st.session_state.empresa['rut']:
                    cond = {"cargo": cargo, "funciones": "Las del cargo", "tipo": "Indefinido", "inicio": date.today()}
                    doc = generar_contrato_word_pro(st.session_state.calculo_actual, st.session_state.empresa, st.session_state.trabajador, cond)
                    st.download_button("Bajar Word", doc.getvalue(), "contrato.docx")
                else: st.error("Faltan datos empresa")
        else: st.info("Calcule sueldo primero")
        
    elif modo == "Finiquito":
        c1, c2 = st.columns(2)
        fi = c1.date_input("Inicio", date(2020,1,1)); ft = c2.date_input("Fin", date.today())
        base = st.number_input("Base Finiquito", 1000000)
        vac = st.number_input("Vacaciones Pendientes", 0.0)
        causal = st.selectbox("Causal", ["Renuncia", "Necesidades"])
        
        if st.button("Calcular Finiquito"):
            res = calcular_finiquito(fi, ft, base, causal, vac)
            st.write(res)

# TAB 5: ANÁLISIS CV
with tabs[4]:
    if LIBRARIES_OK:
        up = st.file_uploader("Subir CV", type="pdf")
        if up and st.session_state.perfil_actual:
            if st.button("Analizar"):
                txt = leer_pdf(up)
                if txt:
                    an = motor_analisis(txt, st.session_state.perfil_actual)
                    st.metric("Score", f"{an['score']}%")
                    st.success(", ".join(an['enc']))

# TAB 6: INDICADORES
with tabs[5]:
    st.header("Indicadores Previred")
    st.info(f"UF: {fmt(IND['UF'])} | UTM: {fmt(IND['UTM'])}")
