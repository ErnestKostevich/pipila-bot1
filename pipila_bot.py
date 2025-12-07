#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🤖 PIPILA - Asistente Financiero Oscar Casco
VERSION: 8.3 - GRANT BY USERNAME
✅ Uses pre-processed ChromaDB from GitHub Releases
✅ Grant team access by ID or @username
✅ Works on Python 3.13
✅ Works on Render.com
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
CREATOR_USERNAME = "Ernest_Kostevich"
CREATOR_ID = None
BOT_START_TIME = datetime.now()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[logging.FileHandler("bot.log"), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

if not BOT_TOKEN or not GEMINI_API_KEY:
    raise ValueError("❌ BOT_TOKEN or GEMINI_API_KEY not found")

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
/search [consulta] - Buscar
/docs - Ver documentos
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
"Explica Badenia"
📄 [archivo PDF]""",
        'docs': """📚 <b>DOCUMENTOS EQUIPO</b>
📊 Chunks en RAG: <b>{count}</b>

<b>📂 Categorías:</b>
• DVAG
• Generali
• Badenia
• Advocard

<b>💡 Uso:</b>
/search [tema] o escribe directamente
📄 Envía archivos PDF/DOCX/TXT""",
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
• DB: {db} ✅
• Idioma: 🇪🇸 Español""",
        'team': """👥 <b>EQUIPO OSCAR CASCO</b>
<b>Total:</b> {count}

{members}""",
        'info': """🤖 <b>PIPILA</b>
<i>Asistente Equipo Oscar Casco</i>

<b>📖 Versión:</b> 8.3
<b>🧠 Capacidades:</b>
• 💬 Chat inteligente con memoria
• 📄 Procesamiento de archivos
• 🌍 Multilenguaje (ES/DE)
• 📚 RAG con ChromaDB pre-procesada

<b>🤖 Tech:</b>
• Gemini 2.5 Flash
• ChromaDB + RAG (pre-procesada)
• PostgreSQL
• GitHub Releases Storage

<b>👨‍💻 Dev:</b> @Ernest_Kostevich
<b>👔 Cliente:</b> Oscar Casco""",
        'no_docs': '⚠️ No hay documentos cargados. Contacta al admin.',
        'team_only': '⚠️ Solo para miembros del equipo.\n\nContacta al admin.',
        'admin_only': '❌ Solo para administradores.',
        'cleared': '🧹 ¡Historial limpio!',
        'error': '😔 Error: {error}',
        'processing': '⏳ Procesando...',
        'processing_file': '📄 Procesando archivo...',
        'no_query': '❓ Uso: /search [consulta]\n\nEjemplo: /search productos DVAG',
        'invalid_id': '❌ ID inválido',
        'user_added': '✅ Usuario {id} añadido al equipo!',
        'lang_changed': '✅ Idioma cambiado a: 🇪🇸 Español',
        'choose_lang': '🌍 <b>Selecciona idioma:</b>',
        'ask_question': '💬 Escribe tu pregunta',
        'file_processed': '✅ Archivo procesado: {filename}\n\n{response}',
        'file_error': '❌ Error procesando archivo: {error}',
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
/clear - Verlauf löschen

<b>💡 Beispiele:</b>
"Was ist DVAG?"
"/search Generali Produkte"
"Erkläre Badenia"
📄 [PDF Datei]""",
        'docs': """📚 <b>TEAM DOKUMENTE</b>
📊 Chunks in RAG: <b>{count}</b>

<b>📂 Kategorien:</b>
• DVAG
• Generali
• Badenia
• Advocard

<b>💡 Verwendung:</b>
/search [Thema] oder direkt schreiben
📄 PDF/DOCX/TXT Dateien senden""",
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
• DB: {db} ✅
• Sprache: 🇩🇪 Deutsch""",
        'team': """👥 <b>OSCAR CASCO TEAM</b>
<b>Gesamt:</b> {count}

{members}""",
        'info': """🤖 <b>PIPILA</b>
<i>Oscar Casco Team Assistent</i>

<b>📖 Version:</b> 8.3
<b>🧠 Fähigkeiten:</b>
• 💬 Intelligenter Chat mit Gedächtnis
• 📄 Dateiverarbeitung
• 🌍 Mehrsprachig (ES/DE)
• 📚 RAG mit ChromaDB (vorverarbeitet)

<b>🤖 Tech:</b>
• Gemini 2.5 Flash
• ChromaDB + RAG (vorverarbeitet)
• PostgreSQL
• GitHub Releases Storage

<b>👨‍💻 Dev:</b> @Ernest_Kostevich
<b>👔 Kunde:</b> Oscar Casco""",
        'no_docs': '⚠️ Keine Dokumente geladen. Kontaktiere den Admin.',
        'team_only': '⚠️ Nur für Teammitglieder.\n\nKontaktiere den Admin.',
        'admin_only': '❌ Nur für Administratoren.',
        'cleared': '🧹 Verlauf gelöscht!',
        'error': '😔 Fehler: {error}',
        'processing': '⏳ Verarbeite...',
        'processing_file': '📄 Verarbeite Datei...',
        'no_query': '❓ Verwendung: /search [Anfrage]\n\nBeispiel: /search DVAG Produkte',
        'invalid_id': '❌ Ungültige ID',
        'user_added': '✅ Benutzer {id} zum Team hinzugefügt!',
        'lang_changed': '✅ Sprache geändert zu: 🇩🇪 Deutsch',
        'choose_lang': '🌍 <b>Sprache wählen:</b>',
        'ask_question': '💬 Stelle deine Frage',
        'file_processed': '✅ Datei verarbeitet: {filename}\n\n{response}',
        'file_error': '❌ Fehler beim Verarbeiten der Datei: {error}',
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
    de_words = ['was', 'wie', 'wo', 'wann', 'warum', 'ist', 'sind', 'haben', 'können',
                'möchte', 'bitte', 'danke', 'gut', 'schlecht', 'ja', 'nein', 'ich', 'du', 'er', 'sie']
    es_words = ['qué', 'cómo', 'dónde', 'cuándo', 'por qué', 'es', 'son', 'tener', 'poder',
                'quiero', 'por favor', 'gracias', 'bueno', 'malo', 'sí', 'no', 'yo', 'tú', 'él', 'ella']
    de_count = sum(1 for word in de_words if word in text_lower)
    es_count = sum(1 for word in es_words if word in text_lower)
    return 'de' if de_count > es_count else 'es'

# ============================================================================
# GEMINI AI
# ============================================================================
genai.configure(api_key=GEMINI_API_KEY)
generation_config = {
    "temperature": 1,
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
    'es': """Eres PIPILA, el Asistente Financiero del equipo de Oscar Casco.
Responde SIEMPRE en español. Sé profesional, claro y conciso (máximo 300 palabras).
Áreas de expertise: DVAG, Generali, Badenia, Advocard
Si tienes documentos en el contexto, cítalos: "Según el documento [nombre]..."
Si procesas un archivo, resume su contenido y responde la pregunta del usuario.
Si no tienes información, admítelo claramente.""",
    'de': """Du bist PIPILA, der Finanzassistent des Teams von Oscar Casco.
Antworte IMMER auf Deutsch. Sei professionell, klar und präzise (maximal 300 Wörter).
Fachgebiete: DVAG, Generali, Badenia, Advocard
Wenn du Dokumente im Kontext hast, zitiere sie: "Laut Dokument [Name]..."
Wenn du eine Datei verarbeitest, fasse ihren Inhalt zusammen und beantworte die Frage des Benutzers.
Wenn du keine Informationen hast, gib das klar zu."""
}
model_text = genai.GenerativeModel(
    model_name='gemini-2.5-flash',
    generation_config=generation_config,
    safety_settings=safety_settings
)
logger.info("✅ Gemini 2.5 Flash configured")

# ============================================================================
# CHAT SESSIONS
# ============================================================================
chat_sessions = {}
user_languages = {}

def get_chat_session(user_id: int, lang: str = 'es'):
    if user_id not in chat_sessions:
        user_model = genai.GenerativeModel(
            model_name='gemini-2.5-flash',
            generation_config=generation_config,
            safety_settings=safety_settings,
            system_instruction=SYSTEM_INSTRUCTIONS[lang]
        )
        chat_sessions[user_id] = user_model.start_chat(history=[])
    return chat_sessions[user_id]

def clear_chat_session(user_id: int):
    if user_id in chat_sessions:
        del chat_sessions[user_id]

def get_user_language(user_id: int) -> str:
    return user_languages.get(user_id, 'es')

def set_user_language(user_id: int, lang: str):
    user_languages[user_id] = lang
    clear_chat_session(user_id)

# ============================================================================
# AI FUNCTIONS
# ============================================================================
async def generate_text_response(query: str, user_id: int = None, context_docs: List[Dict] = None) -> str:
    try:
        lang = get_user_language(user_id) if user_id else 'es'
        chat = get_chat_session(user_id, lang) if user_id else model_text.start_chat(history=[])
        
        if context_docs:
            context_text = "\n\n".join([f"📄 {doc['source']}: {doc['text'][:500]}" for doc in context_docs])
            prompt = f"DOCUMENTOS:\n{context_text}\n\nPREGUNTA: {query[:300]}\n\nResponde breve (máx 200 palabras), citando documentos." if lang == 'es' else f"DOKUMENTE:\n{context_text}\n\nFRAGE: {query[:300]}\n\nAntworte kurz (max 200 Wörter), zitiere Dokumente."
        else:
            prompt = f"PREGUNTA: {query[:300]}\n\nSin documentos. Responde breve (máx 150 palabras)." if lang == 'es' else f"FRAGE: {query[:300]}\n\nKeine Dokumente. Antworte kurz (max 150 Wörter)."
        
        for attempt in range(3):
            try:
                response = chat.send_message(prompt)
                return response.text
            except Exception as e:
                logger.error(f"Gemini retry {attempt}: {e}")
                await asyncio.sleep(2)
        return get_text(lang, 'error', error="Gemini failed")
    except Exception as e:
        logger.error(f"Error generate text: {e}")
        return get_text(lang, 'error', error=str(e)[:100])

async def process_file(file_bytes: bytes, filename: str, query: str = "", user_id: int = None) -> str:
    try:
        lang = get_user_language(user_id) if user_id else 'es'
        file_ext = Path(filename).suffix.lower()
        
        temp_path = f"/tmp/{filename}"
        with open(temp_path, 'wb') as f:
            f.write(file_bytes)
        
        text = ""
        if file_ext == '.pdf':
            text = extract_text_from_pdf(temp_path)
        elif file_ext in ['.docx', '.doc']:
            text = extract_text_from_docx(temp_path)
        elif file_ext == '.txt':
            text = file_bytes.decode('utf-8', errors='ignore')
        
        os.remove(temp_path)
        
        if not text or len(text) < 10:
            return get_text(lang, 'file_error', error="No text extracted")
        
        chat = get_chat_session(user_id, lang)
        prompt = f"ARCHIVO: {filename}\nCONTENIDO:\n{text[:2000]}\n\n{f'PREGUNTA: {query}' if query else ''}\n\nAnaliza y resume (máx 250 palabras)." if lang == 'es' else f"DATEI: {filename}\nINHALT:\n{text[:2000]}\n\n{f'FRAGE: {query}' if query else ''}\n\nAnalysiere und fasse zusammen (max 250 Wörter)."
        
        response = chat.send_message(prompt)
        return response.text
    except Exception as e:
        logger.error(f"Error process file: {e}")
        return get_text(lang, 'file_error', error=str(e)[:100])

# ============================================================================
# CHROMADB - RAG
# ============================================================================
chroma_client = chromadb.PersistentClient(path="./chroma_db")
try:
    collection = chroma_client.get_or_create_collection(name="pipila_documents")
    logger.info(f"✅ ChromaDB OK: {collection.count()} chunks")
except Exception as e:
    logger.error(f"❌ ChromaDB error: {e}")
    collection = None

def extract_text_from_pdf(file_path: str) -> str:
    try:
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            text = ""
            for page in pdf_reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
            return text
    except Exception as e:
        logger.error(f"PDF error {file_path}: {e}")
        return ""

def extract_text_from_docx(file_path: str) -> str:
    try:
        doc = docx.Document(file_path)
        text = "\n".join([p.text for p in doc.paragraphs if p.text])
        return text
    except Exception as e:
        logger.error(f"DOCX error {file_path}: {e}")
        return ""

def search_rag(query: str, n_results: int = 3) -> List[Dict]:
    """Search in ChromaDB RAG"""
    if not collection:
        return []
    try:
        results = collection.query(query_texts=[query], n_results=n_results)
        context_docs = []
        if results and results['documents'] and results['documents'][0]:
            for i, doc in enumerate(results['documents'][0]):
                metadata = results['metadatas'][0][i]
                context_docs.append({
                    'text': doc,
                    'source': metadata.get('source', 'Unknown'),
                    'chunk': metadata.get('chunk', 0)
                })
        return context_docs
    except Exception as e:
        logger.error(f"RAG search error: {e}")
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

class Query(Base):
    __tablename__ = 'queries'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger)
    query = Column(Text)
    response = Column(Text)
    timestamp = Column(DateTime, default=datetime.now)

