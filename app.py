import streamlit as st
import pandas as pd
import io
import zipfile
import tempfile
import os
from datetime import datetime, date
from dateutil.relativedelta import relativedelta

# =============================================================================
# 1. CONFIGURACIÓN VISUAL Y LIBRERÍAS
# =============================================================================
st.set_page_config(page_title="HR Suite V300 Expert", layout="wide", page_icon="🏢")

st.markdown("""
<style>
    .main {background-color: #f4f6f9;}
    h1, h2, h3 {color: #0d2b4e; font-family: 'Segoe UI', sans-serif;}
    .stButton>button {
        background-color: #0d2b4e; color: white; border-radius: 6px; height: 3em; width: 100%; font-weight: bold;
    }
    .metric-card {
        background: white; padding: 15px; border-radius: 8px; border-left: 5px solid #0d2b4e; box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        color: #333; margin-bottom: 10px;
    }
    .alert-box {
        padding: 15px; background-color: #fff3cd; color: #856404; border: 1px solid #ffeeba; border-radius: 5px; margin-bottom: 15px;
    }
</style>
""", unsafe_allow_html=True)

try:
    from fpdf import FPDF
    from docx import Document
    from docx.shared import Pt
    import xlsxwriter
    LIBS_OK = True
except ImportError:
    st.error("⚠️ Faltan librerías. Instala: pip install fpdf python-docx xlsxwriter pandas streamlit python-dateutil")
    st.stop()

# =============================================================================
# 2. DATOS MAESTROS (INDICADORES NOV 2025)
# =============================================================================
IND = {
    "UF": 39643.59, "UTM": 69542.0, "IMM": 530000,
    "TOPE_GRAT": (4.75 * 530000)/12,
    "TOPE_AFP": 84.3, "TOPE_AFC": 126.6,
    "TOPE_INDEM_ANOS": 90
}

# =============================================================================
# 3. MOTORES LÓGICOS (BACKEND)
# =============================================================================

class MotorFinanciero:
    @staticmethod
    def calcular_liquidacion(liquido_obj, col, mov, tipo_contrato, salud_sistema, plan_uf):
        """
        Calcula sueldo bruto desde líquido.
        Regla de Negocio: Si Isapre > 7%, la diferencia se descuenta del líquido objetivo.
        """
        no_imp = col + mov
        meta = liquido_obj - no_imp
        min_b, max_b = meta, meta * 2.5
        res = {}
        
        # Iteración para encontrar el Bruto Base (Asumiendo 7% Salud Legal)
        for _ in range(100):
            test = (min_b + max_b) / 2
            
            # Estructura Base vs Gratificación
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
            
            # Descuentos Estándar (Para encontrar la base imponible correcta)
            tope_afp_p = IND["TOPE_AFP"] * IND["UF"]
            afp = 0 if tipo_contrato == "Sueldo Empresarial" else int(min(imponible, tope_afp_p) * 0.11)
            
            salud_legal = int(min(imponible, tope_afp_p) * 0.07)
            
            afc = 0
            if tipo_contrato == "Indefinido":
                afc = int(min(imponible, IND["TOPE_AFC"]*IND["UF"]) * 0.006)
            
            tributable = imponible - afp - salud_legal - afc
            imp = 0 
            if tributable > (13.5*IND["UTM"]): imp = (tributable*0.04) - (0.54*IND["UTM"])
            imp = max(0, int(imp))
            
            liq_calc = imponible - afp - salud_legal - afc - imp
            
            if abs(liq_calc - meta) < 500:
                # UNA VEZ ENCONTRADO EL BRUTO, APLICAMOS LA REALIDAD DE LA ISAPRE
                salud_real = salud_legal
                diff_isapre = 0
                glosa = ""
                
                if salud_sistema == "Isapre (UF)":
                    valor_plan = int(plan_uf * IND["UF"])
                    # Si el plan es mayor al 7%, el descuento aumenta y el líquido baja
                    if valor_plan > salud_legal:
                        salud_real = valor_plan
                        diff_isapre = valor_plan - salud_legal
                        glosa = f"NOTA: Plan Isapre ({plan_uf} UF) excede el 7% legal. La diferencia de ${diff_isapre:,.0f} es de cargo del trabajador."
                
                # Recálculo final del líquido real
                liq_final = imponible - afp - salud_real - afc - imp + no_imp
                
                return {
                    "Base": int(base), "Grat": int(grat), "Tot_Imp": int(imponible),
                    "No_Imp": int(no_imp), "AFP": afp, "Salud": salud_real,
                    "AFC": afc, "Impuesto": int(imp), "Liquido": int(liq_final),
                    "Glosa": glosa, "Diff_Isapre": diff_isapre
                }
                break
            
            if liq_calc < meta: min_b = test
            else: max_b = test
        return res

