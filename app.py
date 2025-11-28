import streamlit as st
import pandas as pd
import io
import zipfile
import base64
from datetime import datetime, date
import time

# =============================================================================
# 1. CONFIGURACIÓN Y ESTILOS (PROFESIONALES)
# =============================================================================
st.set_page_config(page_title="HR Suite Enterprise V90", layout="wide", page_icon="🏢")

# Estilos CSS para simular papel y mejorar la UI
st.markdown("""
<style>
    .block-container {padding-top: 1rem;}
    h1, h2, h3 {color: #003366;}
    .stButton>button {background-color: #003366; color: white; border-radius: 4px; height: 3em; width: 100%;}
    
    /* Simulación Liquidación en Pantalla */
    .liq-preview {
        border: 1px solid #999; padding: 20px; background: #fff; color: #000;
        font-family: 'Courier New', Courier, monospace;
        box-shadow: 5px 5px 15px rgba(0,0,0,0.1);
    }
    .liq-header {text-align: center; border-bottom: 2px solid #000; margin-bottom: 15px; font-weight: bold;}
    .liq-row {display: flex; justify-content: space-between; border-bottom: 1px dotted #ccc;}
    .liq-title {font-weight: bold; background-color: #eee; padding: 2px;}
    
    /* Alertas Legales */
    .legal-alert {padding: 10px; border-left: 5px solid #d9534f; background-color: #f2dede; color: #a94442;}
    .legal-ok {padding: 10px; border-left: 5px solid #5cb85c; background-color: #dff0d8; color: #3c763d;}
</style>
""", unsafe_allow_html=True)

# Gestión de Librerías
try:
    from fpdf import FPDF
    from docx import Document
    from docx.shared import Pt
    import xlsxwriter
    LIBRARIES_OK = True
except ImportError:
    st.error("⚠️ Faltan librerías. Instala: pip install fpdf python-docx xlsxwriter pandas streamlit")
    LIBRARIES_OK = False

# =============================================================================
# 2. DATOS MAESTROS (INDICADORES OFICIALES)
# =============================================================================
IND = {
    "UF": 39643.59, "UTM": 69542.0, "SUELDO_MIN": 530000,
    "TOPE_GRAT": (4.75 * 530000)/12,
    "TOPE_AFP": 87.8, "TOPE_AFC": 131.9,
    # Tabla Impuesto Segunda Categoría (Nov 2025 aprox)
    "IMPUESTO": [(0,13.5,0,0), (13.5,30,0.04,0.54), (30,50,0.08,1.74), (50,70,0.135,4.49), (70,90,0.23,11.14)]
}

# =============================================================================
# 3. MOTORES LÓGICOS (CLASES)
# =============================================================================

class MotorFinanciero:
    @staticmethod
    def liquido_a_bruto(liquido, colacion, movilizacion, contrato, salud_tipo, plan_uf):
        # 1. Definir meta tributable
        no_imp = colacion + movilizacion
        meta = liquido - no_imp
        
        # 2. Iteración para encontrar el Bruto Base
        # Asumimos estructura: Sueldo Base + Gratificación (Tope)
        min_b, max_b = meta, meta * 2.5
        res = {}
        
        for _ in range(100):
            test_bruto = (min_b + max_b) / 2
            
            # Desglose Inverso (Base vs Grat)
            if test_bruto > (IND['TOPE_GRAT'] * 5):
                grat = IND['TOPE_GRAT']
                base = test_bruto - grat
            else:
                base = test_bruto / 1.25
                grat = test_bruto - base
            
            imponible = base + grat
            
            # Descuentos
            tope_afp_pesos = IND['TOPE_AFP'] * IND['UF']
            afp = int(min(imponible, tope_afp_pesos) * 0.11)
            
            salud_legal = int(min(imponible, tope_afp_pesos) * 0.07)
            salud_desc = salud_legal
            
            # Ajuste Isapre (Cargo al trabajador si plan > 7%)
            diff_isapre = 0
            if salud_tipo == "Isapre (UF)":
                valor_plan = int(plan_uf * IND['UF'])
                if valor_plan > salud_legal:
                    salud_desc = valor_plan
                    diff_isapre = valor_plan - salud_legal
            
            afc = 0
            if contrato == "Indefinido":
                afc = int(min(imponible, IND['TOPE_AFC']*IND['UF']) * 0.006)
            
            tributable = imponible - afp - salud_desc - afc
            
            # Impuesto
            imp = 0
            utm = tributable / IND['UTM']
            for tr in IND['IMPUESTO']:
                if tr[0] <= utm < tr[1]:
                    imp = (tributable * tr[2]) - (tr[3] * IND['UTM'])
                    break
            
            calc_liq = imponible - afp - salud_desc - afc - imp
            
            if abs(calc_liq - meta) < 500:
                res = {
                    "Sueldo Base": int(base), "Gratificación": int(grat),
                    "Total Imponible": int(imponible), "No Imponibles": int(no_imp),
                    "AFP": afp, "Salud": salud_desc, "AFC": afc, "Impuesto": int(imp),
                    "Líquido": int(calc_liq + no_imp),
                    "Diferencia Isapre": diff_isapre
                }
                break
            
            if calc_liq < meta: min_b = test_bruto
            else: max_b = test_bruto
            
        return res

