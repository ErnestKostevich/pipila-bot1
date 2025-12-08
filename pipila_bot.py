#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🤖 PIPILA v8.5 FINAL
Financial Assistant for Oscar Casco Team
✅ Gemini 2.5 Flash AI
✅ RAG System with ChromaDB
✅ PostgreSQL Database
✅ Bilingual (ES/DE)
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
BOT_VERSION = "8.5 FINAL"
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
# TRANSLATIONS - IMPROVED UI
# ============================================================================
TRANSLATIONS = {
    'es': {
        'welcome': """
╔═══════════════════════════════════════╗
║      🤖 <b>PIPILA</b> - Tu Asistente        ║
╚═══════════════════════════════════════╝

¡Hola <b>{name}</b>! 👋

Soy el asistente inteligente del <b>equipo de Oscar Casco</b>.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📚 <b>MIS CONOCIMIENTOS:</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• DVAG - Productos financieros
• Generali - Seguros de vida/salud
• Badenia - Ahorro vivienda
• Advocard - Protección jurídica

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💡 <b>CÓMO USARME:</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• Escribe tu pregunta directamente
• Envía documentos PDF/DOCX
• Usa los botones de abajo ⬇️

<i>Creado por @{creator}</i>
""",
        'help': """
📚 <b>GUÍA DE USO - PIPILA</b>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔍 <b>HACER CONSULTAS:</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• Escribe tu pregunta directamente
• /search [tema] - Buscar específico

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📄 <b>DOCUMENTOS:</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• Envía PDF, DOCX o TXT
• Los analizo y respondo

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚙️ <b>COMANDOS:</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
/start - Reiniciar bot
/docs - Ver base de conocimiento
/stats - Tus estadísticas
/team - Ver equipo
/lang - Cambiar idioma 🇪🇸/🇩🇪
/clear - Limpiar conversación

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💬 <b>EJEMPLOS:</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"¿Qué productos ofrece DVAG?"
"Explícame el seguro de vida Generali"
"¿Cómo funciona Badenia?"
""",
        'docs': """
📚 <b>BASE DE CONOCIMIENTO</b>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 <b>ESTADÍSTICAS:</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Fragmentos indexados: <b>{count}</b>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📂 <b>CATEGORÍAS:</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🏢 DVAG - Estructura y productos
🛡️ Generali - Seguros completos
🏠 Badenia - Ahorro vivienda
⚖️ Advocard - Protección legal

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💡 Escribe tu pregunta y buscaré
   la información relevante.
""",
        'stats': """
📊 <b>TUS ESTADÍSTICAS</b>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
👤 <b>PERFIL:</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Nombre: <b>{name}</b>
Usuario: @{username}
Estado: {access}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📈 <b>ACTIVIDAD:</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Consultas realizadas: <b>{queries}</b>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🤖 <b>SISTEMA:</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Base de datos: {docs} chunks
Uptime: {uptime}
AI: Gemini 2.5 Flash ✅
DB: {db} ✅
Versión: {version}
""",
        'team': """
👥 <b>EQUIPO OSCAR CASCO</b>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 <b>MIEMBROS:</b> {count}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{members}
""",
        'info': """
🤖 <b>PIPILA - INFORMACIÓN</b>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📖 <b>ACERCA DE:</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Versión: <b>{version}</b>
Asistente del equipo de Oscar Casco

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧠 <b>CAPACIDADES:</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Chat inteligente con memoria
✅ Búsqueda en documentos (RAG)
✅ Procesamiento de archivos
✅ Multilenguaje (ES/DE)
✅ Sistema de equipos

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚙️ <b>TECNOLOGÍA:</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🤖 Gemini 2.5 Flash
📚 ChromaDB + RAG
🗄️ PostgreSQL

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
👨‍💻 Desarrollador: @Ernest_Kostevich
👔 Cliente: Oscar Casco
""",
        'no_docs': '⚠️ Base de conocimiento vacía.\nContacta al administrador.',
        'team_only': '🔒 Acceso restringido a miembros del equipo.\n\nContacta al administrador para solicitar acceso.',
        'admin_only': '🔒 Comando solo para administradores.',
        'cleared': '🧹 ¡Conversación limpiada!\n\nPuedes empezar de nuevo.',
        'error': '❌ <b>Error:</b> {error}\n\nIntenta de nuevo o contacta al admin.',
        'processing': '⏳ Procesando tu consulta...',
        'processing_file': '📄 Analizando documento...',
        'no_query': '❓ <b>Uso:</b> /search [tu pregunta]\n\n<b>Ejemplo:</b>\n/search ¿Qué es DVAG?',
        'invalid_id': '❌ ID de usuario inválido',
        'user_added': '✅ ¡Usuario <b>{id}</b> añadido al equipo!',
        'lang_changed': '✅ Idioma cambiado a: 🇪🇸 <b>Español</b>',
        'choose_lang': '🌍 <b>Selecciona tu idioma:</b>',
        'ask_question': '💬 Escribe tu pregunta y te ayudaré',
        'file_processed': '✅ <b>Documento analizado:</b> {filename}\n\n{response}',
        'file_error': '❌ Error al procesar: {error}',
        'thinking': '🤔 Buscando en mi base de conocimiento...',
        'keyboard': {
            'ask': '💬 Preguntar',
            'docs': '📚 Conocimiento',
            'stats': '📊 Estadísticas',
            'team': '👥 Equipo',
            'info': 'ℹ️ Info',
            'help': '❓ Ayuda'
        }
    },
    'de': {
        'welcome': """
╔═══════════════════════════════════════╗
║      🤖 <b>PIPILA</b> - Dein Assistent      ║
╚═══════════════════════════════════════╝

Hallo <b>{name}</b>! 👋

Ich bin der intelligente Assistent des <b>Teams von Oscar Casco</b>.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📚 <b>MEIN WISSEN:</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• DVAG - Finanzprodukte
• Generali - Lebens-/Krankenversicherung
• Badenia - Bausparen
• Advocard - Rechtsschutz

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💡 <b>WIE DU MICH NUTZT:</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• Stelle deine Frage direkt
• Sende PDF/DOCX Dokumente
• Nutze die Buttons unten ⬇️

<i>Erstellt von @{creator}</i>
""",
        'help': """
📚 <b>BENUTZERHANDBUCH - PIPILA</b>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔍 <b>ANFRAGEN STELLEN:</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• Schreibe deine Frage direkt
• /search [Thema] - Gezielt suchen

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📄 <b>DOKUMENTE:</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• Sende PDF, DOCX oder TXT
• Ich analysiere und antworte

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚙️ <b>BEFEHLE:</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
/start - Bot neu starten
/docs - Wissensbasis ansehen
/stats - Deine Statistiken
/team - Team ansehen
/lang - Sprache ändern 🇪🇸/🇩🇪
/clear - Gespräch löschen

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💬 <b>BEISPIELE:</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"Welche Produkte bietet DVAG?"
"Erkläre mir die Generali Lebensversicherung"
"Wie funktioniert Badenia?"
""",
        'docs': """
📚 <b>WISSENSBASIS</b>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 <b>STATISTIKEN:</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Indexierte Fragmente: <b>{count}</b>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📂 <b>KATEGORIEN:</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🏢 DVAG - Struktur und Produkte
🛡️ Generali - Komplette Versicherungen
🏠 Badenia - Bausparen
⚖️ Advocard - Rechtsschutz

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💡 Stelle deine Frage und ich suche
   die relevanten Informationen.
""",
        'stats': """
📊 <b>DEINE STATISTIKEN</b>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
👤 <b>PROFIL:</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Name: <b>{name}</b>
Benutzer: @{username}
Status: {access}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📈 <b>AKTIVITÄT:</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Durchgeführte Anfragen: <b>{queries}</b>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🤖 <b>SYSTEM:</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Wissensbasis: {docs} Chunks
Uptime: {uptime}
AI: Gemini 2.5 Flash ✅
DB: {db} ✅
Version: {version}
""",
        'team': """
👥 <b>TEAM OSCAR CASCO</b>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 <b>MITGLIEDER:</b> {count}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{members}
""",
        'info': """
🤖 <b>PIPILA - INFORMATION</b>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📖 <b>ÜBER:</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Version: <b>{version}</b>
Assistent des Teams von Oscar Casco

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧠 <b>FÄHIGKEITEN:</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Intelligenter Chat mit Gedächtnis
✅ Dokumentensuche (RAG)
✅ Dateiverarbeitung
✅ Mehrsprachig (ES/DE)
✅ Team-System

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚙️ <b>TECHNOLOGIE:</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🤖 Gemini 2.5 Flash
📚 ChromaDB + RAG
🗄️ PostgreSQL

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
👨‍💻 Entwickler: @Ernest_Kostevich
👔 Kunde: Oscar Casco
""",
        'no_docs': '⚠️ Wissensbasis leer.\nKontaktiere den Administrator.',
        'team_only': '🔒 Zugriff nur für Teammitglieder.\n\nKontaktiere den Administrator für Zugang.',
        'admin_only': '🔒 Befehl nur für Administratoren.',
        'cleared': '🧹 Gespräch gelöscht!\n\nDu kannst neu beginnen.',
        'error': '❌ <b>Fehler:</b> {error}\n\nVersuche es erneut oder kontaktiere den Admin.',
        'processing': '⏳ Verarbeite deine Anfrage...',
        'processing_file': '📄 Analysiere Dokument...',
        'no_query': '❓ <b>Verwendung:</b> /search [deine Frage]\n\n<b>Beispiel:</b>\n/search Was ist DVAG?',
        'invalid_id': '❌ Ungültige Benutzer-ID',
        'user_added': '✅ Benutzer <b>{id}</b> zum Team hinzugefügt!',
        'lang_changed': '✅ Sprache geändert zu: 🇩🇪 <b>Deutsch</b>',
        'choose_lang': '🌍 <b>Wähle deine Sprache:</b>',
        'ask_question': '💬 Stelle deine Frage und ich helfe dir',
        'file_processed': '✅ <b>Dokument analysiert:</b> {filename}\n\n{response}',
        'file_error': '❌ Fehler beim Verarbeiten: {error}',
        'thinking': '🤔 Suche in meiner Wissensbasis...',
        'keyboard': {
            'ask': '💬 Fragen',
            'docs': '📚 Wissen',
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
                'möchte', 'bitte', 'danke', 'gut', 'schlecht', 'ja', 'nein', 'ich', 'du']
    es_words = ['qué', 'cómo', 'dónde', 'cuándo', 'por qué', 'es', 'son', 'tener', 'poder',
                'quiero', 'por favor', 'gracias', 'bueno', 'malo', 'sí', 'no', 'yo', 'tú']
    de_count = sum(1 for word in de_words if word in text_lower)
    es_count = sum(1 for word in es_words if word in text_lower)
    return 'de' if de_count > es_count else 'es'

# ============================================================================
# GEMINI AI CONFIGURATION
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
    'es': """Eres PIPILA, el asistente financiero inteligente del equipo de Oscar Casco.

REGLAS IMPORTANTES:
1. Responde SIEMPRE en español
2. Sé profesional, claro y amigable
3. Respuestas concisas (máximo 250 palabras)
4. Si tienes documentos, cítalos: "Según [documento]..."
5. Si no tienes información, admítelo claramente
6. Usa emojis moderadamente para hacer el texto más legible

ÁREAS DE CONOCIMIENTO:
- DVAG: Estructura, productos financieros, carrera
- Generali: Seguros de vida, salud, hogar, auto
- Badenia: Bausparkasse, ahorro vivienda
- Advocard: Protección jurídica

Siempre intenta ser útil y dar información práctica.""",

    'de': """Du bist PIPILA, der intelligente Finanzassistent des Teams von Oscar Casco.

WICHTIGE REGELN:
1. Antworte IMMER auf Deutsch
2. Sei professionell, klar und freundlich
3. Kurze Antworten (maximal 250 Wörter)
4. Wenn du Dokumente hast, zitiere sie: "Laut [Dokument]..."
5. Wenn du keine Informationen hast, gib es klar zu
6. Verwende Emojis moderat für bessere Lesbarkeit

WISSENSBEREICHE:
- DVAG: Struktur, Finanzprodukte, Karriere
- Generali: Lebens-, Kranken-, Haus-, Autoversicherung
- Badenia: Bausparkasse, Wohnungssparen
- Advocard: Rechtsschutz

Versuche immer hilfreich zu sein und praktische Informationen zu geben."""
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
# AI RESPONSE GENERATION
# ============================================================================
async def generate_response(query: str, user_id: int = None, context_docs: List[Dict] = None) -> str:
    try:
        lang = get_user_language(user_id) if user_id else 'es'
        chat = get_chat_session(user_id, lang) if user_id else model_text.start_chat(history=[])
        
        if context_docs:
            context_text = "\n\n".join([
                f"📄 [{doc['source']}]:\n{doc['text'][:600]}" 
                for doc in context_docs
            ])
            if lang == 'es':
                prompt = f"""DOCUMENTOS RELEVANTES:
{context_text}

PREGUNTA DEL USUARIO: {query}

Responde basándote en los documentos. Cita las fuentes. Sé conciso y útil."""
            else:
                prompt = f"""RELEVANTE DOKUMENTE:
{context_text}

BENUTZERFRAGE: {query}

Antworte basierend auf den Dokumenten. Zitiere die Quellen. Sei kurz und hilfreich."""
        else:
            if lang == 'es':
                prompt = f"PREGUNTA: {query}\n\nNo tengo documentos específicos. Responde con tu conocimiento general sobre DVAG, Generali, Badenia, Advocard."
            else:
                prompt = f"FRAGE: {query}\n\nKeine spezifischen Dokumente. Antworte mit deinem allgemeinen Wissen über DVAG, Generali, Badenia, Advocard."
        
        for attempt in range(3):
            try:
                response = chat.send_message(prompt)
                return response.text
            except Exception as e:
                logger.error(f"Gemini attempt {attempt + 1} failed: {e}")
                await asyncio.sleep(1)
        
        return get_text(lang, 'error', error="AI no disponible")
        
    except Exception as e:
        logger.error(f"Generate response error: {e}")
        lang = get_user_language(user_id) if user_id else 'es'
        return get_text(lang, 'error', error=str(e)[:50])

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
            return get_text(lang, 'file_error', error="No se pudo extraer texto")
        
        chat = get_chat_session(user_id, lang)
        
        if lang == 'es':
            prompt = f"""DOCUMENTO: {filename}

CONTENIDO:
{text[:3000]}

{f'PREGUNTA ESPECÍFICA: {query}' if query else 'Analiza y resume el contenido principal.'}

Proporciona un análisis útil y conciso."""
        else:
            prompt = f"""DOKUMENT: {filename}

INHALT:
{text[:3000]}

{f'SPEZIFISCHE FRAGE: {query}' if query else 'Analysiere und fasse den Hauptinhalt zusammen.'}

Gib eine hilfreiche und kurze Analyse."""
        
        response = chat.send_message(prompt)
        return response.text
        
    except Exception as e:
        logger.error(f"Process file error: {e}")
        lang = get_user_language(user_id) if user_id else 'es'
        return get_text(lang, 'file_error', error=str(e)[:50])

# ============================================================================
# CHROMADB - RAG SYSTEM
# ============================================================================
chroma_client = None
collection = None

try:
    chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
    collection = chroma_client.get_or_create_collection(name="pipila_documents")
    logger.info(f"✅ ChromaDB: {collection.count()} chunks loaded")
except Exception as e:
    logger.warning(f"⚠️ ChromaDB not ready: {e}")

def extract_text_from_pdf(file_path: str) -> str:
    try:
        with open(file_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            text = ""
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
            return text
    except Exception as e:
        logger.error(f"PDF extraction error: {e}")
        return ""

def extract_text_from_docx(file_path: str) -> str:
    try:
        doc = docx.Document(file_path)
        return "\n".join([p.text for p in doc.paragraphs if p.text])
    except Exception as e:
        logger.error(f"DOCX extraction error: {e}")
        return ""

def search_knowledge(query: str, n_results: int = 5) -> List[Dict]:
    """Search in ChromaDB knowledge base"""
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
        logger.warning(f"⚠️ Database error: {e}")
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
# HELPER FUNCTIONS
# ============================================================================
def identify_creator(user):
    global CREATOR_ID
    if user.username == CREATOR_USERNAME and CREATOR_ID is None:
        CREATOR_ID = user.id
        logger.info(f"✅ Creator identified: @{user.username} (ID: {user.id})")

def is_creator(user_id: int) -> bool:
    return user_id == CREATOR_ID

def get_keyboard(lang: str = 'es') -> ReplyKeyboardMarkup:
    kb = TRANSLATIONS[lang]['keyboard']
    keyboard = [
        [KeyboardButton(kb['ask']), KeyboardButton(kb['docs'])],
        [KeyboardButton(kb['stats']), KeyboardButton(kb['team'])],
        [KeyboardButton(kb['info']), KeyboardButton(kb['help'])]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

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
    
    text = get_text(lang, 'welcome', name=user.first_name or 'Usuario', creator=CREATOR_USERNAME)
    await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=get_keyboard(lang))

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_language(user_id)
    text = get_text(lang, 'help')
    
    if is_creator(user_id):
        admin_help = "\n\n⚙️ <b>ADMIN:</b>\n/grant_team [ID o @usuario]" if lang == 'es' else "\n\n⚙️ <b>ADMIN:</b>\n/grant_team [ID oder @benutzer]"
        text += admin_help
    
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)

async def cmd_lang(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_language(user_id)
    
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🇪🇸 Español", callback_data="lang_es"),
            InlineKeyboardButton("🇩🇪 Deutsch", callback_data="lang_de")
        ]
    ])
    
    await update.message.reply_text(
        get_text(lang, 'choose_lang'),
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard
    )

