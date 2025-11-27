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

# --- 0. VALIDACIÓN DE LIBRERÍAS (Blindaje contra errores de importación) ---
try:
    import pdfplumber
    from docx import Document
    from docx.shared import Pt, Inches, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    LIBRARIES_OK = True
except ImportError:
    LIBRARIES_OK = False

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="HR Suite Enterprise V26", page_icon="🏢", layout="wide")

# Inicialización de Estado (Para que no se borren los datos al cambiar de pestaña)
if 'empresa' not in st.session_state:
    st.session_state.empresa = {"nombre": "", "rut": "", "direccion": "", "rep_nombre": "", "rep_rut": "", "ciudad": "Santiago", "giro": "Servicios"}
if 'calculo_actual' not in st.session_state: st.session_state.calculo_actual = None
if 'cargo_actual' not in st.session_state: st.session_state.cargo_actual = ""
if 'rubro_actual' not in st.session_state: st.session_state.rubro_actual = ""
if 'perfil_generado' not in st.session_state: st.session_state.perfil_generado = None

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
        css_fondo = """[data-testid="stAppViewContainer"] {background: linear-gradient(135deg, #fdfbfb 0%, #ebedee 100%);}"""

    st.markdown(f"""
        <style>
        {css_fondo}
        .block-container {{background-color: rgba(255, 255, 255, 0.98); padding: 2rem; border-radius: 15px; box-shadow: 0 10px 40px rgba(0,0,0,0.1);}}
        h1, h2, h3 {{color: #004a99 !important; font-family: 'Segoe UI', sans-serif; font-weight: 800;}}
        .stButton>button {{background-color: #004a99 !important; color: white !important; font-weight: bold; border-radius: 8px; width: 100%; height: 3rem;}}
        .stButton>button:hover {{background-color: #003366 !important;}}
        
        /* Liquidación Visual */
        .liq-container {{border: 1px solid #999; padding: 20px; background: #fff; font-family: 'Courier New', monospace;}}
        .liq-row {{display: flex; justify-content: space-between; border-bottom: 1px dotted #ccc; padding: 4px 0;}}
        .liq-total {{font-weight: bold; font-size: 1.2em; background-color: #e3f2fd; padding: 10px; margin-top: 15px; border: 2px solid #004a99;}}
        </style>
        """, unsafe_allow_html=True)

cargar_estilos()

# --- 3. FUNCIONES UTILITARIAS ---
def fmt(valor): return "$0" if pd.isna(valor) else "${:,.0f}".format(valor).replace(",", ".")
def mostrar_miles(valor): 
    if valor > 0: st.markdown(f'<p style="color:green; font-size:0.8rem; margin-top:-15px;">Ingresaste: <b>{fmt(valor)}</b></p>', unsafe_allow_html=True)

def obtener_indicadores():
    try:
        r = requests.get('https://mindicador.cl/api', timeout=2)
        d = r.json()
        return float(d['uf']['valor']), float(d['utm']['valor'])
    except: return 39643.59, 69542.0

# --- 4. MOTORES DE INTELIGENCIA (SIN ERRORES DE LLAVE) ---

def generar_perfil_robusto(cargo, rubro):
    if not cargo: return None
    # ESTANDARIZACIÓN DE LLAVES (ESTO CORRIGE EL KEYERROR)
    return {
        "titulo": cargo.title(),
        "mision": f"Gestionar estratégicamente el área de {cargo} en el rubro {rubro}, asegurando cumplimiento normativo y eficiencia.",
        "funciones": ["Control de Gestión y Presupuesto.", "Liderazgo de Equipos.", "Reportabilidad Gerencial.", "Mejora Continua de Procesos."],
        "requisitos": ["Título Profesional.", f"Experiencia en {rubro}.", "Manejo de ERP.", "Inglés Técnico."],
        "competencias": ["Liderazgo", "Negociación", "Visión Estratégica", "Trabajo bajo presión"] # Llave unificada
    }

