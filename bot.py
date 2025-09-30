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
VERSION = "vFinal-30Sep2025"
CHISTES_DIR = "chistes"
JUEGOS_DIR = "juegos"

mensajes_enviados = set()
trivia_estado = {}  # {chat_id: {"categoria":..., "pregunta":..., "intentos":..., "tipo":"aleatorio/categoria"}}

# ==============================
# Cargar Mensajes
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

# ==============================
# Enviar mensaje diario (temporal)
# ==============================
async def enviar_mensaje_diario(update: Update):
    categorias = list(cargar_mensajes()["categorias"].keys())
    categoria = random.choice(categorias)
    mensaje = seleccionar_mensaje(categoria)
    if mensaje:
        texto = f"El Mensaje {categoria.capitalize()} del día: {mensaje}"
        await update.message.reply_text(texto)

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
    # Temporal: mensaje diario en /start
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

# ==============================
# Submenú de juegos
# ==============================
async def juegos_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("❓ Trivia", callback_data="trivia_menu")],
        [InlineKeyboardButton("🏠 Home", callback_data="help")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    if update.message:
        await update.message.reply_text("🎮 Submenú de juegos:", reply_markup=reply_markup)
    else:
        await update.callback_query.edit_message_text("🎮 Submenú de juegos:", reply_markup=reply_markup)

# ==============================
# Trivia
# ==============================
async def trivia_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🎲 Aleatorio", callback_data="trivia_aleatorio")],
        [InlineKeyboardButton("📂 Por categoría", callback_data="trivia_categorias_0")],
        [InlineKeyboardButton("🏠 Home", callback_data="help")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.edit_message_text("❓ Elige cómo jugar la trivia:", reply_markup=reply_markup)

def elegir_pregunta(categoria=None):
    categorias_trivia = list(cargar_trivia().keys())
    if not categorias_trivia:
        return None, None
    if not categoria:
        categoria = random.choice(categorias_trivia)
    pregunta = random.choice(cargar_trivia()[categoria])
    return categoria, pregunta

async def mostrar_pregunta(update: Update, categoria, pregunta, tipo):
    chat_id = update.effective_chat.id
    trivia_estado[chat_id] = {"categoria": categoria, "pregunta": pregunta, "intentos": 2, "tipo": tipo}

    opciones = pregunta["opciones"]
    keyboard = [[InlineKeyboardButton(opt, callback_data=f"trivia_resp_{opt}")] for opt in opciones]
    keyboard.append([InlineKeyboardButton("🏠 Home", callback_data="help")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    texto = f"🎲 Trivia ({categoria.capitalize()}):\n{pregunta['pregunta']}\nTienes 2 intentos"
    await update.callback_query.edit_message_text(texto, reply_markup=reply_markup)

async def trivia_respuesta(update: Update, context: ContextTypes.DEFAULT_TYPE, opcion):
    chat_id = update.effective_chat.id
    estado = trivia_estado.get(chat_id)
    if not estado:
        await update.callback_query.edit_message_text("⚠ No hay trivia iniciada. Inicia desde el menú de juegos.")
        return

    correcta = estado["pregunta"]["respuesta"]
    estado["intentos"] -= 1
    if opcion == correcta:
        texto = f"✅ Correcto! La respuesta es {correcta}."
        trivia_estado.pop(chat_id)
    elif estado["intentos"] > 0:
        await update.callback_query.answer(f"❌ Incorrecto! Te quedan {estado['intentos']} intentos.", show_alert=True)
        return
    else:
        texto = f"❌ Incorrecto! La respuesta correcta era {correcta}."
        trivia_estado.pop(chat_id)

    # Submenú para continuar
    keyboard = [
        [InlineKeyboardButton("🎲 Otra pregunta aleatoria", callback_data="trivia_aleatorio")],
        [InlineKeyboardButton("📂 Elegir categoría", callback_data="trivia_categorias_0")],
        [InlineKeyboardButton("🏠 Home", callback_data="help")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.edit_message_text(texto + "\n\nPuedes elegir otra pregunta o volver al menú de trivia.", reply_markup=reply_markup)

async def trivia_categorias(update: Update, context: ContextTypes.DEFAULT_TYPE, page=0):
    categorias = list(cargar_trivia().keys())
    if not categorias:
        await update.callback_query.edit_message_text("⚠ No hay categorías disponibles.")
        return
    items_por_pagina = 5
    inicio = page * items_por_pagina
    fin = inicio + items_por_pagina
    categorias_pagina = categorias[inicio:fin]

    keyboard = [[InlineKeyboardButton(cat.capitalize(), callback_data=f"trivia_cat_{cat}")] for cat in categorias_pagina]
    nav_buttons = []
    if inicio > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Atrás", callback_data=f"trivia_categorias_{page-1}"))
    if fin < len(categorias):
        nav_buttons.append(InlineKeyboardButton("➡️ Siguiente", callback_data=f"trivia_categorias_{page+1}"))
    nav_buttons.append(InlineKeyboardButton("🏠 Home", callback_data="help"))
    keyboard.append(nav_buttons)

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.edit_message_text("📂 Elige una categoría de trivia:", reply_markup=reply_markup)

# ==============================
# Callback de botones
# ==============================
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    # --- Menú principal ---
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
    elif data == "juegos_menu":
        await juegos_menu(update, context)
    elif data == "trivia_menu":
        await trivia_menu(update, context)
    elif data == "trivia_aleatorio":
        categoria, pregunta = elegir_pregunta()
        await mostrar_pregunta(update, categoria, pregunta, tipo="aleatorio")
    elif data.startswith("trivia_resp_"):
        opcion = data.split("_", 2)[2]
        await trivia_respuesta(update, context, opcion)
    elif data.startswith("trivia_categorias_"):
        page = int(data.split("_")[-1])
        await trivia_categorias(update, context, page)
    elif data.startswith("trivia_cat_"):
        categoria = data.split("_", 2)[2]
        categoria, pregunta = elegir_pregunta(categoria)
        await mostrar_pregunta(update, categoria, pregunta, tipo="categoria")

# ==============================
# Mostrar categorías de chistes
# ==============================
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
    await update.callback_query.edit_message_text("📂 Elige una categoría de chistes:", reply_markup=reply_markup)

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
