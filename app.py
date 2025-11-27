import streamlit as st
import pandas as pd
import requests
import base64
import os
import io
import random
import tempfile
from datetime import datetime, date, timedelta
import plotly.graph_objects as go
import plotly.express as px

# =============================================================================
# 0. VALIDACIÓN DE LIBRERÍAS Y ENTORNO
# =============================================================================
# Verificamos que las librerías críticas para generar documentos estén instaladas.
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
# 1. CONFIGURACIÓN INICIAL DEL SISTEMA
# =============================================================================
st.set_page_config(
    page_title="HR Suite Enterprise V33",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inicialización de Variables de Estado (Memoria de la App)
# Esto evita que se borren los datos al cambiar de pestaña.

if 'empresa' not in st.session_state:
    st.session_state.empresa = {
        "rut": "", 
        "nombre": "", 
        "rep_nombre": "", 
        "rep_rut": "", 
        "direccion": "", 
        "ciudad": "Santiago", 
        "giro": "Servicios Profesionales"
    }

if 'trabajador' not in st.session_state:
    st.session_state.trabajador = {
        "nombre": "", 
        "rut": "", 
        "nacionalidad": "Chilena", 
        "civil": "Soltero", 
        "nacimiento": date(1990, 1, 1),
        "domicilio": "",
        "cargo": ""
    }

if 'calculo_actual' not in st.session_state: 
    st.session_state.calculo_actual = None

if 'logo_bytes' not in st.session_state: 
    st.session_state.logo_bytes = None

# =============================================================================
# 2. SISTEMA DE DISEÑO VISUAL (CSS)
# =============================================================================
def cargar_estilos_visuales():
    """Configura la apariencia corporativa de la aplicación."""
    
    # Intento de cargar fondo personalizado si existe
    nombres_posibles = ['fondo.png', 'fondo.jpg', 'fondo_marca.png']
    img_fondo = next((n for n in nombres_posibles if os.path.exists(n)), None)
    
    css_fondo = ""
    if img_fondo:
        try:
            with open(img_fondo, "rb") as f: 
                b64_fondo = base64.b64encode(f.read()).decode()
            css_fondo = f"""
            [data-testid="stAppViewContainer"] {{
                background-image: url("data:image/png;base64,{b64_fondo}");
                background-size: cover;
                background-position: center;
                background-attachment: fixed;
            }}
            """
        except: pass
    else:
        # Fondo por defecto elegante si no hay imagen
        css_fondo = """
        [data-testid="stAppViewContainer"] {
            background: linear-gradient(135deg, #fdfbfb 0%, #ebedee 100%);
        }
        """

    st.markdown(f"""
        <style>
        {css_fondo}
        
        /* Contenedor Principal (Tarjeta Blanca) */
        .block-container {{
            background-color: rgba(255, 255, 255, 0.98); 
            padding: 3rem; 
            border-radius: 15px; 
            box-shadow: 0 10px 40px rgba(0,0,0,0.15);
        }}
        
        /* Tipografía Corporativa */
        h1, h2, h3, h4 {{
            color: #004a99 !important; 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
            font-weight: 800;
        }}
        
        /* Inputs y Selectores */
        .stTextInput input, .stNumberInput input, .stSelectbox div[data-baseweb="select"] {{
            background-color: #f8f9fa;
            border: 1px solid #ced4da;
            color: #004a99;
            font-weight: 600;
            border-radius: 8px;
        }}
        
        /* Botones de Acción (Call to Action) */
        .stButton>button {{
            background: linear-gradient(90deg, #004a99 0%, #003366 100%);
            color: white !important;
            font-weight: bold;
            font-size: 16px;
            border-radius: 8px;
            width: 100%;
            height: 3.5rem;
            border: none;
            box-shadow: 0 4px 10px rgba(0,0,0,0.2);
            text-transform: uppercase;
            letter-spacing: 1px;
            transition: all 0.3s ease;
        }}
        .stButton>button:hover {{
            transform: translateY(-2px);
            box-shadow: 0 6px 15px rgba(0, 74, 153, 0.4);
        }}
        
        /* Visualización de Liquidación (HTML Puro) */
        .liq-box {{
            border: 1px solid #ccc; 
            padding: 30px; 
            background: #fff; 
            font-family: 'Courier New', monospace; 
            box-shadow: 5px 5px 20px rgba(0,0,0,0.05);
            margin-top: 20px;
        }}
        .liq-header {{
            text-align: center; 
            border-bottom: 2px solid #000; 
            padding-bottom: 10px; 
            margin-bottom: 20px; 
            font-weight: bold; 
            font-size: 1.2em;
        }}
        .liq-row {{
            display: flex; 
            justify-content: space-between; 
            border-bottom: 1px dotted #ddd; 
            padding: 6px 0;
        }}
        .liq-total {{
            background-color: #e3f2fd; 
            padding: 15px; 
            font-weight: bold; 
            font-size: 1.4em; 
            border: 2px solid #004a99; 
            margin-top: 25px; 
            color: #004a99;
            text-align: right;
        }}
        
        /* Feedback Visual */
        .miles-feedback {{
            font-size: 0.85rem; 
            color: #2e7d32; 
            font-weight: bold; 
            margin-top: -10px; 
            margin-bottom: 15px;
        }}
        
        /* Ocultar elementos de Streamlit no deseados */
        #MainMenu, footer {{visibility: hidden;}}
        </style>
        """, unsafe_allow_html=True)

cargar_estilos_visuales()

# =============================================================================
# 3. FUNCIONES UTILITARIAS Y DE DATOS
# =============================================================================

def fmt(valor):
    """Formatea un número con separadores de miles y signo peso (Ej: $1.500.000)."""
    if valor is None or pd.isna(valor): return "$0"
    return "${:,.0f}".format(valor).replace(",", ".")

def mostrar_miles(valor): 
    """Muestra un mensaje verde debajo del input para confirmar el monto ingresado."""
    if valor > 0: 
        st.markdown(f'<p class="miles-feedback">✅ Ingresaste: {fmt(valor)}</p>', unsafe_allow_html=True)

def obtener_indicadores_economicos():
    """
    Obtiene UF y UTM. Si falla la API, usa valores de contingencia (Previred Nov 2025).
    """
    try:
        r = requests.get('https://mindicador.cl/api', timeout=2)
        d = r.json()
        return float(d['uf']['valor']), float(d['utm']['valor'])
    except:
        return 39643.59, 69542.0

# =============================================================================
# 4. MOTORES DE CÁLCULO FINANCIERO Y LEGAL
# =============================================================================

def calcular_nomina_reversa(liquido_obj, col, mov, contrato, afp_n, salud_t, plan_uf, uf, utm, s_min):
    """
    Motor de Cálculo Inverso (Gross-up).
    Itera para encontrar el Sueldo Base que resulte en el Líquido Objetivo.
    Maneja la lógica de 'Isapre Target' (7% base vs plan real).
    """
    no_imp = col + mov
    # 1. Definir Líquido Tributable Objetivo (Sueldo - No Imponibles)
    liq_meta = liquido_obj - no_imp
    
    if liq_meta < s_min * 0.4: return None
    
    # Constantes Legales
    TOPE_GRAT = (4.75 * s_min) / 12
    # Topes Imponibles (UF)
    TOPE_IMP_UF = 87.8
    TOPE_AFC_UF = 131.9
    
    # Tasas AFP (Nov 2025)
    TASAS_AFP = {"Capital":1.44,"Cuprum":1.44,"Habitat":1.27,"PlanVital":1.16,"Provida":1.45,"Modelo":0.58,"Uno":0.49,"SIN AFP":0.0}
    
    # Configuración según Contrato
    es_emp = (contrato == "Sueldo Empresarial")
    tasa_afp = 0.0 if es_emp else (0.10 + (TASAS_AFP.get(afp_n, 1.44)/100))
    if afp_n == "SIN AFP": tasa_afp = 0.0
    
    tasa_afc_emp = 0.024
    tasa_afc_trab = 0.006 if (contrato == "Indefinido" and not es_emp) else 0.0
    if contrato == "Plazo Fijo": tasa_afc_emp = 0.03
    
    # ALGORITMO DE BÚSQUEDA BINARIA
    min_b, max_b = 100000, liq_meta * 2.5
    
    for _ in range(200): # 200 iteraciones para precisión de $1 peso
        base = (min_b + max_b) / 2
        grat = min(base * 0.25, TOPE_GRAT)
        if es_emp: grat = 0
        tot_imp = base + grat
        
        b_prev = min(tot_imp, TOPE_IMP_UF*uf)
        b_afc = min(tot_imp, TOPE_AFC_UF*uf)
        
        m_afp = int(b_prev * tasa_afp)
        m_afc_t = int(b_afc * tasa_afc_trab)
        
        # PARA EL CÁLCULO TARGET: Usamos siempre el 7% legal primero
        legal_7 = int(b_prev * 0.07)
        
        # Impuesto Único (Usando 7% como rebaja teórica)
        base_trib = max(0, tot_imp - m_afp - legal_7 - m_afc_t)
        
        # Tabla Impuesto Nov 2025 (Simplificada tramos bajos/medios)
        imp = 0
        if base_trib > 13.5*utm: imp = int(base_trib*0.04)
        if base_trib > 30*utm: imp = int((base_trib*0.08) - (1.74*utm))
        if base_trib > 50*utm: imp = int((base_trib*0.135) - (4.49*utm))
        imp = max(0, imp)
        
        # Líquido calculado con 7%
        liq_calc_base = tot_imp - m_afp - legal_7 - m_afc_t - imp
        
        if abs(liq_calc_base - liq_meta) < 100:
            # ¡BRUTO ENCONTRADO! 
            # AHORA APLICAMOS LA REALIDAD DEL PLAN DE ISAPRE
            
            salud_descuento_real = legal_7
            adicional_salud = 0
            warning_msg = None
            
            if salud_t == "Isapre (UF)":
                valor_plan_pesos = int(plan_uf * uf)
                if valor_plan_pesos > legal_7:
                    # El plan es mayor al 7%. El trabajador paga la diferencia.
                    salud_descuento_real = valor_plan_pesos
                    adicional_salud = valor_plan_pesos - legal_7
                    warning_msg = f"⚠️ El plan de Isapre excede el 7% legal. El líquido final disminuirá en {fmt(adicional_salud)} respecto al objetivo."
            
            # Recalculamos Líquido Final Real
            liquido_final_real = tot_imp - m_afp - salud_descuento_real - m_afc_t - imp + no_imp
            
            # Costos Empresa
            ap_sis = int(b_prev*0.0149)
            ap_mut = int(b_prev*0.0093)
            ap_afc_e = int(b_afc*tasa_afc_emp)
            
            return {
                "Sueldo Base": int(base), 
                "Gratificación": int(grat), 
                "Total Imponible": int(tot_imp),
                "No Imponibles": int(no_imp), 
                "LÍQUIDO_OBJETIVO": int(liquido_obj),
                "LÍQUIDO_FINAL": int(liquido_final_real),
                "AFP": m_afp, 
                "Salud_Legal": legal_7,
                "Adicional_Salud": adicional_salud,
                "Salud_Total": salud_descuento_real,
                "AFC": m_afc_t, 
                "Impuesto": imp,
                "Aportes Empresa": ap_sis + ap_mut + ap_afc_e, 
                "COSTO TOTAL": int(tot_imp+no_imp+ap_sis+ap_mut+ap_afc_e),
                "Warning": warning_msg
            }
            break
        elif liq_calc_base < liq_meta: min_b = base
        else: max_b = base
    return None

def calcular_finiquito(f_ini, f_fin, sueldo_base, causal, vac_pend, tope_indem_uf=90):
    """Calcula indemnizaciones legales con topes."""
    # 1. Antigüedad
    dias_trabajados = (f_fin - f_ini).days
    anos = dias_trabajados / 365.25
    anos_pago = int(anos)
    if (anos - anos_pago) * 12 >= 6: anos_pago += 1
    if anos_pago > 11: anos_pago = 11 # Tope legal
    
    # 2. Topes
    uf_val, _ = obtener_indicadores()
    tope_pesos = tope_indem_uf * uf_val
    base_calculo = min(sueldo_base, tope_pesos)
    
    # 3. Montos
    indem_anos = int(base_calculo * anos_pago) if causal == "Necesidades de la Empresa" else 0
    aviso_previo = int(base_calculo) if causal in ["Necesidades de la Empresa", "Desahucio"] else 0
    
    valor_dia = sueldo_base / 30
    feriado = int(vac_pend * 1.25 * valor_dia)
    
    return {
        "indem_anos": indem_anos,
        "aviso": aviso_previo,
        "vacaciones": feriado,
        "total": indem_anos + aviso_previo + feriado,
        "anos_reconocidos": anos_pago
    }

# =============================================================================
# 5. GENERADORES DE DOCUMENTOS (PDF/WORD)
# =============================================================================

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

    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 15, "LIQUIDACION DE SUELDO", 0, 1, 'C')
    pdf.ln(10)
    
    # Datos Empresa/Trabajador
    pdf.set_font("Arial", '', 10)
    # Check seguridad por si los datos están vacíos
    emp_nombre = empresa.get('nombre', 'Sin Nombre Empresa')
    trab_nombre = trabajador.get('nombre', 'Sin Nombre Trabajador')
    trab_rut = trabajador.get('rut', '')
    
    pdf.cell(0, 6, f"Empresa: {emp_nombre}", 0, 1)
    pdf.cell(0, 6, f"Trabajador: {trab_nombre}", 0, 1)
    pdf.cell(0, 6, f"RUT: {trab_rut}", 0, 1)
    pdf.cell(0, 6, f"Fecha: {datetime.now().strftime('%d/%m/%Y')}", 0, 1)
    pdf.ln(5)
    
    # Tabla
    pdf.set_fill_color(230, 230, 230)
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(95, 8, "HABERES", 1, 0, 'C', 1)
    pdf.cell(95, 8, "DESCUENTOS", 1, 1, 'C', 1)
    pdf.set_font("Arial", '', 10)
    
    # Filas
    h1 = [("Sueldo Base", res['Sueldo Base']), ("Gratificacion", res['Gratificación']), ("Colacion/Mov", res['No Imponibles'])]
    d1 = [("AFP", res['AFP']), ("Salud Total", res['Salud_Total']), ("Seg. Cesantia", res['AFC']), ("Impuesto", res['Impuesto'])]
    
    max_row = max(len(h1), len(d1))
    for i in range(max_row):
        ht, hv = h1[i] if i < len(h1) else ("", "")
        dt, dv = d1[i] if i < len(d1) else ("", "")
        pdf.cell(60, 8, ht, 'L'); pdf.cell(35, 8, fmt(hv) if hv!="" else "", 'R')
        pdf.cell(60, 8, dt, 'L'); pdf.cell(35, 8, fmt(dv) if dv!="" else "", 'R', 1)
    
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(130, 12, "TOTAL LIQUIDO:", 1, 0, 'R')
    pdf.cell(60, 12, fmt(res['LÍQUIDO_FINAL']), 1, 1, 'C')
    
    # Pie
    pdf.ln(20)
    pdf.set_font("Arial", '', 9)
    pdf.multi_cell(0, 5, "Recibi conforme. __________________________ Firma.")
    
    return pdf.output(dest='S').encode('latin-1')