engine = None
Session = None
if DATABASE_URL:
    try:
        engine = create_engine(DATABASE_URL, echo=False, pool_pre_ping=True)
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        logger.info("✅ PostgreSQL OK")
    except Exception as e:
        logger.warning(f"⚠️ DB error: {e}")
        engine = None

# ============================================================================
# STORAGE
# ============================================================================
class DataStorage:
    def __init__(self):
        self.users_file = 'users.json'
        if not engine:
            self.users = self.load_users()
        else:
            self.users = {}
    
    def load_users(self) -> Dict:
        try:
            if os.path.exists(self.users_file):
                with open(self.users_file, 'r') as f:
                    data = json.load(f)
                    return {int(k): v for k, v in data.items()} if isinstance(data, dict) else {}
            return {}
        except:
            return {}
    
    def save_users(self):
        if engine:
            return
        try:
            with open(self.users_file, 'w') as f:
                json.dump(self.users, f, indent=2)
        except:
            pass
    
    def get_user(self, user_id: int) -> Dict:
        if engine:
            session = Session()
            try:
                user = session.query(User).filter_by(id=user_id).first()
                if not user:
                    user = User(id=user_id)
                    session.add(user)
                    session.commit()
                    session.refresh(user)
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
                return {'id': user_id, 'is_team': False, 'language': 'es', 'query_count': 0}
            finally:
                session.close()
        else:
            if user_id not in self.users:
                self.users[user_id] = {'id': user_id, 'username': '', 'first_name': '', 'is_team': False, 'language': 'es', 'query_count': 0}
                self.save_users()
            return self.users[user_id]
    
    def update_user(self, user_id: int, data: Dict):
        if engine:
            session = Session()
            try:
                user = session.query(User).filter_by(id=user_id).first()
                if not user:
                    user = User(id=user_id)
                    session.add(user)
                for key, value in data.items():
                    setattr(user, key, value)
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
            self.save_users()
    
    def is_team_member(self, user_id: int) -> bool:
        if user_id == CREATOR_ID:
            return True
        user = self.get_user(user_id)
        return user.get('is_team', False)
    
    def save_query(self, user_id: int, query: str, response: str):
        if not engine:
            return
        session = Session()
        try:
            q = Query(user_id=user_id, query=query[:1000], response=response[:1000])
            session.add(q)
            session.commit()
        except:
            session.rollback()
        finally:
            session.close()
    
    def get_all_team_members(self) -> List[Dict]:
        if engine:
            session = Session()
            try:
                users = session.query(User).filter_by(is_team=True).all()
                return [{'id': u.id, 'username': u.username, 'first_name': u.first_name, 'query_count': u.query_count} for u in users]
            except:
                return []
            finally:
                session.close()
        else:
            return [u for u in self.users.values() if u.get('is_team', False)]

