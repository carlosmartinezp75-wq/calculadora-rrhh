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

# --- 0. VALIDACIÓN DE LIBRERÍAS ---
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
st.set_page_config(page_title="HR Suite CEO", page_icon="⚖️", layout="wide")

# Inicialización de Estado
if 'empresa' not in st.session_state:
    st.session_state.empresa = {
        "nombre": "", "rut": "", "direccion": "", 
        "rep_nombre": "", "rep_rut": "", "ciudad": "Santiago", "giro": "Servicios"
    }
if 'trabajador' not in st.session_state:
    st.session_state.trabajador = {
        "nombre": "", "rut": "", "direccion": "", 
        "nacionalidad": "Chilena", "civil": "Soltero", "nacimiento": date(1990,1,1),
        "cargo": "", "fecha_ingreso": date.today()
    }
if 'calculo_actual' not in st.session_state: st.session_state.calculo_actual = None
if 'logo_bytes' not in st.session_state: st.session_state.logo_bytes = None

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
        h1, h2, h3, h4 {{color: #004a99 !important; font-family: 'Segoe UI', sans-serif; font-weight: 800;}}
        .stButton>button {{background-color: #004a99 !important; color: white !important; font-weight: bold; border-radius: 8px; width: 100%; height: 3rem; text-transform: uppercase;}}
        .stButton>button:hover {{background-color: #003366 !important; transform: translateY(-2px);}}
        .liq-box {{border: 1px solid #ccc; padding: 20px; font-family: 'Courier New'; background: #fff; box-shadow: 5px 5px 15px #eee;}}
        .liq-row {{display: flex; justify-content: space-between; border-bottom: 1px dotted #ccc; padding: 3px 0;}}
        .liq-total {{font-weight: bold; background: #e3f2fd; padding: 10px; border: 1px solid #004a99; margin-top: 10px; color: #004a99;}}
        .miles-feedback {{font-size: 0.8rem; color: #2e7d32; font-weight: bold; margin-top: -10px;}}
        </style>
        """, unsafe_allow_html=True)

cargar_estilos()

# --- 3. FUNCIONES UTILITARIAS ---
def fmt(valor): return "$0" if pd.isna(valor) else "${:,.0f}".format(valor).replace(",", ".")
def mostrar_miles(valor): 
    if valor > 0: st.markdown(f'<p class="miles-feedback">✅ Ingresaste: {fmt(valor)}</p>', unsafe_allow_html=True)

def obtener_indicadores():
    # Valores Previred Nov 2025 (Hardcoded para seguridad)
    return 39643.59, 69542.0

# --- 4. GENERADORES DOCUMENTALES (PDF/WORD) ---

def generar_pdf_liquidacion(res, empresa, trabajador, periodo="Noviembre 2025"):
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
    pdf.cell(0, 15, "LIQUIDACION DE SUELDO MENSUAL", 0, 1, 'C')
    pdf.set_font("Arial", '', 10)
    pdf.cell(0, 5, f"Periodo: {periodo}", 0, 1, 'C')
    pdf.ln(10)
    
    # Datos
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(0, 7, "ANTECEDENTES", 1, 1, 'L', 1)
    pdf.cell(95, 7, f"Nombre: {trabajador['nombre']}", 1)
    pdf.cell(95, 7, f"RUT: {trabajador['rut']}", 1, 1)
    pdf.cell(95, 7, f"Cargo: {res.get('cargo', 'No definido')}", 1)
    pdf.cell(95, 7, f"Centro Costo: Administración", 1, 1)
    pdf.ln(5)
    
    # Tabla Cálculos
    pdf.set_font("Arial", 'B', 9)
    pdf.cell(95, 7, "HABERES", 1, 0, 'C', 1)
    pdf.cell(95, 7, "DESCUENTOS", 1, 1, 'C', 1)
    pdf.set_font("Arial", '', 9)
    
    items_h = [
        ("Sueldo Base", res['Sueldo Base']),
        ("Gratificacion Legal", res['Gratificación']),
        ("Colacion", res['No Imponibles']//2),
        ("Movilizacion", res['No Imponibles']//2),
        ("TOTAL HABERES", res['TOTAL HABERES'])
    ]
    
    items_d = [
        (f"AFP ({res.get('afp_nombre','')})", res['AFP']),
        ("Salud Legal (7%)", res['Salud_Legal']),
        ("Adicional Isapre", res['Adicional_Salud']),
        ("Seguro Cesantia", res['AFC']),
        ("Impuesto Unico", res['Impuesto']),
        ("TOTAL DESCUENTOS", res['Total Descuentos'])
    ]
    
    max_len = max(len(items_h), len(items_d))
    for i in range(max_len):
        h_t, h_v = items_h[i] if i < len(items_h) else ("", "")
        d_t, d_v = items_d[i] if i < len(items_d) else ("", "")
        
        pdf.cell(65, 6, h_t, 'L'); pdf.cell(30, 6, fmt(h_v) if h_v!="" else "", 'R')
        pdf.cell(65, 6, d_t, 'L'); pdf.cell(30, 6, fmt(d_v) if d_v!="" else "", 'R', 1)

    pdf.ln(5)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(130, 10, "LIQUIDO A PAGAR", 1, 0, 'R')
    pdf.cell(60, 10, fmt(res['LÍQUIDO_FINAL']), 1, 1, 'C')
    
    pdf.ln(20)
    pdf.set_font("Arial", '', 8)
    pdf.multi_cell(0, 4, "Certifico que he recibido a mi entera satisfaccion el saldo liquido indicado, no teniendo cargo ni cobro posterior alguno que hacer.")
    pdf.ln(15)
    pdf.cell(95, 10, "__________________________", 0, 0, 'C')
    pdf.cell(95, 10, "__________________________", 0, 1, 'C')
    pdf.cell(95, 5, "FIRMA EMPLEADOR", 0, 0, 'C')
    pdf.cell(95, 5, "FIRMA TRABAJADOR", 0, 1, 'C')
    
    return pdf.output(dest='S').encode('latin-1')

def generar_finiquito_pdf(datos_fin, empresa, trabajador):
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
    pdf.cell(0, 15, "FINIQUITO DE CONTRATO DE TRABAJO", 0, 1, 'C')
    pdf.ln(5)
    
    pdf.set_font("Arial", '', 10)
    texto = f"""En {empresa['ciudad']}, a {datetime.now().strftime("%d de %B de %Y")}, entre {empresa['nombre']}, RUT {empresa['rut']}, representada por {empresa['rep_nombre']}, y don/ña {trabajador['nombre']}, RUT {trabajador['rut']}, se deja constancia del término de la relación laboral."""
    pdf.multi_cell(0, 6, texto)
    pdf.ln(5)
    
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(0, 8, "1. CAUSAL DE TERMINO", 0, 1)
    pdf.set_font("Arial", '', 10)
    pdf.multi_cell(0, 6, f"Causal: {datos_fin['causal']}\nFundamento: {datos_fin['fundamento']}")
    pdf.ln(5)
    
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(0, 8, "2. LIQUIDACION DE HABERES INDEMNIZATORIOS", 0, 1)
    pdf.set_font("Arial", '', 10)
    
    # Detalle Finiquito
    items = [
        ("Indemnizacion Anos de Servicio", datos_fin['indem_anos']),
        ("Indemnizacion Aviso Previo", datos_fin['aviso_previo']),
        ("Feriado Proporcional (Vacaciones)", datos_fin['feriado_prop']),
        ("Remuneracion Pendiente", datos_fin['sueldo_pendiente']),
        ("TOTAL HABERES FINIQUITO", datos_fin['total_haberes'])
    ]
    
    for txt, val in items:
        pdf.cell(140, 7, txt, 1)
        pdf.cell(50, 7, fmt(val), 1, 1, 'R')
    
    pdf.ln(5)
    pdf.multi_cell(0, 6, "El trabajador declara recibir en este acto, a su entera satisfaccion, la suma total indicada anteriormente.")
    
    # Firmas
    pdf.ln(30)
    pdf.cell(95, 10, "__________________________", 0, 0, 'C')
    pdf.cell(95, 10, "__________________________", 0, 1, 'C')
    pdf.cell(95, 5, "FIRMA EMPLEADOR", 0, 0, 'C')
    pdf.cell(95, 5, "FIRMA TRABAJADOR", 0, 1, 'C')
    
    return pdf.output(dest='S').encode('latin-1')

# --- 5. LÓGICA DE NEGOCIO ---

def generar_perfil_word_style(cargo, rubro):
    if not cargo: return None
    # Estructura basada en el archivo Word subido
    return {
        "titulo": cargo.title(),
        "objetivo": f"Coordinar, gestionar y controlar los procesos críticos del área de {cargo} en el sector {rubro}.",
        "dependencia": "Gerencia de Administración y Finanzas / Gerencia General",
        "nivel_resp": "Jefatura / Supervisión Senior",
        "funciones": [
            "Coordinar y gestionar procesos operativos y estratégicos del área.",
            "Elaboración de informes de gestión y reportes financieros (EEFF/KPIs).",
            "Aseguramiento del cumplimiento normativo legal y tributario vigente.",
            "Liderazgo de equipos multidisciplinarios y gestión del clima laboral.",
            "Optimización de procedimientos internos para mejorar la productividad."
        ],
        "requisitos_obj": [
            "Título Profesional: Contador Auditor, Ingeniero Comercial o afín.",
            f"Experiencia: Al menos 5 años en cargos similares en {rubro}.",
            "Conocimientos Técnicos: ERP (SAP/Softland), Excel Avanzado, IFRS.",
            "Idiomas: Inglés Técnico (Deseable)."
        ],
        "competencias": ["Liderazgo", "Trabajo bajo presión", "Orientación al Resultado", "Planificación"],
        "condiciones": ["Jornada: Art. 22 / 44 Horas.", "Lugar: Oficina Central / Terreno.", "Renta Líquida: Acorde a mercado."]
    }

def calcular_finiquito(f_inicio, f_termino, sueldo_base, causal, vacaciones_pend):
    # Cálculo Años Servicio
    dias_trabajados = (f_termino - f_inicio).days
    anos_servicio = dias_trabajados / 365.25
    anos_pago = int(anos_servicio)
    if (anos_servicio - anos_pago) * 12 >= 6: anos_pago += 1 # Fracción superior a 6 meses
    if anos_pago > 11: anos_pago = 11 # Tope legal 11 años
    
    # Topes (UF Nov 2025)
    UF = 39643.59
    TOPE_INDEM = 90 * UF
    
    # 1. Indemnización Años
    base_calc = min(sueldo_base, TOPE_INDEM)
    monto_anos = 0
    if causal == "Necesidades de la Empresa":
        monto_anos = int(base_calc * anos_pago)
    
    # 2. Aviso Previo
    monto_aviso = 0
    if causal == "Necesidades de la Empresa" or causal == "Desahucio":
        monto_aviso = int(base_calc) # 1 mes tope 90 UF
    
    # 3. Feriado Proporcional
    # Factor 1.25 días por mes
    # Simplificado: Vacaciones pendientes * (Sueldo / 30)
    valor_dia = sueldo_base / 30
    monto_feriado = int(vacaciones_pend * 1.25 * valor_dia) # Aprox (sin inhábiles para demo)
    
    total = monto_anos + monto_aviso + monto_feriado
    
    return {
        "indem_anos": monto_anos,
        "aviso_previo": monto_aviso,
        "feriado_prop": monto_feriado,
        "sueldo_pendiente": 0, # Se debe ingresar manual si hay días
        "total_haberes": total,
        "causal": causal,
        "fundamento": "Artículo 161 Código del Trabajo" if causal == "Necesidades de la Empresa" else "Artículo 159/160"
    }

def calcular_nomina_target_isapre(liquido_obj, col, mov, contrato, afp_n, salud_t, plan_uf, uf, utm, s_min):
    no_imp = col + mov
    liq_meta = liquido_obj - no_imp
    if liq_meta < s_min * 0.4: return None
    
    # Tasas
    TASAS_AFP = {"Capital":1.44,"Cuprum":1.44,"Habitat":1.27,"PlanVital":1.16,"Provida":1.45,"Modelo":0.58,"Uno":0.49,"SIN AFP":0.0}
    tasa_afp = 0.0 if (contrato == "Sueldo Empresarial" or afp_n == "SIN AFP") else (0.10 + (TASAS_AFP.get(afp_n,1.44)/100))
    tasa_afc = 0.006 if (contrato == "Indefinido" and contrato != "Sueldo Empresarial") else 0.0
    
    # BÚSQUEDA DEL BRUTO (Usando 7% Legal como base)
    min_b, max_b = 100000, liq_meta * 2.5
    for _ in range(150):
        base = (min_b + max_b) / 2
        grat = min(base * 0.25, (4.75*s_min)/12)
        if contrato == "Sueldo Empresarial": grat = 0
        tot_imp = base + grat
        
        # Descuentos Legales (Para llegar al target)
        m_afp = int(min(tot_imp, 87.8*uf) * tasa_afp)
        m_sal_legal = int(min(tot_imp, 87.8*uf) * 0.07) # USAMOS 7% SIEMPRE PARA EL TARGET
        m_afc = int(min(tot_imp, 131.9*uf) * tasa_afc)
        
        # Impuesto (Usando 7% como rebaja)
        base_trib = max(0, tot_imp - m_afp - m_sal_legal - m_afc)
        imp = 0
        # Tabla Impuesto Nov 2025
        if base_trib > 13.5*utm: imp = int(base_trib*0.04) # Simplificado tramo 1-2
        
        liq_calc = tot_imp - m_afp - m_sal_legal - m_afc - imp
        
        if abs(liq_calc - liq_meta) < 500:
            # ENCONTRADO EL BRUTO. AHORA APLICAMOS EL PLAN REAL
            salud_real_pesos = m_sal_legal
            adicional_salud = 0
            warning = None
            
            if salud_t == "Isapre (UF)":
                costo_plan = int(plan_uf * uf)
                if costo_plan > m_sal_legal:
                    salud_real_pesos = costo_plan
                    adicional_salud = costo_plan - m_sal_legal
                    warning = f"⚠️ El Plan Isapre ({fmt(costo_plan)}) excede el 7% legal ({fmt(m_sal_legal)}). El líquido bajará en {fmt(adicional_salud)}."
            
            liq_final = tot_imp - m_afp - salud_real_pesos - m_afc - imp + no_imp
            
            # Costo Empresa
            sis = int(min(tot_imp, 87.8*uf)*0.0149)
            mut = int(min(tot_imp, 87.8*uf)*0.0093)
            afc_e = int(min(tot_imp, 131.9*uf)*0.024)
            
            return {
                "Sueldo Base": int(base), "Gratificación": int(grat), "Total Imponible": int(tot_imp),
                "No Imponibles": int(no_imp), "LÍQUIDO_OBJETIVO": int(liquido_obj), "LÍQUIDO_FINAL": int(liq_final),
                "AFP": m_afp, "Salud_Legal": m_sal_legal, "Adicional_Salud": adicional_salud, "Salud": salud_real_pesos,
                "AFC": m_afc, "Impuesto": imp, "Total Descuentos": m_afp + salud_real_pesos + m_afc + imp,
                "COSTO TOTAL": int(tot_imp+no_imp+sis+mut+afc_e), "Warning": warning, "cargo": st.session_state.trabajador.get('cargo', 'Sin Cargo')
            }
            break
        elif liq_calc < liq_meta: min_b = base
        else: max_b = base
    return None

# --- 7. INTERFAZ GRÁFICA ---

with st.sidebar:
    st.image("https://www.previred.com/wp-content/uploads/2021/01/logo-previred.png", width=120)
    
    # 1. LOGO EMPRESA
    upl_logo = st.file_uploader("Subir Logo Empresa (Para PDF)", type=["png", "jpg"])
    if upl_logo: st.session_state.logo_bytes = upl_logo.read()
    
    # 2. DATOS EMPRESA
    with st.expander("🏢 Datos Empresa", expanded=False):
        st.session_state.empresa['rut'] = st.text_input("RUT", st.session_state.empresa['rut'])
        st.session_state.empresa['nombre'] = st.text_input("Razón Social", st.session_state.empresa['nombre'])
        st.session_state.empresa['ciudad'] = st.text_input("Ciudad", st.session_state.empresa['ciudad'])
        st.session_state.empresa['rep_nombre'] = st.text_input("Rep. Legal", st.session_state.empresa['rep_nombre'])
        st.session_state.empresa['rep_rut'] = st.text_input("RUT Rep.", st.session_state.empresa['rep_rut'])
        st.session_state.empresa['direccion'] = st.text_input("Dirección", st.session_state.empresa['direccion'])

    # 3. DATOS TRABAJADOR (HÍBRIDO: OPCIONAL PARA SIMULAR, OBLIGATORIO PARA CONTRATO)
    with st.expander("👤 Datos Trabajador (Contratos)", expanded=False):
        st.caption("Llenar para generar documentos legales.")
        st.session_state.trabajador['nombre'] = st.text_input("Nombre", st.session_state.trabajador['nombre'])
        st.session_state.trabajador['rut'] = st.text_input("RUT Trab.", st.session_state.trabajador['rut'])
        st.session_state.trabajador['nacionalidad'] = st.text_input("Nacionalidad", "Chilena")
        st.session_state.trabajador['domicilio'] = st.text_input("Domicilio Trab.", st.session_state.trabajador['domicilio'])
        st.session_state.trabajador['nacimiento'] = st.date_input("F. Nacimiento", value=date(1990,1,1), min_value=date(1950,1,1), max_value=date.today())

    st.divider()
    uf_v, utm_v = obtener_indicadores()
    st.metric("UF", fmt(uf_v).replace("$",""))

st.title("HR Suite CEO")
st.markdown("**Gestión Legal y Financiera de Personas**")

tabs = st.tabs(["💰 Calculadora", "📋 Perfil Cargo", "📜 Legal Hub (Contratos/Finiquitos)", "📊 Indicadores"])

# TAB 1: CALCULADORA
with tabs[0]:
    c1, c2 = st.columns(2)
    with c1:
        liq = st.number_input("Líquido Objetivo ($)", 1000000, step=50000, format="%d")
        mostrar_miles(liq)
        col = st.number_input("Colación", 50000, format="%d"); mov = st.number_input("Movilización", 50000, format="%d")
    with c2:
        con = st.selectbox("Contrato", ["Indefinido", "Plazo Fijo", "Empresarial"])
        afp = st.selectbox("AFP", ["Capital", "Cuprum", "Habitat", "Modelo", "Uno", "SIN AFP"])
        sal = st.selectbox("Salud", ["Fonasa (7%)", "Isapre (UF)"])
        plan = st.number_input("Plan UF", 0.0) if sal == "Isapre (UF)" else 0.0

    if st.button("SIMULAR SUELDO"):
        res = calcular_nomina_target_isapre(liq, col, mov, con, afp, sal, plan, uf_v, utm_v, 529000)
        if res:
            st.session_state.calculo_actual = res
            st.session_state.calculo_actual['cargo'] = st.session_state.trabajador.get('cargo', 'No Definido') # Guardar cargo
            
            if res.get('Warning'): st.warning(res['Warning'])
            
            k1, k2, k3 = st.columns(3)
            k1.metric("Sueldo Base", fmt(res['Sueldo Base']))
            k2.metric("Líquido Final", fmt(res['LÍQUIDO_FINAL']), delta=f"Meta: {fmt(liq)}")
            k3.metric("Costo Empresa", fmt(res['COSTO TOTAL']), delta="Total", delta_color="inverse")
            
            st.markdown(f"""
            <div class="liq-box">
                <div class="liq-header">DETALLE LIQUIDACIÓN</div>
                <div class="liq-row"><span>Sueldo Base:</span><span>{fmt(res['Sueldo Base'])}</span></div>
                <div class="liq-row"><span>Gratificación:</span><span>{fmt(res['Gratificación'])}</span></div>
                <div class="liq-row"><span>No Imponibles:</span><span>{fmt(res['No Imponibles'])}</span></div>
                <br>
                <div class="liq-row"><span>Salud (7%):</span><span style="color:red">-{fmt(res['Salud_Legal'])}</span></div>
                {f'<div class="liq-row"><span><b>Diferencia Isapre:</b></span><span style="color:red">-{fmt(res["Adicional_Salud"])}</span></div>' if res['Adicional_Salud'] > 0 else ''}
                <div class="liq-row"><span>AFP + Cesantía:</span><span style="color:red">-{fmt(res['AFP']+res['AFC'])}</span></div>
                <div class="liq-row"><span>Impuesto:</span><span style="color:red">-{fmt(res['Impuesto'])}</span></div>
                <div class="liq-total">A PAGAR: {fmt(res['LÍQUIDO_FINAL'])}</div>
            </div>
            """, unsafe_allow_html=True)
            
            # PDF BUTTON (FUERA DEL FORM)
            if LIBRARIES_OK:
                pdf_data = generar_pdf_liquidacion(res, st.session_state.empresa, st.session_state.trabajador)
                st.download_button("⬇️ Descargar Liquidación (PDF)", pdf_data, "liquidacion.pdf", "application/pdf")

# TAB 2: PERFIL
with tabs[1]:
    cargo = st.text_input("Cargo a definir", placeholder="Ej: Jefe de Contabilidad")
    rubro = st.selectbox("Rubro", ["Finanzas", "Minería", "Retail", "Tecnología"])
    if cargo:
        perf = generar_perfil_word_style(cargo, rubro)
        st.markdown(f"### 📋 {perf['titulo']}")
        st.info(f"**Dependencia:** {perf['dependencia']} | **Nivel:** {perf['nivel_resp']}")
        
        c1, c2 = st.columns(2)
        c1.success("**Funciones Principales:**\n" + "\n".join([f"- {x}" for x in perf['funciones']]))
        c2.warning("**Requisitos Objetivos:**\n" + "\n".join([f"- {x}" for x in perf['requisitos_obj']]))
        st.write("**Condiciones Ambientales:** " + ", ".join(perf['condiciones']))

# TAB 3: LEGAL HUB (CONTRATOS Y FINIQUITOS)
with tabs[2]:
    st.header("Centro de Documentación Legal")
    
    doc_type = st.selectbox("Tipo de Documento", ["Contrato de Trabajo", "Carta de Amonestación", "Carta de Despido", "Finiquito (Cálculo)"])
    
    if doc_type == "Contrato de Trabajo":
        if st.session_state.calculo_actual:
            if st.button("Generar Contrato (.docx)"):
                cond = {"cargo": cargo if cargo else "Trabajador", "tipo": "Indefinido", "inicio": date.today(), "funciones": "Las del cargo"}
                bio = generar_contrato_word(st.session_state.calculo_actual, st.session_state.empresa, st.session_state.trabajador, cond)
                st.download_button("Descargar DOCX", bio.getvalue(), "contrato.docx")
        else: st.warning("Calcule un sueldo primero.")
    
    elif doc_type == "Finiquito (Cálculo)":
        st.markdown("#### Cálculo de Indemnizaciones")
        c1, c2 = st.columns(2)
        f_ini = c1.date_input("Inicio Relación", date(2020,1,1))
        f_fin = c2.date_input("Término Relación", date.today())
        causal = st.selectbox("Causal", ["Necesidades de la Empresa", "Renuncia Voluntaria", "Mutuo Acuerdo", "Falta Probidad"])
        vac_pend = st.number_input("Días Vacaciones Pendientes", 0.0, step=0.5)
        sueldo_base_fin = st.number_input("Sueldo Base para Finiquito", value=900000, step=10000)
        
        if st.button("CALCULAR FINIQUITO"):
            res_fin = calcular_finiquito(f_ini, f_fin, sueldo_base_fin, causal, vac_pend)
            
            st.success("Cálculo Realizado")
            st.write(f"**Años de Servicio:** {fmt(res_fin['indem_anos'])}")
            st.write(f"**Aviso Previo:** {fmt(res_fin['aviso_previo'])}")
            st.write(f"**Vacaciones:** {fmt(res_fin['feriado_prop'])}")
            st.metric("TOTAL FINIQUITO", fmt(res_fin['total_haberes']))
            
            if LIBRARIES_OK:
                pdf_fin = generar_finiquito_pdf(res_fin, st.session_state.empresa, st.session_state.trabajador)
                st.download_button("⬇️ Descargar Finiquito Legal (PDF)", pdf_fin, "finiquito.pdf", "application/pdf")

# TAB 4: INDICADORES
with tabs[3]:
    st.header("Indicadores Previred (Nov 2025)")
    st.info("UF: $39.643 | UTM: $69.542 | Sueldo Mínimo: $529.000")
    st.write("Tope Indemnización Años Servicio: **90 UF**")
    st.image("https://www.sii.cl/valores_y_fechas/impuesto_2da_categoria/img/imp_2da_cat_2025.png")