def motor_analisis(texto_cv, cargo, rubro):
    kws = ["gestión", "equipo", "liderazgo", "estrategia", "inglés", "excel", "presupuesto", "proyectos"]
    txt_lower = texto_cv.lower()
    enc = [k.title() for k in kws if k in txt_lower]
    fal = [k.title() for k in kws if k not in txt_lower]
    score = int((len(enc)/len(kws))*100) + 15
    score = min(99, max(10, score))
    nivel = "Senior" if score > 70 else "Junior"
    return score, enc, fal, nivel

def leer_pdf(archivo):
    if not LIBRARIES_OK: return None
    try:
        text = ""
        with pdfplumber.open(archivo) as pdf:
            for p in pdf.pages: text += (p.extract_text() or "")
        return text
    except: return None

# --- 5. CÁLCULO SUELDO ---
def calcular_reverso(liquido, col, mov, contrato, afp_n, salud_t, plan, uf, utm, s_min, t_imp, t_afc):
    no_imp = col + mov
    liq_meta = liquido - no_imp
    if liq_meta < s_min * 0.4: return None
    
    TOPE_GRAT = (4.75 * s_min) / 12
    tasa_afp = 0.0 if (contrato == "Sueldo Empresarial" or afp_n == "SIN AFP") else (0.10 + ({"Capital":1.44,"Habitat":1.27,"Modelo":0.58,"Uno":0.49}.get(afp_n,1.44)/100))
    tasa_afc_emp = 0.024
    tasa_afc_trab = 0.006 if contrato == "Indefinido" and contrato != "Sueldo Empresarial" else 0.0
    
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

# --- 6. GENERADOR DE CONTRATOS (INTEGRACIÓN AGENTE LEGAL) ---
def generar_contrato_legal_word(fin, form):
    doc = Document()
    style = doc.styles['Normal']
    style.font.name = 'Arial'
    style.font.size = Pt(11)
    
    # Encabezado
    t = doc.add_heading('CONTRATO DE TRABAJO', 0)
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.add_paragraph("")
    
    # Fecha y Ciudad
    fecha_hoy = datetime.now().strftime("%d de %B de %Y")
    p_fecha = doc.add_paragraph(f"En {form['ciudad']}, a {fecha_hoy}, entre:")
    
    # Identificación Partes (Estilo Legal)
    intro = f"""
    POR UNA PARTE: La empresa "{form['empresa_nombre'].upper()}", RUT {form['empresa_rut']}, giro {form['empresa_giro']}, representada legalmente por don/ña {form['rep_nombre'].upper()}, cédula de identidad N° {form['rep_rut']}, ambos domiciliados en {form['empresa_dir']}, en adelante el "EMPLEADOR".

    Y POR OTRA PARTE: Don/ña {form['trab_nombre'].upper()}, cédula de identidad N° {form['trab_rut']}, de nacionalidad {form['trab_nacionalidad']}, fecha de nacimiento {str(form['trab_nacimiento'])}, domiciliado en {form['trab_dir']}, en adelante el "TRABAJADOR".
    
    Se ha convenido el siguiente contrato de trabajo:
    """
    doc.add_paragraph(intro).alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    
    # Cláusulas Robustas (Basadas en el Agente)
    clausulas = [
        ("PRIMERO: Naturaleza de los Servicios.", f"El Trabajador se compromete a prestar sus servicios personales como {form['cargo'].upper()}, desempeñando las funciones de {form['funciones']}, y cualquier otra labor inherente a su cargo que le encomiende la Jefatura."),
        
        ("SEGUNDO: Lugar de Trabajo.", f"Los servicios se prestarán en las dependencias de la empresa ubicadas en {form['empresa_dir']}, sin perjuicio de los desplazamientos que requiera el cargo dentro o fuera de la ciudad."),
        
        ("TERCERO: Jornada de Trabajo.", "El trabajador cumplirá una jornada ordinaria de 44 horas semanales, distribuidas de lunes a viernes. (Nota: Ajustable si es Art. 22)."),
        
        ("CUARTO: Remuneración.", f"El Empleador pagará al Trabajador una remuneración mensual compuesta por:\n"
                                  f"a) Sueldo Base: {fmt(fin['Sueldo Base'])}\n"
                                  f"b) Gratificación Legal: {fmt(fin['Gratificación'])} (Tope 4.75 IMM)\n"
                                  f"c) Asig. Colación: {fmt(form['colacion'])}\n"
                                  f"d) Asig. Movilización: {fmt(form['movilizacion'])}"),
        
        ("QUINTO: Descuentos Legales.", "El Empleador deducirá de las remuneraciones los impuestos, cotizaciones previsionales y de seguridad social obligatorias."),
        
        ("SEXTO: Obligaciones y Prohibiciones.", "El Trabajador deberá cumplir con el Reglamento Interno de Orden, Higiene y Seguridad. Se prohíbe expresamente utilizar información confidencial de la empresa para fines ajenos al contrato."),
        
        ("SÉPTIMO: Propiedad Intelectual.", "Toda invención, mejora o creación desarrollada por el Trabajador durante la vigencia del contrato será propiedad exclusiva del Empleador."),
        
        ("OCTAVO: Vigencia.", f"El presente contrato es de carácter {form['tipo_contrato']} y comenzará a regir a partir del {str(form['fecha_inicio'])}.")
    ]
    
    for titulo, texto in clausulas:
        p = doc.add_paragraph()
        run = p.add_run(titulo)
        run.bold = True
        run.font.color.rgb = RGBColor(0, 0, 0) # Negro
        p.add_run(f" {texto}")
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        doc.add_paragraph("") # Espacio
    
    # Firmas
    doc.add_paragraph("\n\n\n\n")
    table = doc.add_table(rows=1, cols=2)
    table.alignment = WD_ALIGN_PARAGRAPH.CENTER
    c1 = table.cell(0, 0)
    c1.text = "___________________________\np.p EMPLEADOR\nRUT: " + form['empresa_rut']
    c1.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    c2 = table.cell(0, 1)
    c2.text = "___________________________\nTRABAJADOR\nRUT: " + form['trab_rut']
    c2.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    bio = io.BytesIO()
    doc.save(bio)
    return bio

