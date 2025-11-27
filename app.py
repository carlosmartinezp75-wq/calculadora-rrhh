import streamlit as st
import pandas as pd
import requests
import base64
import os

# --- 1. CONFIGURACIÓN ---
st.set_page_config(
    page_title="Calculadora Remuneraciones Pro",
    page_icon="🇨🇱",
    layout="wide"
)

# --- 2. ESTILOS VISUALES ---
def cargar_estilos():
    # Intento de cargar fondo
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
        css_fondo = ".stApp {background: linear-gradient(135deg, #fdfbfb 0%, #ebedee 100%);}"

    st.markdown(
        f"""
        <style>
        {css_fondo}
        
        .block-container {{
            background-color: rgba(255, 255, 255, 0.98);
            padding: 2.5rem;
            border-radius: 12px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }}
        
        h1, h2, h3, h4, p, label, .stMarkdown, .stSelectbox label, .stNumberInput label {{
            color: #004a99 !important;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }}
        
        [data-testid="stMetricValue"] {{
            color: #0056b3 !important;
            font-weight: 800;
        }}
        
        /* BOTÓN BLANCO SOBRE AZUL FORZADO */
        div.stButton > button {{
            background-color: #0056b3 !important;
            color: #ffffff !important;
            font-size: 16px !important;
            font-weight: bold !important;
            border: 1px solid #004a99;
            padding: 0.8rem 2rem;
            border-radius: 8px;
            width: 100%;
        }}
        div.stButton > button:hover {{
            background-color: #003366 !important;
            border: 1px solid white;
        }}
        
        /* ESTILO TABLAS */
        thead tr th:first-child {{display:none}}
        tbody th {{display:none}}
        
        #MainMenu, footer, header {{visibility: hidden;}}
        </style>
        """,
        unsafe_allow_html=True
    )

cargar_estilos()

# --- 3. FUNCIONES DE FORMATO ---
def fmt(valor):
    """Convierte número a texto con separador de miles: 1000 -> $1.000"""
    if valor is None or pd.isna(valor): return "$0"
    return "${:,.0f}".format(valor).replace(",", ".")

def obtener_indicadores():
    # Valores Noviembre 2025 PDF
    default_uf = 39643.59
    default_utm = 69542.0
    try:
        r = requests.get('https://mindicador.cl/api', timeout=2)
        d = r.json()
        return d['uf']['valor'], d['utm']['valor']
    except:
        return default_uf, default_utm

# --- 4. BARRA LATERAL (PANEL PREVIRED) ---
with st.sidebar:
    st.image("https://www.previred.com/wp-content/uploads/2021/01/logo-previred.png", width=140)
    st.title("Panel de Control")
    
    # Indicadores
    uf_live, utm_live = obtener_indicadores()
    
    col_ind1, col_ind2 = st.columns(2)
    with col_ind1:
        uf_input = st.number_input("UF ($)", value=uf_live, format="%.2f")
    with col_ind2:
        utm_input = st.number_input("UTM ($)", value=utm_live, format="%.2f")
    
    st.divider()
    
    st.subheader("Parámetros Legales")
    sueldo_min = st.number_input("Sueldo Mínimo", value=529000, step=1000)
    
    tope_imponible_uf = st.number_input("Tope AFP/Salud (UF)", value=87.8, step=0.1, help="Actualizado a 87,8 UF")
    tope_seguro_uf = st.number_input("Tope Seg. Cesantía (UF)", value=131.9, step=0.1, help="Actualizado a 131,9 UF")
    
    # Mostrar el tope de gratificación calculado
    tope_grat_mensual = (4.75 * sueldo_min) / 12
    st.caption(f"Tope Gratificación: {fmt(tope_grat_mensual)}")

