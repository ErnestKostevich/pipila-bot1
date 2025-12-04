#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🤖 PIPILA v10.0 - FULLY FIXED
✅ Fixed SQL text() wrapper
✅ Webhook reset on start
✅ Proper error handling
"""
import os
import sys
import json
import logging
import asyncio
import httpx
from datetime import datetime
from typing import List, Dict
from pathlib import Path

from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters, CallbackQueryHandler
from telegram.constants import ParseMode
import google.generativeai as genai
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, Text, BigInteger, text
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

if not BOT_TOKEN:
    logger.error("❌ BOT_TOKEN not found!")
    sys.exit(1)
if not GEMINI_API_KEY:
    logger.error("❌ GEMINI_API_KEY not found!")
    sys.exit(1)

# ============================================================================
# RESET WEBHOOK - CRITICAL FOR 409 ERROR
# ============================================================================
def reset_telegram_webhook():
    """Reset webhook to fix 409 Conflict error"""
    logger.info("🔄 Resetting Telegram webhook...")
    try:
        import urllib.request
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook?drop_pending_updates=true"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as response:
            result = response.read().decode('utf-8')
            logger.info(f"✅ Webhook reset: {result}")
            return True
    except Exception as e:
        logger.error(f"⚠️ Webhook reset failed: {e}")
        return False

# Reset webhook IMMEDIATELY on startup
reset_telegram_webhook()

logger.info(f"📊 DATABASE_URL: {'Set ✅' if DATABASE_URL else 'Not set ❌'}")

# ============================================================================
# TRANSLATIONS (compact)
# ============================================================================
TRANSLATIONS = {
    'es': {
        'welcome': "🤖 <b>¡Hola, {name}!</b>\nSoy <b>PIPILA</b>, Asistente del <b>equipo de Oscar Casco</b>.\n\n<b>Comandos:</b> /search, /docs, /stats, /lang, /help\n\n<b>👨‍💼 Creado por:</b> @{creator}",
        'help': "📚 <b>COMANDOS</b>\n\n/search [pregunta] - Buscar\n/docs - Ver documentos\n/stats - Estadísticas\n/lang - Cambiar idioma\n/clear - Limpiar historial",
        'docs': "📚 <b>DOCUMENTOS</b>\nChunks en RAG: <b>{count}</b>",
        'stats': "📊 <b>ESTADÍSTICAS</b>\n\n👤 {name} (@{username})\n📈 Consultas: <b>{queries}</b>\n📚 Docs: {docs} chunks\n⏱️ Uptime: {uptime}\n🗄️ DB: {db}",
        'team': "👥 <b>EQUIPO</b>\nTotal: {count}\n\n{members}",
        'info': "🤖 <b>PIPILA v10.0</b>\n\nDev: @Ernest_Kostevich\nCliente: Oscar Casco",
        'error': "😔 Error: {error}",
        'processing_file': "📄 Procesando...",
        'no_query': "❓ Uso: /search [consulta]",
        'reloading': "🔄 Recargando...",
        'reloaded': "✅ Docs: {docs}, Chunks: {chunks}",
        'lang_changed': "✅ Idioma: 🇪🇸 Español",
        'choose_lang': "🌍 <b>Idioma:</b>",
        'cleared': "🧹 ¡Limpio!",
        'admin_only': "❌ Solo admin",
        'team_only': "⚠️ Solo equipo",
        'user_added': "✅ Usuario {id} añadido",
        'file_processed': "✅ {filename}\n\n{response}",
        'file_error': "❌ Error: {error}",
        'keyboard': {'consult': '💬 Consultar', 'docs': '📚 Docs', 'stats': '📊 Stats', 'team': '👥 Equipo', 'info': 'ℹ️ Info', 'help': '❓ Ayuda'}
    },
    'de': {
        'welcome': "🤖 <b>Hallo, {name}!</b>\nIch bin <b>PIPILA</b>, Assistent des <b>Teams von Oscar Casco</b>.\n\n<b>Befehle:</b> /search, /docs, /stats, /lang, /help\n\n<b>👨‍💼 Erstellt von:</b> @{creator}",
        'help': "📚 <b>BEFEHLE</b>\n\n/search [Frage] - Suchen\n/docs - Dokumente\n/stats - Statistiken\n/lang - Sprache\n/clear - Löschen",
        'docs': "📚 <b>DOKUMENTE</b>\nChunks in RAG: <b>{count}</b>",
        'stats': "📊 <b>STATISTIKEN</b>\n\n👤 {name} (@{username})\n📈 Anfragen: <b>{queries}</b>\n📚 Docs: {docs} Chunks\n⏱️ Uptime: {uptime}\n🗄️ DB: {db}",
        'team': "👥 <b>TEAM</b>\nGesamt: {count}\n\n{members}",
        'info': "🤖 <b>PIPILA v10.0</b>\n\nDev: @Ernest_Kostevich\nKunde: Oscar Casco",
        'error': "😔 Fehler: {error}",
        'processing_file': "📄 Verarbeite...",
        'no_query': "❓ Verwendung: /search [Anfrage]",
        'reloading': "🔄 Lade neu...",
        'reloaded': "✅ Docs: {docs}, Chunks: {chunks}",
        'lang_changed': "✅ Sprache: 🇩🇪 Deutsch",
        'choose_lang': "🌍 <b>Sprache:</b>",
        'cleared': "🧹 Gelöscht!",
        'admin_only': "❌ Nur Admin",
        'team_only': "⚠️ Nur Team",
        'user_added': "✅ Benutzer {id} hinzugefügt",
        'file_processed': "✅ {filename}\n\n{response}",
        'file_error': "❌ Fehler: {error}",
        'keyboard': {'consult': '💬 Anfragen', 'docs': '📚 Docs', 'stats': '📊 Stats', 'team': '👥 Team', 'info': 'ℹ️ Info', 'help': '❓ Hilfe'}
    }
}

def get_text(lang, key, **kw):
    t = TRANSLATIONS.get(lang, TRANSLATIONS['es']).get(key, key)
    return t.format(**kw) if kw else t

def detect_language(text):
    t = text.lower()
    de = sum(1 for w in ['was','wie','wo','ist','sind','haben','bitte','danke'] if w in t)
    es = sum(1 for w in ['qué','cómo','dónde','es','son','tener','gracias'] if w in t)
    return 'de' if de > es else 'es'

# ============================================================================
# GEMINI AI
# ============================================================================
genai.configure(api_key=GEMINI_API_KEY)
gen_cfg = {"temperature": 0.7, "top_p": 0.95, "top_k": 40, "max_output_tokens": 1024}
safety = [{"category": c, "threshold": "BLOCK_NONE"} for c in ["HARM_CATEGORY_HARASSMENT","HARM_CATEGORY_HATE_SPEECH","HARM_CATEGORY_SEXUALLY_EXPLICIT","HARM_CATEGORY_DANGEROUS_CONTENT"]]
SYS = {
    'es': "Eres PIPILA, Asistente Financiero. Responde en español, máx 300 palabras. Áreas: DVAG, Generali, Badenia, Advocard.",
    'de': "Du bist PIPILA, Finanzassistent. Antworte auf Deutsch, max 300 Wörter. Bereiche: DVAG, Generali, Badenia, Advocard."
}
model = genai.GenerativeModel('gemini-2.5-flash-preview-05-20', generation_config=gen_cfg, safety_settings=safety)
logger.info("✅ Gemini configured")

chat_sessions = {}
user_languages = {}

def get_chat(uid, lang='es'):
    if uid not in chat_sessions:
        m = genai.GenerativeModel('gemini-2.5-flash-preview-05-20', generation_config=gen_cfg, safety_settings=safety, system_instruction=SYS[lang])
        chat_sessions[uid] = m.start_chat(history=[])
    return chat_sessions[uid]

def clear_chat(uid): chat_sessions.pop(uid, None)
def get_lang(uid): return user_languages.get(uid, 'es')
def set_lang(uid, lang): user_languages[uid] = lang; clear_chat(uid)

async def gen_response(query, uid=None, docs=None):
    try:
        lang = get_lang(uid) if uid else 'es'
        chat = get_chat(uid, lang) if uid else model.start_chat(history=[])
        if docs:
            ctx = "\n\n".join([f"📄 {d['source']}: {d['text'][:500]}" for d in docs])
            prompt = f"DOCS:\n{ctx}\n\nQ: {query}\n\nResponde citando docs."
        else:
            prompt = f"Q: {query}\n\nNo docs. Responde según conocimiento."
        for _ in range(3):
            try:
                return chat.send_message(prompt).text
            except Exception as e:
                logger.error(f"Gemini err: {e}")
                await asyncio.sleep(2)
        return get_text(lang, 'error', error="AI fail")
    except Exception as e:
        return get_text('es', 'error', error=str(e)[:100])

async def proc_file(data, fname, query="", uid=None):
    try:
        lang = get_lang(uid) if uid else 'es'
        ext = Path(fname).suffix.lower()
        tmp = f"/tmp/{fname}"
        with open(tmp, 'wb') as f: f.write(data)
        txt = ""
        if ext == '.pdf': txt = extract_pdf(tmp)
        elif ext in ['.docx','.doc']: txt = extract_docx(tmp)
        elif ext == '.txt': txt = data.decode('utf-8', errors='ignore')
        os.remove(tmp)
        if not txt or len(txt) < 10: return get_text(lang, 'file_error', error="No text")
        chat = get_chat(uid, lang)
        return chat.send_message(f"FILE: {fname}\n{txt[:3000]}\n\n{f'Q: {query}' if query else 'Resume.'}").text
    except Exception as e:
        return get_text('es', 'file_error', error=str(e)[:100])

# ============================================================================
# CHROMADB
# ============================================================================
chroma_client = None
collection = None

def init_chroma():
    global chroma_client, collection
    try:
        chroma_client = chromadb.PersistentClient(path="./chroma_db")
        collection = chroma_client.get_or_create_collection(name="pipila_docs", metadata={"hnsw:space": "cosine"})
        logger.info(f"✅ ChromaDB: {collection.count()} chunks")
        return True
    except Exception as e:
        logger.error(f"❌ ChromaDB: {e}")
        return False

def extract_pdf(p):
    try:
        with open(p, 'rb') as f:
            r = PyPDF2.PdfReader(f)
            return "\n".join([pg.extract_text() or "" for pg in r.pages])
    except: return ""

def extract_docx(p):
    try:
        d = docx.Document(p)
        return "\n".join([para.text for para in d.paragraphs if para.text])
    except: return ""

def chunk_text(txt, sz=1000, ov=200):
    if not txt or len(txt) < 100: return []
    chunks, start = [], 0
    while start < len(txt):
        chunks.append(txt[start:start+sz].strip())
        start += sz - ov
    return [c for c in chunks if c]

def load_docs(folder=DOCUMENTS_FOLDER):
    if not collection:
        logger.error("ChromaDB not init")
        return 0
    if not os.path.exists(folder):
        logger.warning(f"Folder not found: {folder}")
        return 0
    loaded, total = 0, 0
    for f in os.listdir(folder):
        p = os.path.join(folder, f)
        ext = Path(f).suffix.lower()
        if ext not in ['.pdf','.docx','.doc','.txt']: continue
        try:
            if os.path.getsize(p) > 10*1024*1024: continue
            txt = ""
            if ext == '.pdf': txt = extract_pdf(p)
            elif ext in ['.docx','.doc']: txt = extract_docx(p)
            elif ext == '.txt':
                with open(p, 'r', encoding='utf-8', errors='ignore') as fl: txt = fl.read()
            if not txt or len(txt) < 100: continue
            chunks = chunk_text(txt)
            if not chunks: continue
            for i, c in enumerate(chunks):
                try: collection.add(documents=[c], ids=[f"{f}_{i}_{hash(c)%10000}"], metadatas=[{"source": f, "chunk": i}])
                except: pass
            loaded += 1
            total += len(chunks)
            logger.info(f"✅ {f}: {len(chunks)} chunks")
        except Exception as e:
            logger.error(f"Err {f}: {e}")
    logger.info(f"📚 Loaded: {loaded} docs, {total} chunks")
    return loaded

def search_rag(q, n=3):
    if not collection or collection.count() == 0: return []
    try:
        r = collection.query(query_texts=[q], n_results=n)
        if r['documents'] and r['documents'][0]:
            return [{'text': d, 'source': r['metadatas'][0][i].get('source', '?')} for i, d in enumerate(r['documents'][0])]
    except: pass
    return []

# ============================================================================
# DATABASE - FIXED
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

def init_db():
    global engine, Session
    if not DATABASE_URL:
        logger.warning("⚠️ No DATABASE_URL")
        return False
    try:
        engine = create_engine(DATABASE_URL, echo=False, pool_pre_ping=True)
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        # ✅ FIXED: Use text() wrapper for raw SQL
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("✅ PostgreSQL connected")
        return True
    except Exception as e:
        logger.error(f"❌ DB error: {e}")
        engine = None
        Session = None
        return False

# ============================================================================
# STORAGE
# ============================================================================
class Storage:
    def __init__(self):
        self.users = {} if engine else self._load()
    
    def _load(self):
        try:
            if os.path.exists('users.json'):
                with open('users.json') as f: return {int(k): v for k,v in json.load(f).items()}
        except: pass
        return {}
    
    def _save(self):
        if engine: return
        try:
            with open('users.json', 'w') as f: json.dump(self.users, f)
        except: pass
    
    def get_user(self, uid):
        if engine and Session:
            s = Session()
            try:
                u = s.query(User).filter_by(id=uid).first()
                if not u:
                    u = User(id=uid)
                    s.add(u)
                    s.commit()
                if u.language: user_languages[uid] = u.language
                return {'id': u.id, 'username': u.username or '', 'first_name': u.first_name or '', 'is_team': u.is_team, 'language': u.language or 'es', 'query_count': u.query_count or 0}
            except: s.rollback()
            finally: s.close()
        if uid not in self.users:
            self.users[uid] = {'id': uid, 'username': '', 'first_name': '', 'is_team': False, 'language': 'es', 'query_count': 0}
            self._save()
        return self.users[uid]
    
    def update_user(self, uid, data):
        if engine and Session:
            s = Session()
            try:
                u = s.query(User).filter_by(id=uid).first()
                if not u:
                    u = User(id=uid)
                    s.add(u)
                for k,v in data.items(): setattr(u, k, v)
                u.last_active = datetime.now()
                s.commit()
                if 'language' in data: user_languages[uid] = data['language']
            except: s.rollback()
            finally: s.close()
        else:
            u = self.get_user(uid)
            u.update(data)
            if 'language' in data: user_languages[uid] = data['language']
            self._save()
    
    def is_team(self, uid):
        if uid == CREATOR_ID: return True
        return self.get_user(uid).get('is_team', False)
    
    def save_query(self, uid, q, r):
        if not engine or not Session: return
        s = Session()
        try:
            s.add(QueryLog(user_id=uid, query=q[:1000], response=r[:1000]))
            s.commit()
        except: s.rollback()
        finally: s.close()
    
    def get_team(self):
        if engine and Session:
            s = Session()
            try:
                return [{'id': u.id, 'username': u.username, 'first_name': u.first_name, 'query_count': u.query_count} for u in s.query(User).filter_by(is_team=True).all()]
            except: return []
            finally: s.close()
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

def is_creator(uid): return uid == CREATOR_ID

def get_kb(lang='es'):
    kb = TRANSLATIONS[lang]['keyboard']
    return ReplyKeyboardMarkup([[KeyboardButton(kb['consult']), KeyboardButton(kb['docs'])], [KeyboardButton(kb['stats']), KeyboardButton(kb['team'])], [KeyboardButton(kb['info']), KeyboardButton(kb['help'])]], resize_keyboard=True)

# ============================================================================
# COMMANDS
# ============================================================================
async def cmd_start(upd, ctx):
    u = upd.effective_user
    identify_creator(u)
    d = storage.get_user(u.id)
    lang = d.get('language', 'es')
    storage.update_user(u.id, {'username': u.username or '', 'first_name': u.first_name or ''})
    await upd.message.reply_text(get_text(lang, 'welcome', name=u.first_name, creator=CREATOR_USERNAME), parse_mode=ParseMode.HTML, reply_markup=get_kb(lang))

async def cmd_help(upd, ctx):
    lang = get_lang(upd.effective_user.id)
    t = get_text(lang, 'help')
    if is_creator(upd.effective_user.id): t += "\n\n<b>Admin:</b> /grant_team [ID], /reload"
    await upd.message.reply_text(t, parse_mode=ParseMode.HTML)

async def cmd_lang(upd, ctx):
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("🇪🇸 ES", callback_data="lang_es"), InlineKeyboardButton("🇩🇪 DE", callback_data="lang_de")]])
    await upd.message.reply_text(get_text(get_lang(upd.effective_user.id), 'choose_lang'), parse_mode=ParseMode.HTML, reply_markup=kb)

async def cb_lang(upd, ctx):
    q = upd.callback_query
    await q.answer()
    lang = q.data.split('_')[1]
    set_lang(q.from_user.id, lang)
    storage.update_user(q.from_user.id, {'language': lang})
    await q.edit_message_text(get_text(lang, 'lang_changed'), parse_mode=ParseMode.HTML)
    await q.message.reply_text("✅", reply_markup=get_kb(lang))

async def cmd_search(upd, ctx):
    uid = upd.effective_user.id
    lang = get_lang(uid)
    if not ctx.args:
        await upd.message.reply_text(get_text(lang, 'no_query'))
        return
    q = ' '.join(ctx.args)
    await upd.message.chat.send_action("typing")
    docs = search_rag(q)
    r = await gen_response(q, uid, docs)
    storage.save_query(uid, q, r)
    u = storage.get_user(uid)
    storage.update_user(uid, {'query_count': u.get('query_count', 0) + 1})
    await upd.message.reply_text(f"🔍 <b>{q}</b>\n\n{r}", parse_mode=ParseMode.HTML)

async def cmd_docs(upd, ctx):
    lang = get_lang(upd.effective_user.id)
    await upd.message.reply_text(get_text(lang, 'docs', count=collection.count() if collection else 0), parse_mode=ParseMode.HTML)

async def cmd_stats(upd, ctx):
    uid = upd.effective_user.id
    lang = get_lang(uid)
    u = storage.get_user(uid)
    up = datetime.now() - BOT_START_TIME
    await upd.message.reply_text(get_text(lang, 'stats', name=u.get('first_name','?'), username=u.get('username','?'), queries=u.get('query_count',0), docs=collection.count() if collection else 0, uptime=f"{up.days}d {up.seconds//3600}h", db="PostgreSQL ✅" if engine else "JSON"), parse_mode=ParseMode.HTML)

async def cmd_team(upd, ctx):
    uid = upd.effective_user.id
    lang = get_lang(uid)
    if not storage.is_team(uid):
        await upd.message.reply_text(get_text(lang, 'team_only'))
        return
    team = storage.get_team()
    if not team:
        await upd.message.reply_text("👥 Empty")
        return
    members = "\n".join([f"• <b>{m.get('first_name','?')}</b> (@{m.get('username','?')})" for m in team])
    await upd.message.reply_text(get_text(lang, 'team', count=len(team), members=members), parse_mode=ParseMode.HTML)

async def cmd_info(upd, ctx):
    await upd.message.reply_text(get_text(get_lang(upd.effective_user.id), 'info'), parse_mode=ParseMode.HTML)

async def cmd_reload(upd, ctx):
    uid = upd.effective_user.id
    lang = get_lang(uid)
    if not is_creator(uid):
        await upd.message.reply_text(get_text(lang, 'admin_only'))
        return
    msg = await upd.message.reply_text(get_text(lang, 'reloading'))
    docs = load_docs()
    await msg.edit_text(get_text(lang, 'reloaded', docs=docs, chunks=collection.count() if collection else 0), parse_mode=ParseMode.HTML)

async def cmd_grant(upd, ctx):
    uid = upd.effective_user.id
    lang = get_lang(uid)
    if not is_creator(uid):
        await upd.message.reply_text(get_text(lang, 'admin_only'))
        return
    if not ctx.args:
        await upd.message.reply_text("❓ /grant_team [id]")
        return
    try:
        target = int(ctx.args[0])
        storage.update_user(target, {'is_team': True})
        await upd.message.reply_text(get_text(lang, 'user_added', id=target))
    except:
        await upd.message.reply_text("❌ Invalid ID")

async def cmd_clear(upd, ctx):
    uid = upd.effective_user.id
    clear_chat(uid)
    await upd.message.reply_text(get_text(get_lang(uid), 'cleared'))

# ============================================================================
# MESSAGE HANDLERS
# ============================================================================
async def handle_doc(upd, ctx):
    u = upd.effective_user
    identify_creator(u)
    lang = get_lang(u.id)
    doc = upd.message.document
    ext = Path(doc.file_name).suffix.lower()
    if ext not in ['.pdf','.docx','.doc','.txt']:
        await upd.message.reply_text("⚠️ PDF/DOCX/TXT only")
        return
    await upd.message.chat.send_action("typing")
    await upd.message.reply_text(get_text(lang, 'processing_file'))
    try:
        f = await ctx.bot.get_file(doc.file_id)
        data = await f.download_as_bytearray()
        r = await proc_file(bytes(data), doc.file_name, upd.message.caption or "", u.id)
        storage.save_query(u.id, f"[FILE: {doc.file_name}]", r)
        usr = storage.get_user(u.id)
        storage.update_user(u.id, {'query_count': usr.get('query_count', 0) + 1})
        await upd.message.reply_text(get_text(lang, 'file_processed', filename=doc.file_name, response=r), parse_mode=ParseMode.HTML)
    except Exception as e:
        await upd.message.reply_text(get_text(lang, 'file_error', error=str(e)[:100]))

async def handle_msg(upd, ctx):
    u = upd.effective_user
    identify_creator(u)
    txt = upd.message.text
    det = detect_language(txt)
    cur = get_lang(u.id)
    if det != cur:
        set_lang(u.id, det)
        storage.update_user(u.id, {'language': det})
        cur = det
    kb = TRANSLATIONS[cur]['keyboard']
    if txt == kb['consult']: await upd.message.reply_text("💬 Escribe tu pregunta"); return
    elif txt == kb['docs']: await cmd_docs(upd, ctx); return
    elif txt == kb['stats']: await cmd_stats(upd, ctx); return
    elif txt == kb['team']: await cmd_team(upd, ctx); return
    elif txt == kb['info']: await cmd_info(upd, ctx); return
    elif txt == kb['help']: await cmd_help(upd, ctx); return
    if txt and not txt.startswith('/'):
        await upd.message.chat.send_action("typing")
        docs = search_rag(txt)
        r = await gen_response(txt, u.id, docs)
        storage.save_query(u.id, txt, r)
        usr = storage.get_user(u.id)
        storage.update_user(u.id, {'query_count': usr.get('query_count', 0) + 1})
        await upd.message.reply_text(r, parse_mode=ParseMode.HTML)

# ============================================================================
# BACKGROUND LOADING
# ============================================================================
async def load_bg():
    logger.info("📚 Background loading...")
    await asyncio.sleep(5)
    try:
        c = load_docs()
        logger.info(f"✅ Loaded: {c} docs, {collection.count() if collection else 0} chunks")
    except Exception as e:
        logger.error(f"❌ Load error: {e}")

# ============================================================================
# MAIN
# ============================================================================
def main():
    global storage
    
    logger.info("=" * 50)
    logger.info("🤖 PIPILA v10.0 - FULLY FIXED")
    logger.info("=" * 50)
    
    init_db()
    init_chroma()
    storage = Storage()
    
    if os.path.exists(DOCUMENTS_FOLDER):
        files = list(Path(DOCUMENTS_FOLDER).glob("*"))
        logger.info(f"📂 Documents: {len(files)} files")
    else:
        logger.warning("⚠️ No documents folder")
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("lang", cmd_lang))
    app.add_handler(CallbackQueryHandler(cb_lang, pattern="^lang_"))
    app.add_handler(CommandHandler("search", cmd_search))
    app.add_handler(CommandHandler("docs", cmd_docs))
    app.add_handler(CommandHandler("stats", cmd_stats))
    app.add_handler(CommandHandler("team", cmd_team))
    app.add_handler(CommandHandler("info", cmd_info))
    app.add_handler(CommandHandler("reload", cmd_reload))
    app.add_handler(CommandHandler("grant_team", cmd_grant))
    app.add_handler(CommandHandler("clear", cmd_clear))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_doc))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_msg))
    
    async def post_init(a): asyncio.create_task(load_bg())
    app.post_init = post_init
    
    logger.info("=" * 50)
    logger.info(f"✅ Ready | DB: {'PostgreSQL' if engine else 'JSON'} | RAG: {collection.count() if collection else 0}")
    logger.info("=" * 50)
    
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

if __name__ == '__main__':
    main()