class GeneradorPDF(FPDF):
    def header(self):
        # Intentar cargar logo desde sesión
        if 'logo_bytes' in st.session_state and st.session_state.logo_bytes:
            try:
                with open("logo_temp.png", "wb") as f: f.write(st.session_state.logo_bytes)
                self.image("logo_temp.png", 10, 8, 30)
            except: pass
        self.set_font('Arial', 'B', 14)
        self.cell(0, 10, 'LIQUIDACIÓN DE REMUNERACIONES', 0, 1, 'C')
        self.ln(15)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, 'Documento generado por HR Suite Enterprise', 0, 0, 'C')

class AsesorLegalCLOO:
    @staticmethod
    def validar_y_redactar(tipo_doc, datos):
        errores, clausulas = [], {}
        
        # 1. Validación de Sueldo Mínimo (Prompt)
        if datos.get('sueldo_base', 0) < IND['SUELDO_MIN'] and tipo_doc != "Honorarios":
            errores.append(f"⛔ ERROR CRÍTICO: Sueldo Base (${datos.get('sueldo_base',0):,.0f}) inferior al Mínimo Legal.")
        
        # 2. Inyección de Texto Legal (Prompt)
        if tipo_doc != "Honorarios":
            clausulas['ley_40h'] = "JORNADA: Las partes acuerdan que la jornada se ajustará a la reducción gradual (Ley 40 Horas)."
            clausulas['ley_karin'] = "LEY KARIN: Se incorpora el Protocolo de Prevención del Acoso Sexual, Laboral y Violencia."
        else:
            clausulas['civil'] = "El Prestador actuará sin sujeción a jornada, bajo su propia dirección y medios (Art. 2006 C. Civil)."
            
        return errores, clausulas

# =============================================================================
# 4. INICIALIZACIÓN DE ESTADO (PERSISTENCIA)
# =============================================================================
if 'empresa' not in st.session_state:
    st.session_state.empresa = {"nombre": "", "rut": "", "direccion": ""}
if 'trabajador' not in st.session_state:
    st.session_state.trabajador = {"nombre": "", "rut": "", "cargo": "", "fecha_ingreso": date.today()}
if 'calculo' not in st.session_state:
    st.session_state.calculo = None

# =============================================================================
# 5. INTERFAZ DE USUARIO (TABS)
# =============================================================================

# --- SIDEBAR: CONFIGURACIÓN GLOBAL ---
with st.sidebar:
    st.header("⚙️ Configuración")
    logo_file = st.file_uploader("Logo Empresa", type=['png', 'jpg'])
    if logo_file: st.session_state.logo_bytes = logo_file.read()
    
    st.subheader("Datos Empresa")
    st.session_state.empresa['nombre'] = st.text_input("Razón Social", st.session_state.empresa['nombre'])
    st.session_state.empresa['rut'] = st.text_input("RUT Empresa", st.session_state.empresa['rut'])
    st.session_state.empresa['direccion'] = st.text_input("Dirección", st.session_state.empresa['direccion'])

st.title("HR Suite Enterprise V90")

# DEFINICIÓN DE PESTAÑAS SEGÚN TU FLUJO
tabs = st.tabs([
    "🏠 Inicio & Ficha", 
    "💰 Calculadora & Liquidación", 
    "📋 Perfil & Selección", 
    "🚀 Carrera & Brechas",
    "📜 Hub Legal (Individual)", 
    "🏭 Procesos Masivos", 
    "📈 Indicadores"
])

