import streamlit as st
import pandas as pd
import requests
import base64

# --- 1. CONFIGURACIÓN INICIAL (OBLIGATORIO PRIMERA LÍNEA) ---
st.set_page_config(
    page_title="Calculadora Remuneraciones",
    page_icon="🏢",
    layout="centered"
)

# --- 2. GESTIÓN DEL FONDO E IMAGEN ---
def cargar_fondo_seguro():
    """
    Intenta cargar fondo.png. Si falla, usa un degradado azul.
    No rompe la app si falta la imagen.
    """
    archivo_imagen = 'fondo.png' # <--- ASEGÚRATE QUE EN GITHUB SE LLAME ASÍ
    
    try:
        with open(archivo_imagen, "rb") as f:
            data = f.read()
            bin_str = base64.b64encode(data).decode()
        
        # Si encuentra la imagen, la pone
        st.markdown(
            f"""
            <style>
            .stApp {{
                background-image: url("data:image/png;base64,{bin_str}");
                background-size: cover;
                background-position: center;
                background-attachment: fixed;
            }}
            </style>
            """,
            unsafe_allow_html=True
        )
    except FileNotFoundError:
        # SI NO LA ENCUENTRA, USA ESTE FONDO AZUL EN VEZ DE QUEDAR EN BLANCO
        st.markdown(
            """
            <style>
            .stApp {
                background: linear-gradient(135deg, #e3f2fd 0%, #ffffff 100%);
            }
            </style>
            """,
            unsafe_allow_html=True
        )
        st.toast("⚠️ No detecté 'fondo.png', usando modo estándar.", icon="ℹ️")

# --- 3. ESTILOS VISUALES (BOTONES Y TEXTOS) ---
def cargar_estilos_css():
    st.markdown(
        """
        <style>
        /* Contenedor principal estilo tarjeta */
        .block-container {
            background-color: rgba(255, 255, 255, 0.95);
            padding: 2rem;
            border-radius: 15px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.1);
            margin-top: 1rem;
        }
        /* Textos Corporativos */
        h1, h2, h3, p, div, label {
            color: #004a99 !important;
            font-family: 'Arial', sans-serif;
        }
        /* Métricas */
        [data-testid="stMetricValue"] {
            color: #0056b3 !important;
            font-weight: 700;
        }
        /* Botón Calcular */
        div.stButton > button {
            background-color: #0056b3;
            color: white;
            width: 100%;
            border-radius: 8px;
            padding: 0.8rem;
            font-size: 16px;
            font-weight: bold;
            border: none;
        }
        div.stButton > button:hover {
            background-color: #003d80;
            color: #ffffff;
        }
        /* Ocultar menú de streamlit */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        </style>
        """,
        unsafe_allow_html=True
    )

# --- EJECUTAR CARGA VISUAL ---
cargar_fondo_seguro()
cargar_estilos_css()

# --- 4. LÓGICA DE CÁLCULO (NO TOCAR) ---
def fmt(valor):
    if valor is None or pd.isna(valor): return "$0"
    return "${:,.0f}".format(valor).replace(",", ".")

def obtener_indicadores():
    try:
        r = requests.get('https://mindicador.cl/api', timeout=2)
        d = r.json()
        return d['uf']['valor'], d['utm']['valor']
    except:
        return 38000.0, 67000.0

def calcular_simulacion(liquido_obj, col, mov, tipo, afp_nom, salud_tipo, plan_uf, uf, utm):
    no_imp = col + mov
    liq_buscado = liquido_obj - no_imp
    if liq_buscado < 0: return None

    TASAS_AFP = {"Capital": 1.44, "Cuprum": 1.44, "Habitat": 1.27, "Modelo": 0.58, "PlanVital": 1.16, "Provida": 1.45, "Uno": 0.49, "SIN AFP": 0.0}
    tasa_afp = 0.10 + (TASAS_AFP.get(afp_nom, 0)/100)
    if afp_nom == "SIN AFP": tasa_afp = 0.0

    es_emp = (tipo == "Sueldo Empresarial")
    tasa_afc_trab = 0.006 if tipo == "Indefinido" else 0.0
    tasa_afc_emp = 0.024 if tipo == "Indefinido" else (0.03 if tipo == "Plazo Fijo" else 0.0)

    tope_afp_pesos = 84.3 * uf
    tope_sc_pesos = 126.6 * uf

    # Búsqueda Binaria
    min_b, max_b = liq_buscado, liq_buscado * 2.2
    bruto_final = 0
    
    TABLA_IMP = [(13.5,0,0), (30,0.04,0.54), (50,0.08,1.08), (70,0.135,2.73), (90,0.23,7.48), (120,0.304,12.66), (99999,0.35,16.80)]

    for _ in range(100):
        bruto = (min_b + max_b) / 2
        base_afp = min(bruto, tope_afp_pesos)
        base_sc = min(bruto, tope_sc_pesos)

        m_afp = int(base_afp * tasa_afp)
        m_afc_trab = int(base_sc * tasa_afc_trab)
        
        legal_7 = int(base_afp * 0.07)
        m_salud = legal_7 if salud_tipo == "Fonasa (7%)" else max(int(plan_uf * uf), legal_7)

        base_trib = max(0, bruto - m_afp - legal_7 - m_afc_trab)
        
        imp = 0
        b_utm = base_trib / utm
        for l, f, r in TABLA_IMP:
            if b_utm <= l:
                imp = (base_trib * f) - (r * utm)
                break
        imp = int(max(0, imp))

        liq_calc = bruto - m_afp - m_salud - m_afc_trab - imp
        
        if abs(liq_calc - liq_buscado) < 5:
            bruto_final = bruto
            m_sis = int(base_afp * 0.0149) if not es_emp else 0
            m_afc_e = int(base_sc * tasa_afc_emp)
            m_mut = int(base_afp * 0.0093) if not es_emp else 0
            
            sueldo_base = int(bruto_final / 1.25)
            grat = int(bruto_final - sueldo_base)
            
            return {
                "Sueldo Base": sueldo_base,
                "Gratificación": grat,
                "Total Imponible": int(bruto_final),
                "No Imponibles": int(no_imp),
                "TOTAL HABERES": int(bruto_final + no_imp),
                "AFP": m_afp, "Salud": m_salud, "AFC": m_afc_trab, "Impuesto": imp,
                "Total Descuentos": m_afp + m_salud + m_afc_trab + imp,
                "LÍQUIDO": int(liq_calc + no_imp),
                "Aportes Empresa": m_sis + m_afc_e + m_mut,
                "COSTO TOTAL": int(bruto_final + no_imp + m_sis + m_afc_e + m_mut)
            }
            break
        elif liq_calc < liq_buscado: min_b = bruto
        else: max_b = bruto
    return None

