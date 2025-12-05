#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔽 PIPILA - ChromaDB Downloader
Downloads pre-processed ChromaDB from Dropbox
Saves 35-40 minutes of processing time!
"""

import os
import sys
import urllib.request
import zipfile
import shutil

def log(msg):
    """Print with flush for build logs"""
    print(f"[CHROMADB] {msg}", flush=True)
    sys.stdout.flush()

def download_chromadb():
    """Download and extract ChromaDB from Dropbox"""
    
    # ✅ Dropbox direct download link for chroma_db.zip
    # Configured with actual link (MUST end with ?dl=1 for direct download)
    dropbox_url = "https://www.dropbox.com/scl/fi/ntxalvi82zh2xao7x1e0f/chroma_db.zip?rlkey=q9qmjvwwdf9bo5c4lnmnr1g30&st=shvsn4tv&dl=1"
    
    zip_path = "/tmp/chroma_db.zip"
    output_dir = "./chroma_db"
    
    log("=" * 70)
    log("🔽 Downloading pre-processed ChromaDB from Dropbox")
    log("=" * 70)
    
    # Check if URL is configured
    if "YOUR_DROPBOX_DIRECT_LINK_HERE" in dropbox_url:
        log("❌ ERROR: Dropbox URL not configured!")
        log("")
        log("Steps to configure:")
        log("1. Upload chroma_db.zip to Dropbox")
        log("2. Get sharing link")
        log("3. Change '?dl=0' to '?dl=1' in the link")
        log("4. Replace YOUR_DROPBOX_DIRECT_LINK_HERE in this script")
        log("")
        log("⚠️ Falling back to empty ChromaDB - bot will work but without documents")
        
        # Create empty ChromaDB so bot doesn't crash
        os.makedirs(output_dir, exist_ok=True)
        return
    
    # Clean old folder
    if os.path.exists(output_dir):
        log(f"🧹 Cleaning old ChromaDB folder")
        try:
            shutil.rmtree(output_dir)
            log("✅ Old folder removed")
        except Exception as e:
            log(f"⚠️ Warning: {e}")
    
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
                    
                    # Progress every 10MB
                    if downloaded % (10 * 1024 * 1024) < chunk_size:
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
    log(f"📦 Extracting ChromaDB...")
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(".")
        
        log(f"✅ Extraction complete")
        
    except zipfile.BadZipFile as e:
        log(f"❌ Extract FAILED: Bad ZIP file - {e}")
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
    
    # Verify ChromaDB folder
    if not os.path.exists(output_dir):
        log(f"❌ ChromaDB folder not found after extraction!")
        sys.exit(1)
    
    # Count files
    log("")
    log("📊 Analyzing ChromaDB...")
    
    file_count = 0
    for root, dirs, files in os.walk(output_dir):
        file_count += len(files)
    
    log("")
    log("=" * 70)
    log("✅ SUCCESS! ChromaDB ready")
    log("=" * 70)
    log(f"📁 Folder: {output_dir}")
    log(f"📊 Files: {file_count}")
    log(f"⚡ Saved: ~35-40 minutes of processing time!")
    log("=" * 70)


if __name__ == "__main__":
    try:
        log("Starting ChromaDB download...")
        download_chromadb()
        log("ChromaDB download completed!")
        sys.exit(0)
    except KeyboardInterrupt:
        log("Download interrupted")
        sys.exit(1)
    except Exception as e:
        log(f"FATAL ERROR: {e}")
        import traceback
        log(traceback.format_exc())
        sys.exit(1)
