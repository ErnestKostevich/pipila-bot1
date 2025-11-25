#!/usr/bin/env python3
"""
Скрипт для рекурсивной загрузки Google Drive папки со всеми вложенными папками
Работает с любой глубиной вложенности
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
    except ImportError:
        print("📦 Устанавливаем gdown...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "gdown", "-q"])
        print("✅ gdown установлен")

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
    """Скачать папку рекурсивно"""
    import gdown
    
    folder_id = get_folder_id(folder_url)
    if not folder_id:
        print(f"❌ Не удалось извлечь ID из URL: {folder_url}")
        return False
    
    print(f"📂 ID папки: {folder_id}")
    print(f"📥 Скачиваем в: {output_dir}")
    
    # Создать выходную директорию
    os.makedirs(output_dir, exist_ok=True)
    
    try:
        # gdown.download_folder поддерживает рекурсивную загрузку
        gdown.download_folder(
            id=folder_id,
            output=output_dir,
            quiet=False,
            use_cookies=False,
            remaining_ok=True
        )
        return True
    except Exception as e:
        print(f"⚠️ Ошибка при загрузке: {e}")
        return False

def count_files(directory, extensions=['.pdf', '.docx', '.doc', '.txt']):
    """Подсчитать количество файлов"""
    count = 0
    for root, dirs, files in os.walk(directory):
        for file in files:
            if any(file.lower().endswith(ext) for ext in extensions):
                count += 1
    return count

def list_files(directory, extensions=['.pdf', '.docx', '.doc', '.txt']):
    """Вывести список файлов"""
    files_found = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if any(file.lower().endswith(ext) for ext in extensions):
                rel_path = os.path.relpath(os.path.join(root, file), directory)
                file_size = os.path.getsize(os.path.join(root, file))
                files_found.append((rel_path, file_size))
    return files_found

def main():
    print("=" * 60)
    print("📥 PIPILA - Descargador Recursivo de Google Drive")
    print("=" * 60)
    print()
    
    # Установить gdown
    install_gdown()
    print()
    
    # URL папки
    folder_url = "https://drive.google.com/drive/folders/1vK_GFk3M3vA4vQksZGnGCM027sv39Rz4"
    output_dir = "documents"
    
    print(f"🔗 URL: {folder_url}")
    print(f"📂 Папка: {output_dir}")
    print()
    
    # Скачать
    print("🔄 Начинаем загрузку...")
    print()
    success = download_folder_recursive(folder_url, output_dir)
    print()
    
    # Проверить результаты
    if success and os.path.exists(output_dir):
        file_count = count_files(output_dir)
        print("=" * 60)
        print(f"✅ Загрузка завершена!")
        print(f"📊 Найдено файлов: {file_count}")
        print()
        
        if file_count > 0:
            print("📂 Список файлов:")
            print()
            files = list_files(output_dir)
            for rel_path, size in sorted(files):
                size_mb = size / (1024 * 1024)
                print(f"  ✓ {rel_path} ({size_mb:.2f} MB)")
            print()
        else:
            print("⚠️ Файлы не найдены!")
            print()
            print("💡 Возможные причины:")
            print("  1. Папка Google Drive не публичная")
            print("  2. Неправильный URL")
            print("  3. В папке нет поддерживаемых файлов (PDF, DOCX, TXT)")
            print()
            print("🔧 Решение:")
            print("  Сделай папку публичной: Share → Anyone with link → Viewer")
            print()
    else:
        print("❌ Загрузка не удалась")
        print()
        print("💡 Альтернативное решение:")
        print("  Загрузи документы напрямую в GitHub:")
        print()
        print("  mkdir documents")
        print("  # Скопируй PDF/DOCX файлы в documents/")
        print("  git add documents/")
        print("  git commit -m 'Add: Documentos'")
        print("  git push")
        print()
    
    print("=" * 60)

if __name__ == "__main__":
    main()