# --- 5. INTERFAZ GRÁFICA ---
st.title("Calculadora de Remuneraciones")

# Indicadores en la barra lateral
with st.sidebar:
    st.header("Indicadores")
    uf, utm = obtener_indicadores()
    st.metric("UF", fmt(uf).replace("$",""))
    st.metric("UTM", fmt(utm))
    st.caption("Fuente: Mindicador.cl")

# Formulario
st.markdown("### 1. Datos del Trabajador")
col1, col2 = st.columns(2)
with col1:
    liq_target = st.number_input("Líquido a Pagar ($)", value=1000000, step=10000, format="%d")
    colacion = st.number_input("Colación ($)", value=50000, step=5000, format="%d")
with col2:
    movilizacion = st.number_input("Movilización ($)", value=50000, step=5000, format="%d")

st.markdown("### 2. Configuración")
c1, c2, c3 = st.columns(3)
with c1:
    tipo = st.selectbox("Contrato", ["Indefinido", "Plazo Fijo", "Sueldo Empresarial"])
with c2:
    afp = st.selectbox("AFP", ["Capital", "Cuprum", "Habitat", "Modelo", "PlanVital", "Provida", "Uno", "SIN AFP"])
with c3:
    salud = st.selectbox("Salud", ["Fonasa (7%)", "Isapre (UF)"])
    plan = 0.0
    if salud == "Isapre (UF)":
        plan = st.number_input("Plan UF", value=0.0, step=0.1)

st.markdown("---")

if st.button("CALCULAR AHORA"):
    if (colacion + movilizacion) >= liq_target:
        st.error("Error: Los haberes no imponibles superan al líquido.")
    else:
        res = calcular_simulacion(liq_target, colacion, movilizacion, tipo, afp, salud, plan, uf, utm)
        if res:
            st.success("Cálculo Exitoso")
            k1, k2, k3 = st.columns(3)
            k1.metric("Bruto", fmt(res['Total Imponible']))
            k2.metric("Líquido", fmt(res['LÍQUIDO']))
            k3.metric("Costo Empresa", fmt(res['COSTO TOTAL']), delta="Total", delta_color="inverse")

            st.subheader("Detalle Liquidación")
            
            # Tabla manual para control total del diseño
            df = pd.DataFrame([
                ["HABERES", ""],
                ["Sueldo Base", fmt(res['Sueldo Base'])],
                ["Gratificación (25%)", fmt(res['Gratificación'])],
                ["Total Imponible", fmt(res['Total Imponible'])],
                ["No Imponibles", fmt(res['No Imponibles'])],
                ["TOTAL HABERES", fmt(res['TOTAL HABERES'])],
                ["", ""],
                ["DESCUENTOS", ""],
                ["AFP", fmt(-res['AFP'])],
                ["Salud", fmt(-res['Salud'])],
                ["Seguro Cesantía", fmt(-res['AFC'])],
                ["Impuesto Único", fmt(-res['Impuesto'])],
                ["TOTAL DESCUENTOS", fmt(-res['Total Descuentos'])],
                ["", ""],
                ["LÍQUIDO A PAGAR", fmt(res['LÍQUIDO'])],
                ["", ""],
                ["COSTOS EMPRESA", ""],
                ["Aportes Patronales", fmt(res['Aportes Empresa'])],
                ["COSTO TOTAL", fmt(res['COSTO TOTAL'])]
            ], columns=["Item", "Monto"])
            
            st.table(df)
        else:
            st.error("No se encontró solución matemática.")
