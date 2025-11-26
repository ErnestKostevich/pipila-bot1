#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🤖 PIPILA - Asistente Financiero Oscar Casco
VERSION: 2.2 - ULTRA SIMPLE (копия рабочего кода AI DISCO BOT)
"""

import os
import json
import logging
import asyncio
from datetime import datetime
from typing import List, Dict
from pathlib import Path

from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from telegram.constants import ParseMode

# ✅ ТОЧНО ТАК ЖЕ как в AI DISCO BOT
import google.generativeai as genai

from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, Text, BigInteger
from sqlalchemy.orm import sessionmaker, declarative_base

# RAG
import chromadb
import PyPDF2
import docx

# ============================================================================
# КОНФИГУРАЦИЯ
# ============================================================================

BOT_TOKEN = os.getenv('BOT_TOKEN')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
DATABASE_URL = os.getenv('DATABASE_URL')

CREATOR_USERNAME = "Ernest_Kostevich"
CREATOR_ID = None
BOT_START_TIME = datetime.now()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN не найден")

# ============================================================================
# GEMINI AI - КОПИЯ AI DISCO BOT (100% РАБОЧИЙ КОД)
# ============================================================================

# ✅ ТОЧНО ТАК ЖЕ как в AI DISCO BOT
genai.configure(api_key=GEMINI_API_KEY)

generation_config = {
    "temperature": 1,
    "top_p": 0.95,
    "top_k": 40,
    "max_output_tokens": 1024,  # Меньше токенов = меньше нагрузка
}

safety_settings = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
]

# ✅ ТОЧНО ТАК ЖЕ как в AI DISCO BOT - простая system instruction
system_instruction = """Eres PIPILA, el Asistente Financiero del equipo de Oscar Casco.

Responde SIEMPRE en español. Sé profesional, claro y conciso (máximo 300 palabras).

Áreas de expertise:
- DVAG
- Generali  
- Badenia
- Advocard

Si tienes documentos en el contexto, cítalos: "Según el documento [nombre]..."
Si no tienes información, admítelo claramente."""

# ✅ Используем стабильную модель gemini-1.5-flash (не experimental)
model = genai.GenerativeModel(
    model_name='gemini-1.5-flash',
    generation_config=generation_config,
    safety_settings=safety_settings,
    system_instruction=system_instruction
)

logger.info("✅ Gemini 1.5 Flash configurado (limite: 1024 tokens)")

# ============================================================================
# CHROMADB - RAG
# ============================================================================

chroma_client = chromadb.PersistentClient(path="./chroma_db")

try:
    collection = chroma_client.get_or_create_collection(
        name="pipila_documents",
        metadata={"description": "Documentos equipo Oscar Casco"}
    )
    logger.info(f"✅ ChromaDB OK: {collection.count()} chunks")
except Exception as e:
    logger.error(f"❌ Error ChromaDB: {e}")
    collection = None

# ============================================================================
# RAG FUNCTIONS
# ============================================================================

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
        logger.error(f"Error PDF {file_path}: {e}")
        return ""

def extract_text_from_docx(file_path: str) -> str:
    try:
        doc = docx.Document(file_path)
        text = "\n".join([p.text for p in doc.paragraphs if p.text])
        return text
    except Exception as e:
        logger.error(f"Error DOCX {file_path}: {e}")
        return ""

def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
    if not text or len(text) < 100:
        return []
    
    chunks = []
    start = 0
    text_length = len(text)
    
    while start < text_length:
        end = min(start + chunk_size, text_length)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start += chunk_size - overlap
    
    return chunks

def load_documents_to_rag(documents_folder: str = "./documents") -> int:
    if not collection:
        logger.error("ChromaDB no disponible")
        return 0
    
    if not os.path.exists(documents_folder):
        logger.warning(f"❌ Carpeta {documents_folder} no existe")
        return 0
    
    documents_loaded = 0
    total_chunks = 0
    
    for root, dirs, files in os.walk(documents_folder):
        for file in files:
            file_path = os.path.join(root, file)
            file_ext = Path(file).suffix.lower()
            
            try:
                text = ""
                if file_ext == '.pdf':
                    text = extract_text_from_pdf(file_path)
                elif file_ext in ['.docx', '.doc']:
                    text = extract_text_from_docx(file_path)
                elif file_ext == '.txt':
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
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
                            metadatas=[{
                                "source": file,
                                "chunk": i,
                                "path": file_path,
                                "total_chunks": len(chunks)
                            }]
                        )
                    except:
                        pass
                
                documents_loaded += 1
                total_chunks += len(chunks)
                logger.info(f"✅ {file} ({len(chunks)} chunks)")
                
            except Exception as e:
                logger.error(f"Error {file}: {e}")
    
    logger.info(f"📚 Total: {documents_loaded} docs, {total_chunks} chunks")
    return documents_loaded

def search_rag(query: str, n_results: int = 3) -> List[Dict]:
    """Búsqueda en documentos - máximo 3 resultados para no sobrecargar"""
    if not collection:
        return []
    
    try:
        results = collection.query(
            query_texts=[query],
            n_results=n_results
        )
        
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
        logger.error(f"Error RAG search: {e}")
        return []

# ✅ Chat sessions - ТОЧНО ТАК ЖЕ как в AI DISCO BOT
chat_sessions = {}

def get_chat_session(user_id: int):
    """Получает chat session для пользователя"""
    if user_id not in chat_sessions:
        chat_sessions[user_id] = model.start_chat(history=[])
    return chat_sessions[user_id]

def clear_chat_session(user_id: int):
    """Очищает chat session"""
    if user_id in chat_sessions:
        del chat_sessions[user_id]

# ✅ УПРОЩЁННАЯ генерация - минимум промптов, максимум эффективности
async def generate_rag_response(query: str, user_id: int = None) -> str:
    """
    ULTRA SIMPLE - копия AI DISCO BOT подхода
    Без retry logic пока - сначала проверим что вообще работает
    """
    
    try:
        # Получаем chat session (как в AI DISCO BOT)
        chat = get_chat_session(user_id) if user_id else model.start_chat(history=[])
        
        # Ищем в документах (максимум 3 для экономии)
        context_docs = search_rag(query, n_results=3)
        
        if context_docs:
            # Простой контекст
            context_text = "\n\n".join([
                f"📄 {doc['source']}: {doc['text'][:500]}"
                for doc in context_docs[:2]  # Только 2 документа
            ])
            
            prompt = f"""DOCUMENTOS:

{context_text}

PREGUNTA: {query[:300]}

Responde breve (máx 200 palabras), citando documentos."""
        else:
            # Без документов - ещё короче
            prompt = f"""PREGUNTA: {query[:300]}

Sin documentos. Responde breve (máx 150 palabras) basándote en tu conocimiento general sobre finanzas."""
        
        # ✅ ТОЧНО ТАК ЖЕ как в AI DISCO BOT
        response = chat.send_message(prompt)
        return response.text
        
    except Exception as e:
        logger.error(f"Error generate: {e}")
        return f"😔 Error: {str(e)[:100]}"

# ============================================================================
# DATABASE - ПРОСТАЯ ВЕРСИЯ
# ============================================================================

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    
    id = Column(BigInteger, primary_key=True)
    username = Column(String(255))
    first_name = Column(String(255))
    is_team = Column(Boolean, default=False)
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
                
                return {
                    'id': user.id,
                    'username': user.username or '',
                    'first_name': user.first_name or '',
                    'is_team': user.is_team,
                    'query_count': user.query_count or 0
                }
            except:
                session.rollback()
                return {'id': user_id, 'is_team': False, 'query_count': 0}
            finally:
                session.close()
        else:
            if user_id not in self.users:
                self.users[user_id] = {
                    'id': user_id,
                    'username': '',
                    'first_name': '',
                    'is_team': False,
                    'query_count': 0
                }
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
            except:
                session.rollback()
            finally:
                session.close()
        else:
            user = self.get_user(user_id)
            user.update(data)
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
                return [{
                    'id': u.id,
                    'username': u.username,
                    'first_name': u.first_name,
                    'query_count': u.query_count
                } for u in users]
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

def get_main_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton("💬 Consultar"), KeyboardButton("📚 Documentos")],
        [KeyboardButton("📊 Estadísticas"), KeyboardButton("👥 Equipo")],
        [KeyboardButton("ℹ️ Info"), KeyboardButton("❓ Ayuda")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# ============================================================================
# КОМАНДЫ
# ============================================================================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    identify_creator(user)
    
    storage.update_user(user.id, {
        'username': user.username or '',
        'first_name': user.first_name or ''
    })
    
    text = f"""🤖 <b>¡Hola, {user.first_name}!</b>