storage = DataStorage()

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

def get_main_keyboard(lang: str = 'es') -> ReplyKeyboardMarkup:
    kb = TRANSLATIONS[lang]['keyboard']
    keyboard = [
        [KeyboardButton(kb['consult']), KeyboardButton(kb['docs'])],
        [KeyboardButton(kb['stats']), KeyboardButton(kb['team'])],
        [KeyboardButton(kb['info']), KeyboardButton(kb['help'])]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# ============================================================================
# COMMANDS
# ============================================================================
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    identify_creator(user)
    user_data = storage.get_user(user.id)
    lang = user_data.get('language', 'es')
    storage.update_user(user.id, {'username': user.username or '', 'first_name': user.first_name or '', 'language': lang})
    text = get_text(lang, 'welcome', name=user.first_name, creator=CREATOR_USERNAME)
    await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=get_main_keyboard(lang))

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_language(user_id)
    text = get_text(lang, 'help')
    if is_creator(user_id):
        admin_text = "\n\n<b>⚙️ Admin:</b>\n/grant_team [ID o @username]" if lang == 'es' else "\n\n<b>⚙️ Admin:</b>\n/grant_team [ID oder @username]"
        text += admin_text
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)

async def lang_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    current_lang = get_user_language(user_id)
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🇪🇸 Español", callback_data="lang_es"), InlineKeyboardButton("🇩🇪 Deutsch", callback_data="lang_de")]])
    await update.message.reply_text(get_text(current_lang, 'choose_lang'), parse_mode=ParseMode.HTML, reply_markup=keyboard)

