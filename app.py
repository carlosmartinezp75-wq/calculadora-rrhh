import streamlit as st
import pandas as pd
import io
import zipfile
from datetime import datetime, date

# =============================================================================
# 1. CONFIGURACIÓN
# =============================================================================
st.set_page_config(page_title="HR Suite V110", layout="wide", page_icon="🏢")

# Estilos CSS para simular la visualización de documentos
st.markdown("""
<style>
    .reportview-container .main .block-container {padding-top: 1rem;}
    h1, h2, h3 {color: #003366;}
    .stButton>button {background-color: #003366; color: white; width: 100%;}
    
    /* Caja estilo Liquidación BKS */
    .liq-container {border: 2px solid #000; padding: 0; font-family: 'Courier New'; background: #fff; color: #000;}
    .liq-header {border-bottom: 2px solid #000; padding: 10px; display: flex; justify-content: space-between;}
    .liq-box {border: 1px solid #000; padding: 10px; margin: 5px; width: 48%; font-size: 0.9em;}
    .liq-body {display: flex; border-top: 2px solid #000;}
    .liq-col {width: 50%; padding: 10px; border-right: 1px solid #000;}
    .liq-footer {border-top: 2px solid #000; padding: 10px; text-align: right; font-weight: bold; font-size: 1.2em;}
</style>
""", unsafe_allow_html=True)

try:
    from fpdf import FPDF
    from docx import Document
    from docx.shared import Pt
    import xlsxwriter
    LIBS_OK = True
except ImportError:
    st.error("⚠️ Faltan librerías. Instala: pip install fpdf python-docx xlsxwriter pandas streamlit")
    LIBS_OK = False

# =============================================================================
# 2. DATOS MAESTROS Y LÓGICA
# =============================================================================
IND = {
    "UF": 39643.59, "UTM": 69542.0, "IMM": 530000,
    "TOPE_GRAT": (4.75 * 530000)/12,
    "TOPE_AFP": 84.3, "TOPE_AFC": 126.6
}

# --- CLASE DE CÁLCULO FINANCIERO ---
class MotorCalculo:
    @staticmethod
    def calcular_sueldo(liquido_obj, col, mov, tipo_contrato, salud_sys, plan_uf):
        # 1. Ajustes Previos
        no_imp = col + mov
        meta = liquido_obj - no_imp
        
        # 2. Iteración Inversa (Líquido -> Bruto)
        min_b, max_b = meta, meta * 2.5
        res = {}
        
        for _ in range(100):
            test = (min_b + max_b) / 2
            
            # Estructura: Base + Gratificación
            if tipo_contrato == "Sueldo Empresarial":
                grat = 0
                base = test
            else:
                if test > (IND["TOPE_GRAT"] * 5):
                    grat = IND["TOPE_GRAT"]
                    base = test - grat
                else:
                    base = test / 1.25
                    grat = test - base
            
            imponible = base + grat
            
            # Descuentos (Standard para encontrar base)
            tope_afp_p = IND["TOPE_AFP"] * IND["UF"]
            
            if tipo_contrato == "Sueldo Empresarial":
                afp = 0
                afc = 0
            else:
                afp = int(min(imponible, tope_afp_p) * 0.11)
                afc = int(min(imponible, IND["TOPE_AFC"]*IND["UF"]) * 0.006) if tipo_contrato == "Indefinido" else 0
            
            salud_legal = int(min(imponible, tope_afp_p) * 0.07)
            tributable = imponible - afp - salud_legal - afc
            
            imp = 0 # Simplificado para iteración
            if tributable > (13.5*IND["UTM"]): imp = (tributable*0.04) - (0.54*IND["UTM"])
            imp = max(0, int(imp))
            
            liq_calc = imponible - afp - salud_legal - afc - imp
            
            if abs(liq_calc - meta) < 500:
                # 3. Cálculo FINAL (Realidad Isapre)
                salud_real = salud_legal
                diff = 0
                glosa = ""
                
                if salud_sys == "Isapre (UF)":
                    valor_plan = int(plan_uf * IND["UF"])
                    if valor_plan > salud_legal:
                        salud_real = valor_plan
                        diff = valor_plan - salud_legal
                        glosa = f"Diferencia Isapre cargo trabajador: ${diff:,.0f}"
                
                liq_final = imponible - afp - salud_real - afc - imp + no_imp
                
                return {
                    "Base": int(base), "Grat": int(grat), "Tot_Imp": int(imponible),
                    "No_Imp": int(no_imp), "AFP": afp, "Salud": salud_real, 
                    "AFC": afc, "Impuesto": int(imp), "Liquido": int(liq_final),
                    "Glosa": glosa
                }
                break
            
            if liq_calc < meta: min_b = test
            else: max_b = test
        return res

