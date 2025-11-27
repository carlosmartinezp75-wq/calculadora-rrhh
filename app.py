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

# --- 0. VALIDACIÓN ---
try:
    import pdfplumber
    from docx import Document
    from docx.shared import Pt
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    LIBRARIES_OK = True
except ImportError:
    LIBRARIES_OK = False

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="HR Suite Ultimate", page_icon="💎", layout="wide")

if 'empresa' not in st.session_state:
    st.session_state.empresa = {"nombre": "", "rut": "", "direccion": "", "rep_nombre": "", "rep_rut": "", "ciudad": "Santiago"}
if 'calculo_actual' not in st.session_state: st.session_state.calculo_actual = None
if 'cargo_actual' not in st.session_state: st.session_state.cargo_actual = ""
if 'rubro_actual' not in st.session_state: st.session_state.rubro_actual = ""

# --- 2. ESTILOS ---
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
        .block-container {{background-color: rgba(255, 255, 255, 0.98); padding: 2.5rem; border-radius: 15px; box-shadow: 0 10px 40px rgba(0,0,0,0.1);}}
        h1, h2, h3 {{color: #004a99 !important; font-family: 'Segoe UI', sans-serif; font-weight: 800;}}
        .stButton>button {{background-color: #004a99 !important; color: white !important; font-weight: bold; border-radius: 8px; width: 100%; height: 3rem;}}
        .stButton>button:hover {{background-color: #003366 !important;}}
        .liq-container {{border: 1px solid #ddd; padding: 20px; background: #fff; font-family: 'Courier New', monospace; margin-top: 20px;}}
        .liq-row {{display: flex; justify-content: space-between; border-bottom: 1px dashed #eee; padding: 5px 0;}}
        .liq-total {{font-weight: bold; font-size: 1.2em; background-color: #f0f8ff; padding: 10px; margin-top: 10px; border: 1px solid #004a99;}}
        .miles-feedback {{font-size: 0.8rem; color: #28a745; font-weight: bold; margin-top: -10px;}}
        </style>
        """, unsafe_allow_html=True)

cargar_estilos()

# --- 3. FUNCIONES ---
def fmt(valor): return "$0" if pd.isna(valor) else "${:,.0f}".format(valor).replace(",", ".")
def mostrar_miles(valor): 
    if valor > 0: st.markdown(f'<p class="miles-feedback">Ingresaste: {fmt(valor)}</p>', unsafe_allow_html=True)

def obtener_indicadores():
    try:
        r = requests.get('https://mindicador.cl/api', timeout=2)
        d = r.json()
        return float(d['uf']['valor']), float(d['utm']['valor'])
    except: return 39643.59, 69542.0

def get_tablas_previred():
    afp = pd.DataFrame({
        "AFP": ["Capital", "Cuprum", "Habitat", "PlanVital", "Provida", "Modelo", "Uno"],
        "Tasa": ["11,44%", "11,44%", "11,27%", "11,16%", "11,45%", "10,58%", "10,46%"],
        "SIS": ["1,49%"]*7
    })
    cesantia = pd.DataFrame({
        "Contrato": ["Indefinido", "Plazo Fijo", "Casa Particular"],
        "Empleador": ["2,4%", "3,0%", "3,0%"],
        "Trabajador": ["0,6%", "0,0%", "0,0%"]
    })
    return afp, cesantia

# --- 4. MOTORES INTELIGENTES ---

# A. PLAN CARRERA
def generar_plan_carrera(cargo, rubro):
    rubro_txt = f"en sector {rubro}" if rubro else ""
    return {
        "corto": [f"Inducción normativa {rubro_txt}.", "Certificación en herramientas de gestión interna.", "Cumplimiento de KPIs operativos."],
        "mediano": ["Liderazgo de proyectos de mejora continua.", f"Especialización técnica en tendencias de {rubro}.", "Mentoring a pares junior."],
        "largo": ["Asumir Jefatura/Gerencia de Área.", "Participación en comité estratégico.", "Desarrollo de nuevos negocios."]
    }

# B. PERFIL ROBUSTO (CORREGIDO KEYERROR)
def generar_perfil_robusto(cargo, rubro):
    if not cargo: return None
    return {
        "titulo": cargo.title(),
        "mision": f"Liderar y ejecutar la estrategia del área de {cargo} {f'en la industria {rubro}' if rubro else ''}, optimizando recursos y garantizando continuidad operativa.",
        "funciones": ["Control presupuestario (CAPEX/OPEX).", "Gestión de equipos de alto desempeño.", "Reportabilidad a Gerencia.", "Aseguramiento normativo."],
        "requisitos": ["Título Profesional afín.", f"Experiencia 3+ años en {rubro}.", "Manejo ERP/Excel Avanzado.", "Inglés Técnico."], # Llave unificada
        "competencias": ["Liderazgo Situacional", "Visión Estratégica", "Resiliencia", "Comunicación Efectiva"]
    }

# C. ANALISIS CV
def motor_analisis(texto_cv, cargo, rubro):
    kws = ["gestión", "equipo", "liderazgo", "estrategia", "inglés", "excel", "presupuesto", "proyectos", "análisis"]
    txt_lower = texto_cv.lower()
    enc = [k.title() for k in kws if k in txt_lower]
    fal = [k.title() for k in kws if k not in txt_lower]
    score = int((len(enc)/len(kws))*100) + random.randint(5,15)
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

# D. CÁLCULO SUELDO
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
        tabla = [(13.5,0,0),(30,0.04,0.54),(50,0.08,1.74),(70,0.135,4.49),(90,0.23,11.14),(120,0.304,17.80),(310,0.35,23.32),(99999,0.40,38.82)]
        for l, f, r in tabla:
            if (base_trib/utm) <= l:
                imp = int((base_trib * f) - (r * utm))
                break
        imp = max(0, imp)
        
        liq_calc = tot_imp - m_afp - m_sal - int(min(tot_imp, t_afc*uf)*tasa_afc_trab) - imp
        if abs(liq_calc - liq_meta) < 500:
            aportes = int(b_prev*(0.0149+0.0093)) + int(min(tot_imp, t_afc*uf)*tasa_afc_emp)
            return {
                "Sueldo Base": int(base), "Gratificación": int(grat), "Total Imponible": int(tot_imp),
                "No Imponibles": int(no_imp), "LÍQUIDO": int(liq_calc+no_imp), "AFP": m_afp, 
                "Salud": m_sal, "AFC": int(min(tot_imp, t_afc*uf)*tasa_afc_trab), "Impuesto": imp,
                "Aportes Empresa": aportes, "COSTO TOTAL": int(tot_imp+no_imp+aportes), "Base Trib": int(base_trib)
            }
            break
        elif liq_calc < liq_meta: min_b = base
        else: max_b = base
    return None

# E. CONTRATOS WORD
def generar_contrato_word(datos_financieros, datos_form):
    doc = Document()
    style = doc.styles['Normal']
    style.font.name = 'Arial'
    style.font.size = Pt(11)
    
    t = doc.add_heading('CONTRATO DE TRABAJO', 0)
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.add_paragraph("")
    
    intro = f"""En {datos_form['ciudad']}, a {datetime.now().strftime("%d de %B de %Y")}, entre "{datos_form['empresa_nombre'].upper()}", RUT {datos_form['empresa_rut']}, representada por {datos_form['rep_nombre'].upper()}, RUT {datos_form['rep_rut']}, ambos domiciliados en {datos_form['empresa_dir']}, en adelante "Empleador"; y {datos_form['trab_nombre'].upper()}, RUT {datos_form['trab_rut']}, nacionalidad {datos_form['trab_nacionalidad']}, nacido el {str(datos_form['trab_nacimiento'])}, domiciliado en {datos_form['trab_dir']}, en adelante "Trabajador", se ha convenido el siguiente contrato de trabajo:"""
    doc.add_paragraph(intro).alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    
    clausulas = [
        ("PRIMERO:", f"El Trabajador prestará servicios como {datos_form['cargo'].upper()}."),
        ("SEGUNDO:", f"El Empleador pagará un sueldo base mensual de {fmt(datos_financieros['Sueldo Base'])}. Además, pagará la gratificación legal con tope de 4.75 IMM ({fmt(datos_financieros['Gratificación'])}). Se pagarán asignaciones de Colación y Movilización por un total de {fmt(datos_financieros['No Imponibles'])}."),
        ("TERCERO:", "La jornada de trabajo será de 44 horas semanales, distribuidas de lunes a viernes."),
        ("CUARTO:", f"El presente contrato es {datos_form['tipo_contrato']} e inicia el {str(datos_form['fecha_inicio'])}.")
    ]
    
    for tit, txt in clausulas:
        p = doc.add_paragraph(); p.add_run(tit).bold = True; p.add_run(f" {txt}")
    
    bio = io.BytesIO()
    doc.save(bio)
    return bio

# --- 8. INTERFAZ ---

with st.sidebar:
    st.image("https://www.previred.com/wp-content/uploads/2021/01/logo-previred.png", width=120)
    
    with st.expander("🏢 Datos Empresa (Configuración)", expanded=True):
        st.session_state.empresa['nombre'] = st.text_input("Razón Social", st.session_state.empresa['nombre'])
        st.session_state.empresa['rut'] = st.text_input("RUT Empresa", st.session_state.empresa['rut'])
        st.session_state.empresa['direccion'] = st.text_input("Dirección", st.session_state.empresa['direccion'])
        st.session_state.empresa['rep_nombre'] = st.text_input("Rep. Legal", st.session_state.empresa['rep_nombre'])
        st.session_state.empresa['rep_rut'] = st.text_input("RUT Rep.", st.session_state.empresa['rep_rut'])
        if st.button("Guardar Datos"): st.success("Guardado")

    st.divider()
    uf_v, utm_v = obtener_indicadores()
    st.metric("UF", fmt(uf_v).replace("$",""))
    st.metric("UTM", fmt(utm_v))

st.title("HR Suite Ultimate V24")
st.markdown("**Sistema Integral de Gestión de Personas**")

tabs = st.tabs(["💰 Calculadora", "📋 Perfil Cargo", "🧠 Análisis CV", "🚀 Carrera", "📝 Contratos", "📊 Indicadores"])

# TAB 1: CALCULADORA
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
        res = calcular_reverso(liq, col, mov, con, afp, sal, plan, uf_v, utm_v, 529000, 87.8, 131.9)
        if res:
            st.session_state.calculo_actual = res
            
            st.markdown("#### Resultado Simulación")
            k1, k2, k3 = st.columns(3)
            k1.metric("Sueldo Base", fmt(res['Sueldo Base']))
            k2.metric("Líquido", fmt(res['LÍQUIDO']), delta="Objetivo")
            k3.metric("Costo Empresa", fmt(res['COSTO TOTAL']), delta="Inversión", delta_color="inverse")
            
            st.markdown(f"""
            <div class="liq-container">
                <div style="text-align:center; font-weight:bold; border-bottom:2px solid #333; margin-bottom:10px;">LIQUIDACIÓN DE SUELDO</div>
                <div class="liq-row"><span>Sueldo Base:</span><span>{fmt(res['Sueldo Base'])}</span></div>
                <div class="liq-row"><span>Gratificación:</span><span>{fmt(res['Gratificación'])}</span></div>
                <div class="liq-row" style="background:#eee;"><span><b>TOTAL IMPONIBLE:</b></span><span><b>{fmt(res['Total Imponible'])}</b></span></div>
                <br>
                <div class="liq-row"><span>No Imponibles:</span><span>{fmt(res['No Imponibles'])}</span></div>
                <div class="liq-row"><span><b>TOTAL HABERES:</b></span><span><b>{fmt(res['Total Imponible']+res['No Imponibles'])}</b></span></div>
                <br>
                <div class="liq-row"><span>AFP:</span><span style="color:#d9534f;">-{fmt(res['AFP'])}</span></div>
                <div class="liq-row"><span>Salud:</span><span style="color:#d9534f;">-{fmt(res['Salud'])}</span></div>
                <div class="liq-row"><span>Cesantía:</span><span style="color:#d9534f;">-{fmt(res['AFC'])}</span></div>
                <div class="liq-row"><span>Impuesto:</span><span style="color:#d9534f;">-{fmt(res['Impuesto'])}</span></div>
                <div class="liq-total" style="display:flex; justify-content:space-between;">
                    <span>LÍQUIDO A PAGAR:</span><span>{fmt(res['LÍQUIDO'])}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
        else: st.error("Error matemático.")

# TAB 2: PERFIL
with tabs[1]:
    col1, col2 = st.columns(2)
    cargo = col1.text_input("Cargo", placeholder="Ej: Jefe de Ventas")
    
    # LISTA DE RUBROS COMPLETA
    rubros_list = [
        "Minería", "Tecnología/TI", "Retail", "Banca/Finanzas", "Salud", 
        "Construcción", "Agroindustria", "Transporte/Logística", 
        "Educación", "Servicios", "Sector Público", "Energía"
    ]
    rubro = col2.selectbox("Rubro", rubros_list)
    
    if cargo:
        st.session_state.cargo_actual = cargo
        st.session_state.rubro_actual = rubro
        perf = generar_perfil_robusto(cargo, rubro)
        
        st.info(f"**Misión:** {perf['mision']}")
        c1, c2 = st.columns(2)
        c1.success("**Funciones:**\n" + "\n".join([f"- {x}" for x in perf['funciones']]))
        c2.warning("**Requisitos:**\n" + "\n".join([f"- {x}" for x in perf['requisitos']])) # KEY CORREGIDA

# TAB 3: ANÁLISIS CV
with tabs[2]:
    st.header("Análisis de Talento")
    if not LIBRARIES_OK: st.warning("Instalar pdfplumber.")
    else:
        uploaded = st.file_uploader("Subir CV (PDF)", type="pdf")
        if uploaded and st.session_state.cargo_actual:
            if st.button("ANALIZAR CANDIDATO"):
                txt = leer_pdf(uploaded)
                if txt:
                    score, enc, fal, nivel = motor_analisis(txt, st.session_state.cargo_actual, st.session_state.rubro_actual)
                    
                    c1, c2 = st.columns([1,2])
                    c1.metric("Match Score", f"{score}%")
                    c1.info(f"Nivel: **{nivel}**")
                    fig = go.Figure(go.Indicator(mode="gauge+number", value=score, gauge={'axis':{'range':[0,100]}, 'bar':{'color':"#004a99"}}))
                    c1.plotly_chart(fig, use_container_width=True)
                    
                    c2.success(f"✅ Detectado: {', '.join(enc)}")
                    c2.error(f"⚠️ Brecha: {', '.join(fal)}")

# TAB 4: CARRERA
with tabs[3]:
    st.header("Plan de Desarrollo")
    if st.session_state.cargo_actual:
        plan = generar_plan_carrera(st.session_state.cargo_actual, st.session_state.rubro_actual)
        c1, c2, c3 = st.columns(3)
        c1.markdown("#### Corto Plazo"); c1.write("\n".join([f"- {p}" for p in plan['corto']]))
        c2.markdown("#### Mediano Plazo"); c2.write("\n".join([f"- {p}" for p in plan['mediano']]))
        c3.markdown("#### Largo Plazo"); c3.write("\n".join([f"- {p}" for p in plan['largo']]))
    else: st.warning("Defina cargo en Pestaña 2")

# TAB 5: CONTRATOS
with tabs[4]:
    st.header("Generador Legal")
    if st.session_state.calculo_actual:
        if not st.session_state.empresa['rut']: st.warning("⚠️ Complete datos de empresa en Sidebar.")
        
        with st.form("form_cont"):
            st.markdown("#### Datos Trabajador")
            c1, c2 = st.columns(2)
            tn = c1.text_input("Nombre")
            tr = c2.text_input("RUT")
            tnac = c1.text_input("Nacionalidad", "Chilena")
            tdir = c2.text_input("Domicilio")
            tfec = st.date_input("Nacimiento")
            fini = st.date_input("Inicio Contrato")
            
            if st.form_submit_button("GENERAR DOCX"):
                datos = {
                    "empresa_nombre": st.session_state.empresa['nombre'],
                    "empresa_rut": st.session_state.empresa['rut'],
                    "empresa_dir": st.session_state.empresa['direccion'],
                    "rep_nombre": st.session_state.empresa['rep_nombre'],
                    "rep_rut": st.session_state.empresa['rep_rut'],
                    "ciudad": st.session_state.empresa['ciudad'],
                    "trab_nombre": tn, "trab_rut": tr, "trab_nacionalidad": tnac,
                    "trab_nacimiento": tfec, "trab_dir": tdir,
                    "cargo": st.session_state.cargo_actual if st.session_state.cargo_actual else "Trabajador",
                    "fecha_inicio": fini, "tipo_contrato": "Indefinido"
                }
                bio = generar_contrato_word(st.session_state.calculo_actual, datos)
                st.download_button("⬇️ Descargar Contrato", bio.getvalue(), f"Contrato_{tn}.docx")
    else: st.info("Realice cálculo en Pestaña 1")

# TAB 6: INDICADORES
with tabs[5]:
    st.header("Indicadores Oficiales")
    t_afp, t_ces = get_tablas_previred()
    c1, c2 = st.columns(2)
    c1.subheader("Tasas AFP"); c1.table(t_afp)
    c2.subheader("Seguro Cesantía"); c2.table(t_ces)
