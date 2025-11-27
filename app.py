import streamlit as st
import pandas as pd
import requests
import base64
import os
import io
import random
from datetime import datetime, date
import plotly.graph_objects as go

# --- 0. VALIDACIÓN DE LIBRERÍAS (CRÍTICO) ---
try:
    import pdfplumber
    from fpdf import FPDF
    from docx import Document
    from docx.shared import Pt, Inches
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    LIBRARIES_OK = True
except ImportError:
    LIBRARIES_OK = False

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="HR Suite Ultimate V30", page_icon="💎", layout="wide")

# Inicialización de Estado (Persistencia de Datos)
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
        .block-container {{
            background-color: rgba(255, 255, 255, 0.98); 
            padding: 2.5rem; 
            border-radius: 15px; 
            box-shadow: 0 10px 40px rgba(0,0,0,0.15);
        }}
        h1, h2, h3 {{color: #004a99 !important; font-family: 'Segoe UI', sans-serif; font-weight: 800;}}
        .miles-feedback {{font-size: 0.8rem; color: #28a745; font-weight: bold; margin-top: -10px;}}
        
        /* Botones Pro */
        .stButton>button {{
            background-color: #004a99 !important;
            color: white !important;
            font-weight: bold;
            border-radius: 8px;
            width: 100%;
            height: 3rem;
            border: 1px solid #003366;
        }}
        .stButton>button:hover {{background-color: #003366 !important; transform: translateY(-2px);}}
        
        /* Liquidación Box */
        .liq-box {{
            border: 1px solid #ccc; padding: 20px; background: #fff; font-family: 'Courier New';
            box-shadow: inset 0 0 10px #f9f9f9;
        }}
        .liq-row {{display: flex; justify-content: space-between; border-bottom: 1px dashed #ddd; padding: 4px 0;}}
        .liq-total {{background: #e3f2fd; padding: 10px; font-weight: bold; font-size: 1.2em; border: 1px solid #004a99; margin-top: 15px;}}
        </style>
        """, unsafe_allow_html=True)

cargar_estilos()

# --- 3. FUNCIONES UTILITARIAS ---
def fmt(valor): return "$0" if pd.isna(valor) else "${:,.0f}".format(valor).replace(",", ".")
def mostrar_miles(valor): 
    if valor > 0: st.markdown(f'<p class="miles-feedback">Ingresaste: {fmt(valor)}</p>', unsafe_allow_html=True)

def obtener_indicadores():
    try:
        r = requests.get('https://mindicador.cl/api', timeout=2)
        d = r.json()
        return float(d['uf']['valor']), float(d['utm']['valor'])
    except: return 39643.59, 69542.0

# --- 4. GENERADORES DOCUMENTALES (RECUPERADOS) ---

# A. PDF LIQUIDACIÓN
def generar_pdf_liq(res, empresa, trabajador):
    if not LIBRARIES_OK: return None
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, "LIQUIDACION DE SUELDO (SIMULACION)", 0, 1, 'C')
    pdf.ln(10)
    
    pdf.set_font("Arial", '', 10)
    pdf.cell(0, 6, f"Empresa: {empresa['nombre']} | RUT: {empresa['rut']}", 0, 1)
    pdf.cell(0, 6, f"Trabajador: {trabajador['nombre']} | RUT: {trabajador['rut']}", 0, 1)
    pdf.cell(0, 6, f"Fecha Emision: {datetime.now().strftime('%d/%m/%Y')}", 0, 1)
    pdf.ln(10)
    
    # Tabla
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(95, 8, "HABERES", 1, 0, 'C')
    pdf.cell(95, 8, "DESCUENTOS", 1, 1, 'C')
    pdf.set_font("Arial", '', 10)
    
    items = [
        ("Sueldo Base", res['Sueldo Base'], "AFP", res['AFP']),
        ("Gratificacion", res['Gratificación'], "Salud", res['Salud']),
        ("Movilizacion", res['No Imponibles']//2, "Seg. Cesantia", res['AFC']),
        ("Colacion", res['No Imponibles']//2, "Impuesto Unico", res['Impuesto'])
    ]
    
    for h_txt, h_val, d_txt, d_val in items:
        pdf.cell(60, 8, h_txt, 'L'); pdf.cell(35, 8, fmt(h_val), 'R')
        pdf.cell(60, 8, d_txt, 'L'); pdf.cell(35, 8, fmt(d_val), 'R')
        pdf.ln()
    
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(130, 10, "LIQUIDO A PAGAR", 1, 0, 'R')
    pdf.cell(60, 10, fmt(res['LÍQUIDO']), 1, 1, 'C')
    
    return pdf.output(dest='S').encode('latin-1')

# B. CONTRATO WORD ROBUSTO
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
    intro = f"""En {emp['ciudad']}, a {fecha}, entre "{emp['nombre'].upper()}", RUT {emp['rut']}, giro {emp.get('giro','Servicios')}, representada por {emp['rep_nombre'].upper()}, ambos domiciliados en {emp['direccion']}, en adelante "EMPLEADOR"; y {trab['nombre'].upper()}, RUT {trab['rut']}, nacionalidad {trab['nacionalidad']}, nacido el {str(trab['nacimiento'])}, domiciliado en {trab['direccion']}, en adelante "TRABAJADOR", se conviene:"""
    p = doc.add_paragraph(intro); p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    
    clausulas = [
        ("PRIMERO:", f"El Trabajador prestará servicios como {cond['cargo'].upper()}, desempeñando las funciones de: {cond['funciones']}."),
        ("SEGUNDO:", f"Sueldo Base: {fmt(fin['Sueldo Base'])}. Gratificación Legal: {fmt(fin['Gratificación'])} (Tope 4.75 IMM). Asignaciones: {fmt(fin['No Imponibles'])}."),
        ("TERCERO:", "La jornada será de 44 horas semanales, distribuidas de lunes a viernes (Sujeto a Ley 40 Horas)."),
        ("CUARTO:", "El Trabajador deberá cumplir con el Reglamento Interno de Orden, Higiene y Seguridad."),
        ("QUINTO (Confidencialidad):", "Se prohíbe la divulgación de información sensible de la empresa a terceros."),
        ("SEXTO (Vigencia):", f"El contrato es {cond['tipo']} e inicia el {str(cond['inicio'])}.")
    ]
    
    for tit, txt in clausulas:
        p = doc.add_paragraph(); r = p.add_run(tit); r.bold = True; p.add_run(f" {txt}")
    
    bio = io.BytesIO()
    doc.save(bio)
    return bio

# --- 5. MOTORES DE INTELIGENCIA (RECUPERADOS COMPLETOS) ---

def generar_perfil_detallado(cargo, rubro):
    if not cargo: return None
    # Base de conocimiento expandida
    skills_map = {
        "Tecnología": ["Cloud Computing (AWS/Azure)", "Scrum/Agile", "Python/SQL", "Cybersecurity"],
        "Minería": ["Normativa Sernageomin", "Gestión de Activos", "Seguridad Industrial", "Lean Mining"],
        "Retail": ["E-commerce", "Logística Última Milla", "Customer Experience", "Visual Merchandising"],
        "Salud": ["Gestión Clínica", "Calidad Asistencial", "Bioestadística", "Normativa Minsal"],
        "Construcción": ["Autocad/BIM", "Control de Costos", "Prevención de Riesgos", "Gestión de Obras"]
    }
    hard = skills_map.get(rubro, ["Gestión de Proyectos", "Excel Avanzado", "ERP", "Inglés"])
    
    return {
        "titulo": cargo.title(),
        "mision": f"Liderar y gestionar las operaciones de {cargo} en el sector {rubro}, asegurando la continuidad del negocio y el cumplimiento de estándares de calidad.",
        "funciones": [
            "Planificación estratégica y operativa del área.",
            "Control presupuestario (CAPEX y OPEX).",
            "Liderazgo de equipos multidisciplinarios.",
            "Reportabilidad de KPIs críticos a la Gerencia."
        ],
        "requisitos": ["Título Profesional afín.", f"Experiencia 3-5 años en {rubro}.", "Manejo de ERP.", "Inglés Técnico."],
        "competencias": ["Liderazgo", "Comunicación", "Resolución de Problemas", "Visión Estratégica"],
        "kpis": ["Cumplimiento Presupuestario", "Tasa de Retención", "Satisfacción Cliente", "Eficiencia Operativa"]
    }

def motor_analisis(texto_cv, perfil):
    # Lógica de coincidencia semántica simulada
    kws = [k.lower() for k in perfil['competencias'] + perfil['requisitos']]
    txt = texto_cv.lower()
    
    enc = list(set([k.title() for k in kws if k.split()[0] in txt])) # Coincidencia parcial
    fal = list(set([k.title() for k in kws if k.split()[0] not in txt]))
    
    score = int((len(enc) / len(kws)) * 100) + random.randint(10, 20)
    score = min(98, max(15, score))
    
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

# --- 6. CÁLCULO FINANCIERO ROBUSTO ---
def calcular_reverso(liquido, col, mov, contrato, afp_n, salud_t, plan, uf, utm, s_min):
    no_imp = col + mov
    liq_meta = liquido - no_imp
    if liq_meta < s_min * 0.4: return None
    
    TOPE_GRAT = (4.75 * s_min) / 12
    # Tasas Hardcoded Nov 2025 para seguridad
    TASAS = {"Capital":1.44,"Cuprum":1.44,"Habitat":1.27,"PlanVital":1.16,"Provida":1.45,"Modelo":0.58,"Uno":0.49,"SIN AFP":0.0}
    
    es_emp = (contrato == "Sueldo Empresarial")
    tasa_afp = 0.0 if es_emp else (0.10 + (TASAS.get(afp_n, 1.44)/100))
    if afp_n == "SIN AFP": tasa_afp = 0.0
    
    tasa_afc_trab = 0.006 if (contrato == "Indefinido" and not es_emp) else 0.0
    tasa_afc_emp = 0.024
    if not es_emp: tasa_afc_emp = 0.024 if contrato == "Indefinido" else 0.03
    
    min_b, max_b = 100000, liq_meta * 2.5
    for _ in range(150):
        base = (min_b + max_b) / 2
        grat = min(base * 0.25, TOPE_GRAT)
        if es_emp: grat = 0
        tot_imp = base + grat
        
        b_prev = min(tot_imp, 87.8*uf) # Tope 87.8 UF
        b_afc = min(tot_imp, 131.9*uf) # Tope 131.9 UF
        
        m_afp = int(b_prev * tasa_afp)
        m_afc = int(b_afc * tasa_afc_trab)
        
        leg_7 = int(b_prev * 0.07)
        m_sal = leg_7 if salud_t == "Fonasa (7%)" else max(int(plan*uf), leg_7)
        reb_trib = leg_7 if salud_t == "Fonasa (7%)" else leg_7
        
        base_trib = max(0, tot_imp - m_afp - reb_trib - m_afc)
        
        # Impuesto simplificado (Tramo 1 y 2 para velocidad)
        imp = 0
        if base_trib > 13.5*utm: imp = int(base_trib*0.04)
        if base_trib > 30*utm: imp = int((base_trib*0.08) - (1.74*utm))
        imp = max(0, imp)
        
        liq_calc = tot_imp - m_afp - m_sal - m_afc - imp
        
        if abs(liq_calc - liq_meta) < 500:
            ap_sis = int(b_prev*0.0149)
            ap_mut = int(b_prev*0.0093)
            ap_afc_e = int(b_afc*tasa_afc_emp)
            return {
                "Sueldo Base": int(base), "Gratificación": int(grat), "Total Imponible": int(tot_imp),
                "No Imponibles": int(no_imp), "LÍQUIDO": int(liq_calc+no_imp), 
                "AFP": m_afp, "Salud": m_sal, "AFC": m_afc, "Impuesto": imp,
                "Aportes Empresa": ap_sis + ap_mut + ap_afc_e, 
                "COSTO TOTAL": int(tot_imp+no_imp+ap_sis+ap_mut+ap_afc_e)
            }
            break
        elif liq_calc < liq_meta: min_b = base
        else: max_b = base
    return None

# --- 7. INTERFAZ GRÁFICA ---

with st.sidebar:
    st.image("https://www.previred.com/wp-content/uploads/2021/01/logo-previred.png", width=120)
    
    with st.expander("🏢 Datos Empresa (Fijo)", expanded=True):
        st.session_state.empresa['nombre'] = st.text_input("Razón Social", st.session_state.empresa['nombre'])
        st.session_state.empresa['rut'] = st.text_input("RUT Empresa", st.session_state.empresa['rut'])
        st.session_state.empresa['rep_nombre'] = st.text_input("Rep. Legal", st.session_state.empresa['rep_nombre'])
        st.session_state.empresa['rep_rut'] = st.text_input("RUT Rep.", st.session_state.empresa['rep_rut'])
        st.session_state.empresa['direccion'] = st.text_input("Dirección", st.session_state.empresa['direccion'])
        st.session_state.empresa['giro'] = st.text_input("Giro", st.session_state.empresa['giro'])
        st.session_state.empresa['ciudad'] = st.text_input("Ciudad", st.session_state.empresa['ciudad'])

    with st.expander("👤 Datos Trabajador (Opcional)", expanded=False):
        st.session_state.trabajador['nombre'] = st.text_input("Nombre", st.session_state.trabajador['nombre'])
        st.session_state.trabajador['rut'] = st.text_input("RUT", st.session_state.trabajador['rut'])
        st.session_state.trabajador['direccion'] = st.text_input("Domicilio", st.session_state.trabajador['direccion'])
        st.session_state.trabajador['nacimiento'] = st.date_input("Nacimiento", 
            value=st.session_state.trabajador['nacimiento'], 
            min_value=date(1950,1,1), 
            max_value=datetime.now())

    st.divider()
    uf_v, utm_v = obtener_indicadores()
    st.metric("UF", fmt(uf_v).replace("$",""))
    st.metric("UTM", fmt(utm_v))

st.title("HR Suite Enterprise V30")
st.markdown("**Sistema Integral de Gestión de Personas y Contratos**")

tabs = st.tabs(["💰 Calculadora", "📋 Perfil de Cargo", "🧠 Análisis CV", "🚀 Carrera", "📝 Contratos", "📊 Indicadores"])

# TAB 1: CALCULADORA (CON PDF)
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
        
        # Validación Isapre
        if sal == "Isapre (UF)" and (plan*uf_v) > (liq*0.07):
            st.warning("⚠️ El plan de Isapre supera el 7%. El costo empresa aumentará.")

    if st.button("CALCULAR NÓMINA"):
        res = calcular_reverso(liq, col, mov, con, afp, sal, plan, uf_v, utm_v, 529000)
        if res:
            st.session_state.calculo_actual = res
            k1, k2, k3 = st.columns(3)
            k1.metric("Sueldo Base", fmt(res['Sueldo Base']))
            k2.metric("Líquido", fmt(res['LÍQUIDO']), delta="Objetivo")
            k3.metric("Costo Empresa", fmt(res['COSTO TOTAL']), delta="Total", delta_color="inverse")
            
            # LIQUIDACIÓN VISUAL
            st.markdown(f"""
            <div class="liq-box">
                <div style="text-align:center; font-weight:bold; border-bottom:1px solid #000; margin-bottom:10px;">LIQUIDACIÓN SIMULADA</div>
                <div class="liq-row"><span>Sueldo Base:</span><span>{fmt(res['Sueldo Base'])}</span></div>
                <div class="liq-row"><span>Gratificación:</span><span>{fmt(res['Gratificación'])}</span></div>
                <div class="liq-row" style="background:#f0f0f0;"><span><b>TOTAL IMPONIBLE:</b></span><span><b>{fmt(res['Total Imponible'])}</b></span></div>
                <div class="liq-row"><span>No Imponibles:</span><span>{fmt(res['No Imponibles'])}</span></div>
                <br>
                <div class="liq-row"><span>AFP ({afp}):</span><span style="color:red">-{fmt(res['AFP'])}</span></div>
                <div class="liq-row"><span>Salud ({sal}):</span><span style="color:red">-{fmt(res['Salud'])}</span></div>
                <div class="liq-row"><span>Cesantía:</span><span style="color:red">-{fmt(res['AFC'])}</span></div>
                <div class="liq-row"><span>Impuesto:</span><span style="color:red">-{fmt(res['Impuesto'])}</span></div>
                <div class="liq-total">LÍQUIDO A PAGAR: {fmt(res['LÍQUIDO'])}</div>
            </div>
            """, unsafe_allow_html=True)
            
            # BOTÓN PDF (FUERA DEL FORM)
            if LIBRARIES_OK:
                pdf_data = generar_pdf_liq(res, st.session_state.empresa, st.session_state.trabajador)
                st.download_button("⬇️ Descargar Liquidación (PDF)", pdf_data, "liquidacion.pdf", "application/pdf")
        else: st.error("Error matemático.")

# TAB 2: PERFIL (ROBUSTO)
with tabs[1]:
    col1, col2 = st.columns(2)
    cargo = col1.text_input("Cargo", placeholder="Ej: Analista Contable")
    rubro = col2.selectbox("Rubro", ["Tecnología", "Minería", "Retail", "Salud", "Construcción", "Banca"])
    
    if cargo:
        st.session_state.cargo_actual = cargo
        st.session_state.rubro_actual = rubro
        perf = generar_perfil_detallado(cargo, rubro)
        st.session_state.perfil_actual = perf
        
        st.info(f"**Misión:** {perf['mision']}")
        c1, c2 = st.columns(2)
        c1.success("**Funciones:**\n" + "\n".join([f"- {x}" for x in perf['funciones']]))
        c2.warning("**Competencias:**\n" + "\n".join([f"- {x}" for x in perf['competencias']]))
        st.markdown("**KPIs:** " + ", ".join(perf['kpis']))

# TAB 3: ANÁLISIS CV
with tabs[2]:
    st.header("Análisis de Brechas")
    if not LIBRARIES_OK: st.warning("Faltan librerías.")
    else:
        uploaded = st.file_uploader("Subir CV (PDF)", type="pdf")
        if uploaded and st.session_state.perfil_actual:
            if st.button("ANALIZAR"):
                txt = leer_pdf(uploaded)
                if txt:
                    score, enc, fal, nivel = motor_analisis(txt, st.session_state.perfil_actual)
                    c1, c2 = st.columns([1,2])
                    c1.metric("Match", f"{score}%")
                    c1.info(f"Nivel: **{nivel}**")
                    c2.success(f"✅ Fortalezas: {', '.join(enc)}")
                    c2.error(f"⚠️ Brechas: {', '.join(fal)}")
        elif not st.session_state.perfil_actual:
            st.warning("Genere un perfil en Pestaña 2.")

# TAB 4: CARRERA
with tabs[3]:
    st.header("Plan de Desarrollo")
    if st.session_state.cargo_actual:
        st.markdown(f"Plan sugerido para **{st.session_state.cargo_actual}** en **{st.session_state.rubro_actual}**")
        c1, c2, c3 = st.columns(3)
        c1.markdown("#### Corto Plazo"); c1.write("- Inducción\n- Certificación técnica")
        c2.markdown("#### Mediano Plazo"); c2.write("- Liderazgo proyectos\n- Especialización")
        c3.markdown("#### Largo Plazo"); c3.write("- Jefatura\n- Estrategia")
    else: st.warning("Defina cargo en Pestaña 2")

# TAB 5: CONTRATOS
with tabs[4]:
    st.header("Generador Legal")
    
    if st.session_state.calculo_actual:
        c1, c2 = st.columns(2)
        fini = c1.date_input("Inicio Contrato", datetime.now())
        tcon = c2.selectbox("Tipo", ["Indefinido", "Plazo Fijo", "Obra Faena"])
        
        # Botón directo (Usa datos del Sidebar)
        if st.session_state.empresa['rut']:
            cond = {"cargo": st.session_state.cargo_actual, "tipo": tcon, "inicio": fini, "funciones": "Las propias del cargo"}
            if st.button("GENERAR CONTRATO (.DOCX)"):
                bio = generar_contrato_word(st.session_state.calculo_actual, st.session_state.empresa, st.session_state.trabajador, cond)
                st.download_button("⬇️ Descargar DOCX", bio.getvalue(), "contrato.docx")
        else:
            st.error("⚠️ Falta RUT Empresa en la barra lateral.")
    else: st.info("Calcule sueldo en Pestaña 1.")

# TAB 6: INDICADORES
with tabs[5]:
    st.header("Indicadores Previred (Nov 2025)")
    c1, c2 = st.columns(2)
    c1.subheader("Tasas AFP"); c1.table(pd.DataFrame({"AFP": ["Capital", "Habitat", "Modelo", "Uno"], "Tasa": ["11.44%", "11.27%", "10.58%", "10.46%"]}))
    c2.subheader("Asignación"); c2.table(pd.DataFrame({"Tramo": ["A", "B", "C"], "Monto": ["$22.007", "$13.505", "$4.267"]}))
