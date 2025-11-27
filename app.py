import streamlit as st
import pandas as pd
import requests
import base64
import os
import io
import plotly.express as px
import plotly.graph_objects as go
import random
from datetime import datetime

# --- 0. VALIDACIÓN LIBRERÍAS ---
try:
    import pdfplumber
    from docx import Document
    from docx.shared import Pt, Inches
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    LIBRARIES_OK = True
except ImportError:
    LIBRARIES_OK = False

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="HR Suite Ultimate", page_icon="👔", layout="wide")

if 'calculo_actual' not in st.session_state: st.session_state.calculo_actual = None

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
        .block-container {{background-color: rgba(255, 255, 255, 0.98); padding: 3rem; border-radius: 15px; box-shadow: 0 10px 40px rgba(0,0,0,0.1);}}
        h1, h2, h3 {{color: #004a99 !important; font-family: 'Segoe UI', sans-serif; font-weight: 800;}}
        
        /* Estilo Liquidación en Pantalla */
        .liquidacion-box {{
            border: 1px solid #ccc;
            padding: 20px;
            background-color: #fff;
            font-family: 'Courier New', monospace;
            box-shadow: 3px 3px 10px rgba(0,0,0,0.1);
        }}
        .liq-header {{text-align: center; font-weight: bold; border-bottom: 2px solid #333; margin-bottom: 10px;}}
        .liq-row {{display: flex; justify-content: space-between; padding: 2px 0; border-bottom: 1px dotted #eee;}}
        .liq-total {{font-weight: bold; font-size: 1.1em; border-top: 2px solid #333; margin-top: 10px; padding-top: 5px;}}
        
        /* Botones */
        .stButton>button {{background-color: #004a99 !important; color: white !important; font-weight: bold; border-radius: 8px; width: 100%;}}
        .stButton>button:hover {{background-color: #003366 !important;}}
        </style>
        """, unsafe_allow_html=True)

cargar_estilos()

# --- 3. FUNCIONES UTILITARIAS ---
def fmt(valor): return "$0" if pd.isna(valor) else "${:,.0f}".format(valor).replace(",", ".")
def mostrar_miles(valor): 
    if valor > 0: st.markdown(f'<p style="color:green; font-size:0.8rem; margin-top:-10px;">Ingresaste: <b>{fmt(valor)}</b></p>', unsafe_allow_html=True)

def obtener_indicadores():
    try:
        r = requests.get('https://mindicador.cl/api', timeout=2)
        d = r.json()
        return float(d['uf']['valor']), float(d['utm']['valor'])
    except: return 39643.59, 69542.0

# --- 4. GENERADOR DE CONTRATOS (MOTOR LEGAL ROBUSTO) ---
def generar_contrato_legal(datos_financieros, datos_form):
    doc = Document()
    style = doc.styles['Normal']
    style.font.name = 'Arial'
    style.font.size = Pt(11)
    
    # Título
    titulo = doc.add_heading('CONTRATO DE TRABAJO', 0)
    titulo.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    # Datos combinados
    fecha_hoy = datetime.now().strftime("%d de %B de %Y")
    
    texto_intro = f"""
    En {datos_form['ciudad_firma']}, a {fecha_hoy}, entre la empresa "{datos_form['empresa_nombre'].upper()}", RUT {datos_form['empresa_rut']}, representada legalmente por don/ña {datos_form['rep_nombre'].upper()}, RUT {datos_form['rep_rut']}, ambos con domicilio en {datos_form['empresa_dir']}, en adelante el "Empleador"; y don/ña {datos_form['trab_nombre'].upper()}, RUT {datos_form['trab_rut']}, de nacionalidad {datos_form['trab_nacionalidad']}, estado civil {datos_form['trab_civil']}, nacido el {datos_form['trab_nacimiento']}, con domicilio en {datos_form['trab_dir']}, en adelante el "Trabajador", se ha convenido el siguiente contrato de trabajo:
    """
    doc.add_paragraph(texto_intro).alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    
    # Cláusulas
    clausulas = [
        ("PRIMERO (Naturaleza de los Servicios):", f"El Trabajador se compromete a desempeñar el cargo de {datos_form['cargo'].upper()}, realizando las funciones de {datos_form['funciones_breves']} y otras tareas inherentes a su cargo."),
        ("SEGUNDO (Lugar de Trabajo):", f"Los servicios se prestarán en las dependencias de la empresa ubicadas en {datos_form['lugar_trabajo']}."),
        ("TERCERO (Remuneración):", f"El Empleador pagará al Trabajador un sueldo base mensual de {fmt(datos_financieros['Sueldo Base'])}. Adicionalmente, se pagará una gratificación mensual con tope legal de 4.75 IMM ({fmt(datos_financieros['Gratificación'])}). También se pagarán asignaciones no imponibles de Colación y Movilización por un total de {fmt(datos_financieros['No Imponibles'])}. El sueldo líquido aproximado asciende a {fmt(datos_financieros['LÍQUIDO'])}."),
        ("CUARTO (Jornada):", "El trabajador cumplirá una jornada ordinaria de 44 horas semanales (sujeta a reducción gradual Ley 40 Horas), distribuida de lunes a viernes."),
        ("QUINTO (Vigencia):", f"El presente contrato es de carácter {datos_form['tipo_contrato']} y comenzará a regir a partir del {datos_form['fecha_inicio']}.")
    ]
    
    for titulo, contenido in clausulas:
        p = doc.add_paragraph()
        runner = p.add_run(titulo)
        runner.bold = True
        p.add_run(f" {contenido}")
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    
    # Firmas
    doc.add_paragraph("\n\n\n\n")
    table = doc.add_table(rows=1, cols=2)
    table.alignment = WD_ALIGN_PARAGRAPH.CENTER
    c1 = table.cell(0, 0)
    c1.text = "__________________________\nFIRMA EMPLEADOR\nRUT: " + datos_form['empresa_rut']
    c1.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    c2 = table.cell(0, 1)
    c2.text = "__________________________\nFIRMA TRABAJADOR\nRUT: " + datos_form['trab_rut']
    c2.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER

    bio = io.BytesIO()
    doc.save(bio)
    return bio

# --- 5. PERFILES ROBUSTOS ---
def generar_perfil_robusto(cargo, rubro):
    if not cargo: return None
    return {
        "titulo": cargo.title(),
        "mision": f"Liderar, planificar y ejecutar las estrategias del área de {cargo} en el sector {rubro}, optimizando recursos y garantizando la continuidad operacional.",
        "funciones": [
            "Gestión y control presupuestario del área (CAPEX/OPEX).",
            "Liderazgo de equipos de alto desempeño y gestión del cambio.",
            "Reportabilidad a Gerencia General mediante KPIs estratégicos.",
            "Aseguramiento de la normativa legal y técnica vigente."
        ],
        "requisitos_duros": [
            "Título Universitario (Ingeniería, Administración o afín).",
            f"Experiencia mínima de 4-5 años en industria {rubro}.",
            "Manejo avanzado de ERP (SAP, Oracle) y Excel.",
            "Inglés Nivel Intermedio/Avanzado."
        ],
        "competencias": ["Liderazgo Situacional", "Visión Estratégica", "Negociación", "Resiliencia"],
        "condiciones": ["Jornada Art. 22", "Modalidad Híbrida (según política)", "Seguro Complementario de Salud"]
    }

# --- 6. ANÁLISIS CV (LECTURA PDF) ---
def leer_pdf(archivo):
    if not LIBRARIES_OK: return None
    try:
        text = ""
        with pdfplumber.open(archivo) as pdf:
            for page in pdf.pages: text += (page.extract_text() or "")
        return text
    except: return None

def motor_analisis(texto_cv, cargo, rubro):
    keywords = ["liderazgo", "gestión", "equipo", "estrategia", "inglés", "excel", "presupuesto", "proyectos"]
    texto_lower = texto_cv.lower()
    
    encontradas = [k.title() for k in keywords if k in texto_lower]
    faltantes = [k.title() for k in keywords if k not in texto_lower]
    score = int((len(encontradas)/len(keywords))*100)
    
    decision = "Recomendable para Entrevista" if score > 60 else "No cumple perfil base"
    return score, encontradas, faltantes, decision

# --- 7. CÁLCULO REVERSO (LÓGICA PREVIRED) ---
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
        
        imp = 0 # Simplificado
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

# --- 8. INTERFAZ GRÁFICA ---

with st.sidebar:
    st.image("https://www.previred.com/wp-content/uploads/2021/01/logo-previred.png", width=120)
    uf_v, utm_v = obtener_indicadores()
    st.metric("UF", fmt(uf_v).replace("$",""))
    st.metric("UTM", fmt(utm_v))
    st.divider()
    s_min = st.number_input("Sueldo Mínimo", value=529000, step=1000)
    tope_prev = st.number_input("Tope AFP (UF)", value=87.8)
    tope_afc = st.number_input("Tope AFC (UF)", value=131.9)

st.title("HR Suite Ultimate V21")
st.markdown("**Sistema Integral de Gestión de Personas y Contratos**")

tabs = st.tabs(["💰 Calculadora & Liquidación", "📋 Perfil de Cargo", "🧠 Análisis CV", "📝 Generador Contratos"])

# --- TAB 1: CALCULADORA ---
with tabs[0]:
    c1, c2 = st.columns(2)
    with c1:
        liq = st.number_input("Líquido ($)", value=1000000, step=50000, format="%d")
        mostrar_miles(liq)
        col = st.number_input("Colación ($)", value=50000, format="%d")
        mov = st.number_input("Movilización ($)", value=50000, format="%d")
    with c2:
        con = st.selectbox("Contrato", ["Indefinido", "Plazo Fijo", "Sueldo Empresarial"])
        afp = st.selectbox("AFP", ["Capital", "Cuprum", "Habitat", "Modelo", "PlanVital", "Uno", "SIN AFP"])
        sal = st.selectbox("Salud", ["Fonasa (7%)", "Isapre (UF)"])
        plan = st.number_input("Plan UF", 0.0) if sal == "Isapre (UF)" else 0.0

    if st.button("CALCULAR NÓMINA"):
        res = calcular_reverso(liq, col, mov, con, afp, sal, plan, uf_v, utm_v, s_min, tope_prev, tope_afc)
        if res:
            st.session_state.calculo_actual = res
            
            # VISUALIZACIÓN TIPO LIQUIDACIÓN REAL
            st.markdown("### 📄 Liquidación de Sueldo Simulada")
            st.markdown(f"""
            <div class="liquidacion-box">
                <div class="liq-header">LIQUIDACIÓN DE SUELDO (Simulación)</div>
                <div class="liq-row"><span>Sueldo Base:</span><span>{fmt(res['Sueldo Base'])}</span></div>
                <div class="liq-row"><span>Gratificación Legal:</span><span>{fmt(res['Gratificación'])}</span></div>
                <div class="liq-row" style="font-weight:bold;"><span>TOTAL IMPONIBLE:</span><span>{fmt(res['Total Imponible'])}</span></div>
                <br>
                <div class="liq-row"><span>Asig. Colación:</span><span>{fmt(col)}</span></div>
                <div class="liq-row"><span>Asig. Movilización:</span><span>{fmt(mov)}</span></div>
                <div class="liq-row" style="background:#f0f0f0;"><span>TOTAL HABERES:</span><span>{fmt(res['Total Imponible']+res['No Imponibles'])}</span></div>
                <br>
                <div class="liq-row"><span>AFP ({afp}):</span><span style="color:red;">-{fmt(res['AFP'])}</span></div>
                <div class="liq-row"><span>Salud ({sal}):</span><span style="color:red;">-{fmt(res['Salud'])}</span></div>
                <div class="liq-row"><span>Seguro Cesantía:</span><span style="color:red;">-{fmt(res['AFC'])}</span></div>
                <div class="liq-row"><span>Impuesto Único:</span><span style="color:red;">-{fmt(res['Impuesto'])}</span></div>
                
                <div class="liq-row liq-total">
                    <span>LÍQUIDO A PAGAR:</span>
                    <span style="font-size:1.3em;">{fmt(res['LÍQUIDO'])}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            st.info(f"💰 **Costo Empresa Real:** {fmt(res['COSTO TOTAL'])} (Incluye Aportes Patronales)")
        else: st.error("Error de cálculo.")

# --- TAB 2: PERFIL ---
with tabs[1]:
    st.header("Generador de Perfiles de Alto Nivel")
    col_c, col_r = st.columns(2)
    cargo = col_c.text_input("Cargo", placeholder="Ej: Gerente de Finanzas")
    rubro = col_r.selectbox("Industria", ["Minería", "Tecnología", "Retail", "Banca", "Servicios"])
    
    if cargo:
        perf = generar_perfil_robusto(cargo, rubro)
        st.markdown(f"### 📋 {perf['titulo']}")
        st.info(f"**Misión:** {perf['mision']}")
        
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("#### 🔹 Funciones Clave")
            for f in perf['funciones']: st.write(f"- {f}")
            st.markdown("#### 🔹 Competencias")
            for c in perf['competencias']: st.write(f"- {c}")
        with c2:
            st.markdown("#### 🔸 Requisitos Excluyentes")
            for r in perf['requisitos_duros']: st.write(f"- {r}")
            st.markdown("#### 🔸 Condiciones")
            for k in perf['condiciones']: st.write(f"- {k}")

# --- TAB 3: ANÁLISIS CV ---
with tabs[2]:
    st.header("Análisis de CV (IA)")
    if not LIBRARIES_OK: st.warning("Instale librerías.")
    else:
        uploaded = st.file_uploader("Subir PDF", type="pdf")
        if uploaded and cargo:
            if st.button("ANALIZAR"):
                txt = leer_pdf(uploaded)
                if txt:
                    score, enc, fal, dec = motor_analisis(txt, cargo, rubro)
                    c1, c2 = st.columns([1,2])
                    c1.metric("Match Score", f"{score}%")
                    c1.info(f"Dictamen: {dec}")
                    c2.success(f"✅ Encontrado: {', '.join(enc)}")
                    c2.error(f"⚠️ Faltante: {', '.join(fal)}")

# --- TAB 4: CONTRATOS (NUEVO FORMULARIO COMPLETO) ---
with tabs[3]:
    st.header("📝 Generador de Contrato de Trabajo")
    
    if st.session_state.calculo_actual:
        st.success(f"✅ Datos financieros cargados (Sueldo Base: {fmt(st.session_state.calculo_actual['Sueldo Base'])})")
        
        with st.form("contract_full"):
            st.markdown("#### 1. Datos del Empleador")
            ce1, ce2 = st.columns(2)
            emp_nom = ce1.text_input("Razón Social Empresa")
            emp_rut = ce2.text_input("RUT Empresa")
            emp_dir = st.text_input("Dirección Empresa")
            
            ce3, ce4 = st.columns(2)
            rep_nom = ce3.text_input("Nombre Representante Legal")
            rep_rut = ce4.text_input("RUT Representante")
            
            st.markdown("#### 2. Datos del Trabajador")
            ct1, ct2 = st.columns(2)
            trab_nom = ct1.text_input("Nombre Completo Trabajador")
            trab_rut = ct2.text_input("RUT Trabajador")
            trab_nac = ct1.date_input("Fecha Nacimiento")
            trab_nac_pais = ct2.text_input("Nacionalidad", "Chilena")
            trab_civ = st.selectbox("Estado Civil", ["Soltero", "Casado", "Viudo", "Divorciado"])
            trab_dir = st.text_input("Domicilio Trabajador")
            
            st.markdown("#### 3. Condiciones Contractuales")
            cc1, cc2 = st.columns(2)
            cargo_con = cc1.text_input("Cargo", value=cargo if cargo else "")
            lugar_con = cc2.text_input("Lugar de prestación servicios", value=emp_dir)
            f_ini = st.date_input("Fecha Inicio Contrato")
            t_con = st.selectbox("Tipo", ["Indefinido", "Plazo Fijo", "Obra Faena"])
            func_brev = st.text_area("Descripción breve de funciones")
            
            sub_btn = st.form_submit_button("GENERAR CONTRATO LEGAL (.DOCX)")
            
            if sub_btn and emp_nom and trab_nom:
                datos_form = {
                    "empresa_nombre": emp_nom, "empresa_rut": emp_rut, "empresa_dir": emp_dir,
                    "rep_nombre": rep_nom, "rep_rut": rep_rut,
                    "trab_nombre": trab_nom, "trab_rut": trab_rut, 
                    "trab_nacionalidad": trab_nac_pais, "trab_civil": trab_civ, 
                    "trab_nacimiento": str(trab_nac), "trab_dir": trab_dir,
                    "cargo": cargo_con, "lugar_trabajo": lugar_con, 
                    "fecha_inicio": str(f_ini), "tipo_contrato": t_con, "funciones_breves": func_brev,
                    "ciudad_firma": "Santiago"
                }
                
                doc_io = generar_contrato_legal(st.session_state.calculo_actual, datos_form)
                
                st.download_button(
                    label="⬇️ DESCARGAR CONTRATO LISTO",
                    data=doc_io.getvalue(),
                    file_name=f"Contrato_{trab_nom}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
    else:
        st.warning("⚠️ Primero realice un cálculo de sueldo en la Pestaña 1.")
