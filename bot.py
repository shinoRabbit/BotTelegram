# bot.py
# 🤖 ChumelitoBot - Bot de Telegram
# Versión final - 28 Sep 2025

import os
import json
import random
import re
import aiohttp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

# ==============================
# Configuración
# ==============================
TOKEN = os.getenv("TOKEN")
BOT_NAME = "ChumelitoBot"
VERSION = "vFinal-28Sep2025"
CHISTES_DIR = "chistes"

# ==============================
# Utilidades
# ==============================
def limpiar_html(texto: str) -> str:
    """Limpia etiquetas HTML no permitidas, conserva <b>, <i>, <u>, <code>, <br>"""
    if not isinstance(texto, str):
        return str(texto)
    texto = re.sub(r"</?(?!b|i|u|code|br)\w+.*?>", "", texto)
    return texto.replace("<br/>", "\n").replace("<br>", "\n")

def cargar_categorias():
    """Carga los archivos .json en /chistes como categorías"""
    categorias = []
    for archivo in os.listdir(CHISTES_DIR):
        if archivo.endswith(".json"):
            categorias.append(archivo.replace(".json", ""))
    return sorted(categorias)

def cargar_chistes(categoria):
    """Carga los chistes de una categoría"""
    ruta = os.path.join(CHISTES_DIR, f"{categoria}.json")
    try:
        with open(ruta, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Puede ser dict con clave "chistes" o lista directa
            if isinstance(data, dict) and "chistes" in data:
                return data["chistes"]
            elif isinstance(data, list):
                return data
            else:
                print(f"⚠ {ruta} no tiene un formato válido")
                return []
    except Exception as e:
        print(f"❌ Error cargando {ruta}: {e}")
        return []

async def enviar_chiste(update: Update, context: ContextTypes.DEFAULT_TYPE, categoria: str):
    """Envía un chiste aleatorio de una categoría"""
    chistes = cargar_chistes(categoria)
    if not chistes:
        await update.callback_query.edit_message_text(f"⚠ No hay chistes en {categoria}")
        return

    chiste = random.choice(chistes)
    chiste = limpiar_html(chiste)

    await update.callback_query.edit_message_text(f"😂 {chiste}", parse_mode="HTML")

async def obtener_meme():
    """Obtiene un meme random desde API"""
    url = "https://meme-api.com/gimme"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data.get("url")
            return None

# ==============================
# Handlers principales
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
        "👉 /meme - Envía un meme aleatorio\n"
        "👉 /chiste - Muestra un chiste aleatorio\n"
        "👉 También puedes navegar desde el menú con botones"
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

async def chiste_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    categorias = cargar_categorias()
    if not categorias:
        await update.message.reply_text("⚠ No hay categorías de chistes disponibles.")
        return

    categoria = random.choice(categorias)
    chistes = cargar_chistes(categoria)
    if not chistes:
        await update.message.reply_text("⚠ No encontré chistes en esta categoría.")
        return

    chiste = random.choice(chistes)
    chiste = limpiar_html(chiste)

    await update.message.reply_text(f"😂 {chiste}", parse_mode="HTML")

# ==============================
# Menús y botones
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
            await query.edit_message_media(
                media={"type": "photo", "media": meme_url}
            )
        else:
            await query.edit_message_text("⚠ No pude obtener un meme ahora mismo.")

    elif data == "chistes_menu":
        await mostrar_menu_categorias(update, context, 0)

    elif data.startswith("cat_"):
        categoria = data.split("_", 1)[1]
        await enviar_chiste(update, context, categoria)

    elif data.startswith("page_"):
        page = int(data.split("_", 1)[1])
        await mostrar_menu_categorias(update, context, page)

async def mostrar_menu_categorias(update: Update, context: ContextTypes.DEFAULT_TYPE, page: int):
    categorias = cargar_categorias()
    if not categorias:
        await update.callback_query.edit_message_text("⚠ No hay categorías disponibles.")
        return

    items_por_pagina = 10
    inicio = page * items_por_pagina
    fin = inicio + items_por_pagina
    categorias_pagina = categorias[inicio:fin]

    keyboard = []
    for cat in categorias_pagina:
        keyboard.append([InlineKeyboardButton(cat.capitalize(), callback_data=f"cat_{cat}")])

    nav_buttons = []
    if inicio > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Atrás", callback_data=f"page_{page-1}"))
    nav_buttons.append(InlineKeyboardButton("🏠 Home", callback_data="help"))
    if fin < len(categorias):
        nav_buttons.append(InlineKeyboardButton("➡️ Siguiente", callback_data=f"page_{page+1}"))

    if nav_buttons:
        keyboard.append(nav_buttons)

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.edit_message_text("📂 Elige una categoría:", reply_markup=reply_markup)

# ==============================
# Main
# ==============================
def main():
    if not TOKEN:
        print("❌ ERROR: Falta TELEGRAM_TOKEN en variables de entorno")
        return

    app = Application.builder().token(TOKEN).build()

    # Comandos
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("rules", rules_command))
    app.add_handler(CommandHandler("meme", meme_command))
    app.add_handler(CommandHandler("chiste", chiste_command))

    # Botones
    app.add_handler(CallbackQueryHandler(button))

    print(f"✅ {BOT_NAME} corriendo... | Versión: {VERSION}")
    app.run_polling()

if __name__ == "__main__":
    main()