class ExpertoFiniquitos:
    @staticmethod
    def calcular(f_inicio, f_termino, sueldo_base, gratificacion, col_mov, causal, dias_vac_tomados):
        dias_totales = (f_termino - f_inicio).days + 1
        antiguedad = relativedelta(f_termino, f_inicio)
        
        # Tope Indemnización (90 UF)
        tope_indem_pesos = IND["TOPE_INDEM_ANOS"] * IND["UF"]
        # Base cálculo indemnización incluye colación y movilización (Topada)
        base_indem = min((sueldo_base + gratificacion + col_mov), tope_indem_pesos)
        
        # Vacaciones Proporcionales
        factor_diario = 1.25 / 30
        dias_vac_ganados = dias_totales * factor_diario
        saldo_dias_vac = max(0, dias_vac_ganados - dias_vac_tomados)
        
        valor_dia_vac = (sueldo_base + gratificacion) / 30
        monto_vacaciones = int(saldo_dias_vac * valor_dia_vac)
        
        monto_anos = 0
        monto_aviso = 0
        anos_pago = 0
        
        if causal == "Necesidades de la Empresa (Art. 161)":
            anos_pago = antiguedad.years
            if antiguedad.months >= 6:
                anos_pago += 1
            if anos_pago > 11: anos_pago = 11
            
            monto_anos = int(base_indem * anos_pago)
            monto_aviso = int(base_indem)
            
        return {
            "Antiguedad": f"{antiguedad.years} años, {antiguedad.months} meses",
            "Base Calculo Indem": int(base_indem),
            "Dias Vacaciones Pendientes": round(saldo_dias_vac, 2),
            "Monto Vacaciones": monto_vacaciones,
            "Anos Servicio": monto_anos,
            "Mes Aviso": monto_aviso,
            "Total Finiquito": monto_vacaciones + monto_anos + monto_aviso
        }

class PDFGenerator(FPDF):
    def header(self):
        if 'empresa' in st.session_state and st.session_state.empresa.get('logo_bytes'):
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
                    tmp.write(st.session_state.empresa['logo_bytes'])
                    tmp_path = tmp.name
                self.image(tmp_path, 10, 8, 30)
            except:
                pass
        self.set_font('Arial', 'B', 14)
        self.cell(0, 10, 'DOCUMENTO OFICIAL', 0, 1, 'C')
        self.ln(10)

    def generar_liquidacion_bks(self, d, emp, trab):
        self.add_page()
        self.set_font('Arial', '', 9)
        
        y = self.get_y()
        # Caja Empresa
        self.rect(10, y, 90, 30); self.set_xy(12, y+2)
        self.multi_cell(85, 5, f"EMPRESA: {emp.get('nombre','')}\nRUT: {emp.get('rut','')}\nDIR: {emp.get('direccion','')}")
        
        # Caja Trabajador
        self.rect(110, y, 90, 30); self.set_xy(112, y+2)
        self.multi_cell(85, 5, f"TRABAJADOR: {trab.get('nombre','')}\nRUT: {trab.get('rut','')}\nCARGO: {trab.get('cargo','')}")
        
        self.set_y(y + 35)
        
        # Columnas
        self.set_fill_color(220, 220, 220)
        self.cell(95, 8, "HABERES", 1, 0, 'C', 1)
        self.cell(95, 8, "DESCUENTOS", 1, 1, 'C', 1)
        self.ln()
        
        h_list = [("Sueldo Base", d['Base']), ("Gratificación", d['Grat']), ("Movilización", int(d['No_Imp']/2)), ("Colación", int(d['No_Imp']/2))]
        d_list = [("AFP", d['AFP']), ("Salud", d['Salud']), ("AFC", d['AFC']), ("Impuesto", d['Impuesto'])]
        
        for i in range(max(len(h_list), len(d_list))):
            h = h_list[i] if i < len(h_list) else ("", "")
            d = d_list[i] if i < len(d_list) else ("", "")
            self.cell(65, 6, h[0], 'L'); self.cell(30, 6, f"{h[1]:,.0f}" if h[1]!="" else "", 'R')
            self.cell(65, 6, d[0], 'L'); self.cell(30, 6, f"{d[1]:,.0f}" if d[1]!="" else "", 'R', 1)
            self.ln()
            
        self.ln(5)
        self.set_font('Arial', 'B', 12)
        self.cell(130, 10, "LÍQUIDO A PAGAR", 1, 0, 'R')
        self.cell(60, 10, f"${d['Liquido']:,.0f}", 1, 1, 'C', 1)
        
        if d['Glosa']:
            self.ln(5); self.set_font('Arial', 'I', 8)
            self.cell(0, 5, d['Glosa'], 0, 1, 'C')
            
        return self.output(dest='S').encode('latin-1')
    
    def generar_perfil(self, cargo, rubro, funciones):
        self.add_page()
        self.set_font('Arial', 'B', 16)
        self.cell(0, 10, f"PERFIL DE CARGO: {cargo}", 0, 1, 'C')
        self.ln(10)
        
        self.set_font('Arial', '', 12)
        self.multi_cell(0, 10, f"Rubro de la Empresa: {rubro}")
        self.ln(5)
        
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, "Funciones Principales:", 0, 1)
        self.set_font('Arial', '', 12)
        for f in funciones:
            self.multi_cell(0, 8, f"- {f}")
            
        return self.output(dest='S').encode('latin-1')

