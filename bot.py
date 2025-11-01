import os
import json
import random
import re
import aiohttp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from flask import Flask
from threading import Thread

# ==============================
# Configuración
# ==============================
TOKEN = os.getenv("TOKEN")
BOT_NAME = "ChumelitoBot"
VERSION = "vFinal-01Nov2025"  # Actualizada
CHISTES_DIR = "chistes"
JUEGOS_DIR = "juegos"

mensajes_enviados = set()
trivia_estado = {}  # {chat_id: {"categoria":..., "pregunta":..., "intentos":..., "tipo":"aleatorio/categoria"}}

# ==============================
# Flask para mantener activo el bot
# ==============================
app = Flask('')

@app.route('/')
def home():
    return "Bot despierto 😎"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# ==============================
# Funciones del bot
# ==============================
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
    categorias = list(cargar_mensajes()["categorias"].keys())
    categoria = random.choice(categorias)
    mensaje = seleccionar_mensaje(categoria)
    if mensaje:
        texto = f"El Mensaje {categoria.capitalize()} del día: {mensaje}"
        await update.message.reply_text(texto)

def limpiar_chiste(texto: str) -> str:
    if not isinstance(texto, str):
        texto = str(texto)
    texto = re.sub(r'<\s*p\s*>', '', texto, flags=re.IGNORECASE)
    texto = re.sub(r'<\s*/\s*p\s*>', '\n\n', texto, flags=re.IGNORECASE)
    texto = re.sub(r'<\s*br\s*/?\s*>', '\n', texto, flags=re.IGNORECASE)
    texto = re.sub(r'</?(?!b|i|u|code|br)\w+.*?>', '', texto)
    return texto.strip()

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

# ==============================
# Comandos y botones
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

# Aquí irían todas las demás funciones de comandos y callback buttons de tu bot
# (chistes_menu, enviar_chiste, juegos_menu, trivia_menu, button, etc.)
# Las dejamos igual que tu código original para no romper nada

# ==============================
# Main
# ==============================
def main():
    if not TOKEN:
        print("❌ ERROR: Falta TOKEN en variables de entorno")
        return

    keep_alive()  # Inicia el servidor Flask para mantener activo

    app_telegram = Application.builder().token(TOKEN).build()

    # Comandos
    app_telegram.add_handler(CommandHandler("start", start))
    # ... añade los demás comandos como en tu bot original

    # Botones
    app_telegram.add_handler(CallbackQueryHandler(button))

    print(f"✅ {BOT_NAME} corriendo... | Versión: {VERSION}")
    app_telegram.run_polling()

if __name__ == "__main__":
    main()