async def lang_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    new_lang = query.data.split('_')[1]
    set_user_language(user_id, new_lang)
    storage.update_user(user_id, {'language': new_lang})
    await query.edit_message_text(get_text(new_lang, 'lang_changed'), parse_mode=ParseMode.HTML)
    await query.message.reply_text("✅", reply_markup=get_main_keyboard(new_lang))

async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_language(user_id)
    if not context.args:
        await update.message.reply_text(get_text(lang, 'no_query'))
        return
    query = ' '.join(context.args)
    await update.message.chat.send_action("typing")
    try:
        context_docs = search_rag(query)
        response = await generate_text_response(query, user_id=user_id, context_docs=context_docs)
        storage.save_query(user_id, query, response)
        user = storage.get_user(user_id)
        storage.update_user(user_id, {'query_count': user.get('query_count', 0) + 1})
        search_label = "🔍 <b>Consulta:</b>" if lang == 'es' else "🔍 <b>Anfrage:</b>"
        await update.message.reply_text(f"{search_label} {query}\n\n{response}", parse_mode=ParseMode.HTML)
    except Exception as e:
        logger.error(f"Search error: {e}")
        await update.message.reply_text(get_text(lang, 'error', error=str(e)))

async def docs_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_language(user_id)
    count = collection.count() if collection else 0
    text = get_text(lang, 'docs', count=count)
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_language(user_id)
    user = storage.get_user(user_id)
    uptime = datetime.now() - BOT_START_TIME
    uptime_str = f"{uptime.days}d {uptime.seconds//3600}h"
    doc_count = collection.count() if collection else 0
    access = "✅ Equipo" if storage.is_team_member(user_id) else ("⏳ Sin acceso" if lang == 'es' else "⏳ Kein Zugang")
    db_type = "PostgreSQL" if engine else "JSON"
    text = get_text(lang, 'stats', name=user.get('first_name', 'N/A'), username=user.get('username', 'N/A'), access=access, queries=user.get('query_count', 0), docs=doc_count, uptime=uptime_str, db=db_type)
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)

