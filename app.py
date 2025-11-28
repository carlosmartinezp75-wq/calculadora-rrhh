import streamlit as st
import pandas as pd
import base64
import io
import zipfile
from datetime import datetime, date
import random

# --- 0. CONFIGURACIÓN INICIAL (Siempre va primero) ---
st.set_page_config(page_title="HR Suite V35 Final", page_icon="🏢", layout="wide")

# --- 1. LIBRERÍAS (Manejo de errores si faltan) ---
try:
    from fpdf import FPDF
    from docx import Document
    from docx.shared import Pt
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    import plotly.graph_objects as go
    import pdfplumber
    LIBRARIES_OK = True
except ImportError:
    LIBRARIES_OK = False
    st.error("Faltan librerías. Asegúrate de que requirements.txt tenga: fpdf, python-docx, plotly, pdfplumber, openpyxl, xlsxwriter")

# --- 2. VARIABLES DE MEMORIA (Para que no se borren datos al clickear) ---
if 'empresa' not in st.session_state:
    st.session_state.empresa = {"rut": "", "nombre": "", "rep_nombre": "", "rep_rut": "", "direccion": "", "ciudad": "Santiago", "giro": "Servicios"}
if 'calculo_actual' not in st.session_state: st.session_state.calculo_actual = None
if 'finiquito_actual' not in st.session_state: st.session_state.finiquito_actual = None
if 'perfil_actual' not in st.session_state: st.session_state.perfil_actual = None

# --- 3. ESTILOS VISUALES ---
def cargar_estilos():
    st.markdown("""
        <style>
        .block-container {padding: 2rem;}
        h1, h2, h3 {color: #004a99;}
        /* Botones */
        .stButton>button {
            background-color: #004a99 !important; color: white !important; 
            border-radius: 5px; width: 100%; font-weight: bold;
        }
        /* Cajas de Resultado */
        .result-box {
            border: 1px solid #ddd; padding: 15px; border-radius: 5px; 
            background-color: #f9f9f9; margin-bottom: 10px;
        }
        /* Feedback visual */
        .feedback {color: green; font-size: 0.8em; margin-top: -10px;}
        </style>
    """, unsafe_allow_html=True)
cargar_estilos()

# --- 4. FUNCIONES DE FORMATO ---
def fmt(valor):
    if pd.isna(valor) or valor == "": return "$0"
    try: return "${:,.0f}".format(float(valor)).replace(",", ".")
    except: return str(valor)

def mostrar_miles(valor):
    if valor > 0: st.markdown(f'<p class="feedback">Ingresaste: {fmt(valor)}</p>', unsafe_allow_html=True)

# --- 5. MOTORES DE CÁLCULO ---