# --- CLASE GENERADORA DE PDF (TIPO BKS) ---
class PDFLiquidacion(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 14)
        self.cell(0, 10, 'LIQUIDACIÓN DE SUELDO', 0, 1, 'C')
        self.ln(5)

    def generar_documento(self, datos, emp, trab):
        self.add_page()
        self.set_font('Arial', '', 9)
        
        # --- BLOQUE 1: CAJAS DE DATOS ---
        y_start = self.get_y()
        
        # Caja Empresa (Izquierda)
        self.rect(10, y_start, 90, 35)
        self.set_xy(12, y_start + 2)
        self.multi_cell(85, 5, f"EMPRESA: {emp['nombre'].upper()}\nRUT: {emp['rut']}\nDIR: {emp['direccion']}\nCIUDAD: {emp['ciudad']}\nRUBRO: {emp['rubro']}")
        
        # Caja Trabajador (Derecha)
        self.rect(110, y_start, 90, 35)
        self.set_xy(112, y_start + 2)
        self.multi_cell(85, 5, f"TRABAJADOR: {trab['nombre'].upper()}\nRUT: {trab['rut']}\nCARGO: {trab['cargo']}\nC. COSTO: {trab.get('centro_costo','General')}\nFECHA: {date.today().strftime('%d-%m-%Y')}")
        
        self.set_y(y_start + 40)
        
        # --- BLOQUE 2: DETALLE (COLUMNAS) ---
        # Encabezados
        self.set_fill_color(220, 220, 220)
        self.cell(95, 8, "HABERES", 1, 0, 'C', 1)
        self.cell(95, 8, "DESCUENTOS", 1, 1, 'C', 1)
        self.ln()
        
        # Filas
        col_h = [
            ("Sueldo Base", datos['Base']),
            ("Gratificación Legal", datos['Grat']),
            ("Colación", int(datos['No_Imp']/2)),
            ("Movilización", int(datos['No_Imp']/2)),
            ("TOTAL IMPONIBLE", datos['Tot_Imp'])
        ]
        col_d = [
            ("AFP", datos['AFP']),
            ("Salud", datos['Salud']),
            ("Seguro Cesantía", datos['AFC']),
            ("Impuesto Único", datos['Impuesto']),
            ("TOTAL DESCUENTOS", datos['AFP']+datos['Salud']+datos['AFC']+datos['Impuesto'])
        ]
        
        y_filas = self.get_y()
        for i in range(max(len(col_h), len(col_d))):
            h = col_h[i] if i < len(col_h) else ("", "")
            d = col_d[i] if i < len(col_d) else ("", "")
            
            # Columna Izq
            self.cell(65, 6, str(h[0]), 'L'); self.cell(30, 6, f"{h[1]:,.0f}" if h[1]!="" else "", 'R')
            # Columna Der
            self.cell(65, 6, str(d[0]), 'L'); self.cell(30, 6, f"{d[1]:,.0f}" if d[1]!="" else "", 'R')
            self.ln()
            
        # --- BLOQUE 3: TOTALES ---
        self.ln(5)
        self.set_font('Arial', 'B', 12)
        self.cell(130, 10, "LÍQUIDO A PAGAR", 1, 0, 'R')
        self.cell(60, 10, f"${datos['Liquido']:,.0f}", 1, 1, 'C', 1)
        
        # --- BLOQUE 4: GLOSA Y FIRMAS ---
        if datos['Glosa']:
            self.ln(5)
            self.set_font('Arial', 'I', 8)
            self.cell(0, 5, datos['Glosa'], 0, 1, 'C')
            
        self.ln(30)
        self.set_font('Arial', '', 9)
        self.cell(90, 10, "__________________________", 0, 0, 'C')
        self.cell(90, 10, "__________________________", 0, 1, 'C')
        self.cell(90, 5, "FIRMA EMPLEADOR", 0, 0, 'C')
        self.cell(90, 5, "FIRMA TRABAJADOR", 0, 1, 'C')
        self.cell(90, 5, f"RUT: {emp['rut']}", 0, 0, 'C')
        self.cell(90, 5, f"RUT: {trab['rut']}", 0, 1, 'C')

        return self.output(dest='S').encode('latin-1')

