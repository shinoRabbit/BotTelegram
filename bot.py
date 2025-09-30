import os
import json
import random
import re
import aiohttp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# ==============================
# Configuración
# ==============================
TOKEN = os.getenv("TOKEN")
BOT_NAME = "ChumelitoBot"
VERSION = "vFinal-29Sep2025"
CHISTES_DIR = "chistes"

# ==============================
# Utilidades
# ==============================
def limpiar_chiste(texto: str) -> str:
    """Limpia HTML parcial para Telegram"""
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
            if isinstance(data, dict) and "jokes" in data and isinstance(data["jokes"], list):
                chistes = data["jokes"]
            elif isinstance(data, list):
                chistes = data
            else:
                print(f"⚠ {ruta} no tiene un formato válido")
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

# ==============================
# Comandos
# ==============================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📖 Ayuda", callback_data="help")],
        [InlineKeyboardButton("📜 Reglas", callback_data="rules")],
        [InlineKeyboardButton("🤣 Chistes", callback_data="chistes_menu")],
        [InlineKeyboardButton("🖼️ Meme", callback_data="meme")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        f"👋 Soy <b>{BOT_NAME}</b>\nVersión: {VERSION}\nSelecciona una opción:",
        parse_mode="HTML",
        reply_markup=reply_markup,
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = (
        "ℹ️ <b>Ayuda</b>\n\n"
        "👉 /start - Muestra el menú principal\n"
        "👉 /chistes - Submenú de chistes\n"
        "👉 /meme - Envía un meme aleatorio\n"
        "👉 /reglas - Muestra reglas del grupo\n"
        "También puedes navegar desde los botones del menú"
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

# ==============================
# Submenú de chistes
# ==============================
async def chistes_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🎲 Aleatorio", callback_data="chiste_aleatorio")],
        [InlineKeyboardButton("📂 Por categoría", callback_data="categorias_page_0")],
        [InlineKeyboardButton("🏠 Home", callback_data="help")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    if update.message:
        await update.message.reply_text("📂 Submenú de chistes:", reply_markup=reply_markup)
    else:
        await update.callback_query.edit_message_text("📂 Submenú de chistes:", reply_markup=reply_markup)

async def enviar_chiste(update: Update, context: ContextTypes.DEFAULT_TYPE, categoria=None):
    if categoria:
        chistes = cargar_chistes(categoria)
    else:
        categorias = cargar_categorias()
        categoria = random.choice(categorias) if categorias else None
        chistes = cargar_chistes(categoria) if categoria else []

    if not chistes:
        await update.callback_query.edit_message_text(f"⚠ No hay chistes en {categoria}")
        return

    chiste = random.choice(chistes)

    keyboard = [
        [InlineKeyboardButton("🔄 Otro", callback_data=f"cat_{categoria}")],
        [InlineKeyboardButton("🎲 Aleatorio", callback_data="chiste_aleatorio")],
        [InlineKeyboardButton("🏠 Home", callback_data="help")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.message:
        await update.message.reply_text(f"😂 {chiste}", parse_mode="HTML", reply_markup=reply_markup)
    else:
        await update.callback_query.edit_message_text(f"😂 {chiste}", parse_mode="HTML", reply_markup=reply_markup)

async def mostrar_categorias(update: Update, context: ContextTypes.DEFAULT_TYPE, page=0):
    categorias = cargar_categorias()
    if not categorias:
        await update.callback_query.edit_message_text("⚠ No hay categorías disponibles.")
        return

    items_por_pagina = 10
    inicio = page * items_por_pagina
    fin = inicio + items_por_pagina
    categorias_pagina = categorias[inicio:fin]

    keyboard = [[InlineKeyboardButton(cat.capitalize(), callback_data=f"cat_{cat}") ] for cat in categorias_pagina]

    nav_buttons = []
    if inicio > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Atrás", callback_data=f"categorias_page_{page-1}"))
    nav_buttons.append(InlineKeyboardButton("🏠 Home", callback_data="help"))
    if fin < len(categorias):
        nav_buttons.append(InlineKeyboardButton("➡️ Siguiente", callback_data=f"categorias_page_{page+1}"))
    if nav_buttons:
        keyboard.append(nav_buttons)

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.edit_message_text("📂 Elige una categoría:", reply_markup=reply_markup)

# ==============================
# Callback de botones
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
        meme_url = await obtener_meme()
        if meme_url:
            await query.edit_message_media(media={"type": "photo", "media": meme_url})
        else:
            await query.edit_message_text("⚠ No pude obtener un meme ahora mismo.")
    elif data == "chistes_menu":
        await chistes_menu(update, context)
    elif data == "chiste_aleatorio":
        await enviar_chiste(update, context)
    elif data.startswith("categorias_page_"):
        page = int(data.split("_")[-1])
        await mostrar_categorias(update, context, page)
    elif data.startswith("cat_"):
        categoria = data.split("_", 1)[1]
        await enviar_chiste(update, context, categoria=categoria)

# ==============================
# Main
# ==============================
def main():
    if not TOKEN:
        print("❌ ERROR: Falta TOKEN en variables de entorno")
        return

    app = Application.builder().token(TOKEN).build()

    # Comandos
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("reglas", rules_command))
    app.add_handler(CommandHandler("meme", meme_command))
    app.add_handler(CommandHandler("chistes", chistes_menu))

    # Botones
    app.add_handler(CallbackQueryHandler(button))

    print(f"✅ {BOT_NAME} corriendo... | Versión: {VERSION}")
    app.run_polling()

if __name__ == "__main__":
    main()
