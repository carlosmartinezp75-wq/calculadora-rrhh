import streamlit as st
import pandas as pd
import requests
import base64
import os
import io
import zipfile
import random
from datetime import datetime, date
import plotly.graph_objects as go
import plotly.express as px

# =============================================================================
# 1. GESTIÓN DE LIBRERÍAS (Validación de Entorno)
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
    page_title="HR Suite Enterprise V44",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inicialización de Estado (Memoria de la App)
def init_session():
    defaults = {
        "empresa": {"rut": "", "nombre": "", "giro": "Servicios", "direccion": "", "ciudad": "Santiago", "rep_nombre": "", "rep_rut": ""},
        "trabajador": {"rut": "", "nombre": "", "nacionalidad": "Chilena", "civil": "Soltero", "nacimiento": date(1990, 1, 1), "domicilio": "", "cargo": ""},
        "calculo_actual": None,
        "perfil_generado": None,
        "plan_carrera": None,
        "analisis_cv": None,
        "logo_bytes": None
    }
    for k, v in defaults.items():
        if k not in st.session_state: st.session_state[k] = v

init_session()

# =============================================================================
# 3. SISTEMA DE DISEÑO (CSS CORPORATIVO)
# =============================================================================
def cargar_estilos():
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
            padding: 2rem; border-radius: 12px; box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        }}
        h1, h2, h3 {{color: #004a99 !important; font-family: 'Segoe UI', sans-serif;}}
        .stButton>button {{
            background: linear-gradient(90deg, #004a99 0%, #003366 100%);
            color: white !important; font-weight: bold; border-radius: 6px;
            height: 3rem; width: 100%; border: none; transition: 0.3s;
        }}
        .stButton>button:hover {{transform: translateY(-2px); box-shadow: 0 6px 12px rgba(0,0,0,0.2);}}
        
        .liq-paper {{
            border: 1px solid #ccc; padding: 30px; background: #fff;
            font-family: 'Courier New', monospace; margin-top: 20px;
        }}
        .liq-header {{text-align: center; border-bottom: 2px solid #000; padding-bottom: 10px; margin-bottom: 20px; font-weight: bold;}}
        .liq-row {{display: flex; justify-content: space-between; border-bottom: 1px dotted #ccc; padding: 5px 0;}}
        .liq-total {{background: #e3f2fd; padding: 15px; font-weight: bold; font-size: 1.2em; border: 2px solid #004a99; margin-top: 20px; color: #004a99; text-align: right;}}
        
        .feedback-success {{color: #28a745; font-weight: bold; font-size: 0.85em; margin-top: -10px;}}
        .glosa-warning {{background-color: #fff3cd; color: #856404; padding: 10px; border-left: 5px solid #ffeeba; margin-top: 10px; font-size: 0.9em;}}
        </style>
        """, unsafe_allow_html=True)

cargar_estilos()

# =============================================================================
# 4. UTILIDADES Y DATA
# =============================================================================
def fmt(valor):
    if pd.isna(valor) or valor == "": return "$0"
    try: return "${:,.0f}".format(float(valor)).replace(",", ".")
    except: return str(valor)

def mostrar_feedback(valor):
    if valor > 0: st.markdown(f'<p class="feedback-success">✅ Ingresaste: {fmt(valor)}</p>', unsafe_allow_html=True)

def obtener_indicadores():
    return {"UF": 39643.59, "UTM": 69542.0, "SUELDO_MIN": 529000, "TOPE_AFP_UF": 87.8, "TOPE_AFC_UF": 131.9}

IND = obtener_indicadores()

# =============================================================================
# 5. MOTORES DE CÁLCULO
# =============================================================================

def calcular_sueldo_inteligente(liquido_obj, col, mov, contrato, afp_n, salud_t, plan_uf):
    no_imp = col + mov
    liq_tributable_meta = liquido_obj - no_imp
    
    if liq_tributable_meta < IND["SUELDO_MIN"] * 0.4: return None

    # Topes y Tasas
    TOPE_GRAT = (4.75 * IND["SUELDO_MIN"]) / 12
    TASAS_AFP = {"Capital": 11.44, "Cuprum": 11.44, "Habitat": 11.27, "PlanVital": 11.16, "Provida": 11.45, "Modelo": 10.58, "Uno": 10.46, "SIN AFP": 0.0}
    
    es_emp = (contrato == "Sueldo Empresarial")
    tasa_afp = 0.0 if es_emp else (0.10 + (TASAS_AFP.get(afp_n, 11.44)/100))
    if afp_n == "SIN AFP": tasa_afp = 0.0
    
    tasa_afc_trab = 0.006 if (contrato == "Indefinido" and not es_emp) else 0.0
    tasa_afc_emp = 0.024
    if not es_emp: tasa_afc_emp = 0.024 if contrato == "Indefinido" else 0.03

    # Goal Seek
    min_b, max_b = 100000, liq_tributable_meta * 2.5
    
    for _ in range(150):
        base = (min_b + max_b) / 2
        grat = min(base * 0.25, TOPE_GRAT)
        if es_emp: grat = 0
        tot_imp = base + grat
        
        b_prev = min(tot_imp, 87.8 * IND["UF"])
        b_afc = min(tot_imp, 131.9 * IND["UF"])
        
        m_afp = int(b_prev * tasa_afp)
        m_afc = int(b_afc * tasa_afc_trab)
        legal_7 = int(b_prev * 0.07) # Siempre calculamos con el 7% base
        
        base_trib = max(0, tot_imp - m_afp - legal_7 - m_afc)
        
        imp = 0 # Tabla Nov 2025 simplificada
        if base_trib > 13.5 * IND["UTM"]: imp = int(base_trib * 0.04)
        if base_trib > 30 * IND["UTM"]: imp = int((base_trib * 0.08) - (1.74 * IND["UTM"]))
        imp = max(0, imp)
        
        liq_calc = tot_imp - m_afp - legal_7 - m_afc - imp
        
        if abs(liq_calc - liq_tributable_meta) < 50:
            # Lógica Isapre: El trabajador paga la diferencia
            salud_total = legal_7
            adicional = 0
            glosa = None
            
            if salud_t == "Isapre (UF)":
                plan_pesos = int(plan_uf * IND["UF"])
                if plan_pesos > legal_7:
                    salud_total = plan_pesos
                    adicional = plan_pesos - legal_7
                    glosa = f"⚠️ NOTA IMPORTANTE: Su plan de Isapre ({fmt(plan_pesos)}) excede el 7% legal ({fmt(legal_7)}). La diferencia de {fmt(adicional)} se descuenta del líquido, resultando en un monto menor al solicitado."
            
            liq_final = tot_imp - m_afp - salud_total - m_afc - imp + no_imp
            
            ap_sis = int(b_prev * 0.0149)
            ap_mut = int(b_prev * 0.0093)
            ap_afc_e = int(b_afc * tasa_afc_emp)
            
            return {
                "Sueldo Base": int(base), "Gratificación": int(grat), "Total Imponible": int(tot_imp),
                "No Imponibles": int(no_imp), "LÍQUIDO_OBJETIVO": int(liquido_obj), "LÍQUIDO_FINAL": int(liq_final),
                "AFP": m_afp, "Salud_Legal": legal_7, "Adicional_Salud": adicional, "Salud_Total": salud_total,
                "AFC": m_afc, "Impuesto": imp, "Total Descuentos": m_afp + salud_total + m_afc + imp,
                "Aportes Empresa": ap_sis + ap_mut + ap_afc_e, "COSTO TOTAL": int(tot_imp + no_imp + ap_sis + ap_mut + ap_afc_e),
                "Glosa": glosa
            }
            break
        elif liq_calc < liq_tributable_meta: min_b = base
        else: max_b = base
    return None

def calcular_finiquito_legal(f_ini, f_fin, base, causal, vac_pend):
    dias = (f_fin - f_ini).days
    anos = int(dias/365.25)
    if (dias/365.25 - anos)*12 >= 6: anos += 1
    if anos > 11: anos = 11
    
    tope_pesos = 90 * IND["UF"]
    base_calc = min(base, tope_pesos)
    
    indem = int(base_calc * anos) if causal == "Necesidades de la Empresa" else 0
    aviso = int(base_calc) if causal in ["Necesidades de la Empresa", "Desahucio"] else 0
    vacs = int(vac_pend * 1.25 * (base/30))
    
    return {"Anos": indem, "Aviso": aviso, "Vacaciones": vacs, "Total": indem+aviso+vacs}

# =============================================================================
# 6. MOTORES DE INTELIGENCIA (PERFIL Y CV)
# =============================================================================

def generar_perfil_detallado(cargo, rubro):
    if not cargo: return None
    skills = {
        "Minería": ["Normativa Sernageomin", "ISO 45001", "Gestión de Activos"],
        "TI": ["Scrum/Agile", "Cloud Architecture", "DevOps"],
        "Retail": ["Visual Merchandising", "Customer Experience", "Logística"],
        "Salud": ["Gestión Clínica", "IAAS", "Acreditación"],
        "Construcción": ["BIM", "Last Planner", "Prevención Riesgos"]
    }
    rubro_s = skills.get(rubro, ["Gestión de Proyectos", "Excel Avanzado"])
    
    return {
        "titulo": cargo.title(),
        "dependencia": "Gerencia General",
        "objetivo": f"Gestionar y optimizar los procesos de {cargo} en el rubro {rubro}.",
        "funciones": ["Planificación estratégica.", "Control presupuestario.", "Liderazgo de equipos.", "Reportes KPI."],
        "requisitos": ["Título Profesional.", f"Experiencia 4 años en {rubro}.", "Inglés Técnico.", "Manejo ERP."],
        "competencias": ["Liderazgo", "Negociación", "Resiliencia"],
        "condiciones": ["Art. 22", "Seguro Salud", "Bono Desempeño"]
    }

def generar_plan_carrera(cargo, rubro):
    return {
        "corto": ["Inducción Corporativa", "Certificación Técnica", "Metas Trimestrales"],
        "mediano": ["Liderazgo de Proyectos", "Mentoring", "Diplomado Especialización"],
        "largo": ["Jefatura de Área", "MBA / Magíster", "Plan de Sucesión"]
    }

def analizar_cv(texto, perfil):
    kws = [k.lower() for k in perfil['competencias'] + perfil['requisitos']]
    txt = texto.lower()
    enc = [k.title() for k in kws if k.split()[0] in txt]
    fal = [k.title() for k in kws if k.split()[0] not in txt]
    score = int((len(enc)/len(kws))*100) + 15
    score = min(99, max(10, score))
    nivel = "Senior" if score > 75 else "Junior"
    return score, nivel, enc, fal

def leer_pdf(archivo):
    if not LIBRARIES_OK: return None
    try:
        text = ""
        with pdfplumber.open(archivo) as pdf:
            for p in pdf.pages: text += (p.extract_text() or "")
        return text
    except: return None

# =============================================================================
# 7. GENERADORES DOCUMENTALES (PDF / WORD / EXCEL)
# =============================================================================

def generar_pdf_reporte_perfil(perfil, plan):
    if not LIBRARIES_OK: return None
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16); pdf.cell(0, 10, f"PERFIL DE CARGO: {perfil['titulo'].upper()}", 0, 1, 'C')
    pdf.ln(5)
    
    pdf.set_font("Arial", 'B', 12); pdf.cell(0, 8, "1. IDENTIFICACION", 0, 1)
    pdf.set_font("Arial", '', 10)
    pdf.multi_cell(0, 6, f"Objetivo: {perfil['objetivo']}\nDependencia: {perfil['dependencia']}")
    pdf.ln(5)
    
    pdf.set_font("Arial", 'B', 12); pdf.cell(0, 8, "2. REQUISITOS Y COMPETENCIAS", 0, 1)
    pdf.set_font("Arial", '', 10)
    for r in perfil['requisitos']: pdf.cell(0, 6, f"- {r}", 0, 1)
    pdf.ln(5)
    
    pdf.set_font("Arial", 'B', 12); pdf.cell(0, 8, "3. PLAN DE CARRERA SUGERIDO", 0, 1)
    pdf.set_font("Arial", '', 10)
    pdf.cell(0, 6, "CORTO PLAZO:", 0, 1)
    for p in plan['corto']: pdf.cell(0, 6, f"  * {p}", 0, 1)
    
    return pdf.output(dest='S').encode('latin-1')

def generar_contrato_docx(fin, emp, trab, cond):
    if not LIBRARIES_OK: return None
    doc = Document()
    style = doc.styles['Normal']; style.font.name = 'Arial'; style.font.size = Pt(11)
    
    doc.add_heading('CONTRATO DE TRABAJO', 0).alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.add_paragraph("")
    
    fecha = datetime.now().strftime("%d de %B de %Y")
    intro = f"""En {emp['ciudad']}, a {fecha}, entre "{emp['nombre']}", RUT {emp['rut']}, representada por {emp['rep_nombre']}, en adelante EMPLEADOR; y {trab['nombre']}, RUT {trab['rut']}, en adelante TRABAJADOR, se acuerda:"""
    doc.add_paragraph(intro).alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    
    clausulas = [
        ("PRIMERO:", f"El trabajador se desempeñará como {cond['cargo']}, realizando: {cond['funciones']}."),
        ("SEGUNDO:", f"Sueldo Base: {fmt(fin['Sueldo Base'])}. Gratificación: {fmt(fin['Gratificación'])}."),
        ("TERCERO:", "Jornada de 44 horas semanales (Ley 40 Horas)."),
        ("CUARTO:", "Obligación de confidencialidad y respeto al Reglamento Interno (Ley Karin)."),
        ("QUINTO:", f"Contrato {cond['tipo']} con inicio el {cond['inicio']}.")
    ]
    for t, x in clausulas: p=doc.add_paragraph(); r=p.add_run(t); r.bold=True; p.add_run(f" {x}")
    
    bio = io.BytesIO(); doc.save(bio); return bio

def generar_plantilla_excel():
    df = pd.DataFrame(columns=["TIPO", "NOMBRE", "RUT", "CARGO", "SUELDO", "FECHA_INI"])
    df.loc[0] = ["Contrato", "Juan Perez", "1-9", "Analista", 800000, "2025-01-01"]
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer: df.to_excel(writer, index=False)
    buffer.seek(0)
    return buffer

def procesar_masivo(df, empresa):
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zf:
        for i, r in df.iterrows():
            try:
                # Simulación de generación para masivo
                dummy_fin = {"Sueldo Base": r.get('SUELDO',0), "Gratificación": 0, "No Imponibles": 0}
                dummy_trab = {"nombre": str(r.get('NOMBRE','')), "rut": str(r.get('RUT',''))}
                dummy_cond = {"cargo": str(r.get('CARGO','')), "funciones": "N/A", "tipo": "Indefinido", "inicio": str(r.get('FECHA_INI',''))}
                
                doc = generar_contrato_docx(dummy_fin, empresa, dummy_trab, dummy_cond)
                zf.writestr(f"Doc_{dummy_trab['nombre']}.docx", doc.getvalue())
            except: pass
    zip_buffer.seek(0)
    return zip_buffer

# =============================================================================
# 8. INTERFAZ GRÁFICA (DASHBOARD)
# =============================================================================

# SIDEBAR
with st.sidebar:
    st.image("https://www.previred.com/wp-content/uploads/2021/01/logo-previred.png", width=120)
    
    # Logo PDF
    up_logo = st.file_uploader("Logo Empresa (PDF)", type=["png","jpg"])
    if up_logo: st.session_state.logo_bytes = up_logo.read()
    
    with st.expander("🏢 Datos Empresa (Base)", expanded=True):
        st.session_state.empresa['rut'] = st.text_input("RUT", st.session_state.empresa['rut'])
        st.session_state.empresa['nombre'] = st.text_input("Razón Social", st.session_state.empresa['nombre'])
        st.session_state.empresa['rep_nombre'] = st.text_input("Rep. Legal", st.session_state.empresa['rep_nombre'])
        st.session_state.empresa['ciudad'] = st.text_input("Ciudad", st.session_state.empresa['ciudad'])
        st.session_state.empresa['direccion'] = st.text_input("Dirección", st.session_state.empresa['direccion'])

    with st.expander("👤 Datos Trabajador (Opcional)", expanded=False):
        st.caption("Llenar solo para generar contrato final.")
        st.session_state.trabajador['nombre'] = st.text_input("Nombre", st.session_state.trabajador['nombre'])
        st.session_state.trabajador['rut'] = st.text_input("RUT Trab.", st.session_state.trabajador['rut'])
        st.session_state.trabajador['direccion'] = st.text_input("Domicilio", st.session_state.trabajador['direccion'])

st.title("HR Suite Enterprise V44")
st.markdown("**Sistema Integral de Gestión de Personas**")

tabs = st.tabs(["💰 Calculadora", "📂 Carga Masiva", "📋 Perfil & Carrera", "📜 Legal Hub", "📊 Indicadores"])

# --- TAB 1: CALCULADORA ---
with tabs[0]:
    with st.expander("📘 GUÍA DE USO: Calculadora de Sueldos"):
        st.write("""
        1. Ingrese el **Líquido** que negoció con el trabajador.
        2. Si el trabajador tiene **Isapre**, ingrese el valor del plan en UF.
        3. Si el plan excede el 7% legal, el sistema **descontará la diferencia** del líquido.
        4. Presione **Calcular** para ver la Liquidación y el Costo Empresa.
        """)
    
    c1, c2 = st.columns(2)
    with c1:
        liq = st.number_input("Líquido Objetivo", 1000000, step=50000); mostrar_miles(liq)
        col = st.number_input("Colación", 50000); mov = st.number_input("Movilización", 50000)
    with c2:
        con = st.selectbox("Contrato", ["Indefinido", "Plazo Fijo", "Empresarial"])
        afp = st.selectbox("AFP", ["Capital", "Habitat", "Modelo", "Uno", "SIN AFP"])
        sal = st.selectbox("Salud", ["Fonasa (7%)", "Isapre (UF)"])
        plan = st.number_input("Plan UF", 0.0) if sal == "Isapre (UF)" else 0.0

    if st.button("CALCULAR"):
        res = calcular_sueldo_inteligente(liq, col, mov, con, afp, sal, plan)
        if res:
            st.session_state.calculo_actual = res
            
            if res['Glosa']: st.markdown(f"<div class='glosa-warning'>{res['Glosa']}</div>", unsafe_allow_html=True)
            
            k1, k2, k3 = st.columns(3)
            k1.metric("Base", fmt(res['Sueldo Base']))
            k2.metric("Líquido Final", fmt(res['LÍQUIDO_FINAL']))
            k3.metric("Costo Empresa", fmt(res['COSTO TOTAL']))
            
            # Liquidación HTML
            st.markdown(f"""
            <div class="liq-paper">
                <div class="liq-header">LIQUIDACIÓN SIMULADA</div>
                <div class="liq-row"><span>Base:</span><span>{fmt(res['Sueldo Base'])}</span></div>
                <div class="liq-row"><span>Gratif:</span><span>{fmt(res['Gratificación'])}</span></div>
                <div class="liq-row"><span>No Imp:</span><span>{fmt(res['No Imponibles'])}</span></div>
                <hr>
                <div class="liq-row"><span>AFP:</span><span style="color:red">-{fmt(res['AFP'])}</span></div>
                <div class="liq-row"><span>Salud (Total):</span><span style="color:red">-{fmt(res['Salud_Total'])}</span></div>
                <div class="liq-row"><span>Impuesto:</span><span style="color:red">-{fmt(res['Impuesto'])}</span></div>
                <div class="liq-total">PAGO: {fmt(res['LÍQUIDO_FINAL'])}</div>
            </div>
            """, unsafe_allow_html=True)

# --- TAB 2: MASIVA ---
with tabs[1]:
    with st.expander("📘 GUÍA DE USO: Carga Masiva"):
        st.write("1. Descargue la Plantilla Excel. 2. Llene los datos. 3. Suba el archivo para generar los contratos.")
    
    if LIBRARIES_OK:
        plantilla = generar_plantilla_excel()
        st.download_button("1. Descargar Plantilla", plantilla, "plantilla.xlsx")
        
        up = st.file_uploader("2. Subir Excel", type="xlsx")
        if up and st.button("PROCESAR ZIP"):
            if st.session_state.empresa['rut']:
                zip_f = procesar_masivo(pd.read_excel(up), st.session_state.empresa)
                st.download_button("⬇️ Descargar ZIP", zip_f, "docs.zip", "application/zip")
            else: st.error("Faltan datos empresa.")

# --- TAB 3: PERFIL ---
with tabs[2]:
    with st.expander("📘 GUÍA DE USO: Perfiles"):
        st.write("Defina un cargo y rubro para generar el perfil y plan de carrera. Puede descargar el PDF.")
        
    c1, c2 = st.columns(2)
    cargo = c1.text_input("Cargo", "Jefe de Ventas")
    rubro = c2.selectbox("Rubro", ["Minería", "Tecnología", "Retail", "Salud", "Construcción"])
    
    if cargo:
        perf = generar_perfil_detallado(cargo, rubro)
        plan = generar_plan_carrera(cargo, rubro)
        
        st.info(f"**Misión:** {perf['objetivo']}")
        c1, c2 = st.columns(2)
        c1.write("**Funciones:**"); c1.write("\n".join([f"- {x}" for x in perf['funciones']]))
        c2.write("**Requisitos:**"); c2.write("\n".join([f"- {x}" for x in perf['requisitos']]))
        
        st.markdown("---")
        st.subheader("Plan de Carrera")
        c1, c2, c3 = st.columns(3)
        c1.markdown("##### Corto Plazo"); c1.write("\n".join(plan['corto']))
        c2.markdown("##### Mediano Plazo"); c2.write("\n".join(plan['mediano']))
        c3.markdown("##### Largo Plazo"); c3.write("\n".join(plan['largo']))
        
        if LIBRARIES_OK:
            pdf_perf = generar_pdf_reporte_perfil(perf, plan)
            st.download_button("⬇️ Descargar Perfil PDF", pdf_perf, "perfil.pdf", "application/pdf")

# --- TAB 4: LEGAL HUB ---
with tabs[3]:
    with st.expander("📘 GUÍA DE USO: Legal"):
        st.write("Genere contratos individuales o finiquitos. Requiere cálculo previo para contratos.")
    
    modo = st.radio("Tipo", ["Contrato", "Finiquito"])
    
    if modo == "Contrato":
        if st.session_state.calculo_actual:
            if st.button("Generar Word"):
                if st.session_state.empresa['rut']:
                    cond = {"cargo": cargo, "funciones": "N/A", "tipo": "Indefinido", "inicio": date.today()}
                    doc = generar_contrato_docx(st.session_state.calculo_actual, st.session_state.empresa, st.session_state.trabajador, cond)
                    st.download_button("Descargar", doc.getvalue(), "contrato.docx")
                else: st.error("Faltan datos empresa.")
        else: st.info("Calcule sueldo en Pestaña 1.")
        
    elif modo == "Finiquito":
        c1, c2 = st.columns(2)
        fi = c1.date_input("Inicio", date(2020,1,1)); ft = c2.date_input("Fin", date.today())
        base = st.number_input("Base", 1000000); vac = st.number_input("Vacaciones", 0)
        causal = st.selectbox("Causal", ["Necesidades", "Renuncia"])
        
        if st.button("Calcular Finiquito"):
            res = calcular_finiquito_legal(fi, ft, base, causal, vac)
            st.write(res)

# --- TAB 5: INDICADORES ---
with tabs[4]:
    st.header("Indicadores Oficiales")
    st.info(f"UF: {fmt(IND['UF'])} | UTM: {fmt(IND['UTM'])}")
