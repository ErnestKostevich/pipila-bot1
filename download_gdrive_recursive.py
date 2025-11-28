#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔽 PIPILA - Simple Dropbox Downloader
Works with your exact Dropbox link
VERSION: 2.0 with detailed logging
"""

import os
import sys
import urllib.request
import zipfile
import shutil
from pathlib import Path

def log(msg):
    """Print with flush for build logs"""
    print(f"[DOWNLOAD] {msg}", flush=True)
    sys.stdout.flush()

def download_and_extract():
    """Download ZIP from Dropbox and extract"""
    
    # ✅ Твоя ПРЯМАЯ ссылка Dropbox (заменил dl=0 на dl=1)
    dropbox_url = "https://www.dropbox.com/scl/fi/gg6o8vc2dgc7ks9z8x1bx/Fuentes-de-informaci-n-RAG?rlkey=tt8cpimwv232fwk436esxhhp2&st=k9zfpx4z&dl=1"
    
    zip_path = "/tmp/documents.zip"
    output_dir = "documents"
    
    log("=" * 70)
    log("🔽 PIPILA - Downloading documents from Dropbox")
    log("=" * 70)
    log(f"Dropbox URL: {dropbox_url[:80]}...")
    log(f"Temp ZIP path: {zip_path}")
    log(f"Output directory: {output_dir}")
    log("")
    
    # Удалить старую папку
    if os.path.exists(output_dir):
        log(f"🧹 Cleaning old folder: {output_dir}")
        try:
            shutil.rmtree(output_dir)
            log("✅ Old folder removed")
        except Exception as e:
            log(f"⚠️ Warning cleaning folder: {e}")
    
    # Создать папку
    try:
        os.makedirs(output_dir, exist_ok=True)
        log(f"✅ Created directory: {output_dir}")
    except Exception as e:
        log(f"❌ FAILED to create directory: {e}")
        sys.exit(1)
    
    # Скачать ZIP
    log("")
    log("📥 Starting download from Dropbox...")
    try:
        # Add headers to avoid being blocked
        req = urllib.request.Request(
            dropbox_url,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
        )
        
        with urllib.request.urlopen(req, timeout=300) as response:
            with open(zip_path, 'wb') as out_file:
                # Download with progress
                total_size = int(response.headers.get('content-length', 0))
                log(f"Total size: {total_size / (1024*1024):.2f} MB")
                
                downloaded = 0
                chunk_size = 8192
                
                while True:
                    chunk = response.read(chunk_size)
                    if not chunk:
                        break
                    out_file.write(chunk)
                    downloaded += len(chunk)
                    
                    # Progress every 5MB
                    if downloaded % (5 * 1024 * 1024) < chunk_size:
                        log(f"Downloaded: {downloaded / (1024*1024):.1f} MB")
        
        size_mb = os.path.getsize(zip_path) / (1024 * 1024)
        log(f"✅ Download complete: {size_mb:.2f} MB")
        
        # Verify file exists
        if not os.path.exists(zip_path):
            log(f"❌ CRITICAL: ZIP file not found at {zip_path}")
            sys.exit(1)
            
        if os.path.getsize(zip_path) < 1000:
            log(f"❌ CRITICAL: ZIP file too small ({os.path.getsize(zip_path)} bytes)")
            sys.exit(1)
            
    except Exception as e:
        log(f"❌ Download FAILED: {e}")
        log(f"Error type: {type(e).__name__}")
        import traceback
        log(f"Traceback: {traceback.format_exc()}")
        sys.exit(1)
    
    # Распаковать ZIP
    log("")
    log(f"📦 Extracting ZIP to: {output_dir}")
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            file_list = zip_ref.namelist()
            log(f"Files in ZIP: {len(file_list)}")
            
            # Show first 5 files
            for i, fname in enumerate(file_list[:5]):
                log(f"  - {fname}")
            if len(file_list) > 5:
                log(f"  ... and {len(file_list) - 5} more files")
            
            log("Extracting files directly to documents/ (flat structure)...")
            
            # ✅ EXTRACT FLAT: All files go directly to documents/
            extracted_count = 0
            for member in zip_ref.namelist():
                # Skip directories
                if member.endswith('/'):
                    continue
                    
                # Get just the filename (no path)
                filename = os.path.basename(member)
                
                # Skip if no filename
                if not filename:
                    continue
                
                # Skip system files
                if filename.startswith('.') or filename.startswith('_'):
                    continue
                
                # Skip __MACOSX
                if '__MACOSX' in member:
                    continue
                
                # Extract to documents/ directly
                try:
                    source = zip_ref.open(member)
                    target_path = os.path.join(output_dir, filename)
                    
                    # If file exists, add number
                    if os.path.exists(target_path):
                        name, ext = os.path.splitext(filename)
                        counter = 1
                        while os.path.exists(target_path):
                            target_path = os.path.join(output_dir, f"{name}_{counter}{ext}")
                            counter += 1
                    
                    with open(target_path, "wb") as target:
                        target.write(source.read())
                    
                    source.close()
                    extracted_count += 1
                except Exception as e:
                    log(f"⚠️ Failed to extract {filename}: {e}")
            
            log(f"✅ Extracted {extracted_count} files to: {output_dir}")
            
        log(f"✅ Extraction complete")
        
        # Verify extraction
        if not os.path.exists(output_dir):
            log(f"❌ CRITICAL: Output directory not found after extraction")
            sys.exit(1)
            
    except zipfile.BadZipFile as e:
        log(f"❌ Extract FAILED: Bad ZIP file - {e}")
        log("This means the downloaded file is not a valid ZIP")
        log("Possible reasons:")
        log("  1. Dropbox link is not a direct download link")
        log("  2. Dropbox returned an error page instead of the file")
        log("  3. Download was interrupted")
        
        # Try to read first 100 bytes to see what we got
        try:
            with open(zip_path, 'rb') as f:
                first_bytes = f.read(100)
                log(f"First 100 bytes of file: {first_bytes[:100]}")
        except:
            pass
            
        sys.exit(1)
        
    except Exception as e:
        log(f"❌ Extract FAILED: {e}")
        import traceback
        log(f"Traceback: {traceback.format_exc()}")
        sys.exit(1)
    
    # Удалить ZIP
    try:
        os.remove(zip_path)
        log(f"✅ Removed temp ZIP file")
    except Exception as e:
        log(f"⚠️ Warning removing ZIP: {e}")
    
    # Очистка macOS мусора
    log("")
    log("🧹 Cleaning macOS system files...")
    removed_count = 0
    
    for root, dirs, files in os.walk(output_dir, topdown=False):
        # Удалить .DS_Store и ._* файлы
        for file in files:
            if file == '.DS_Store' or file.startswith('._'):
                try:
                    file_path = os.path.join(root, file)
                    os.remove(file_path)
                    removed_count += 1
                except Exception as e:
                    log(f"⚠️ Could not remove {file}: {e}")
        
        # Удалить __MACOSX папки
        for dir_name in dirs:
            if dir_name == '__MACOSX':
                try:
                    dir_path = os.path.join(root, dir_name)
                    shutil.rmtree(dir_path)
                    removed_count += 1
                    log(f"Removed __MACOSX folder: {dir_path}")
                except Exception as e:
                    log(f"⚠️ Could not remove {dir_name}: {e}")
    
    if removed_count > 0:
        log(f"✅ Cleaned {removed_count} system files/folders")
    
    # Подсчёт файлов
    log("")
    log("📊 Analyzing downloaded files...")
    
    file_count = 0
    file_types = {}
    
    for root, dirs, files in os.walk(output_dir):
        for file in files:
            ext = Path(file).suffix.lower()
            
            # Count all files
            if ext not in file_types:
                file_types[ext] = 0
            file_types[ext] += 1
            
            # Count target files
            if ext in ['.pdf', '.docx', '.doc', '.txt']:
                file_count += 1
    
    log("")
    log("=" * 70)
    log("📊 DOWNLOAD RESULT")
    log("=" * 70)
    log(f"✅ Target files (PDF/DOCX/TXT): {file_count}")
    log("")
    
    # Show all file types found
    if file_types:
        log("File types found:")
        for ext, count in sorted(file_types.items(), key=lambda x: x[1], reverse=True):
            ext_display = ext if ext else '(no extension)'
            log(f"  {ext_display}: {count} files")
    
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
            
            # Show first 3 files in each folder
            for f in files[:3]:
                log(f"     • {f}")
            if len(files) > 3:
                log(f"     ... and {len(files) - 3} more")
        
        log("")
        log(f"✅ SUCCESS! Ready for RAG: {file_count} documents")
        log("=" * 70)
        
    else:
        log("")
        log("⚠️ WARNING: No PDF/DOCX/TXT files found!")
        log("")
        log("This could mean:")
        log("  1. The ZIP contains files in different formats")
        log("  2. Files are nested in subdirectories we're not seeing")
        log("  3. The download was incomplete")
        log("")
        log("Total files downloaded (all types): " + str(sum(file_types.values())))
        log("=" * 70)

if __name__ == "__main__":
    try:
        log("Starting download process...")
        download_and_extract()
        log("Download process completed!")
        sys.exit(0)
    except KeyboardInterrupt:
        log("Download interrupted by user")
        sys.exit(1)
    except Exception as e:
        log(f"FATAL ERROR: {e}")
        import traceback
        log(traceback.format_exc())
        sys.exit(1)
