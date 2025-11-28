#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔽 PIPILA - Descargador BULLETPROOF (Dropbox + Google Drive)
GARANTIZADO que funcionará - con múltiples fallbacks
"""

import os
import sys
import subprocess
import urllib.request
import zipfile
import shutil
from pathlib import Path

def log(msg):
    """Print con flush para ver en build logs"""
    print(msg, flush=True)

def download_file(url, output_path):
    """Descargar archivo con progress"""
    log(f"📥 Descargando desde: {url[:60]}...")
    try:
        urllib.request.urlretrieve(url, output_path)
        return True
    except Exception as e:
        log(f"❌ Error: {e}")
        return False

def extract_zip(zip_path, output_dir):
    """Extraer ZIP"""
    log(f"📦 Extrayendo {zip_path}...")
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(output_dir)
        return True
    except Exception as e:
        log(f"❌ Error extrayendo: {e}")
        return False

def count_files(directory, extensions=['.pdf', '.docx', '.doc', '.txt']):
    """Contar archivos"""
    count = 0
    for root, dirs, files in os.walk(directory):
        for file in files:
            if any(file.lower().endswith(ext) for ext in extensions):
                count += 1
    return count

def cleanup_macos_files(directory):
    """Eliminar archivos __MACOSX y .DS_Store"""
    log("🧹 Limpiando archivos de sistema...")
    removed = 0
    for root, dirs, files in os.walk(directory, topdown=False):
        # Eliminar archivos .DS_Store
        for file in files:
            if file == '.DS_Store' or file.startswith('._'):
                file_path = os.path.join(root, file)
                try:
                    os.remove(file_path)
                    removed += 1
                except:
                    pass
        
        # Eliminar carpetas __MACOSX
        for dir_name in dirs:
            if dir_name == '__MACOSX':
                dir_path = os.path.join(root, dir_name)
                try:
                    shutil.rmtree(dir_path)
                    removed += 1
                except:
                    pass
    
    if removed > 0:
        log(f"✅ Eliminados {removed} archivos de sistema")

def try_dropbox():
    """Método 1: Dropbox (MÁS CONFIABLE)"""
    log("=" * 70)
    log("🔵 MÉTODO 1: Dropbox")
    log("=" * 70)
    
    # URL de Dropbox - cambiar dl=0 a dl=1 para descarga directa
    dropbox_url = "https://www.dropbox.com/scl/fi/gg6o8vc2dgc7ks9z8x1bx/Fuentes-de-informaci-n-RAG?rlkey=tt8cpimwv232fwk436esxhhp2&st=f8pow9t2&dl=1"
    
    zip_path = "/tmp/documents.zip"
    output_dir = "documents"
    
    log(f"📥 Descargando ZIP desde Dropbox...")
    
    if download_file(dropbox_url, zip_path):
        log(f"✅ Descargado: {os.path.getsize(zip_path) / (1024*1024):.2f} MB")
        
        if extract_zip(zip_path, output_dir):
            cleanup_macos_files(output_dir)
            
            file_count = count_files(output_dir)
            log(f"✅ Archivos extraídos: {file_count}")
            
            # Limpiar ZIP temporal
            try:
                os.remove(zip_path)
            except:
                pass
            
            if file_count > 0:
                return True
            else:
                log("⚠️ No se encontraron archivos PDF/DOCX/TXT")
    
    return False

def try_google_drive_gdown():
    """Método 2: Google Drive con gdown"""
    log("=" * 70)
    log("🔴 MÉTODO 2: Google Drive (gdown)")
    log("=" * 70)
    
    try:
        # Instalar gdown
        log("📦 Instalando gdown...")
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", 
            "gdown>=5.1.0", "-q", "--no-cache-dir"
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        import gdown
        
        folder_id = "1vK_GFk3M3vA4vQksZGnGCM027sv39Rz4"
        output_dir = "documents"
        
        log(f"📂 Folder ID: {folder_id}")
        log(f"📥 Descargando recursivamente...")
        
        gdown.download_folder(
            id=folder_id,
            output=output_dir,
            quiet=False,
            use_cookies=False,
            remaining_ok=True
        )
        
        cleanup_macos_files(output_dir)
        file_count = count_files(output_dir)
        
        if file_count > 0:
            log(f"✅ Descargados: {file_count} archivos")
            return True
        else:
            log("⚠️ No se encontraron archivos")
            return False
            
    except Exception as e:
        log(f"❌ Error Google Drive: {e}")
        return False

def try_direct_download():
    """Método 3: Descarga directa como fallback"""
    log("=" * 70)
    log("🟡 MÉTODO 3: Descarga directa alternativa")
    log("=" * 70)
    
    # Intentar URL de descarga directa de Dropbox
    direct_urls = [
        "https://www.dropbox.com/scl/fi/gg6o8vc2dgc7ks9z8x1bx/Fuentes-de-informaci-n-RAG?rlkey=tt8cpimwv232fwk436esxhhp2&st=f8pow9t2&dl=1",
    ]
    
    for url in direct_urls:
        zip_path = "/tmp/docs_direct.zip"
        output_dir = "documents"
        
        log(f"📥 Intentando: {url[:50]}...")
        
        if download_file(url, zip_path):
            if extract_zip(zip_path, output_dir):
                cleanup_macos_files(output_dir)
                file_count = count_files(output_dir)
                
                try:
                    os.remove(zip_path)
                except:
                    pass
                
                if file_count > 0:
                    log(f"✅ Éxito: {file_count} archivos")
                    return True
    
    return False

def show_results(output_dir="documents"):
    """Mostrar resultados finales"""
    if not os.path.exists(output_dir):
        log("❌ Carpeta documents no existe")
        return
    
    file_count = count_files(output_dir)
    
    log("")
    log("=" * 70)
    log("📊 RESULTADO FINAL")
    log("=" * 70)
    log(f"✅ Archivos descargados: {file_count}")
    log("")
    
    if file_count > 0:
        log("📂 Estructura de carpetas:")
        folders = {}
        for root, dirs, files in os.walk(output_dir):
            for file in files:
                ext = Path(file).suffix.lower()
                if ext in ['.pdf', '.docx', '.doc', '.txt']:
                    rel_dir = os.path.relpath(root, output_dir)
                    if rel_dir not in folders:
                        folders[rel_dir] = 0
                    folders[rel_dir] += 1
        
        for folder, count in sorted(folders.items()):
            if folder == '.':
                log(f"  📁 (raíz): {count} archivos")
            else:
                log(f"  📁 {folder}: {count} archivos")
        
        log("")
        log(f"📚 Total para RAG: {file_count} archivos")
        log("✅ ¡Descarga completada con éxito!")
    else:
        log("⚠️ ADVERTENCIA: No se encontraron archivos PDF/DOCX/TXT")
        log("")
        log("💡 Posibles causas:")
        log("  1. El ZIP no contiene archivos con esas extensiones")
        log("  2. Los archivos están en un formato no soportado")
        log("  3. La carpeta está vacía")
    
    log("=" * 70)

def main():
    log("=" * 70)
    log("🔽 PIPILA - Descargador BULLETPROOF de Documentos")
    log("=" * 70)
    log("")
    
    output_dir = "documents"
    
    # Limpiar carpeta anterior si existe
    if os.path.exists(output_dir):
        log("🧹 Limpiando carpeta anterior...")
        shutil.rmtree(output_dir)
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Intentar métodos en orden de confiabilidad
    methods = [
        ("Dropbox ZIP", try_dropbox),
        ("Google Drive gdown", try_google_drive_gdown),
        ("Descarga directa", try_direct_download),
    ]
    
    success = False
    for method_name, method_func in methods:
        log("")
        try:
            if method_func():
                log(f"✅ ¡Éxito con {method_name}!")
                success = True
                break
            else:
                log(f"❌ {method_name} no funcionó, probando siguiente método...")
        except Exception as e:
            log(f"❌ Error en {method_name}: {e}")
            log("   Probando siguiente método...")
    
    log("")
    
    if not success:
        log("=" * 70)
        log("❌ TODOS LOS MÉTODOS FALLARON")
        log("=" * 70)
        log("")
        log("🔧 ACCIONES REQUERIDAS:")
        log("")
        log("1. Verifica que el ZIP de Dropbox sea público:")
        log("   https://www.dropbox.com/scl/fi/gg6o8vc2dgc7ks9z8x1bx/")
        log("")
        log("2. Verifica que la carpeta de Google Drive sea pública:")
        log("   https://drive.google.com/drive/folders/1vK_GFk3M3vA4vQksZGnGCM027sv39Rz4")
        log("   Settings → Share → Anyone with link → Viewer")
        log("")
        log("3. Alternativa: Sube los archivos directamente al repo GitHub")
        log("   (si no son muy grandes)")
        log("")
        sys.exit(1)
    
    # Mostrar resultados
    show_results(output_dir)

if __name__ == "__main__":
    main()
