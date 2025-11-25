#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🤖 PIPILA - Asistente Financiero Oscar Casco y Equipo
Bot con RAG (Retrieval Augmented Generation) para equipo financiero
Creado por Ernest Kostevich para Oscar Casco
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

import google.generativeai as genai
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, Text, BigInteger
from sqlalchemy.orm import sessionmaker, declarative_base

# Bibliotecas para RAG
import chromadb
import PyPDF2
import docx

# ============================================================================
# CONFIGURACIÓN
# ============================================================================

BOT_TOKEN = os.getenv('BOT_TOKEN')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
DATABASE_URL = os.getenv('DATABASE_URL')

# Creador del bot
CREATOR_USERNAME = "Ernest_Kostevich"
CREATOR_ID = None

BOT_START_TIME = datetime.now()

# Configuración de logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN no encontrado")

# ============================================================================
# GEMINI AI
# ============================================================================

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    
    ai_model = genai.GenerativeModel(
        model_name='gemini-2.0-flash-exp',
        generation_config={
            "temperature": 0.7,
            "top_p": 0.95,
            "top_k": 40,
            "max_output_tokens": 2048,
        },
        system_instruction="""Eres PIPILA, el Asistente Financiero del equipo de Oscar Casco.

IDENTIDAD:
- Asistente profesional para TODO el equipo de Oscar Casco
- Ayudas a todos los miembros por igual con dedicación
- Experto en: DVAG, Generali, Badenia, Advocard
- Metodología: Basada en documentos y enseñanzas de Oscar Casco
- Tono: Profesional, claro, cercano y colaborativo

REGLAS IMPORTANTES:
1. Responde SIEMPRE en español
2. Trata a todos los miembros con igual profesionalismo
3. Cita documentos específicos cuando uses su información
4. Admite si no sabes algo - la honestidad es clave
5. Prioriza información de los documentos del equipo
6. Usa ejemplos concretos y prácticos

FORMATO:
- Emojis profesionales con moderación (📊 💰 📈 ✅ ⚠️ 📄)
- Estructura: Intro → Contenido → Recomendación
- Citas: "Según el documento [nombre], ..."
- Conciso pero completo

LÍMITES:
- NO des asesoramiento sin base documental
- NO inventes datos
- NO prometas rendimientos garantizados
- NO compartas info fuera del equipo"""
    )
    
    logger.info("✅ Gemini 2.0 Flash configurado")
else:
    ai_model = None
    logger.error("❌ GEMINI_API_KEY no configurado")

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
# FUNCIONES RAG
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
        logger.warning(f"Carpeta {documents_folder} no existe")
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

def search_rag(query: str, n_results: int = 5) -> List[Dict]:
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
                    'chunk': metadata.get('chunk', 0),
                    'relevance': 1 - (i * 0.15)
                })
        
        return context_docs
        
    except Exception as e:
        logger.error(f"Error RAG search: {e}")
        return []

# Sistema de memoria de conversación (40 mensajes por usuario)
conversation_memory = {}

def get_conversation_history(user_id: int) -> List[Dict]:
    """Obtiene historial de conversación del usuario"""
    if user_id not in conversation_memory:
        conversation_memory[user_id] = []
    return conversation_memory[user_id]

def add_to_conversation(user_id: int, role: str, content: str):
    """Añade mensaje al historial (máximo 40 mensajes)"""
    if user_id not in conversation_memory:
        conversation_memory[user_id] = []
    
    conversation_memory[user_id].append({
        'role': role,
        'content': content,
        'timestamp': datetime.now()
    })
    
    # Mantener solo últimos 40 mensajes
    if len(conversation_memory[user_id]) > 40:
        conversation_memory[user_id] = conversation_memory[user_id][-40:]