# --- 5. MOTOR DE CÁLCULO ---
def calcular_reverso_exacto(liquido_obj, col, mov, tipo_con, afp_nom, salud_tipo, plan_uf, uf, utm, s_min, t_imp_uf, t_sc_uf):
    
    no_imp = col + mov
    liq_trib_meta = liquido_obj - no_imp
    
    if liq_trib_meta < s_min * 0.4: return None

    # Topes
    TOPE_GRAT = (4.75 * s_min) / 12
    TOPE_IMP_PESOS = t_imp_uf * uf
    TOPE_AFC_PESOS = t_sc_uf * uf
    
    # Tasas AFP (Nov 2025)
    TASAS_AFP = {"Capital": 1.44, "Cuprum": 1.44, "Habitat": 1.27, "Modelo": 0.58, "PlanVital": 1.16, "Provida": 1.45, "Uno": 0.49, "SIN AFP": 0.0}
    
    es_emp = (tipo_con == "Sueldo Empresarial")
    
    # Tasa AFP Trabajador
    comision = 0.0
    if afp_nom in TASAS_AFP: comision = TASAS_AFP[afp_nom]
    
    tasa_afp_trab = 0.10 + (comision/100)
    if afp_nom == "SIN AFP" or es_emp: tasa_afp_trab = 0.0

    # Tasas AFC
    tasa_afc_trab = 0.006 if (tipo_con == "Indefinido" and not es_emp) else 0.0
    
    # Tasas Empleador
    pct_sis = 0.0149
    pct_mut = 0.0093
    
    if es_emp:
        tasa_afc_emp = 0.024 # Asumimos aporte base para cálculo de costo
    else:
        tasa_afc_emp = 0.024 if tipo_con == "Indefinido" else (0.03 if tipo_con == "Plazo Fijo" else 0.0)

    # TABLA IMPUESTO (UTM)
    TABLA_IMP = [
        (13.5, 0.0, 0.0), (30.0, 0.04, 0.54), (50.0, 0.08, 1.74),
        (70.0, 0.135, 4.49), (90.0, 0.23, 11.14), (120.0, 0.304, 17.80),
        (310.0, 0.35, 23.32), (99999.0, 0.40, 38.82)
    ]

    min_b, max_b = 100000, liq_trib_meta * 2.5
    
    for _ in range(150):
        base_test = (min_b + max_b) / 2
        
        # Gratificación
        grat = min(base_test * 0.25, TOPE_GRAT)
        
        tot_imp = base_test + grat
        
        # Bases Topadas
        b_prev = min(tot_imp, TOPE_IMP_PESOS)
        b_afc = min(tot_imp, TOPE_AFC_PESOS)
        
        # Descuentos
        m_afp = int(b_prev * tasa_afp_trab)
        m_afc = int(b_afc * tasa_afc_trab)
        
        legal_7 = int(b_prev * 0.07)
        m_salud = 0
        rebaja_trib = 0
        
        if salud_tipo == "Fonasa (7%)":
            m_salud = legal_7
            rebaja_trib = legal_7
        else:
            val_plan = int(plan_uf * uf)
            m_salud = max(val_plan, legal_7)
            rebaja_trib = legal_7

        # Impuesto
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
            # Costos Empresa
            m_sis = int(b_prev * pct_sis)
            m_afc_e = int(b_afc * tasa_afc_emp)
            m_mut = int(b_prev * pct_mut)
            
            aportes = m_sis + m_afc_e + m_mut
            costo_fin = tot_imp + no_imp + aportes
            
            return {
                "Sueldo Base": int(base_test),
                "Gratificación": int(grat),
                "Total Imponible": int(tot_imp),
                "No Imponibles": int(no_imp),
                "TOTAL HABERES": int(tot_imp + no_imp),
                "AFP": m_afp, "Salud": m_salud, "AFC": m_afc, "Impuesto": imp,
                "Total Descuentos": m_afp + m_salud + m_afc + imp,
                "LÍQUIDO": int(liq_calc + no_imp),
                "Aportes Empresa": aportes,
                "COSTO TOTAL": int(costo_fin),
                "Base Tributable": int(base_trib)
            }
            break
        elif liq_calc < liq_trib_meta: min_b = base_test
        else: max_b = base_test
    return None

# --- 6. INTERFAZ PRINCIPAL ---
st.title("Calculadora de Remuneraciones")
st.markdown("#### Simulación Actualizada Noviembre 2025")

# FORMULARIO
c1, c2 = st.columns(2)
with c1:
    st.subheader("Objetivo Líquido")
    # Nota: Los inputs no muestran separadores al escribir, pero el cálculo sí.
    liq_target = st.number_input("Sueldo Líquido ($)", value=1000000, step=10000, format="%d")
    colacion = st.number_input("Colación ($)", value=50000, step=5000, format="%d")
    movilizacion = st.number_input("Movilización ($)", value=50000, step=5000, format="%d")

with c2:
    st.subheader("Configuración")
    tipo = st.selectbox("Contrato", ["Indefinido", "Plazo Fijo", "Sueldo Empresarial"])
    
    col_a, col_b = st.columns(2)
    with col_a:
        afp = st.selectbox("AFP", ["Capital", "Cuprum", "Habitat", "Modelo", "PlanVital", "Provida", "Uno", "SIN AFP"])
    with col_b:
        salud = st.selectbox("Salud", ["Fonasa (7%)", "Isapre (UF)"])
    
    plan = 0.0
    if salud == "Isapre (UF)":
        plan = st.number_input("Valor Plan (UF)", value=0.0, step=0.01)