Soy <b>PIPILA</b>, Asistente del <b>equipo de Oscar Casco</b>.

<b>💬 Uso:</b>
Escribe tu pregunta directamente o usa:

/search [consulta] - Buscar
/docs - Ver documentos
/stats - Estadísticas
/help - Ayuda

<b>📖 Áreas:</b>
DVAG • Generali • Badenia • Advocard

<b>👨‍💻 Creado por:</b> @{CREATOR_USERNAME}"""

    await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=get_main_keyboard())

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = """📚 <b>COMANDOS PIPILA</b>

<b>🔍 Consultas:</b>
/search [pregunta] - Buscar
Escribe directamente - responderé

<b>📊 Info:</b>
/docs - Documentos disponibles
/stats - Tus estadísticas
/team - Ver equipo
/clear - Limpiar historial

<b>💡 Ejemplos:</b>
"¿Qué es DVAG?"
"/search productos Generali"
"Explica Badenia"""

    if is_creator(update.effective_user.id):
        text += """

<b>⚙️ Admin:</b>
/grant_team [ID] - Añadir miembro
/reload - Recargar docs"""

    await update.message.reply_text(text, parse_mode=ParseMode.HTML)

async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not context.args:
        await update.message.reply_text("❓ /search [consulta]\n\nEjemplo: /search productos DVAG")
        return
    
    query = ' '.join(context.args)
    await update.message.chat.send_action("typing")
    
    try:
        response = await generate_rag_response(query, user_id=user_id)
        storage.save_query(user_id, query, response)
        
        user = storage.get_user(user_id)
        storage.update_user(user_id, {'query_count': user.get('query_count', 0) + 1})
        
        await update.message.reply_text(f"🔍 <b>Consulta:</b> {query}\n\n{response}", parse_mode=ParseMode.HTML)
        
    except Exception as e:
        logger.error(f"Error search: {e}")
        await update.message.reply_text(f"😔 Error: {str(e)}")

async def docs_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    count = collection.count() if collection else 0
    
    text = f"""📚 <b>DOCUMENTOS EQUIPO</b>

📊 Chunks: <b>{count}</b>

<b>📂 Categorías:</b>
• DVAG
• Generali
• Badenia
• Advocard

<b>💡 Uso:</b>
/search [tema] o escribe directamente"""

    await update.message.reply_text(text, parse_mode=ParseMode.HTML)

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = storage.get_user(user_id)
    
    uptime = datetime.now() - BOT_START_TIME
    doc_count = collection.count() if collection else 0
    
    text = f"""📊 <b>TUS STATS</b>

<b>👤 Perfil:</b>
• {user.get('first_name', 'N/A')}
• @{user.get('username', 'N/A')}
• {'✅ Equipo' if storage.is_team_member(user_id) else '⏳ Sin acceso'}

<b>📈 Actividad:</b>
• Consultas: <b>{user.get('query_count', 0)}</b>

<b>🤖 Sistema:</b>
• Docs: {doc_count} chunks
• Uptime: {uptime.days}d {uptime.seconds//3600}h
• AI: Gemini 2.0 ✅
• DB: {'PostgreSQL' if engine else 'JSON'} ✅"""

    await update.message.reply_text(text, parse_mode=ParseMode.HTML)

async def team_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not storage.is_team_member(update.effective_user.id):
        await update.message.reply_text("⚠️ Solo miembros.\n\nContacta al admin.")
        return
    
    team = storage.get_all_team_members()
    
    if not team:
        await update.message.reply_text("👥 Sin miembros aún.")
        return
    
    text = f"👥 <b>EQUIPO OSCAR CASCO</b>\n\n<b>Total:</b> {len(team)}\n\n"
    
    for i, m in enumerate(team, 1):
        text += f"{i}. <b>{m.get('first_name', 'N/A')}</b> (@{m.get('username', 'N/A')})\n"
        text += f"   Consultas: {m.get('query_count', 0)}\n\n"
    
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)

