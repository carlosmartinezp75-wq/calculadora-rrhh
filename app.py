import streamlit as st
import pandas as pd
import requests
import base64
import os
import io
import random
from datetime import datetime, date
import plotly.graph_objects as go
import plotly.express as px

# --- 0. VALIDACIÓN LIBRERÍAS ---
try:
    import pdfplumber
    from fpdf import FPDF
    from docx import Document
    from docx.shared import Pt, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    LIBRARIES_OK = True
except ImportError:
    LIBRARIES_OK = False

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="HR Suite Ultimate V28", page_icon="💎", layout="wide")

# Inicialización de Estado
if 'empresa' not in st.session_state:
    st.session_state.empresa = {
        "nombre": "", "rut": "", "direccion": "", 
        "rep_nombre": "", "rep_rut": "", "ciudad": "Santiago", "giro": "Servicios Generales"
    }
if 'calculo_actual' not in st.session_state: st.session_state.calculo_actual = None
if 'cargo_actual' not in st.session_state: st.session_state.cargo_actual = ""
if 'rubro_actual' not in st.session_state: st.session_state.rubro_actual = ""
if 'brechas_detectadas' not in st.session_state: st.session_state.brechas_detectadas = []

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
        css_fondo = """[data-testid="stAppViewContainer"] {background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);}"""

    st.markdown(f"""
        <style>
        {css_fondo}
        .block-container {{background-color: rgba(255, 255, 255, 0.98); padding: 2rem; border-radius: 15px; box-shadow: 0 10px 40px rgba(0,0,0,0.1);}}
        h1, h2, h3 {{color: #004a99 !important; font-family: 'Segoe UI', sans-serif; font-weight: 800;}}
        .stButton>button {{background-color: #004a99 !important; color: white !important; font-weight: bold; border-radius: 8px; width: 100%; height: 3rem;}}
        .stButton>button:hover {{background-color: #003366 !important;}}
        .miles-feedback {{font-size: 0.8rem; color: #28a745; font-weight: bold; margin-top: -10px;}}
        
        /* Estilo Liquidación HTML */
        .liq-box {{border: 1px solid #ccc; padding: 20px; font-family: 'Courier New'; background: #fff;}}
        .liq-title {{text-align: center; font-weight: bold; border-bottom: 2px solid #000; margin-bottom: 10px;}}
        .liq-item {{display: flex; justify-content: space-between; border-bottom: 1px dashed #ddd; padding: 3px 0;}}
        .liq-total {{background: #e3f2fd; padding: 10px; font-weight: bold; font-size: 1.2em; border: 1px solid #004a99; margin-top: 10px;}}
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

# --- 4. GENERADORES DE DOCUMENTOS ---

# A. GENERAR PDF LIQUIDACIÓN (NUEVO)
def generar_pdf_liquidacion(res, nombre="Trabajador", cargo="No Definido"):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, "LIQUIDACION DE SUELDO (SIMULACION)", 0, 1, 'C')
    pdf.ln(5)
    
    pdf.set_font("Arial", '', 10)
    pdf.cell(0, 6, f"Nombre: {nombre}", 0, 1)
    pdf.cell(0, 6, f"Cargo: {cargo}", 0, 1)
    pdf.cell(0, 6, f"Fecha: {datetime.now().strftime('%d/%m/%Y')}", 0, 1)
    
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(95, 8, "HABERES", 1, 0, 'C')
    pdf.cell(95, 8, "DESCUENTOS", 1, 1, 'C')
    
    pdf.set_font("Arial", '', 9)
    # Fila 1
    pdf.cell(60, 6, "Sueldo Base", 'L', 0)
    pdf.cell(35, 6, fmt(res['Sueldo Base']), 'R', 0)
    pdf.cell(60, 6, "AFP", 'L', 0)
    pdf.cell(35, 6, fmt(res['AFP']), 'R', 1)
    
    # Fila 2
    pdf.cell(60, 6, "Gratificacion Legal", 'L', 0)
    pdf.cell(35, 6, fmt(res['Gratificación']), 'R', 0)
    pdf.cell(60, 6, "Salud", 'L', 0)
    pdf.cell(35, 6, fmt(res['Salud']), 'R', 1)
    
    # Fila 3
    pdf.cell(60, 6, "Colacion/Movil.", 'L', 0)
    pdf.cell(35, 6, fmt(res['No Imponibles']), 'R', 0)
    pdf.cell(60, 6, "Seguro Cesantia", 'L', 0)
    pdf.cell(35, 6, fmt(res['AFC']), 'R', 1)
    
    # Fila 4
    pdf.cell(60, 6, "", 'L', 0)
    pdf.cell(35, 6, "", 'R', 0)
    pdf.cell(60, 6, "Impuesto Unico", 'L', 0)
    pdf.cell(35, 6, fmt(res['Impuesto']), 'R', 1)
    
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(130, 10, "TOTAL LIQUIDO A PAGAR:", 1, 0, 'R')
    pdf.cell(60, 10, fmt(res['LÍQUIDO']), 1, 1, 'C')
    
    return pdf.output(dest='S').encode('latin-1')

# B. GENERAR CONTRATO WORD (CORREGIDO GIRO Y FECHA)
def generar_contrato_word(fin, form):
    doc = Document()
    style = doc.styles['Normal']
    style.font.name = 'Arial'
    style.font.size = Pt(11)
    
    t = doc.add_heading('CONTRATO DE TRABAJO', 0)
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.add_paragraph("")
    
    fecha_hoy = datetime.now().strftime("%d de %B de %Y")
    giro_empresa = form.get('giro', 'Servicios Profesionales') # Fallback para evitar KeyError
    
    intro = f"""En {form['ciudad']}, a {fecha_hoy}, entre "{form['nombre'].upper()}", RUT {form['rut']}, giro {giro_empresa}, representada por {form['rep_nombre'].upper()}, RUT {form['rep_rut']}, ambos domiciliados en {form['direccion']}, en adelante "EMPLEADOR"; y {form['trab_nombre'].upper()}, RUT {form['trab_rut']}, nacionalidad {form['trab_nacionalidad']}, nacido el {str(form['trab_nacimiento'])}, domiciliado en {form['trab_dir']}, en adelante "TRABAJADOR", se conviene:"""
    
    p = doc.add_paragraph(intro)
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    
    clausulas = [
        ("PRIMERO:", f"El Trabajador se desempeñará como {form['cargo'].upper()}, ejecutando funciones de {form['funciones']}."),
        ("SEGUNDO:", f"Sueldo Base: {fmt(fin['Sueldo Base'])}. Gratificación: {fmt(fin['Gratificación'])} (Tope 4.75 IMM). Asignaciones: {fmt(fin['No Imponibles'])}."),
        ("TERCERO:", "Jornada ordinaria de 44 horas semanales, distribuidas de lunes a viernes."),
        ("CUARTO:", f"Contrato {form['tipo_contrato']} con inicio el {str(form['fecha_inicio'])}."),
        ("QUINTO:", "Se prohíbe la divulgación de información confidencial de la empresa."),
        ("SEXTO:", "La propiedad intelectual de lo desarrollado pertenece al Empleador.")
    ]
    
    for tit, txt in clausulas:
        p = doc.add_paragraph(); run = p.add_run(tit); run.bold = True; p.add_run(f" {txt}")
    
    bio = io.BytesIO()
    doc.save(bio)
    return bio

# --- 5. MOTORES INTELIGENTES ---

def generar_perfil_robusto(cargo, rubro):
    if not cargo: return None
    # Base de datos simulada de competencias por rubro
    skills_map = {
        "Tecnología": ["Python/SQL", "Cloud Computing", "Agile/Scrum", "DevOps"],
        "Minería": ["Norma ISO 9001", "Seguridad Sernageomin", "Mantenimiento Preventivo", "Gestión de Turnos"],
        "Retail": ["Visual Merchandising", "Control de Inventario", "Atención al Cliente", "KPIs de Venta"],
        "Salud": ["Protocolos Minsal", "Atención Clínica", "Gestión de Pacientes", "Bioseguridad"]
    }
    hard_skills = skills_map.get(rubro, ["Gestión de Proyectos", "Excel Avanzado", "ERP", "Inglés Técnico"])
    
    return {
        "titulo": cargo.title(),
        "mision": f"Garantizar la operatividad y eficiencia del área de {cargo} en el sector {rubro}, alineado con los objetivos estratégicos.",
        "funciones": [
            "Planificación estratégica y control presupuestario.",
            "Liderazgo y desarrollo de equipos de alto rendimiento.",
            "Optimización continua de procesos operativos.",
            "Reportabilidad directa a Gerencia."
        ],
        "requisitos_duros": hard_skills,
        "competencias": ["Liderazgo Situacional", "Comunicación Efectiva", "Resolución de Problemas", "Adaptabilidad"],
        "kpis": ["Cumplimiento Presupuestario", "Satisfacción Cliente Interno", "Tasa de Error/Falla"]
    }

def motor_analisis(texto_cv, cargo, rubro, perfil):
    # Análisis de Coincidencias
    texto_lower = texto_cv.lower()
    
    # Skills del perfil
    target_skills = [s.lower() for s in perfil['requisitos_duros'] + perfil['competencias']]
    
    encontradas = []
    brechas = []
    
    for skill in target_skills:
        # Búsqueda laxa (palabras clave dentro de la skill)
        palabras = skill.split()
        match = False
        for p in palabras:
            if len(p) > 3 and p in texto_lower:
                match = True
                break
        
        if match: encontradas.append(skill.title())
        else: brechas.append(skill.title())
    
    score = int((len(encontradas) / len(target_skills)) * 100)
    score = min(99, max(10, score + 15)) # Ajuste base
    
    st.session_state.brechas_detectadas = brechas # Guardar para Plan Carrera
    
    return score, encontradas, brechas

def leer_pdf(archivo):
    if not LIBRARIES_OK: return None
    try:
        text = ""
        with pdfplumber.open(archivo) as pdf:
            for p in pdf.pages: text += (p.extract_text() or "")
        return text
    except: return None

# --- 6. CÁLCULO FINANCIERO ---
def calcular_reverso(liquido, col, mov, contrato, afp_n, salud_t, plan, uf, utm, s_min, t_imp, t_afc):
    no_imp = col + mov
    liq_meta = liquido - no_imp
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
        
        b_prev = min(tot_imp, t_imp*uf)
        m_afp = int(b_prev * tasa_afp)
        m_sal = int(b_prev*0.07) if salud_t == "Fonasa (7%)" else max(int(plan*uf), int(b_prev*0.07))
        
        base_trib = max(0, tot_imp - m_afp - int(b_prev*0.07) - int(min(tot_imp, t_afc*uf)*tasa_afc_trab))
        imp = 0
        if base_trib > 13.5*utm: imp = int(base_trib*0.04) 
        
        liq_calc = tot_imp - m_afp - m_sal - int(min(tot_imp, t_afc*uf)*tasa_afc_trab) - imp
        if abs(liq_calc - liq_meta) < 500:
            aportes = int(b_prev*(0.0149+0.0093)) + int(min(tot_imp, t_afc*uf)*tasa_afc_emp)
            return {
                "Sueldo Base": int(base), "Gratificación": int(grat), "Total Imponible": int(tot_imp),
                "No Imponibles": int(no_imp), "LÍQUIDO": int(liq_calc+no_imp), 
                "AFP": m_afp, "Salud": m_sal, "AFC": int(min(tot_imp, t_afc*uf)*tasa_afc_trab), "Impuesto": imp,
                "Aportes Empresa": aportes, "COSTO TOTAL": int(tot_imp+no_imp+aportes)
            }
            break
        elif liq_calc < liq_meta: min_b = base
        else: max_b = base
    return None

# --- 7. INTERFAZ ---

with st.sidebar:
    st.image("https://www.previred.com/wp-content/uploads/2021/01/logo-previred.png", width=120)
    
    with st.expander("🏢 Datos Empresa (Obligatorio)", expanded=True):
        st.session_state.empresa['nombre'] = st.text_input("Razón Social", st.session_state.empresa['nombre'])
        st.session_state.empresa['rut'] = st.text_input("RUT Empresa", st.session_state.empresa['rut'])
        st.session_state.empresa['giro'] = st.text_input("Giro", st.session_state.empresa['giro'])
        st.session_state.empresa['direccion'] = st.text_input("Dirección", st.session_state.empresa['direccion'])
        st.session_state.empresa['rep_nombre'] = st.text_input("Rep. Legal", st.session_state.empresa['rep_nombre'])
        st.session_state.empresa['rep_rut'] = st.text_input("RUT Rep.", st.session_state.empresa['rep_rut'])
        st.session_state.empresa['ciudad'] = st.text_input("Ciudad", st.session_state.empresa['ciudad'])
        if st.button("💾 Guardar Datos"): st.success("Guardado")

    st.divider()
    uf_v, utm_v = obtener_indicadores()
    st.metric("UF", fmt(uf_v).replace("$",""))
    st.metric("UTM", fmt(utm_v))

st.title("HR Suite Enterprise V28")
st.markdown("**Sistema Integral de Gestión de Personas**")

tabs = st.tabs(["💰 Calculadora", "📋 Perfil Cargo", "🧠 Análisis CV", "🚀 Carrera", "📝 Contratos", "📊 Indicadores"])

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

    if st.button("CALCULAR NÓMINA"):
        res = calcular_reverso(liq, col, mov, con, afp, sal, plan, uf_v, utm_v, 529000, 87.8, 131.9)
        if res:
            st.session_state.calculo_actual = res
            k1, k2, k3 = st.columns(3)
            k1.metric("Sueldo Base", fmt(res['Sueldo Base']))
            k2.metric("Líquido", fmt(res['LÍQUIDO']), delta="Objetivo")
            k3.metric("Costo Empresa", fmt(res['COSTO TOTAL']), delta="Total", delta_color="inverse")
            
            st.markdown(f"""
            <div class="liq-box">
                <div class="liq-title">LIQUIDACIÓN DE SUELDO</div>
                <div class="liq-item"><span>Sueldo Base:</span><span>{fmt(res['Sueldo Base'])}</span></div>
                <div class="liq-item"><span>Gratificación:</span><span>{fmt(res['Gratificación'])}</span></div>
                <div class="liq-item" style="font-weight:bold; background:#f0f0f0;"><span>TOTAL IMPONIBLE:</span><span>{fmt(res['Total Imponible'])}</span></div>
                <div class="liq-item"><span>No Imponibles:</span><span>{fmt(res['No Imponibles'])}</span></div>
                <br>
                <div class="liq-item"><span>AFP ({afp}):</span><span style="color:red">-{fmt(res['AFP'])}</span></div>
                <div class="liq-item"><span>Salud ({sal}):</span><span style="color:red">-{fmt(res['Salud'])}</span></div>
                <div class="liq-item"><span>Impuesto Único:</span><span style="color:red">-{fmt(res['Impuesto'])}</span></div>
                <div class="liq-total">LÍQUIDO A PAGAR: {fmt(res['LÍQUIDO'])}</div>
            </div>
            """, unsafe_allow_html=True)
            
            # BOTÓN PDF LIQUIDACIÓN
            if LIBRARIES_OK:
                pdf_bytes = generar_pdf_liquidacion(res)
                st.download_button("⬇️ Descargar Liquidación (PDF)", pdf_bytes, "liquidacion.pdf", "application/pdf")
        else: st.error("Error matemático.")

# TAB 2: PERFIL
with tabs[1]:
    c1, c2 = st.columns(2)
    cargo = c1.text_input("Cargo", placeholder="Ej: Analista de Finanzas")
    rubro = c2.selectbox("Rubro", ["Tecnología", "Minería", "Retail", "Banca", "Salud", "Servicios"])
    
    if cargo:
        st.session_state.cargo_actual = cargo
        st.session_state.rubro_actual = rubro
        perf = generar_perfil_robusto(cargo, rubro)
        st.session_state.perfil_generado = perf
        
        st.info(f"**Misión:** {perf['mision']}")
        c1, c2 = st.columns(2)
        c1.success("**Requisitos Técnicos:**\n" + "\n".join([f"- {x}" for x in perf['requisitos_duros']]))
        c2.warning("**Competencias:**\n" + "\n".join([f"- {x}" for x in perf['competencias']]))
        st.markdown("**KPIs:** " + ", ".join(perf['kpis']))

# TAB 3: ANÁLISIS CV
with tabs[2]:
    st.header("Análisis de Brechas")
    if not LIBRARIES_OK: st.warning("Faltan librerías PDF.")
    else:
        uploaded = st.file_uploader("Subir CV (PDF)", type="pdf")
        if uploaded and st.session_state.perfil_generado:
            if st.button("ANALIZAR"):
                txt = leer_pdf(uploaded)
                if txt:
                    score, enc, fal = motor_analisis(txt, cargo, rubro, st.session_state.perfil_generado)
                    c1, c2 = st.columns([1,2])
                    c1.metric("Match Score", f"{score}%")
                    c1.plotly_chart(go.Figure(go.Indicator(mode="gauge+number", value=score, gauge={'axis':{'range':[0,100]}, 'bar':{'color':"#004a99"}})), use_container_width=True)
                    c2.success(f"✅ Fortalezas: {', '.join(enc)}")
                    c2.error(f"⚠️ Brechas Críticas: {', '.join(fal)}")
        elif not st.session_state.perfil_generado:
            st.warning("Genere un perfil en la Pestaña 2 primero.")

# TAB 4: CARRERA
with tabs[3]:
    st.header("Plan de Cierre de Brechas")
    if st.session_state.brechas_detectadas:
        st.write("Basado en el análisis del CV, se sugiere:")
        for brecha in st.session_state.brechas_detectadas:
            st.warning(f"🔸 **Brecha:** {brecha} -> **Acción:** Capacitación técnica o certificación en 3 meses.")
    else:
        st.info("Analice un CV en Pestaña 3 para ver brechas específicas.")

# TAB 5: CONTRATOS (CORREGIDO)
with tabs[4]:
    st.header("Generador Legal")
    if st.session_state.calculo_actual:
        with st.form("form_legal"):
            st.subheader("Datos Trabajador")
            c1, c2 = st.columns(2)
            tn = c1.text_input("Nombre Completo")
            tr = c2.text_input("RUT")
            tnac = c1.text_input("Nacionalidad", "Chilena")
            tdir = c2.text_input("Domicilio")
            # FECHA CORREGIDA: Sin límite inferior ridículo y hasta hoy
            tfec = st.date_input("Fecha Nacimiento", min_value=date(1940,1,1), max_value=datetime.now())
            
            st.subheader("Condiciones")
            cc1, cc2 = st.columns(2)
            fini = cc1.date_input("Inicio Contrato", value=datetime.now())
            tcon = cc2.selectbox("Tipo", ["Indefinido", "Plazo Fijo", "Obra Faena"])
            func = st.text_area("Funciones Específicas", "Las propias del cargo.")
            
            if st.form_submit_button("GENERAR CONTRATO (.DOCX)"):
                # Se mezcla datos de empresa (sidebar) con datos trabajador (form)
                datos_form = {**st.session_state.empresa, "trab_nombre": tn, "trab_rut": tr, "trab_nacionalidad": tnac, "trab_nacimiento": tfec, "trab_dir": tdir, "cargo": st.session_state.cargo_actual, "funciones": func, "fecha_inicio": fini, "tipo_contrato": tcon, "colacion": st.session_state.calculo_actual['No Imponibles']//2, "movilizacion": st.session_state.calculo_actual['No Imponibles']//2}
                
                bio = generar_contrato_word(st.session_state.calculo_actual, datos_form)
                st.download_button("⬇️ Descargar DOCX", bio.getvalue(), f"Contrato_{tn}.docx")
    else: st.warning("Calcule sueldo en Pestaña 1 primero.")

# TAB 6: INDICADORES
with tabs[5]:
    st.header("Indicadores Oficiales")
    # Tablas estáticas seguras
    st.subheader("AFP")
    st.table(pd.DataFrame({"AFP": ["Capital", "Cuprum", "Habitat", "PlanVital", "Provida", "Modelo", "Uno"], "Tasa": ["11,44%", "11,44%", "11,27%", "11,16%", "11,45%", "10,58%", "10,46%"]}))
