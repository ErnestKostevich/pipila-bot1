#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔽 PIPILA - Descargador Recursivo Google Drive
Скачивает ВСЕ файлы из папки включая вложенные подпапки
"""

import os
import sys
import subprocess
import re
from pathlib import Path

def install_gdown():
    """Установить gdown если нужно"""
    try:
        import gdown
        print("✅ gdown уже установлен")
        return True
    except ImportError:
        print("📦 Устанавливаем gdown...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "gdown>=5.1.0", "-q"])
            print("✅ gdown установлен")
            return True
        except Exception as e:
            print(f"❌ Ошибка установки gdown: {e}")
            return False

def get_folder_id(url):
    """Извлечь ID папки из URL"""
    patterns = [
        r'folders/([a-zA-Z0-9_-]+)',
        r'id=([a-zA-Z0-9_-]+)'
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

def download_folder_recursive(folder_url, output_dir="documents"):
    """
    Скачать папку рекурсивно со всеми вложенными подпапками
    """
    import gdown
    
    folder_id = get_folder_id(folder_url)
    if not folder_id:
        print(f"❌ Не удалось извлечь ID из URL: {folder_url}")
        return False
    
    print(f"📂 ID папки: {folder_id}")
    print(f"📥 Скачиваем в: {output_dir}")
    print()
    
    # Создать выходную директорию
    os.makedirs(output_dir, exist_ok=True)
    
    try:
        # gdown.download_folder с поддержкой вложенных папок
        print("🔄 Начинаем рекурсивную загрузку...")
        print("⏳ Это может занять несколько минут...")
        print()
        
        gdown.download_folder(
            id=folder_id,
            output=output_dir,
            quiet=False,
            use_cookies=False,
            remaining_ok=True
        )
        
        print()
        print("✅ Загрузка завершена!")
        return True
        
    except Exception as e:
        print(f"⚠️ Ошибка при загрузке: {e}")
        print()
        print("💡 Возможные причины:")
        print("  1. Папка Google Drive не публичная")
        print("  2. Нет доступа к папке")
        print("  3. Проблемы с сетью")
        print()
        print("🔧 Решение:")
        print("  Сделай папку публичной:")
        print("  1. Открой Google Drive")
        print("  2. Правый клик на папку → Share")
        print("  3. Change to 'Anyone with the link'")
        print("  4. Access: Viewer")
        print("  5. Copy link")
        print()
        return False

def count_files(directory, extensions=['.pdf', '.docx', '.doc', '.txt']):
    """Подсчитать количество файлов рекурсивно"""
    count = 0
    for root, dirs, files in os.walk(directory):
        for file in files:
            if any(file.lower().endswith(ext) for ext in extensions):
                count += 1
    return count

def list_files(directory, extensions=['.pdf', '.docx', '.doc', '.txt']):
    """Вывести список файлов рекурсивно"""
    files_found = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if any(file.lower().endswith(ext) for ext in extensions):
                rel_path = os.path.relpath(os.path.join(root, file), directory)
                file_size = os.path.getsize(os.path.join(root, file))
                files_found.append((rel_path, file_size))
    return files_found

def main():
    print("=" * 70)
    print("🔽 PIPILA - Descargador Recursivo de Google Drive")
    print("=" * 70)
    print()
    
    # Установить gdown
    if not install_gdown():
        print("❌ No se pudo instalar gdown")
        sys.exit(1)
    
    print()
    
    # URL папки Oscar Casco
    folder_url = "https://drive.google.com/drive/folders/1vK_GFk3M3vA4vQksZGnGCM027sv39Rz4"
    output_dir = "documents"
    
    print(f"🔗 URL: {folder_url}")
    print(f"📂 Carpeta destino: {output_dir}")
    print()
    
    # Скачать
    success = download_folder_recursive(folder_url, output_dir)
    
    # Проверить результаты
    if success and os.path.exists(output_dir):
        file_count = count_files(output_dir)
        
        print()
        print("=" * 70)
        print(f"📊 RESULTADO")
        print("=" * 70)
        print(f"✅ Archivos descargados: {file_count}")
        print()
        
        if file_count > 0:
            print("📂 Lista de archivos:")
            print()
            files = list_files(output_dir)
            
            # Группировка по подпапкам
            folders = {}
            for rel_path, size in files:
                folder = os.path.dirname(rel_path)
                if not folder:
                    folder = "root"
                if folder not in folders:
                    folders[folder] = []
                folders[folder].append((os.path.basename(rel_path), size))
            
            # Вывод по папкам
            for folder, folder_files in sorted(folders.items()):
                print(f"  📁 {folder}/")
                for filename, size in sorted(folder_files):
                    size_mb = size / (1024 * 1024)
                    print(f"     ✓ {filename} ({size_mb:.2f} MB)")
                print()
            
            print(f"📚 Total: {file_count} archivos para RAG")
            print()
        else:
            print("⚠️ No se encontraron archivos PDF/DOCX/TXT!")
            print()
            print("💡 Posibles causas:")
            print("  1. La carpeta está vacía")
            print("  2. No hay archivos con extensiones soportadas")
            print("  3. La carpeta no es pública")
            print()
            print("🔧 Solución:")
            print("  1. Verifica que la carpeta contenga archivos")
            print("  2. Asegúrate que la carpeta sea pública")
            print("  3. Revisa los permisos de acceso")
            print()
    else:
        print()
        print("=" * 70)
        print("❌ LA DESCARGA FALLÓ")
        print("=" * 70)
        print()
        print("🔧 SOLUCIÓN ALTERNATIVA:")
        print()
        print("Opción 1: Hacer la carpeta pública")
        print("  1. Abre Google Drive")
        print("  2. Click derecho en la carpeta → Compartir")
        print("  3. Cambiar a 'Cualquiera con el enlace'")
        print("  4. Acceso: Lector")
        print("  5. Copiar enlace")
        print()
        print("Opción 2: Subir archivos directamente a GitHub")
        print("  (No recomendado - archivos grandes)")
        print()
        print("Opción 3: Usar otro servicio de almacenamiento")
        print("  - Dropbox")
        print("  - OneDrive")
        print("  - Amazon S3")
        print()
    
    print("=" * 70)
    print("🏁 Proceso completado")
    print("=" * 70)

if __name__ == "__main__":
    main()