# =============================================================================
# 3. INTERFAZ Y FLUJO DE DATOS
# =============================================================================

# --- SIDEBAR: DATOS MAESTROS COMPLETOS ---
with st.sidebar:
    st.image("https://www.previred.com/wp-content/uploads/2021/01/logo-previred.png", width=120)
    st.header("1. Datos Empresa")
    
    if 'emp' not in st.session_state: st.session_state.emp = {}
    st.session_state.emp['rut'] = st.text_input("RUT Empresa", "76.123.456-7")
    st.session_state.emp['nombre'] = st.text_input("Razón Social", "Servicios SpA")
    st.session_state.emp['rubro'] = st.selectbox("Rubro", ["Minería", "Retail", "Tecnología", "Construcción", "Servicios"])
    st.session_state.emp['direccion'] = st.text_input("Dirección", "Av. Providencia 1234")
    st.session_state.emp['ciudad'] = st.text_input("Ciudad", "Santiago")
    
    st.markdown("---")
    st.subheader("Representante Legal")
    st.session_state.emp['rep_nom'] = st.text_input("Nombre Rep. Legal")
    st.session_state.emp['rep_rut'] = st.text_input("RUT Rep. Legal")
    
    st.markdown("---")
    st.header("2. Datos Trabajador")
    if 'trab' not in st.session_state: st.session_state.trab = {}
    st.session_state.trab['rut'] = st.text_input("RUT Trabajador", "15.123.456-7")
    st.session_state.trab['nombre'] = st.text_input("Nombre Completo")
    st.session_state.trab['nacionalidad'] = st.text_input("Nacionalidad", "Chilena")
    st.session_state.trab['estado_civil'] = st.selectbox("Estado Civil", ["Soltero", "Casado"])
    st.session_state.trab['domicilio'] = st.text_input("Domicilio Trabajador")
    st.session_state.trab['cargo'] = st.text_input("Cargo a Contratar")
    st.session_state.trab['centro_costo'] = st.text_input("Centro de Costo", "Administración")

# --- CUERPO PRINCIPAL ---
st.title("HR Suite V110: All-in-One")

tabs = st.tabs(["💰 Liquidación & Finanzas", "🧠 Perfil & Selección", "📜 Generador Documentos", "🏭 Carga Masiva", "📊 Indicadores"])

