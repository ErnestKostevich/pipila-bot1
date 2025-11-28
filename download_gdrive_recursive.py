#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔽 PIPILA - Simple Dropbox Downloader
Works with your exact Dropbox link
"""

import os
import sys
import urllib.request
import zipfile
import shutil
from pathlib import Path

def log(msg):
    print(msg, flush=True)

def download_and_extract():
    """Download ZIP from Dropbox and extract"""
    
    # ✅ Твоя ПРЯМАЯ ссылка Dropbox (заменил dl=0 на dl=1)
    dropbox_url = "https://www.dropbox.com/scl/fi/gg6o8vc2dgc7ks9z8x1bx/Fuentes-de-informaci-n-RAG?rlkey=tt8cpimwv232fwk436esxhhp2&st=k9zfpx4z&dl=1"
    
    zip_path = "/tmp/documents.zip"
    output_dir = "documents"
    
    log("=" * 70)
    log("🔽 PIPILA - Downloading documents")
    log("=" * 70)
    
    # Удалить старую папку
    if os.path.exists(output_dir):
        log("🧹 Cleaning old folder...")
        shutil.rmtree(output_dir)
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Скачать ZIP
    log(f"📥 Downloading from Dropbox...")
    try:
        urllib.request.urlretrieve(dropbox_url, zip_path)
        size_mb = os.path.getsize(zip_path) / (1024 * 1024)
        log(f"✅ Downloaded: {size_mb:.2f} MB")
    except Exception as e:
        log(f"❌ Download failed: {e}")
        sys.exit(1)
    
    # Распаковать ZIP
    log(f"📦 Extracting ZIP...")
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(output_dir)
        log(f"✅ Extracted to: {output_dir}")
    except Exception as e:
        log(f"❌ Extract failed: {e}")
        os.remove(zip_path)
        sys.exit(1)
    
    # Удалить ZIP
    os.remove(zip_path)
    
    # Очистка macOS мусора
    log("🧹 Cleaning macOS files...")
    for root, dirs, files in os.walk(output_dir, topdown=False):
        # Удалить .DS_Store и ._* файлы
        for file in files:
            if file == '.DS_Store' or file.startswith('._'):
                try:
                    os.remove(os.path.join(root, file))
                except:
                    pass
        # Удалить __MACOSX папки
        for dir_name in dirs:
            if dir_name == '__MACOSX':
                try:
                    shutil.rmtree(os.path.join(root, dir_name))
                except:
                    pass
    
    # Подсчёт файлов
    file_count = 0
    for root, dirs, files in os.walk(output_dir):
        for file in files:
            if file.lower().endswith(('.pdf', '.docx', '.doc', '.txt')):
                file_count += 1
    
    log("")
    log("=" * 70)
    log("📊 RESULT")
    log("=" * 70)
    log(f"✅ Files downloaded: {file_count}")
    
    if file_count > 0:
        log("")
        log("📂 Folder structure:")
        folders = {}
        for root, dirs, files in os.walk(output_dir):
            for file in files:
                ext = Path(file).suffix.lower()
                if ext in ['.pdf', '.docx', '.doc', '.txt']:
                    rel_dir = os.path.relpath(root, output_dir)
                    if rel_dir not in folders:
                        folders[rel_dir] = []
                    folders[rel_dir].append(file)
        
        for folder, files in sorted(folders.items()):
            if folder == '.':
                log(f"  📁 (root): {len(files)} files")
            else:
                log(f"  📁 {folder}: {len(files)} files")
            for f in files[:3]:  # Показать первые 3 файла
                log(f"     • {f}")
            if len(files) > 3:
                log(f"     ... and {len(files) - 3} more")
        
        log("")
        log(f"✅ Ready for RAG: {file_count} documents")
        log("=" * 70)
    else:
        log("⚠️ WARNING: No PDF/DOCX/TXT files found!")
        log("=" * 70)
        sys.exit(1)

if __name__ == "__main__":
    download_and_extract()