def calcular_sueldo_inverso(liquido_obj, col, mov, contrato, afp_nombre, salud_tipo, plan_uf):
    # Valores Previred Nov 2025 (Fijos para estabilidad)
    UF = 39643.59
    UTM = 69542.0
    S_MIN = 529000
    TOPE_GRAT = (4.75 * S_MIN) / 12
    
    no_imp = col + mov
    liq_meta = liquido_obj - no_imp
    
    # Tasas
    tasas_afp = {"Capital": 1.44, "Cuprum": 1.44, "Habitat": 1.27, "Modelo": 0.58, "Uno": 0.49, "SIN AFP": 0.0}
    tasa_afp_trab = 0.0 if (contrato == "Sueldo Empresarial" or afp_nombre == "SIN AFP") else (0.10 + tasas_afp.get(afp_nombre, 1.44)/100)
    
    # Iteración para encontrar Bruto
    min_b, max_b = 100000, liq_meta * 2.5
    for _ in range(100):
        base = (min_b + max_b) / 2
        grat = min(base * 0.25, TOPE_GRAT)
        if contrato == "Sueldo Empresarial": grat = 0
        tot_imp = base + grat
        
        # Topes Legales
        tope_prev = min(tot_imp, 87.8 * UF)
        tope_afc = min(tot_imp, 131.9 * UF)
        
        m_afp = int(tope_prev * tasa_afp_trab)
        m_afc = int(tope_afc * 0.006) if contrato == "Indefinido" and contrato != "Sueldo Empresarial" else 0
        
        # SALUD: Cálculo del 7% Legal
        legal_7 = int(tope_prev * 0.07)
        
        # Impuesto (Usando 7% como rebaja tributaria)
        base_trib = max(0, tot_imp - m_afp - legal_7 - m_afc)
        imp = 0
        # Tabla simplificada Nov 2025
        if base_trib > 13.5*UTM: imp = int(base_trib*0.04) 
        if base_trib > 30*UTM: imp = int((base_trib*0.08) - (1.74*UTM))
        
        liq_calc_base = tot_imp - m_afp - legal_7 - m_afc - imp
        
        if abs(liq_calc_base - liq_meta) < 500:
            # AJUSTE REAL ISAPRE (Si Plan > 7%)
            salud_descuento = legal_7
            adicional_isapre = 0
            msg_isapre = ""
            
            if salud_tipo == "Isapre (UF)":
                valor_plan = int(plan_uf * UF)
                if valor_plan > legal_7:
                    salud_descuento = valor_plan # Se descuenta el total
                    adicional_isapre = valor_plan - legal_7 # Diferencia que baja el líquido
                    msg_isapre = f"⚠️ Plan Isapre excede el 7%. El líquido baja en {fmt(adicional_isapre)}."
            
            liq_final = tot_imp - m_afp - salud_descuento - m_afc - imp + no_imp
            
            # Costo Empresa
            sis = int(tope_prev * 0.0149)
            mut = int(tope_prev * 0.0093)
            afc_emp = int(tope_afc * 0.024)
            
            return {
                "Sueldo Base": int(base), "Gratificación": int(grat), "Total Imponible": int(tot_imp),
                "No Imponibles": int(no_imp), "LÍQUIDO": int(liq_final),
                "AFP": m_afp, "Salud_Legal": legal_7, "Adicional_Isapre": adicional_isapre,
                "Salud_Total": salud_descuento, "AFC": m_afc, "Impuesto": int(imp),
                "Costo Empresa": int(tot_imp + no_imp + sis + mut + afc_emp),
                "Mensaje": msg_isapre
            }
            break
        elif liq_calc_base < liq_meta: min_b = base
        else: max_b = base
    return None

def calcular_finiquito_legal(f_ini, f_fin, base, causal, vac_pend):
    # Cálculo simple indemnizaciones
    dias = (f_fin - f_ini).days
    anos = int(dias/365.25)
    if (dias/365.25 - anos)*12 >= 6: anos += 1
    if anos > 11: anos = 11
    
    tope_uf = 90 * 39643.59
    base_calc = min(base, tope_uf)
    
    indem_anos = int(base_calc * anos) if causal == "Necesidades de la Empresa" else 0
    aviso = int(base_calc) if causal in ["Necesidades de la Empresa", "Desahucio"] else 0
    feriado = int(vac_pend * 1.25 * (base/30))
    
    return {"Anos": indem_anos, "Aviso": aviso, "Vacaciones": feriado, "Total": indem_anos+aviso+feriado}

# --- 6. GENERADORES DE DOCUMENTOS ---

def generar_pdf_liquidacion(res, emp, trab):
    if not LIBRARIES_OK: return None
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, "LIQUIDACION DE SUELDO", 0, 1, 'C')
    pdf.set_font("Arial", '', 10)
    
    # Datos
    pdf.cell(0, 6, f"Empresa: {emp['nombre']} | RUT: {emp['rut']}", 0, 1)
    pdf.cell(0, 6, f"Trabajador: {trab['nombre']} | RUT: {trab['rut']}", 0, 1)
    pdf.ln(5)
    
    # Tabla
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(95, 7, "HABERES", 1, 0, 'C', 1)
    pdf.cell(95, 7, "DESCUENTOS", 1, 1, 'C', 1)
    
    # Filas
    h = [("Sueldo Base", res['Sueldo Base']), ("Gratificacion", res['Gratificación']), ("Col/Mov", res['No Imponibles'])]
    d = [("AFP", res['AFP']), ("Salud Total", res['Salud_Total']), ("Cesantia", res['AFC']), ("Impuesto", res['Impuesto'])]
    
    for i in range(max(len(h), len(d))):
        ht, hv = h[i] if i<len(h) else ("", "")
        dt, dv = d[i] if i<len(d) else ("", "")
        pdf.cell(65, 6, ht, 'L'); pdf.cell(30, 6, fmt(hv) if hv!="" else "", 'R')
        pdf.cell(65, 6, dt, 'L'); pdf.cell(30, 6, fmt(dv) if dv!="" else "", 'R', 1)
        
    pdf.ln(10)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, f"LIQUIDO A PAGAR: {fmt(res['LÍQUIDO'])}", 1, 1, 'R')
    return pdf.output(dest='S').encode('latin-1')

