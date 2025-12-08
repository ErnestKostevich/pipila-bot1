#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🤖 PIPILA v9.0 PRO
Professional Financial Assistant for Oscar Casco Team
✅ Streamlined interface for consultants
✅ Quick access to products and client categories
✅ Gemini 2.5 Flash AI + RAG
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
# CONFIGURATION
# ============================================================================
BOT_TOKEN = os.getenv('BOT_TOKEN')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
DATABASE_URL = os.getenv('DATABASE_URL')
CHROMA_PATH = "./chroma_db"
CREATOR_USERNAME = "Ernest_Kostevich"
CREATOR_ID = None
BOT_VERSION = "9.0 PRO"
BOT_START_TIME = datetime.now()

logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

if not BOT_TOKEN or not GEMINI_API_KEY:
    logger.error("❌ Missing BOT_TOKEN or GEMINI_API_KEY")
    sys.exit(1)

# ============================================================================
# PROFESSIONAL TRANSLATIONS (ES/DE)
# ============================================================================
TRANSLATIONS = {
    'es': {
        'welcome': """👋 Hola <b>{name}</b>

Soy tu asistente del <b>equipo Oscar Casco</b>.

Tengo acceso a toda la información sobre:
• DVAG
• Generali  
• Badenia
• Advocard

Usa el menú ⬇️ o escribe tu consulta directamente.""",

        'main_menu_msg': "📱 <b>Menú Principal</b>\n\nSelecciona una opción:",
        
        # Product quick access
        'product_dvag': """<b>🏢 DVAG</b>

Información disponible:
• Estructura y funcionamiento
• Productos financieros
• Plan de carrera
• Comisiones

¿Qué necesitas saber?""",

        'product_generali': """<b>🛡️ GENERALI</b>

Seguros disponibles:
• Vida
• Salud
• Hogar
• Auto
• Responsabilidad civil

¿Qué seguro consultas?""",

        'product_badenia': """<b>🏠 BADENIA</b>

Bausparkasse:
• Plan de ahorro vivienda
• Préstamos hipotecarios
• Condiciones y ventajas

¿Qué información necesitas?""",

        'product_advocard': """<b>⚖️ ADVOCARD</b>

Protección jurídica:
• Cobertura laboral
• Tráfico
• Vivienda
• Privado

¿Sobre qué área consultas?""",

        # Client categories
        'client_familia': """<b>👨‍👩‍👧 FAMILIAS</b>

Productos recomendados:
• Seguro de vida
• Seguro de salud
• Plan de ahorro
• Protección del hogar

¿Qué caso tienes?""",

        'client_autonomo': """<b>💼 AUTÓNOMOS</b>

Soluciones para autónomos:
• Seguro de responsabilidad
• Protección de ingresos
• Jubilación privada
• Seguro de salud

¿Qué necesita tu cliente?""",

        'client_empresa': """<b>🏭 EMPRESARIOS</b>

Para empresas:
• Seguro de responsabilidad civil
• Protección de empleados
• Planes de pensiones
• Seguros de negocio

¿Qué consultas?""",

        # Templates
        'templates_msg': """<b>📋 CONSULTAS FRECUENTES</b>

Ejemplos de preguntas útiles:

<b>Comisiones:</b>
"¿Cuánto se cobra por un seguro de vida?"

<b>Comparativas:</b>
"Diferencias entre seguros de salud"

<b>Requisitos:</b>
"¿Qué documentos necesita un cliente nuevo?"

<b>Procesos:</b>
"¿Cómo se tramita una póliza Generali?"

Puedes copiar y adaptar estas preguntas.""",

        # System
        'thinking': '⏳ Consultando...',
        'error': '❌ Error: {error}',
        'cleared': '✅ Conversación reiniciada',
        'file_processed': '<b>📄 {filename}</b>\n\n{response}',
        'file_error': '❌ Error al procesar archivo',
        'admin_only': '🔒 Solo administradores',
        'user_added': '✅ Usuario {id} añadido al equipo',
        'no_access': '🔒 Solo para el equipo de Oscar.\nContacta al administrador.',
        
        # Keyboard
        'keyboard': {
            'products': '🏢 Productos',
            'clients': '👥 Clientes',
            'templates': '📋 Consultas',
            'team': '👔 Equipo',
            'lang': '🌍 Idioma',
            'reset': '🔄 Reiniciar'
        },
        'products_keyboard': {
            'dvag': 'DVAG',
            'generali': 'Generali',
            'badenia': 'Badenia',
            'advocard': 'Advocard',
            'back': '◀️ Atrás'
        },
        'clients_keyboard': {
            'familia': '👨‍👩‍👧 Familias',
            'autonomo': '💼 Autónomos',
            'empresa': '🏭 Empresarios',
            'back': '◀️ Atrás'
        }
    },
    'de': {
        'welcome': """👋 Hallo <b>{name}</b>

Ich bin dein Assistent vom <b>Team Oscar Casco</b>.

Ich habe Zugriff auf alle Informationen über:
• DVAG
• Generali  
• Badenia
• Advocard

Nutze das Menü ⬇️ oder stelle direkt deine Frage.""",

        'main_menu_msg': "📱 <b>Hauptmenü</b>\n\nWähle eine Option:",
        
        'product_dvag': """<b>🏢 DVAG</b>

Verfügbare Informationen:
• Struktur und Funktionsweise
• Finanzprodukte
• Karriereplan
• Provisionen

Was möchtest du wissen?""",

        'product_generali': """<b>🛡️ GENERALI</b>

Verfügbare Versicherungen:
• Leben
• Gesundheit
• Haus
• Auto
• Haftpflicht

Welche Versicherung?""",

        'product_badenia': """<b>🏠 BADENIA</b>

Bausparkasse:
• Bausparplan
• Hypothekendarlehen
• Bedingungen und Vorteile

Welche Information brauchst du?""",

        'product_advocard': """<b>⚖️ ADVOCARD</b>

Rechtsschutz:
• Arbeitsrecht
• Verkehr
• Wohnen
• Privat

Über welchen Bereich?""",

        'client_familia': """<b>👨‍👩‍👧 FAMILIEN</b>

Empfohlene Produkte:
• Lebensversicherung
• Krankenversicherung
• Sparplan
• Hausschutz

Welcher Fall?""",

        'client_autonomo': """<b>💼 SELBSTÄNDIGE</b>

Lösungen für Selbständige:
• Haftpflichtversicherung
• Einkommensschutz
• Private Altersvorsorge
• Krankenversicherung

Was braucht dein Kunde?""",

        'client_empresa': """<b>🏭 UNTERNEHMER</b>

Für Unternehmen:
• Betriebshaftpflicht
• Mitarbeiterschutz
• Pensionspläne
• Betriebsversicherungen

Was möchtest du wissen?""",

        'templates_msg': """<b>📋 HÄUFIGE ANFRAGEN</b>

Beispiele nützlicher Fragen:

<b>Provisionen:</b>
"Wie viel verdient man mit Lebensversicherung?"

<b>Vergleiche:</b>
"Unterschiede zwischen Krankenversicherungen"

<b>Anforderungen:</b>
"Welche Dokumente braucht ein Neukunde?"

<b>Prozesse:</b>
"Wie bearbeitet man eine Generali Police?"

Du kannst diese Fragen kopieren und anpassen.""",

        'thinking': '⏳ Suche...',
        'error': '❌ Fehler: {error}',
        'cleared': '✅ Gespräch neu gestartet',
        'file_processed': '<b>📄 {filename}</b>\n\n{response}',
        'file_error': '❌ Fehler beim Verarbeiten',
        'admin_only': '🔒 Nur für Administratoren',
        'user_added': '✅ Benutzer {id} zum Team hinzugefügt',
        'no_access': '🔒 Nur für Oscar Team.\nKontaktiere den Administrator.',
        
        'keyboard': {
            'products': '🏢 Produkte',
            'clients': '👥 Kunden',
            'templates': '📋 Anfragen',
            'team': '👔 Team',
            'lang': '🌍 Sprache',
            'reset': '🔄 Reset'
        },
        'products_keyboard': {
            'dvag': 'DVAG',
            'generali': 'Generali',
            'badenia': 'Badenia',
            'advocard': 'Advocard',
            'back': '◀️ Zurück'
        },
        'clients_keyboard': {
            'familia': '👨‍👩‍👧 Familien',
            'autonomo': '💼 Selbständige',
            'empresa': '🏭 Unternehmer',
            'back': '◀️ Zurück'
        }
    }
}