async def generate_rag_response(query: str, user_id: int = None) -> str:
    if not ai_model:
        return "❌ Sistema IA no disponible."
    
    try:
        # Buscar en documentos
        context_docs = search_rag(query, n_results=5)
        
        # Obtener historial de conversación
        history = get_conversation_history(user_id) if user_id else []
        
        # Construir contexto de conversación
        conversation_context = ""
        if history and len(history) > 0:
            recent_history = history[-10:]  # Últimos 10 mensajes
            conversation_context = "\n\nCONVERSACIÓN PREVIA:\n"
            for msg in recent_history:
                role_label = "Usuario" if msg['role'] == 'user' else "PIPILA"
                conversation_context += f"{role_label}: {msg['content'][:200]}\n"
        
        if not context_docs:
            prompt = f"""Usuario del equipo pregunta: {query}
{conversation_context}

No hay documentos disponibles. Responde profesionalmente indicando que 
sería mejor consultar los documentos del equipo para info precisa.
Considera la conversación previa si es relevante."""
            
            response = ai_model.generate_content(prompt)
            result = response.text
            
            # Guardar en memoria
            if user_id:
                add_to_conversation(user_id, 'user', query)
                add_to_conversation(user_id, 'assistant', result)
            
            return result
        
        context_text = "\n\n---\n\n".join([
            f"📄 {doc['source']}\n{doc['text']}" 
            for doc in context_docs
        ])
        
        rag_prompt = f"""Basándote en documentos del equipo de Oscar Casco, responde:

DOCUMENTOS:
{context_text}
{conversation_context}

PREGUNTA ACTUAL:
{query}

INSTRUCCIONES:
- Usa info de los documentos
- Considera la conversación previa si es relevante
- Cita: "Según [documento], ..."
- Si falta info, dilo claramente
- Tono profesional y colaborativo
- Ejemplos prácticos"""

        response = ai_model.generate_content(rag_prompt)
        result = response.text
        
        # Guardar en memoria
        if user_id:
            add_to_conversation(user_id, 'user', query)
            add_to_conversation(user_id, 'assistant', result)
        
        return result
        
    except Exception as e:
        logger.error(f"Error RAG: {e}")
        return f"😔 Error: {str(e)}\n\nIntenta de nuevo o usa /help"

# ============================================================================
# BASE DE DATOS
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
        engine = create_engine(DATABASE_URL, echo=False)
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
# UTILIDADES
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
# COMANDOS
# ============================================================================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    identify_creator(user)
    
    storage.update_user(user.id, {
        'username': user.username or '',
        'first_name': user.first_name or ''
    })
    
    is_team = storage.is_team_member(user.id)
    
    text = f"""🤖 <b>¡Hola, {user.first_name}!</b>

Soy <b>PIPILA</b>, Asistente del <b>equipo de Oscar Casco</b>.

<b>🎯 Funciones:</b>

• 💬 Consultas sobre productos financieros
• 📊 Estrategias de inversión
• 📚 Búsqueda en documentos del equipo
• 💡 Asesoría según metodología de Oscar
• 👥 Apoyo a todo el equipo

<b>⚡ Comandos:</b>

/search [consulta] - Buscar
/docs - Ver documentos
/stats - Tus estadísticas
/team - Ver equipo
/help - Ayuda completa

<b>📖 Áreas:</b>
DVAG • Generali • Badenia • Advocard

<b>👨‍💻 Creado por:</b> @{CREATOR_USERNAME}
<b>👔 Para:</b> Equipo Oscar Casco"""

    if is_team:
        text += "\n\n✅ <i>Eres miembro - acceso completo</i>"
    else:
        text += "\n\n⚠️ <i>Solicita acceso al admin</i>"
    
    await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=get_main_keyboard())

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    is_team = storage.is_team_member(update.effective_user.id)
    
    text = """📚 <b>COMANDOS PIPILA</b>

<b>🔍 Consultas:</b>
/search [pregunta] - Buscar
/ask [pregunta] - Consulta directa

<b>📊 Info:</b>
/docs - Documentos disponibles
/stats - Tus estadísticas
/team - Ver equipo
/info - Info del bot
/clear - Limpiar historial conversación

<b>💡 Ejemplos:</b>

/search productos DVAG
/search fondos Generali
¿Cómo funciona Badenia?

<b>💬 Uso directo:</b>
Escribe sin comandos, responderé
basándome en documentos.

<b>🧠 Memoria:</b>
Recuerdo últimos 40 mensajes para
contexto. Usa /clear para reiniciar."""

    if is_team:
        text += """

<b>👥 Equipo:</b>
/reload - Recargar docs"""

    if is_creator(update.effective_user.id):
        text += """

<b>⚙️ Admin:</b>
/grant_team [ID] - Añadir
/remove_team [ID] - Remover"""

    await update.message.reply_text(text, parse_mode=ParseMode.HTML)

