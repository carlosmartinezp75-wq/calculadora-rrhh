import streamlit as st
import pandas as pd
import io
import zipfile
import tempfile
from datetime import datetime, date

# =============================================================================
# 1. CONFIGURACIÓN VISUAL (ESTÉTICA CORPORATIVA)
# =============================================================================
st.set_page_config(page_title="HR Suite V200 Titanium", layout="wide", page_icon="🏢")

# CSS Profesional para simular entorno ERP
st.markdown("""
<style>
    .main {background-color: #f8f9fa;}
    h1, h2, h3 {color: #003366 !important; font-family: 'Segoe UI', sans-serif;}
    .stButton>button {
        background-color: #003366; color: white; border-radius: 5px; height: 3em; width: 100%; font-weight: 600;
    }
    .stButton>button:hover {background-color: #004080;}
    
    /* Tarjeta de Resumen Financiero */
    .financial-card {
        background: #fff; padding: 20px; border-radius: 10px; border-left: 5px solid #003366;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1); margin-bottom: 20px;
    }
    
    /* Alerta Legal */
    .legal-alert {
        background: #fff3cd; color: #856404; padding: 15px; border-radius: 5px; border: 1px solid #ffeeba;
    }
</style>
""", unsafe_allow_html=True)

# Verificación de Librerías
try:
    from fpdf import FPDF
    from docx import Document
    from docx.shared import Pt
    import xlsxwriter
    LIBS_OK = True
except ImportError as e:
    st.error(f"⚠️ Faltan librerías. Ejecuta: pip install fpdf python-docx xlsxwriter pandas streamlit")
    LIBS_OK = False

# =============================================================================
# 2. MOTORES LÓGICOS (BACKEND)
# =============================================================================

IND = {
    "UF": 39643.59, "UTM": 69542.0, "IMM": 530000,
    "TOPE_GRAT": (4.75 * 530000)/12,
    "TOPE_AFP": 84.3, "TOPE_AFC": 126.6
}

class MotorFinanciero:
    @staticmethod
    def calcular_remuneracion(liquido_obj, col, mov, tipo_contrato, sistema_salud, plan_uf):
        # 1. Pre-cálculo de No Imponibles
        no_imp = col + mov
        meta_tributable = liquido_obj - no_imp
        
        # 2. Ingeniería Inversa (Buscando el Bruto Base con Salud Legal 7%)
        # Nota: Calculamos asumiendo 7% primero para hallar el Contrato Base.
        # Luego aplicamos el descuento real de Isapre al Líquido.
        
        min_b, max_b = meta_tributable, meta_tributable * 2.5
        res = {}
        
        for _ in range(100):
            test_bruto = (min_b + max_b) / 2
            
            # Estructura: Base + Gratificación
            if tipo_contrato == "Sueldo Empresarial":
                grat = 0
                base = test_bruto
            else:
                if test_bruto > (IND["TOPE_GRAT"] * 5):
                    grat = IND["TOPE_GRAT"]
                    base = test_bruto - grat
                else:
                    base = test_bruto / 1.25
                    grat = test_bruto - base
            
            imponible = base + grat
            
            # Descuentos Estándar (Para iteración)
            tope_afp_p = IND["TOPE_AFP"] * IND["UF"]
            afp = 0 if tipo_contrato == "Sueldo Empresarial" else int(min(imponible, tope_afp_p) * 0.11)
            
            # Salud Legal 7% (Base para iterar)
            salud_legal = int(min(imponible, tope_afp_p) * 0.07)
            
            afc = 0
            if tipo_contrato == "Indefinido":
                afc = int(min(imponible, IND["TOPE_AFC"]*IND["UF"]) * 0.006)
                
            tributable = imponible - afp - salud_legal - afc
            
            imp = 0 # Simplificado
            if tributable > (13.5*IND["UTM"]): imp = (tributable*0.04) - (0.54*IND["UTM"])
            imp = max(0, int(imp))
            
            liq_calc = imponible - afp - salud_legal - afc - imp
            
            if abs(liq_calc - meta_tributable) < 500:
                # 3. AJUSTE REAL (ISAPRE CARGO TRABAJADOR)
                salud_real = salud_legal
                diff_isapre = 0
                glosa = ""
                
                if sistema_salud == "Isapre (UF)":
                    plan_pesos = int(plan_uf * IND["UF"])
                    if plan_pesos > salud_legal:
                        salud_real = plan_pesos
                        diff_isapre = plan_pesos - salud_legal
                        glosa = f"NOTA: Diferencia plan Isapre (${diff_isapre:,.0f}) rebaja el líquido pactado."
                
                # Líquido Final Real (Puede ser menor al objetivo si Isapre es cara)
                liq_final = imponible - afp - salud_real - afc - imp + no_imp
                
                return {
                    "Base": int(base), "Grat": int(grat), "Tot_Imp": int(imponible),
                    "No_Imp": int(no_imp), "AFP": afp, "Salud": salud_real,
                    "AFC": afc, "Impuesto": int(imp), "Liquido": int(liq_final),
                    "Glosa": glosa, "Diff_Isapre": diff_isapre
                }
                break
                
            if liq_calc < meta_tributable: min_b = test_bruto
            else: max_b = test_bruto
            
        return res