# --- 7. INTERFAZ GRÁFICA ---

with st.sidebar:
    st.image("https://www.previred.com/wp-content/uploads/2021/01/logo-previred.png", width=120)
    
    with st.expander("🏢 DATOS EMPRESA (Persistentes)", expanded=True):
        st.session_state.empresa['nombre'] = st.text_input("Razón Social", st.session_state.empresa['nombre'])
        st.session_state.empresa['rut'] = st.text_input("RUT Empresa", st.session_state.empresa['rut'])
        st.session_state.empresa['giro'] = st.text_input("Giro Comercial", st.session_state.empresa['giro'])
        st.session_state.empresa['direccion'] = st.text_input("Dirección", st.session_state.empresa['direccion'])
        st.session_state.empresa['ciudad'] = st.text_input("Ciudad Firma", st.session_state.empresa['ciudad'])
        st.session_state.empresa['rep_nombre'] = st.text_input("Rep. Legal", st.session_state.empresa['rep_nombre'])
        st.session_state.empresa['rep_rut'] = st.text_input("RUT Rep.", st.session_state.empresa['rep_rut'])
        if st.button("💾 Guardar Configuración"): st.success("Datos guardados en memoria.")

    st.divider()
    uf_v, utm_v = obtener_indicadores()
    st.metric("UF Hoy", fmt(uf_v).replace("$",""))
    st.metric("UTM Hoy", fmt(utm_v))
    st.caption("Parametros Legales: Sueldo Mín. $529.000")

st.title("HR Suite Enterprise V26")
st.markdown("**Sistema Integral de Gestión de Personas y Contratos**")

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

# TAB 2: PERFIL (CORREGIDO KEYERROR)
with tabs[1]:
    col1, col2 = st.columns(2)
    cargo = col1.text_input("Cargo", placeholder="Ej: Jefe de Ventas")
    # LISTA DE RUBROS COMPLETA
    rubros = ["Minería", "Tecnología", "Retail", "Banca", "Salud", "Construcción", "Agro", "Transporte", "Educación", "Servicios"]
    rubro = col2.selectbox("Rubro", rubros)
    
    if cargo:
        st.session_state.cargo_actual = cargo
        st.session_state.rubro_actual = rubro
        perf = generar_perfil_robusto(cargo, rubro)
        st.session_state.perfil_generado = perf # Guardar
        
        st.info(f"**Misión:** {perf['mision']}")
        c1, c2 = st.columns(2)
        # USO DE KEYS CORRECTAS UNIFICADAS
        c1.success("**Funciones:**\n" + "\n".join([f"- {x}" for x in perf['funciones']]))
        c2.warning("**Requisitos:**\n" + "\n".join([f"- {x}" for x in perf['requisitos']]))
        st.markdown("**Competencias:** " + ", ".join(perf['competencias']))