async def team_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_language(user_id)
    if not storage.is_team_member(user_id):
        await update.message.reply_text(get_text(lang, 'team_only'))
        return
    team = storage.get_all_team_members()
    if not team:
        await update.message.reply_text("👥 No members yet." if lang == 'es' else "👥 Noch keine Mitglieder.")
        return
    members_text = ""
    for i, m in enumerate(team, 1):
        name = m.get('first_name', 'N/A')
        username = m.get('username', 'N/A')
        queries = m.get('query_count', 0)
        label = "Consultas:" if lang == 'es' else "Anfragen:"
        members_text += f"{i}. <b>{name}</b> (@{username})\n   {label} {queries}\n\n"
    text = get_text(lang, 'team', count=len(team), members=members_text)
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)

async def info_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_language(user_id)
    text = get_text(lang, 'info')
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)

# ============================================================================
# GRANT TEAM - SUPPORTS BOTH ID AND @USERNAME
# ============================================================================
async def grant_team_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Grant team access by ID or @username"""
    user_id = update.effective_user.id
    lang = get_user_language(user_id)
    
    if not is_creator(user_id):
        await update.message.reply_text(get_text(lang, 'admin_only'))
        return
    
    if not context.args:
        usage = """❓ <b>Uso:</b>
/grant_team [user_id]
/grant_team @username

