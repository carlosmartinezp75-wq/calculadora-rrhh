🏢 HR Suite Pro - Sistema Integral de Recursos Humanos
📋 Descripción General
HR Suite Pro es una aplicación integral de gestión de recursos humanos desarrollada en Streamlit que combina cálculo de liquidaciones, finiquitos, evaluación de competencias, generación de documentos legales y análisis de brechas de talento.

✨ Funcionalidades Principales
💰 1. Calculadora Inteligente de Liquidaciones
Motor financiero avanzado con lógica isapre
Ingeniería inversa para determinar sueldo bruto desde líquido deseado
Análisis de cargas laborales en tiempo real
Cálculo de valor hora y porcentajes de descuentos
Alertas automáticas por alta carga o planes isapre excesivos
📄 2. Calculadora Avanzada de Finiquitos
Múltiples causales legales: Renuncia voluntaria, Art. 161, Art. 168, muerte, etc.
Vacaciones proporcionales con factor 1.25 días/mes
Años de servicio con tope de 90 UF
Conceptos adicionales y cálculos personalizados
Conversión automática a UF para verificación legal
📋 3. Generador de Documentos Legales
Contratos de trabajo (indefinido/plazo fijo) con cumplimiento normativo
Cartas de amonestación personalizadas
Cartas de desvinculación con base legal
Certificados de trabajo y avvisos previos
Cumplimiento Ley 40 Horas y Ley KARIN
🎯 4. Sistema de Evaluación de Competencias
Perfiles de cargo por área funcional
Evaluación de brechas técnica y blandas
Planes de carrera personalizados en 3 fases
Cronograma de desarrollo detallado
Recomendaciones automáticas de capacitación
🏗️ 5. Constructor de Perfiles de Cargo
Perfiles detallados por seniority y área
Competencias técnicas y blandas parametrizadas
Análisis presupuestario de ofertas
Modalidades de trabajo (presencial/híbrido/remoto)
Funciones y responsabilidades estructuradas
📊 6. Centro de Reportes Masivos
Importación masiva de datos (Excel)
Plantillas predefinidas para trabajadores, contratos, evaluaciones
Reportes automáticos: liquidaciones, finiquitos, brechas, rotación
Procesamiento batch con validación de errores
⚖️ 7. Centro Legal y Compliance
Checklists automáticos para ingreso, término y auditoría
Calculadoras especializadas: horas extras, proporcional vacaciones, indemnizaciones
Actualizaciones normativas en tiempo real
Capacitaciones obligatorias por área
🚀 Instalación y Configuración
Requisitos Previos
Python 3.8+
Sistema operativo: Windows, macOS, Linux
4GB RAM mínimo recomendado
Instalación Automática
1.
Descarga todos los archivos en una carpeta
2.
Ejecuta el instalador automático:
bash
chmod +x install.sh
./install.sh
Instalación Manual
1.
Crear entorno virtual:
bash
python -m venv hr_suite_env
source hr_suite_env/bin/activate  # Linux/macOS
hr_suite_env\Scripts\activate     # Windows
2.
Instalar dependencias:
bash
pip install -r requirements.txt
Ejecutar la Aplicación
bash
# Opción 1: Script automático
bash run.sh

