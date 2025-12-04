#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
📥 PIPILA Document Downloader v3.0
Robust download from Dropbox with retries
"""

import os
import sys
import zipfile
import shutil
import time
import urllib.request
import ssl
from pathlib import Path

# ============================================================================
# CONFIG
# ============================================================================
# ✅ Your Dropbox direct link (dl=1 for direct download)
DROPBOX_URL = "https://www.dropbox.com/scl/fi/gg6o8vc2dgc7ks9z8x1bx/Fuentes-de-informaci-n-RAG?rlkey=tt8cpimwv232fwk436esxhhp2&dl=1"

OUTPUT_DIR = "documents"
ZIP_PATH = "/tmp/pipila_docs.zip"
MAX_RETRIES = 3
TIMEOUT = 600  # 10 minutes for large files

# ============================================================================
# LOGGING
# ============================================================================
def log(msg):
    print(f"[DOWNLOAD] {msg}", flush=True)

def log_error(msg):
    print(f"[ERROR] {msg}", flush=True)

# ============================================================================
# DOWNLOAD FUNCTION
# ============================================================================
def download_file(url, dest_path, retries=MAX_RETRIES):
    """Download file with retries and progress"""
    
    for attempt in range(1, retries + 1):
        try:
            log(f"Attempt {attempt}/{retries}...")
            
            # Create SSL context that doesn't verify (for Dropbox redirects)
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            
            # Create request with browser-like headers
            req = urllib.request.Request(url, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': '*/*',
                'Accept-Encoding': 'identity',
            })
            
            # Download with progress
            with urllib.request.urlopen(req, timeout=TIMEOUT, context=ctx) as response:
                total_size = int(response.headers.get('content-length', 0))
                
                if total_size > 0:
                    log(f"File size: {total_size / (1024*1024):.1f} MB")
                else:
                    log("File size: unknown (streaming)")
                
                downloaded = 0
                chunk_size = 1024 * 1024  # 1MB chunks
                
                with open(dest_path, 'wb') as f:
                    while True:
                        chunk = response.read(chunk_size)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        # Progress every 10MB
                        if downloaded % (10 * 1024 * 1024) < chunk_size:
                            if total_size > 0:
                                pct = (downloaded / total_size) * 100
                                log(f"Progress: {downloaded / (1024*1024):.1f} MB ({pct:.1f}%)")
                            else:
                                log(f"Downloaded: {downloaded / (1024*1024):.1f} MB")
            
            # Verify download
            final_size = os.path.getsize(dest_path)
            log(f"✅ Download complete: {final_size / (1024*1024):.1f} MB")
            
            if final_size < 1000:
                log_error("File too small - might be error page")
                # Show first bytes
                with open(dest_path, 'rb') as f:
                    log(f"First 200 bytes: {f.read(200)}")
                if attempt < retries:
                    time.sleep(5)
                    continue
                return False
            
            return True
            
        except Exception as e:
            log_error(f"Attempt {attempt} failed: {e}")
            if attempt < retries:
                log(f"Waiting 10 seconds before retry...")
                time.sleep(10)
            else:
                return False
    
    return False

# ============================================================================
# EXTRACT FUNCTION
# ============================================================================
def extract_zip(zip_path, output_dir):
    """Extract ZIP to flat structure"""
    
    log(f"📦 Extracting to: {output_dir}")
    
    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            members = zf.namelist()
            log(f"Files in archive: {len(members)}")
            
            extracted = 0
            skipped = 0
            
            for member in members:
                # Skip directories
                if member.endswith('/'):
                    continue
                
                # Get filename only (flatten structure)
                filename = os.path.basename(member)
                
                # Skip system files
                if not filename or filename.startswith('.') or filename.startswith('_'):
                    skipped += 1
                    continue
                
                # Skip macOS junk
                if '__MACOSX' in member or '.DS_Store' in member:
                    skipped += 1
                    continue
                
                # Target path
                target = os.path.join(output_dir, filename)
                
                # Handle duplicates
                if os.path.exists(target):
                    name, ext = os.path.splitext(filename)
                    counter = 1
                    while os.path.exists(target):
                        target = os.path.join(output_dir, f"{name}_{counter}{ext}")
                        counter += 1
                
                # Extract
                try:
                    with zf.open(member) as src, open(target, 'wb') as dst:
                        dst.write(src.read())
                    extracted += 1
                except Exception as e:
                    log_error(f"Failed to extract {filename}: {e}")
            
            log(f"✅ Extracted: {extracted} files")
            if skipped > 0:
                log(f"⏭️ Skipped: {skipped} system files")
            
            return extracted
            
    except zipfile.BadZipFile:
        log_error("❌ Not a valid ZIP file!")
        # Show what we got
        with open(zip_path, 'rb') as f:
            content = f.read(500)
            log(f"File content preview: {content[:200]}")
        return 0
    except Exception as e:
        log_error(f"❌ Extraction failed: {e}")
        return 0

# ============================================================================
# MAIN
# ============================================================================
def main():
    log("=" * 60)
    log("📥 PIPILA Document Downloader v3.0")
    log("=" * 60)
    
    # Clean old data
    if os.path.exists(OUTPUT_DIR):
        log(f"🧹 Removing old {OUTPUT_DIR}/")
        shutil.rmtree(OUTPUT_DIR)
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Remove old ZIP
    if os.path.exists(ZIP_PATH):
        os.remove(ZIP_PATH)
    
    # Download
    log("")
    log("📥 Downloading from Dropbox...")
    log(f"URL: {DROPBOX_URL[:60]}...")
    
    if not download_file(DROPBOX_URL, ZIP_PATH):
        log_error("❌ DOWNLOAD FAILED after all retries")
        log("Creating empty documents folder...")
        # Don't exit - let bot start without docs
        return
    
    # Extract
    log("")
    count = extract_zip(ZIP_PATH, OUTPUT_DIR)
    
    # Cleanup ZIP
    if os.path.exists(ZIP_PATH):
        os.remove(ZIP_PATH)
        log("🧹 Removed temp ZIP")
    
    # Summary
    log("")
    log("=" * 60)
    
    # Count by type
    pdf_count = len(list(Path(OUTPUT_DIR).glob("*.pdf")))
    docx_count = len(list(Path(OUTPUT_DIR).glob("*.docx")))
    txt_count = len(list(Path(OUTPUT_DIR).glob("*.txt")))
    total = pdf_count + docx_count + txt_count
    
    log(f"📊 RESULT:")
    log(f"   PDF:  {pdf_count}")
    log(f"   DOCX: {docx_count}")
    log(f"   TXT:  {txt_count}")
    log(f"   ─────────────")
    log(f"   TOTAL: {total} documents")
    log("=" * 60)
    
    if total == 0:
        log("⚠️ WARNING: No documents found!")
        log("Bot will start without RAG documents")
    else:
        log(f"✅ SUCCESS! {total} documents ready for RAG")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("Interrupted")
        sys.exit(1)
    except Exception as e:
        log_error(f"FATAL: {e}")
        import traceback
        traceback.print_exc()
        # Don't exit with error - let bot start
        sys.exit(0)