async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not context.args:
        await update.message.reply_text(
            "❓ <b>Uso:</b> /search [consulta]\n\n"
            "<b>Ejemplos:</b>\n"
            "/search estrategias inversión\n"
            "/search productos DVAG",
            parse_mode=ParseMode.HTML
        )
        return
    
    query = ' '.join(context.args)
    await update.message.chat.send_action("typing")
    
    try:
        response = await generate_rag_response(query, user_id=user_id)
        storage.save_query(user_id, query, response)
        
        user = storage.get_user(user_id)
        storage.update_user(user_id, {'query_count': user.get('query_count', 0) + 1})
        
        await send_long_message(update.message, f"🔍 <b>Consulta:</b> {query}\n\n{response}")
        
    except Exception as e:
        logger.error(f"Error search: {e}")
        await update.message.reply_text(f"😔 Error: {str(e)}")

async def ask_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await search_command(update, context)

async def docs_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not collection:
        await update.message.reply_text("❌ Sistema docs no disponible")
        return
    
    count = collection.count()
    
    text = f"""📚 <b>DOCUMENTOS EQUIPO</b>

📊 Chunks: <b>{count}</b>

<b>📂 Categorías:</b>

• 🏢 <b>DVAG</b> - Productos/servicios
• 🛡️ <b>Generali</b> - Seguros/fondos
• 🔐 <b>Badenia</b> - Seguros especializados
• ⚖️ <b>Advocard</b> - Protección legal

<b>💡 Uso:</b>

/search [tema] o escribe directamente

<b>✨ Ejemplos:</b>

"¿Fondos Generali?"
"Explica productos DVAG"
"Seguros Badenia"""

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
• DB: {'PostgreSQL ✅' if engine else 'JSON ✅'}

<b>🚀 Estado:</b> 🟢 Online"""

    if storage.is_team_member(user_id):
        team = storage.get_all_team_members()
        text += f"\n\n<b>👥 Equipo:</b> {len(team)} miembros"
    
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)

async def team_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not storage.is_team_member(update.effective_user.id):
        await update.message.reply_text(
            "⚠️ Solo miembros del equipo.\n\nContacta al admin."
        )
        return
    
    team = storage.get_all_team_members()
    
    if not team:
        await update.message.reply_text("👥 Sin miembros aún.")
        return
    
    text = f"👥 <b>EQUIPO OSCAR CASCO</b>\n\n<b>Total:</b> {len(team)}\n\n<b>📋 Miembros:</b>\n\n"
    
    for i, m in enumerate(team, 1):
        text += f"{i}. <b>{m.get('first_name', 'N/A')}</b> (@{m.get('username', 'N/A')})\n"
        text += f"   • Consultas: {m.get('query_count', 0)}\n\n"
    
    text += "\n💡 <i>Todos con acceso completo</i>"
    
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)

async def info_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = """🤖 <b>PIPILA</b>
<i>Asistente Equipo Oscar Casco</i>

<b>📖 Versión:</b> 1.0

<b>🧠 Tech:</b>
• RAG + ChromaDB
• Gemini 2.0 Flash
• PostgreSQL
• Telegram Bot API 21.5

<b>🎯 Áreas:</b>
• DVAG
• Generali
• Badenia
• Advocard