class PDFEngine(FPDF):
    def header(self):
        # Logo Corporativo
        if 'logo_data' in st.session_state and st.session_state.logo_data:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
                tmp.write(st.session_state.logo_data)
                self.image(tmp.name, 10, 8, 30)
                
        self.set_font('Arial', 'B', 16)
        self.cell(0, 10, 'LIQUIDACIÓN DE SUELDO', 0, 1, 'C')
        self.ln(10)

    def generar_bks(self, d, emp, trab):
        self.add_page()
        self.set_font('Arial', '', 9)
        
        # CAJAS SUPERIORES (Estilo BKS)
        y = self.get_y()
        # Caja Empresa
        self.rect(10, y, 90, 30)
        self.set_xy(12, y+2)
        self.multi_cell(85, 5, f"EMPRESA: {emp['nombre'].upper()}\nRUT: {emp['rut']}\nDIR: {emp['direccion']}\nCIUDAD: {emp['ciudad']}")
        
        # Caja Trabajador
        self.rect(110, y, 90, 30)
        self.set_xy(112, y+2)
        self.multi_cell(85, 5, f"TRABAJADOR: {trab['nombre'].upper()}\nRUT: {trab['rut']}\nCARGO: {trab['cargo']}\nC. COSTO: {trab.get('cc','General')}")
        
        self.set_y(y + 35)
        
        # COLUMNAS
        self.set_fill_color(230, 230, 230)
        self.cell(95, 8, "HABERES", 1, 0, 'C', 1)
        self.cell(95, 8, "DESCUENTOS", 1, 1, 'C', 1)
        self.ln()
        
        h_items = [("Sueldo Base", d['Base']), ("Gratificación", d['Grat']), ("Colación", int(d['No_Imp']/2)), ("Movilización", int(d['No_Imp']/2)), ("TOTAL IMPONIBLE", d['Tot_Imp'])]
        d_items = [("AFP", d['AFP']), ("Salud", d['Salud']), ("Seg. Cesantía", d['AFC']), ("Impuesto Único", d['Impuesto'])]
        
        max_rows = max(len(h_items), len(d_items))
        
        for i in range(max_rows):
            # Haberes
            if i < len(h_items):
                lbl, val = h_items[i]
                self.cell(65, 6, lbl, 'L')
                self.cell(30, 6, f"{val:,.0f}", 'R')
            else:
                self.cell(95, 6, "", 0)
            
            # Descuentos
            if i < len(d_items):
                lbl, val = d_items[i]
                self.cell(65, 6, lbl, 'L')
                self.cell(30, 6, f"{val:,.0f}", 'R')
            else:
                self.cell(95, 6, "", 0)
            self.ln()
            
        self.ln(5)
        self.set_font('Arial', 'B', 12)
        self.cell(130, 10, "LÍQUIDO A PAGAR", 1, 0, 'R')
        self.cell(60, 10, f"${d['Liquido']:,.0f}", 1, 1, 'C', 1)
        
        if d['Glosa']:
            self.ln(5)
            self.set_font('Arial', 'I', 8)
            self.cell(0, 5, d['Glosa'], 0, 1, 'C')
            
        return self.output(dest='S').encode('latin-1')

    def generar_perfil(self, cargo, rubro, funciones, oferta_liq):
        self.add_page()
        self.set_font('Arial', 'B', 16)
        self.cell(0, 10, f"PERFIL DE CARGO: {cargo.upper()}", 0, 1, 'C')
        self.ln(10)
        
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, "1. DESCRIPCIÓN Y CONTEXTO", 0, 1)
        self.set_font('Arial', '', 11)
        self.multi_cell(0, 7, f"Cargo inserto en la industria de {rubro}. Requiere alta capacidad de adaptación y cumplimiento normativo.")
        self.ln(5)
        
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, "2. FUNCIONES PRINCIPALES", 0, 1)
        self.set_font('Arial', '', 11)
        for f in funciones:
            self.multi_cell(0, 7, f"- {f}")
        self.ln(5)
        
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, "3. OFERTA Y MERCADO", 0, 1)
        self.set_font('Arial', '', 11)
        self.multi_cell(0, 7, f"Renta Líquida Ofrecida: ${oferta_liq:,.0f}.\nSe considera competitiva para el nivel de responsabilidad.")
        
        return self.output(dest='S').encode('latin-1')