async def callback_lang(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    new_lang = query.data.split('_')[1]
    
    set_user_language(user_id, new_lang)
    storage.update_user(user_id, {'language': new_lang})
    
    await query.edit_message_text(
        get_text(new_lang, 'lang_changed'),
        parse_mode=ParseMode.HTML
    )
    await query.message.reply_text("✅", reply_markup=get_keyboard(new_lang))

async def cmd_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_language(user_id)
    
    if not context.args:
        await update.message.reply_text(get_text(lang, 'no_query'), parse_mode=ParseMode.HTML)
        return
    
    query = ' '.join(context.args)
    await update.message.chat.send_action("typing")
    
    # Show thinking message
    thinking_msg = await update.message.reply_text(get_text(lang, 'thinking'))
    
    try:
        # Search in knowledge base
        context_docs = search_knowledge(query)
        
        # Generate response
        response = await generate_response(query, user_id=user_id, context_docs=context_docs)
        
        # Save query
        storage.save_query(user_id, query, response)
        user = storage.get_user(user_id)
        storage.update_user(user_id, {'query_count': user.get('query_count', 0) + 1})
        
        # Delete thinking message and send response
        await thinking_msg.delete()
        
        search_label = "🔍 <b>Búsqueda:</b>" if lang == 'es' else "🔍 <b>Suche:</b>"
        await update.message.reply_text(
            f"{search_label} {query}\n\n{response}",
            parse_mode=ParseMode.HTML
        )
        
    except Exception as e:
        await thinking_msg.delete()
        logger.error(f"Search error: {e}")
        await update.message.reply_text(get_text(lang, 'error', error=str(e)[:50]), parse_mode=ParseMode.HTML)

async def cmd_docs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_language(user_id)
    count = collection.count() if collection else 0
    await update.message.reply_text(get_text(lang, 'docs', count=count), parse_mode=ParseMode.HTML)

async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_language(user_id)
    user = storage.get_user(user_id)
    
    uptime = datetime.now() - BOT_START_TIME
    uptime_str = f"{uptime.days}d {uptime.seconds//3600}h {(uptime.seconds%3600)//60}m"
    
    doc_count = collection.count() if collection else 0
    
    if lang == 'es':
        access = "✅ Miembro del equipo" if storage.is_team_member(user_id) else "⏳ Sin acceso completo"
    else:
        access = "✅ Teammitglied" if storage.is_team_member(user_id) else "⏳ Kein voller Zugang"
    
    db_status = "PostgreSQL ✅" if engine else "JSON (local)"
    
    text = get_text(lang, 'stats',
        name=user.get('first_name', 'N/A'),
        username=user.get('username', 'N/A'),
        access=access,
        queries=user.get('query_count', 0),
        docs=doc_count,
        uptime=uptime_str,
        db=db_status,
        version=BOT_VERSION
    )
    
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)

