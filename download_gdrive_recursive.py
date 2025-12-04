#!/usr/bin/env python3
"""
📥 PIPILA Document Downloader v4.0
Guaranteed to work with Dropbox
"""
import os
import sys
import zipfile
import shutil
import time
import urllib.request
import ssl
from pathlib import Path

DROPBOX_URL = "https://www.dropbox.com/scl/fi/gg6o8vc2dgc7ks9z8x1bx/Fuentes-de-informaci-n-RAG?rlkey=tt8cpimwv232fwk436esxhhp2&dl=1"
OUTPUT_DIR = "documents"
ZIP_PATH = "/tmp/pipila_docs.zip"

def log(msg):
    print(f"[DOWNLOAD] {msg}", flush=True)
    sys.stdout.flush()

def download():
    log("=" * 60)
    log("📥 PIPILA Document Downloader v4.0")
    log("=" * 60)
    
    # Clean
    if os.path.exists(OUTPUT_DIR):
        shutil.rmtree(OUTPUT_DIR)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    if os.path.exists(ZIP_PATH):
        os.remove(ZIP_PATH)
    
    log(f"📥 Downloading from Dropbox...")
    log(f"URL: {DROPBOX_URL[:70]}...")
    
    for attempt in range(3):
        try:
            log(f"Attempt {attempt+1}/3...")
            
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            
            req = urllib.request.Request(DROPBOX_URL, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': '*/*',
            })
            
            with urllib.request.urlopen(req, timeout=600, context=ctx) as resp:
                total = int(resp.headers.get('content-length', 0))
                log(f"Size: {total/(1024*1024):.1f} MB" if total else "Size: streaming")
                
                downloaded = 0
                with open(ZIP_PATH, 'wb') as f:
                    while True:
                        chunk = resp.read(1024*1024)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)
                        if downloaded % (50*1024*1024) < 1024*1024:
                            log(f"Progress: {downloaded/(1024*1024):.0f} MB")
            
            size = os.path.getsize(ZIP_PATH)
            log(f"✅ Downloaded: {size/(1024*1024):.1f} MB")
            
            if size < 1000:
                log("❌ File too small!")
                with open(ZIP_PATH, 'rb') as f:
                    log(f"Content: {f.read(200)}")
                continue
            
            break
            
        except Exception as e:
            log(f"❌ Error: {e}")
            if attempt < 2:
                log("Retry in 10s...")
                time.sleep(10)
            else:
                log("❌ FAILED after 3 attempts")
                return
    
    # Extract
    log("")
    log("📦 Extracting...")
    try:
        with zipfile.ZipFile(ZIP_PATH, 'r') as zf:
            extracted = 0
            for member in zf.namelist():
                if member.endswith('/'):
                    continue
                fname = os.path.basename(member)
                if not fname or fname.startswith('.') or fname.startswith('_'):
                    continue
                if '__MACOSX' in member:
                    continue
                
                target = os.path.join(OUTPUT_DIR, fname)
                if os.path.exists(target):
                    name, ext = os.path.splitext(fname)
                    i = 1
                    while os.path.exists(target):
                        target = os.path.join(OUTPUT_DIR, f"{name}_{i}{ext}")
                        i += 1
                
                try:
                    with zf.open(member) as src, open(target, 'wb') as dst:
                        dst.write(src.read())
                    extracted += 1
                except:
                    pass
            
            log(f"✅ Extracted: {extracted} files")
            
    except zipfile.BadZipFile:
        log("❌ Not a valid ZIP!")
        with open(ZIP_PATH, 'rb') as f:
            log(f"First bytes: {f.read(100)}")
        return
    except Exception as e:
        log(f"❌ Extract error: {e}")
        return
    
    # Cleanup
    if os.path.exists(ZIP_PATH):
        os.remove(ZIP_PATH)
    
    # Summary
    pdf = len(list(Path(OUTPUT_DIR).glob("*.pdf")))
    docx = len(list(Path(OUTPUT_DIR).glob("*.docx")))
    txt = len(list(Path(OUTPUT_DIR).glob("*.txt")))
    total = pdf + docx + txt
    
    log("")
    log("=" * 60)
    log(f"📊 RESULT: PDF={pdf}, DOCX={docx}, TXT={txt}")
    log(f"📚 TOTAL: {total} documents")
    log("=" * 60)
    
    if total > 0:
        log("✅ SUCCESS!")
    else:
        log("⚠️ No documents found")

if __name__ == "__main__":
    try:
        download()
    except Exception as e:
        log(f"FATAL: {e}")
        import traceback
        traceback.print_exc()
    sys.exit(0)

