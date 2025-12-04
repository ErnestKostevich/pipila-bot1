#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🤖 PIPILA - Asistente Financiero Oscar Casco
VERSION: 9.0 - RENDER OPTIMIZED
✅ Proper PostgreSQL connection
✅ Background document loading  
✅ Works on Render Standard plan (2GB RAM)
"""
import os
import sys
import json
import logging
import asyncio
from datetime import datetime
from typing import List, Dict
from pathlib import Path

from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters, CallbackQueryHandler
from telegram.constants import ParseMode
import google.generativeai as genai
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, Text, BigInteger
from sqlalchemy.orm import sessionmaker, declarative_base
import chromadb
import PyPDF2
import docx

# ============================================================================
# CONFIG
# ============================================================================
BOT_TOKEN = os.getenv('BOT_TOKEN')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
DATABASE_URL = os.getenv('DATABASE_URL')

# ✅ Fix for Render PostgreSQL URL format
if DATABASE_URL and DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

CREATOR_USERNAME = "Ernest_Kostevich"
CREATOR_ID = None
BOT_START_TIME = datetime.now()
DOCUMENTS_FOLDER = "./documents"

# ============================================================================
# LOGGING
# ============================================================================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Validate required env vars
if not BOT_TOKEN:
    logger.error("❌ BOT_TOKEN not found!")
    sys.exit(1)
if not GEMINI_API_KEY:
    logger.error("❌ GEMINI_API_KEY not found!")
    sys.exit(1)

logger.info(f"📊 DATABASE_URL: {'Set ✅' if DATABASE_URL else 'Not set ❌'}")

# ============================================================================
# TRANSLATIONS
# ============================================================================
TRANSLATIONS = {
    'es': {
        'welcome': """🤖 <b>¡Hola, {name}!</b>
Soy <b>PIPILA</b>, Asistente del <b>equipo de Oscar Casco</b>.

<b>💬 Uso:</b>
Escribe tu pregunta directamente o envía:
• 📄 Archivos PDF/DOCX/TXT

<b>Comandos:</b>
/search [consulta] - Buscar en documentos
/docs - Ver documentos cargados
/stats - Estadísticas
/lang - Cambiar idioma
/help - Ayuda

<b>📖 Áreas:</b>
DVAG • Generali • Badenia • Advocard

<b>👨‍💼 Creado por:</b> @{creator}""",
        'help': """📚 <b>COMANDOS PIPILA</b>

<b>🔍 Consultas:</b>
/search [pregunta] - Buscar en docs
Escribe directamente - responderé
📄 Envía archivo - lo proceso

<b>📊 Info:</b>
/docs - Documentos disponibles
/stats - Tus estadísticas
/team - Ver equipo
/lang - Cambiar idioma (ES/DE)
/clear - Limpiar historial

<b>💡 Ejemplos:</b>
"¿Qué es DVAG?"
"/search productos Generali"
"Explica Badenia" """,
        'docs': """📚 <b>DOCUMENTOS CARGADOS</b>
📊 Chunks en RAG: <b>{count}</b>

<b>📂 Categorías:</b>
• DVAG
• Generali
• Badenia
• Advocard

<b>💡 Uso:</b>
/search [tema] o escribe directamente""",
        'stats': """📊 <b>TUS ESTADÍSTICAS</b>

<b>👤 Perfil:</b>
• {name}
• @{username}
• {access}

<b>📈 Actividad:</b>
• Consultas: <b>{queries}</b>

<b>🤖 Sistema:</b>
• Docs: {docs} chunks
• Uptime: {uptime}
• AI: Gemini 2.5 Flash ✅
• DB: {db}
• Idioma: 🇪🇸 Español""",
        'team': """👥 <b>EQUIPO OSCAR CASCO</b>
<b>Total:</b> {count}

{members}""",
        'info': """🤖 <b>PIPILA v9.0</b>
<i>Asistente Equipo Oscar Casco</i>