# TAB 1: LIQUIDACIÓN BKS
with tabs[0]:
    st.subheader("Simulador de Remuneraciones")
    c1, c2 = st.columns(2)
    with c1:
        liq = st.number_input("Líquido Objetivo", 800000, step=10000)
        no_imp = st.number_input("Colación + Movilización", 60000)
        contrato = st.selectbox("Tipo Contrato", ["Indefinido", "Plazo Fijo", "Sueldo Empresarial"])
    with c2:
        salud = st.radio("Salud", ["Fonasa", "Isapre (UF)"])
        plan = st.number_input("Plan (UF)", 0.0) if salud == "Isapre (UF)" else 0.0
        
    if st.button("CALCULAR Y GENERAR PDF"):
        res = MotorCalculo.calcular_sueldo(liq, no_imp/2, no_imp/2, contrato, salud, plan)
        st.session_state.calculo = res # Guardar
        
        # HTML Preview (Estilo BKS)
        st.markdown(f"""
        <div class="liq-container">
            <div class="liq-header">
                <div><b>EMPRESA:</b> {st.session_state.emp['nombre']}<br>RUT: {st.session_state.emp['rut']}</div>
                <div style="text-align:right;"><b>TRABAJADOR:</b> {st.session_state.trab['nombre']}<br>RUT: {st.session_state.trab['rut']}</div>
            </div>
            <div class="liq-body">
                <div class="liq-col">
                    <b>HABERES</b><br>
                    Base: ${res['Base']:,.0f}<br>Gratif: ${res['Grat']:,.0f}<br>No Imp: ${res['No_Imp']:,.0f}
                </div>
                <div class="liq-col">
                    <b>DESCUENTOS</b><br>
                    AFP: ${res['AFP']:,.0f}<br>Salud: ${res['Salud']:,.0f}<br>Impuesto: ${res['Impuesto']:,.0f}
                </div>
            </div>
            <div class="liq-footer">LÍQUIDO A PAGAR: ${res['Liquido']:,.0f}</div>
        </div>
        """, unsafe_allow_html=True)
        
        if res['Glosa']: st.warning(res['Glosa'])
        
        # PDF Real
        pdf_gen = PDFLiquidacion()
        pdf_bytes = pdf_gen.generar_documento(res, st.session_state.emp, st.session_state.trab)
        st.download_button("📄 Descargar PDF Liquidación", pdf_bytes, "Liquidacion.pdf", "application/pdf")

# TAB 2: PERFIL CON RUBRO
with tabs[1]:
    st.subheader("Perfil de Cargo Inteligente")
    st.info(f"Generando perfil para el rubro: **{st.session_state.emp['rubro']}**")
    
    cargo = st.session_state.trab['cargo']
    if st.button("Generar Perfil"):
        # Lógica de Rubro
        rubro_context = ""
        if st.session_state.emp['rubro'] == "Minería": rubro_context = "con énfasis en seguridad, turnos y normativa minera."
        elif st.session_state.emp['rubro'] == "Retail": rubro_context = "enfocado en atención al cliente, ventas y control de inventario."
        elif st.session_state.emp['rubro'] == "Tecnología": rubro_context = "utilizando metodologías ágiles y herramientas digitales."
        
        st.markdown(f"""
        ### DESCRIPCIÓN DE CARGO: {cargo.upper()}
        **1. OBJETIVO:**
        Desempeñar funciones de {cargo} {rubro_context}, asegurando la continuidad operativa de {st.session_state.emp['nombre']}.
        
        **2. FUNCIONES PRINCIPALES (Sugeridas):**
        * Gestionar los indicadores clave del área de {cargo}.
        * Reportar a la gerencia sobre avances y desviaciones.
        * Asegurar el cumplimiento de los estándares de calidad del rubro {st.session_state.emp['rubro']}.
        
        **3. REQUISITOS:**
        * Experiencia comprobable en el sector {st.session_state.emp['rubro']}.
        * Título técnico o profesional afín.
        """)