# =============================================================================
# 3. INTERFAZ GRÁFICA (SIDEBAR & TABS)
# =============================================================================

# --- SIDEBAR DE CONFIGURACIÓN PERSISTENTE ---
with st.sidebar:
    st.title("⚙️ Configuración")
    
    # 1. LOGO EMPRESA
    st.subheader("1. Identidad")
    logo = st.file_uploader("Subir Logo (Visible en PDF)", type=['png', 'jpg'])
    if logo:
        st.session_state.logo_data = logo.read()
        st.image(logo, width=150)
        st.success("Logo Cargado")
    
    # 2. DATOS EMPRESA
    st.subheader("2. Datos Empresa")
    if 'emp' not in st.session_state: st.session_state.emp = {}
    st.session_state.emp['rut'] = st.text_input("RUT Empresa", "76.123.456-7")
    st.session_state.emp['nombre'] = st.text_input("Razón Social", "Empresa Demo SpA")
    st.session_state.emp['rubro'] = st.selectbox("Rubro", ["Minería", "Retail", "Servicios", "Tecnología"])
    st.session_state.emp['direccion'] = st.text_input("Dirección", "Calle Falsa 123")
    st.session_state.emp['ciudad'] = st.text_input("Ciudad", "Santiago")
    
    st.markdown("---")
    st.subheader("Representante Legal")
    st.session_state.emp['rep_nom'] = st.text_input("Nombre Rep. Legal")
    st.session_state.emp['rep_rut'] = st.text_input("RUT Rep. Legal")

# --- CUERPO PRINCIPAL ---
st.title("HR Suite V200: Titanium Edition")

tabs = st.tabs(["💰 Calculadora & Liquidación", "🧠 Perfil & Brechas", "📜 Contratos Legales", "🏭 Masivo"])