def generar_contrato_word(fin, emp, trab, cond):
    if not LIBRARIES_OK: return None
    doc = Document()
    style = doc.styles['Normal']
    style.font.name = 'Arial'
    style.font.size = Pt(11)
    
    t = doc.add_heading('CONTRATO DE TRABAJO', 0)
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.add_paragraph("")
    
    fecha = datetime.now().strftime("%d de %B de %Y")
    giro = emp.get('giro', 'Servicios') # Fallback para evitar KeyError
    
    intro = f"""En {emp.get('ciudad','Santiago')}, a {fecha}, entre "{emp.get('nombre','Empresa').upper()}", RUT {emp.get('rut','')}, giro {giro}, representada por {emp.get('rep_nombre','').upper()}, ambos domiciliados en {emp.get('direccion','')}, en adelante "EMPLEADOR"; y {trab.get('nombre','Trabajador').upper()}, RUT {trab.get('rut','')}, nacionalidad {trab.get('nacionalidad','')}, nacido el {str(trab.get('nacimiento',''))}, domiciliado en {trab.get('domicilio','')}, en adelante "TRABAJADOR", se conviene:"""
    
    p = doc.add_paragraph(intro)
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    
    # Cláusulas Robustas
    clausulas = [
        ("PRIMERO (Funciones):", f"El Trabajador se desempeñará como {cond['cargo'].upper()}, realizando las siguientes funciones principales: {cond['funciones']}."),
        ("SEGUNDO (Lugar):", f"Los servicios se prestarán en las oficinas ubicadas en {emp.get('direccion','')}, sin perjuicio de los desplazamientos necesarios."),
        ("TERCERO (Remuneración):", f"Sueldo Base: {fmt(fin['Sueldo Base'])}. Gratificación: {fmt(fin['Gratificación'])} (Tope Legal). Asignaciones No Imponibles: {fmt(fin['No Imponibles'])}. Total Líquido Aprox: {fmt(fin['LÍQUIDO_FINAL'])}."),
        ("CUARTO (Jornada):", "44 horas semanales distribuidas de lunes a viernes (Sujeto a reducción gradual Ley 40 Horas)."),
        ("QUINTO (Confidencialidad):", "El Trabajador guardará estricta reserva de la información sensible de la empresa."),
        ("SEXTO (Propiedad Intelectual):", "Toda creación derivada del trabajo será propiedad exclusiva del Empleador."),
        ("SEPTIMO (Vigencia):", f"Contrato {cond['tipo']} con inicio el {str(cond['inicio'])}.")
    ]
    
    for tit, txt in clausulas:
        p = doc.add_paragraph(); r = p.add_run(tit); r.bold = True; p.add_run(f" {txt}")
    
    bio = io.BytesIO()
    doc.save(bio)
    return bio

