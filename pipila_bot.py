#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🤖 PIPILA - Asistente Financiero Oscar Casco
Bot con RAG (Retrieval Augmented Generation) para equipo financiero
Creado por Ernest Kostevich para Oscar Casco
"""

import os
import json
import logging
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import re

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from telegram.constants import ParseMode

import google.generativeai as genai
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, JSON, Text, BigInteger
from sqlalchemy.orm import sessionmaker, declarative_base

# Библиотеки для RAG
import chromadb
from chromadb.config import Settings
import PyPDF2
import docx
from pathlib import Path

# ============================================================================
# КОНФИГУРАЦИЯ
# ============================================================================

BOT_TOKEN = os.getenv('BOT_TOKEN')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
DATABASE_URL = os.getenv('DATABASE_URL')

CREATOR_USERNAME = "Ernest_Kostevich"
CREATOR_ID = None
ADMIN_IDS = []  # ID членов команды Оскара (добавить позже)

BOT_START_TIME = datetime.now()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN required")

# ============================================================================
# GEMINI AI
# ============================================================================

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    
    ai_model = genai.GenerativeModel(
        model_name='gemini-2.0-flash-exp',
        generation_config={
            "temperature": 0.7,  # Más preciso para finanzas
            "top_p": 0.95,
            "top_k": 40,
            "max_output_tokens": 2048,
        },
        system_instruction="""Eres PIPILA, el Asistente Financiero de Oscar Casco.

IDENTIDAD:
- Asistente profesional para el equipo financiero de Oscar Casco
- Experto en: DVAG, Generali, Badenia, Advocard
- Metodología: Basada en las enseñanzas de Oscar Casco
- Tono: Formal, claro, cercano, con humor inteligente cuando es apropiado

REGLAS:
1. Responde SIEMPRE en español
2. Sé preciso y cita documentos cuando sea posible
3. Si no sabes algo, admítelo honestamente
4. Prioriza la seguridad financiera del cliente
5. Usa ejemplos concretos cuando expliques conceptos
6. Mantén respuestas concisas pero completas

FORMATO DE RESPUESTAS:
- Usa emojis moderadamente (📊 💰 📈 ✅ ⚠️)
- Estructura: Introducción breve → Contenido → Acción/Siguiente paso
- Cita fuentes: "Según [documento], ..."

