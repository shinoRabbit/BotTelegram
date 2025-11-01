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
    if not isinstance(texto, str):
        texto = str(texto)
    texto = re.sub(r'<\s*p\s*>', '', texto, flags=re.IGNORECASE)
    texto = re.sub(r'<\s*/\s*p\s*>', '\n\n', texto, flags=re.IGNORECASE)
    texto = re.sub(r'<\s*br\s*/?\s*>', '\n', texto, flags=re.IGNORECASE)
    texto = re.sub(r'</?(?!b|i|u|code|br)\w+.*?>', '', texto)
    return texto.strip()

def cargar_mensajes():
    ruta = os.path.join("mjsDelDia", "mjeDiario.json")
    try:
        with open(ruta, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Error cargando {ruta}: {e}")
        return None

def seleccionar_mensaje(categoria):
    mensajes = cargar_mensajes()
    if not mensajes or categoria not in mensajes["categorias"]:
        return None
    opciones = mensajes["categorias"][categoria]
    opciones_disponibles = [m for m in opciones if m not in mensajes_enviados]
    if opciones_disponibles:
        mensaje = random.choice(opciones_disponibles)
        mensajes_enviados.add(mensaje)
        return mensaje
    return None

async def enviar_mensaje_diario(update: Update):
    mensajes = cargar_mensajes()
    if not mensajes:
        return
    categorias = list(mensajes["categorias"].keys())
    categoria = random.choice(categorias)
    mensaje = seleccionar_mensaje(categoria)
    if mensaje:
        texto = f"El Mensaje {categoria.capitalize()} del día: {mensaje}"
        await update.message.reply_text(texto)

def cargar_categorias():
    categorias = []
    for archivo in os.listdir(CHISTES_DIR):
        if archivo.endswith(".json"):
            categorias.append(archivo.replace(".json", ""))
    return sorted(categorias)

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
    except Exception as e:
        print(f"❌ Error cargando {ruta}: {e}")
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
    except Exception as e:
        print(f"❌ Error cargando {ruta}: {e}")
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
# Funciones de comandos y botones
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
    await enviar_mensaje_diario(update)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = (
        "ℹ️ <b>Ayuda</b>\n\n"
        "👉 /start - Menú principal\n"
        "👉 /chistes - Submenú de chistes\n"
        "👉 /meme - Envía un meme aleatorio\n"
        "👉 Juegos - Mini juegos como trivia\n"
        "También puedes navegar usando los botones del menú"
    )
    if update.message:
        await update.message.reply_text(texto, parse_mode="HTML")
    else:
        await update.callback_query.edit_message_text(texto, parse_mode="HTML")

async def rules_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = (
        "📜 <b>Reglas del grupo</b>\n\n"
        "1️⃣ Respeta a los demás miembros.\n"
        "2️⃣ Nada de spam ni publicidad.\n"
        "3️⃣ Usa el humor con responsabilidad.\n"
        "4️⃣ Disfruta y comparte memes y chistes 😄"
    )
    if update.message:
        await update.message.reply_text(texto, parse_mode="HTML")
    else:
        await update.callback_query.edit_message_text(texto, parse_mode="HTML")

async def meme_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    meme_url = await obtener_meme()
    if meme_url:
        await update.message.reply_photo(meme_url)
    else:
        await update.message.reply_text("⚠ No pude obtener un meme ahora mismo.")

# --- Aquí irían el resto de funciones para chistes, juegos y trivia ---
# Asegúrate de incluir todas las funciones que tenías definidas (ej. enviar_chiste, chistes_menu, juegos_menu, trivia_menu, mostrar_pregunta, trivia_respuesta, button, etc.)

# ==============================
# Main
# ==============================
def main():
    if not TOKEN:
        print("❌ ERROR: Falta TOKEN en variables de entorno")
        return

    # Inicia Flask en un hilo paralelo
    threading.Thread(target=run_flask).start()

    app_telegram = Application.builder().token(TOKEN).build()

    # Comandos
    app_telegram.add_handler(CommandHandler("start", start))
    app_telegram.add_handler(CommandHandler("help", help_command))
    app_telegram.add_handler(CommandHandler("reglas", rules_command))
    app_telegram.add_handler(CommandHandler("meme", meme_command))
    # ... agrega aquí los demás comandos si quieres mantenerlos
    app_telegram.add_handler(CallbackQueryHandler(button))  # button debe estar definido arriba

    print(f"✅ {BOT_NAME} corriendo... | Versión: {VERSION}")
    app_telegram.run_polling()

if __name__ == "__main__":
    main()