# TAB 3: DOCUMENTOS (WORD REAL)
with tabs[2]:
    st.subheader("Generador de Contratos y Finiquitos")
    tipo_doc = st.selectbox("Tipo Documento", ["Contrato Trabajo Indefinido", "Contrato Plazo Fijo", "Finiquito"])
    
    if st.button("Generar Documento"):
        if not st.session_state.emp['rep_nom']:
            st.error("Falta ingresar Representante Legal en la barra lateral.")
        elif not st.session_state.trab['rut']:
            st.error("Falta ingresar datos del Trabajador.")
        else:
            # Crear Word con python-docx
            doc = Document()
            style = doc.styles['Normal']
            style.font.name = 'Arial'
            style.font.size = Pt(11)
            
            doc.add_heading(tipo_doc.upper(), 0)
            
            # Párrafo 1: Comparecencia
            p = doc.add_paragraph()
            p.add_run(f"En {st.session_state.emp['ciudad']}, a {date.today().strftime('%d de %B de %Y')}, entre ").bold = False
            p.add_run(f"{st.session_state.emp['nombre']}").bold = True
            p.add_run(f", RUT {st.session_state.emp['rut']}, representada por don/ña ").bold = False
            p.add_run(f"{st.session_state.emp['rep_nom']}").bold = True
            p.add_run(f", ambos domiciliados en {st.session_state.emp['direccion']}, en adelante el EMPLEADOR; y don/ña ").bold = False
            p.add_run(f"{st.session_state.trab['nombre']}").bold = True
            p.add_run(f", RUT {st.session_state.trab['rut']}, nacionalidad {st.session_state.trab['nacionalidad']}, estado civil {st.session_state.trab['estado_civil']}, domiciliado en {st.session_state.trab['domicilio']}, en adelante el TRABAJADOR, se ha convenido lo siguiente:").bold = False
            
            # Párrafo 2: Cargo
            doc.add_heading("PRIMERO: Naturaleza de los Servicios", level=2)
            doc.add_paragraph(f"El trabajador se compromete a desempeñar el cargo de {st.session_state.trab['cargo']}, realizando las funciones inherentes a dicho puesto en el rubro de {st.session_state.emp['rubro']}.")
            
            # Párrafo 3: Remuneración (Si hay cálculo)
            if st.session_state.calculo:
                doc.add_heading("SEGUNDO: Remuneración", level=2)
                doc.add_paragraph(f"Sueldo Base: ${st.session_state.calculo['Base']:,.0f}")
                doc.add_paragraph(f"Gratificación: ${st.session_state.calculo['Grat']:,.0f}")
                doc.add_paragraph(f"Colación y Movilización: ${st.session_state.calculo['No_Imp']:,.0f}")
            
            # Párrafo 4: Legal
            doc.add_heading("TERCERO: Normativa Vigente", level=2)
            doc.add_paragraph("LEY 40 HORAS: Las partes acuerdan que la jornada se ajustará a la reducción gradual establecida en la Ley 21.561.")
            doc.add_paragraph("LEY KARIN: Se incorpora el Protocolo de Prevención del Acoso Sexual, Laboral y Violencia.")
            
            # Guardar
            bio = io.BytesIO()
            doc.save(bio)
            bio.seek(0)
            st.download_button(f"⬇️ Descargar {tipo_doc}", bio, f"{tipo_doc}.docx")

# TAB 4: MASIVO CORREGIDO
with tabs[3]:
    st.subheader("Carga Masiva (Matriz ERP)")
    st.info("Esta plantilla contiene todas las columnas necesarias para generar contratos completos.")
    
    # Generar Plantilla Correcta
    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
    ws = workbook.add_worksheet()
    
    headers = [
        "RUT_TRABAJADOR", "NOMBRE_COMPLETO", "NACIONALIDAD", "ESTADO_CIVIL", 
        "DOMICILIO", "CARGO", "FECHA_INGRESO", "SUELDO_LIQUIDO", "TIPO_CONTRATO", 
        "PREVISION_SALUD"
    ]
    ws.write_row(0, 0, headers)
    # Ejemplo
    ws.write_row(1, 0, ["11.111.111-1", "Juan Perez", "Chilena", "Soltero", "Av. Siempre Viva 123", "Vendedor", "01/01/2025", 700000, "Indefinido", "Fonasa"])
    workbook.close()
    
    st.download_button("📥 Descargar Matriz Maestra (.xlsx)", output.getvalue(), "Matriz_Maestra_RRHH.xlsx")
    
    up = st.file_uploader("Subir Matriz Completa", type=['xlsx'])
    if up:
        st.success("Archivo cargado. Listo para procesar lotes.")

# TAB 5: INDICADORES
with tabs[4]:
    st.header("Indicadores Oficiales")
    col1, col2 = st.columns(2)
    col1.metric("UF Hoy", f"${IND['UF']:,.2f}")
    col2.metric("Sueldo Mínimo", f"${IND['IMM']:,.0f}")
    st.markdown("[🔗 Ir a Previred (Indicadores)](https://www.previred.com/indicadores-previsionales/)")
    st.markdown("[🔗 Ir a SII (Impuestos)](https://www.sii.cl/valores_y_fechas/impuesto_2da_categoria/impuesto2025.htm)")
