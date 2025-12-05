# 🤖 PIPILA Bot v8.2 ULTIMATE

**Asistente Financiero para el equipo de Oscar Casco**

## ✅ VERSION 8.2 - PRE-PROCESSED CHROMADB

Esta versión usa **ChromaDB pre-procesada** almacenada en Dropbox, eliminando 35-40 minutos de procesamiento.

### 🔥 QUÉ CAMBIÓ

**PROBLEMA:** GitHub no acepta archivos >25MB (chroma_db.zip = 74.79 MB)

**SOLUCIÓN V8.2:**
1. ✅ ChromaDB pre-procesada en **Google Colab** (1 vez)
2. ✅ Subida a **Dropbox** (almacenamiento ilimitado)
3. ✅ Render descarga ChromaDB lista para usar
4. ✅ Deployment **2-3 minutos** vs 35-45 minutos

### 📂 ESTRUCTURA DE ARCHIVOS

```
pipila-bot1/
├── pipila_bot.py                  # 🤖 Bot (v8.2 - usa ChromaDB pre-procesada)
├── download_chromadb.py           # 📥 Descarga ChromaDB desde Dropbox
├── upload_chromadb_to_dropbox.py  # 📤 Para subir ChromaDB (usar en Colab)
├── download_gdrive_recursive.py   # 📥 Descarga docs originales (ya no se usa)
├── render.yaml                    # ⚙️ Config Render.com
├── requirements_pipila.txt        # 📦 Dependencies
└── chroma_db/                     # 📚 Se descarga automáticamente
```

### 🚀 FLUJO DE TRABAJO

#### PASO 1: PREPARAR CHROMADB (1 VEZ)

**En Google Colab:**

```python
# 1. Procesa documentos (ya hecho en conversación anterior)
# Resultado: chroma_db.zip (74.79 MB, 19,121 chunks)

# 2. Sube a Dropbox
!python upload_chromadb_to_dropbox.py
```

**Configurar `upload_chromadb_to_dropbox.py`:**
- Línea 94: Pegar tu Dropbox Access Token
- Obtener token: https://www.dropbox.com/developers/apps

**Obtener link de Dropbox:**
1. Sube `chroma_db.zip` a Dropbox (vía script o manual)
2. Click derecho → "Share" → "Create link"
3. Copia el link y cambia `?dl=0` a `?dl=1`
4. Ejemplo: `https://www.dropbox.com/s/xxx/chroma_db.zip?dl=1`

#### PASO 2: CONFIGURAR DOWNLOAD

**Edita `download_chromadb.py` línea 23:**
```python
dropbox_url = "https://www.dropbox.com/s/TU_LINK/chroma_db.zip?dl=1"
```

#### PASO 3: DEPLOY

```bash
git add .
git commit -m "v8.2 ULTIMATE - Pre-processed ChromaDB from Dropbox"
git push origin main
```

**Render auto-deploy:**
- Build: ~2 minutos
- Download ChromaDB: ~30 segundos
- Start bot: ~10 segundos
- **Total: ~3 minutos** 🎉

### 📊 LOGS ESPERADOS

```
[CHROMADB] ======================================================================
[CHROMADB] 🔽 Downloading pre-processed ChromaDB from Dropbox
[CHROMADB] ======================================================================
[CHROMADB] Total size: 74.79 MB
[CHROMADB] Downloaded: 10.0 MB
[CHROMADB] Downloaded: 20.0 MB
...
[CHROMADB] ✅ Download complete: 74.79 MB
[CHROMADB] 📦 Extracting ChromaDB...
[CHROMADB] ✅ Extraction complete
[CHROMADB] ======================================================================
[CHROMADB] ✅ SUCCESS! ChromaDB ready
[CHROMADB] ======================================================================
[CHROMADB] 📁 Folder: ./chroma_db
[CHROMADB] 📊 Files: 27
[CHROMADB] ⚡ Saved: ~35-40 minutes of processing time!
[CHROMADB] ======================================================================

🚀 PIPILA v8.2 ULTIMATE
✅ Using pre-processed ChromaDB: 19121 chunks
✅ PIPILA started successfully
```

### 🎯 COMPARACIÓN DE VERSIONES

| Versión | Tiempo Deploy | Proceso |
|---------|--------------|---------|
| v8.1 | 35-45 min | Build + Download docs (1GB) + Process (228 docs) + Start |
| v8.2 | **2-3 min** | Build + Download ChromaDB (75MB) + Start |

**Ahorro:** ~32-42 minutos ⚡

### 🔄 ACTUALIZAR DOCUMENTOS

Si añades/cambias documentos:

1. **En Colab:** Re-procesa docs → nuevo `chroma_db.zip`
2. **Sube** nuevo ZIP a Dropbox (reemplaza)
3. **Redeploy** en Render (automático con push)

### 🛠️ DEPLOYMENT

**Variables de entorno en Render:**
```
BOT_TOKEN=tu_token_telegram
GEMINI_API_KEY=tu_api_key_gemini
DATABASE_URL=auto (desde render database)
```

### 📝 COMANDOS

- `/start` - Iniciar bot
- `/search [consulta]` - Buscar en documentos
- `/docs` - Ver documentos disponibles
- `/stats` - Ver estadísticas
- `/team` - Ver miembros del equipo
- `/lang` - Cambiar idioma (ES/DE)
- `/help` - Ayuda
- `/clear` - Limpiar historial

**Admin:**
- `/grant_team [id]` - Añadir usuario al equipo

### 🎯 CARACTERÍSTICAS

- 💬 Chat inteligente con memoria (Gemini 2.5 Flash)
- 📄 Procesa archivos PDF, DOCX, TXT
- 🔍 Sistema RAG con ChromaDB **pre-procesada**
- 🌍 Multilenguaje (Español/Deutsch)
- 👥 Sistema de equipos con permisos
- 📊 Estadísticas de uso
- 🗄️ PostgreSQL database
- ⚡ **Deployment ultra-rápido (2-3 min)**

### 📖 ÁREAS DE CONOCIMIENTO

- **DVAG** - Seguros y productos financieros
- **Generali** - Seguros de vida, salud, hogar
- **Badenia** - Bausparkasse (ahorro vivienda)
- **Advocard** - Protección jurídica

**Total:** 139 documentos, 19,121 chunks

### 🐛 TROUBLESHOOTING

**ChromaDB no descarga:**
- Verifica link de Dropbox termine en `?dl=1`
- Verifica link sea público
- Prueba descarga manual del link

**Bot sin documentos:**
- Check logs: `[CHROMADB] ✅ SUCCESS!`
- Verifica carpeta `./chroma_db` existe
- Chunks > 0 en logs de inicio

**Build falla:**
- Verifica `requirements_pipila.txt`
- Check Python version en Render

### 👨‍💻 DEVELOPER

Ernest Kostevich (@Ernest_Kostevich)

### 👔 CLIENTE

Oscar Casco

---

## 📋 CHECKLIST DEPLOYMENT

- [ ] ChromaDB procesada en Colab
- [ ] `chroma_db.zip` subido a Dropbox
- [ ] Link de Dropbox configurado en `download_chromadb.py`
- [ ] Variables de entorno en Render
- [ ] Push a GitHub
- [ ] Verificar logs: ChromaDB descargada
- [ ] Verificar logs: Bot iniciado con X chunks
- [ ] Test: enviar mensaje al bot

🎉 **¡Listo para producción!**