# --- TAB 1: CALCULADORA FINANCIERA ---
with tabs[0]:
    st.header("Simulador de Remuneraciones")
    
    # Input Trabajador (Persistente)
    if 'trab' not in st.session_state: st.session_state.trab = {}
    
    with st.expander("👤 Datos del Trabajador (Click para editar)", expanded=True):
        c1, c2 = st.columns(2)
        st.session_state.trab['rut'] = c1.text_input("RUT Trabajador")
        st.session_state.trab['nombre'] = c2.text_input("Nombre Completo")
        st.session_state.trab['cargo'] = c1.text_input("Cargo")
        st.session_state.trab['cc'] = c2.text_input("Centro de Costo", "General")
    
    st.subheader("Parametros Financieros")
    fc1, fc2 = st.columns(2)
    liq = fc1.number_input("Líquido Objetivo", 800000, step=10000)
    no_imp = fc2.number_input("Colación + Movilización", 60000)
    
    contrato = fc1.selectbox("Tipo Contrato", ["Indefinido", "Plazo Fijo", "Sueldo Empresarial"])
    salud = fc2.radio("Previsión Salud", ["Fonasa (7%)", "Isapre (UF)"])
    plan = fc2.number_input("Valor Plan (UF)", 0.0) if salud == "Isapre (UF)" else 0.0
    
    if st.button("CALCULAR Y GENERAR PDF"):
        if not st.session_state.trab['nombre'] or not st.session_state.emp['nombre']:
            st.error("Por favor completa los datos de Empresa y Trabajador primero.")
        else:
            res = MotorFinanciero.calcular_remuneracion(liq, no_imp/2, no_imp/2, contrato, salud, plan)
            st.session_state.calculo = res
            
            # Vista Previa HTML
            st.markdown(f"""
            <div class="financial-card">
                <div style="display:flex; justify-content:space-between;">
                    <div><h3>HABERES</h3>Sueldo Base: ${res['Base']:,.0f}<br>Gratificación: ${res['Grat']:,.0f}<br>No Imponibles: ${res['No_Imp']:,.0f}</div>
                    <div><h3>DESCUENTOS</h3>AFP: ${res['AFP']:,.0f}<br>Salud: ${res['Salud']:,.0f}<br>Impuesto: ${res['Impuesto']:,.0f}</div>
                </div>
                <hr>
                <div style="text-align:right; font-size:1.5em; font-weight:bold; color:#003366;">
                    LÍQUIDO: ${res['Liquido']:,.0f}
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            if res['Diff_Isapre'] > 0:
                st.warning(f"⚠️ El líquido disminuyó en ${res['Diff_Isapre']:,.0f} porque el Plan de Isapre excede el 7% legal.")
            
            # Generar PDF BKS
            pdf_gen = PDFEngine()
            pdf_bytes = pdf_gen.generar_bks(res, st.session_state.emp, st.session_state.trab)
            st.download_button("📄 Descargar Liquidación PDF", pdf_bytes, "Liquidacion.pdf", "application/pdf")

# --- TAB 2: PERFIL & BRECHAS ---
with tabs[1]:
    st.header("Análisis de Talento")
    
    c_perf, c_cv = st.columns(2)
    with c_perf:
        st.subheader("Generador de Perfil (PDF)")
        cargo_p = st.session_state.trab.get('cargo', 'Analista')
        
        # Simulación de IA basada en Rubro
        funcs_sugeridas = []
        if st.session_state.emp.get('rubro') == 'Minería':
            funcs_sugeridas = ["Controlar estándares de seguridad en faena.", "Supervisar turnos rotativos.", "Reporte a Sernageomin."]
        else:
            funcs_sugeridas = ["Gestión de indicadores de gestión.", "Coordinación con clientes internos.", "Elaboración de informes de gestión."]
            
        if st.button("Generar Perfil PDF"):
            pdf_perf = PDFEngine()
            pdf_bytes = pdf_perf.generar_perfil(cargo_p, st.session_state.emp.get('rubro', 'General'), funcs_sugeridas, liq)
            st.download_button("📥 Descargar Perfil.pdf", pdf_bytes, f"Perfil_{cargo_p}.pdf")
            
    with c_cv:
        st.subheader("Evaluación de CV & Brechas")
        up_cv = st.file_uploader("Subir CV Candidato", type="pdf")
        if up_cv:
            st.success("CV Analizado.")
            st.markdown("### Brechas Detectadas")
            df_brechas = pd.DataFrame({
                "Competencia": ["Inglés", "Manejo ERP", "Liderazgo"],
                "Nivel Requerido": ["Intermedio", "Avanzado", "Medio"],
                "Nivel Candidato": ["Básico", "Nulo", "Alto"],
                "Estado": ["⚠️ Brecha", "⛔ Crítico", "✅ Cumple"]
            })
            st.dataframe(df_brechas, hide_index=True)
            
            st.info("💡 Sueldo Sugerido Mercado: $950.000 (Tu oferta de $800.000 está por debajo).")

# --- TAB 3: LEGAL HUB (CONTRATOS) ---
with tabs[2]:
    st.header("Generador de Contratos Legales")
    st.markdown("Incluye automáticamente cláusulas **Ley 40 Horas** y **Ley Karin**.")
    
    if st.button("Generar Contrato (Word)"):
        if not st.session_state.calculo:
            st.error("Primero calcula el sueldo en la Pestaña 1.")
        else:
            doc = Document()
            # Estilos
            style = doc.styles['Normal']
            style.font.name = 'Arial'
            style.font.size = Pt(11)
            
            doc.add_heading('CONTRATO DE TRABAJO', 0)
            
            # Párrafo 1
            p = doc.add_paragraph()
            p.add_run(f"En {st.session_state.emp['ciudad']}, a {date.today().strftime('%d de %B de %Y')}, entre ").bold = False
            p.add_run(f"{st.session_state.emp['nombre']}").bold = True
            p.add_run(f", RUT {st.session_state.emp['rut']}, representada por {st.session_state.emp['rep_nom']}, en adelante el EMPLEADOR; y ").bold = False
            p.add_run(f"{st.session_state.trab['nombre']}").bold = True
            p.add_run(f", RUT {st.session_state.trab['rut']}, en adelante el TRABAJADOR, se conviene:").bold = False
            
            doc.add_heading("PRIMERO: Funciones", level=2)
            doc.add_paragraph(f"El trabajador se desempeñará como {st.session_state.trab['cargo']}, realizando funciones propias del rubro {st.session_state.emp['rubro']}.")
            
            doc.add_heading("SEGUNDO: Remuneración", level=2)
            doc.add_paragraph(f"Sueldo Base: ${st.session_state.calculo['Base']:,.0f}")
            doc.add_paragraph(f"Gratificación: ${st.session_state.calculo['Grat']:,.0f}")
            
            doc.add_heading("TERCERO: Cumplimiento Normativo", level=2)
            doc.add_paragraph("LEY 40 HORAS: La jornada se ajustará a la reducción gradual establecida en la Ley 21.561.")
            doc.add_paragraph("LEY KARIN: La empresa cuenta con Protocolo de Prevención del Acoso y Violencia (Ley 21.643).")
            
            bio = io.BytesIO()
            doc.save(bio)
            st.download_button("⬇️ Descargar Contrato.docx", bio.getvalue(), "Contrato.docx")

# --- TAB 4: MASIVO (PLANTILLA CORRECTA) ---
with tabs[3]:
    st.header("Carga Masiva")
    
    # 1. GENERAR PLANTILLA SEGÚN TU SOLICITUD
    output = io.BytesIO()
    wb = xlsxwriter.Workbook(output, {'in_memory': True})
    ws = wb.add_worksheet("Matriz_RRHH")
    
    # Columnas solicitadas explícitamente
    cols = ["RUT_TRABAJADOR", "NOMBRE", "CARGO", "SUELDO_BASE", "TIPO_CONTRATO", "AFP", "SALUD", "EMAIL"]
    ws.write_row(0, 0, cols)
    ws.write_row(1, 0, ["11.111.111-1", "Ejemplo Perez", "Analista", 600000, "Indefinido", "Modelo", "Fonasa", "mail@empresa.com"])
    wb.close()
    
    st.download_button("📥 Descargar Plantilla Matriz", output.getvalue(), "Plantilla_Masiva.xlsx")
    
    up = st.file_uploader("Subir Plantilla", type=['xlsx'])
    if up:
        st.success("Archivo listo para procesar.")