# Opción 2: Comando directo
streamlit run hr_suite_complete.py
📱 Acceso
URL Local: http://localhost:8501
Se abre automáticamente en el navegador
📖 Guía de Usuario
Configuración Inicial
1.
Sidebar - Configuración Global:
Subir logo de la empresa
Completar datos de la empresa
Ingresar datos del trabajador
2.
Indicadores Superiores:
UF, UTM, IMM actualizadas
Tope de indemnización en UF
Flujo de Trabajo Típico
Para Crear una Liquidación:
1.
Tab 1 - Calculadora Sueldos
2.
Ingresar sueldo líquido objetivo
3.
Configurar colación, movilización, tipo contrato
4.
Seleccionar sistema de salud (Fonasa/Isapre)
5.
"Calcular Liquidación"
6.
Descargar PDF generado
Para Calcular un Finiquito:
1.
Tab 2 - Finiquitos Avanzados
2.
Ingresar fechas de ingreso y término
3.
Seleccionar causal legal
4.
Configurar días de vacaciones tomados
5.
"Calcular Finiquito Completo"
6.
Verificar totales y descargar
Para Evaluar un Candidato:
1.
Tab 4 - Evaluación Competencias
2.
Crear perfil de cargo (si no existe)
3.
Ingresar nombre del candidato
4.
Evaluar competencias técnicas y blandas
5.
"Evaluar y Generar Plan"
6.
Revisar brechas y plan de desarrollo
Para Generar Documentos:
1.
Tab 3 - Gestión Documentos
2.
Seleccionar tipo de documento
3.
Completar parámetros específicos
4.
"Generar Documento"
5.
Descargar archivo DOCX
🏗️ Arquitectura Técnica
Clases Principales
MotorFinanciero: Cálculos de liquidaciones e ingeniería inversa
MotorFiniquitos: Cálculos avanzados de finiquitos por causal
MotorCompetencias: Evaluación y planes de carrera
GeneradorDocumentos: Creación de contratos y cartas legales
PDFGenerator: Generación de documentos PDF profesionales
Indicadores Legales 2025
python
UF = 39,643.59
UTM = 69,542.0
IMM = 530,000
Tope_Indemnizacion = 90 UF
Tope_Gratificacion = 4.75 IMM/12
Competencias Base por Área
Administración
Técnicas: Contabilidad, Administración, Excel
Blandas: Comunicación, Liderazgo, Análisis
Tecnología
Técnicas: Programación, Bases de Datos, Redes
Blandas: Resolución Problemas, Innovación, Trabajo Equipo
Operaciones
Técnicas: Gestión Operaciones, Procesos, Logística
Blandas: Planificación, Organización, Orientación Resultados
📊 Datos y Reportes
Tipos de Reportes Disponibles
1.
Liquidaciones Mensuales: Complete payroll processing
2.
Finiquitos Pendientes: Outstanding termination payments
3.
Análisis de Brechas: Competency gap analysis by area
4.
Rotación de Personal: Turnover analysis and causes
5.
Cumplimiento Legal: Regulatory compliance status
6.
Presupuesto Salarial: Personnel cost analysis
Formatos de Exportación
PDF: Documentos oficiales y reportes
Excel: Datos tabulares y análisis masivo
DOCX: Contratos y cartas legales
JSON: Integración con otros sistemas
⚖️ Cumplimiento Legal
Leyes y Normativas Incluidas
Ley 20.123: Régimen de subcontratación
Ley 20.348: Reducción gradual 40 horas
Ley KARIN: Prevención acoso laboral/sexual
Código del Trabajo: Artículos 159, 161, 168
Normativas AFP/Isapre: Sistema previsional chileno
Calculadoras Legales
Horas Extras: Cálculo con recargos 25%/50%
Proporcional Vacaciones: Factor 15 días/año
Indemnización Años: Tope 90 UF por año
Cargas Laborales: AFP 11%, Salud 7%, AFC 0.6%
🔧 Personalización
Configuración Avanzada
python
# Modificar indicadores económicos
IND = {
    "UF": 39643.59,
    "UTM": 69542.0,
    # ... otros indicadores
}

# Agregar nuevas competencias
COMPETENCIAS_BASE["Nueva_Area"] = {
    "Conocimientos_Tecnicos": {
        "Nueva_Competencia": ["Básico", "Intermedio", "Avanzado", "Experto"]
    }
}
Temas y Branding
CSS Personalizable: Modificar estilos en st.markdown()
Logos Empresariales: Carga automática en sidebar
Colores Corporativos: Configurables por empresa
🆘 Soporte y Troubleshooting
Problemas Comunes
1.
Error de dependencias:
bash
pip install --upgrade pip
pip install -r requirements.txt --force-reinstall
2.
Puerto ocupado:
bash
streamlit run hr_suite_complete.py --server.port 8502
3.
Error de fuentes:
Instalar fuentes del sistema
Reiniciar la aplicación
Logs y Debug
bash
# Ver logs en tiempo real
streamlit run hr_suite_complete.py --logger.level debug
Contacto
Email: soporte@hrsuite.com
WhatsApp: +56 9 XXXX XXXX
Documentación: https://docs.hrsuite.com
📈 Roadmap y Próximas Versiones
v3.1 (En Desarrollo)
 Integración con APIs bancarias
 App móvil companion
 Dashboard ejecutivo en tiempo real
 Módulo de reclutamiento AI
v3.2 (Planificado)
 Integración con sistemas de asistencia
 Análisis predictivo de rotación
 Módulo de compensación variable
 Certificación ISO 9001
v4.0 (Futuro)
 IA para matching candidato-cargo
 Análisis de sentimientos en evaluaciones
 Blockchain para contratos digitales
 API pública para integraciones
📄 Licencia
Este software está licenciado bajo MIT License. Ver archivo LICENSE para más detalles.

🤝 Contribuciones
Las contribuciones son bienvenidas. Por favor:

1.
Fork el repositorio
2.
Crear branch para feature (git checkout -b feature/nueva-funcionalidad)
3.
Commit cambios (git commit -am 'Agregar nueva funcionalidad')
4.
Push al branch (git push origin feature/nueva-funcionalidad)
5.
Crear Pull Request
HR Suite Pro - Desarrollado con ❤️ para optimizar la gestión de recursos humanos

Versión: 2025.11.28 | Autor: MiniMax Agent
