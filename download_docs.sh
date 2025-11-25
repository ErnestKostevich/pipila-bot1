#!/bin/bash
set -e

echo "📥 Descargando documentos de Google Drive..."

# Устанавливаем gdown
pip install gdown --quiet

# Создаем папку
mkdir -p documents
cd documents

# Скачиваем папку целиком
echo "🔄 Descargando carpeta completa..."
gdown --folder https://drive.google.com/drive/folders/1vK_GFk3M3vA4vQksZGnGCM027sv39Rz4 --remaining-ok

echo "✅ Documentos descargados!"
ls -lh
