import os
import json
import random
import re
import aiohttp
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import threading

# ==============================
# Configuración
# ==============================
TOKEN = os.getenv("TOKEN")
BOT_NAME = "ChumelitoBot"
VERSION = "vFinal-30Sep2025"
CHISTES_DIR = "chistes"
JUEGOS_DIR = "juegos"

mensajes_enviados = set()
trivia_estado = {}  # {chat_id: {"categoria":..., "pregunta":..., "intentos":..., "tipo":"aleatorio/categoria"}}

# ==============================
# Flask para mantener vivo el bot
# ==============================
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot corriendo ✅"

def run_flask():
    app.run(host="0.0.0.0", port=8080)

# ==============================
# Funciones auxiliares
# ==============================
def limpiar_chiste(texto: str) -> str:
    texto = re.sub(r'<\s*p\s*>', '', texto, flags=re.IGNORECASE)
    texto = re.sub(r'<\s*/\s*p\s*>', '\n\n', texto, flags=re.IGNORECASE)
    texto = re.sub(r'<\s*br\s*/?\s*>', '\n', texto, flags=re.IGNORECASE)
    texto = re.sub(r'</?(?!b|i|u|code|br)\w+.*?>', '', texto)
    return texto.strip()

def cargar_chistes(categoria):
    ruta = os.path.join(CHISTES_DIR, f"{categoria}.json")
    try:
        with open(ruta, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict) and "jokes" in data:
                chistes = data["jokes"]
            elif isinstance(data, list):
                chistes = data
            else:
                return []
            return [limpiar_chiste(c) for c in chistes if isinstance(c, str)]
    except:
        return []

def cargar_categorias():
    return sorted([f.replace(".json", "") for f in os.listdir(CHISTES_DIR) if f.endswith(".json")])

async def obtener_meme():
    url = "https://meme-api.com/gimme"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data.get("url")
            return None

def cargar_trivia():
    ruta = os.path.join(JUEGOS_DIR, "trivia.json")
    try:
        return json.load(open(ruta, encoding="utf-8"))["categorias"]
    except:
        return {}

def elegir_pregunta(categoria=None):
    categorias_trivia = list(cargar_trivia().keys())
    if not categorias_trivia:
        return None, None
    if not categoria:
        categoria = random.choice(categorias_trivia)
    pregunta = random.choice(cargar_trivia()[categoria])
    return categoria, pregunta

# ==============================
# Comandos
# ==============================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📖 Ayuda", callback_data="help")],
        [InlineKeyboardButton("📜 Reglas", callback_data="rules")],
        [InlineKeyboardButton("🤣 Chistes", callback_data="chistes_menu")],
        [InlineKeyboardButton("🖼️ Meme", callback_data="meme")],
        [InlineKeyboardButton("🎮 Juegos", callback_data="juegos_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        f"👋 Soy <b>{BOT_NAME}</b>\nVersión: {VERSION}\nSelecciona una opción:",
        parse_mode="HTML",
        reply_markup=reply_markup,
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = "ℹ️ Ayuda:\n/start - Inicio\n/chistes - Chistes\n/meme - Meme\nJuegos disponibles con botones."
    await update.message.reply_text(texto)

async def rules_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = "📜 Reglas:\n1. Respeto\n2. Sin spam\n3. Humor responsable"
    await update.message.reply_text(texto)

async def meme_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    meme = await obtener_meme()
    if meme:
        await update.message.reply_photo(meme)
    else:
        await update.message.reply_text("⚠ No pude obtener un meme.")

# ==============================
# Botones
# ==============================
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "help":
        await help_command(update, context)
    elif data == "rules":
        await rules_command(update, context)
    elif data == "meme":
        meme = await obtener_meme()
        if meme:
            await query.edit_message_media(media={"type": "photo", "media": meme})
        else:
            await query.edit_message_text("⚠ No pude obtener un meme.")
    elif data == "chistes_menu":
        categorias = cargar_categorias()
        botones = [[InlineKeyboardButton(c, callback_data=f"cat_{c}") ] for c in categorias]
        botones.append([InlineKeyboardButton("🏠 Home", callback_data="help")])
        await query.edit_message_text("📂 Elige categoría de chistes:", reply_markup=InlineKeyboardMarkup(botones))
    elif data.startswith("cat_"):
        categoria = data.split("_", 1)[1]
        chistes = cargar_chistes(categoria)
        if chistes:
            chiste = random.choice(chistes)
            await query.edit_message_text(f"😂 {chiste}")
        else:
            await query.edit_message_text("⚠ No hay chistes en esta categoría.")

# ==============================
# Main
# ==============================
def main():
    if not TOKEN:
        print("❌ ERROR: Falta TOKEN en variables de entorno")
        return

    # Iniciar Flask en hilo paralelo
    threading.Thread(target=run_flask).start()

    app_telegram = Application.builder().token(TOKEN).build()

    # Comandos
    app_telegram.add_handler(CommandHandler("start", start))
    app_telegram.add_handler(CommandHandler("help", help_command))
    app_telegram.add_handler(CommandHandler("reglas", rules_command))
    app_telegram.add_handler(CommandHandler("meme", meme_command))

    # Botones
    app_telegram.add_handler(CallbackQueryHandler(button))

    print(f"✅ {BOT_NAME} corriendo... | Versión: {VERSION}")
    app_telegram.run_polling()

if __name__ == "__main__":
    main()
