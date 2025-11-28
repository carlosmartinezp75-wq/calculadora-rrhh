# 🚀 INSTRUCCIONES PARA SUBIR A TU HOSTING DE STREAMLIT

## 📋 ¿QUÉ VAMOS A HACER?
Vamos a subir tu nueva HR Suite Completa al sitio web que ya tienes funcionando:
**https://calculadora-rrhh-nmdzsklwgkuhqkgs2r3yvg.streamlit.app**

## 🗂️ ARCHIVOS LISTOS PARA SUBIR

Los siguientes archivos están optimizados para tu hosting:

1. **`streamlit_app.py`** - Aplicación principal (reemplaza tu app.py actual)
2. **`requirements.txt`** - Dependencias necesarias
3. **`.streamlit/config.toml`** - Configuración para hosting
4. **`fondo.png`** - Imagen de fondo (puedes mantener la actual)

## 🔧 PASOS PARA ACTUALIZAR TU REPOSITORIO

### PASO 1: Preparar los Archivos
1. **Descarga** los archivos de este workspace
2. **Guarda** todos en una carpeta temporal en tu computadora

### PASO 2: Subir a tu Repositorio de GitHub

#### OPCIÓN A - Directamente desde GitHub (Recomendada)
1. Ve a tu repositorio: https://github.com/carlosmartinezp75-wq/calculadora-rrhh
2. Haz clic en **"uploading an existing file"** (es el botón para subir archivos)
3. **ARRASTRA** los archivos nuevos:
   - `streamlit_app.py` → Reemplazará tu `app.py` actual
   - `requirements.txt` → Reemplazará el actual
   - `.streamlit/config.toml` → Crear la carpeta `.streamlit` y subir el archivo
   - `fondo.png` → Opcional (puedes mantener tu imagen actual)

#### OPCIÓN B - Desde tu Computadora
1. **Clona** tu repositorio:
   ```bash
   git clone https://github.com/carlosmartinezp75-wq/calculadora-rrhh.git
   cd calculadora-rrhh
   ```

2. **Copia** los nuevos archivos a la carpeta del repositorio

3. **Sube** los cambios:
   ```bash
   git add .
   git commit -m "Actualización HR Suite Completa v2025.11.28"
   git push origin main
   ```

### PASO 3: Verificar el Deploy
1. **Espera** 2-3 minutos después del push
2. **Visita** tu sitio: https://calculadora-rrhh-nmdzsklwgkuhqkgs2r3yvg.streamlit.app
3. **Debería** mostrar la nueva aplicación completa

## 🎯 ¿QUÉ CAMBIA EN TU APLICACIÓN?

### ✅ FUNCIONALIDADES AGREGADAS:
- **7 Módulos Completos**: Calculadora, Documentos, Finiquitos, Candidatos, Perfiles, Brechas, Carrera
- **Cumplimiento Legal Chileno**: UF, UTM, IMM actualizadas 2025
- **Generación de PDFs**: Contratos profesionales
- **Evaluación de Competencias**: Sistema completo con análisis de gaps
- **Planes de Carrera**: Generación automática de desarrollo profesional

### 🔄 ESTRUCTURA MEJORADA:
- **Interfaz Moderna**: Diseño optimizado para web
- **Navegación por Pestañas**: 7 secciones organizadas
- **Cálculos Automáticos**: Finiquitos con múltiples causas legales
- **Reportes Descargables**: PDF, Excel, TXT

## 🛠️ SOLUCIÓN DE PROBLEMAS

### ❌ "Error de Deploy"
**Solución:**
1. Verifica que `requirements.txt` esté en la raíz del repositorio
2. Asegúrate de que el archivo principal se llame `streamlit_app.py`
3. Revisa que no haya errores de sintaxis en el código

### ❌ "Archivo no encontrado"
**Solución:**
1. Verifica que `.streamlit/config.toml` esté en la carpeta correcta
2. Asegúrate de que los nombres de archivos coincidan exactamente

### ❌ "Dependencias faltantes"
**Solución:**
1. El `requirements.txt` incluye todas las librerías necesarias
2. Si persiste el error, Streamlit mostrará qué librería falta

### ❌ "La página no carga"
**Solución:**
1. **Espera 5-10 minutos** después del push (primera vez puede tardar)
2. **Verifica** la URL: https://calculadora-rrhh-nmdzsklwgkuhqkgs2r3yvg.streamlit.app
3. **Revisa** los logs en GitHub Actions si están disponibles

## 📞 CARACTERÍSTICAS PRINCIPALES DE LA NUEVA APP

### 💰 **1. Calculadora de Sueldos Inteligente**
- Cálculo directo desde sueldo bruto
- Cálculo por objetivo (sueldo líquido deseado)
- AFP: Capital, Modelo, Provida, Habitat
- ISAPRE: Banmédica, Consalud, Cruz Blanca, Más Vida

### 📝 **2. Generador de Documentos Legales**
- Contratos de trabajo profesionales
- Cartas de amonestación
- Cartas de desvinculación
- Formatos PDF automáticos

### 💸 **3. Calculadora de Finiquitos**
- Múltiples causas legales (Art. 159, 161, 168)
- Indemnizaciones automáticas
- Vacaciones proporcionales
- Tope 90 UF por año de servicio

### 👥 **4. Evaluación de Candidatos**
- Template Excel para carga masiva
- Evaluación por competencias
- Ranking automático
- Sistema de recomendaciones

### 🎯 **5. Constructor de Perfiles**
- Perfiles por área funcional
- Competencias técnicas y blandas
- Análisis de compensación
- Modalidades de trabajo

### 📊 **6. Análisis de Brechas**
- Comparación competencias actuales vs. requeridas
- Identificación de gaps críticos
- Visualización de áreas de mejora
- Métricas de desarrollo

### 🚀 **7. Planes de Carrera**
- Desarrollo en 3 fases
- Cronogramas de capacitación
- Seguimiento de progreso
- Recomendaciones automáticas

## 🎨 PERSONALIZACIÓN DISPONIBLE

### 🖼️ **Cambiar Imagen de Fondo**
1. Prepara una imagen de fondo (fondo.png)
2. Súbela a tu repositorio (reemplaza la actual)
3. La app la mostrará automáticamente

### 🎨 **Cambiar Colores del Tema**
Edita el archivo `.streamlit/config.toml`:
```toml
[theme]
primaryColor = "#3b82f6"      # Color principal
backgroundColor = "#ffffff"    # Fondo
secondaryBackgroundColor = "#f8fafc"  # Fondo secundario
textColor = "#1e293b"         # Texto
```

### 📝 **Personalizar Competencias**
En `streamlit_app.py`, modifica el diccionario `COMPETENCIAS_BASE` para agregar/quitar competencias según tu empresa.

## 🚀 ¡LISTO!

Una vez que subas los archivos:
1. ✅ Tu app estará 100% operativa en línea
2. ✅ Funcionará 24/7 sin necesidad de tu computadora
3. ✅ Tendrá todas las funcionalidades de RRHH que necesitas
4. ✅ Será accesible desde cualquier dispositivo

**¡Tu HR Suite estará lista para usar desde cualquier lugar del mundo! 🌍**