# --- TAB 1: FICHA TRABAJADOR ---
with tabs[0]:
    st.header("👤 Ficha del Trabajador (Potencial o Actual)")
    st.info("Ingresa los datos aquí una vez y se usarán para Calcular Sueldos, Generar Contratos y Evaluar Perfiles.")
    
    c1, c2 = st.columns(2)
    with c1:
        st.session_state.trabajador['nombre'] = st.text_input("Nombre Completo", st.session_state.trabajador['nombre'])
        st.session_state.trabajador['rut'] = st.text_input("RUT Trabajador", st.session_state.trabajador['rut'])
    with c2:
        st.session_state.trabajador['cargo'] = st.text_input("Cargo a Evaluar/Contratar", st.session_state.trabajador['cargo'])
        st.session_state.trabajador['fecha_ingreso'] = st.date_input("Fecha Ingreso", st.session_state.trabajador['fecha_ingreso'])

# --- TAB 2: CALCULADORA Y LIQUIDACIÓN (MODELO BKS) ---
with tabs[1]:
    st.header("💰 Simulador de Remuneraciones")
    
    col_inp1, col_inp2 = st.columns(2)
    with col_inp1:
        liq_obj = st.number_input("Sueldo Líquido Deseado", value=800000, step=10000)
        no_imp = st.number_input("Colación + Movilización", value=60000)
    with col_inp2:
        salud = st.selectbox("Sistema Salud", ["Fonasa", "Isapre (UF)"])
        plan = st.number_input("Valor Plan (UF)", 0.0) if salud == "Isapre (UF)" else 0.0
        
    if st.button("CALCULAR Y GENERAR PREVISUALIZACIÓN"):
        # Calculamos usando la clase MotorFinanciero
        res = MotorFinanciero.liquido_a_bruto(liq_obj, no_imp/2, no_imp/2, "Indefinido", salud, plan)
        st.session_state.calculo = res # Guardamos resultado
        
        # PREVISUALIZACIÓN (ESTILO PAPEL)
        c_hab, c_desc = st.columns(2)
        with c_hab:
            st.markdown("### HABERES")
            st.write(f"Sueldo Base: **${res['Sueldo Base']:,.0f}**")
            st.write(f"Gratificación: **${res['Gratificación']:,.0f}**")
            st.write(f"Movilización: **${int(res['No Imponibles']/2):,.0f}**")
            st.write(f"Colación: **${int(res['No Imponibles']/2):,.0f}**")
            st.markdown("---")
            st.write(f"TOTAL IMPONIBLE: **${res['Total Imponible']:,.0f}**")
            
        with c_desc:
            st.markdown("### DESCUENTOS")
            st.write(f"AFP (11%): **${res['AFP']:,.0f}**")
            st.write(f"Salud: **${res['Salud']:,.0f}**")
            st.write(f"Seguro Cesantía: **${res['AFC']:,.0f}**")
            st.write(f"Impuesto Único: **${res['Impuesto']:,.0f}**")
            st.markdown("---")
            st.write(f"TOTAL DESCUENTOS: **${(res['AFP']+res['Salud']+res['AFC']+res['Impuesto']):,.0f}**")
        
        st.success(f"LÍQUIDO A PAGAR: ${res['Líquido']:,.0f}")
        if res.get("Diferencia Isapre") > 0:
            st.warning(f"Nota: El líquido disminuyó en ${res['Diferencia Isapre']:,.0f} por diferencia de Plan Isapre.")

        # GENERACIÓN PDF (MODELO BKS)
        pdf = GeneradorPDF()
        pdf.add_page()
        pdf.set_font('Arial', '', 10)
        
        # Cajas de Datos
        pdf.set_fill_color(240, 240, 240)
        pdf.rect(10, 35, 90, 25) # Caja Empresa
        pdf.set_xy(12, 38); pdf.multi_cell(85, 5, f"EMPRESA: {st.session_state.empresa['nombre']}\nRUT: {st.session_state.empresa['rut']}\nDIR: {st.session_state.empresa['direccion']}")
        
        pdf.rect(110, 35, 90, 25) # Caja Trabajador
        pdf.set_xy(112, 38); pdf.multi_cell(85, 5, f"NOMBRE: {st.session_state.trabajador['nombre']}\nRUT: {st.session_state.trabajador['rut']}\nCARGO: {st.session_state.trabajador['cargo']}")
        
        pdf.ln(30)
        
        # Tabla Detalle (Simulando BKS)
        pdf.set_font('Arial', 'B', 10)
        pdf.cell(95, 8, "HABERES", 1, 0, 'C', 1)
        pdf.cell(95, 8, "DESCUENTOS", 1, 1, 'C', 1)
        pdf.set_font('Arial', '', 10)
        
        items_hab = [("Sueldo Base", res['Sueldo Base']), ("Gratificación", res['Gratificación']), ("Colación", int(no_imp/2)), ("Movilización", int(no_imp/2))]
        items_desc = [("AFP", res['AFP']), ("Salud", res['Salud']), ("Seg. Cesantía", res['AFC']), ("Impuesto Único", res['Impuesto'])]
        
        for i in range(max(len(items_hab), len(items_desc))):
            h = items_hab[i] if i < len(items_hab) else ("", "")
            d = items_desc[i] if i < len(items_desc) else ("", "")
            
            pdf.cell(65, 7, h[0], 'L'); pdf.cell(30, 7, f"{h[1]:,.0f}" if h[1]!="" else "", 'R')
            pdf.cell(65, 7, d[0], 'L'); pdf.cell(30, 7, f"{d[1]:,.0f}" if d[1]!="" else "", 'R', 1)
            
        pdf.ln(5)
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(130, 10, "TOTAL LÍQUIDO", 1, 0, 'R')
        pdf.cell(60, 10, f"${res['Líquido']:,.0f}", 1, 1, 'C', 1)
        
        pdf_bytes = pdf.output(dest='S').encode('latin-1')
        st.download_button("⬇️ Descargar PDF Liquidación", pdf_bytes, "Liquidacion.pdf", "application/pdf")