def get_text(lang: str, key: str, **kwargs) -> str:
    text = TRANSLATIONS.get(lang, TRANSLATIONS['es']).get(key, key)
    return text.format(**kwargs) if kwargs else text

def detect_language(text: str) -> str:
    text_lower = text.lower()
    de_words = ['was', 'wie', 'wo', 'wann', 'warum', 'ist', 'sind', 'haben']
    es_words = ['qué', 'cómo', 'dónde', 'cuándo', 'por qué', 'es', 'son']
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
    'es': """Eres PIPILA, asistente del equipo de Oscar Casco.

INSTRUCCIONES:
- Responde en español, profesional y directo
- Máximo 200 palabras
- Cita documentos cuando disponibles
- Si no sabes algo, dilo claramente
- Usa formato claro, sin emojis excesivos

CONOCIMIENTO:
- DVAG: productos financieros, estructura, carrera
- Generali: seguros vida, salud, hogar, auto
- Badenia: ahorro vivienda
- Advocard: protección jurídica

Sé práctico y útil.""",

    'de': """Du bist PIPILA, Assistent des Teams von Oscar Casco.

ANWEISUNGEN:
- Antworte auf Deutsch, professionell und direkt
- Maximal 200 Wörter
- Zitiere Dokumente wenn verfügbar
- Wenn du etwas nicht weißt, sag es klar
- Klares Format, keine übermäßigen Emojis

WISSEN:
- DVAG: Finanzprodukte, Struktur, Karriere
- Generali: Lebens-, Kranken-, Haus-, Autoversicherung
- Badenia: Bausparen
- Advocard: Rechtsschutz

Sei praktisch und hilfreich."""
}