# =============================================================================
# 4. INTERFAZ DE USUARIO (SIDEBAR PERSISTENTE)
# =============================================================================

# Inicialización de Estado
if 'empresa' not in st.session_state: 
    st.session_state.empresa = {"nombre": "", "rut": "", "rep_legal": "", "direccion": "", "logo_bytes": None, "rubro": "General"}
if 'trabajador' not in st.session_state:
    st.session_state.trabajador = {"nombre": "", "rut": "", "cargo": "", "fecha_ingreso": date.today()}
if 'calculo' not in st.session_state:
    st.session_state.calculo = None

with st.sidebar:
    st.image("https://www.previred.com/wp-content/uploads/2021/01/logo-previred.png", width=100)
    st.title("Configuración Global")
    
    # 1. LOGO
    logo = st.file_uploader("1. Logo Empresa", type=['png', 'jpg'])
    if logo: 
        st.session_state.empresa['logo_bytes'] = logo.read()
        st.success("Logo Cargado")
        
    # 2. DATOS EMPRESA
    with st.expander("2. Datos Empresa", expanded=True):
        st.session_state.empresa['rut'] = st.text_input("RUT Empresa", st.session_state.empresa.get('rut', ''))
        st.session_state.empresa['nombre'] = st.text_input("Razón Social", st.session_state.empresa.get('nombre', ''))
        st.session_state.empresa['rep_legal'] = st.text_input("Representante Legal", st.session_state.empresa.get('rep_legal', ''))
        st.session_state.empresa['direccion'] = st.text_input("Dirección", st.session_state.empresa.get('direccion', ''))
        st.session_state.empresa['rubro'] = st.selectbox("Rubro", ["Minería", "Retail", "Servicios", "Tecnología"], index=2)
        
    # 3. DATOS TRABAJADOR
    with st.expander("3. Datos Trabajador (Ficha)", expanded=True):
        st.session_state.trabajador['rut'] = st.text_input("RUT Trabajador", st.session_state.trabajador.get('rut', ''))
        st.session_state.trabajador['nombre'] = st.text_input("Nombre Completo", st.session_state.trabajador.get('nombre', ''))
        st.session_state.trabajador['cargo'] = st.text_input("Cargo", st.session_state.trabajador.get('cargo', ''))
        st.session_state.trabajador['fecha_ingreso'] = st.date_input("Fecha Ingreso", st.session_state.trabajador.get('fecha_ingreso', date.today()))