<b>Ejemplos:</b>
<code>/grant_team 123456789</code>
<code>/grant_team @OscarCasco</code>""" if lang == 'es' else """❓ <b>Verwendung:</b>
/grant_team [user_id]
/grant_team @username

<b>Beispiele:</b>
<code>/grant_team 123456789</code>
<code>/grant_team @OscarCasco</code>"""
        await update.message.reply_text(usage, parse_mode=ParseMode.HTML)
        return
    
    target = context.args[0]
    
    # Check if it's a username (starts with @)
    if target.startswith('@'):
        username = target[1:]  # Remove @
        
        # Search for user in database by username
        if engine:
            session = Session()
            try:
                user = session.query(User).filter(User.username.ilike(username)).first()
                if user:
                    user.is_team = True
                    session.commit()
                    success_msg = f"✅ Usuario @{username} (ID: {user.id}) añadido al equipo!" if lang == 'es' else f"✅ Benutzer @{username} (ID: {user.id}) zum Team hinzugefügt!"
                    await update.message.reply_text(success_msg)
                else:
                    not_found = f"""⚠️ Usuario @{username} no encontrado en la base de datos.

<b>Opciones:</b>
1. Pide que el usuario envíe /start al bot primero
2. Usa su ID numérico: /grant_team [ID]

<i>Tip: Cuando el usuario escriba al bot, se registrará automáticamente.</i>""" if lang == 'es' else f"""⚠️ Benutzer @{username} nicht in der Datenbank gefunden.

<b>Optionen:</b>
1. Bitte den Benutzer zuerst /start an den Bot zu senden
2. Verwende seine numerische ID: /grant_team [ID]