LÍMITES:
- NO des asesoramiento financiero personal sin documentos
- NO inventes datos o estadísticas
- NO prometas rendimientos garantizados"""
    )
    
    logger.info("✅ Gemini 2.0 Flash configurado para PIPILA")
else:
    ai_model = None
    logger.error("❌ GEMINI_API_KEY no configurado")

# ============================================================================
# CHROMADB - RAG SYSTEM
# ============================================================================

# Inicialización de ChromaDB
chroma_client = chromadb.Client(Settings(
    chroma_db_impl="duckdb+parquet",
    persist_directory="./chroma_db"
))

# Colección para documentos
try:
    collection = chroma_client.get_or_create_collection(
        name="pipila_documents",
        metadata={"description": "Documentos financieros de Oscar Casco"}
    )
    logger.info(f"✅ ChromaDB inicializado: {collection.count()} documentos")
except Exception as e:
    logger.error(f"❌ Error ChromaDB: {e}")
    collection = None

# ============================================================================
# FUNCIONES RAG
# ============================================================================

def extract_text_from_pdf(file_path: str) -> str:
    """Extrae texto de PDF"""
    try:
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
            return text
    except Exception as e:
        logger.error(f"Error PDF {file_path}: {e}")
        return ""

def extract_text_from_docx(file_path: str) -> str:
    """Extrae texto de DOCX"""
    try:
        doc = docx.Document(file_path)
        text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
        return text
    except Exception as e:
        logger.error(f"Error DOCX {file_path}: {e}")
        return ""

def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
    """Divide texto en chunks con overlap"""
    chunks = []
    start = 0
    text_length = len(text)
    
    while start < text_length:
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        start += chunk_size - overlap
    
    return chunks

def load_documents_to_rag(documents_folder: str = "./documents"):
    """Carga todos los documentos a ChromaDB"""
    if not collection:
        logger.error("ChromaDB no disponible")
        return 0
    
    if not os.path.exists(documents_folder):
        logger.warning(f"Carpeta {documents_folder} no existe")
        return 0
    
    documents_loaded = 0
    
    for root, dirs, files in os.walk(documents_folder):
        for file in files:
            file_path = os.path.join(root, file)
            file_ext = Path(file).suffix.lower()
            
            try:
                # Extraer texto según tipo
                if file_ext == '.pdf':
                    text = extract_text_from_pdf(file_path)
                elif file_ext in ['.docx', '.doc']:
                    text = extract_text_from_docx(file_path)
                elif file_ext == '.txt':
                    with open(file_path, 'r', encoding='utf-8') as f:
                        text = f.read()
                else:
                    continue
                
                if not text or len(text) < 100:
                    continue
                
                # Dividir en chunks
                chunks = chunk_text(text)
                
                # Añadir a ChromaDB
                for i, chunk in enumerate(chunks):
                    doc_id = f"{file}_{i}"
                    collection.add(
                        documents=[chunk],
                        ids=[doc_id],
                        metadatas=[{
                            "source": file,
                            "chunk": i,
                            "path": file_path
                        }]
                    )
                
                documents_loaded += 1
                logger.info(f"✅ Cargado: {file} ({len(chunks)} chunks)")
                
            except Exception as e:
                logger.error(f"Error cargando {file}: {e}")
    
    logger.info(f"📚 Total documentos cargados: {documents_loaded}")
    return documents_loaded

def search_rag(query: str, n_results: int = 3) -> List[Dict]:
    """Busca en RAG y devuelve contexto relevante"""
    if not collection:
        return []
    
    try:
        results = collection.query(
            query_texts=[query],
            n_results=n_results
        )
        
        context_docs = []
        if results and results['documents']:
            for i, doc in enumerate(results['documents'][0]):
                metadata = results['metadatas'][0][i]
                context_docs.append({
                    'text': doc,
                    'source': metadata.get('source', 'Unknown'),
                    'relevance': 1 - (i * 0.1)  # Score simple
                })
        
        return context_docs
    except Exception as e:
        logger.error(f"Error RAG search: {e}")
        return []

async def generate_rag_response(query: str) -> str:
    """Genera respuesta usando RAG + Gemini"""
    if not ai_model:
        return "❌ AI no disponible en este momento."
    
    try:
        # 1. Buscar contexto relevante
        context_docs = search_rag(query, n_results=5)
        
        if not context_docs:
            # Sin contexto, respuesta general
            response = ai_model.generate_content(query)
            return response.text
        
        # 2. Construir prompt con contexto
        context_text = "\n\n---\n\n".join([
            f"📄 {doc['source']}\n{doc['text']}" 
            for doc in context_docs
        ])
        
        rag_prompt = f"""Basándote en los siguientes documentos, responde la pregunta del usuario.

DOCUMENTOS RELEVANTES:
{context_text}

PREGUNTA DEL USUARIO:
{query}