# =============================================================================
# 5. CUERPO PRINCIPAL (TABS)
# =============================================================================
st.title("HR Suite V300: Expert Edition")



tabs = st.tabs(["💰 Calculadora Sueldos", "🏁 Experto Finiquitos", "🧠 Perfil & Mercado", "📜 Legal Hub", "🏭 Masivo"])

# --- TAB 1: CALCULADORA SUELDOS ---
with tabs[0]:
    st.header("Simulador de Liquidaciones (Lógica Isapre)")
    
    col1, col2 = st.columns(2)
    with col1:
        liq_obj = st.number_input("Sueldo Líquido Objetivo", 800000, step=10000)
        no_imp = st.number_input("Colación + Movilización", 60000)
    with col2:
        tipo_cont = st.selectbox("Contrato", ["Indefinido", "Plazo Fijo", "Sueldo Empresarial"])
        salud = st.radio("Salud", ["Fonasa", "Isapre (UF)"])
        plan = st.number_input("Plan UF", 0.0) if salud == "Isapre (UF)" else 0.0
        
    if st.button("CALCULAR & GENERAR PDF"):
        res = MotorFinanciero.calcular_liquidacion(liq_obj, no_imp/2, no_imp/2, tipo_cont, salud, plan)
        st.session_state.calculo = res # Guardar para contratos
        
        # Mostrar Alerta si Isapre impacta líquido
        if res['Diff_Isapre'] > 0:
            st.warning(f"⚠️ El líquido baja en ${res['Diff_Isapre']:,.0f} porque el plan Isapre excede el 7% legal.")
            
        # Tarjeta Visual
        st.markdown(f"""
        <div class="metric-card">
            <div style="display:flex; justify-content:space-between;">
                <div><h3>HABERES</h3>Base: ${res['Base']:,.0f}<br>Grat: ${res['Grat']:,.0f}</div>
                <div><h3>DESCUENTOS</h3>AFP: ${res['AFP']:,.0f}<br>Salud: ${res['Salud']:,.0f}</div>
            </div>
            <hr>
            <h2 style="text-align:right;">LÍQUIDO: ${res['Liquido']:,.0f}</h2>
        </div>
        """, unsafe_allow_html=True)
        
        # PDF
        pdf = PDFGenerator()
        pdf_bytes = pdf.generar_liquidacion_bks(res, st.session_state.empresa, st.session_state.trabajador)
        st.download_button("📄 Descargar PDF BKS", pdf_bytes, "Liquidacion.pdf", "application/pdf")

# --- TAB 2: EXPERTO FINIQUITOS ---
with tabs[1]:
    st.header("Calculadora Experta de Finiquitos")
    st.info("Calcula vacaciones proporcionales y años de servicio con tope de 90 UF.")
    
    c_fin1, c_fin2 = st.columns(2)
    with c_fin1:
        f_termino = st.date_input("Fecha Término", date.today())
        causal = st.selectbox("Causal", ["Renuncia Voluntaria", "Necesidades de la Empresa (Art. 161)", "Otras"])
        vac_tomados = st.number_input("Días Vacaciones ya tomados", 0.0)
    
    with c_fin2:
        # Usamos datos de la sesión si existen
        base_calc = st.session_state.calculo['Base'] if st.session_state.calculo else 0
        grat_calc = st.session_state.calculo['Grat'] if st.session_state.calculo else 0
        
        sb = st.number_input("Sueldo Base", value=base_calc)
        gr = st.number_input("Gratificación", value=grat_calc)
        colmov = st.number_input("Col + Mov (Base Indemnización)", value=60000)
        
    if st.button("CALCULAR FINIQUITO"):
        if not st.session_state.trabajador['fecha_ingreso']:
            st.error("Debes ingresar la FECHA DE INGRESO en el Sidebar.")
        else:
            res_fin = ExpertoFiniquitos.calcular(
                st.session_state.trabajador['fecha_ingreso'], 
                f_termino, sb, gr, colmov, causal, vac_tomados
            )
            
            st.markdown(f"""
            <div class="metric-card">
                <h3>Resumen Finiquito</h3>
                <p><b>Antigüedad:</b> {res_fin['Antiguedad']}</p>
                <p><b>Vacaciones Proporcionales:</b> ${res_fin['Monto Vacaciones']:,.0f} ({res_fin['Dias Vacaciones Pendientes']} días)</p>
                <p><b>Indemnización Años Servicio:</b> ${res_fin['Anos Servicio']:,.0f}</p>
                <p><b>Aviso Previo:</b> ${res_fin['Mes Aviso']:,.0f}</p>
                <hr>
                <h2 style="color:#28a745;">TOTAL A PAGAR: ${res_fin['Total Finiquito']:,.0f}</h2>
            </div>
            """, unsafe_allow_html=True)