def generar_word_contrato(datos):
    if not LIBRARIES_OK: return None
    doc = Document()
    doc.add_heading('CONTRATO DE TRABAJO', 0)
    
    texto = f"""En {datos['ciudad']}, a {datetime.now().strftime('%d/%m/%Y')}, entre {datos['emp_nombre']}, RUT {datos['emp_rut']}, y {datos['trab_nombre']}, RUT {datos['trab_rut']}, se acuerda:
    
    PRIMERO: El trabajador se desempeñará como {datos['cargo']}.
    SEGUNDO: Sueldo Base de {fmt(datos['sueldo'])}. Gratificación Legal tope 4.75 IMM.
    TERCERO: Jornada de 44 horas semanales.
    """
    doc.add_paragraph(texto)
    bio = io.BytesIO()
    doc.save(bio)
    return bio

def generar_plantilla_excel():
    df = pd.DataFrame(columns=["TIPO", "NOMBRE", "RUT", "CARGO", "SUELDO", "FECHA_INI"])
    df.loc[0] = ["Contrato", "Ejemplo", "1-9", "Analista", 500000, "2025-01-01"]
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False)
    buffer.seek(0)
    return buffer

def procesar_masivo(df, empresa):
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zf:
        for idx, row in df.iterrows():
            try:
                datos = {
                    "ciudad": empresa['ciudad'], "emp_nombre": empresa['nombre'], "emp_rut": empresa['rut'],
                    "trab_nombre": str(row.get('NOMBRE', '')), "trab_rut": str(row.get('RUT', '')),
                    "cargo": str(row.get('CARGO', '')), "sueldo": row.get('SUELDO', 0)
                }
                docx = generar_word_contrato(datos)
                zf.writestr(f"Contrato_{datos['trab_nombre']}.docx", docx.getvalue())
            except: pass
    zip_buffer.seek(0)
    return zip_buffer

# =============================================================================
# 7. INTERFAZ GRÁFICA
# =============================================================================

# --- SIDEBAR (DATOS EMPRESA) ---
with st.sidebar:
    st.title("🏢 Configuración")
    # Datos Empresa Persistentes
    st.session_state.empresa['rut'] = st.text_input("RUT Empresa", st.session_state.empresa['rut'])
    st.session_state.empresa['nombre'] = st.text_input("Razón Social", st.session_state.empresa['nombre'])
    st.session_state.empresa['rep_nombre'] = st.text_input("Rep. Legal", st.session_state.empresa['rep_nombre'])
    st.session_state.empresa['ciudad'] = st.text_input("Ciudad", st.session_state.empresa['ciudad'])
    
    st.markdown("---")
    # Datos Trabajador (Opcional)
    with st.expander("Datos Trabajador (Opcional)"):
        st.session_state.trabajador['nombre'] = st.text_input("Nombre", st.session_state.trabajador['nombre'])
        st.session_state.trabajador['rut'] = st.text_input("RUT", st.session_state.trabajador['rut'])

st.title("HR Suite Enterprise")

tabs = st.tabs(["💰 Calculadora", "📂 Carga Masiva", "📋 Perfil Cargo", "📜 Legal Hub", "📊 Indicadores"])

# --- TAB 1: CALCULADORA ---
with tabs[0]:
    c1, c2 = st.columns(2)
    with c1:
        liq = st.number_input("Líquido Objetivo", 1000000, step=50000); mostrar_miles(liq)
        col = st.number_input("Colación", 50000); mov = st.number_input("Movilización", 50000)
    with c2:
        con = st.selectbox("Contrato", ["Indefinido", "Plazo Fijo", "Sueldo Empresarial"])
        afp = st.selectbox("AFP", ["Capital", "Habitat", "Modelo", "Uno", "SIN AFP"])
        sal = st.selectbox("Salud", ["Fonasa (7%)", "Isapre (UF)"])
        plan = st.number_input("Plan UF", 0.0) if sal == "Isapre (UF)" else 0.0

    if st.button("CALCULAR"):
        res = calcular_sueldo_inverso(liq, col, mov, con, afp, sal, plan)
        if res:
            st.session_state.calculo_actual = res
            if res['Mensaje']: st.warning(res['Mensaje'])
            
            k1, k2, k3 = st.columns(3)
            k1.metric("Sueldo Base", fmt(res['Sueldo Base']))
            k2.metric("Líquido", fmt(res['LÍQUIDO']))
            k3.metric("Costo Empresa", fmt(res['Costo Empresa']))
            
            st.markdown(f"""
            <div class="result-box">
                <b>RESUMEN LIQUIDACIÓN:</b><br>
                Base: {fmt(res['Sueldo Base'])} | Grat: {fmt(res['Gratificación'])} | No Imp: {fmt(res['No Imponibles'])}<br>
                Descuentos: -{fmt(res['AFP'] + res['Salud_Total'] + res['AFC'] + res['Impuesto'])}
            </div>
            """, unsafe_allow_html=True)
            
    # Botón de descarga PDF FUERA del flujo del botón calcular
    if st.session_state.calculo_actual and LIBRARIES_OK:
        pdf_data = generar_pdf_liquidacion(st.session_state.calculo_actual, st.session_state.empresa, st.session_state.trabajador)
        st.download_button("⬇️ Descargar Liquidación PDF", pdf_data, "liquidacion.pdf", "application/pdf")