<b>🧠 Capacidades:</b>
• 💬 Chat inteligente con memoria
• 📄 Procesamiento de archivos
• 🌍 Multilenguaje (ES/DE)
• 📚 RAG con ChromaDB

<b>👨‍💻 Dev:</b> @Ernest_Kostevich
<b>👔 Cliente:</b> Oscar Casco""",
        'no_docs': '⚠️ No hay documentos cargados.',
        'team_only': '⚠️ Solo para miembros del equipo.',
        'admin_only': '❌ Solo para administradores.',
        'cleared': '🧹 ¡Historial limpio!',
        'error': '😔 Error: {error}',
        'processing': '⏳ Procesando...',
        'processing_file': '📄 Procesando archivo...',
        'no_query': '❓ Uso: /search [consulta]',
        'invalid_id': '❌ ID inválido',
        'user_added': '✅ Usuario {id} añadido al equipo!',
        'reloading': '🔄 Recargando documentos...',
        'reloaded': '✅ Documentos: <b>{docs}</b>\nChunks: <b>{chunks}</b>',
        'lang_changed': '✅ Idioma: 🇪🇸 Español',
        'choose_lang': '🌍 <b>Selecciona idioma:</b>',
        'ask_question': '💬 Escribe tu pregunta',
        'file_processed': '✅ {filename}\n\n{response}',
        'file_error': '❌ Error: {error}',
        'keyboard': {
            'consult': '💬 Consultar',
            'docs': '📚 Documentos',
            'stats': '📊 Estadísticas',
            'team': '👥 Equipo',
            'info': 'ℹ️ Info',
            'help': '❓ Ayuda'
        }
    },
    'de': {
        'welcome': """🤖 <b>Hallo, {name}!</b>
Ich bin <b>PIPILA</b>, Assistent des <b>Teams von Oscar Casco</b>.

<b>💬 Verwendung:</b>
Stelle direkt deine Frage oder sende:
• 📄 PDF/DOCX/TXT Dateien

<b>Befehle:</b>
/search [Anfrage] - Suchen
/docs - Dokumente ansehen
/stats - Statistiken
/lang - Sprache ändern
/help - Hilfe

<b>📖 Bereiche:</b>
DVAG • Generali • Badenia • Advocard

<b>👨‍💼 Erstellt von:</b> @{creator}""",
        'help': """📚 <b>PIPILA BEFEHLE</b>

<b>🔍 Anfragen:</b>
/search [Frage] - In Docs suchen
Direkt schreiben - ich antworte
📄 Datei senden - ich verarbeite

<b>📊 Info:</b>
/docs - Verfügbare Dokumente
/stats - Deine Statistiken
/team - Team ansehen
/lang - Sprache ändern (ES/DE)
/clear - Verlauf löschen""",
        'docs': """📚 <b>GELADENE DOKUMENTE</b>
📊 Chunks in RAG: <b>{count}</b>

<b>📂 Kategorien:</b>
• DVAG
• Generali
• Badenia
• Advocard""",
        'stats': """📊 <b>DEINE STATISTIKEN</b>

<b>👤 Profil:</b>
• {name}
• @{username}
• {access}

<b>📈 Aktivität:</b>
• Anfragen: <b>{queries}</b>

<b>🤖 System:</b>
• Docs: {docs} Chunks
• Uptime: {uptime}
• AI: Gemini 2.5 Flash ✅
• DB: {db}
• Sprache: 🇩🇪 Deutsch""",
        'team': """👥 <b>OSCAR CASCO TEAM</b>
<b>Gesamt:</b> {count}

{members}""",
        'info': """🤖 <b>PIPILA v9.0</b>
<i>Oscar Casco Team Assistent</i>

<b>🧠 Fähigkeiten:</b>
• 💬 Intelligenter Chat
• 📄 Dateiverarbeitung
• 🌍 Mehrsprachig (ES/DE)
• 📚 RAG mit ChromaDB

