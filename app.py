import streamlit as st
import pandas as pd
import requests
import base64
import io
import random
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
st.set_page_config(page_title="HR Suite V40 Stable", page_icon="🛡️", layout="wide")

# Inicialización de Estado (Memoria)
if 'empresa' not in st.session_state:
    st.session_state.empresa = {
        "nombre": "", "rut": "", "direccion": "", 
        "rep_nombre": "", "rep_rut": "", "ciudad": "Santiago", "giro": "Servicios"
    }
if 'calculo_actual' not in st.session_state: st.session_state.calculo_actual = None
if 'perfil_actual' not in st.session_state: st.session_state.perfil_actual = None

# --- 2. ESTILOS VISUALES ---
def cargar_estilos():
    css = """
    <style>
        .block-container {padding: 2rem 1rem;}
        h1, h2, h3 {color: #004a99;}
        .stButton>button {
            background-color: #004a99; color: white; border-radius: 8px; 
            width: 100%; height: 3rem; font-weight: bold;
        }
        .liq-box {
            border: 1px solid #ccc; padding: 20px; background: #fff; 
            font-family: monospace; border-radius: 5px; margin-top: 15px;
        }
        .liq-row {display: flex; justify-content: space-between; border-bottom: 1px dotted #ccc; padding: 5px 0;}
        .liq-total {
            background: #e3f2fd; padding: 10px; font-weight: bold; 
            text-align: right; border: 1px solid #004a99; margin-top: 15px;
        }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

cargar_estilos()

# --- 3. FUNCIONES UTILITARIAS ---
def fmt(valor):
    if valor is None or pd.isna(valor): return "$0"
    try: return "${:,.0f}".format(float(valor)).replace(",", ".")
    except: return str(valor)

def obtener_indicadores():
    # Valores Fijos Nov 2025 (Seguridad)
    return 39643.59, 69542.0

# --- 4. MOTORES DE LÓGICA ---

def generar_perfil_robusto(cargo, rubro):
    if not cargo: return None
    # Diccionario unificado para evitar errores de llave
    return {
        "titulo": cargo.title(),
        "objetivo": f"Gestionar las operaciones de {cargo} en el sector {rubro}.",
        "funciones": [
            "Control de gestión y presupuesto.",
            "Liderazgo de equipos.",
            "Reportabilidad a Gerencia.",
            "Cumplimiento normativo."
        ],
        "requisitos": [ # LLAVE CORREGIDA
            "Título Profesional.",
            f"Experiencia en {rubro}.",
            "Manejo de ERP.",
            "Inglés Técnico."
        ],
        "competencias": ["Liderazgo", "Visión Estratégica", "Resiliencia"],
        "condiciones": ["Art. 22", "Presencial/Híbrido"]
    }

def calcular_nomina_reversa(liquido, col, mov, contrato, afp_n, salud_t, plan_uf, uf, utm, s_min):
    no_imp = col + mov
    liq_meta = liquido - no_imp
    if liq_meta < s_min * 0.4: return None
    
    TOPE_GRAT = (4.75 * s_min) / 12
    tasa_afp = 0.0 if (contrato == "Sueldo Empresarial" or afp_n == "SIN AFP") else 0.1144 # Promedio
    
    min_b, max_b = 100000, liq_meta * 2.5
    for _ in range(150):
        base = (min_b + max_b) / 2
        grat = min(base * 0.25, TOPE_GRAT)
        if contrato == "Sueldo Empresarial": grat = 0
        tot_imp = base + grat
        
        b_prev = min(tot_imp, 87.8*uf)
        m_afp = int(b_prev * tasa_afp)
        legal_7 = int(b_prev * 0.07)
        m_afc = int(min(tot_imp, 131.9*uf) * 0.006) if contrato == "Indefinido" else 0
        
        base_trib = max(0, tot_imp - m_afp - legal_7 - m_afc)
        imp = 0
        if base_trib > 13.5*utm: imp = int(base_trib*0.04) # Simplificado
        
        liq_calc = tot_imp - m_afp - legal_7 - m_afc - imp
        
        if abs(liq_calc - liq_meta) < 500:
            salud_real = legal_7
            if salud_t == "Isapre (UF)":
                plan_pesos = int(plan_uf * uf)
                if plan_pesos > legal_7: salud_real = plan_pesos
            
            liq_final = tot_imp - m_afp - salud_real - m_afc - imp + no_imp
            costo = int(tot_imp * 1.05) # Aprox costo empresa
            
            return {
                "Sueldo Base": int(base), "Gratificación": int(grat), "Total Imponible": int(tot_imp),
                "No Imponibles": int(no_imp), "LÍQUIDO": int(liq_final), 
                "AFP": m_afp, "Salud": salud_real, "AFC": m_afc, "Impuesto": imp,
                "COSTO TOTAL": costo
            }
            break
        elif liq_calc < liq_meta: min_b = base
        else: max_b = base
    return None

# --- 5. GENERADORES DOCUMENTALES ---

def generar_pdf(res, emp, trab_nombre):
    if not LIBRARIES_OK: return None
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, "LIQUIDACION DE SUELDO", 0, 1, 'C')
    pdf.set_font("Arial", '', 10)
    pdf.ln(10)
    pdf.cell(0, 6, f"Empresa: {emp.get('nombre','S/N')}", 0, 1)
    pdf.cell(0, 6, f"Trabajador: {trab_nombre}", 0, 1)
    pdf.ln(5)
    
    # Detalle
    items = [
        ("Sueldo Base", res['Sueldo Base']), ("Gratificacion", res['Gratificación']),
        ("Colacion/Mov", res['No Imponibles']), ("AFP", res['AFP']*-1),
        ("Salud", res['Salud']*-1), ("Impuesto", res['Impuesto']*-1)
    ]
    
    for txt, val in items:
        pdf.cell(100, 8, txt, 1)
        pdf.cell(40, 8, fmt(val), 1, 1, 'R')
    
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(100, 10, "LIQUIDO A PAGAR", 1)
    pdf.cell(40, 10, fmt(res['LÍQUIDO']), 1, 1, 'R')
    
    return pdf.output(dest='S').encode('latin-1')

def generar_contrato_docx(fin, emp, trab, cargo):
    if not LIBRARIES_OK: return None
    doc = Document()
    doc.add_heading('CONTRATO DE TRABAJO', 0).alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    # Uso de .get() para evitar KeyError si falta el giro
    giro = emp.get('giro', 'Servicios')
    
    texto = f"""En {emp.get('ciudad','Santiago')}, a {datetime.now().strftime('%d/%m/%Y')}, entre "{emp.get('nombre','Empresa')}", RUT {emp.get('rut','XX')}, giro {giro}, y don/ña {trab.get('nombre','Trabajador')}, RUT {trab.get('rut','XX')}, se acuerda:
    
    PRIMERO: El trabajador se desempeñará como {cargo}.
    
    SEGUNDO: Remuneración mensual:
    - Sueldo Base: {fmt(fin['Sueldo Base'])}
    - Gratificación Legal: {fmt(fin['Gratificación'])}
    - Colación y Movilización: {fmt(fin['No Imponibles'])}
    
    TERCERO: Jornada de 44 horas semanales.
    """
    doc.add_paragraph(texto)
    
    bio = io.BytesIO()
    doc.save(bio)
    return bio

# --- 6. INTERFAZ GRÁFICA ---

with st.sidebar:
    st.image("https://www.previred.com/wp-content/uploads/2021/01/logo-previred.png", width=120)
    
    with st.expander("1. Datos Empresa (Obligatorio)", expanded=True):
        st.session_state.empresa['rut'] = st.text_input("RUT Empresa", st.session_state.empresa['rut'])
        st.session_state.empresa['nombre'] = st.text_input("Razón Social", st.session_state.empresa['nombre'])
        st.session_state.empresa['giro'] = st.text_input("Giro", st.session_state.empresa['giro'])
        st.session_state.empresa['ciudad'] = st.text_input("Ciudad", st.session_state.empresa['ciudad'])
        st.session_state.empresa['direccion'] = st.text_input("Dirección", st.session_state.empresa['direccion'])
        st.session_state.empresa['rep_nombre'] = st.text_input("Rep. Legal", st.session_state.empresa['rep_nombre'])
        st.session_state.empresa['rep_rut'] = st.text_input("RUT Rep.", st.session_state.empresa['rep_rut'])

    st.divider()
    uf_v, utm_v = obtener_indicadores()
    st.metric("UF", fmt(uf_v).replace("$",""))

st.title("HR Suite V40 Stable")

tabs = st.tabs(["💰 Calculadora", "📋 Perfil de Cargo", "📜 Legal Hub", "📊 Indicadores"])

# --- TAB 1: CALCULADORA ---
with tabs[0]:
    c1, c2 = st.columns(2)
    with c1:
        liq = st.number_input("Líquido Objetivo ($)", 1000000, step=50000)
        mostrar_miles(liq)
        col = st.number_input("Colación", 50000); mov = st.number_input("Movilización", 50000)
    with c2:
        con = st.selectbox("Contrato", ["Indefinido", "Plazo Fijo", "Empresarial"])
        sal = st.selectbox("Salud", ["Fonasa (7%)", "Isapre (UF)"])
        plan = st.number_input("Plan UF", 0.0) if sal == "Isapre (UF)" else 0.0
        afp = st.selectbox("AFP", ["Capital", "Habitat", "Modelo", "Uno"])

    if st.button("CALCULAR"):
        res = calcular_nomina_reversa(liq, col, mov, con, afp, sal, plan, uf_v, utm_v, 529000)
        if res:
            st.session_state.calculo_actual = res
            
            k1, k2, k3 = st.columns(3)
            k1.metric("Sueldo Base", fmt(res['Sueldo Base']))
            k2.metric("Líquido", fmt(res['LÍQUIDO']))
            k3.metric("Costo Total", fmt(res['COSTO TOTAL']))
            
            st.markdown(f"""
            <div class="liq-box">
                <div class="liq-row"><span>Base:</span><span>{fmt(res['Sueldo Base'])}</span></div>
                <div class="liq-row"><span>Gratificación:</span><span>{fmt(res['Gratificación'])}</span></div>
                <div class="liq-row"><span>No Imponibles:</span><span>{fmt(res['No Imponibles'])}</span></div>
                <hr>
                <div class="liq-row"><span>Descuentos:</span><span style="color:red">-{fmt(res['AFP']+res['Salud']+res['AFC']+res['Impuesto'])}</span></div>
                <div class="liq-total">A PAGAR: {fmt(res['LÍQUIDO'])}</div>
            </div>
            """, unsafe_allow_html=True)
            
            # Nombre trabajador opcional para el PDF
            nom_trab = st.text_input("Nombre Trabajador (Opcional para PDF)", "Trabajador")
            if st.button("Descargar PDF Liquidación"):
                if LIBRARIES_OK:
                    pdf = generar_pdf(res, st.session_state.empresa, nom_trab)
                    st.download_button("Descargar PDF", pdf, "liquidacion.pdf", "application/pdf")
                else: st.error("Faltan librerías.")

# --- TAB 2: PERFIL ---
with tabs[1]:
    cargo = st.text_input("Cargo", "Analista")
    rubro = st.selectbox("Rubro", ["Minería", "TI", "Retail"])
    
    if cargo:
        perf = generar_perfil_robusto(cargo, rubro)
        st.info(f"**Objetivo:** {perf['objetivo']}")
        c1, c2 = st.columns(2)
        c1.write("**Funciones:**")
        for f in perf['funciones']: c1.write(f"- {f}")
        c2.write("**Requisitos:**")
        # CORRECCIÓN DE LLAVE: usamos 'requisitos' que es seguro
        for r in perf['requisitos']: c2.write(f"- {r}")

# --- TAB 3: LEGAL HUB ---
with tabs[2]:
    st.header("Generador de Contratos")
    
    if st.session_state.calculo_actual:
        if not st.session_state.empresa['rut']:
            st.warning("⚠️ Complete los Datos de Empresa en la barra lateral.")
        else:
            c1, c2 = st.columns(2)
            tn = c1.text_input("Nombre Trabajador")
            tr = c2.text_input("RUT Trabajador")
            td = st.text_input("Domicilio Trabajador")
            
            if st.button("GENERAR CONTRATO WORD"):
                trab_data = {"nombre": tn, "rut": tr, "direccion": td, "nacionalidad": "Chilena", "nacimiento": ""}
                doc = generar_contrato_docx(st.session_state.calculo_actual, st.session_state.empresa, trab_data, cargo)
                st.download_button("Descargar .docx", doc.getvalue(), "contrato.docx")
    else:
        st.info("Primero calcule un sueldo en la Pestaña 1.")

# --- TAB 4: INDICADORES ---
with tabs[3]:
    st.header("Indicadores Oficiales (Nov 2025)")
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Rentas Mínimas")
        st.write(pd.DataFrame({
            "Item": ["Sueldo Mínimo", "Menores 18/Mayores 65", "Casa Particular"],
            "Valor": ["$529.000", "$394.622", "$529.000"]
        }))
        st.subheader("Topes Imponibles")
        st.write(pd.DataFrame({
            "Concepto": ["AFP/Salud", "Seguro Cesantía"],
            "UF": ["87,8", "131,9"]
        }))

    with col2:
        st.subheader("Tasas AFP")
        st.write(pd.DataFrame({
            "AFP": ["Capital", "Cuprum", "Habitat", "PlanVital", "Provida", "Modelo", "Uno"],
            "Tasa": ["11,44%", "11,44%", "11,27%", "11,16%", "11,45%", "10,58%", "10,46%"]
        }))