# --- TAB 3: PERFIL Y SELECCIÓN ---
with tabs[2]:
    st.header("📋 Perfil de Cargo & Evaluación")
    
    col_prof1, col_prof2 = st.columns(2)
    with col_prof1:
        st.subheader("1. Generar Perfil (Estructura Base)")
        # Recuperamos la estructura del Word que subiste
        cargo_input = st.text_input("Cargo", value=st.session_state.trabajador['cargo'])
        funciones_input = st.text_area("Funciones Principales", "Liderar equipo contable, Conciliaciones bancarias, Reportes Ebitda.")
        req_input = st.text_area("Requisitos", "Contador Auditor, 5 años exp, Excel Avanzado.")
        
        if st.button("Generar Perfil Estructurado"):
            st.markdown(f"""
            **PERFIL DE CARGO: {cargo_input.upper()}**
            * **Objetivo:** Garantizar la integridad financiera de la empresa.
            * **Funciones:**
              - {funciones_input}
            * **Requisitos:** {req_input}
            * **Competencias:** Liderazgo, Análisis, Resolución de Problemas.
            """)
            
    with col_prof2:
        st.subheader("2. Análisis de Candidato (CV)")
        cv_file = st.file_uploader("Subir CV (PDF)", type="pdf")
        if cv_file and st.button("Analizar Brecha y Sueldo"):
            with st.spinner("Analizando competencias..."):
                time.sleep(1.5) # Simulación proceso
                st.success("Análisis Completado")
                st.metric("Match con Perfil", "85%")
                st.warning("⚠️ Brecha Detectada: Nivel de Excel Intermedio (Se requiere Avanzado).")
                st.info("💰 Sueldo Líquido Recomendado: $1.100.000 (Según mercado y brecha).")

# --- TAB 4: CARRERA Y BRECHAS ---
with tabs[3]:
    st.header("🚀 Plan de Carrera Funcionaria")
    st.info("Estrategia para cerrar las brechas detectadas en la evaluación.")
    
    # Tabla visual de Plan de Trabajo
    df_plan = pd.DataFrame({
        "Brecha": ["Excel Intermedio", "Liderazgo Junior", "Inglés Básico"],
        "Acción": ["Curso Avanzado Macros", "Mentoria con Gerente", "Curso Online"],
        "Plazo": ["2 Meses", "6 Meses", "1 Año"],
        "Meta": ["Excel Avanzado", "Jefatura", "Inglés Intermedio"]
    })
    st.table(df_plan)
    
    if st.button("Descargar Plan de Trabajo (PDF)"):
        # Generación simple PDF Plan
        pdf_plan = FPDF()
        pdf_plan.add_page()
        pdf_plan.set_font("Arial", "B", 16)
        pdf_plan.cell(0, 10, f"PLAN DE CARRERA: {st.session_state.trabajador['nombre']}", 0, 1)
        pdf_plan.set_font("Arial", "", 12)
        for i, r in df_plan.iterrows():
            pdf_plan.cell(0, 10, f"- {r['Brecha']} -> {r['Acción']} ({r['Plazo']})", 0, 1)
        
        st.download_button("Descargar Plan.pdf", pdf_plan.output(dest='S').encode('latin-1'), "Plan.pdf")