# --- TAB 2: CARGA MASIVA ---
with tabs[1]:
    st.header("Generación Masiva")
    st.info("Descarga la plantilla, llénala y súbela para generar contratos en lote.")
    
    if LIBRARIES_OK:
        plantilla = generar_plantilla_excel()
        st.download_button("1. Descargar Plantilla Excel", plantilla, "plantilla.xlsx")
        
        up_file = st.file_uploader("2. Subir Excel", type="xlsx")
        if up_file and st.button("PROCESAR Y GENERAR ZIP"):
            if st.session_state.empresa['rut']:
                df = pd.read_excel(up_file)
                zip_file = procesar_masivo(df, st.session_state.empresa)
                st.download_button("⬇️ Descargar ZIP", zip_file, "documentos.zip", "application/zip")
            else:
                st.error("Faltan datos de empresa en el menú lateral.")

# --- TAB 3: PERFIL ---
with tabs[2]:
    cargo = st.text_input("Cargo", "Analista")
    rubro = st.selectbox("Rubro", ["Minería", "Retail", "Tecnología", "Salud", "Banca"])
    if cargo:
        perf = generar_perfil_robusto(cargo, rubro)
        st.info(f"**Misión:** {perf['objetivo']}")
        st.write("**Funciones:**")
        for f in perf['funciones']: st.write(f"- {f}")
        st.write("**Requisitos:**")
        for r in perf['requisitos']: st.write(f"- {r}")

# --- TAB 4: LEGAL HUB ---
with tabs[3]:
    modo = st.radio("Documento", ["Contrato Individual", "Finiquito (Cálculo)"])
    
    if modo == "Contrato Individual":
        if st.session_state.calculo_actual:
            if st.button("GENERAR CONTRATO WORD"):
                datos = {**st.session_state.empresa, 
                         "trab_nombre": st.session_state.trabajador['nombre'], 
                         "trab_rut": st.session_state.trabajador['rut'],
                         "cargo": cargo, "sueldo": st.session_state.calculo_actual['Sueldo Base'],
                         "tipo_contrato": "Indefinido", "fecha_inicio": datetime.now().date()}
                doc = generar_contrato_word(st.session_state.calculo_actual, st.session_state.empresa, st.session_state.trabajador, datos)
                st.download_button("Descargar Contrato", doc.getvalue(), "contrato.docx")
        else: st.warning("Calcule sueldo en Pestaña 1 primero.")
        
    elif modo == "Finiquito (Cálculo)":
        c1, c2 = st.columns(2)
        fi = c1.date_input("Inicio", date(2020,1,1)); ft = c2.date_input("Fin", date.today())
        base = st.number_input("Base Finiquito", 1000000)
        vac = st.number_input("Vacaciones Pendientes", 0.0)
        causal = st.selectbox("Causal", ["Renuncia", "Necesidades de la Empresa"])
        
        if st.button("CALCULAR FINIQUITO"):
            res = calcular_finiquito_legal(fi, ft, base, causal, vac)
            st.write(res)

# --- TAB 5: INDICADORES ---
with tabs[4]:
    st.header("Indicadores Previred (Nov 2025)")
    st.table(pd.DataFrame({
        "Indicador": ["UF", "UTM", "Sueldo Mínimo", "Tope AFC", "Tope AFP"],
        "Valor": [fmt(39643.59), fmt(69542), fmt(529000), "131.9 UF", "87.8 UF"]
    }))