<b>👨‍💻 Dev:</b> @Ernest_Kostevich
<b>👔 Kunde:</b> Oscar Casco""",
        'no_docs': '⚠️ Keine Dokumente geladen.',
        'team_only': '⚠️ Nur für Teammitglieder.',
        'admin_only': '❌ Nur für Administratoren.',
        'cleared': '🧹 Verlauf gelöscht!',
        'error': '😔 Fehler: {error}',
        'processing': '⏳ Verarbeite...',
        'processing_file': '📄 Verarbeite Datei...',
        'no_query': '❓ Verwendung: /search [Anfrage]',
        'invalid_id': '❌ Ungültige ID',
        'user_added': '✅ Benutzer {id} hinzugefügt!',
        'reloading': '🔄 Lade Dokumente neu...',
        'reloaded': '✅ Dokumente: <b>{docs}</b>\nChunks: <b>{chunks}</b>',
        'lang_changed': '✅ Sprache: 🇩🇪 Deutsch',
        'choose_lang': '🌍 <b>Sprache wählen:</b>',
        'ask_question': '💬 Stelle deine Frage',
        'file_processed': '✅ {filename}\n\n{response}',
        'file_error': '❌ Fehler: {error}',
        'keyboard': {
            'consult': '💬 Anfragen',
            'docs': '📚 Dokumente',
            'stats': '📊 Statistiken',
            'team': '👥 Team',
            'info': 'ℹ️ Info',
            'help': '❓ Hilfe'
        }
    }
}

def get_text(lang: str, key: str, **kwargs) -> str:
    text = TRANSLATIONS.get(lang, TRANSLATIONS['es']).get(key, key)
    return text.format(**kwargs) if kwargs else text

def detect_language(text: str) -> str:
    text_lower = text.lower()
    de_words = ['was', 'wie', 'wo', 'wann', 'warum', 'ist', 'sind', 'haben', 'können', 'möchte', 'bitte', 'danke']
    es_words = ['qué', 'cómo', 'dónde', 'cuándo', 'por qué', 'es', 'son', 'tener', 'poder', 'quiero', 'gracias']
    de_count = sum(1 for word in de_words if word in text_lower)
    es_count = sum(1 for word in es_words if word in text_lower)
    return 'de' if de_count > es_count else 'es'

# ============================================================================
# GEMINI AI
# ============================================================================
genai.configure(api_key=GEMINI_API_KEY)
generation_config = {
    "temperature": 0.7,
    "top_p": 0.95,
    "top_k": 40,
    "max_output_tokens": 1024,
}
safety_settings = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
]
SYSTEM_INSTRUCTIONS = {
    'es': """Eres PIPILA, Asistente Financiero del equipo de Oscar Casco.
Responde en español. Sé profesional y conciso (máximo 300 palabras).
Áreas: DVAG, Generali, Badenia, Advocard
Si tienes documentos, cítalos: "Según [documento]..."
Si no sabes algo, admítelo.""",
    'de': """Du bist PIPILA, Finanzassistent des Teams von Oscar Casco.