# --- TAB 3: PERFIL & IA ---
with tabs[2]:
    st.header("Perfil de Cargo & Selección")
    
    col_p1, col_p2 = st.columns(2)
    with col_p1:
        st.subheader("Generador de Perfil")
        cargo_p = st.session_state.trabajador['cargo']
        rubro = st.session_state.empresa['rubro']
        
        if st.button("Generar Perfil PDF"):
            # Lógica Rubro Simulado
            funcs = ["Supervisión de procesos críticos.", "Gestión de KPI del área.", "Reportabilidad a gerencia."]
            pdf = PDFGenerator()
            pdf_bytes = pdf.generar_perfil(cargo_p, rubro, funcs)
            st.download_button("Descargar Perfil.pdf", pdf_bytes, "Perfil.pdf")
            
    with col_p2:
        st.subheader("Análisis Mercado")
        oferta = st.number_input("Tu Oferta Líquida", 800000)
        mercado = 950000 # Simulado
        diff = oferta - mercado
        if diff < 0:
            st.error(f"Estás ${abs(diff):,.0f} bajo el mercado. Riesgo de fuga.")
        else:
            st.success("Oferta competitiva.")

# --- TAB 4: LEGAL HUB ---
with tabs[3]:
    st.header("Generador de Contratos")
    opcion = st.selectbox("Tipo Documento", ["Contrato Indefinido", "Carta Amonestación"])
    
    if st.button("Generar Word"):
        if not st.session_state.empresa['nombre'] or not st.session_state.trabajador['nombre']:
             st.error("Faltan datos en el Sidebar.")
        else:
            doc = Document()
            doc.add_heading(opcion.upper(), 0)
            
            # Datos desde sesión persistente
            doc.add_paragraph(f"En {st.session_state.empresa.get('direccion', 'Santiago')}, comparecen {st.session_state.empresa['nombre']} (RUT {st.session_state.empresa['rut']}), representada por {st.session_state.empresa['rep_legal']}, y don/ña {st.session_state.trabajador['nombre']} (RUT {st.session_state.trabajador['rut']})...")
            
            doc.add_heading("CUMPLIMIENTO LEGAL", level=2)
            doc.add_paragraph("LEY 40 HORAS: Se ajustará a la reducción gradual establecida en la Ley 21.561.")
            doc.add_paragraph("LEY KARIN: Se incorpora protocolo de prevención del acoso (Ley 21.643).")
            
            if st.session_state.calculo:
                doc.add_heading("REMUNERACIÓN", level=2)
                doc.add_paragraph(f"Sueldo Base: ${st.session_state.calculo['Base']:,.0f}")
                doc.add_paragraph(f"Gratificación: ${st.session_state.calculo['Grat']:,.0f}")

            bio = io.BytesIO()
            doc.save(bio)
            st.download_button(f"Descargar {opcion}", bio.getvalue(), f"{opcion}.docx")

# --- TAB 5: MASIVO ---
with tabs[4]:
    st.header("Carga Masiva")
    st.info("Descarga la plantilla oficial con las columnas correctas para importación.")
    
    # Plantilla Correcta
    output = io.BytesIO()
    wb = xlsxwriter.Workbook(output, {'in_memory': True})
    ws = wb.add_worksheet()
    cols = ["RUT", "NOMBRE", "CARGO", "SUELDO_BASE", "AFP", "SALUD", "EMAIL", "CENTRO_COSTO"]
    ws.write_row(0, 0, cols)
    wb.close()
    
    st.download_button("📥 Descargar Plantilla Correcta", output.getvalue(), "Plantilla_Masiva.xlsx")
    
    up = st.file_uploader("Subir Excel", type=['xlsx'])
    if up: st.success("Listo para procesar.")