INSTRUCCIONES:
- Usa la información de los documentos cuando sea posible
- Cita las fuentes: "Según [nombre documento], ..."
- Si los documentos no contienen la info, dilo claramente
- Mantén tu tono profesional pero cercano"""

        # 3. Generar respuesta
        response = ai_model.generate_content(rag_prompt)
        return response.text
        
    except Exception as e:
        logger.error(f"Error RAG response: {e}")
        return f"😔 Error generando respuesta: {str(e)}"

# ============================================================================
# BASE DE DATOS
# ============================================================================

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    
    id = Column(BigInteger, primary_key=True)
    username = Column(String(255))
    first_name = Column(String(255))
    is_team = Column(Boolean, default=False)  # Miembro del equipo
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
        engine = create_engine(DATABASE_URL, echo=False)
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        logger.info("✅ PostgreSQL conectado")
    except Exception as e:
        logger.warning(f"⚠️ Error DB: {e}")

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
                    user = session.query(User).filter_by(id=user_id).first()
                
                return {
                    'id': user.id,
                    'username': user.username or '',
                    'first_name': user.first_name or '',
                    'is_team': user.is_team,
                    'query_count': user.query_count
                }
            except Exception as e:
                logger.error(f"get_user error: {e}")
                return {'id': user_id, 'is_team': False}
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
        """Verifica si es miembro del equipo"""
        if user_id == CREATOR_ID:
            return True
        if user_id in ADMIN_IDS:
            return True
        user = self.get_user(user_id)
        return user.get('is_team', False)

    def save_query(self, user_id: int, query: str, response: str):
        """Guarda consulta para analytics"""
        if not engine:
            return
        session = Session()
        try:
            q = Query(user_id=user_id, query=query[:1000], response=response[:1000])
            session.add(q)
            session.commit()
        except:
            pass
        finally:
            session.close()

storage = DataStorage()

# ============================================================================
# UTILIDADES
# ============================================================================

def identify_creator(user):
    global CREATOR_ID
    if user.username == CREATOR_USERNAME and CREATOR_ID is None:
        CREATOR_ID = user.id
        logger.info(f"Creator identificado: {user.id}")

def is_creator(user_id: int) -> bool:
    return user_id == CREATOR_ID

def get_main_keyboard() -> ReplyKeyboardMarkup:
    """Teclado principal del bot"""
    keyboard = [
        [KeyboardButton("💬 Consultar"), KeyboardButton("📚 Documentos")],
        [KeyboardButton("📊 Estadísticas"), KeyboardButton("ℹ️ Info")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# ============================================================================
# COMANDOS DEL BOT
# ============================================================================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    identify_creator(user)
    
    storage.update_user(user.id, {
        'username': user.username or '',
        'first_name': user.first_name or ''
    })
    
    is_team = storage.is_team_member(user.id)
    
    welcome_text = f"""🤖 <b>¡Hola, {user.first_name}!</b>

Soy <b>PIPILA</b>, el Asistente Financiero de Oscar Casco.

<b>🎯 ¿Qué puedo hacer por ti?</b>

• 💬 Responder consultas sobre productos financieros
• 📊 Explicar estrategias de inversión
• 📚 Buscar información en documentos
• 💡 Asesorarte según la metodología de Oscar

<b>⚡ Comandos principales:</b>

/help - Ver todos los comandos
/search [consulta] - Buscar en documentos
/stats - Estadísticas de uso

<b>📖 Conocimiento:</b>
DVAG • Generali • Badenia • Advocard

<b>👨‍💻 Creado por:</b> @{CREATOR_USERNAME}
<b>👔 Para:</b> Oscar Casco y su equipo"""

    if not is_team:
        welcome_text += "\n\n⚠️ <i>Nota: Este bot está diseñado para el equipo de Oscar Casco</i>"
    
    await update.message.reply_text(
        welcome_text, 
        parse_mode=ParseMode.HTML,
        reply_markup=get_main_keyboard()
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """📚 <b>COMANDOS DE PIPILA</b>

<b>🔍 Consultas:</b>
/search [pregunta] - Buscar en documentos
/ask [pregunta] - Consulta directa

<b>📊 Información:</b>
/docs - Lista de documentos disponibles
/stats - Estadísticas de uso
/info - Información del bot

<b>👥 Equipo (solo team):</b>
/reload - Recargar documentos
/users - Ver usuarios

<b>💡 Ejemplos:</b>

/search estrategias de inversión
/ask ¿Qué es DVAG?
/search fondos Generali

<b>💬 Conversación:</b>
También puedes escribirme directamente sin comandos.

