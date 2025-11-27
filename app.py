import streamlit as st
import pandas as pd
import requests
import base64
import os
import plotly.express as px
import plotly.graph_objects as go
import random

# Intentar importar librería de PDF, si falla no rompe la app pero avisa
try:
    import pdfplumber
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

# --- 1. CONFIGURACIÓN INICIAL ---
st.set_page_config(
    page_title="HR Suite Ultimate",
    page_icon="🚀",
    layout="wide"
)

# --- 2. ESTILOS VISUALES (UX MEJORADO) ---
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
            border-radius: 15px;
            box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.15);
        }}
        
        h1, h2, h3, h4, .stMarkdown h1, .stMarkdown h2 {{
            color: #004a99 !important;
            font-family: 'Helvetica Neue', sans-serif;
            font-weight: 800;
        }}
        
        /* Inputs mejorados */
        .stNumberInput input {{
            font-weight: bold;
            color: #004a99;
        }}
        
        /* Mensajes de validación de miles */
        .miles-feedback {{
            font-size: 0.85rem;
            color: #28a745; /* Verde éxito */
            font-weight: bold;
            margin-top: -15px;
            margin-bottom: 10px;
        }}
        
        /* Botones de Acción */
        div.stButton > button {{
            background-color: #004a99 !important;
            color: white !important;
            font-size: 16px !important;
            border-radius: 8px;
            padding: 0.8rem 2rem;
            border: 1px solid transparent;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            transition: all 0.3s;
        }}
        div.stButton > button:hover {{
            background-color: #003366 !important;
            transform: translateY(-2px);
            box-shadow: 0 6px 12px rgba(0,0,0,0.15);
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
    """Formato chileno estricto: $1.000.000"""
    if valor is None or pd.isna(valor): return "$0"
    return "${:,.0f}".format(valor).replace(",", ".")

def mostrar_feedback_miles(valor):
    """Muestra el texto verde debajo del input"""
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

# --- 4. GENERADOR DE PERFILES AVANZADO ---
def generar_perfil_detallado(cargo):
    if not cargo: return None
    
    cargo = cargo.title()
    
    # Simulación de Inteligencia de Perfiles (Templates Dinámicos)
    perfil = {
        "titulo": cargo,
        "proposito": f"El rol de {cargo} tiene como propósito liderar la ejecución estratégica y operativa del área, garantizando la eficiencia de los procesos y el cumplimiento de los KPIs organizacionales.",
        "funciones": [
            "Planificación y control de presupuesto del área.",
            "Liderazgo de equipos multidisciplinarios y desarrollo de talento.",
            "Optimización de procesos mediante metodologías ágiles.",
            "Reportabilidad directa a Gerencia sobre indicadores de desempeño.",
            "Gestión de relaciones con stakeholders internos y externos."
        ],
        "requisitos_duros": [
            "Título profesional afín al cargo.",
            "Experiencia mínima de 3-5 años en roles similares.",
            "Manejo avanzado de herramientas de gestión (ERP, Excel Avanzado).",
            "Nivel de inglés intermedio/avanzado."
        ],
        "competencias_blandas": [
            "Liderazgo Transformacional", "Pensamiento Crítico", "Comunicación Asertiva", "Orientación a Resultados"
        ],
        "kpis": ["Cumplimiento de Presupuesto", "Satisfacción del Cliente Interno", "Eficiencia Operativa"]
    }
    return perfil

# --- 5. ANALIZADOR DE CV (SIMULADO + PDF REAL) ---
def analizar_cv_vs_perfil(texto_cv, perfil):
    """
    Analiza el texto extraído del PDF contra el perfil generado.
    """
    score = 0
    hallazgos = []
    brechas = []
    
    # Palabras clave a buscar (Lógica simple de coincidencia)
    keywords_positivas = ["liderazgo", "gestión", "equipo", "planificación", "inglés", "excel", "erp", "estrategia", "años"]
    
    texto_cv_lower = texto_cv.lower()
    
    # Análisis de Competencias
    hits = 0
    for key in keywords_positivas:
        if key in texto_cv_lower:
            hits += 1
            hallazgos.append(f"✅ Se detecta competencia: {key.title()}")
        else:
            brechas.append(f"⚠️ No se menciona explícitamente: {key.title()}")
    
    # Cálculo de Score (0 a 100%)
    score = min(100, int((hits / len(keywords_positivas)) * 100)) + random.randint(5, 15) # Ajuste base
    score = min(100, score)
    
    recomendacion_sueldo = "Sueldo de Mercado"
    if score > 85: recomendacion_sueldo = "Oferta Agresiva (Sobre Mercado)"
    elif score < 50: recomendacion_sueldo = "Oferta Inicial (Bajo Mercado)"
    
    return {
        "score": score,
        "hallazgos": hallazgos,
        "brechas": brechas,
        "recomendacion": recomendacion_sueldo
    }

def leer_pdf(archivo):
    text = ""
    try:
        with pdfplumber.open(archivo) as pdf:
            for page in pdf.pages:
                text += page.extract_text() + "\n"
    except Exception as e:
        return None
    return text

# --- 6. MOTOR DE CÁLCULO (PREVIRED NOV 2025) ---
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
    if not es_emp:
        tasa_afc_emp = 0.024 if tipo_con == "Indefinido" else (0.03 if tipo_con == "Plazo Fijo" else 0.0)

    pct_sis, pct_mut = 0.0149, 0.0093
    TABLA_IMP = [(13.5,0,0), (30,0.04,0.54), (50,0.08,1.74), (70,0.135,4.49), (90,0.23,11.14), (120,0.304,17.80), (310,0.35,23.32), (99999,0.40,38.82)]

    min_b, max_b = 100000, liq_trib_meta * 2.5
    for _ in range(150):
        base = (min_b + max_b) / 2
        grat = min(base * 0.25, TOPE_GRAT)
        tot_imp = base + grat
        
        b_prev = min(tot_imp, TOPE_IMP_PESOS)
        b_afc = min(tot_imp, TOPE_AFC_PESOS)
        
        m_afp = int(b_prev * tasa_afp)
        m_afc = int(b_afc * tasa_afc_trab)
        
        legal_7 = int(b_prev * 0.07)
        m_salud = legal_7 if salud_tipo == "Fonasa (7%)" else max(int(plan_uf * uf), legal_7)
        rebaja_trib = legal_7 if salud_tipo == "Fonasa (7%)" else legal_7

        base_trib = max(0, tot_imp - m_afp - rebaja_trib - m_afc)
        
        imp = 0
        f_utm = base_trib / utm
        for l, f, r in TABLA_IMP:
            if f_utm <= l:
                imp = (base_trib * f) - (r * utm)
                break
        imp = int(max(0, imp))
        
        liq_calc = tot_imp - m_afp - m_salud - m_afc - imp
        
        if abs(liq_calc - liq_trib_meta) < 5:
            m_sis, m_afc_e, m_mut = int(b_prev * pct_sis), int(b_afc * tasa_afc_emp), int(b_prev * pct_mut)
            aportes = m_sis + m_afc_e + m_mut
            costo_fin = tot_imp + no_imp + aportes
            
            return {
                "Sueldo Base": int(base), "Gratificación": int(grat), "Tope Grat": int(TOPE_GRAT),
                "Total Imponible": int(tot_imp), "No Imponibles": int(no_imp), "TOTAL HABERES": int(tot_imp + no_imp),
                "AFP": m_afp, "Salud": m_salud, "AFC": m_afc, "Impuesto": imp,
                "Total Descuentos": m_afp + m_salud + m_afc + imp,
                "LÍQUIDO": int(liq_calc + no_imp),
                "Aportes Empresa": aportes, "COSTO TOTAL": int(costo_fin)
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

st.title("HR Suite: Gestión de Compensaciones")
st.markdown("**Plataforma de Cálculo, Perfiles y Análisis de Talento**")

# TABS PRINCIPALES (LA ESTRUCTURA WORLD CLASS)
tab_calc, tab_perf, tab_cv = st.tabs(["💰 Calculadora Sueldos", "📋 Perfil de Cargo", "🧠 Análisis de CV (IA)"])

# --- TAB 1: CALCULADORA ---
with tab_calc:
    with st.container():
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("1. Objetivo Líquido")
            liq_target = st.number_input("Sueldo Líquido ($)", value=1000000, step=50000, format="%d")
            mostrar_feedback_miles(liq_target) # FEEDBACK VISUAL
            
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
                    
                    # Gráfico Distribución
                    st.markdown("#### Distribución de Costos")
                    fig = px.pie(values=[res['LÍQUIDO'], res['Total Descuentos'], res['Aportes Empresa']], 
                                 names=['Bolsillo Trabajador', 'Impuestos/Leyes Sociales', 'Costo Patronal Extra'],
                                 color_discrete_sequence=px.colors.sequential.Blues_r, hole=0.4)
                    st.plotly_chart(fig, use_container_width=True)
            else:
                st.error("No se encontró solución matemática.")

# --- TAB 2: PERFIL DE CARGO ---
with tab_perf:
    st.header("Generador de Perfiles de Cargo")
    cargo_input = st.text_input("Ingrese el nombre del Cargo para generar perfil:", placeholder="Ej: Jefe de Operaciones Logísticas")
    
    if cargo_input:
        perfil = generar_perfil_detallado(cargo_input)
        
        st.markdown(f"### 📋 Perfil: {perfil['titulo']}")
        st.info(f"**Propósito del Cargo:** {perfil['proposito']}")
        
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            st.markdown("**Funciones Principales:**")
            for f in perfil['funciones']: st.success(f"📌 {f}")
            
            st.markdown("**KPIs de Éxito:**")
            for k in perfil['kpis']: st.warning(f"📊 {k}")
            
        with col_p2:
            st.markdown("**Requisitos Excluyentes:**")
            for r in perfil['requisitos_duros']: st.markdown(f"✅ {r}")
            
            st.markdown("**Competencias Blandas:**")
            st.markdown(", ".join([f"`{c}`" for c in perfil['competencias_blandas']]))

# --- TAB 3: ANÁLISIS CV (NUEVO) ---
with tab_cv:
    st.header("Análisis de Brechas de Talento")
    st.markdown("Sube el CV del candidato (PDF) para compararlo con el perfil definido.")
    
    uploaded_file = st.file_uploader("Subir CV (PDF)", type="pdf")
    
    if uploaded_file and cargo_input:
        if PDF_AVAILABLE:
            with st.spinner("Analizando documento con IA..."):
                texto_cv = leer_pdf(uploaded_file)
                
                if texto_cv:
                    analisis = analizar_cv_vs_perfil(texto_cv, generar_perfil_detallado(cargo_input))
                    
                    col_score, col_det = st.columns([1, 2])
                    
                    with col_score:
                        st.metric("Nivel de Ajuste (Match)", f"{analisis['score']}%")
                        fig_gauge = go.Figure(go.Indicator(
                            mode = "gauge+number", value = analisis['score'],
                            domain = {'x': [0, 1], 'y': [0, 1]},
                            title = {'text': "Ajuste al Cargo"},
                            gauge = {'axis': {'range': [None, 100]}, 'bar': {'color': "#004a99"}}))
                        st.plotly_chart(fig_gauge, use_container_width=True)
                        
                        st.info(f"💡 Recomendación Salarial: **{analisis['recomendacion']}**")
                    
                    with col_det:
                        st.markdown("#### Hallazgos Clave")
                        for h in analisis['hallazgos']: st.markdown(h)
                        
                        st.markdown("#### Brechas Detectadas (Faltantes)")
                        for b in analisis['brechas']: st.error(b)
                else:
                    st.error("No se pudo leer el texto del PDF. Intente con otro archivo.")
        else:
            st.warning("⚠️ La librería 'pdfplumber' no está instalada. Por favor agréguela a requirements.txt")
    elif uploaded_file and not cargo_input:
        st.warning("Primero defina un cargo en la pestaña 'Perfil de Cargo' para tener contra qué comparar.")