<i>Tipp: Wenn der Benutzer dem Bot schreibt, wird er automatisch registriert.</i>"""
                    await update.message.reply_text(not_found, parse_mode=ParseMode.HTML)
            except Exception as e:
                session.rollback()
                logger.error(f"Grant team error: {e}")
                await update.message.reply_text(get_text(lang, 'error', error=str(e)[:100]))
            finally:
                session.close()
        else:
            # JSON storage - search in local users
            found = False
            for uid, udata in storage.users.items():
                if udata.get('username', '').lower() == username.lower():
                    storage.update_user(uid, {'is_team': True})
                    success_msg = f"✅ Usuario @{username} (ID: {uid}) añadido al equipo!" if lang == 'es' else f"✅ Benutzer @{username} (ID: {uid}) zum Team hinzugefügt!"
                    await update.message.reply_text(success_msg)
                    found = True
                    break
            
            if not found:
                not_found = f"⚠️ Usuario @{username} no encontrado. Pide que envíe /start primero." if lang == 'es' else f"⚠️ Benutzer @{username} nicht gefunden. Bitte ihn zuerst /start zu senden."
                await update.message.reply_text(not_found)
    else:
        # It's an ID
        try:
            target_id = int(target)
            storage.update_user(target_id, {'is_team': True})
            await update.message.reply_text(get_text(lang, 'user_added', id=target_id))
        except ValueError:
            invalid = "❌ ID inválido. Usa número o @username" if lang == 'es' else "❌ Ungültige ID. Verwende Nummer oder @username"
            await update.message.reply_text(invalid)

async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_language(user_id)
    clear_chat_session(user_id)
    await update.message.reply_text(get_text(lang, 'cleared'))

# ============================================================================
# MESSAGE HANDLERS
# ============================================================================
async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    identify_creator(user)
    user_id = user.id
    lang = get_user_language(user_id)
    storage.update_user(user_id, {'username': user.username or '', 'first_name': user.first_name or ''})
    document = update.message.document
    filename = document.file_name
    file_ext = Path(filename).suffix.lower()
    if file_ext not in ['.pdf', '.docx', '.doc', '.txt']:
        unsupported = "⚠️ Tipo no soportado. Envía PDF, DOCX, TXT" if lang == 'es' else "⚠️ Dateityp nicht unterstützt. Sende PDF, DOCX, TXT"
        await update.message.reply_text(unsupported)
        return
    caption = update.message.caption or ""
    await update.message.chat.send_action("typing")
    await update.message.reply_text(get_text(lang, 'processing_file'))
    try:
        file = await context.bot.get_file(document.file_id)
        file_bytes = await file.download_as_bytearray()
        response = await process_file(bytes(file_bytes), filename, query=caption, user_id=user_id)
        storage.save_query(user_id, f"[FILE: {filename}] {caption}", response)
        user_data = storage.get_user(user_id)
        storage.update_user(user_id, {'query_count': user_data.get('query_count', 0) + 1})
        result_text = get_text(lang, 'file_processed', filename=filename, response=response)
        await update.message.reply_text(result_text, parse_mode=ParseMode.HTML)
    except Exception as e:
        logger.error(f"Document error: {e}")
        await update.message.reply_text(get_text(lang, 'file_error', error=str(e)[:100]))

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    identify_creator(user)
    user_id = user.id
    text = update.message.text
    user_data = storage.get_user(user_id)
    current_lang = user_data.get('language', 'es')
    detected_lang = detect_language(text)
    if detected_lang != current_lang:
        set_user_language(user_id, detected_lang)
        storage.update_user(user_id, {'language': detected_lang})
        current_lang = detected_lang
    storage.update_user(user_id, {'username': user.username or '', 'first_name': user.first_name or ''})
    kb = TRANSLATIONS[current_lang]['keyboard']
    if text == kb['consult']:
        await update.message.reply_text(get_text(current_lang, 'ask_question'))
        return
    elif text == kb['docs']:
        await docs_command(update, context)
        return
    elif text == kb['stats']:
        await stats_command(update, context)
        return
    elif text == kb['team']:
        await team_command(update, context)
        return
    elif text == kb['info']:
        await info_command(update, context)
        return
    elif text == kb['help']:
        await help_command(update, context)
        return
    if text and not text.startswith('/'):
        await update.message.chat.send_action("typing")
        try:
            context_docs = search_rag(text)
            response = await generate_text_response(text, user_id=user_id, context_docs=context_docs)
            storage.save_query(user_id, text, response)
            user = storage.get_user(user_id)
            storage.update_user(user_id, {'query_count': user.get('query_count', 0) + 1})
            await update.message.reply_text(response, parse_mode=ParseMode.HTML)
        except Exception as e:
            logger.error(f"Message error: {e}")
            await update.message.reply_text(get_text(current_lang, 'error', error=str(e)))

# ============================================================================
# MAIN
# ============================================================================
def main():
    """Main function"""
    logger.info("=" * 60)
    logger.info("🚀 PIPILA v8.3 - Grant by Username")
    logger.info("=" * 60)
    
    # Check ChromaDB
    chunks = collection.count() if collection else 0
    if chunks > 0:
        logger.info(f"✅ Using pre-processed ChromaDB: {chunks} chunks")
    else:
        logger.warning("⚠️ ChromaDB empty - no documents available")
    
    # Build application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("lang", lang_command))
    application.add_handler(CallbackQueryHandler(lang_callback, pattern="^lang_"))
    application.add_handler(CommandHandler("search", search_command))
    application.add_handler(CommandHandler("docs", docs_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("team", team_command))
    application.add_handler(CommandHandler("info", info_command))
    application.add_handler(CommandHandler("grant_team", grant_team_command))
    application.add_handler(CommandHandler("clear", clear_command))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logger.info("=" * 60)
    logger.info("✅ PIPILA started successfully")
    logger.info(f"🤖 AI: Gemini 2.5 Flash")
    logger.info(f"📊 Chunks: {chunks}")
    logger.info(f"🗄️ DB: {'PostgreSQL' if engine else 'JSON'}")
    logger.info(f"🌍 Languages: ES, DE")
    logger.info("=" * 60)
    
    # Start bot
    application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

if __name__ == '__main__':
    main()