<b>✨ Features:</b>
• Búsqueda inteligente
• Citas de fuentes
• Gestión equipo
• Stats uso

<b>👨‍💻 Dev:</b> @Ernest_Kostevich
<b>👔 Cliente:</b> Oscar Casco

<b>🔒 Privacidad:</b>
Bot exclusivo equipo.
Info confidencial."""

    await update.message.reply_text(text, parse_mode=ParseMode.HTML)

async def reload_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not storage.is_team_member(user_id):
        await update.message.reply_text("❌ Solo equipo")
        return
    
    msg = await update.message.reply_text("🔄 Recargando docs...")
    
    try:
        count = load_documents_to_rag()
        await msg.edit_text(
            f"✅ <b>Docs recargados</b>\n\n"
            f"📚 Documentos: <b>{count}</b>\n"
            f"📊 Chunks: <b>{collection.count() if collection else 0}</b>\n\n"
            f"💡 Equipo ya puede consultar info actualizada",
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        await msg.edit_text(f"❌ Error: {e}")

async def grant_team_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not is_creator(user_id):
        await update.message.reply_text("❌ Solo creator")
        return
    
    if not context.args:
        await update.message.reply_text(
            "❓ <b>Uso:</b> /grant_team [user_id]\n\n"
            "<b>Ejemplo:</b> /grant_team 123456789",
            parse_mode=ParseMode.HTML
        )
        return
    
    try:
        target_id = int(context.args[0])
        storage.update_user(target_id, {'is_team': True})
        
        target = storage.get_user(target_id)
        name = target.get('first_name', 'Usuario')
        
        await update.message.reply_text(
            f"✅ <b>{name}</b> (ID: {target_id}) añadido!\n\n"
            f"👥 Acceso completo activado",
            parse_mode=ParseMode.HTML
        )
        
        logger.info(f"✅ User {target_id} → equipo por {user_id}")
        
    except ValueError:
        await update.message.reply_text("❌ ID inválido")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /clear - Limpia historial de conversación"""
    user_id = update.effective_user.id
    
    if user_id in conversation_memory:
        msg_count = len(conversation_memory[user_id])
        conversation_memory[user_id] = []
        await update.message.reply_text(
            f"🧹 <b>Historial limpio</b>\n\n"
            f"Se borraron {msg_count} mensajes.\n"
            f"Puedes empezar una nueva conversación.",
            parse_mode=ParseMode.HTML
        )
    else:
        await update.message.reply_text(
            "ℹ️ No hay historial que limpiar.\n\n"
            "Tu conversación ya está vacía."
        )

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
        await update.message.reply_text(
            "💬 <b>Modo consulta</b>\n\n"
            "Escribe tu pregunta\n\n"
            "<b>Ejemplos:</b>\n"
            "¿Qué es DVAG?\n"
            "Fondos Generali",
            parse_mode=ParseMode.HTML
        )
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
            
            await send_long_message(update.message, response)
            
        except Exception as e:
            logger.error(f"Error handle: {e}")
            await update.message.reply_text(f"😔 Error: {str(e)}")

async def send_long_message(message, text: str):
    max_length = 4000
    
    if len(text) <= max_length:
        await message.reply_text(text, parse_mode=ParseMode.HTML)
    else:
        parts = [text[i:i+max_length] for i in range(0, len(text), max_length)]
        for i, part in enumerate(parts):
            if i > 0:
                await asyncio.sleep(0.5)
            await message.reply_text(part, parse_mode=ParseMode.HTML)

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
    application.add_handler(CommandHandler("ask", ask_command))
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
    logger.info(f"🤖 AI: Gemini + RAG")
    logger.info(f"📚 Docs: {docs_loaded}")
    logger.info(f"📊 Chunks: {collection.count() if collection else 0}")
    logger.info(f"🗄️ DB: {'PostgreSQL ✅' if engine else 'JSON ✅'}")
    logger.info("👥 Listo para equipo Oscar Casco")
    logger.info("=" * 60)
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
