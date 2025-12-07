#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔽 PIPILA - ChromaDB Downloader v8.2
Downloads pre-processed ChromaDB from GitHub Releases
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
    """Download and extract ChromaDB from GitHub Releases"""
    
    # ✅ GitHub Releases direct download link
    github_url = "https://github.com/ErnestKostevich/pipila-bot1/releases/download/v8.2/chroma_db.zip"
    
    zip_path = "/tmp/chroma_db.zip"
    output_dir = "./chroma_db"
    
    log("=" * 70)
    log("🔽 PIPILA v8.2 - Downloading ChromaDB from GitHub Releases")
    log("=" * 70)
    log(f"📥 Source: {github_url}")
    log("")
    
    # Clean old folder
    if os.path.exists(output_dir):
        log("🧹 Cleaning old ChromaDB folder...")
        try:
            shutil.rmtree(output_dir)
            log("✅ Old folder removed")
        except Exception as e:
            log(f"⚠️ Warning: {e}")
    
    # Download ZIP
    log("")
    log("📥 Starting download...")
    try:
        req = urllib.request.Request(
            github_url,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/octet-stream'
            }
        )
        
        with urllib.request.urlopen(req, timeout=300) as response:
            with open(zip_path, 'wb') as out_file:
                total_size = int(response.headers.get('content-length', 0))
                if total_size > 0:
                    log(f"📦 Total size: {total_size / (1024*1024):.2f} MB")
                
                downloaded = 0
                chunk_size = 65536  # 64KB chunks for faster download
                
                while True:
                    chunk = response.read(chunk_size)
                    if not chunk:
                        break
                    out_file.write(chunk)
                    downloaded += len(chunk)
                    
                    # Progress every 10MB
                    if downloaded % (10 * 1024 * 1024) < chunk_size:
                        log(f"   Downloaded: {downloaded / (1024*1024):.1f} MB")
        
        size_mb = os.path.getsize(zip_path) / (1024 * 1024)
        log(f"✅ Download complete: {size_mb:.2f} MB")
        
        # Verify file size
        if size_mb < 1:
            log("❌ CRITICAL: Downloaded file too small!")
            log("   Check if GitHub release file exists")
            sys.exit(1)
            
    except urllib.error.HTTPError as e:
        log(f"❌ HTTP Error {e.code}: {e.reason}")
        if e.code == 404:
            log("   File not found on GitHub Releases!")
            log("   Check: https://github.com/ErnestKostevich/pipila-bot1/releases/tag/v8.2")
        sys.exit(1)
        
    except Exception as e:
        log(f"❌ Download FAILED: {e}")
        import traceback
        log(f"Traceback: {traceback.format_exc()}")
        sys.exit(1)
    
    # Extract ZIP
    log("")
    log("📦 Extracting ChromaDB...")
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            # List contents
            file_list = zip_ref.namelist()
            log(f"   Archive contains {len(file_list)} items")
            zip_ref.extractall(".")
        
        log("✅ Extraction complete")
        
    except zipfile.BadZipFile as e:
        log(f"❌ Extract FAILED: Bad ZIP file - {e}")
        sys.exit(1)
        
    except Exception as e:
        log(f"❌ Extract FAILED: {e}")
        import traceback
        log(f"Traceback: {traceback.format_exc()}")
        sys.exit(1)
    
    # Remove ZIP to save space
    try:
        os.remove(zip_path)
        log("✅ Cleaned up temp files")
    except:
        pass
    
    # Verify ChromaDB folder
    if not os.path.exists(output_dir):
        log("❌ ChromaDB folder not found after extraction!")
        log("   Expected: ./chroma_db")
        sys.exit(1)
    
    # Count files and check structure
    log("")
    log("📊 Verifying ChromaDB structure...")
    
    file_count = 0
    has_sqlite = False
    for root, dirs, files in os.walk(output_dir):
        file_count += len(files)
        for f in files:
            if f.endswith('.sqlite3'):
                has_sqlite = True
    
    if not has_sqlite:
        log("⚠️ Warning: No SQLite database found in ChromaDB")
    
    # Success summary
    log("")
    log("=" * 70)
    log("✅ SUCCESS! ChromaDB ready for PIPILA")
    log("=" * 70)
    log(f"📁 Location: {output_dir}")
    log(f"📊 Files: {file_count}")
    log(f"💾 SQLite: {'✅ Found' if has_sqlite else '⚠️ Not found'}")
    log(f"⚡ Saved: ~35-40 minutes of document processing!")
    log("=" * 70)


if __name__ == "__main__":
    try:
        log("=" * 70)
        log("🚀 PIPILA ChromaDB Downloader v8.2")
        log("=" * 70)
        download_chromadb()
        log("")
        log("✅ Ready to start bot!")
        sys.exit(0)
    except KeyboardInterrupt:
        log("⚠️ Download interrupted by user")
        sys.exit(1)
    except Exception as e:
        log(f"💥 FATAL ERROR: {e}")
        import traceback
        log(traceback.format_exc())
        sys.exit(1)
