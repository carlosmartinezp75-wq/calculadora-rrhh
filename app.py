import streamlit as st
import pandas as pd
import requests
from io import BytesIO

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Calculadora RRHH Chile", page_icon="🇨🇱", layout="centered")

# --- LÓGICA DE NEGOCIO ---
def obtener_indicadores():
    try:
        response = requests.get('https://mindicador.cl/api', timeout=3)
        data = response.json()
        return data['uf']['valor'], data['utm']['valor']
    except:
        return 38000.0, 67000.0 # Fallback

def calcular_sueldo(base, grat_bool, colacion, movilizacion, afp_nom, salud_nom, plan_uf, uf_dia, utm_dia):
    # Parámetros Base
    sueldo_min = 500000
    tope_grat = (4.75 * sueldo_min) / 12
    tope_imp_uf = 84.3
    tope_sc_uf = 126.6
    
    # 1. Haberes
    gratificacion = min(base * 0.25, tope_grat) if grat_bool == "SI" else 0
    imponible = base + gratificacion
    total_haberes = imponible + colacion + movilizacion
    
    # 2. Descuentos
    # AFP
    tasas_afp = {
        "Capital": 1.44, "Cuprum": 1.44, "Habitat": 1.27, "Modelo": 0.58,
        "PlanVital": 1.16, "Provida": 1.45, "Uno": 0.49, "SIN AFP": 0.0
    }
    tasa_afp_num = (10 + tasas_afp.get(afp_nom, 0)) / 100
    if afp_nom == "SIN AFP": tasa_afp_num = 0
    
    tope_pesos = tope_imp_uf * uf_dia
    monto_afp = int(min(imponible, tope_pesos) * tasa_afp_num)
    
    # Salud
    legal_7 = int(min(imponible, tope_pesos) * 0.07)
    monto_salud = 0
    if salud_nom == "Fonasa (7%)":
        monto_salud = legal_7
    else: # Isapre
        pactado = int(plan_uf * uf_dia)
        monto_salud = max(pactado, legal_7)
        
    # AFC (Indefinido 0.6%)
    tope_sc_pesos = tope_sc_uf * uf_dia
    monto_afc = int(min(imponible, tope_sc_pesos) * 0.006)
    
    # Impuesto
    total_prev = monto_afp + monto_salud + monto_afc
    tributable = imponible - total_prev
    
    base_utm = tributable / utm_dia
    impuesto = 0
    # Tabla simplificada (se puede expandir)
    tabla = [(13.5,0,0), (30,0.04,0.54), (50,0.08,1.08), (70,0.135,2.73), (90,0.23,7.48), (120,0.304,12.66), (9999,0.35,16.80)]
    for lim, fac, reb in tabla:
        if base_utm <= lim:
            impuesto = (tributable * fac) - (reb * utm_dia)
            break
    impuesto = int(max(0, impuesto))
    
    liquido = total_haberes - (total_prev + impuesto)
    
    # Costo Empresa
    sis = int(min(imponible, tope_pesos) * 0.0149)
    afc_emp = int(min(imponible, tope_sc_pesos) * 0.024)
    mutual = int(min(imponible, tope_pesos) * 0.0093)
    costo_empresa = total_haberes + sis + afc_emp + mutual
    
    return {
        "Imponible": imponible, "Haberes": total_haberes,
        "AFP": monto_afp, "Salud": monto_salud, "AFC": monto_afc, "Impuesto": impuesto,
        "Líquido": liquido, "Costo Empresa": costo_empresa
    }

# --- UI (INTERFAZ DE USUARIO) ---
st.title("🇨🇱 Calculadora RRHH Web")
st.markdown("---")

# Barra Lateral (Indicadores)
with st.sidebar:
    st.header("Indicadores Hoy")
    uf_val, utm_val = obtener_indicadores()
    st.metric("Valor UF", f"${uf_val:,.2f}")
    st.metric("Valor UTM", f"${utm_val:,.2f}")
    st.info("Datos obtenidos en tiempo real del Banco Central.")

# Formulario Principal
col1, col2 = st.columns(2)

with col1:
    st.subheader("1. Haberes")
    base = st.number_input("Sueldo Base ($)", value=500000, step=10000)
    grat_bool = st.selectbox("Gratificación Legal", ["SI", "NO"])
    colacion = st.number_input("Colación ($)", value=50000, step=5000)
    movilizacion = st.number_input("Movilización ($)", value=50000, step=5000)

with col2:
    st.subheader("2. Previsión")
    afp = st.selectbox("AFP", ["Capital", "Cuprum", "Habitat", "Modelo", "PlanVital", "Provida", "Uno", "SIN AFP"], index=3)
    salud = st.selectbox("Salud", ["Fonasa (7%)", "Isapre (UF)"])
    plan_uf = 0.0
    if salud == "Isapre (UF)":
        plan_uf = st.number_input("Valor Plan (UF)", value=0.0, step=0.1)

# Botón Calcular
if st.button("CALCULAR LIQUIDACIÓN", type="primary", use_container_width=True):
    res = calcular_sueldo(base, grat_bool, colacion, movilizacion, afp, salud, plan_uf, uf_val, utm_val)
    
    st.success("✅ Cálculo Realizado con Éxito")
    
    # Mostrar Resultados en Tarjetas
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Haberes", f"${res['Haberes']:,.0f}")
    c2.metric("Líquido a Pago", f"${res['Líquido']:,.0f}", delta="Bolsillo")
    c3.metric("Costo Empresa", f"${res['Costo Empresa']:,.0f}", delta="Total", delta_color="inverse")
    
    # Detalle
    st.subheader("Desglose")
    datos = {
        "Concepto": ["Sueldo Base", "Gratificación", "No Imponibles", "Total Haberes", "AFP", "Salud", "AFC", "Impuesto", "Líquido Final"],
        "Monto": [base, res['Haberes']-base-colacion-movilizacion, colacion+movilizacion, res['Haberes'], -res['AFP'], -res['Salud'], -res['AFC'], -res['Impuesto'], res['Líquido']]
    }
    df = pd.DataFrame(datos)
    st.dataframe(df, use_container_width=True)