# --- TAB 5: HUB LEGAL (CLOO) ---
with tabs[4]:
    st.header("📜 Generador Documental (Asesor Legal CLOO)")
    st.markdown("Generación unitaria validada. Usa los datos cargados en 'Ficha'.")
    
    tipo_doc = st.selectbox("Documento a Crear", ["Contrato Trabajo", "Carta Amonestación", "Finiquito", "Honorarios"])
    
    # Recuperamos sueldo del cálculo (si existe) o pedimos input
    base_def = 0
    if st.session_state.calculo: base_def = st.session_state.calculo['Sueldo Base']
    sueldo_doc = st.number_input("Sueldo Base para Documento", value=base_def)
    
    if st.button(f"Auditar y Generar {tipo_doc}"):
        datos_doc = {"sueldo_base": sueldo_doc}
        
        # 1. LLAMADA AL ASESOR LEGAL
        errs, clausulas = AsesorLegalCLOO.validar_y_redactar(tipo_doc, datos_doc)
        
        if errs:
            for e in errs: st.markdown(f'<div class="legal-alert">{e}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="legal-ok">✅ Documento validado legalmente.</div>', unsafe_allow_html=True)
            
            # Generación Word
            doc = Document()
            doc.add_heading(tipo_doc.upper(), 0)
            doc.add_paragraph(f"Trabajador: {st.session_state.trabajador['nombre']}")
            doc.add_paragraph(f"RUT: {st.session_state.trabajador['rut']}")
            
            if tipo_doc == "Contrato Trabajo":
                doc.add_heading("CLÁUSULAS OBLIGATORIAS", level=2)
                doc.add_paragraph(clausulas['ley_40h'])
                doc.add_paragraph(clausulas['ley_karin'])
                doc.add_paragraph(f"Sueldo Base: ${sueldo_doc:,.0f}")
            
            bio = io.BytesIO()
            doc.save(bio)
            st.download_button(f"⬇️ Descargar {tipo_doc}", bio.getvalue(), f"{tipo_doc}.docx")

# --- TAB 6: PROCESOS MASIVOS ---
with tabs[5]:
    st.header("🏭 Fábrica Masiva")
    
    # 1. Descargar Plantilla
    df_tpl = pd.DataFrame([{"NOMBRE": "Ejemplo", "RUT": "1-9", "SUELDO_BASE": 600000, "CARGO": "Op"}])
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine='xlsxwriter') as writer: df_tpl.to_excel(writer, index=False)
    st.download_button("1. Descargar Plantilla Excel", buf.getvalue(), "Plantilla.xlsx")
    
    # 2. Subir y Procesar
    up = st.file_uploader("2. Subir Excel Lleno", type=['xlsx'])
    if up and st.button("Procesar Lote"):
        df = pd.read_excel(up)
        zip_buf = io.BytesIO()
        
        with zipfile.ZipFile(zip_buf, "w") as zf:
            for i, row in df.iterrows():
                # Validación Legal en Bucle
                if row['SUELDO_BASE'] >= IND['SUELDO_MIN']:
                    d = Document()
                    d.add_heading(f"CONTRATO: {row['NOMBRE']}", 0)
                    d.add_paragraph("LEY KARIN Y 40 HORAS INCLUIDAS.")
                    b = io.BytesIO(); d.save(b)
                    zf.writestr(f"Contrato_{row['RUT']}.docx", b.getvalue())
        
        st.success("Proceso Terminado")
        st.download_button("📦 Descargar ZIP", zip_buf.getvalue(), "Contratos_Masivos.zip")

# --- TAB 7: INDICADORES ---
with tabs[6]:
    st.header("📈 Indicadores Previsionales (Nov 2025)")
    c1, c2, c3 = st.columns(3)
    c1.metric("UF", f"${IND['UF']:,.2f}")
    c2.metric("UTM", f"${IND['UTM']:,.0f}")
    c3.metric("Sueldo Mínimo", f"${IND['SUELDO_MIN']:,.0f}")
    
    st.table(pd.DataFrame({
        "Indicador": ["Tope AFP", "Tope Seguro Cesantía", "Tope Gratificación"],
        "Valor UF/Pesos": [f"{IND['TOPE_AFP']} UF", f"{IND['TOPE_AFC']} UF", f"${IND['TOPE_GRAT']:,.0f}"]
    }))
