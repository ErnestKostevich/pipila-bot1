#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔽 PIPILA v8.4 - Document Processor
Downloads documents from GitHub Releases and creates ChromaDB
Processing time: ~35-40 minutes on Render
"""

import os
import sys
import urllib.request
import urllib.parse
import zipfile
import shutil
import time
from pathlib import Path

def log(msg):
    """Print with flush for build logs"""
    print(f"[PROCESSOR] {msg}", flush=True)
    sys.stdout.flush()

def download_documents():
    """Download documents ZIP from GitHub Releases"""
    
    # ✅ EXACT filename from GitHub Releases
    github_url = "https://github.com/ErnestKostevich/pipila-bot1/releases/download/v8.2/Fuentes.de.informacion.RAG-20251207T164947Z-3-001.zip"
    
    zip_path = "/tmp/documents.zip"
    extract_dir = "/tmp/documents"
    
    log("=" * 70)
    log("🔽 PIPILA v8.4 - Downloading Documents from GitHub Releases")
    log("=" * 70)
    log(f"📥 Source: {github_url}")
    log("")
    
    # Clean old folders
    for path in [zip_path, extract_dir, "./chroma_db"]:
        if os.path.exists(path):
            log(f"🧹 Cleaning {path}...")
            try:
                if os.path.isdir(path):
                    shutil.rmtree(path)
                else:
                    os.remove(path)
            except Exception as e:
                log(f"⚠️ Warning: {e}")
    
    # Download ZIP
    log("")
    log("📥 Starting download (~1GB, this takes a few minutes)...")
    start_time = time.time()
    
    try:
        req = urllib.request.Request(
            github_url,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/octet-stream, */*'
            }
        )
        
        with urllib.request.urlopen(req, timeout=600) as response:
            with open(zip_path, 'wb') as out_file:
                total_size = int(response.headers.get('content-length', 0))
                if total_size > 0:
                    log(f"📦 Total size: {total_size / (1024*1024):.2f} MB")
                
                downloaded = 0
                chunk_size = 131072  # 128KB chunks
                last_report = 0
                
                while True:
                    chunk = response.read(chunk_size)
                    if not chunk:
                        break
                    out_file.write(chunk)
                    downloaded += len(chunk)
                    
                    # Progress every 100MB
                    mb_downloaded = downloaded / (1024 * 1024)
                    if mb_downloaded - last_report >= 100:
                        log(f"   Downloaded: {mb_downloaded:.0f} MB")
                        last_report = mb_downloaded
        
        size_mb = os.path.getsize(zip_path) / (1024 * 1024)
        elapsed = time.time() - start_time
        log(f"✅ Download complete: {size_mb:.2f} MB in {elapsed:.1f}s")
        
        if size_mb < 10:
            log("❌ CRITICAL: Downloaded file too small!")
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
        log(traceback.format_exc())
        sys.exit(1)
    
    # Extract ZIP
    log("")
    log("📦 Extracting documents...")
    try:
        os.makedirs(extract_dir, exist_ok=True)
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            file_list = zip_ref.namelist()
            log(f"   Archive contains {len(file_list)} items")
            zip_ref.extractall(extract_dir)
        log("✅ Extraction complete")
        
        # Remove ZIP to save space (important for Render's limited disk)
        os.remove(zip_path)
        log("✅ Cleaned up ZIP file (saved ~1GB disk space)")
        
    except Exception as e:
        log(f"❌ Extract FAILED: {e}")
        import traceback
        log(traceback.format_exc())
        sys.exit(1)
    
    return extract_dir

def find_documents(base_dir):
    """Find all processable documents"""
    supported_extensions = {'.pdf', '.docx', '.doc', '.pptx', '.ppt', '.txt'}
    documents = []
    
    for root, dirs, files in os.walk(base_dir):
        # Skip hidden folders and temp files
        dirs[:] = [d for d in dirs if not d.startswith('.') and not d.startswith('~')]
        
        for file in files:
            if file.startswith('~') or file.startswith('.'):
                continue
            
            ext = Path(file).suffix.lower()
            if ext in supported_extensions:
                full_path = os.path.join(root, file)
                documents.append(full_path)
    
    return documents

def extract_text_from_pdf(file_path):
    """Extract text from PDF"""
    try:
        import PyPDF2
        with open(file_path, 'rb') as file:
            try:
                pdf_reader = PyPDF2.PdfReader(file)
                text = ""
                for page in pdf_reader.pages:
                    try:
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text + "\n"
                    except:
                        continue
                return text.strip()
            except Exception as e:
                return ""
    except Exception as e:
        return ""

def extract_text_from_docx(file_path):
    """Extract text from DOCX"""
    try:
        import docx
        doc = docx.Document(file_path)
        text = "\n".join([p.text for p in doc.paragraphs if p.text])
        return text.strip()
    except Exception as e:
        return ""

def extract_text_from_pptx(file_path):
    """Extract text from PPTX"""
    try:
        from pptx import Presentation
        prs = Presentation(file_path)
        text_parts = []
        for slide in prs.slides:
            for shape in slide.shapes:
                if hasattr(shape, "text") and shape.text:
                    text_parts.append(shape.text)
        return "\n".join(text_parts).strip()
    except Exception as e:
        return ""

def extract_text_from_txt(file_path):
    """Extract text from TXT"""
    try:
        encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    return f.read().strip()
            except:
                continue
        return ""
    except Exception as e:
        return ""

def extract_text(file_path):
    """Extract text from any supported file"""
    ext = Path(file_path).suffix.lower()
    
    if ext == '.pdf':
        return extract_text_from_pdf(file_path)
    elif ext in ['.docx', '.doc']:
        return extract_text_from_docx(file_path)
    elif ext in ['.pptx', '.ppt']:
        return extract_text_from_pptx(file_path)
    elif ext == '.txt':
        return extract_text_from_txt(file_path)
    else:
        return ""

def chunk_text(text, chunk_size=1000, overlap=200):
    """Split text into overlapping chunks"""
    if not text or len(text) < 100:
        return []
    
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        
        if len(chunk.strip()) > 50:  # Minimum chunk size
            chunks.append(chunk.strip())
        
        start = end - overlap
        if start >= len(text):
            break
    
    return chunks

def create_chromadb(documents_dir):
    """Process documents and create ChromaDB"""
    import chromadb
    
    log("")
    log("=" * 70)
    log("🔧 Creating ChromaDB from documents")
    log("=" * 70)
    
    # Find all documents
    log("📂 Scanning for documents...")
    doc_files = find_documents(documents_dir)
    log(f"   Found {len(doc_files)} documents")
    
    if not doc_files:
        log("❌ No documents found!")
        sys.exit(1)
    
    # Show document types
    by_type = {}
    for f in doc_files:
        ext = Path(f).suffix.lower()
        by_type[ext] = by_type.get(ext, 0) + 1
    log(f"   Types: {by_type}")
    
    # Initialize ChromaDB
    log("")
    log("🗄️ Initializing ChromaDB...")
    chroma_client = chromadb.PersistentClient(path="./chroma_db")
    
    # Delete existing collection if exists
    try:
        chroma_client.delete_collection("pipila_documents")
        log("   Deleted old collection")
    except:
        pass
    
    collection = chroma_client.create_collection(
        name="pipila_documents",
        metadata={"hnsw:space": "cosine"}
    )
    log("✅ ChromaDB initialized")
    
    # Process documents
    log("")
    log("📄 Processing documents (this takes 30-40 minutes)...")
    log("   Please wait...")
    start_time = time.time()
    
    total_chunks = 0
    processed = 0
    errors = 0
    skipped = 0
    
    for i, doc_path in enumerate(doc_files):
        filename = os.path.basename(doc_path)
        relative_path = os.path.relpath(doc_path, documents_dir)
        
        # Progress every 25 files
        if (i + 1) % 25 == 0:
            elapsed = time.time() - start_time
            rate = (i + 1) / elapsed * 60 if elapsed > 0 else 0
            eta = (len(doc_files) - i - 1) / rate if rate > 0 else 0
            log(f"   [{i+1}/{len(doc_files)}] {processed} processed, {total_chunks} chunks | ETA: {eta:.0f}min")
        
        try:
            # Extract text
            text = extract_text(doc_path)
            
            if not text or len(text) < 100:
                skipped += 1
                continue
            
            # Create chunks
            chunks = chunk_text(text, chunk_size=1000, overlap=200)
            
            if not chunks:
                skipped += 1
                continue
            
            # Add to ChromaDB
            for j, chunk in enumerate(chunks):
                chunk_id = f"doc_{processed}_{j}"
                
                collection.add(
                    documents=[chunk],
                    metadatas=[{
                        "source": filename,
                        "path": relative_path,
                        "chunk": j,
                        "total_chunks": len(chunks)
                    }],
                    ids=[chunk_id]
                )
                total_chunks += 1
            
            processed += 1
            
        except Exception as e:
            errors += 1
            if errors <= 10:
                log(f"   ⚠️ Error: {filename[:30]} - {str(e)[:30]}")
    
    elapsed = time.time() - start_time
    
    # Summary
    log("")
    log("=" * 70)
    log("✅ ChromaDB Creation Complete!")
    log("=" * 70)
    log(f"📁 Documents found: {len(doc_files)}")
    log(f"✅ Processed: {processed}")
    log(f"⏭️ Skipped (no text): {skipped}")
    log(f"⚠️ Errors: {errors}")
    log(f"📊 Total chunks: {total_chunks}")
    log(f"⏱️ Time: {elapsed/60:.1f} minutes")
    log(f"💾 Location: ./chroma_db")
    log("=" * 70)
    
    return total_chunks

def main():
    """Main function"""
    log("=" * 70)
    log("🚀 PIPILA v8.4 - Full Document Processor")
    log("=" * 70)
    log("")
    log("⏱️ Expected total time: 35-45 minutes")
    log("   - Download: ~2-5 minutes (1GB)")
    log("   - Processing: ~30-40 minutes")
    log("")
    
    total_start = time.time()
    
    # Step 1: Download documents
    documents_dir = download_documents()
    
    # Step 2: Install PPTX support if needed
    log("")
    log("📦 Checking python-pptx...")
    try:
        from pptx import Presentation
        log("✅ python-pptx available")
    except ImportError:
        log("📥 Installing python-pptx...")
        os.system("pip install python-pptx --quiet --break-system-packages 2>/dev/null || pip install python-pptx --quiet")
        log("✅ python-pptx installed")
    
    # Step 3: Create ChromaDB
    total_chunks = create_chromadb(documents_dir)
    
    # Step 4: Cleanup
    log("")
    log("🧹 Cleaning up temporary files...")
    try:
        shutil.rmtree(documents_dir)
        log("✅ Cleanup complete")
    except:
        pass
    
    # Final summary
    total_elapsed = time.time() - total_start
    log("")
    log("=" * 70)
    log("🎉 ALL DONE!")
    log("=" * 70)
    log(f"📊 ChromaDB ready with {total_chunks} chunks")
    log(f"⏱️ Total time: {total_elapsed/60:.1f} minutes")
    log("=" * 70)
    log("")
    log("✅ Ready to start bot!")
    
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        log("⚠️ Interrupted by user")
        sys.exit(1)
    except Exception as e:
        log(f"💥 FATAL ERROR: {e}")
        import traceback
        log(traceback.format_exc())
        sys.exit(1)