Responderé basándome en los documentos de Oscar."""

    await update.message.reply_text(help_text, parse_mode=ParseMode.HTML)

async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Búsqueda en documentos RAG"""
    user_id = update.effective_user.id
    
    if not context.args:
        await update.message.reply_text(
            "❓ <b>Uso:</b> /search [tu consulta]\n\n"
            "<b>Ejemplo:</b> /search estrategias de inversión sostenible",
            parse_mode=ParseMode.HTML
        )
        return
    
    query = ' '.join(context.args)
    
    await update.message.chat.send_action("typing")
    
    try:
        # Generar respuesta con RAG
        response = await generate_rag_response(query)
        
        # Guardar consulta
        storage.save_query(user_id, query, response)
        
        # Actualizar contador
        user = storage.get_user(user_id)
        storage.update_user(user_id, {
            'query_count': user.get('query_count', 0) + 1
        })
        
        # Enviar respuesta
        await send_long_message(update.message, f"🔍 <b>Consulta:</b> {query}\n\n{response}")
        
    except Exception as e:
        logger.error(f"Error en search: {e}")
        await update.message.reply_text(
            f"😔 Error procesando tu consulta: {str(e)}"
        )

async def ask_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Alias para search"""
    await search_command(update, context)

async def docs_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lista documentos disponibles"""
    if not collection:
        await update.message.reply_text("❌ Sistema de documentos no disponible")
        return
    
    count = collection.count()
    
    docs_text = f"""📚 <b>DOCUMENTOS DISPONIBLES</b>

📊 Total de chunks: {count}

<b>Categorías:</b>
• DVAG - Productos y servicios
• Generali - Seguros y fondos
• Badenia - Seguros especializados
• Advocard - Protección legal

<b>Uso:</b>
/search [tema] para buscar información

<b>Ejemplos:</b>
• /search fondos de inversión DVAG
• /search seguros de vida Generali
• /search protección legal Advocard"""

    await update.message.reply_text(docs_text, parse_mode=ParseMode.HTML)

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Estadísticas del bot"""
    user_id = update.effective_user.id
    user = storage.get_user(user_id)
    
    uptime = datetime.now() - BOT_START_TIME
    doc_count = collection.count() if collection else 0
    
    stats_text = f"""📊 <b>ESTADÍSTICAS</b>

<b>👤 Tu uso:</b>
• Consultas: {user.get('query_count', 0)}