# --- 6. PERFILES DE CARGO ROBUSTOS (Word Style) ---
def generar_perfil_robusto(cargo, rubro):
    if not cargo: return None
    # Estructura expandida basada en tu documento Word
    return {
        "titulo": cargo.title(),
        "objetivo": f"Gestionar y controlar los procesos operativos del área de {cargo} en el sector {rubro}.",
        "dependencia": "Gerencia General / Gerencia de Área",
        "nivel": "Profesional Senior / Jefatura",
        "funciones": [
            "Coordinación y supervisión de equipos de trabajo.",
            "Control presupuestario y gestión de recursos.",
            "Reportabilidad de estados de avance y KPIs.",
            "Aseguramiento de la calidad y normativa vigente."
        ],
        "requisitos_obj": [
            "Título Profesional Universitario.",
            f"Experiencia mínima de 4 años en {rubro}.",
            "Manejo de ERP y Office Avanzado.",
            "Inglés Técnico."
        ],
        "competencias": ["Liderazgo", "Autonomía", "Orientación al Resultado", "Trabajo bajo presión"],
        "condiciones": ["Jornada Completa", "Trabajo en Terreno/Oficina", "Disponibilidad para viajar"]
    }

# --- 7. INTERFAZ GRÁFICA PRINCIPAL ---