# TAB 3: ANÁLISIS CV (CORREGIDO)
with tabs[2]:
    st.header("Análisis Inteligente de Talento")
    if not LIBRARIES_OK: st.warning("⚠️ Librerías faltantes.")
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
                    c2.success(f"✅ Fortalezas: {', '.join(enc)}")
                    c2.error(f"⚠️ Brechas: {', '.join(fal)}")

# TAB 4: CARRERA (RECUPERADO)
with tabs[3]:
    st.header("Plan de Desarrollo Profesional")
    if st.session_state.cargo_actual:
        # Generador simple para el ejemplo
        st.markdown("#### 🔹 Corto Plazo (0-1 Año)")
        st.write("- Inducción corporativa y normativa específica del rubro.")
        st.write("- Cumplimiento de metas operativas iniciales.")
        st.markdown("#### 🏆 Largo Plazo (3+ Años)")
        st.write("- Liderazgo estratégico de área.")
        st.write("- Participación en nuevos negocios.")
    else: st.warning("Defina un cargo en la Pestaña 2.")

# TAB 5: CONTRATOS (AGENTE LEGAL INTEGRADO)
with tabs[4]:
    st.header("Generador Legal (Agent Powered)")
    if st.session_state.calculo_actual:
        if not st.session_state.empresa['rut']: st.warning("⚠️ Complete 'Datos Empresa' en la barra lateral.")
        
        with st.form("form_legal"):
            st.markdown("#### Datos del Trabajador")
            c1, c2 = st.columns(2)
            tn = c1.text_input("Nombre Completo")
            tr = c2.text_input("RUT")
            tnac = c1.text_input("Nacionalidad", "Chilena")
            tdir = c2.text_input("Domicilio")
            tfec = st.date_input("Nacimiento", value=datetime(1990,1,1))
            
            st.markdown("#### Condiciones Contractuales")
            cc1, cc2 = st.columns(2)
            fini = cc1.date_input("Inicio Contrato", value=datetime.now())
            tcon = cc2.selectbox("Tipo", ["Indefinido", "Plazo Fijo", "Obra Faena"])
            func = st.text_area("Funciones Específicas", "Las propias del cargo y las encomendadas por la jefatura.")
            
            if st.form_submit_button("GENERAR CONTRATO (.DOCX)"):
                datos_form = {
                    **st.session_state.empresa, # Hereda todo del sidebar
                    "trab_nombre": tn, "trab_rut": tr, "trab_nacionalidad": tnac,
                    "trab_nacimiento": tfec, "trab_dir": tdir,
                    "cargo": st.session_state.cargo_actual if st.session_state.cargo_actual else "Trabajador",
                    "funciones": func,
                    "fecha_inicio": fini, "tipo_contrato": tcon,
                    "colacion": st.session_state.calculo_actual['No Imponibles'] // 2,
                    "movilizacion": st.session_state.calculo_actual['No Imponibles'] // 2
                }
                bio = generar_contrato_legal_word(st.session_state.calculo_actual, datos_form)
                st.download_button("⬇️ Descargar Documento Legal", bio.getvalue(), f"Contrato_{tn}.docx")
    else: st.info("Primero calcule un sueldo en Pestaña 1.")

# TAB 6: INDICADORES
with tabs[5]:
    st.header("Indicadores Oficiales")
    # Tablas Hardcoded para evitar errores de API
    st.subheader("Tasas AFP (Nov 2025)")
    st.table(pd.DataFrame({
        "AFP": ["Capital", "Cuprum", "Habitat", "PlanVital", "Provida", "Modelo", "Uno"],
        "Tasa": ["11,44%", "11,44%", "11,27%", "11,16%", "11,45%", "10,58%", "10,46%"]
    }))