model_text = genai.GenerativeModel(
    model_name='gemini-2.5-flash',
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
# AI RESPONSE
# ============================================================================
async def generate_response(query: str, user_id: int = None, context_docs: List[Dict] = None) -> str:
    try:
        lang = get_user_language(user_id) if user_id else 'es'
        chat = get_chat_session(user_id, lang) if user_id else model_text.start_chat(history=[])
        
        if context_docs:
            context_text = "\n\n".join([
                f"[{doc['source']}]: {doc['text'][:500]}" 
                for doc in context_docs
            ])
            prompt = f"""DOCUMENTOS:\n{context_text}\n\nPREGUNTA: {query}\n\nResponde basándote en los documentos."""
        else:
            prompt = query
        
        for attempt in range(3):
            try:
                response = chat.send_message(prompt)
                return response.text
            except Exception as e:
                logger.error(f"Gemini error: {e}")
                await asyncio.sleep(1)
        
        return get_text(lang, 'error', error="AI no disponible")
        
    except Exception as e:
        logger.error(f"Response error: {e}")
        lang = get_user_language(user_id) if user_id else 'es'
        return get_text(lang, 'error', error=str(e)[:30])

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
            return get_text(lang, 'file_error')
        
        chat = get_chat_session(user_id, lang)
        prompt = f"DOCUMENTO: {filename}\n\n{text[:3000]}\n\n{query if query else 'Resume el contenido.'}"
        
        response = chat.send_message(prompt)
        return response.text
        
    except Exception as e:
        logger.error(f"File error: {e}")
        lang = get_user_language(user_id) if user_id else 'es'
        return get_text(lang, 'file_error')

# ============================================================================
# CHROMADB
# ============================================================================
chroma_client = None
collection = None

try:
    chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
    collection = chroma_client.get_or_create_collection(name="pipila_documents")
    logger.info(f"✅ ChromaDB: {collection.count()} chunks")
except Exception as e:
    logger.warning(f"⚠️ ChromaDB: {e}")

def extract_text_from_pdf(file_path: str) -> str:
    try:
        with open(file_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            return "".join([p.extract_text() for p in reader.pages if p.extract_text()])
    except:
        return ""

def extract_text_from_docx(file_path: str) -> str:
    try:
        doc = docx.Document(file_path)
        return "\n".join([p.text for p in doc.paragraphs if p.text])
    except:
        return ""

def search_knowledge(query: str, n_results: int = 5) -> List[Dict]:
    if not collection:
        return []
    try:
        results = collection.query(query_texts=[query], n_results=n_results)
        docs = []
        if results and results['documents'] and results['documents'][0]:
            for i, doc in enumerate(results['documents'][0]):
                metadata = results['metadatas'][0][i]
                docs.append({
                    'text': doc,
                    'source': metadata.get('source', 'Unknown'),
                    'chunk': metadata.get('chunk', 0)
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
        logger.info("✅ PostgreSQL connected")
    except Exception as e:
        logger.warning(f"⚠️ Database: {e}")
        engine = None

# ============================================================================
# DATA STORAGE
# ============================================================================
class DataStorage:
    def __init__(self):
        self.users_file = 'users.json'
        self.users = {} if engine else self._load_users()
    
    def _load_users(self) -> Dict:
        try:
            if os.path.exists(self.users_file):
                with open(self.users_file, 'r') as f:
                    data = json.load(f)
                    return {int(k): v for k, v in data.items()}
            return {}
        except:
            return {}
    
    def _save_users(self):
        if not engine:
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
                self.users[user_id] = {
                    'id': user_id, 'username': '', 'first_name': '',
                    'is_team': False, 'language': 'es', 'query_count': 0
                }
                self._save_users()
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
            self._save_users()
    
    def is_team_member(self, user_id: int) -> bool:
        if user_id == CREATOR_ID:
            return True
        return self.get_user(user_id).get('is_team', False)
    
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
    
    def get_team_members(self) -> List[Dict]:
        if engine:
            session = Session()
            try:
                users = session.query(User).filter_by(is_team=True).all()
                return [{
                    'id': u.id, 'username': u.username,
                    'first_name': u.first_name, 'query_count': u.query_count
                } for u in users]
            except:
                return []
            finally:
                session.close()
        else:
            return [u for u in self.users.values() if u.get('is_team')]

storage = DataStorage()

# ============================================================================
# KEYBOARDS
# ============================================================================
def get_main_keyboard(lang: str = 'es') -> ReplyKeyboardMarkup:
    kb = TRANSLATIONS[lang]['keyboard']
    keyboard = [
        [KeyboardButton(kb['products']), KeyboardButton(kb['clients'])],
        [KeyboardButton(kb['templates']), KeyboardButton(kb['team'])],
        [KeyboardButton(kb['lang']), KeyboardButton(kb['reset'])]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_products_keyboard(lang: str = 'es') -> ReplyKeyboardMarkup:
    kb = TRANSLATIONS[lang]['products_keyboard']
    keyboard = [
        [KeyboardButton(kb['dvag']), KeyboardButton(kb['generali'])],
        [KeyboardButton(kb['badenia']), KeyboardButton(kb['advocard'])],
        [KeyboardButton(kb['back'])]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_clients_keyboard(lang: str = 'es') -> ReplyKeyboardMarkup:
    kb = TRANSLATIONS[lang]['clients_keyboard']
    keyboard = [
        [KeyboardButton(kb['familia'])],
        [KeyboardButton(kb['autonomo'])],
        [KeyboardButton(kb['empresa'])],
        [KeyboardButton(kb['back'])]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# ============================================================================
# HELPERS
# ============================================================================
def identify_creator(user):
    global CREATOR_ID
    if user.username == CREATOR_USERNAME and CREATOR_ID is None:
        CREATOR_ID = user.id
        logger.info(f"✅ Creator: @{user.username} ({user.id})")

def is_creator(user_id: int) -> bool:
    return user_id == CREATOR_ID

# ============================================================================
# COMMAND HANDLERS
# ============================================================================
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    identify_creator(user)
    
    user_data = storage.get_user(user.id)
    lang = user_data.get('language', 'es')
    
    storage.update_user(user.id, {
        'username': user.username or '',
        'first_name': user.first_name or '',
        'language': lang
    })
    
    text = get_text(lang, 'welcome', name=user.first_name or 'Usuario')
    await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=get_main_keyboard(lang))

async def cmd_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command for user management only"""
    user_id = update.effective_user.id
    lang = get_user_language(user_id)
    
    if not is_creator(user_id):
        await update.message.reply_text(get_text(lang, 'admin_only'))
        return
    
    if not context.args:
        usage = """<b>⚙️ COMANDOS DE ADMINISTRACIÓN</b>

<b>Gestión de usuarios:</b>
/admin add [user_id] - Añadir por ID
/admin add @username - Añadir por username

<b>Información del sistema:</b>
/docs - Estadísticas base de datos
/stats - Estadísticas detalladas equipo

<b>Ejemplos:</b>
<code>/admin add 123456789</code>
<code>/admin add @OscarCasco</code>""" if lang == 'es' else """<b>⚙️ ADMINISTRATORBEFEHLE</b>

<b>Benutzerverwaltung:</b>
/admin add [user_id] - Per ID hinzufügen
/admin add @username - Per Username hinzufügen

<b>Systeminformation:</b>
/docs - Datenbankstatistiken
/stats - Detaillierte Team-Statistiken

<b>Beispiele:</b>
<code>/admin add 123456789</code>
<code>/admin add @OscarCasco</code>"""
        await update.message.reply_text(usage, parse_mode=ParseMode.HTML)
        return
    
    cmd = context.args[0].lower()
    
    if cmd == 'add' and len(context.args) > 1:
        target = context.args[1]
        if target.startswith('@'):
            username = target[1:]
            if engine:
                session = Session()
                try:
                    user = session.query(User).filter(User.username.ilike(username)).first()
                    if user:
                        user.is_team = True
                        session.commit()
                        msg = f"✅ @{username} añadido al equipo" if lang == 'es' else f"✅ @{username} zum Team hinzugefügt"
                        await update.message.reply_text(msg)
                    else:
                        msg = f"⚠️ @{username} no encontrado. Debe usar /start primero." if lang == 'es' else f"⚠️ @{username} nicht gefunden. Muss /start verwenden."
                        await update.message.reply_text(msg)
                finally:
                    session.close()
            else:
                found = False
                for uid, udata in storage.users.items():
                    if udata.get('username', '').lower() == username.lower():
                        storage.update_user(uid, {'is_team': True})
                        msg = f"✅ @{username} añadido al equipo" if lang == 'es' else f"✅ @{username} zum Team hinzugefügt"
                        await update.message.reply_text(msg)
                        found = True
                        break
                if not found:
                    msg = f"⚠️ @{username} no encontrado" if lang == 'es' else f"⚠️ @{username} nicht gefunden"
                    await update.message.reply_text(msg)
        else:
            try:
                target_id = int(target)
                storage.update_user(target_id, {'is_team': True})
                await update.message.reply_text(get_text(lang, 'user_added', id=target_id), parse_mode=ParseMode.HTML)
            except ValueError:
                msg = "❌ ID inválido" if lang == 'es' else "❌ Ungültige ID"
                await update.message.reply_text(msg)

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Help command - available for all team members"""
    user_id = update.effective_user.id
    lang = get_user_language(user_id)
    
    if not storage.is_team_member(user_id):
        await update.message.reply_text(get_text(lang, 'no_access'))
        return
    
    if lang == 'es':
        help_text = """<b>📖 COMANDOS DISPONIBLES</b>

<b>Básicos:</b>
/start - Reiniciar bot
/help - Esta ayuda
/lang - Cambiar idioma
/reset - Limpiar conversación

<b>Información:</b>
/team - Ver miembros del equipo

<b>💡 USO DEL BOT:</b>

<b>1. Menú principal:</b>
Usa los botones para navegar:
• 🏢 Productos - DVAG, Generali, Badenia, Advocard
• 👥 Clientes - Familias, Autónomos, Empresarios
• 📋 Consultas - Ejemplos de preguntas
• 👔 Equipo - Ver miembros
• 🌍 Idioma - Cambiar ES/DE
• 🔄 Reiniciar - Limpiar chat

<b>2. Preguntas directas:</b>
Escribe tu pregunta directamente:
"¿Cuánto cuesta seguro de vida?"
"¿Qué documentos necesita cliente nuevo?"
"Diferencias entre seguros Generali"

<b>3. Enviar documentos:</b>
Envía PDF/DOCX/TXT y añade pregunta como caption.

El bot buscará en la base de conocimiento (19,000+ fragmentos) y responderá con fuentes."""
    else:
        help_text = """<b>📖 VERFÜGBARE BEFEHLE</b>

<b>Grundlegend:</b>
/start - Bot neu starten
/help - Diese Hilfe
/lang - Sprache ändern
/reset - Gespräch löschen

<b>Information:</b>
/team - Teammitglieder ansehen

<b>💡 BOT-NUTZUNG:</b>

<b>1. Hauptmenü:</b>
Nutze die Buttons zur Navigation:
• 🏢 Produkte - DVAG, Generali, Badenia, Advocard
• 👥 Kunden - Familien, Selbständige, Unternehmer
• 📋 Anfragen - Beispielfragen
• 👔 Team - Mitglieder ansehen
• 🌍 Sprache - ES/DE wechseln
• 🔄 Reset - Chat löschen

<b>2. Direkte Fragen:</b>
Stelle deine Frage direkt:
"Wie viel kostet Lebensversicherung?"
"Welche Dokumente braucht Neukunde?"
"Unterschiede zwischen Generali Versicherungen"

<b>3. Dokumente senden:</b>
Sende PDF/DOCX/TXT mit Frage als Caption.

Der Bot sucht in der Wissensbasis (19.000+ Fragmente) und antwortet mit Quellen."""
    
    if is_creator(user_id):
        admin_text = """

<b>⚙️ ADMIN:</b>
/admin add [ID/@user] - Usuario al equipo
/admin stats - Estadísticas del bot
/docs - Estadísticas base de datos
/stats - Estadísticas detalladas""" if lang == 'es' else """

<b>⚙️ ADMIN:</b>
/admin add [ID/@user] - Benutzer zum Team
/admin stats - Bot-Statistiken
/docs - Datenbankstatistiken
/stats - Detaillierte Statistiken"""
        help_text += admin_text
    
    await update.message.reply_text(help_text, parse_mode=ParseMode.HTML)

async def cmd_docs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Docs command - available only for admin"""
    user_id = update.effective_user.id
    lang = get_user_language(user_id)
    
    if not is_creator(user_id):
        await update.message.reply_text(get_text(lang, 'admin_only'))
        return
    
    count = collection.count() if collection else 0
    
    if lang == 'es':
        docs_text = f"""<b>📚 BASE DE CONOCIMIENTO</b>

<b>Estadísticas:</b>
• Fragmentos indexados: <b>{count:,}</b>
• Estado: {'✅ Activa' if count > 0 else '❌ Vacía'}
• Sistema: ChromaDB + RAG

<b>Categorías disponibles:</b>
🏢 DVAG - Productos financieros
🛡️ Generali - Seguros completos
🏠 Badenia - Ahorro vivienda
⚖️ Advocard - Protección jurídica

Los consultores pueden hacer preguntas y el bot buscará automáticamente en estos documentos."""
    else:
        docs_text = f"""<b>📚 WISSENSBASIS</b>

<b>Statistiken:</b>
• Indexierte Fragmente: <b>{count:,}</b>
• Status: {'✅ Aktiv' if count > 0 else '❌ Leer'}
• System: ChromaDB + RAG

<b>Verfügbare Kategorien:</b>
🏢 DVAG - Finanzprodukte
🛡️ Generali - Komplette Versicherungen
🏠 Badenia - Bausparen
⚖️ Advocard - Rechtsschutz

Berater können Fragen stellen und der Bot sucht automatisch in diesen Dokumenten."""
    
    await update.message.reply_text(docs_text, parse_mode=ParseMode.HTML)

async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Stats command - available only for admin"""
    user_id = update.effective_user.id
    lang = get_user_language(user_id)
    
    if not is_creator(user_id):
        await update.message.reply_text(get_text(lang, 'admin_only'))
        return
    
    team = storage.get_team_members()
    uptime = datetime.now() - BOT_START_TIME
    total_queries = sum(m.get('query_count', 0) for m in team)
    doc_count = collection.count() if collection else 0
    
    if lang == 'es':
        stats_text = f"""<b>📊 ESTADÍSTICAS DETALLADAS</b>

<b>Sistema:</b>
• Versión: {BOT_VERSION}
• Uptime: {uptime.days}d {uptime.seconds//3600}h {(uptime.seconds%3600)//60}m
• Base de datos: {'PostgreSQL ✅' if engine else 'JSON (local)'}
• AI: Gemini 2.5 Flash ✅

<b>Base de conocimiento:</b>
• Chunks: {doc_count:,}
• Sistema: ChromaDB + RAG
• Estado: {'✅ Activa' if doc_count > 0 else '❌ Vacía'}

<b>Equipo:</b>
• Miembros: {len(team)}
• Consultas totales: {total_queries:,}
• Promedio: {(total_queries / len(team) if team else 0):.1f} por miembro

<b>Top usuarios:</b>"""
        
        sorted_team = sorted(team, key=lambda x: x.get('query_count', 0), reverse=True)[:5]
        for i, m in enumerate(sorted_team, 1):
            stats_text += f"\n{i}. {m['first_name']} - {m.get('query_count', 0)} consultas"
    else:
        stats_text = f"""<b>📊 DETAILLIERTE STATISTIKEN</b>

<b>System:</b>
• Version: {BOT_VERSION}
• Uptime: {uptime.days}d {uptime.seconds//3600}h {(uptime.seconds%3600)//60}m
• Datenbank: {'PostgreSQL ✅' if engine else 'JSON (lokal)'}
• AI: Gemini 2.5 Flash ✅

<b>Wissensbasis:</b>
• Chunks: {doc_count:,}
• System: ChromaDB + RAG
• Status: {'✅ Aktiv' if doc_count > 0 else '❌ Leer'}

<b>Team:</b>
• Mitglieder: {len(team)}
• Gesamtanfragen: {total_queries:,}
• Durchschnitt: {(total_queries / len(team) if team else 0):.1f} pro Mitglied

<b>Top Benutzer:</b>"""
        
        sorted_team = sorted(team, key=lambda x: x.get('query_count', 0), reverse=True)[:5]
        for i, m in enumerate(sorted_team, 1):
            stats_text += f"\n{i}. {m['first_name']} - {m.get('query_count', 0)} Anfragen"
    
    await update.message.reply_text(stats_text, parse_mode=ParseMode.HTML)

async def cmd_team(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Team command - available for all team members"""
    user_id = update.effective_user.id
    lang = get_user_language(user_id)
    
    if not storage.is_team_member(user_id):
        await update.message.reply_text(get_text(lang, 'no_access'))
        return
    
    team = storage.get_team_members()
    
    if not team:
        no_members = "👥 Aún no hay miembros en el equipo." if lang == 'es' else "👥 Noch keine Teammitglieder."
        await update.message.reply_text(no_members)
        return
    
    if lang == 'es':
        members_text = f"<b>👔 EQUIPO OSCAR CASCO</b> ({len(team)} miembros)\n\n"
        for i, m in enumerate(team, 1):
            name = m.get('first_name', 'N/A')
            username = m.get('username', 'N/A')
            queries = m.get('query_count', 0)
            members_text += f"{i}. <b>{name}</b> (@{username})\n   📊 {queries} consultas\n\n"
    else:
        members_text = f"<b>👔 TEAM OSCAR CASCO</b> ({len(team)} Mitglieder)\n\n"
        for i, m in enumerate(team, 1):
            name = m.get('first_name', 'N/A')
            username = m.get('username', 'N/A')
            queries = m.get('query_count', 0)
            members_text += f"{i}. <b>{name}</b> (@{username})\n   📊 {queries} Anfragen\n\n"
    
    await update.message.reply_text(members_text, parse_mode=ParseMode.HTML)

async def cmd_lang(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Language selection for all team members"""
    user_id = update.effective_user.id
    lang = get_user_language(user_id)
    
    if not storage.is_team_member(user_id):
        await update.message.reply_text(get_text(lang, 'no_access'))
        return
    
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🇪🇸 Español", callback_data="lang_es"),
            InlineKeyboardButton("🇩🇪 Deutsch", callback_data="lang_de")
        ]
    ])
    
    current = "Español" if lang == 'es' else "Deutsch"
    await update.message.reply_text(
        f"<b>🌍 Idioma / Sprache</b>\n\nActual: {current}\n\nSelecciona:",
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard
    )

async def callback_lang(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle language selection callback"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    new_lang = query.data.split('_')[1]
    
    set_user_language(user_id, new_lang)
    storage.update_user(user_id, {'language': new_lang})
    
    lang_name = "Español 🇪🇸" if new_lang == 'es' else "Deutsch 🇩🇪"
    await query.edit_message_text(
        f"✅ Idioma cambiado / Sprache geändert: <b>{lang_name}</b>",
        parse_mode=ParseMode.HTML
    )
    
    # Send new keyboard in selected language
    await query.message.reply_text("👍", reply_markup=get_main_keyboard(new_lang))

async def cmd_reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    
    if not storage.is_team_member(user_id):
        await update.message.reply_text(get_text(lang, 'no_access'))
        return
    
    document = update.message.document
    filename = document.file_name
    file_ext = Path(filename).suffix.lower()
    
    if file_ext not in ['.pdf', '.docx', '.doc', '.txt']:
        await update.message.reply_text("⚠️ Solo PDF, DOCX o TXT")
        return
    
    caption = update.message.caption or ""
    await update.message.chat.send_action("typing")
    processing_msg = await update.message.reply_text(get_text(lang, 'thinking'))
    
    try:
        file = await context.bot.get_file(document.file_id)
        file_bytes = await file.download_as_bytearray()
        response = await process_file(bytes(file_bytes), filename, query=caption, user_id=user_id)
        
        storage.save_query(user_id, f"[FILE: {filename}] {caption}", response)
        user_data = storage.get_user(user_id)
        storage.update_user(user_id, {'query_count': user_data.get('query_count', 0) + 1})
        
        await processing_msg.delete()
        await update.message.reply_text(
            get_text(lang, 'file_processed', filename=filename, response=response),
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        await processing_msg.delete()
        logger.error(f"Document error: {e}")
        await update.message.reply_text(get_text(lang, 'file_error'))

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    identify_creator(user)
    user_id = user.id
    text = update.message.text
    
    user_data = storage.get_user(user_id)
    current_lang = user_data.get('language', 'es')
    
    if not storage.is_team_member(user_id):
        await update.message.reply_text(get_text(current_lang, 'no_access'))
        return
    
    # Auto-detect language
    detected_lang = detect_language(text)
    if detected_lang != current_lang and len(text) > 15:
        set_user_language(user_id, detected_lang)
        storage.update_user(user_id, {'language': detected_lang})
        current_lang = detected_lang
    
    # Handle keyboard buttons
    kb_main = TRANSLATIONS[current_lang]['keyboard']
    kb_products = TRANSLATIONS[current_lang]['products_keyboard']
    kb_clients = TRANSLATIONS[current_lang]['clients_keyboard']
    
    # Main menu
    if text == kb_main['products']:
        await update.message.reply_text(
            get_text(current_lang, 'main_menu_msg'),
            parse_mode=ParseMode.HTML,
            reply_markup=get_products_keyboard(current_lang)
        )
        return
    elif text == kb_main['clients']:
        await update.message.reply_text(
            get_text(current_lang, 'main_menu_msg'),
            parse_mode=ParseMode.HTML,
            reply_markup=get_clients_keyboard(current_lang)
        )
        return
    elif text == kb_main['templates']:
        await update.message.reply_text(
            get_text(current_lang, 'templates_msg'),
            parse_mode=ParseMode.HTML
        )
        return
    elif text == kb_main['team']:
        await cmd_team(update, context)
        return
    elif text == kb_main['lang']:
        await cmd_lang(update, context)
        return
    elif text == kb_main['reset']:
        await cmd_reset(update, context)
        return
    
    # Products submenu
    elif text == kb_products['dvag']:
        await update.message.reply_text(get_text(current_lang, 'product_dvag'), parse_mode=ParseMode.HTML)
        return
    elif text == kb_products['generali']:
        await update.message.reply_text(get_text(current_lang, 'product_generali'), parse_mode=ParseMode.HTML)
        return
    elif text == kb_products['badenia']:
        await update.message.reply_text(get_text(current_lang, 'product_badenia'), parse_mode=ParseMode.HTML)
        return
    elif text == kb_products['advocard']:
        await update.message.reply_text(get_text(current_lang, 'product_advocard'), parse_mode=ParseMode.HTML)
        return
    elif text == kb_products['back']:
        await update.message.reply_text("📱", reply_markup=get_main_keyboard(current_lang))
        return
    
    # Clients submenu
    elif text == kb_clients['familia']:
        await update.message.reply_text(get_text(current_lang, 'client_familia'), parse_mode=ParseMode.HTML)
        return
    elif text == kb_clients['autonomo']:
        await update.message.reply_text(get_text(current_lang, 'client_autonomo'), parse_mode=ParseMode.HTML)
        return
    elif text == kb_clients['empresa']:
        await update.message.reply_text(get_text(current_lang, 'client_empresa'), parse_mode=ParseMode.HTML)
        return
    elif text == kb_clients['back']:
        await update.message.reply_text("📱", reply_markup=get_main_keyboard(current_lang))
        return
    
    # Regular query
    if text and not text.startswith('/'):
        await update.message.chat.send_action("typing")
        thinking_msg = await update.message.reply_text(get_text(current_lang, 'thinking'))
        
        try:
            context_docs = search_knowledge(text)
            response = await generate_response(text, user_id=user_id, context_docs=context_docs)
            
            storage.save_query(user_id, text, response)
            user = storage.get_user(user_id)
            storage.update_user(user_id, {'query_count': user.get('query_count', 0) + 1})
            
            await thinking_msg.delete()
            await update.message.reply_text(response, parse_mode=ParseMode.HTML)
            
        except Exception as e:
            await thinking_msg.delete()
            logger.error(f"Message error: {e}")
            await update.message.reply_text(get_text(current_lang, 'error', error=str(e)[:30]))

# ============================================================================
# MAIN
# ============================================================================
def main():
    logger.info("=" * 60)
    logger.info(f"🤖 PIPILA v{BOT_VERSION}")
    logger.info("=" * 60)
    
    chunks = collection.count() if collection else 0
    logger.info(f"📚 Knowledge: {chunks} chunks")
    logger.info(f"🗄️ DB: {'PostgreSQL' if engine else 'JSON'}")
    
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Commands
    application.add_handler(CommandHandler("start", cmd_start))
    application.add_handler(CommandHandler("help", cmd_help))
    application.add_handler(CommandHandler("docs", cmd_docs))
    application.add_handler(CommandHandler("stats", cmd_stats))
    application.add_handler(CommandHandler("team", cmd_team))
    application.add_handler(CommandHandler("lang", cmd_lang))
    application.add_handler(CommandHandler("admin", cmd_admin))
    application.add_handler(CommandHandler("reset", cmd_reset))
    
    # Callbacks
    application.add_handler(CallbackQueryHandler(callback_lang, pattern="^lang_"))
    
    # Messages
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logger.info("✅ Bot started")
    logger.info("=" * 60)
    
    application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

if __name__ == '__main__':
    main()