<b>🤖 Sistema:</b>
• Documentos: {doc_count} chunks
• Uptime: {uptime.days}d {uptime.seconds//3600}h
• AI: Gemini 2.0 Flash ✓
• DB: {'PostgreSQL ✓' if engine else 'JSON'}

<b>🚀 Estado:</b> Online"""

    if storage.is_team_member(user_id):
        # Estadísticas adicionales para el equipo
        all_users = storage.users if not engine else {}
        stats_text += f"\n\n<b>📈 Equipo:</b>\n• Usuarios: {len(all_users)}"
    
    await update.message.reply_text(stats_text, parse_mode=ParseMode.HTML)

async def info_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Información del bot"""
    info_text = """🤖 <b>PIPILA</b>
Asistente Financiero de Oscar Casco

<b>📖 Versión:</b> 1.0

<b>🧠 Tecnología:</b>
• RAG (Retrieval Augmented Generation)
• ChromaDB para búsqueda vectorial
• Gemini 2.0 Flash para IA
• PostgreSQL para datos

<b>🎯 Especialización:</b>
• DVAG - Deutsche Vermögensberatung
• Generali - Seguros y fondos
• Badenia - Seguros especializados
• Advocard - Protección legal

<b>👨‍💻 Desarrollador:</b>
@Ernest_Kostevich

<b>👔 Cliente:</b>
Oscar Casco y equipo

<b>📧 Soporte:</b>
Contacta a @Ernest_Kostevich"""

    await update.message.reply_text(info_text, parse_mode=ParseMode.HTML)

async def reload_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recarga documentos (solo team)"""
    user_id = update.effective_user.id
    
    if not storage.is_team_member(user_id):
        await update.message.reply_text("❌ Solo para miembros del equipo")
        return
    
    await update.message.reply_text("🔄 Recargando documentos...")
    
    try:
        count = load_documents_to_rag()
        await update.message.reply_text(
            f"✅ Documentos recargados\n\n📚 Total: {count} documentos"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

async def grant_team_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Añade miembro al equipo (solo creator)"""
    user_id = update.effective_user.id
    
    if not is_creator(user_id):
        await update.message.reply_text("❌ Solo para el creador")
        return
    
    if not context.args:
        await update.message.reply_text("❓ Uso: /grant_team [user_id]")
        return
    
    try:
        target_id = int(context.args[0])
        storage.update_user(target_id, {'is_team': True})
        await update.message.reply_text(f"✅ Usuario {target_id} añadido al equipo")
    except:
        await update.message.reply_text("❌ Error: ID inválido")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja mensajes de texto"""
    user = update.effective_user
    identify_creator(user)
    
    user_id = user.id
    text = update.message.text
    
    # Actualizar usuario
    storage.update_user(user_id, {
        'username': user.username or '',
        'first_name': user.first_name or ''
    })
    
    # Botones del menú
    if text in ["💬 Consultar"]:
        await update.message.reply_text(
            "💬 <b>Modo consulta activado</b>\n\n"
            "Escribe tu pregunta y buscaré en los documentos.\n\n"
            "<b>Ejemplos:</b>\n"
            "• ¿Qué es DVAG?\n"
            "• Estrategias de inversión sostenible\n"
            "• Fondos de Generali",
            parse_mode=ParseMode.HTML
        )
        return
    
    elif text in ["📚 Documentos"]:
        await docs_command(update, context)
        return
    
    elif text in ["📊 Estadísticas"]:
        await stats_command(update, context)
        return
    
    elif text in ["ℹ️ Info"]:
        await info_command(update, context)
        return
    
    # Consulta directa (sin comando)
    if text and not text.startswith('/'):
        await update.message.chat.send_action("typing")
        
        try:
            response = await generate_rag_response(text)
            storage.save_query(user_id, text, response)
            
            user_data = storage.get_user(user_id)
            storage.update_user(user_id, {
                'query_count': user_data.get('query_count', 0) + 1
            })
            
            await send_long_message(update.message, response)
            
        except Exception as e:
            logger.error(f"Error: {e}")
            await update.message.reply_text(f"😔 Error: {str(e)}")

async def send_long_message(message, text: str):
    """Envía mensajes largos divididos"""
    if len(text) <= 4000:
        await message.reply_text(text, parse_mode=ParseMode.HTML)
    else:
        parts = [text[i:i+4000] for i in range(0, len(text), 4000)]
        for part in parts:
            await message.reply_text(part, parse_mode=ParseMode.HTML)
            await asyncio.sleep(0.5)

# ============================================================================
# MAIN
# ============================================================================

def main():
    # Cargar documentos al inicio
    logger.info("📚 Cargando documentos...")
    docs_loaded = load_documents_to_rag()
    logger.info(f"✅ {docs_loaded} documentos cargados")
    
    # Configurar bot
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Comandos
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("search", search_command))
    application.add_handler(CommandHandler("ask", ask_command))
    application.add_handler(CommandHandler("docs", docs_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("info", info_command))
    application.add_handler(CommandHandler("reload", reload_command))
    application.add_handler(CommandHandler("grant_team", grant_team_command))
    
    # Mensajes
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND, 
        handle_message
    ))
    
    logger.info("=" * 60)
    logger.info("✅ PIPILA - Asistente Financiero Oscar Casco")
    logger.info("🤖 AI: Gemini 2.0 Flash + RAG (ChromaDB)")
    logger.info(f"📚 Documentos: {docs_loaded}")
    logger.info(f"🗄️ DB: {'PostgreSQL ✓' if engine else 'JSON'}")
    logger.info("=" * 60)
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
