#!/bin/bash

# Script de instalación automática para HR Suite Pro
# Uso: chmod +x install.sh && ./install.sh

echo "🚀 Instalando HR Suite Pro..."
echo "=================================="

# Verificar Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 no está instalado. Por favor instálalo primero."
    exit 1
fi

echo "✅ Python 3 encontrado"

# Crear entorno virtual
echo "📦 Creando entorno virtual..."
python3 -m venv hr_suite_env

# Activar entorno virtual
source hr_suite_env/bin/activate

# Actualizar pip
echo "🔄 Actualizando pip..."
pip install --upgrade pip

# Instalar dependencias
echo "📚 Instalando dependencias..."
pip install -r requirements.txt

echo "✅ Instalación completada!"
echo ""
echo "🚀 Para ejecutar HR Suite Pro:"
echo "source hr_suite_env/bin/activate"
echo "streamlit run hr_suite_complete.py"
echo ""
echo "📖 O ejecutar directamente:"
echo "bash run.sh"