st.markdown("---")

# BOTÓN DE CÁLCULO
if st.button("CALCULAR AHORA"):
    if (colacion + movilizacion) >= liq_target:
        st.error("Error: Haberes no imponibles superan al líquido.")
    else:
        res = calcular_reverso_exacto(
            liq_target, colacion, movilizacion, tipo, afp, salud, plan, 
            uf_input, utm_input, 
            sueldo_min, tope_imponible_uf, tope_seguro_uf
        )
        
        if res:
            st.success("✅ Cálculo Exitoso")
            
            # 1. TARJETAS (FORMATO MILES OK)
            k1, k2, k3 = st.columns(3)
            k1.metric("Total Imponible", fmt(res['Total Imponible']))
            k2.metric("Líquido a Pagar", fmt(res['LÍQUIDO']))
            k3.metric("Costo Empresa", fmt(res['COSTO TOTAL']), delta="Total", delta_color="inverse")
            
            st.markdown("---")
            
            # 2. TABLA RESULTADOS (FORZANDO STRING PARA MILES)
            col_res1, col_res2 = st.columns([1, 1])
            
            with col_res1:
                st.subheader("Detalle Liquidación")
                # Crear DataFrame con strings pre-formateados
                df_liq = pd.DataFrame([
                    ["HABERES", ""],
                    ["Sueldo Base", fmt(res['Sueldo Base'])],
                    ["Gratificación Legal", fmt(res['Gratificación'])],
                    ["TOTAL IMPONIBLE", fmt(res['Total Imponible'])],
                    ["Colación y Movilización", fmt(res['No Imponibles'])],
                    ["TOTAL HABERES", fmt(res['TOTAL HABERES'])],
                    ["", ""],
                    ["DESCUENTOS", ""],
                    [f"AFP ({afp})", fmt(-res['AFP'])],
                    [f"Salud ({salud})", fmt(-res['Salud'])],
                    ["Seguro Cesantía", fmt(-res['AFC'])],
                    ["Impuesto Único", fmt(-res['Impuesto'])],
                    ["TOTAL DESCUENTOS", fmt(-res['Total Descuentos'])],
                    ["", ""],
                    ["LÍQUIDO A PAGO", fmt(res['LÍQUIDO'])],
                    ["", ""],
                    ["COSTOS EMPRESA", ""],
                    ["Aportes Patronales", fmt(res['Aportes Empresa'])],
                    ["COSTO TOTAL REAL", fmt(res['COSTO TOTAL'])]
                ], columns=["Concepto", "Monto"])
                
                # st.table fuerza el renderizado de texto, manteniendo los puntos
                st.table(df_liq)
            
            with col_res2:
                # 3. TABLA IMPUESTO (GLOBAL COMPLEMENTARIO / 2DA CAT)
                st.subheader("Tabla Impuesto Único Utilizada")
                st.caption(f"Calculada sobre UTM: {fmt(utm_input)}")
                st.markdown(f"**Base Tributable:** {fmt(res['Base Tributable'])}")
                
                # Generar tabla de tramos dinámica con la UTM actual
                tramos = [
                    (13.5, 0.0, 0.0), (30.0, 0.04, 0.54), (50.0, 0.08, 1.74),
                    (70.0, 0.135, 4.49), (90.0, 0.23, 11.14), (120.0, 0.304, 17.80),
                    (310.0, 0.35, 23.32), (99999.0, 0.40, 38.82)
                ]
                
                data_imp = []
                base_trib = res['Base Tributable']
                
                for i, (limite, factor, rebaja) in enumerate(tramos):
                    desde = "$0" if i==0 else fmt(tramos[i-1][0] * utm_input)
                    hasta = fmt(limite * utm_input)
                    
                    # Marcar fila activa
                    check = ""
                    lim_anterior_pesos = 0 if i==0 else tramos[i-1][0] * utm_input
                    lim_actual_pesos = limite * utm_input
                    
                    if lim_anterior_pesos < base_trib <= lim_actual_pesos:
                        check = "👈 Aplicado"
                    
                    data_imp.append([
                        f"{desde} - {hasta}", 
                        f"{factor*100:.2f}%", 
                        fmt(rebaja * utm_input),
                        check
                    ])
                
                df_imp = pd.DataFrame(data_imp, columns=["Tramo Renta (Pesos)", "Factor", "Rebaja", "Estado"])
                st.table(df_imp)

        else:
            st.error("No se encontró solución matemática viable.")