# SIDEBAR: DATOS MAESTROS
with st.sidebar:
    st.image("https://www.previred.com/wp-content/uploads/2021/01/logo-previred.png", width=120)
    
    st.markdown("### 🏢 Configuración Inicial")
    
    # 1. Logo
    upl_logo = st.file_uploader("Logo (Para PDF)", type=["png", "jpg"])
    if upl_logo: st.session_state.logo_bytes = upl_logo.read()
    
    # 2. Datos Empresa (Persistentes)
    with st.expander("Datos Empresa (Obligatorio para Contratos)", expanded=False):
        st.session_state.empresa['rut'] = st.text_input("RUT Empresa", st.session_state.empresa['rut'])
        st.session_state.empresa['nombre'] = st.text_input("Razón Social", st.session_state.empresa['nombre'])
        st.session_state.empresa['rep_nombre'] = st.text_input("Rep. Legal", st.session_state.empresa['rep_nombre'])
        st.session_state.empresa['rep_rut'] = st.text_input("RUT Rep.", st.session_state.empresa['rep_rut'])
        st.session_state.empresa['direccion'] = st.text_input("Dirección", st.session_state.empresa['direccion'])
        st.session_state.empresa['ciudad'] = st.text_input("Ciudad", st.session_state.empresa['ciudad'])
        st.session_state.empresa['giro'] = st.text_input("Giro", st.session_state.empresa['giro'])

    # 3. Datos Trabajador (Opcional al inicio)
    with st.expander("Datos Trabajador (Opcional para Simular)", expanded=False):
        st.session_state.trabajador['nombre'] = st.text_input("Nombre", st.session_state.trabajador['nombre'])
        st.session_state.trabajador['rut'] = st.text_input("RUT", st.session_state.trabajador['rut'])
        st.session_state.trabajador['domicilio'] = st.text_input("Domicilio", st.session_state.trabajador['domicilio'])
        # FECHA DESBLOQUEADA (1940 - Hoy)
        st.session_state.trabajador['nacimiento'] = st.date_input("Nacimiento", 
            value=st.session_state.trabajador['nacimiento'], 
            min_value=date(1940,1,1), 
            max_value=datetime.now())

    st.divider()
    uf_v, utm_v = obtener_indicadores()
    st.metric("UF", fmt(uf_v).replace("$",""))