Antworte auf Deutsch. Sei professionell und präzise (max 300 Wörter).
Bereiche: DVAG, Generali, Badenia, Advocard
Zitiere Dokumente wenn vorhanden.
Gib zu wenn du etwas nicht weißt."""
}

model_text = genai.GenerativeModel(
    model_name='gemini-2.5-flash-preview-05-20',
    generation_config=generation_config,
    safety_settings=safety_settings
)
logger.info("✅ Gemini configured")

# ============================================================================
# CHAT SESSIONS
# ============================================================================
chat_sessions = {}
user_languages = {}

def get_chat_session(user_id: int, lang: str = 'es'):
    if user_id not in chat_sessions:
        user_model = genai.GenerativeModel(
            model_name='gemini-2.5-flash-preview-05-20',
            generation_config=generation_config,
            safety_settings=safety_settings,
            system_instruction=SYSTEM_INSTRUCTIONS[lang]
        )
        chat_sessions[user_id] = user_model.start_chat(history=[])
    return chat_sessions[user_id]

def clear_chat_session(user_id: int):
    chat_sessions.pop(user_id, None)

def get_user_language(user_id: int) -> str:
    return user_languages.get(user_id, 'es')

def set_user_language(user_id: int, lang: str):
    user_languages[user_id] = lang
    clear_chat_session(user_id)

# ============================================================================
# AI FUNCTIONS
# ============================================================================
async def generate_response(query: str, user_id: int = None, context_docs: List[Dict] = None) -> str:
    try:
        lang = get_user_language(user_id) if user_id else 'es'
        chat = get_chat_session(user_id, lang) if user_id else model_text.start_chat(history=[])
        
        if context_docs:
            context = "\n\n".join([f"📄 {d['source']}: {d['text'][:500]}" for d in context_docs])
            prompt = f"DOCUMENTOS:\n{context}\n\nPREGUNTA: {query}\n\nResponde citando documentos."
        else:
            prompt = f"PREGUNTA: {query}\n\nNo hay documentos. Responde según tu conocimiento."
        
        for attempt in range(3):
            try:
                response = chat.send_message(prompt)
                return response.text
            except Exception as e:
                logger.error(f"Gemini retry {attempt}: {e}")
                await asyncio.sleep(2)
        
        return get_text(lang, 'error', error="AI no disponible")
    except Exception as e:
        logger.error(f"Generate error: {e}")
        return get_text(lang, 'error', error=str(e)[:100])

async def process_file(file_bytes: bytes, filename: str, query: str = "", user_id: int = None) -> str:
    try:
        lang = get_user_language(user_id) if user_id else 'es'
        ext = Path(filename).suffix.lower()
        
        temp_path = f"/tmp/{filename}"
        with open(temp_path, 'wb') as f:
            f.write(file_bytes)
        
        text = ""
        if ext == '.pdf':
            text = extract_pdf(temp_path)
        elif ext in ['.docx', '.doc']:
            text = extract_docx(temp_path)
        elif ext == '.txt':
            text = file_bytes.decode('utf-8', errors='ignore')
        
        os.remove(temp_path)
        
        if not text or len(text) < 10:
            return get_text(lang, 'file_error', error="No se pudo extraer texto")
        
        chat = get_chat_session(user_id, lang)
        prompt = f"ARCHIVO: {filename}\nCONTENIDO:\n{text[:3000]}\n\n{f'PREGUNTA: {query}' if query else 'Resume el documento.'}"
        
        response = chat.send_message(prompt)
        return response.text
    except Exception as e:
        logger.error(f"File error: {e}")
        return get_text(lang, 'file_error', error=str(e)[:100])

# ============================================================================
# CHROMADB - RAG
# ============================================================================
chroma_client = None
collection = None

def init_chromadb():
    global chroma_client, collection
    try:
        chroma_client = chromadb.PersistentClient(path="./chroma_db")
        collection = chroma_client.get_or_create_collection(
            name="pipila_docs",
            metadata={"hnsw:space": "cosine"}
        )
        logger.info(f"✅ ChromaDB: {collection.count()} chunks")
        return True
    except Exception as e:
        logger.error(f"❌ ChromaDB error: {e}")
        return False

def extract_pdf(path: str) -> str:
    try:
        with open(path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            return "\n".join([p.extract_text() or "" for p in reader.pages])
    except Exception as e:
        logger.error(f"PDF error: {e}")
        return ""

def extract_docx(path: str) -> str:
    try:
        doc = docx.Document(path)
        return "\n".join([p.text for p in doc.paragraphs if p.text])
    except Exception as e:
        logger.error(f"DOCX error: {e}")
        return ""

def chunk_text(text: str, size: int = 1000, overlap: int = 200) -> List[str]:
    if not text or len(text) < 100:
        return []
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start += size - overlap
    return chunks

def load_documents(folder: str = DOCUMENTS_FOLDER) -> int:
    """Load documents into ChromaDB"""
    if not collection:
        logger.error("ChromaDB not initialized")
        return 0
    
    if not os.path.exists(folder):
        logger.warning(f"Folder not found: {folder}")
        return 0
    
    loaded = 0
    total_chunks = 0
    
    for file in os.listdir(folder):
        path = os.path.join(folder, file)
        ext = Path(file).suffix.lower()
        
        if ext not in ['.pdf', '.docx', '.doc', '.txt']:
            continue
        
        try:
            if os.path.getsize(path) > 10 * 1024 * 1024:  # Skip >10MB
                continue
            
            if ext == '.pdf':
                text = extract_pdf(path)
            elif ext in ['.docx', '.doc']:
                text = extract_docx(path)
            elif ext == '.txt':
                with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                    text = f.read()
            else:
                continue
            
            if not text or len(text) < 100:
                continue
            
            chunks = chunk_text(text)
            if not chunks:
                continue
            
            for i, chunk in enumerate(chunks):
                doc_id = f"{file}_{i}_{hash(chunk) % 10000}"
                try:
                    collection.add(
                        documents=[chunk],
                        ids=[doc_id],
                        metadatas=[{"source": file, "chunk": i}]
                    )
                except:
                    pass
            
            loaded += 1
            total_chunks += len(chunks)
            logger.info(f"✅ {file}: {len(chunks)} chunks")
            
        except Exception as e:
            logger.error(f"Error {file}: {e}")
    
    logger.info(f"📚 Loaded: {loaded} docs, {total_chunks} chunks")
    return loaded

def search_rag(query: str, n: int = 3) -> List[Dict]:
    """Search documents"""
    if not collection or collection.count() == 0:
        return []
    try:
        results = collection.query(query_texts=[query], n_results=n)
        docs = []
        if results['documents'] and results['documents'][0]:
            for i, doc in enumerate(results['documents'][0]):
                docs.append({
                    'text': doc,
                    'source': results['metadatas'][0][i].get('source', 'Unknown')
                })
        return docs
    except Exception as e:
        logger.error(f"Search error: {e}")
        return []

# ============================================================================
# DATABASE
# ============================================================================
Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(BigInteger, primary_key=True)
    username = Column(String(255))
    first_name = Column(String(255))
    is_team = Column(Boolean, default=False)
    language = Column(String(2), default='es')
    registered = Column(DateTime, default=datetime.now)
    last_active = Column(DateTime, default=datetime.now)
    query_count = Column(Integer, default=0)

class QueryLog(Base):
    __tablename__ = 'queries'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger)
    query = Column(Text)
    response = Column(Text)
    timestamp = Column(DateTime, default=datetime.now)

engine = None
Session = None

def init_database():
    global engine, Session
    
    if not DATABASE_URL:
        logger.warning("⚠️ No DATABASE_URL - using JSON storage")
        return False
    
    try:
        engine = create_engine(DATABASE_URL, echo=False, pool_pre_ping=True)
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        
        # Test connection
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        
        logger.info("✅ PostgreSQL connected")
        return True
    except Exception as e:
        logger.error(f"❌ Database error: {e}")
        engine = None
        Session = None
        return False

# ============================================================================
# STORAGE
# ============================================================================
class Storage:
    def __init__(self):
        self.users_file = 'users.json'
        self.users = self._load_json() if not engine else {}
    
    def _load_json(self) -> Dict:
        try:
            if os.path.exists(self.users_file):
                with open(self.users_file, 'r') as f:
                    return {int(k): v for k, v in json.load(f).items()}
        except:
            pass
        return {}
    
    def _save_json(self):
        if engine:
            return
        try:
            with open(self.users_file, 'w') as f:
                json.dump(self.users, f, indent=2)
        except:
            pass
    
    def get_user(self, user_id: int) -> Dict:
        if engine and Session:
            session = Session()
            try:
                user = session.query(User).filter_by(id=user_id).first()
                if not user:
                    user = User(id=user_id)
                    session.add(user)
                    session.commit()
                if user.language:
                    user_languages[user_id] = user.language
                return {
                    'id': user.id,
                    'username': user.username or '',
                    'first_name': user.first_name or '',
                    'is_team': user.is_team,
                    'language': user.language or 'es',
                    'query_count': user.query_count or 0
                }
            except:
                session.rollback()
            finally:
                session.close()
        
        if user_id not in self.users:
            self.users[user_id] = {
                'id': user_id, 'username': '', 'first_name': '',
                'is_team': False, 'language': 'es', 'query_count': 0
            }
            self._save_json()
        return self.users[user_id]
    
    def update_user(self, user_id: int, data: Dict):
        if engine and Session:
            session = Session()
            try:
                user = session.query(User).filter_by(id=user_id).first()
                if not user:
                    user = User(id=user_id)
                    session.add(user)
                for k, v in data.items():
                    setattr(user, k, v)
                user.last_active = datetime.now()
                session.commit()
                if 'language' in data:
                    user_languages[user_id] = data['language']
            except:
                session.rollback()
            finally:
                session.close()
        else:
            user = self.get_user(user_id)
            user.update(data)
            if 'language' in data:
                user_languages[user_id] = data['language']
            self._save_json()
    
    def is_team(self, user_id: int) -> bool:
        if user_id == CREATOR_ID:
            return True
        return self.get_user(user_id).get('is_team', False)
    
    def save_query(self, user_id: int, query: str, response: str):
        if not engine or not Session:
            return
        session = Session()
        try:
            session.add(QueryLog(user_id=user_id, query=query[:1000], response=response[:1000]))
            session.commit()
        except:
            session.rollback()
        finally:
            session.close()
    
    def get_team(self) -> List[Dict]:
        if engine and Session:
            session = Session()
            try:
                users = session.query(User).filter_by(is_team=True).all()
                return [{'id': u.id, 'username': u.username, 'first_name': u.first_name, 'query_count': u.query_count} for u in users]
            except:
                return []
            finally:
                session.close()
        return [u for u in self.users.values() if u.get('is_team')]

storage = None

# ============================================================================
# UTILS
# ============================================================================
def identify_creator(user):
    global CREATOR_ID
    if user.username == CREATOR_USERNAME and CREATOR_ID is None:
        CREATOR_ID = user.id
        logger.info(f"✅ Creator: @{user.username} (ID: {user.id})")

def is_creator(user_id: int) -> bool:
    return user_id == CREATOR_ID

def get_keyboard(lang: str = 'es') -> ReplyKeyboardMarkup:
    kb = TRANSLATIONS[lang]['keyboard']
    return ReplyKeyboardMarkup([
        [KeyboardButton(kb['consult']), KeyboardButton(kb['docs'])],
        [KeyboardButton(kb['stats']), KeyboardButton(kb['team'])],
        [KeyboardButton(kb['info']), KeyboardButton(kb['help'])]
    ], resize_keyboard=True)

# ============================================================================
# COMMANDS
# ============================================================================
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    identify_creator(user)
    data = storage.get_user(user.id)
    lang = data.get('language', 'es')
    storage.update_user(user.id, {'username': user.username or '', 'first_name': user.first_name or ''})
    await update.message.reply_text(
        get_text(lang, 'welcome', name=user.first_name, creator=CREATOR_USERNAME),
        parse_mode=ParseMode.HTML,
        reply_markup=get_keyboard(lang)
    )

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_user_language(update.effective_user.id)
    text = get_text(lang, 'help')
    if is_creator(update.effective_user.id):
        text += "\n\n<b>Admin:</b> /grant_team [ID], /reload"
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)

async def cmd_lang(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🇪🇸 Español", callback_data="lang_es"),
         InlineKeyboardButton("🇩🇪 Deutsch", callback_data="lang_de")]
    ])
    await update.message.reply_text(
        get_text(get_user_language(update.effective_user.id), 'choose_lang'),
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard
    )

async def callback_lang(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = query.data.split('_')[1]
    set_user_language(query.from_user.id, lang)
    storage.update_user(query.from_user.id, {'language': lang})
    await query.edit_message_text(get_text(lang, 'lang_changed'), parse_mode=ParseMode.HTML)
    await query.message.reply_text("✅", reply_markup=get_keyboard(lang))

async def cmd_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_language(user_id)
    
    if not context.args:
        await update.message.reply_text(get_text(lang, 'no_query'))
        return
    
    query = ' '.join(context.args)
    await update.message.chat.send_action("typing")
    
    docs = search_rag(query)
    response = await generate_response(query, user_id, docs)
    
    storage.save_query(user_id, query, response)
    user = storage.get_user(user_id)
    storage.update_user(user_id, {'query_count': user.get('query_count', 0) + 1})
    
    await update.message.reply_text(f"🔍 <b>{query}</b>\n\n{response}", parse_mode=ParseMode.HTML)

async def cmd_docs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_user_language(update.effective_user.id)
    count = collection.count() if collection else 0
    await update.message.reply_text(get_text(lang, 'docs', count=count), parse_mode=ParseMode.HTML)

async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_language(user_id)
    user = storage.get_user(user_id)
    uptime = datetime.now() - BOT_START_TIME
    
    await update.message.reply_text(get_text(lang, 'stats',
        name=user.get('first_name', 'N/A'),
        username=user.get('username', 'N/A'),
        access="✅ Equipo" if storage.is_team(user_id) else "⏳",
        queries=user.get('query_count', 0),
        docs=collection.count() if collection else 0,
        uptime=f"{uptime.days}d {uptime.seconds//3600}h",
        db="PostgreSQL ✅" if engine else "JSON"
    ), parse_mode=ParseMode.HTML)

async def cmd_team(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_language(user_id)
    
    if not storage.is_team(user_id):
        await update.message.reply_text(get_text(lang, 'team_only'))
        return
    
    team = storage.get_team()
    if not team:
        await update.message.reply_text("👥 No hay miembros aún.")
        return
    
    members = "\n".join([f"• <b>{m.get('first_name', 'N/A')}</b> (@{m.get('username', 'N/A')})" for m in team])
    await update.message.reply_text(get_text(lang, 'team', count=len(team), members=members), parse_mode=ParseMode.HTML)

async def cmd_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_user_language(update.effective_user.id)
    await update.message.reply_text(get_text(lang, 'info'), parse_mode=ParseMode.HTML)

async def cmd_reload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_language(user_id)
    
    if not is_creator(user_id):
        await update.message.reply_text(get_text(lang, 'admin_only'))
        return
    
    msg = await update.message.reply_text(get_text(lang, 'reloading'))
    docs = load_documents()
    chunks = collection.count() if collection else 0
    await msg.edit_text(get_text(lang, 'reloaded', docs=docs, chunks=chunks), parse_mode=ParseMode.HTML)

async def cmd_grant(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_language(user_id)
    
    if not is_creator(user_id):
        await update.message.reply_text(get_text(lang, 'admin_only'))
        return
    
    if not context.args:
        await update.message.reply_text("❓ /grant_team [user_id]")
        return
    
    try:
        target = int(context.args[0])
        storage.update_user(target, {'is_team': True})
        await update.message.reply_text(get_text(lang, 'user_added', id=target))
    except:
        await update.message.reply_text(get_text(lang, 'invalid_id'))

async def cmd_clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    clear_chat_session(user_id)
    await update.message.reply_text(get_text(get_user_language(user_id), 'cleared'))

# ============================================================================
# MESSAGE HANDLERS
# ============================================================================
async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    identify_creator(user)
    lang = get_user_language(user.id)
    
    doc = update.message.document
    ext = Path(doc.file_name).suffix.lower()
    
    if ext not in ['.pdf', '.docx', '.doc', '.txt']:
        await update.message.reply_text("⚠️ Solo PDF, DOCX, TXT")
        return
    
    await update.message.chat.send_action("typing")
    await update.message.reply_text(get_text(lang, 'processing_file'))
    
    try:
        file = await context.bot.get_file(doc.file_id)
        data = await file.download_as_bytearray()
        response = await process_file(bytes(data), doc.file_name, update.message.caption or "", user.id)
        
        storage.save_query(user.id, f"[FILE: {doc.file_name}]", response)
        u = storage.get_user(user.id)
        storage.update_user(user.id, {'query_count': u.get('query_count', 0) + 1})
        
        await update.message.reply_text(
            get_text(lang, 'file_processed', filename=doc.file_name, response=response),
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        await update.message.reply_text(get_text(lang, 'file_error', error=str(e)[:100]))

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    identify_creator(user)
    text = update.message.text
    
    # Detect and set language
    detected = detect_language(text)
    current = get_user_language(user.id)
    if detected != current:
        set_user_language(user.id, detected)
        storage.update_user(user.id, {'language': detected})
        current = detected
    
    # Check keyboard buttons
    kb = TRANSLATIONS[current]['keyboard']
    if text == kb['consult']:
        await update.message.reply_text(get_text(current, 'ask_question'))
        return
    elif text == kb['docs']:
        await cmd_docs(update, context)
        return
    elif text == kb['stats']:
        await cmd_stats(update, context)
        return
    elif text == kb['team']:
        await cmd_team(update, context)
        return
    elif text == kb['info']:
        await cmd_info(update, context)
        return
    elif text == kb['help']:
        await cmd_help(update, context)
        return
    
    # Regular message - search and respond
    if text and not text.startswith('/'):
        await update.message.chat.send_action("typing")
        
        docs = search_rag(text)
        response = await generate_response(text, user.id, docs)
        
        storage.save_query(user.id, text, response)
        u = storage.get_user(user.id)
        storage.update_user(user.id, {'query_count': u.get('query_count', 0) + 1})
        
        await update.message.reply_text(response, parse_mode=ParseMode.HTML)

# ============================================================================
# BACKGROUND LOADING
# ============================================================================
async def load_docs_background():
    """Load documents in background after bot starts"""
    logger.info("📚 Starting background document loading...")
    await asyncio.sleep(5)
    
    try:
        count = load_documents()
        logger.info(f"✅ Background loading complete: {count} docs, {collection.count() if collection else 0} chunks")
    except Exception as e:
        logger.error(f"❌ Background loading error: {e}")

# ============================================================================
# MAIN
# ============================================================================
def main():
    global storage
    
    logger.info("=" * 50)
    logger.info("🤖 PIPILA v9.0 - RENDER OPTIMIZED")
    logger.info("=" * 50)
    
    # Initialize database
    init_database()
    
    # Initialize ChromaDB
    init_chromadb()
    
    # Initialize storage
    storage = Storage()
    
    # Check documents folder
    if os.path.exists(DOCUMENTS_FOLDER):
        files = list(Path(DOCUMENTS_FOLDER).glob("*"))
        logger.info(f"📂 Documents folder: {len(files)} files")
    else:
        logger.warning("⚠️ Documents folder not found")
    
    # Build application
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("lang", cmd_lang))
    app.add_handler(CallbackQueryHandler(callback_lang, pattern="^lang_"))
    app.add_handler(CommandHandler("search", cmd_search))
    app.add_handler(CommandHandler("docs", cmd_docs))
    app.add_handler(CommandHandler("stats", cmd_stats))
    app.add_handler(CommandHandler("team", cmd_team))
    app.add_handler(CommandHandler("info", cmd_info))
    app.add_handler(CommandHandler("reload", cmd_reload))
    app.add_handler(CommandHandler("grant_team", cmd_grant))
    app.add_handler(CommandHandler("clear", cmd_clear))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Background loading
    async def post_init(application):
        asyncio.create_task(load_docs_background())
    
    app.post_init = post_init
    
    logger.info("=" * 50)
    logger.info(f"✅ Bot ready")
    logger.info(f"📊 DB: {'PostgreSQL' if engine else 'JSON'}")
    logger.info(f"📚 RAG: {collection.count() if collection else 0} chunks")
    logger.info("=" * 50)
    
    # Run
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

if __name__ == '__main__':
    main()