async def cmd_team(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_language(user_id)
    
    if not storage.is_team_member(user_id):
        await update.message.reply_text(get_text(lang, 'team_only'), parse_mode=ParseMode.HTML)
        return
    
    team = storage.get_team_members()
    
    if not team:
        no_members = "👥 Aún no hay miembros en el equipo." if lang == 'es' else "👥 Noch keine Teammitglieder."
        await update.message.reply_text(no_members)
        return
    
    members_text = ""
    for i, m in enumerate(team, 1):
        name = m.get('first_name', 'N/A')
        username = m.get('username', 'N/A')
        queries = m.get('query_count', 0)
        label = "consultas" if lang == 'es' else "Anfragen"
        members_text += f"{i}. <b>{name}</b> (@{username})\n   📊 {queries} {label}\n\n"
    
    text = get_text(lang, 'team', count=len(team), members=members_text)
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)

async def cmd_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_language(user_id)
    text = get_text(lang, 'info', version=BOT_VERSION)
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)

async def cmd_grant_team(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    
    if target.startswith('@'):
        username = target[1:]
        if engine:
            session = Session()
            try:
                user = session.query(User).filter(User.username.ilike(username)).first()
                if user:
                    user.is_team = True
                    session.commit()
                    msg = f"✅ @{username} añadido al equipo!" if lang == 'es' else f"✅ @{username} zum Team hinzugefügt!"
                    await update.message.reply_text(msg)
                else:
                    msg = f"⚠️ @{username} no encontrado. Debe enviar /start primero." if lang == 'es' else f"⚠️ @{username} nicht gefunden. Muss zuerst /start senden."
                    await update.message.reply_text(msg)
            except Exception as e:
                session.rollback()
                await update.message.reply_text(f"❌ Error: {str(e)[:50]}")
            finally:
                session.close()
        else:
            found = False
            for uid, udata in storage.users.items():
                if udata.get('username', '').lower() == username.lower():
                    storage.update_user(uid, {'is_team': True})
                    await update.message.reply_text(f"✅ @{username} added!")
                    found = True
                    break
            if not found:
                await update.message.reply_text(f"⚠️ @{username} not found")
    else:
        try:
            target_id = int(target)
            storage.update_user(target_id, {'is_team': True})
            await update.message.reply_text(get_text(lang, 'user_added', id=target_id), parse_mode=ParseMode.HTML)
        except ValueError:
            await update.message.reply_text(get_text(lang, 'invalid_id'))

async def cmd_clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    
    storage.update_user(user_id, {
        'username': user.username or '',
        'first_name': user.first_name or ''
    })
    
    document = update.message.document
    filename = document.file_name
    file_ext = Path(filename).suffix.lower()
    
    if file_ext not in ['.pdf', '.docx', '.doc', '.txt']:
        msg = "⚠️ Solo acepto archivos PDF, DOCX o TXT" if lang == 'es' else "⚠️ Nur PDF, DOCX oder TXT Dateien"
        await update.message.reply_text(msg)
        return
    
    caption = update.message.caption or ""
    
    await update.message.chat.send_action("typing")
    processing_msg = await update.message.reply_text(get_text(lang, 'processing_file'))
    
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
        await update.message.reply_text(get_text(lang, 'file_error', error=str(e)[:50]))

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    identify_creator(user)
    user_id = user.id
    text = update.message.text
    
    user_data = storage.get_user(user_id)
    current_lang = user_data.get('language', 'es')
    
    # Auto-detect language
    detected_lang = detect_language(text)
    if detected_lang != current_lang and len(text) > 20:
        set_user_language(user_id, detected_lang)
        storage.update_user(user_id, {'language': detected_lang})
        current_lang = detected_lang
    
    storage.update_user(user_id, {
        'username': user.username or '',
        'first_name': user.first_name or ''
    })
    
    # Handle keyboard buttons
    kb = TRANSLATIONS[current_lang]['keyboard']
    
    if text == kb['ask']:
        await update.message.reply_text(get_text(current_lang, 'ask_question'))
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
    
    # Handle regular questions
    if text and not text.startswith('/'):
        await update.message.chat.send_action("typing")
        
        thinking_msg = await update.message.reply_text(get_text(current_lang, 'thinking'))
        
        try:
            # Search knowledge base
            context_docs = search_knowledge(text)
            
            # Generate response
            response = await generate_response(text, user_id=user_id, context_docs=context_docs)
            
            # Save query
            storage.save_query(user_id, text, response)
            user = storage.get_user(user_id)
            storage.update_user(user_id, {'query_count': user.get('query_count', 0) + 1})
            
            await thinking_msg.delete()
            await update.message.reply_text(response, parse_mode=ParseMode.HTML)
            
        except Exception as e:
            await thinking_msg.delete()
            logger.error(f"Message error: {e}")
            await update.message.reply_text(
                get_text(current_lang, 'error', error=str(e)[:50]),
                parse_mode=ParseMode.HTML
            )

# ============================================================================
# MAIN
# ============================================================================
def main():
    logger.info("=" * 60)
    logger.info(f"🤖 PIPILA v{BOT_VERSION}")
    logger.info("=" * 60)
    
    chunks = collection.count() if collection else 0
    
    logger.info(f"📚 Knowledge base: {chunks} chunks")
    logger.info(f"🗄️ Database: {'PostgreSQL' if engine else 'JSON'}")
    logger.info(f"🤖 AI: Gemini 2.5 Flash")
    
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Command handlers
    application.add_handler(CommandHandler("start", cmd_start))
    application.add_handler(CommandHandler("help", cmd_help))
    application.add_handler(CommandHandler("lang", cmd_lang))
    application.add_handler(CommandHandler("search", cmd_search))
    application.add_handler(CommandHandler("docs", cmd_docs))
    application.add_handler(CommandHandler("stats", cmd_stats))
    application.add_handler(CommandHandler("team", cmd_team))
    application.add_handler(CommandHandler("info", cmd_info))
    application.add_handler(CommandHandler("grant_team", cmd_grant_team))
    application.add_handler(CommandHandler("clear", cmd_clear))
    
    # Callback handlers
    application.add_handler(CallbackQueryHandler(callback_lang, pattern="^lang_"))
    
    # Message handlers
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logger.info("=" * 60)
    logger.info("✅ Bot started successfully!")
    logger.info("=" * 60)
    
    application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

if __name__ == '__main__':
    main()