st.title("HR Suite CEO Edition")
st.markdown("**Plataforma Integral de Gestión de Personas**")

# TABS (6 Módulos)
tabs = st.tabs(["💰 Calculadora", "📋 Perfil Cargo", "📜 Legal Hub", "🧠 Análisis CV", "🚀 Carrera", "📊 Indicadores"])

# --- TAB 1: CALCULADORA ---
with tabs[0]:
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
        res = calcular_nomina_target_isapre(liq, col, mov, con, afp, sal, plan, uf_v, utm_v, 529000)
        if res:
            st.session_state.calculo_actual = res
            
            if res.get('Warning'): st.warning(res['Warning'])
            
            k1, k2, k3 = st.columns(3)
            k1.metric("Sueldo Base", fmt(res['Sueldo Base']))
            k2.metric("Líquido Final", fmt(res['LÍQUIDO_FINAL']))
            k3.metric("Costo Empresa", fmt(res['COSTO TOTAL']), delta="Total", delta_color="inverse")
            
            # Liquidación Visual
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
            
            # Botón PDF (Fuera de Form)
            if LIBRARIES_OK:
                pdf_bytes = generar_pdf_liquidacion(res, st.session_state.empresa, st.session_state.trabajador)
                st.download_button("⬇️ Descargar Liquidación (PDF)", pdf_bytes, "liquidacion.pdf", "application/pdf")
        else: st.error("Error matemático.")

