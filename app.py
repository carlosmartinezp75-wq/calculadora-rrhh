import streamlit as st
import pandas as pd
import requests
import base64
import os
import io
import zipfile
import tempfile
import random
from datetime import datetime, date
import plotly.graph_objects as go
import plotly.express as px

# =============================================================================
# 0. VALIDACIÓN DE ENTORNO
# =============================================================================
try:
    import pdfplumber
    from fpdf import FPDF
    from docx import Document
    from docx.shared import Pt, Inches, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    import xlsxwriter # Requerido para generar excel
    LIBRARIES_OK = True
except ImportError:
    LIBRARIES_OK = False

# =============================================================================
# 1. CONFIGURACIÓN
# =============================================================================
st.set_page_config(page_title="HR Suite Legal Core V38", page_icon="⚖️", layout="wide")

# Estado Persistente
if 'empresa' not in st.session_state:
    st.session_state.empresa = {
        "nombre": "", "rut": "", "direccion": "", 
        "rep_nombre": "", "rep_rut": "", "ciudad": "Santiago", "giro": "Servicios"
    }
if 'calculo_actual' not in st.session_state: st.session_state.calculo_actual = None
if 'finiquito_actual' not in st.session_state: st.session_state.finiquito_actual = None

# =============================================================================
# 2. ESTILOS VISUALES (UI PREMIUM)
# =============================================================================
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
        
        /* Botones Acción */
        .stButton>button {{
            background-color: #004a99 !important; color: white !important; font-weight: bold; border-radius: 8px; width: 100%; height: 3rem;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1); transition: all 0.3s;
        }}
        .stButton>button:hover {{background-color: #003366 !important; transform: translateY(-2px);}}
        
        /* Cajas de Resultado */
        .result-box {{border: 1px solid #ddd; padding: 20px; background: #fff; margin-bottom: 20px; border-radius: 8px;}}
        .legal-header {{text-align: center; font-weight: bold; border-bottom: 2px solid #000; margin-bottom: 15px;}}
        
        /* Feedback Inputs */
        .miles-feedback {{font-size: 0.8rem; color: #28a745; font-weight: bold; margin-top: -10px;}}
        </style>
        """, unsafe_allow_html=True)

cargar_estilos()

# =============================================================================
# 3. UTILIDADES Y DATA
# =============================================================================
def fmt(valor): 
    if pd.isna(valor) or valor == "": return "$0"
    try: return "${:,.0f}".format(float(valor)).replace(",", ".")
    except: return str(valor)

def mostrar_miles(valor): 
    if valor > 0: st.markdown(f'<p class="miles-feedback">✅ Ingresaste: {fmt(valor)}</p>', unsafe_allow_html=True)

def obtener_indicadores():
    # Valores Nov 2025 para estabilidad
    return 39643.59, 69542.0

# =============================================================================
# 4. MOTORES DE CÁLCULO (FINANCIERO Y LEGAL)
# =============================================================================

def calcular_nomina_reversa(liquido_obj, col, mov, contrato, afp_n, salud_t, plan_uf, uf, utm, s_min):
    """Calcula Sueldo Base a partir del Líquido."""
    no_imp = col + mov
    liq_meta = liquido_obj - no_imp
    if liq_meta < s_min * 0.4: return None
    
    TOPE_GRAT = (4.75 * s_min) / 12
    tasa_afp = 0.0 if (contrato == "Sueldo Empresarial" or afp_n == "SIN AFP") else (0.10 + ({"Capital":1.44,"Habitat":1.27,"Modelo":0.58,"Uno":0.49}.get(afp_n,1.44)/100))
    tasa_afc_emp = 0.024 if contrato == "Indefinido" else 0.03
    tasa_afc_trab = 0.006 if (contrato == "Indefinido" and contrato != "Sueldo Empresarial") else 0.0
    
    min_b, max_b = 100000, liq_meta * 2.5
    for _ in range(150):
        base = (min_b + max_b) / 2
        grat = min(base * 0.25, TOPE_GRAT)
        if contrato == "Sueldo Empresarial": grat = 0
        tot_imp = base + grat
        
        b_prev = min(tot_imp, 87.8*uf)
        m_afp = int(b_prev * tasa_afp)
        legal_7 = int(b_prev * 0.07)
        m_afc = int(min(tot_imp, 131.9*uf) * tasa_afc_trab)
        
        base_trib = max(0, tot_imp - m_afp - legal_7 - m_afc)
        imp = 0
        if base_trib > 13.5*utm: imp = int(base_trib*0.04) # Simplificado
        
        liq_calc = tot_imp - m_afp - legal_7 - m_afc - imp
        
        if abs(liq_calc - liq_meta) < 500:
            salud_real = legal_7
            adicional = 0
            warning = None
            if salud_t == "Isapre (UF)":
                plan_pesos = int(plan_uf * uf)
                if plan_pesos > legal_7:
                    salud_real = plan_pesos
                    adicional = plan_pesos - legal_7
                    warning = f"⚠️ Plan Isapre excede el 7%. Líquido baja en {fmt(adicional)}."
            
            liq_final = tot_imp - m_afp - salud_real - m_afc - imp + no_imp
            ap_sis, ap_mut, ap_afc_e = int(b_prev*0.0149), int(b_prev*0.0093), int(min(tot_imp, 131.9*uf)*tasa_afc_emp)
            
            return {
                "Sueldo Base": int(base), "Gratificación": int(grat), "Total Imponible": int(tot_imp),
                "No Imponibles": int(no_imp), "LÍQUIDO": int(liq_final), 
                "AFP": m_afp, "Salud": salud_real, "AFC": m_afc, "Impuesto": imp,
                "Aportes Empresa": ap_sis+ap_mut+ap_afc_e, "COSTO TOTAL": int(tot_imp+no_imp+ap_sis+ap_mut+ap_afc_e),
                "Warning": warning
            }
            break
        elif liq_calc < liq_meta: min_b = base
        else: max_b = base
    return None

def calcular_finiquito_legal(f_ini, f_fin, sueldo_base, causal, vac_pend, uf):
    """Calcula indemnización años de servicio y vacaciones."""
    dias = (f_fin - f_ini).days
    anos = int(dias / 365.25)
    meses_extra = (dias % 365.25) / 30
    
    anos_pago = anos
    if meses_extra >= 6: anos_pago += 1
    if anos_pago > 11: anos_pago = 11 # Tope legal
    
    tope_indem = 90 * uf
    base_calc = min(sueldo_base, tope_indem)
    
    m_anos = 0
    m_aviso = 0
    if causal == "Necesidades de la Empresa":
        m_anos = int(base_calc * anos_pago)
        # Asumimos aviso previo no dado (se paga)
        m_aviso = int(base_calc)
        
    # Feriado Proporcional (Simplificado)
    valor_dia = sueldo_base / 30
    m_feriado = int(vac_pend * 1.25 * valor_dia)
    
    return {
        "Años Servicio": m_anos,
        "Aviso Previo": m_aviso,
        "Vacaciones": m_feriado,
        "TOTAL": m_anos + m_aviso + m_feriado,
        "Antigüedad": f"{anos} años"
    }

# =============================================================================
# 5. GENERADORES DOCUMENTALES (WORD/PDF/EXCEL)
# =============================================================================

def generar_plantilla_excel():
    df = pd.DataFrame(columns=[
        "TIPO_DOCUMENTO", "NOMBRE", "RUT", "CARGO", "SUELDO_BASE", 
        "FECHA_INICIO", "FECHA_TERMINO", "CAUSAL", "VACACIONES_PEND"
    ])
    df.loc[0] = ["Contrato", "Juan Perez", "12.345.678-9", "Analista", 800000, "2025-01-01", "", "", ""]
    df.loc[1] = ["Finiquito", "Maria Soto", "9.876.543-2", "Vendedora", 600000, "2020-01-01", "2025-11-27", "Necesidades", 10]
    
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Carga_Masiva')
    buffer.seek(0)
    return buffer

def crear_docx_legal(tipo, datos, empresa):
    doc = Document()
    style = doc.styles['Normal']; style.font.name = 'Arial'; style.font.size = Pt(11)
    fecha = datetime.now().strftime("%d de %B de %Y")
    
    doc.add_heading(str(tipo).upper(), 0).alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.add_paragraph(f"En {empresa.get('ciudad','Santiago')}, a {fecha}").alignment = WD_ALIGN_PARAGRAPH.RIGHT
    
    # Recuperación segura de datos (Soporta Excel o Input Manual)
    def g(k): return str(datos.get(k, "_____________"))
    
    intro = f"""
    Entre la empresa "{empresa.get('nombre','EMPRESA')}", RUT {empresa.get('rut','XX')}, representada por {empresa.get('rep_nombre','REP')}, en adelante el EMPLEADOR; y don/ña {g('NOMBRE')}, RUT {g('RUT')}, en adelante el TRABAJADOR, se acuerda:
    """
    doc.add_paragraph(intro)
    
    if "CONTRATO" in str(tipo).upper():
        clausulas = [
            ("PRIMERO (Cargo):", f"El trabajador se desempeñará como {g('CARGO')}."),
            ("SEGUNDO (Remuneración):", f"Sueldo Base: {fmt(g('SUELDO_BASE'))}. Gratificación Legal tope 4.75 IMM."),
            ("TERCERO (Jornada):", "44 horas semanales (Ley 40 Horas)."),
            ("CUARTO (Confidencialidad):", "El trabajador guardará secreto de la información sensible.")
        ]
        for t, x in clausulas: 
            p = doc.add_paragraph(); p.add_run(t).bold=True; p.add_run(f" {x}")
            
    elif "FINIQUITO" in str(tipo).upper():
        # Calcular si viene del Excel
        try:
            sueldo = float(datos.get('SUELDO_BASE', 0))
            vac = float(datos.get('VACACIONES_PEND', 0))
            # Simulación cálculo rápido para el documento masivo
            total_txt = fmt(sueldo + (vac*1.25*(sueldo/30))) 
        except: total_txt = "$0"
        
        doc.add_paragraph(f"1. CAUSAL: {g('CAUSAL')}.")
        doc.add_paragraph(f"2. PAGO: El empleador paga la suma total de {total_txt}.")
        doc.add_paragraph("3. DECLARACIÓN: El trabajador declara recibir a entera satisfacción el monto.")
    
    elif "AMONESTACION" in str(tipo).upper():
        doc.add_paragraph("Por medio de la presente, se amonesta al trabajador por incumplimiento de sus obligaciones contractuales, específicamente:")
        doc.add_paragraph(f"HECHOS: {g('HECHOS') if g('HECHOS')!='_____________' else 'Faltas reiteradas al reglamento interno.'}")
        doc.add_paragraph("Se deja constancia en su carpeta personal.")

    doc.add_paragraph("\n\n___________________\nFIRMA EMPLEADOR\n\n___________________\nFIRMA TRABAJADOR")
    
    bio = io.BytesIO()
    doc.save(bio)
    return bio

def procesar_lote_masivo(df, empresa_data):
    zip_buffer = io.BytesIO()
    reporte = []
    with zipfile.ZipFile(zip_buffer, "w") as zf:
        for idx, row in df.iterrows():
            try:
                # Normalizar nombres de columnas (Upper case)
                row = {k.upper(): v for k, v in row.items()}
                tipo = row.get('TIPO_DOCUMENTO', 'Contrato')
                nombre = row.get('NOMBRE', f'Trabajador_{idx}')
                
                docx = crear_docx_legal(tipo, row, empresa_data)
                zf.writestr(f"{tipo}_{nombre}.docx", docx.getvalue())
            except Exception as e:
                reporte.append(f"Error Fila {idx}: {str(e)}")
    zip_buffer.seek(0)
    return zip_buffer, reporte

def generar_pdf_liquidacion(res, emp, trab):
    if not LIBRARIES_OK: return None
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 14); pdf.cell(0, 10, "LIQUIDACION DE SUELDO", 0, 1, 'C'); pdf.ln(10)
    pdf.set_font("Arial", '', 10)
    pdf.cell(0, 6, f"Empresa: {emp.get('nombre','S/N')}", 0, 1)
    pdf.cell(0, 6, f"Trabajador: {trab.get('nombre','S/N')}", 0, 1)
    pdf.ln(5)
    # Tabla
    h = [("Base", res['Sueldo Base']), ("Gratif.", res['Gratificación']), ("No Imp.", res['No Imponibles'])]
    d = [("AFP", res['AFP']), ("Salud", res['Salud']), ("AFC", res['AFC']), ("Impuesto", res['Impuesto'])]
    for i in range(max(len(h), len(d))):
        t1, v1 = h[i] if i<len(h) else ("",""); t2, v2 = d[i] if i<len(d) else ("","")
        pdf.cell(50,6,t1,1); pdf.cell(30,6,fmt(v1),1); pdf.cell(10,6,"",0); pdf.cell(50,6,t2,1); pdf.cell(30,6,fmt(v2),1,1)
    pdf.ln(5); pdf.cell(0,10, f"LIQUIDO A PAGAR: {fmt(res['LÍQUIDO'])}", 1, 1, 'C')
    return pdf.output(dest='S').encode('latin-1')

# =============================================================================
# 6. INTERFAZ DE USUARIO
# =============================================================================

# --- SIDEBAR (DATOS EMPRESA) ---
with st.sidebar:
    st.image("https://www.previred.com/wp-content/uploads/2021/01/logo-previred.png", width=120)
    
    with st.expander("🏢 Datos Empresa (Obligatorio)", expanded=True):
        st.session_state.empresa['rut'] = st.text_input("RUT Empresa", st.session_state.empresa['rut'])
        st.session_state.empresa['nombre'] = st.text_input("Razón Social", st.session_state.empresa['nombre'])
        st.session_state.empresa['rep_nombre'] = st.text_input("Rep. Legal", st.session_state.empresa['rep_nombre'])
        st.session_state.empresa['ciudad'] = st.text_input("Ciudad Firma", st.session_state.empresa['ciudad'])
        
    st.info("Estos datos se usarán en todos los documentos generados.")

st.title("HR Suite Legal Core V38")
st.markdown("**Plataforma de Cálculo de Remuneraciones y Gestión Documental Legal**")

# --- NAVEGACIÓN PRINCIPAL ---
tabs = st.tabs(["💰 Calculadora Sueldo", "📜 Legal Hub (Contratos/Finiquitos)", "🧠 Análisis CV & Perfil", "📊 Indicadores"])

# --- TAB 1: CALCULADORA ---
with tabs[0]:
    with st.expander("📘 Guía: ¿Cómo calcular un sueldo?"):
        st.write("Ingresa el monto líquido que deseas pagar. El sistema calculará el Bruto y el Costo Empresa.")
    
    c1, c2 = st.columns(2)
    with c1:
        liq = st.number_input("Líquido Objetivo", 1000000, step=50000)
        mostrar_miles(liq)
        col = st.number_input("Colación", 50000); mov = st.number_input("Movilización", 50000)
    with c2:
        con = st.selectbox("Contrato", ["Indefinido", "Plazo Fijo", "Empresarial"])
        afp = st.selectbox("AFP", ["Capital", "Habitat", "Modelo", "Uno", "SIN AFP"])
        sal = st.selectbox("Salud", ["Fonasa (7%)", "Isapre (UF)"])
        plan = st.number_input("Plan UF", 0.0) if sal == "Isapre (UF)" else 0.0

    if st.button("CALCULAR NÓMINA"):
        res = calcular_nomina_reversa(liq, col, mov, con, afp, sal, plan, 39643.59, 69542.0, 529000)
        if res:
            st.session_state.calculo_actual = res
            if res.get('Warning'): st.warning(res['Warning'])
            
            k1, k2, k3 = st.columns(3)
            k1.metric("Sueldo Base", fmt(res['Sueldo Base']))
            k2.metric("Líquido Final", fmt(res['LÍQUIDO']))
            k3.metric("Costo Empresa", fmt(res['COSTO TOTAL']), delta="Total", delta_color="inverse")
            
            st.markdown(f"""
            <div class="result-box">
                <div class="legal-header">LIQUIDACIÓN SIMULADA</div>
                <div class="liq-row"><span>Base:</span><span>{fmt(res['Sueldo Base'])}</span></div>
                <div class="liq-row"><span>Gratificación:</span><span>{fmt(res['Gratificación'])}</span></div>
                <div class="liq-row"><span>No Imponibles:</span><span>{fmt(res['No Imponibles'])}</span></div>
                <hr>
                <div class="liq-row"><span>Descuentos Legales:</span><span style="color:red">-{fmt(res['Total Descuentos'])}</span></div>
                <div class="liq-total">A PAGAR: {fmt(res['LÍQUIDO'])}</div>
            </div>
            """, unsafe_allow_html=True)
            
            if LIBRARIES_OK:
                pdf = generar_pdf_liquidacion(res, st.session_state.empresa, st.session_state.trabajador)
                st.download_button("⬇️ Descargar Liquidación (PDF)", pdf, "liquidacion.pdf", "application/pdf")

# --- TAB 2: LEGAL HUB (MASIVO E INDIVIDUAL) ---
with tabs[1]:
    st.header("Centro de Documentación Legal")
    modo = st.radio("Seleccione Modo:", ["👤 Individual (Manual)", "📂 Masivo (Excel)"], horizontal=True)
    
    if modo == "👤 Individual (Manual)":
        doc_type = st.selectbox("Tipo Documento", ["Contrato de Trabajo", "Finiquito Laboral", "Carta Amonestación"])
        
        with st.form("doc_form"):
            c1, c2 = st.columns(2)
            nom = c1.text_input("Nombre Trabajador")
            rut = c2.text_input("RUT Trabajador")
            cargo = c1.text_input("Cargo")
            
            if doc_type == "Finiquito Laboral":
                st.markdown("---")
                st.markdown("**Cálculo de Indemnizaciones**")
                fi = c1.date_input("Inicio Relación", date(2022,1,1))
                ft = c2.date_input("Término Relación", date.today())
                base = st.number_input("Sueldo Base", 900000)
                vac = st.number_input("Vacaciones Pendientes", 0.0)
                causal = st.selectbox("Causal", ["Renuncia Voluntaria", "Necesidades de la Empresa"])
            
            sub = st.form_submit_button("GENERAR DOCUMENTO")
            
            if sub:
                if not st.session_state.empresa['rut']:
                    st.error("⚠️ Complete los Datos de Empresa en el menú lateral.")
                else:
                    if doc_type == "Finiquito Laboral":
                        fin_calc = calcular_finiquito_legal(fi, ft, base, causal, vac, 39643.59)
                        st.success(f"Cálculo Finiquito: {fmt(fin_calc['TOTAL'])}")
                        # Preparamos datos para el docx
                        datos = {"NOMBRE": nom, "RUT": rut, "CAUSAL": causal, "TOTAL": fin_calc['TOTAL']}
                        docx = crear_documento_word_masivo("FINIQUITO", datos, st.session_state.empresa)
                        st.download_button("Descargar Finiquito (.docx)", docx, "finiquito.docx")
                    else:
                        # Contrato / Amonestación
                        sueldo_txt = fmt(st.session_state.calculo_actual['Sueldo Base']) if st.session_state.calculo_actual else "$0"
                        datos = {"NOMBRE": nom, "RUT": rut, "CARGO": cargo, "SUELDO_BASE": sueldo_txt}
                        docx = crear_documento_word_masivo(doc_type.split()[0].upper(), datos, st.session_state.empresa)
                        st.download_button("Descargar Documento (.docx)", docx, f"{doc_type}.docx")

    elif modo == "📂 Masivo (Excel)":
        with st.expander("📘 Instrucciones Carga Masiva"):
            st.write("1. Descargue la plantilla Excel.")
            st.write("2. Llene las filas con los trabajadores (Contrato, Finiquito, etc).")
            st.write("3. Suba el archivo y presione Procesar.")
        
        # 1. Bajar Plantilla
        plantilla = generar_plantilla_excel()
        st.download_button("1. Descargar Plantilla Excel", plantilla, "plantilla_rrhh.xlsx")
        
        # 2. Subir y Procesar
        up_file = st.file_uploader("2. Subir Excel Completo", type="xlsx")
        if up_file and st.button("PROCESAR Y GENERAR ZIP"):
            if not st.session_state.empresa['rut']:
                st.error("⚠️ Falta RUT Empresa en barra lateral.")
            else:
                try:
                    df = pd.read_excel(up_file)
                    zip_file, log = procesar_lote_masivo(df, st.session_state.empresa)
                    st.success("Procesamiento finalizado.")
                    if log: st.warning(f"Advertencias: {log}")
                    st.download_button("⬇️ DESCARGAR ZIP CON DOCUMENTOS", zip_file, "documentos_legales.zip", "application/zip")
                except Exception as e:
                    st.error(f"Error crítico: {e}")

# --- TAB 3: TALENTO (CV & PERFIL) ---
with tabs[2]:
    st.info("Módulo de Análisis de CV y Perfiles (Requiere librerías PDF).")
    # (Aquí va el código de análisis CV de versiones anteriores si se desea activar)

# --- TAB 4: INDICADORES ---
with tabs[3]:
    st.header("Indicadores Oficiales")
    st.table(pd.DataFrame({"Indicador": ["UF", "UTM", "Sueldo Mínimo"], "Valor": [fmt(39643.59), fmt(69542), fmt(529000)]}))
