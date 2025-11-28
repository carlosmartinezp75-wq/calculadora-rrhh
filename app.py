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
# 1. CONFIGURACIÓN DEL SISTEMA
# =============================================================================
st.set_page_config(
    page_title="HR Suite Universe V39",
    page_icon="🌌",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inicialización de Estado (Persistencia Completa)
if 'empresa' not in st.session_state:
    st.session_state.empresa = {
        "nombre": "", "rut": "", "direccion": "", 
        "rep_nombre": "", "rep_rut": "", "ciudad": "Santiago", "giro": "Servicios"
    }
if 'trabajador' not in st.session_state:
    st.session_state.trabajador = {
        "nombre": "", "rut": "", "direccion": "", 
        "nacionalidad": "Chilena", "civil": "Soltero", "nacimiento": date(1990,1,1),
        "cargo": "", "email": ""
    }
if 'calculo_actual' not in st.session_state: st.session_state.calculo_actual = None
if 'texto_perfil_cargado' not in st.session_state: st.session_state.texto_perfil_cargado = ""
if 'logo_bytes' not in st.session_state: st.session_state.logo_bytes = None

# =============================================================================
# 2. SISTEMA DE DISEÑO VISUAL
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
        h1, h2, h3, h4 {{color: #004a99 !important; font-family: 'Segoe UI', sans-serif; font-weight: 800;}}
        
        /* Tabs personalizados */
        .stTabs [data-baseweb="tab-list"] button [data-testid="stMarkdownContainer"] p {{
            font-size: 1.1rem; font-weight: bold;
        }}
        
        /* Botones Acción */
        .stButton>button {{
            background: linear-gradient(90deg, #004a99 0%, #003366 100%);
            color: white !important; font-weight: bold; border-radius: 8px; width: 100%; height: 3rem;
            text-transform: uppercase; letter-spacing: 1px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        .stButton>button:hover {{transform: translateY(-2px); box-shadow: 0 6px 12px rgba(0,0,0,0.2);}}
        
        /* Feedback Miles */
        .miles-feedback {{font-size: 0.8rem; color: #2e7d32; font-weight: bold; margin-top: -10px; margin-bottom: 10px;}}
        
        /* Ocultar elementos */
        #MainMenu, footer {{visibility: hidden;}}
        thead tr th:first-child {{display:none}}
        tbody th {{display:none}}
        </style>
        """, unsafe_allow_html=True)

cargar_estilos()

# =============================================================================
# 3. FUNCIONES DE DATOS Y UTILIDADES
# =============================================================================
def fmt(valor): return "$0" if pd.isna(valor) else "${:,.0f}".format(valor).replace(",", ".")
def mostrar_miles(valor): 
    if valor > 0: st.markdown(f'<p class="miles-feedback">✅ Ingresaste: {fmt(valor)}</p>', unsafe_allow_html=True)

def obtener_indicadores():
    # Intenta obtener online, si falla usa Nov 2025 fijo
    try:
        r = requests.get('https://mindicador.cl/api', timeout=2)
        d = r.json()
        return float(d['uf']['valor']), float(d['utm']['valor'])
    except: return 39643.59, 69542.0

def leer_pdf(archivo):
    """Extrae texto de un PDF usando pdfplumber"""
    if not LIBRARIES_OK: return None
    try:
        text = ""
        with pdfplumber.open(archivo) as pdf:
            for p in pdf.pages: text += (p.extract_text() or "") + "\n"
        return text
    except: return None

# =============================================================================
# 4. DATOS OFICIALES PREVIRED (Hardcoded del PDF subido)
# =============================================================================
def get_previred_data():
    # 1. Rentas Mínimas
    rentas = pd.DataFrame({
        "Concepto": ["Trabajadores Dependientes e Independientes", "Menores de 18 y Mayores de 65", "Trabajadores de Casa Particular", "Para fines no remuneracionales"],
        "Valor": ["$529.000", "$394.622", "$529.000", "$340.988"]
    })
    
    # 2. Topes Imponibles (UF)
    topes = pd.DataFrame({
        "Concepto": ["Para afiliados a una AFP (87,8 UF)", "Para afiliados al IPS (60 UF)", "Para Seguro de Cesantía (131,9 UF)"],
        "Monto ($ Estimado)": [fmt(87.8 * 39643.59), fmt(60 * 39643.59), fmt(131.9 * 39643.59)]
    })
    
    # 3. Tasas AFP
    afp = pd.DataFrame({
        "AFP": ["Capital", "Cuprum", "Habitat", "PlanVital", "Provida", "Modelo", "Uno"],
        "Tasa Trabajador": ["11,44%", "11,44%", "11,27%", "11,16%", "11,45%", "10,58%", "10,46%"],
        "SIS (Empleador)": ["1,49%", "1,49%", "1,49%", "1,49%", "1,49%", "1,49%", "1,49%"],
        "Costo Total": ["12,93%", "12,93%", "12,76%", "12,65%", "12,94%", "12,07%", "11,95%"]
    })
    
    # 4. Seguro Cesantía
    cesantia = pd.DataFrame({
        "Contrato": ["Indefinido", "Plazo Fijo", "Indefinido 11+ años", "Casa Particular"],
        "Empleador": ["2,4%", "3,0%", "0,8%", "3,0%"],
        "Trabajador": ["0,6%", "0,0%", "0,0%", "0,0%"]
    })
    
    # 5. Asignación Familiar
    asig = pd.DataFrame({
        "Tramo": ["A", "B", "C", "D"],
        "Requisito de Renta": ["Renta <= $620.251", "> $620.251 y <= $905.941", "> $905.941 y <= $1.412.957", "> $1.412.957"],
        "Monto": ["$22.007", "$13.505", "$4.267", "$0"]
    })
    
    # 6. APV
    apv = pd.DataFrame({
        "Tope": ["Mensual (50 UF)", "Anual (600 UF)", "Depósito Convenido Anual (900 UF)"],
        "Monto": [fmt(50*39643.59), fmt(600*39643.59), fmt(900*39643.59)]
    })
    
    return rentas, topes, afp, cesantia, asig, apv

# =============================================================================
# 5. MOTOR DE CÁLCULO FINANCIERO (Isapre Target + Previred)
# =============================================================================
def calcular_nomina_reversa(liquido_obj, col, mov, contrato, afp_n, salud_t, plan_uf, uf, utm, s_min):
    no_imp = col + mov
    liq_meta = liquido_obj - no_imp
    if liq_meta < s_min * 0.4: return None
    
    # Topes
    TOPE_GRAT = (4.75 * s_min) / 12
    TOPE_IMP_PESOS = 87.8 * uf
    TOPE_AFC_PESOS = 131.9 * uf
    
    # Tasas
    TASAS_AFP = {"Capital":11.44,"Cuprum":11.44,"Habitat":11.27,"PlanVital":11.16,"Provida":11.45,"Modelo":10.58,"Uno":10.46,"SIN AFP":0.0}
    tasa_total = TASAS_AFP.get(afp_n, 11.44)
    tasa_afp = 0.0 if (contrato == "Sueldo Empresarial" or afp_n == "SIN AFP") else (tasa_total/100) # Usamos tasa completa para descuento
    
    tasa_afc_trab = 0.006 if (contrato == "Indefinido" and contrato != "Sueldo Empresarial") else 0.0
    tasa_afc_emp = 0.024 if contrato == "Indefinido" else 0.03
    if contrato == "Sueldo Empresarial": tasa_afc_emp = 0.0 # Empresarial no paga AFC empleador obligatoriamente, pero se puede configurar
    
    min_b, max_b = 100000, liq_meta * 2.5
    for _ in range(150):
        base = (min_b + max_b) / 2
        grat = min(base * 0.25, TOPE_GRAT)
        if contrato == "Sueldo Empresarial": grat = 0
        tot_imp = base + grat
        
        b_prev = min(tot_imp, TOPE_IMP_PESOS)
        b_afc = min(tot_imp, TOPE_AFC_PESOS)
        
        m_afp = int(b_prev * (0.10 + (tasa_total-10)/100)) # 10% + Comision
        if afp_n == "SIN AFP" or contrato == "Sueldo Empresarial": m_afp = 0
        
        m_afc = int(b_afc * tasa_afc_trab)
        
        # TARGET ISAPRE: Usamos el 7% legal para encontrar el bruto objetivo
        legal_7 = int(b_prev * 0.07)
        
        base_trib = max(0, tot_imp - m_afp - legal_7 - m_afc)
        
        # Tabla Impuesto Nov 2025
        imp = 0
        tabla_imp = [(13.5,0,0),(30,0.04,0.54),(50,0.08,1.74),(70,0.135,4.49),(90,0.23,11.14),(120,0.304,17.80),(310,0.35,23.32),(99999,0.40,38.82)]
        for l, f, r in tabla_imp:
            if (base_trib/utm) <= l:
                imp = int((base_trib * f) - (r * utm))
                break
        imp = max(0, imp)
        
        liq_calc_base = tot_imp - m_afp - legal_7 - m_afc - imp
        
        if abs(liq_calc_base - liq_meta) < 500:
            # AJUSTE REAL ISAPRE
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
            ap_sis = int(b_prev*0.0149)
            ap_mut = int(b_prev*0.0093)
            ap_afc_e = int(b_afc*tasa_afc_emp)
            
            return {
                "Sueldo Base": int(base), "Gratificación": int(grat), "Total Imponible": int(tot_imp),
                "No Imponibles": int(no_imp), "LÍQUIDO": int(liq_final), 
                "AFP": m_afp, "Salud_Legal": legal_7, "Adicional_Salud": adicional, "Salud_Total": salud_real,
                "AFC": m_afc, "Impuesto": imp, "Aportes Empresa": ap_sis+ap_mut+ap_afc_e, 
                "COSTO TOTAL": int(tot_imp+no_imp+ap_sis+ap_mut+ap_afc_e), "Warning": warning
            }
            break
        elif liq_calc_base < liq_meta: min_b = base
        else: max_b = base
    return None

# =============================================================================
# 6. MOTORES DE ANÁLISIS Y GENERACIÓN
# =============================================================================

def motor_analisis_dual(texto_cv, texto_perfil):
    """Compara texto del CV con texto del Perfil (Cargado o Escrito)"""
    # 1. Extracción de Keywords del Perfil (Simulado: Asumimos que el texto perfil tiene keywords)
    # En una app real usaríamos NLP. Aquí usamos una lista maestra contra el texto.
    keywords_master = ["liderazgo", "gestión", "equipo", "estrategia", "inglés", "excel", "presupuesto", "proyectos", "seguridad", "ventas", "programación", "agile", "calidad", "iso", "finanzas"]
    
    requeridas = [k for k in keywords_master if k in texto_perfil.lower()]
    if not requeridas: requeridas = keywords_master[:5] # Fallback
    
    encontradas = [k.title() for k in requeridas if k in texto_cv.lower()]
    faltantes = [k.title() for k in requeridas if k not in texto_cv.lower()]
    
    score = int((len(encontradas) / len(requeridas)) * 100) if requeridas else 0
    score = min(100, max(10, score + 10))
    
    return score, encontradas, faltantes

def generar_plantilla_generica(tipo):
    """Genera un DOCX en blanco con formato tipo para descargar"""
    doc = Document()
    style = doc.styles['Normal']; style.font.name = 'Arial'; style.font.size = Pt(11)
    
    titulo = f"FORMATO TIPO: {tipo.upper()}"
    doc.add_heading(titulo, 0).alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.add_paragraph("[CIUDAD], [FECHA]").alignment = WD_ALIGN_PARAGRAPH.RIGHT
    doc.add_paragraph("\n")
    
    if tipo == "Contrato":
        doc.add_paragraph("Entre [NOMBRE EMPRESA], RUT [RUT], representada por [REPRESENTANTE], en adelante EMPLEADOR; y [TRABAJADOR], RUT [RUT], se acuerda:")
        doc.add_paragraph("PRIMERO: El trabajador se desempeñará como [CARGO].")
        doc.add_paragraph("SEGUNDO: Remuneración de $[MONTO].")
    elif tipo == "Carta Amonestación":
        doc.add_paragraph("Señor(a) [NOMBRE TRABAJADOR]:")
        doc.add_paragraph("Por medio de la presente, se amonesta a usted por los siguientes hechos: [DESCRIPCIÓN].")
    elif tipo == "Finiquito":
        doc.add_paragraph("En [CIUDAD], las partes ponen término a la relación laboral.")
        doc.add_paragraph("Causal: [CAUSAL LEGAL].")
    
    doc.add_paragraph("\n\n__________________\nFIRMA").alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    bio = io.BytesIO()
    doc.save(bio)
    return bio

# =============================================================================
# 7. INTERFAZ GRÁFICA PRINCIPAL
# =============================================================================

# SIDEBAR (DATOS PERSISTENTES)
with st.sidebar:
    st.image("https://www.previred.com/wp-content/uploads/2021/01/logo-previred.png", width=120)
    
    st.markdown("### 🏢 Configuración Empresa")
    # Logo para PDF
    up_logo = st.file_uploader("Logo (Para PDF)", type=["png", "jpg"])
    if up_logo: st.session_state.logo_bytes = up_logo.read()
    
    with st.expander("Datos Empresa (Fijos)", expanded=False):
        st.session_state.empresa['rut'] = st.text_input("RUT", st.session_state.empresa['rut'])
        st.session_state.empresa['nombre'] = st.text_input("Razón Social", st.session_state.empresa['nombre'])
        st.session_state.empresa['rep_nombre'] = st.text_input("Rep. Legal", st.session_state.empresa['rep_nombre'])
        st.session_state.empresa['rep_rut'] = st.text_input("RUT Rep.", st.session_state.empresa['rep_rut'])
        st.session_state.empresa['direccion'] = st.text_input("Dirección", st.session_state.empresa['direccion'])
        st.session_state.empresa['ciudad'] = st.text_input("Ciudad", st.session_state.empresa['ciudad'])
        st.session_state.empresa['giro'] = st.text_input("Giro", st.session_state.empresa['giro'])

    # DATOS TRABAJADOR OPCIONALES
    st.markdown("### 👤 Configuración Trabajador")
    with st.expander("Datos Trabajador (Opcional)", expanded=False):
        st.info("Llene estos datos solo si desea generar el contrato final. No es necesario para simular sueldo.")
        st.session_state.trabajador['nombre'] = st.text_input("Nombre", st.session_state.trabajador['nombre'])
        st.session_state.trabajador['rut'] = st.text_input("RUT Trab.", st.session_state.trabajador['rut'])
        st.session_state.trabajador['direccion'] = st.text_input("Domicilio", st.session_state.trabajador['direccion'])
        st.session_state.trabajador['nacimiento'] = st.date_input("Nacimiento", value=date(1990,1,1), min_value=date(1940,1,1), max_value=datetime.now())

    st.divider()
    uf_v, utm_v = obtener_indicadores()
    st.metric("UF", fmt(uf_v).replace("$",""))
    st.metric("UTM", fmt(utm_v))

st.title("HR Suite Universe V39")
st.markdown("**Sistema Integral de Gestión de Personas y Contratos**")

tabs = st.tabs(["💰 Calculadora", "🧠 Perfil & Talentos", "📜 Legal Hub", "📊 Indicadores Completos"])

# --- TAB 1: CALCULADORA ---
with tabs[0]:
    with st.expander("📘 Guía de Uso"): st.write("Ingrese el Líquido deseado. El sistema calculará el Bruto necesario. Si el trabajador tiene Isapre sobre el 7%, se mostrará la diferencia.")
    
    c1, c2 = st.columns(2)
    with c1:
        liq = st.number_input("Líquido Objetivo", 1000000, step=50000); mostrar_miles(liq)
        col = st.number_input("Colación", 50000); mov = st.number_input("Movilización", 50000)
    with c2:
        con = st.selectbox("Contrato", ["Indefinido", "Plazo Fijo", "Sueldo Empresarial"])
        afp = st.selectbox("AFP", ["Capital", "Habitat", "Modelo", "Uno", "SIN AFP"])
        sal = st.selectbox("Salud", ["Fonasa (7%)", "Isapre (UF)"])
        plan = st.number_input("Plan UF", 0.0) if sal == "Isapre (UF)" else 0.0

    if st.button("CALCULAR SIMULACIÓN"):
        res = calcular_nomina_reversa(liq, col, mov, con, afp, sal, plan, uf_v, utm_v, 529000)
        if res:
            st.session_state.calculo_actual = res
            if res.get('Warning'): st.warning(res['Warning'])
            
            k1, k2, k3 = st.columns(3)
            k1.metric("Sueldo Base", fmt(res['Sueldo Base']))
            k2.metric("Líquido Final", fmt(res['LÍQUIDO_FINAL']))
            k3.metric("Costo Empresa", fmt(res['COSTO TOTAL']))
            
            # Liquidación HTML
            st.markdown(f"""
            <div class="liq-box">
                <div class="liq-header">LIQUIDACIÓN SIMULADA</div>
                <div class="liq-row"><span>Sueldo Base:</span><span>{fmt(res['Sueldo Base'])}</span></div>
                <div class="liq-row"><span>Gratificación:</span><span>{fmt(res['Gratificación'])}</span></div>
                <div class="liq-row"><span>No Imponibles:</span><span>{fmt(res['No Imponibles'])}</span></div>
                <hr>
                <div class="liq-row"><span>AFP + Cesantía:</span><span style="color:red">-{fmt(res['AFP']+res['AFC'])}</span></div>
                <div class="liq-row"><span>Salud Legal (7%):</span><span style="color:red">-{fmt(res['Salud_Legal'])}</span></div>
                {f'<div class="liq-row"><span>Adicional Isapre:</span><span style="color:red">-{fmt(res["Adicional_Salud"])}</span></div>' if res['Adicional_Salud'] > 0 else ''}
                <div class="liq-row"><span>Impuesto:</span><span style="color:red">-{fmt(res['Impuesto'])}</span></div>
                <div class="liq-total">A PAGAR: {fmt(res['LÍQUIDO_FINAL'])}</div>
            </div>
            """, unsafe_allow_html=True)

# --- TAB 2: PERFIL & TALENTO (DUAL) ---
with tabs[1]:
    st.header("Análisis de Ajuste (Match)")
    st.markdown("Suba el **Perfil de Cargo** (PDF) y el **Currículum** (PDF) para compararlos.")
    
    c_perf, c_cv = st.columns(2)
    up_perf = c_perf.file_uploader("1. Subir Perfil de Cargo (PDF)", type="pdf")
    up_cv = c_cv.file_uploader("2. Subir Currículum (PDF)", type="pdf")
    
    if up_perf and up_cv:
        if st.button("ANALIZAR COINCIDENCIA"):
            txt_p = leer_pdf(up_perf)
            txt_c = leer_pdf(up_cv)
            if txt_p and txt_c:
                score, enc, fal = motor_analisis_dual(txt_c, txt_p)
                c1, c2 = st.columns([1,2])
                c1.metric("Match Score", f"{score}%")
                c1.plotly_chart(go.Figure(go.Indicator(mode="gauge+number", value=score, gauge={'axis':{'range':[0,100]}, 'bar':{'color':"#004a99"}})), use_container_width=True)
                c2.success(f"✅ Coincidencias: {', '.join(enc)}")
                c2.error(f"⚠️ Brechas: {', '.join(fal)}")
    
    st.markdown("---")
    st.markdown("#### O definir Perfil Manualmente:")
    cargo = st.text_input("Nombre Cargo Manual", "Analista")
    # (Aquí iría la lógica de generación de perfil manual anterior si se desea)

# --- TAB 3: LEGAL HUB (REPOSITORIO) ---
with tabs[2]:
    st.header("Centro de Documentación Legal")
    
    col_a, col_b = st.columns(2)
    
    with col_a:
        st.subheader("1. Generador Automático")
        st.info("Usa los datos calculados en la Pestaña 1 y del Sidebar.")
        if st.button("Generar Contrato con Datos"):
            if st.session_state.calculo_actual and st.session_state.empresa['rut']:
                # Lógica simplificada llamada a generador
                st.success("Contrato Generado (Simulación)")
            else: st.warning("Faltan datos.")
            
    with col_b:
        st.subheader("2. Banco de Modelos (Templates)")
        st.info("Descargue formatos tipo para llenar manualmente.")
        t_tipo = st.selectbox("Seleccione Documento", ["Contrato", "Carta Amonestación", "Finiquito", "Carta Despido"])
        
        if LIBRARIES_OK:
            docx_bytes = generar_plantilla_generica(t_tipo)
            st.download_button(f"⬇️ Descargar Modelo {t_tipo}", docx_bytes, f"Modelo_{t_tipo}.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")

# --- TAB 4: INDICADORES COMPLETOS (PREVIRED) ---
with tabs[3]:
    st.header("Indicadores Previsionales (Noviembre 2025)")
    st.caption("Fuente: Previred")
    
    rentas, topes, afp, cesantia, asig, apv = get_previred_data()
    
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Rentas Mínimas")
        st.table(rentas)
        st.subheader("Topes Imponibles")
        st.table(topes)
        st.subheader("Asignación Familiar")
        st.table(asig)
    
    with c2:
        st.subheader("Tasas AFP")
        st.table(afp)
        st.subheader("Seguro Cesantía")
        st.table(cesantia)
        st.subheader("APV")
        st.table(apv)
    
    st.markdown("---")
    st.subheader("Impuesto Único Segunda Categoría")
    imp_data = []
    tabla = [(13.5,0,0),(30,0.04,0.54),(50,0.08,1.74),(70,0.135,4.49),(90,0.23,11.14),(120,0.304,17.80),(310,0.35,23.32),(99999,0.40,38.82)]
    for l, f, r in tabla:
        imp_data.append([f"Hasta {l} UTM", f"{f*100:.2f}%", fmt(r*utm_v)])
    st.table(pd.DataFrame(imp_data, columns=["Tramo", "Factor", "Rebaja"]))
