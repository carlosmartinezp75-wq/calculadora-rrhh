import streamlit as st
import pandas as pd
import requests
import base64
import os
import io
import plotly.express as px
import plotly.graph_objects as go
import random
from datetime import datetime, timedelta

# --- 0. VALIDACIÓN DE LIBRERÍAS CRÍTICAS ---
try:
    import pdfplumber
    from docx import Document
    from docx.shared import Pt, Inches, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    LIBRARIES_OK = True
except ImportError:
    LIBRARIES_OK = False

# --- 1. CONFIGURACIÓN DEL SISTEMA ---
st.set_page_config(
    page_title="HR Suite Enterprise V25",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inicialización de Estado Persistente
if 'empresa' not in st.session_state:
    st.session_state.empresa = {
        "nombre": "", "rut": "", "direccion": "", 
        "rep_nombre": "", "rep_rut": "", "ciudad": "Santiago",
        "giro": ""
    }
if 'calculo_actual' not in st.session_state: st.session_state.calculo_actual = None
if 'cargo_actual' not in st.session_state: st.session_state.cargo_actual = ""
if 'rubro_actual' not in st.session_state: st.session_state.rubro_actual = ""

# --- 2. SISTEMA DE DISEÑO (CSS AVANZADO) ---
def cargar_estilos():
    nombres = ['fondo.png', 'fondo.jpg', 'fondo.jpeg', 'fondo_marca.png']
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
        
        /* Contenedor Principal Estilo Tarjeta Glassmorphism */
        .block-container {{
            background-color: rgba(255, 255, 255, 0.96);
            padding: 3rem;
            border-radius: 16px;
            box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.15);
            border: 1px solid rgba(255, 255, 255, 0.18);
        }}
        
        /* Tipografía */
        h1, h2, h3, h4 {{color: #004a99 !important; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; font-weight: 800;}}
        p, label, li, span {{color: #003366 !important; font-weight: 500;}}
        
        /* Inputs Personalizados */
        .stNumberInput input, .stTextInput input, .stSelectbox div[data-baseweb="select"] {{
            background-color: #f8f9fa;
            border: 1px solid #ced4da;
            color: #004a99;
            font-weight: bold;
            border-radius: 8px;
        }}
        
        /* Botones de Alta Interacción */
        .stButton>button {{
            background: linear-gradient(90deg, #004a99 0%, #003366 100%);
            color: white !important;
            font-weight: bold;
            border-radius: 8px;
            width: 100%;
            height: 3.5rem;
            border: none;
            box-shadow: 0 4px 15px rgba(0, 74, 153, 0.3);
            transition: all 0.3s ease;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        .stButton>button:hover {{
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(0, 74, 153, 0.4);
        }}
        
        /* Liquidación Visual */
        .liq-container {{
            border: 1px solid #e0e0e0;
            padding: 25px;
            background: #ffffff;
            font-family: 'Courier New', monospace;
            margin-top: 20px;
            box-shadow: inset 0 0 20px #f0f0f0;
        }}
        .liq-header {{text-align: center; font-weight: bold; border-bottom: 2px solid #000; margin-bottom: 15px; padding-bottom: 10px;}}
        .liq-row {{display: flex; justify-content: space-between; border-bottom: 1px dashed #ccc; padding: 6px 0;}}
        .liq-total {{
            font-weight: bold; font-size: 1.3em; 
            background-color: #e3f2fd; 
            color: #0d47a1;
            padding: 15px; 
            margin-top: 15px; 
            border: 2px solid #0d47a1;
            border-radius: 5px;
        }}
        
        /* Feedback Miles */
        .miles-feedback {{font-size: 0.85rem; color: #2e7d32; font-weight: bold; margin-top: -10px; margin-bottom: 10px;}}
        
        #MainMenu, footer {{visibility: hidden;}}
        </style>
        """, unsafe_allow_html=True)

cargar_estilos()

# --- 3. FUNCIONES UTILITARIAS Y CONEXIÓN ---
def fmt(valor): return "$0" if pd.isna(valor) else "${:,.0f}".format(valor).replace(",", ".")
def mostrar_miles(valor): 
    if valor > 0: st.markdown(f'<p class="miles-feedback">✅ Ingresaste: {fmt(valor)}</p>', unsafe_allow_html=True)

def obtener_indicadores():
    # Datos default robustos en caso de falla API
    def_uf, def_utm = 39643.59, 69542.0
    try:
        r = requests.get('https://mindicador.cl/api', timeout=2)
        d = r.json()
        return float(d['uf']['valor']), float(d['utm']['valor'])
    except: return def_uf, def_utm

# --- 4. MOTORES DE INTELIGENCIA DE NEGOCIO ---

def generar_plan_carrera_detallado(cargo, rubro):
    """
    Genera un plan de carrera estructurado y específico por industria.
    """
    rubro_txt = f"en la industria {rubro}" if rubro else ""
    
    # Base de conocimientos por rubro
    skills_rubro = {
        "Minería": ["Normativa Sernageomin", "Seguridad Industrial Avanzada", "Gestión de Turnos"],
        "Tecnología": ["Certificaciones Cloud (AWS/Azure)", "Metodologías Ágiles (Scrum Master)", "Arquitectura de Datos"],
        "Banca": ["Compliance Financiero", "Riesgo Operacional", "Transformación Digital"],
        "Salud": ["Gestión Clínica", "Acreditación de Calidad", "Humanización del Trato"],
        "Retail": ["E-commerce Strategy", "Supply Chain Management", "Customer Experience (CX)"]
    }
    
    skills = skills_rubro.get(rubro, ["Gestión de Proyectos", "Liderazgo de Equipos", "Negociación"])
    
    return {
        "corto": [
            f"Onboarding cultural y técnico {rubro_txt}.",
            f"Dominio operativo de herramientas internas y {skills[0]}.",
            "Cumplimiento de metas individuales al 100%."
        ],
        "mediano": [
            "Liderazgo de células de trabajo o proyectos transversales.",
            f"Profundización técnica en {skills[1]}.",
            "Mentoring a nuevos ingresos y participación en reclutamiento."
        ],
        "largo": [
            "Posicionamiento como referente técnico/comercial en la compañía.",
            f"Liderazgo estratégico en {skills[2]}.",
            "Sucesión planificada para cargos de Jefatura o Gerencia."
        ]
    }

def generar_perfil_maestro(cargo, rubro):
    if not cargo: return None
    cargo = cargo.title()
    
    perfil = {
        "titulo": cargo,
        "mision": f"Planificar, dirigir y controlar las actividades inherentes a {cargo} dentro del sector {rubro}, alineando los recursos disponibles con la estrategia corporativa para maximizar la rentabilidad y sostenibilidad.",
        "funciones": [
            "Desarrollar y ejecutar el plan operativo anual del área.",
            "Gestionar el presupuesto (OPEX/CAPEX) asegurando eficiencia de costos.",
            "Liderar equipos de alto desempeño, fomentando un clima laboral positivo.",
            "Reportar KPIs críticos a la Gerencia y proponer mejoras continuas.",
            "Asegurar el cumplimiento estricto de la normativa legal y políticas internas."
        ],
        "requisitos_duros": [
            "Título Profesional Universitario (Ingeniería, Administración o carrera afín).",
            f"Experiencia mínima de 3 a 5 años en roles similares en {rubro}.",
            "Manejo avanzado de herramientas Office y ERP (SAP, Oracle, Softland).",
            "Conocimiento específico en normativas de la industria."
        ],
        "competencias_blandas": [
            "Liderazgo Transformacional", "Pensamiento Estratégico", "Resolución de Conflictos", "Adaptabilidad al Cambio"
        ],
        "condiciones": [
            "Jornada: Art. 22 o 44 Horas (Según contrato).",
            "Modalidad: Presencial / Híbrida.",
            "Beneficios: Seguro Complementario, Bonos por Desempeño."
        ]
    }
    return perfil

def motor_analisis_cv_avanzado(texto_cv, cargo, rubro):
    # Diccionario de Competencias Expandido
    keywords_base = ["liderazgo", "comunicación", "equipo", "proactivo", "responsable", "gestión"]
    keywords_rubro = {
        "Minería": ["seguridad", "prevención", "calidad", "iso", "medio ambiente"],
        "Tecnología": ["python", "java", "sql", "cloud", "agile", "devops"],
        "Finanzas": ["presupuesto", "auditoría", "ifrs", "tributaria", "flujo"],
        "Comercial": ["ventas", "crm", "negociación", "cliente", "marketing"]
    }
    
    target = keywords_base + keywords_rubro.get(rubro, ["proyectos"])
    texto_lower = texto_cv.lower()
    
    encontradas = list(set([k.title() for k in target if k in texto_lower]))
    faltantes = list(set([k.title() for k in target if k not in texto_lower]))
    
    # Score ponderado
    score = int((len(encontradas) / len(target)) * 100) + 20 # Base
    score = min(99, max(10, score))
    
    nivel = "Junior"
    if score > 50: nivel = "Semi-Senior"
    if score > 80: nivel = "Senior / Experto"
    
    return score, encontradas, faltantes, nivel

def leer_pdf(archivo):
    if not LIBRARIES_OK: return None
    try:
        text = ""
        with pdfplumber.open(archivo) as pdf:
            for p in pdf.pages: text += (p.extract_text() or "") + "\n"
        return text
    except: return None

# --- 5. MOTOR DE CÁLCULO FINANCIERO ---
def calcular_nomina_reversa(liquido, col, mov, contrato, afp_n, salud_t, plan, uf, utm, s_min, t_imp, t_afc):
    no_imp = col + mov
    liq_meta = liquido - no_imp
    if liq_meta < s_min * 0.4: return None
    
    TOPE_GRAT = (4.75 * s_min) / 12
    tasa_afp = 0.0 if (contrato == "Sueldo Empresarial" or afp_n == "SIN AFP") else (0.10 + ({"Capital":1.44,"Cuprum":1.44,"Habitat":1.27,"PlanVital":1.16,"Provida":1.45,"Modelo":0.58,"Uno":0.49}.get(afp_n,1.44)/100))
    tasa_afc_emp = 0.024
    tasa_afc_trab = 0.006 if contrato == "Indefinido" and contrato != "Sueldo Empresarial" else 0.0
    if contrato == "Plazo Fijo": tasa_afc_emp = 0.03
    
    min_b, max_b = 100000, liq_meta * 2.5
    
    for _ in range(200): # Mayor precisión
        base = (min_b + max_b) / 2
        grat = min(base * 0.25, TOPE_GRAT)
        if contrato == "Sueldo Empresarial": grat = 0
        
        tot_imp = base + grat
        b_prev = min(tot_imp, t_imp*uf)
        b_afc = min(tot_imp, t_afc*uf)
        
        m_afp = int(b_prev * tasa_afp)
        m_sal = int(b_prev*0.07) if salud_t == "Fonasa (7%)" else max(int(plan*uf), int(b_prev*0.07))
        m_afc_t = int(b_afc * tasa_afc_trab)
        
        # Impuesto Único (Tabla Nov 2025 Real)
        base_trib = max(0, tot_imp - m_afp - int(b_prev*0.07) - m_afc_t)
        imp = 0
        tabla_imp = [(13.5,0,0),(30,0.04,0.54),(50,0.08,1.74),(70,0.135,4.49),(90,0.23,11.14),(120,0.304,17.80),(310,0.35,23.32),(99999,0.40,38.82)]
        
        for l, f, r in tabla_imp:
            if (base_trib/utm) <= l:
                imp = int((base_trib * f) - (r * utm))
                break
        imp = max(0, imp)
        
        liq_calc = tot_imp - m_afp - m_sal - m_afc_t - imp
        
        if abs(liq_calc - liq_meta) < 100:
            ap_sis = int(b_prev*0.0149)
            ap_mut = int(b_prev*0.0093)
            ap_afc = int(b_afc*tasa_afc_emp)
            
            return {
                "Sueldo Base": int(base), "Gratificación": int(grat), "Total Imponible": int(tot_imp),
                "No Imponibles": int(no_imp), "LÍQUIDO": int(liq_calc+no_imp), 
                "AFP": m_afp, "Salud": m_sal, "AFC": m_afc_t, "Impuesto": imp,
                "Aportes Empresa": ap_sis + ap_mut + ap_afc, 
                "COSTO TOTAL": int(tot_imp+no_imp + ap_sis + ap_mut + ap_afc)
            }
            break
        elif liq_calc < liq_meta: min_b = base
        else: max_b = base
    return None

# --- 6. GENERADOR DE CONTRATOS LEGAL (ART 10) ---
def generar_contrato_word(fin, form):
    doc = Document()
    style = doc.styles['Normal']
    style.font.name = 'Arial'
    style.font.size = Pt(11)
    
    t = doc.add_heading('CONTRATO DE TRABAJO', 0)
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.add_paragraph(f"FECHA: {datetime.now().strftime('%d/%m/%Y')}").alignment = WD_ALIGN_PARAGRAPH.RIGHT
    
    # Texto Legal Robusto
    intro = f"""En {form['ciudad']}, a {datetime.now().strftime("%d de %B de %Y")}, entre la empresa "{form['empresa_nombre'].upper()}", RUT {form['empresa_rut']}, giro {form.get('empresa_giro','Servicios')}, representada legalmente por don/ña {form['rep_nombre'].upper()}, RUT {form['rep_rut']}, ambos domiciliados en {form['empresa_dir']}, en adelante el "EMPLEADOR"; y don/ña {form['trab_nombre'].upper()}, RUT {form['trab_rut']}, de nacionalidad {form['trab_nacionalidad']}, nacido el {str(form['trab_nacimiento'])}, domiciliado en {form['trab_dir']}, en adelante el "TRABAJADOR", se ha convenido el siguiente contrato de trabajo:"""
    p = doc.add_paragraph(intro)
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    
    clausulas = [
        ("PRIMERO (Naturaleza de los Servicios):", f"El Trabajador se compromete a prestar sus servicios personales como {form['cargo'].upper()}, desempeñando las funciones de {form['funciones']} y cualquier otra labor inherente a su cargo que le encomiende la Jefatura."),
        ("SEGUNDO (Lugar de Trabajo):", f"Los servicios se prestarán en las dependencias de la empresa ubicadas en {form['empresa_dir']}, sin perjuicio de los desplazamientos que requiera el cargo."),
        ("TERCERO (Remuneración):", f"El Empleador pagará al Trabajador una remuneración mensual compuesta por:\n"
                                    f"a) Sueldo Base: {fmt(fin['Sueldo Base'])}\n"
                                    f"b) Gratificación Legal: {fmt(fin['Gratificación'])} (Con tope legal de 4.75 IMM anual)\n"
                                    f"c) Asignación Colación: {fmt(form['colacion'])}\n"
                                    f"d) Asignación Movilización: {fmt(form['movilizacion'])}"),
        ("CUARTO (Jornada):", "El trabajador cumplirá una jornada ordinaria de 44 horas semanales, distribuida de lunes a viernes, o según lo dispuesto en el Artículo 22 del Código del Trabajo si correspondiere."),
        ("QUINTO (Confidencialidad):", "El Trabajador se obliga a mantener estricta reserva respecto de la información confidencial de la Empresa, clientes y proveedores, prohibiéndose su divulgación a terceros."),
        ("SEXTO (Propiedad Intelectual):", "Toda invención, mejora o creación desarrollada por el Trabajador en el desempeño de sus funciones será propiedad exclusiva del Empleador."),
        ("SÉPTIMO (Vigencia):", f"El presente contrato es de carácter {form['tipo_contrato']} y comenzará a regir a partir del {str(form['fecha_inicio'])}.")
    ]
    
    for tit, texto in clausulas:
        p = doc.add_paragraph()
        p.add_run(tit).bold = True
        p.add_run(f" {texto}")
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    
    doc.add_paragraph("\n\n\n")
    firma_table = doc.add_table(rows=1, cols=2)
    firma_table.alignment = WD_ALIGN_PARAGRAPH.CENTER
    c1 = firma_table.cell(0,0)
    c1.text = "___________________________\nFIRMA EMPLEADOR\n" + form['empresa_rut']
    c1.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    c2 = firma_table.cell(0,1)
    c2.text = "___________________________\nFIRMA TRABAJADOR\n" + form['trab_rut']
    c2.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    bio = io.BytesIO()
    doc.save(bio)
    return bio

# --- 7. INTERFAZ GRÁFICA PRINCIPAL ---

# SIDEBAR PERSISTENTE
with st.sidebar:
    st.image("https://www.previred.com/wp-content/uploads/2021/01/logo-previred.png", width=130)
    
    with st.expander("🏢 DATOS EMPRESA (Configurar)", expanded=True):
        st.caption("Estos datos se usarán automáticamente en los contratos.")
        st.session_state.empresa['nombre'] = st.text_input("Razón Social", st.session_state.empresa['nombre'])
        st.session_state.empresa['rut'] = st.text_input("RUT Empresa", st.session_state.empresa['rut'])
        st.session_state.empresa['giro'] = st.text_input("Giro Comercial", st.session_state.empresa.get('giro',''))
        st.session_state.empresa['direccion'] = st.text_input("Dirección", st.session_state.empresa['direccion'])
        st.session_state.empresa['ciudad'] = st.text_input("Ciudad Firma", st.session_state.empresa['ciudad'])
        st.session_state.empresa['rep_nombre'] = st.text_input("Rep. Legal", st.session_state.empresa['rep_nombre'])
        st.session_state.empresa['rep_rut'] = st.text_input("RUT Rep.", st.session_state.empresa['rep_rut'])
        
        if st.button("💾 Guardar Configuración"): st.success("Datos de empresa guardados.")

    st.divider()
    uf_v, utm_v = obtener_indicadores()
    st.metric("UF Hoy", fmt(uf_v).replace("$",""))
    st.metric("UTM Hoy", fmt(utm_v))
    
    st.markdown("---")
    st.subheader("Parámetros Legales")
    s_min = st.number_input("Sueldo Mínimo ($)", value=529000, step=1000)
    tope_grat = (4.75 * s_min) / 12
    st.caption(f"Tope Grat: {fmt(tope_grat)}")
    t_prev = st.number_input("Tope AFP (UF)", value=87.8)
    t_afc = st.number_input("Tope AFC (UF)", value=131.9)

st.title("HR Suite Enterprise V25")
st.markdown("**Plataforma Integral de Gestión de Personas y Contratos**")

# NAVEGACIÓN
tabs = st.tabs(["💰 Calculadora & Liquidación", "📋 Perfil de Cargo", "🧠 Análisis CV", "🚀 Carrera", "📝 Contratos", "📊 Indicadores"])

# --- TAB 1: CALCULADORA ---
with tabs[0]:
    c1, c2 = st.columns(2)
    with c1:
        liq = st.number_input("Sueldo Líquido Objetivo ($)", value=1000000, step=50000, format="%d")
        mostrar_miles(liq)
        col = st.number_input("Colación ($)", value=50000, format="%d")
        mov = st.number_input("Movilización ($)", value=50000, format="%d")
    with c2:
        con = st.selectbox("Contrato", ["Indefinido", "Plazo Fijo", "Sueldo Empresarial"])
        afp = st.selectbox("AFP", ["Capital", "Cuprum", "Habitat", "Modelo", "PlanVital", "Uno", "SIN AFP"])
        sal = st.selectbox("Salud", ["Fonasa (7%)", "Isapre (UF)"])
        plan = st.number_input("Plan UF", 0.0) if sal == "Isapre (UF)" else 0.0

    if st.button("CALCULAR SIMULACIÓN"):
        res = calcular_nomina_reversa(liq, col, mov, con, afp, sal, plan, uf_v, utm_v, s_min, t_prev, t_afc)
        if res:
            st.session_state.calculo_actual = res
            st.markdown("#### Resultados")
            k1, k2, k3 = st.columns(3)
            k1.metric("Sueldo Base", fmt(res['Sueldo Base']))
            k2.metric("Líquido", fmt(res['LÍQUIDO']), delta="Objetivo")
            k3.metric("Costo Empresa", fmt(res['COSTO TOTAL']), delta="Total", delta_color="inverse")
            
            # LIQUIDACIÓN VISUAL (HTML/CSS)
            st.markdown(f"""
            <div class="liq-container">
                <div class="liq-header">LIQUIDACIÓN DE SUELDO (Simulación)</div>
                <div class="liq-row"><span>Sueldo Base:</span><span>{fmt(res['Sueldo Base'])}</span></div>
                <div class="liq-row"><span>Gratificación Legal:</span><span>{fmt(res['Gratificación'])}</span></div>
                <div class="liq-row" style="background:#f9f9f9; font-weight:bold;"><span>TOTAL IMPONIBLE:</span><span>{fmt(res['Total Imponible'])}</span></div>
                <div class="liq-row"><span>Colación y Movilización:</span><span>{fmt(res['No Imponibles'])}</span></div>
                <div class="liq-row" style="background:#eef; font-weight:bold;"><span>TOTAL HABERES:</span><span>{fmt(res['Total Imponible']+res['No Imponibles'])}</span></div>
                <br>
                <div class="liq-row"><span>AFP ({afp}):</span><span style="color:#d32f2f;">-{fmt(res['AFP'])}</span></div>
                <div class="liq-row"><span>Salud ({sal}):</span><span style="color:#d32f2f;">-{fmt(res['Salud'])}</span></div>
                <div class="liq-row"><span>Seguro Cesantía:</span><span style="color:#d32f2f;">-{fmt(res['AFC'])}</span></div>
                <div class="liq-row"><span>Impuesto Único:</span><span style="color:#d32f2f;">-{fmt(res['Impuesto'])}</span></div>
                
                <div class="liq-total" style="display:flex; justify-content:space-between;">
                    <span>LÍQUIDO A PAGAR:</span><span>{fmt(res['LÍQUIDO'])}</span>
                </div>
                <div style="font-size:0.8em; text-align:right; margin-top:5px; color:#666;">
                    * Costo Empresa Real (Incluye Aportes): {fmt(res['COSTO TOTAL'])}
                </div>
            </div>
            """, unsafe_allow_html=True)
        else: st.error("No se pudo calcular. Revise si el líquido es muy bajo para el mínimo legal.")

# --- TAB 2: PERFIL ---
with tabs[1]:
    st.header("Generador de Perfiles")
    c1, c2 = st.columns(2)
    cargo = c1.text_input("Cargo", placeholder="Ej: Jefe de Proyectos")
    rubro = c2.selectbox("Rubro", ["Minería", "Tecnología", "Retail", "Banca", "Salud", "Construcción", "Agro", "Transporte", "Educación", "Servicios"])
    
    if cargo:
        st.session_state.cargo_actual = cargo
        st.session_state.rubro_actual = rubro
        perf = generar_perfil_maestro(cargo, rubro)
        
        st.info(f"**Misión:** {perf['mision']}")
        cc1, cc2 = st.columns(2)
        cc1.success("**Funciones:**\n" + "\n".join([f"- {x}" for x in perf['funciones']]))
        cc2.warning("**Requisitos:**\n" + "\n".join([f"- {x}" for x in perf['requisitos_duros']]))
        st.markdown("**Competencias:** " + ", ".join(perf['competencias']))

# --- TAB 3: ANÁLISIS CV ---
with tabs[2]:
    st.header("Análisis de CV (IA Engine)")
    if not LIBRARIES_OK: st.warning("⚠️ Instalar librerías PDF.")
    else:
        uploaded = st.file_uploader("Subir CV (PDF)", type="pdf")
        if uploaded and st.session_state.cargo_actual:
            if st.button("ANALIZAR CANDIDATO"):
                txt = leer_pdf(uploaded)
                if txt:
                    score, enc, fal, analisis, nivel = motor_analisis_robusto(txt, st.session_state.cargo_actual, st.session_state.rubro_actual)
                    
                    c1, c2 = st.columns([1, 2])
                    c1.metric("Match Score", f"{score}%")
                    c1.info(f"Nivel: **{nivel}**")
                    fig = go.Figure(go.Indicator(mode="gauge+number", value=score, gauge={'axis':{'range':[0,100]}, 'bar':{'color':"#004a99"}}))
                    c1.plotly_chart(fig, use_container_width=True)
                    
                    with c2:
                        st.markdown(analisis)
                        st.success(f"✅ **Fortalezas:** {', '.join(enc)}")
                        st.error(f"⚠️ **Brechas:** {', '.join(fal)}")

# --- TAB 4: CARRERA ---
with tabs[3]:
    st.header("Plan de Desarrollo")
    if st.session_state.cargo_actual:
        plan = generar_plan_carrera_detallado(st.session_state.cargo_actual, st.session_state.rubro_actual)
        c1, c2, c3 = st.columns(3)
        c1.markdown("#### 🔹 Corto Plazo"); c1.write("\n".join([f"- {x}" for x in plan['corto']]))
        c2.markdown("#### 🔸 Mediano Plazo"); c2.write("\n".join([f"- {x}" for x in plan['mediano']]))
        c3.markdown("#### 🏆 Largo Plazo"); c3.write("\n".join([f"- {x}" for x in plan['largo']]))
    else: st.info("Defina un cargo en la pestaña Perfil.")

# --- TAB 5: CONTRATOS ---
with tabs[4]:
    st.header("Generador Legal")
    if st.session_state.calculo_actual:
        if not st.session_state.empresa['rut']: st.warning("⚠️ Configure los Datos de Empresa en la barra lateral.")
        
        with st.form("form_legal"):
            st.markdown("#### Antecedentes del Trabajador")
            c1, c2 = st.columns(2)
            tn = c1.text_input("Nombre Completo")
            tr = c2.text_input("RUT")
            tnac = c1.text_input("Nacionalidad", "Chilena")
            tdir = c2.text_input("Domicilio")
            tfec = st.date_input("Fecha Nacimiento", value=datetime(1990,1,1))
            
            st.markdown("#### Condiciones")
            cc1, cc2 = st.columns(2)
            fini = cc1.date_input("Inicio Contrato", value=datetime.now())
            tcon = cc2.selectbox("Tipo", ["Indefinido", "Plazo Fijo", "Obra Faena"])
            
            if st.form_submit_button("GENERAR CONTRATO (.DOCX)"):
                datos_form = {
                    **st.session_state.empresa,
                    "trab_nombre": tn, "trab_rut": tr, "trab_nacionalidad": tnac,
                    "trab_nacimiento": tfec, "trab_dir": tdir,
                    "cargo": st.session_state.cargo_actual if st.session_state.cargo_actual else "Trabajador",
                    "funciones": "las propias del cargo y las encomendadas por la jefatura",
                    "fecha_inicio": fini, "tipo_contrato": tcon,
                    "colacion": st.session_state.calculo_actual['No Imponibles'] // 2, # Estimado
                    "movilizacion": st.session_state.calculo_actual['No Imponibles'] // 2
                }
                bio = generar_contrato_word(st.session_state.calculo_actual, datos_form)
                st.download_button("⬇️ Descargar Documento Legal", bio.getvalue(), f"Contrato_{tn}.docx")
    else: st.info("Primero calcule un sueldo en Pestaña 1.")

# --- TAB 6: INDICADORES ---
with tabs[5]:
    st.header("Indicadores Oficiales Previred (Nov 2025)")
    c1, c2 = st.columns(2)
    
    with c1:
        st.subheader("Tasas AFP")
        afp_df = pd.DataFrame({"AFP": ["Capital", "Cuprum", "Habitat", "PlanVital", "Provida", "Modelo", "Uno"], "Tasa": ["11,44%", "11,44%", "11,27%", "11,16%", "11,45%", "10,58%", "10,46%"]})
        st.table(afp_df)
    
    with c2:
        st.subheader("Asignación Familiar")
        asig_df = pd.DataFrame({"Tramo": ["A", "B", "C", "D"], "Renta Tope": ["$620.251", "$905.941", "$1.412.957", "Superior"], "Monto": ["$22.007", "$13.505", "$4.267", "$0"]})
        st.table(asig_df)
        
        st.markdown("---")
        st.subheader("Impuesto Único (Simulación)")
        imp_data = []
        tabla = [(13.5,0,0),(30,0.04,0.54),(50,0.08,1.74),(70,0.135,4.49),(90,0.23,11.14),(120,0.304,17.80),(310,0.35,23.32),(99999,0.40,38.82)]
        for l, f, r in tabla:
            imp_data.append([f"Hasta {l} UTM", f"{f*100:.2f}%", fmt(r*utm_v)])
        st.table(pd.DataFrame(imp_data, columns=["Tramo", "Factor", "Rebaja"]))
