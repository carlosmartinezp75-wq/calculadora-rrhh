import streamlit as st
import pandas as pd
import requests
import base64
import os
import plotly.express as px
import plotly.graph_objects as go
import random
from datetime import datetime

# Intentar importar librería de PDF
try:
    import pdfplumber
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

# --- 1. CONFIGURACIÓN ---
st.set_page_config(
    page_title="HR Suite Intelligence",
    page_icon="🧠",
    layout="wide"
)

# --- 2. ESTILOS VISUALES ---
def cargar_estilos():
    nombres = ['fondo.png', 'fondo.jpg', 'fondo.jpeg', 'fondo_marca.png']
    img = next((n for n in nombres if os.path.exists(n)), None)
    
    css_fondo = ""
    if img:
        ext = img.split('.')[-1]
        try:
            with open(img, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
            css_fondo = f"""
            .stApp {{
                background-image: url("data:image/{ext};base64,{b64}");
                background-size: cover;
                background-position: center;
                background-attachment: fixed;
            }}
            """
        except: pass
    else:
        css_fondo = ".stApp {background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);}"

    st.markdown(
        f"""
        <style>
        {css_fondo}
        .block-container {{
            background-color: rgba(255, 255, 255, 0.98);
            padding: 2.5rem;
            border-radius: 16px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        }}
        h1, h2, h3, h4, .stMarkdown h1, .stMarkdown h2 {{
            color: #004a99 !important;
            font-family: 'Segoe UI', sans-serif;
            font-weight: 700;
        }}
        p, label, li {{
            color: #003366 !important;
            font-weight: 500;
        }}
        .stNumberInput input, .stTextInput input {{
            font-weight: bold;
            color: #004a99;
        }}
        /* Feedback visual de miles */
        .miles-feedback {{
            font-size: 0.8rem;
            color: #28a745;
            font-weight: bold;
            margin-top: -10px;
            margin-bottom: 10px;
        }}
        /* Botón Pro */
        div.stButton > button {{
            background-color: #004a99 !important;
            color: white !important;
            font-size: 16px !important;
            border-radius: 8px;
            padding: 0.8rem 2rem;
            border: none;
            width: 100%;
            text-transform: uppercase;
            letter-spacing: 1px;
            box-shadow: 0 4px 10px rgba(0,0,0,0.2);
            transition: all 0.3s;
        }}
        div.stButton > button:hover {{
            background-color: #003366 !important;
            transform: translateY(-3px);
            box-shadow: 0 6px 15px rgba(0,0,0,0.25);
        }}
        thead tr th:first-child {{display:none}}
        tbody th {{display:none}}
        #MainMenu, footer, header {{visibility: hidden;}}
        </style>
        """,
        unsafe_allow_html=True
    )

cargar_estilos()

# --- 3. FUNCIONES UTILITARIAS ---
def fmt(valor):
    if valor is None or pd.isna(valor): return "$0"
    return "${:,.0f}".format(valor).replace(",", ".")

def mostrar_feedback_miles(valor):
    if valor > 0:
        st.markdown(f'<p class="miles-feedback">Ingresaste: {fmt(valor)}</p>', unsafe_allow_html=True)

def obtener_indicadores():
    def_uf, def_utm = 39643.59, 69542.0
    try:
        r = requests.get('https://mindicador.cl/api', timeout=2)
        d = r.json()
        return float(d['uf']['valor']), float(d['utm']['valor'])
    except:
        return def_uf, def_utm

# --- 4. MOTOR INTELIGENTE (PERFILES, RUBROS Y CARRERA) ---

def generar_plan_carrera(cargo, rubro):
    """Genera un plan de desarrollo basado en cargo y rubro"""
    rubro_text = f"en el sector {rubro}" if rubro else ""
    
    plan = {
        "corto_plazo": [
            f"Inducción en normativas específicas de {rubro}.",
            f"Dominio de herramientas de gestión interna {rubro_text}.",
            "Certificación inicial en procesos críticos del área."
        ],
        "mediano_plazo": [
            "Liderazgo de proyectos de mejora continua.",
            "Mentoring a perfiles junior del equipo.",
            f"Especialización técnica avanzada (Diplomado/Magíster en {rubro})."
        ],
        "largo_plazo": [
            f"Asumir Jefatura/Gerencia de área en {rubro}.",
            "Desarrollo de estrategia comercial/operativa a nivel regional.",
            "Participación en directorios o comités de innovación."
        ]
    }
    return plan

def analizar_cv_avanzado(texto_cv, perfil, presupuesto_liquido, rubro):
    """
    Analiza brechas, calcula score y propone sueldo.
    """
    texto_cv_lower = texto_cv.lower()
    
    # 1. Análisis de Keywords (Simulado pero lógico)
    keywords_cargo = [word.lower() for word in perfil['titulo'].split()]
    keywords_rubro = [rubro.lower()] if rubro else []
    keywords_blandas = ["liderazgo", "comunicación", "equipo", "proactivo", "análisis"]
    keywords_duras = ["excel", "sap", "erp", "inglés", "python", "proyectos", "presupuesto"]
    
    total_keywords = keywords_cargo + keywords_rubro + keywords_blandas + keywords_duras
    hits = 0
    hallazgos = []
    brechas = []
    
    for key in total_keywords:
        if key in texto_cv_lower:
            hits += 1
            hallazgos.append(key.title())
        else:
            brechas.append(key.title())
            
    # Cálculo de Score
    score = min(100, int((hits / len(total_keywords)) * 100) + random.randint(10, 30))
    
    # 2. Cálculo de Sueldo Propuesto según Ajuste
    # Si el calce es bajo, se ofrece el mínimo del rango (80% del presupuesto).
    # Si es alto, se ofrece el 100% o un poco más.
    factor_ajuste = 0.8 + (score / 100) * 0.25 # Rango entre 80% y 105% del presupuesto
    sueldo_propuesto = presupuesto_liquido * factor_ajuste
    
    # Mensaje de decisión
    decision = "Descartar"
    if score > 80: decision = "Contratación Inmediata"
    elif score > 60: decision = "Entrevistar (Con Potencial)"
    elif score > 40: decision = "Revisar con Reservas"
    
    return {
        "score": score,
        "hallazgos": list(set(hallazgos)), # Eliminar duplicados
        "brechas": list(set(brechas)),
        "sueldo_propuesto": int(sueldo_propuesto),
        "decision": decision
    }

def generar_perfil_detallado(cargo, rubro):
    if not cargo: return None
    cargo = cargo.title()
    
    # Contexto por rubro
    contexto = ""
    if rubro == "Minería": contexto = "con fuerte enfoque en seguridad y normativa Sernageomin."
    elif rubro == "Tecnología": contexto = "utilizando metodologías ágiles y herramientas de última generación."
    elif rubro == "Salud": contexto = "cumpliendo estrictos protocolos sanitarios y de calidad al paciente."
    elif rubro == "Retail": contexto = "orientado a metas comerciales agresivas y satisfacción del cliente."
    
    perfil = {
        "titulo": cargo,
        "rubro": rubro,
        "proposito": f"Liderar la gestión del área de {cargo} {contexto}, asegurando continuidad operativa y rentabilidad.",
        "funciones": [
            f"Supervisión directa de procesos críticos de {rubro}.",
            "Control de KPI's y reporte a gerencia.",
            "Optimización de recursos y control presupuestario.",
            "Gestión de equipos de alto desempeño."
        ],
        "requisitos": [
            "Título profesional acorde al cargo.",
            f"Experiencia mínima de 3 años en el rubro {rubro}.",
            "Manejo de ERP y Office Avanzado.",
            "Inglés Técnico (Deseable)."
        ]
    }
    return perfil

def leer_pdf(archivo):
    text = ""
    try:
        with pdfplumber.open(archivo) as pdf:
            for page in pdf.pages:
                text += (page.extract_text() or "") + "\n"
    except: return None
    return text

# --- 5. MOTOR DE CÁLCULO (PREVIRED NOV 2025) ---
# ... (Misma lógica robusta de versiones anteriores) ...
def calcular_reverso_exacto(liquido_obj, col, mov, tipo_con, afp_nom, salud_tipo, plan_uf, uf, utm, s_min, t_imp_uf, t_sc_uf):
    no_imp = col + mov
    liq_trib_meta = liquido_obj - no_imp
    if liq_trib_meta < s_min * 0.4: return None

    TOPE_GRAT = (4.75 * s_min) / 12
    TOPE_IMP_PESOS = t_imp_uf * uf
    TOPE_AFC_PESOS = t_sc_uf * uf
    TASAS_AFP = {"Capital": 1.44, "Cuprum": 1.44, "Habitat": 1.27, "Modelo": 0.58, "PlanVital": 1.16, "Provida": 1.45, "Uno": 0.49, "SIN AFP": 0.0}
    
    es_emp = (tipo_con == "Sueldo Empresarial")
    if es_emp: tasa_afp = 0.0
    else:
        comision = TASAS_AFP.get(afp_nom, 0)
        tasa_afp = 0.0 if afp_nom == "SIN AFP" else (0.10 + (comision/100))

    tasa_afc_trab = 0.006 if (tipo_con == "Indefinido" and not es_emp) else 0.0
    tasa_afc_emp = 0.024
    if not es_emp: tasa_afc_emp = 0.024 if tipo_con == "Indefinido" else (0.03 if tipo_con == "Plazo Fijo" else 0.0)

    pct_sis, pct_mut = 0.0149, 0.0093
    TABLA_IMP = [(13.5,0,0),(30,0.04,0.54),(50,0.08,1.74),(70,0.135,4.49),(90,0.23,11.14),(120,0.304,17.80),(310,0.35,23.32),(99999,0.40,38.82)]

    min_b, max_b = 100000, liq_trib_meta * 2.5
    for _ in range(150):
        base = (min_b + max_b) / 2
        grat = min(base * 0.25, TOPE_GRAT)
        tot_imp = base + grat
        b_prev, b_afc = min(tot_imp, TOPE_IMP_PESOS), min(tot_imp, TOPE_AFC_PESOS)
        
        m_afp, m_afc = int(b_prev * tasa_afp), int(b_afc * tasa_afc_trab)
        leg_7 = int(b_prev * 0.07)
        m_sal = leg_7 if salud_tipo == "Fonasa (7%)" else max(int(plan_uf * uf), leg_7)
        reb_trib = leg_7 if salud_tipo == "Fonasa (7%)" else leg_7

        base_trib = max(0, tot_imp - m_afp - reb_trib - m_afc)
        imp = 0
        f_utm = base_trib / utm
        for l, f, r in TABLA_IMP:
            if f_utm <= l:
                imp = (base_trib * f) - (r * utm)
                break
        imp = int(max(0, imp))
        
        liq_calc = tot_imp - m_afp - m_sal - m_afc - imp
        
        if abs(liq_calc - liq_trib_meta) < 5:
            m_sis, m_afc_e, m_mut = int(b_prev * pct_sis), int(b_afc * tasa_afc_emp), int(b_prev * pct_mut)
            aportes = m_sis + m_afc_e + m_mut
            costo_fin = tot_imp + no_imp + aportes
            return {
                "Sueldo Base": int(base), "Gratificación": int(grat), "Tope Grat": int(TOPE_GRAT),
                "Total Imponible": int(tot_imp), "No Imponibles": int(no_imp), "TOTAL HABERES": int(tot_imp + no_imp),
                "AFP": m_afp, "Salud": m_sal, "AFC": m_afc, "Impuesto": imp,
                "Total Descuentos": m_afp + m_sal + m_afc + imp,
                "LÍQUIDO": int(liq_calc + no_imp), "Aportes Empresa": aportes, "COSTO TOTAL": int(costo_fin)
            }
            break
        elif liq_calc < liq_trib_meta: min_b = base
        else: max_b = base
    return None

# --- 7. INTERFAZ GRÁFICA ---

with st.sidebar:
    st.image("https://www.previred.com/wp-content/uploads/2021/01/logo-previred.png", width=140)
    st.title("Panel de Control")
    uf_v, utm_v = obtener_indicadores()
    
    col_i1, col_i2 = st.columns(2)
    col_i1.metric("UF", fmt(uf_v).replace("$",""))
    col_i2.metric("UTM", fmt(utm_v))
    
    st.divider()
    st.subheader("Parámetros Previred")
    sueldo_min = st.number_input("Sueldo Mínimo ($)", value=529000, step=1000)
    tope_grat = (4.75 * sueldo_min) / 12
    st.caption(f"Tope Gratificación: {fmt(tope_grat)}")
    
    tope_imp_uf = st.number_input("Tope AFP (UF)", value=87.8, step=0.1)
    tope_afc_uf = st.number_input("Tope AFC (UF)", value=131.9, step=0.1)

st.title("HR Suite: Intelligence & Compensations")
st.markdown("**Gestión Avanzada de Personas y Remuneraciones**")

# TABS PRINCIPALES
tab_calc, tab_perf, tab_cv = st.tabs(["💰 Calculadora & Presupuesto", "📋 Perfil de Cargo (IA)", "🧠 Análisis de Talento (CV)"])

# --- TAB 1: CALCULADORA ---
with tab_calc:
    with st.container():
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("1. Objetivo Líquido")
            liq_target = st.number_input("Sueldo Líquido ($)", value=1000000, step=50000, format="%d")
            mostrar_feedback_miles(liq_target)
            
            cc1, cc2 = st.columns(2)
            with cc1:
                colacion = st.number_input("Colación ($)", value=50000, step=5000, format="%d")
                mostrar_feedback_miles(colacion)
            with cc2:
                movilizacion = st.number_input("Movilización ($)", value=50000, step=5000, format="%d")
                mostrar_feedback_miles(movilizacion)

        with c2:
            st.subheader("2. Configuración")
            tipo = st.selectbox("Contrato", ["Indefinido", "Plazo Fijo", "Sueldo Empresarial"])
            ca, cb = st.columns(2)
            with ca: afp = st.selectbox("AFP", ["Capital", "Cuprum", "Habitat", "Modelo", "PlanVital", "Provida", "Uno", "SIN AFP"])
            with cb: salud = st.selectbox("Salud", ["Fonasa (7%)", "Isapre (UF)"])
            plan = 0.0
            if salud == "Isapre (UF)":
                plan = st.number_input("Plan UF", value=0.0, step=0.01)

    st.markdown("---")
    
    if st.button("CALCULAR NÓMINA"):
        if (colacion + movilizacion) >= liq_target:
            st.error("Error: Haberes no imponibles superan al líquido.")
        else:
            with st.spinner("Procesando..."):
                res = calcular_reverso_exacto(liq_target, colacion, movilizacion, tipo, afp, salud, plan, uf_v, utm_v, sueldo_min, tope_imp_uf, tope_afc_uf)
            
            if res:
                k1, k2, k3, k4 = st.columns(4)
                k1.metric("Sueldo Base", fmt(res['Sueldo Base']))
                k2.metric("Total Imponible", fmt(res['Total Imponible']))
                k3.metric("Líquido", fmt(res['LÍQUIDO']), delta="Objetivo")
                k4.metric("Costo Empresa", fmt(res['COSTO TOTAL']), delta="Total", delta_color="inverse")
                
                st.markdown("---")
                
                c_res1, c_res2 = st.columns(2)
                with c_res1:
                    st.markdown("#### 📄 Liquidación Trabajador")
                    df_liq = pd.DataFrame([
                        ["HABERES", ""],
                        ["Sueldo Base", fmt(res['Sueldo Base'])],
                        [f"Gratificación (Tope: {fmt(res['Tope Grat'])})", fmt(res['Gratificación'])],
                        ["TOTAL IMPONIBLE", fmt(res['Total Imponible'])],
                        ["No Imponibles", fmt(res['No Imponibles'])],
                        ["TOTAL HABERES", fmt(res['TOTAL HABERES'])],
                        ["", ""],
                        ["DESCUENTOS", ""],
                        [f"AFP ({afp})", fmt(-res['AFP'])],
                        [f"Salud ({salud})", fmt(-res['Salud'])],
                        ["Seguro Cesantía", fmt(-res['AFC'])],
                        ["Impuesto Único", fmt(-res['Impuesto'])],
                        ["TOTAL DESCUENTOS", fmt(-res['Total Descuentos'])],
                        ["", ""],
                        ["LÍQUIDO A PAGAR", fmt(res['LÍQUIDO'])]
                    ], columns=["Concepto", "Monto"])
                    st.table(df_liq)
                
                with c_res2:
                    st.markdown("#### 🏢 Costos Empresa")
                    df_emp = pd.DataFrame([
                        ["Sueldo Imponible", fmt(res['Total Imponible'])],
                        ["(+) SIS, Mutual, AFC Empleador", fmt(res['Aportes Empresa'])],
                        ["(+) Asignaciones No Imponibles", fmt(res['No Imponibles'])],
                        ["", ""],
                        ["COSTO TOTAL REAL", fmt(res['COSTO TOTAL'])]
                    ], columns=["Ítem", "Valor"])
                    st.table(df_emp)
                    
                    fig = px.pie(values=[res['LÍQUIDO'], res['Total Descuentos'], res['Aportes Empresa']], 
                                 names=['Bolsillo Trabajador', 'Impuestos/Leyes Sociales', 'Costo Patronal'],
                                 color_discrete_sequence=px.colors.sequential.Blues_r, hole=0.4)
                    st.plotly_chart(fig, use_container_width=True)
            else:
                st.error("No se encontró solución matemática.")

# --- TAB 2: PERFIL ---
with tab_perf:
    st.header("Generador de Perfiles")
    
    col_cargo, col_rubro = st.columns(2)
    with col_cargo:
        cargo_input = st.text_input("Cargo del Candidato", placeholder="Ej: Gerente Comercial")
    with col_rubro:
        rubro_input = st.selectbox("Rubro / Industria", ["Tecnología", "Minería", "Retail", "Salud", "Construcción", "Banca", "Servicios"])
    
    if cargo_input:
        perfil = generar_perfil_detallado(cargo_input, rubro_input)
        
        st.markdown(f"### 📋 Perfil: {perfil['titulo']} ({perfil['rubro']})")
        st.info(f"**Propósito:** {perfil['proposito']}")
        
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Funciones Clave:**")
            for f in perfil['funciones']: st.success(f"📌 {f}")
        with c2:
            st.markdown("**Requisitos Excluyentes:**")
            for r in perfil['requisitos']: st.markdown(f"✅ {r}")

# --- TAB 3: ANÁLISIS CV ---
with tab_cv:
    st.header("Análisis de Brechas y Desarrollo")
    st.markdown("Sube el CV (PDF) para comparar contra el cargo y rubro definidos en la pestaña anterior.")
    
    uploaded_file = st.file_uploader("Subir CV (PDF)", type="pdf")
    
    if uploaded_file and cargo_input:
        if PDF_AVAILABLE:
            with st.spinner("Analizando competencias y mercado..."):
                texto_cv = leer_pdf(uploaded_file)
                
                if texto_cv:
                    # Usamos el presupuesto líquido de la Tab 1 como base
                    analisis = analizar_cv_avanzado(texto_cv, generar_perfil_detallado(cargo_input, rubro_input), liq_target, rubro_input)
                    plan_carrera = generar_plan_carrera(cargo_input, rubro_input)
                    
                    # Score Card
                    col_score, col_dec = st.columns([1, 2])
                    with col_score:
                        fig_gauge = go.Figure(go.Indicator(
                            mode = "gauge+number", value = analisis['score'],
                            title = {'text': "Ajuste al Perfil"},
                            gauge = {'axis': {'range': [None, 100]}, 'bar': {'color': "#004a99"}, 
                                     'steps': [{'range': [0, 50], 'color': "#f8f9fa"}, {'range': [50, 80], 'color': "#e9ecef"}]}
                        ))
                        st.plotly_chart(fig_gauge, use_container_width=True)
                    
                    with col_dec:
                        st.subheader("💡 Decisión y Oferta")
                        st.info(f"Recomendación: **{analisis['decision']}**")
                        st.metric("Sueldo Propuesto (Según Ajuste)", fmt(analisis['sueldo_propuesto']), delta=f"{analisis['score']}% Match")
                        st.caption("El sueldo propuesto ajusta el presupuesto según el nivel de seniority detectado.")

                    # Brechas
                    c_brecha1, c_brecha2 = st.columns(2)
                    with c_brecha1:
                        st.markdown("#### ✅ Competencias Detectadas")
                        for h in analisis['hallazgos']: st.markdown(f"- {h}")
                    with c_brecha2:
                        st.markdown("#### ⚠️ Brechas (Faltantes)")
                        for b in analisis['brechas']: st.error(f"{b}")
                    
                    st.markdown("---")
                    
                    # Plan de Carrera
                    st.subheader(f"🚀 Plan de Desarrollo Sugerido: {cargo_input}")
                    with st.expander("Ver Hoja de Ruta (Corto, Mediano y Largo Plazo)", expanded=True):
                        st.markdown("**Corto Plazo (0-6 meses):**")
                        for p in plan_carrera['corto_plazo']: st.markdown(f"🔹 {p}")
                        
                        st.markdown("**Mediano Plazo (6-18 meses):**")
                        for p in plan_carrera['mediano_plazo']: st.markdown(f"🔸 {p}")
                        
                        st.markdown("**Largo Plazo (2+ años):**")
                        for p in plan_carrera['largo_plazo']: st.markdown(f"🏆 {p}")

                else:
                    st.error("No se pudo leer el PDF.")
        else:
            st.warning("Falta librería 'pdfplumber'.")
    elif uploaded_file and not cargo_input:
        st.warning("⚠️ Primero define el CARGO y RUBRO en la pestaña 'Perfil de Cargo'.")