# --- TAB 2: PERFIL ---
with tabs[1]:
    c1, c2 = st.columns(2)
    cargo = c1.text_input("Cargo", placeholder="Ej: Jefe de Administración")
    rubro = c2.selectbox("Rubro", ["Finanzas", "Minería", "Retail", "Tecnología", "Salud"])
    
    if cargo:
        perf = generar_perfil_robusto(cargo, rubro)
        st.session_state.perfil_actual = perf
        
        st.markdown(f"### 📋 {perf['titulo']}")
        st.info(f"**Objetivo:** {perf['objetivo']}")
        
        c_a, c_b = st.columns(2)
        c_a.success("**Funciones Principales:**\n" + "\n".join([f"- {x}" for x in perf['funciones']]))
        c_b.warning("**Requisitos:**\n" + "\n".join([f"- {x}" for x in perf['requisitos_obj']]))
        st.write(f"**Condiciones:** {', '.join(perf['condiciones'])}")

# --- TAB 3: LEGAL HUB (CONTRATOS/FINIQUITOS) ---
with tabs[2]:
    st.header("Centro de Documentación Legal")
    modo = st.radio("Tipo de Documento", ["Contrato de Trabajo", "Finiquito (Cálculo)"], horizontal=True)
    
    if modo == "Contrato de Trabajo":
        if st.session_state.calculo_actual:
            if not st.session_state.empresa['rut'] or not st.session_state.trabajador['rut']:
                st.warning("⚠️ Complete los datos de Empresa y Trabajador en la barra lateral izquierda.")
            else:
                c1, c2 = st.columns(2)
                f_ini = c1.date_input("Inicio", datetime.now())
                t_con = c2.selectbox("Tipo", ["Indefinido", "Plazo Fijo"])
                func = st.text_area("Funciones", "Las propias del cargo.")
                
                cond = {"cargo": cargo if cargo else "Trabajador", "tipo": t_con, "inicio": f_ini, "funciones": func}
                
                if st.button("GENERAR CONTRATO (.DOCX)"):
                    bio = generar_contrato_word(st.session_state.calculo_actual, st.session_state.empresa, st.session_state.trabajador, cond)
                    st.download_button("⬇️ Descargar DOCX", bio.getvalue(), "contrato.docx")
        else: st.info("Realice un cálculo en Pestaña 1 primero.")
        
    elif modo == "Finiquito (Cálculo)":
        st.markdown("#### Calculadora de Indemnizaciones")
        c1, c2 = st.columns(2)
        fi = c1.date_input("Fecha Inicio", date(2020,1,1))
        ft = c2.date_input("Fecha Término", date.today())
        causal = st.selectbox("Causal", ["Necesidades de la Empresa", "Renuncia Voluntaria"])
        vac = st.number_input("Vacaciones Pendientes (Días)", 0.0, step=0.5)
        base = st.number_input("Sueldo Base Finiquito", 1000000, step=50000)
        
        if st.button("CALCULAR FINIQUITO"):
            res_fin = calcular_finiquito(fi, ft, base, causal, vac)
            st.success("Cálculo Realizado")
            st.write(f"**Años Servicio:** {res_fin['indem_anos']}")
            st.write(f"**Aviso Previo:** {res_fin['aviso']}")
            st.write(f"**Vacaciones:** {res_fin['vacaciones']}")
            st.metric("TOTAL A PAGAR", fmt(res_fin['total']))

# --- TAB 4, 5, 6 (RESTO DE MÓDULOS) ---
with tabs[3]:
    st.info("Módulo de Análisis de CV (Requiere librerías PDF).")
with tabs[4]:
    st.info("Módulo de Carrera (Vinculado a Perfil).")
with tabs[5]:
    st.header("Indicadores Previred")
    st.table(pd.DataFrame({"Indicador": ["UF", "UTM", "Sueldo Mínimo"], "Valor": [fmt(39643.59), fmt(69542), fmt(529000)]}))