async def info_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = """🤖 <b>PIPILA</b>
<i>Asistente Equipo Oscar Casco</i>

<b>📖 Versión:</b> 2.2 (ULTRA SIMPLE)

<b>🧠 Tech:</b>
• Gemini 2.0 Flash
• ChromaDB + RAG
• PostgreSQL

<b>👨‍💻 Dev:</b> @Ernest_Kostevich
<b>👔 Cliente:</b> Oscar Casco"""

    await update.message.reply_text(text, parse_mode=ParseMode.HTML)

async def reload_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_creator(update.effective_user.id):
        await update.message.reply_text("❌ Solo creator")
        return
    
    msg = await update.message.reply_text("🔄 Recargando...")
    
    try:
        count = load_documents_to_rag()
        await msg.edit_text(
            f"✅ <b>Docs recargados</b>\n\n"
            f"📚 Documentos: <b>{count}</b>\n"
            f"📊 Chunks: <b>{collection.count() if collection else 0}</b>",
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        await msg.edit_text(f"❌ Error: {e}")

async def grant_team_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_creator(update.effective_user.id):
        await update.message.reply_text("❌ Solo creator")
        return
    
    if not context.args:
        await update.message.reply_text("❓ /grant_team [user_id]")
        return
    
    try:
        target_id = int(context.args[0])
        storage.update_user(target_id, {'is_team': True})
        
        await update.message.reply_text(f"✅ User {target_id} añadido al equipo!")
        
    except ValueError:
        await update.message.reply_text("❌ ID inválido")

async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    clear_chat_session(user_id)
    await update.message.reply_text("🧹 Historial limpio!")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    identify_creator(user)
    
    user_id = user.id
    text = update.message.text
    
    storage.update_user(user_id, {
        'username': user.username or '',
        'first_name': user.first_name or ''
    })
    
    # Botones menú
    if text == "💬 Consultar":
        await update.message.reply_text("💬 Escribe tu pregunta")
        return
    elif text == "📚 Documentos":
        await docs_command(update, context)
        return
    elif text == "📊 Estadísticas":
        await stats_command(update, context)
        return
    elif text == "👥 Equipo":
        await team_command(update, context)
        return
    elif text == "ℹ️ Info":
        await info_command(update, context)
        return
    elif text == "❓ Ayuda":
        await help_command(update, context)
        return
    
    # Consulta directa
    if text and not text.startswith('/'):
        await update.message.chat.send_action("typing")
        
        try:
            response = await generate_rag_response(text, user_id=user_id)
            storage.save_query(user_id, text, response)
            
            user_data = storage.get_user(user_id)
            storage.update_user(user_id, {'query_count': user_data.get('query_count', 0) + 1})
            
            await update.message.reply_text(response, parse_mode=ParseMode.HTML)
            
        except Exception as e:
            logger.error(f"Error handle: {e}")
            await update.message.reply_text(f"😔 Error: {str(e)}")

# ============================================================================
# MAIN
# ============================================================================

def main():
    logger.info("=" * 60)
    logger.info("🚀 PIPILA - Asistente Oscar Casco")
    logger.info("=" * 60)
    
    logger.info("📚 Cargando documentos...")
    docs_loaded = load_documents_to_rag()
    logger.info(f"✅ {docs_loaded} docs cargados")
    
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Comandos
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("search", search_command))
    application.add_handler(CommandHandler("docs", docs_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("team", team_command))
    application.add_handler(CommandHandler("info", info_command))
    application.add_handler(CommandHandler("reload", reload_command))
    application.add_handler(CommandHandler("grant_team", grant_team_command))
    application.add_handler(CommandHandler("clear", clear_command))
    
    # Mensajes
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handle_message
    ))
    
    logger.info("=" * 60)
    logger.info("✅ PIPILA iniciado")
    logger.info(f"🤖 AI: Gemini 1.5 Flash (ULTRA SIMPLE)")
    logger.info(f"📚 Docs: {docs_loaded}")
    logger.info(f"📊 Chunks: {collection.count() if collection else 0}")
    logger.info(f"🗄️ DB: {'PostgreSQL' if engine else 'JSON'}")
    logger.info("=" * 60)
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
