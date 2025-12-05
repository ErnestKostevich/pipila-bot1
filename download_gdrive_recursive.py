#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔽 PIPILA - Dropbox Downloader for Render.com
Downloads and extracts documents from Dropbox
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
    """Download ZIP from Dropbox and extract flat"""
    
    # ✅ Your direct Dropbox link
    dropbox_url = "https://www.dropbox.com/scl/fi/gg6o8vc2dgc7ks9z8x1bx/Fuentes-de-informaci-n-RAG?rlkey=tt8cpimwv232fwk436esxhhp2&st=k9zfpx4z&dl=1"
    
    zip_path = "/tmp/documents.zip"
    output_dir = "documents"
    
    log("=" * 70)
    log("🔽 PIPILA - Downloading documents from Dropbox")
    log("=" * 70)
    
    # Clean old folder
    if os.path.exists(output_dir):
        log(f"🧹 Cleaning old folder: {output_dir}")
        try:
            shutil.rmtree(output_dir)
            log("✅ Old folder removed")
        except Exception as e:
            log(f"⚠️ Warning: {e}")
    
    # Create folder
    try:
        os.makedirs(output_dir, exist_ok=True)
        log(f"✅ Created directory: {output_dir}")
    except Exception as e:
        log(f"❌ FAILED to create directory: {e}")
        sys.exit(1)
    
    # Download ZIP
    log("")
    log("📥 Starting download from Dropbox...")
    try:
        req = urllib.request.Request(
            dropbox_url,
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        )
        
        with urllib.request.urlopen(req, timeout=600) as response:
            with open(zip_path, 'wb') as out_file:
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
                    
                    # Progress every 50MB
                    if downloaded % (50 * 1024 * 1024) < chunk_size:
                        log(f"Downloaded: {downloaded / (1024*1024):.1f} MB")
        
        size_mb = os.path.getsize(zip_path) / (1024 * 1024)
        log(f"✅ Download complete: {size_mb:.2f} MB")
        
        # Verify
        if not os.path.exists(zip_path) or os.path.getsize(zip_path) < 1000:
            log(f"❌ CRITICAL: Invalid ZIP file")
            sys.exit(1)
            
    except Exception as e:
        log(f"❌ Download FAILED: {e}")
        import traceback
        log(f"Traceback: {traceback.format_exc()}")
        sys.exit(1)
    
    # Extract ZIP
    log("")
    log(f"📦 Extracting ZIP to: {output_dir}")
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            file_list = zip_ref.namelist()
            log(f"Files in ZIP: {len(file_list)}")
            
            log("Extracting files (FLAT structure)...")
            
            extracted_count = 0
            for member in zip_ref.namelist():
                if member.endswith('/'):
                    continue
                
                filename = os.path.basename(member)
                
                if not filename:
                    continue
                
                if filename.startswith('.') or filename.startswith('_'):
                    continue
                
                if '__MACOSX' in member:
                    continue
                
                try:
                    source = zip_ref.open(member)
                    target_path = os.path.join(output_dir, filename)
                    
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
        
    except zipfile.BadZipFile as e:
        log(f"❌ Extract FAILED: Bad ZIP file - {e}")
        log("Dropbox might have returned an error page instead of the file")
        sys.exit(1)
        
    except Exception as e:
        log(f"❌ Extract FAILED: {e}")
        import traceback
        log(f"Traceback: {traceback.format_exc()}")
        sys.exit(1)
    
    # Remove ZIP
    try:
        os.remove(zip_path)
        log(f"✅ Removed temp ZIP file")
    except:
        pass
    
    # Clean macOS junk
    log("")
    log("🧹 Cleaning system files...")
    removed_count = 0
    
    for root, dirs, files in os.walk(output_dir, topdown=False):
        for file in files:
            if file == '.DS_Store' or file.startswith('._'):
                try:
                    os.remove(os.path.join(root, file))
                    removed_count += 1
                except:
                    pass
        
        for dir_name in dirs:
            if dir_name == '__MACOSX':
                try:
                    shutil.rmtree(os.path.join(root, dir_name))
                    removed_count += 1
                except:
                    pass
    
    if removed_count > 0:
        log(f"✅ Cleaned {removed_count} system files")
    
    # Count files
    log("")
    log("📊 Analyzing files...")
    
    file_count = 0
    file_types = {}
    
    for root, dirs, files in os.walk(output_dir):
        for file in files:
            ext = Path(file).suffix.lower()
            
            if ext not in file_types:
                file_types[ext] = 0
            file_types[ext] += 1
            
            if ext in ['.pdf', '.docx', '.doc', '.txt']:
                file_count += 1
    
    log("")
    log("=" * 70)
    log("📊 DOWNLOAD RESULT")
    log("=" * 70)
    log(f"✅ Target files (PDF/DOCX/TXT): {file_count}")
    
    if file_types:
        log("")
        log("File types found:")
        for ext, count in sorted(file_types.items(), key=lambda x: x[1], reverse=True):
            ext_display = ext if ext else '(no extension)'
            log(f"  {ext_display}: {count} files")
    
    if file_count > 0:
        log("")
        log(f"✅ SUCCESS! Ready for RAG: {file_count} documents")
        log("=" * 70)
    else:
        log("")
        log("⚠️ WARNING: No PDF/DOCX/TXT files found!")
        log("=" * 70)

if __name__ == "__main__":
    try:
        log("Starting download process...")
        download_and_extract()
        log("Download process completed!")
        sys.exit(0)
    except KeyboardInterrupt:
        log("Download interrupted")
        sys.exit(1)
    except Exception as e:
        log(f"FATAL ERROR: {e}")
        import traceback
        log(traceback.format_exc())
        sys.exit(1)
