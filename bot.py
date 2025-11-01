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
# Flask (para Replit/UptimeRobot)
# ==============================
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot corriendo ✅"

def run_flask():
    app.run(host="0.0.0.0", port=8080)

# ==============================
# Utilidades
# ==============================
def limpiar_chiste(texto: str) -> str:
    texto = re.sub(r'<\s*p\s*>', '', str(texto), flags=re.IGNORECASE)
    texto = re.sub(r'<\s*/\s*p\s*>', '\n\n', texto, flags=re.IGNORECASE)
    texto = re.sub(r'<\s*br\s*/?\s*>', '\n', texto, flags=re.IGNORECASE)
    texto = re.sub(r'</?(?!b|i|u|code|br)\w+.*?>', '', texto)
    return texto.strip()

def cargar_mensajes():
    try:
        with open(os.path.join("mjsDelDia", "mjeDiario.json"), "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return None

def seleccionar_mensaje(categoria):
    mensajes = cargar_mensajes()
    if not mensajes or categoria not in mensajes["categorias"]:
        return None
    opciones_disponibles = [m for m in mensajes["categorias"][categoria] if m not in mensajes_enviados]
    if opciones_disponibles:
        mensaje = random.choice(opciones_disponibles)
        mensajes_enviados.add(mensaje)
        return mensaje
    return None

async def enviar_mensaje_diario(update: Update):
    mensajes = cargar_mensajes()
    if not mensajes:
        return
    categoria = random.choice(list(mensajes["categorias"].keys()))
    mensaje = seleccionar_mensaje(categoria)
    if mensaje:
        texto = f"El Mensaje {categoria.capitalize()} del día: {mensaje}"
        if update.message:
            await update.message.reply_text(texto)
        elif update.callback_query:
            await update.callback_query.edit_message_text(texto)

def cargar_categorias():
    return sorted([f.replace(".json","") for f in os.listdir(CHISTES_DIR) if f.endswith(".json")])

def cargar_chistes(categoria):
    ruta = os.path.join(CHISTES_DIR, f"{categoria}.json")
    try:
        data = json.load(open(ruta, encoding="utf-8"))
        if isinstance(data, dict) and "jokes" in data:
            chistes = data["jokes"]
        elif isinstance(data, list):
            chistes = data
        else:
            return []
        return [limpiar_chiste(c) for c in chistes if isinstance(c,str)]
    except:
        return []

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
        [InlineKeyboardButton("🖼 Meme", callback_data="meme")],
        [InlineKeyboardButton("🎮 Juegos", callback_data="juegos_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    if update.message:
        await update.message.reply_text(f"👋 Soy <b>{BOT_NAME}</b>\nVersión: {VERSION}", parse_mode="HTML", reply_markup=reply_markup)
    elif update.callback_query:
        await update.callback_query.edit_message_text(f"👋 Soy <b>{BOT_NAME}</b>\nVersión: {VERSION}", parse_mode="HTML", reply_markup=reply_markup)
    await enviar_mensaje_diario(update)

# ==============================
# Función de botones central
# ==============================
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    await query.answer()

    if data == "help":
        await query.edit_message_text(
            "ℹ️ Ayuda\n/start - Menú principal\n/chistes - Submenú chistes\n/meme - Meme aleatorio\nJuegos - Mini juegos"
        )
    elif data == "rules":
        await query.edit_message_text(
            "📜 Reglas del grupo:\n1️⃣ Respeta a los demás\n2️⃣ Nada de spam\n3️⃣ Usa el humor con responsabilidad\n4️⃣ Disfruta y comparte memes"
        )
    elif data == "meme":
        meme_url = await obtener_meme()
        if meme_url:
            await query.edit_message_text("Aquí está tu meme: " + meme_url)
        else:
            await query.edit_message_text("⚠ No pude obtener un meme ahora mismo.")
    elif data == "chistes_menu":
        categorias = cargar_categorias()
        keyboard = [[InlineKeyboardButton(cat.capitalize(), callback_data=f"ch_{cat}")] for cat in categorias[:10]]
        keyboard.append([InlineKeyboardButton("🏠 Home", callback_data="help")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("📂 Categorías de chistes:", reply_markup=reply_markup)
    elif data.startswith("ch_"):
        cat = data.split("_",1)[1]
        chistes = cargar_chistes(cat)
        if not chistes:
            await query.edit_message_text(f"No hay chistes en {cat}")
        else:
            await query.edit_message_text(f"😂 {random.choice(chistes)}")
    elif data == "juegos_menu":
        keyboard = [
            [InlineKeyboardButton("❓ Trivia", callback_data="trivia_aleatoria")],
            [InlineKeyboardButton("🏠 Home", callback_data="help")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("🎮 Menú de juegos:", reply_markup=reply_markup)
    elif data == "trivia_aleatoria":
        cat, preg = elegir_pregunta()
        if preg:
            opciones = preg["opciones"]
            keyboard = [[InlineKeyboardButton(opt, callback_data=f"trivia_{opt}")] for opt in opciones]
            keyboard.append([InlineKeyboardButton("🏠 Home", callback_data="help")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(f"❓ Trivia ({cat}): {preg['pregunta']}", reply_markup=reply_markup)
    elif data.startswith("trivia_"):
        opcion = data.split("_",1)[1]
        await query.edit_message_text(f"Tu respuesta fue: {opcion}\n✅ Respuesta registrada.")

# ==============================
# Main
# ==============================
def main():
    if not TOKEN:
        print("❌ ERROR: Falta TOKEN en variables de entorno")
        return

    threading.Thread(target=run_flask).start()  # Flask en paralelo

    app_telegram = Application.builder().token(TOKEN).build()
    app_telegram.add_handler(CommandHandler("start", start))
    app_telegram.add_handler(CallbackQueryHandler(button))

    print(f"✅ {BOT_NAME} corriendo... | Versión: {VERSION}")
    app_telegram.run_polling()

if __name__ == "__main__":
    main()
