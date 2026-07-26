# main.py
import os
import logging
import asyncio
import random
from datetime import datetime
from flask import Flask
from threading import Thread
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, CommandHandler, CallbackQueryHandler, filters
from huggingface_hub import InferenceClient

logging.basicConfig(level=logging.INFO)

app = Flask('')

@app.route('/')
def home():
    return "Bot is alive!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# Render Environment Variable မှ Owner IDs များကို ဖတ်ယူခြင်း
owner_env = os.environ.get("OWNER_IDS", "")
OWNER_IDS = [int(uid.strip()) for uid in owner_env.split(",") if uid.strip().isdigit()]

# Database အတွက် ယာယီ သိမ်းဆည်းရန်
call_settings_db = {}

def get_call_settings(chat_id: int):
    if chat_id not in call_settings_db:
        call_settings_db[chat_id] = {
            "language": "🇲🇲",
            "call_count": 5,
            "who_can_call": "admin",
            "use_emoji": True
        }
    return call_settings_db[chat_id]

def update_call_settings(chat_id: int, key: str, value):
    if chat_id not in call_settings_db:
        get_call_settings(chat_id)
    call_settings_db[chat_id][key] = value

CALL_EMOJIS = [
    "😀", "😬", "😁", "😂", "😃", "😄", "😅", "😇", "😉", "😊",
    "🙂", "🙃", "☺", "😋", "😌", "😍", "🥰", "😘", "😗", "😙",
    "😚", "😜", "🤣", "🥳", "🤩", "😎", "🤓", "🤑", "😛", "🤪",
    "😝", "🤗", "🤭", "🤫", "😏", "😶", "😐", "😑", "😒", "🤨",
    "🙄", "🤔", "🧐", "😳", "🥺", "🤤", "🤥", "😕", "😔", "🤯",
    "🤬", "😡", "😠", "😟", "😞", "🤧", "🙁", "☹", "😣", "😖",
    "😫", "😩", "😤", "😮", "😱", "😨", "😥", "😪", "😓", "😭",
    "😵", "😲", "🤐", "😷", "👿", "😈", "💩", "💤", "🥱", "😴",
    "🤕", "🤒", "🤢", "🤮", "🥴", "🥵", "🥶", "🤠", "👹", "🤡",
    "👺", "💀", "☠", "👻", "👽", "🤖", "👾", "😺", "😾", "😿",
    "🙀", "😽", "😼", "😻", "😹", "😸", "👏", "👋", "👍", "👎",
    "👊", "✊", "✌", "🖖", "🤚", "✋", "🤏", "👌", "🤞", "🤛",
    "🤜", "👐", "🤲", "🤝", "💪", "🙏", "☝", "🤌", "👆", "🤘",
    "🤙", "🤟", "🖐", "🖕", "👉", "👈", "👇", "🦾", "🦿", "🦵",
    "🦶", "✍", "💅", "🤳", "👄", "👀", "👁", "🧠", "👃", "🦻",
    "👂", "👅", "🦷", "👤", "👥", "🗣", "👶", "👦", "👧", "👨🏻",
    "🧔", "👩🏿", "👩🏾", "👩🏽", "👩🏼", "👩🏻", "👨🏾", "👨🏽", "👨🏼", "🤵",
    "👼", "🤴", "👸", "👰", "🎅", "🤶", "👷", "🐶", "🐱", "🐭",
    "🐹", "🐰", "🐻", "🐼", "🐨", "🐵", "🐙", "🐸", "🐽", "🐷",
    "🐮", "🦁", "🐯", "🙈", "🙉", "🙊", "🐒", "🐔", "🐧", "🐦",
    "🐤", "🦇", "🦄", "🐴", "🐗", "🦊", "🐺", "🐥", "🐣", "🐝",
    "🦋", "🐛", "🐌", "🐞", "🐜", "🕷", "🦗", "🐟", "🐠", "🐢",
    "🐍", "🦎", "🦀", "🦂", "🦟", "🍏", "🍎", "🍐", "🍊", "🥭",
    "🥥", "🧅", "🥦", "🍆", "🍈", "🍖", "🧈", "🍞", "🏀", "🏈",
    "🎾", "🏉", "🏸", "🏹", "🪁", "🥌", "🕴", "🚒", "🚐", "🦼",
    "🛴", "🚝", "🚆", "🖲", "☎", "📡", "💴", "🩸", "😯", "😦", "😧"
]

LANGUAGES = {
    "🇲🇲": "Myanmar", "🇯🇵": "Japanese", "🇮🇳": "Hindi",
    "🇵🇰": "Urdu", "🇰🇭": "Khmer", "🇰🇵": "Korean",
    "🇱🇨": "Chinese", "🇱🇮": "Lao", "🇱🇰": "Sinhala",
    "🇱🇷": "Liberia", "🇱🇸": "Lesotho", "🇱🇹": "Lithuanian",
    "🇱🇺": "Luxembourgish", "🇱🇻": "Latvian", "🇲🇰": "Macedonian",
    "🇲🇱": "Malian", "🇲🇳": "Mongolian", "🇲🇴": "Macanese",
    "🇲🇵": "Northern Mariana", "🇲🇷": "Mauritanian", "🇲🇿": "Mozambique",
    "🇲🇽": "Spanish", "🇲🇼": "Malawi", "🇲🇻": "Dhivehi",
    "🇲🇺": "Mauritian", "🇲🇹": "Maltese", "🇲🇸": "Montserrat",
    "🇳🇦": "Namibian", "🇳🇮": "Nicaraguan", "🇳🇱": "Dutch",
    "🇳🇴": "Norwegian", "🇵🇫": "French Polynesian", "🇵🇪": "Peruvian",
    "🇵🇦": "Panamanian", "🇴🇲": "Omani", "🇳🇿": "New Zealand",
    "🇳🇺": "Niuean", "🇳🇷": "Nauruan", "🇦🇩": "Andorran", "🇨🇳": "Chinese"
}

# Hugging Face Client
hf_token = os.environ.get("HF_TOKEN")
client = InferenceClient(api_key=hf_token) if hf_token else None

async def get_ai_response(text):
    if not client:
        return "⚠️ HF_TOKEN ကို Environment Variables ထဲတွင် ထည့်သွင်းထားခြင်း မရှိပါ။"
    try:
        response = client.chat.completions.create(
            model="meta-llama/Llama-3.1-8B-Instruct",
            messages=[{"role": "user", "content": text}],
            max_tokens=500
        )
        return response.choices[0].message.content
    except Exception as e:
        logging.error(f"HF Error: {e}")
        return None

bad_words = ["စောက်", "လိုး", "ခွေး", "ေခွေး", "fuck", "shit", "bitch"]
user_locks = {}

# Admin ဟုတ်မဟုတ် စစ်ဆေးရန်
async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    
    if user_id in OWNER_IDS:
        return True
    
    try:
        admins = await context.bot.get_chat_administrators(chat_id)
        for admin in admins:
            if admin.user.id == user_id:
                return True
    except:
        pass
    
    return False

# /start Command (ပရိုဖိုင်ပုံ နှင့် ခလုတ်များပါဝင်သော မက်ဆေ့ခ်ျ)
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat_id = update.effective_chat.id
    
    welcome_text = (
        f"✨ *မင်္ဂလာပါ* {user.first_name} ရေ... 👋\n\n"
        f"ကျွန်ုပ်သည် Hugging Face AI ဖြင့် ချိတ်ဆက်ထားသော AI လက်ထောက် Bot ဖြစ်ပါသည်။\n\n"
        f"🛠 *သင်၏ အချက်အလက်များ:*\n"
        f"• *အမည်:* {user.full_name}\n"
        f"• *User ID:* `{user.id}`\n"
        f"• *Username:* @{user.username if user.username else 'မရှိပါ'}\n\n"
        f"💬 _သိလိုသည်များကို လွတ်လပ်စွာ မေးမြန်းနိုင်ပါပြီ။_"
    )
    
    keyboard = [
        [InlineKeyboardButton("⚙️ လူခေါ်စနစ် ဆက်တင်များသို့ သွားရန်", callback_data="open_call_settings")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    try:
        photos = await context.bot.get_user_profile_photos(user.id, limit=1)
        if photos.total_count > 0:
            photo_file_id = photos.photos[0][-1].file_id
            await context.bot.send_photo(
                chat_id=chat_id,
                photo=photo_file_id,
                caption=welcome_text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')
    except Exception as e:
        logging.error(f"Profile photo error: {e}")
        await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')

# လူခေါ်သည့် စနစ် (/call)
async def call_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = update.effective_user
    message = update.message
    
    if update.effective_chat.type == "private":
        await message.reply_text("⚠️ ဤအမိန့်ကို Group များတွင်သာ အသုံးပြုနိုင်ပါသည်။")
        return

    settings = get_call_settings(chat_id)
    who_can_call = settings['who_can_call']
    
    if who_can_call == 'admin':
        if not (await is_admin(update, context)):
            await message.reply_text("❌ တောင်းပန်ပါတယ်ရှင့်... သင့်မှာခွင့်ပြုချက်မရှိပါ")
            return
    elif who_can_call == 'owner':
        if user.id not in OWNER_IDS:
            await message.reply_text("❌ တောင်းပန်ပါတယ်ရှင့်... သင့်မှာခွင့်ပြုချက်မရှိပါ")
            return
    
    call_text = " ".join(context.args) if context.args else "အားလုံးကိုခေါ်ဆိုပါတယ်"
    
    try:
        admins = await context.bot.get_chat_administrators(chat_id)
        members = [admin.user for admin in admins if admin.user.username]
    except:
        members = []
    
    if not members:
        await message.reply_text("❌ ခေါ်ဆိုရန် အဖွဲ့ဝင်မရှိပါ")
        return
    
    await message.reply_text(f"🔊 မဂ်လာပါရှင့် 0.2ms နဲစတင်ခေါ်ဆိုပေးနေပါပီရှင့်")
    
    emoji_list = [CALL_EMOJIS[i % len(CALL_EMOJIS)] for i in range(len(members))]
    random.shuffle(emoji_list)
    
    sent_count = 0
    use_emoji = settings['use_emoji']
    call_count_per_message = settings['call_count']
    message_buffer = []
    
    for i, member in enumerate(members):
        username = f"@{member.username}"
        emoji = emoji_list[i]
        mention = f"{emoji} [{username}](tg://user?id={member.id})" if use_emoji else username
        
        message_buffer.append(mention)
        
        if len(message_buffer) >= call_count_per_message:
            full_text = "\n".join(message_buffer) + f"\n\n{call_text}"
            await context.bot.send_message(chat_id, full_text, parse_mode="Markdown")
            message_buffer = []
            await asyncio.sleep(0.2)
        
        sent_count += 1
    
    if message_buffer:
        full_text = "\n".join(message_buffer) + f"\n\n{call_text}"
        await context.bot.send_message(chat_id, full_text, parse_mode="Markdown")
    
    await context.bot.send_message(
        chat_id,
        f"\n━━━━━━━━━━━━━━━━\n👤 By @Tear808\n📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    )
    
    await message.reply_text(f"✅ ခေါ်ဆိုမှုပြီးဆုံးပါပြီ။ လူ {sent_count} ယောက်ကိုခေါ်ဆိုခဲ့ပါတယ်")

# Settings Menu (/callset)
async def call_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    settings = get_call_settings(chat_id)
    
    keyboard = [
        [InlineKeyboardButton(f"🌍 ဘာသာစကား ({settings['language']})", callback_data="call_lang")],
        [InlineKeyboardButton(f"👥 ခေါ်ဆိုလူဉီးရေ ({settings['call_count']})", callback_data="call_count")],
        [InlineKeyboardButton(f"🔑 ခေါ်ဆိုနိုင်သူ ({settings['who_can_call']})", callback_data="call_who")],
        [InlineKeyboardButton(f"🎭 Emoji / Link", callback_data="call_emoji")],
        [InlineKeyboardButton("❌ Delete", callback_data="call_delete")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.edit_message_text("⚙️ **Call Settings Menu**", reply_markup=reply_markup)
    else:
        await update.message.reply_text("⚙️ **Call Settings Menu**", reply_markup=reply_markup)

async def call_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    chat_id = query.message.chat.id
    
    if data == "open_call_settings":
        if query.message.chat.type == "private":
            await query.edit_message_text("⚠️ ဤဆက်တင်များကို Group များအတွင်းတွင်သာ ပြင်ဆင်အသုံးပြုနိုင်ပါသည်။ (သို့မဟုတ် /callset ကို Group ထဲတွင် သုံးပါ)")
        else:
            await call_settings(update, context)
        return

    if data == "call_lang":
        keyboard = []
        row = []
        for i, (flag, name) in enumerate(LANGUAGES.items(), 1):
            row.append(InlineKeyboardButton(f"{flag} {name}", callback_data=f"lang_{flag}"))
            if i % 3 == 0:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)
        keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="call_back")])
        await query.edit_message_text("🌍 ဘာသာစကားရွေးပါ:", reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif data.startswith("lang_"):
        lang = data.replace("lang_", "")
        update_call_settings(chat_id, "language", lang)
        await query.edit_message_text(f"✅ ဘာသာစကား {LANGUAGES.get(lang, lang)} သတ်မှတ်ပြီးပါပြီ")
    
    elif data == "call_count":
        keyboard = [
            [InlineKeyboardButton("👥 ၃ယောက်", callback_data="count_3")],
            [InlineKeyboardButton("👥 ၅ယောက်", callback_data="count_5")],
            [InlineKeyboardButton("👥 ၇ယောက်", callback_data="count_7")],
            [InlineKeyboardButton("🔙 Back", callback_data="call_back")]
        ]
        await query.edit_message_text("👥 ခေါ်ဆိုလူဉီးရေ ရွေးပါ:", reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif data.startswith("count_"):
        count = int(data.replace("count_", ""))
        update_call_settings(chat_id, "call_count", count)
        await query.edit_message_text(f"✅ လူ {count} ယောက်သတ်မှတ်ပြီးပါပြီ")
    
    elif data == "call_who":
        keyboard = [
            [InlineKeyboardButton("👑 Admin", callback_data="who_admin")],
            [InlineKeyboardButton("👤 Owner", callback_data="who_owner")],
            [InlineKeyboardButton("👥 All", callback_data="who_all")],
            [InlineKeyboardButton("🔙 Back", callback_data="call_back")]
        ]
        await query.edit_message_text("🔑 ခေါ်ဆိုနိုင်သူ ရွေးပါ:", reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif data.startswith("who_"):
        who = data.replace("who_", "")
        update_call_settings(chat_id, "who_can_call", who)
        await query.edit_message_text(f"✅ {who} သတ်မှတ်ပြီးပါပြီ")
    
    elif data == "call_emoji":
        settings = get_call_settings(chat_id)
        current = "Emoji" if settings['use_emoji'] else "Link"
        keyboard = [
            [InlineKeyboardButton(f"🎭 Emoji", callback_data="emoji_on")],
            [InlineKeyboardButton(f"🔗 Link", callback_data="emoji_off")],
            [InlineKeyboardButton("🔙 Back", callback_data="call_back")]
        ]
        await query.edit_message_text(f"🎭 လက်ရှိ: {current}\n\nEmoji / Link ရွေးပါ:", reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif data == "emoji_on":
        update_call_settings(chat_id, "use_emoji", True)
        await query.edit_message_text("✅ Emoji mode သတ်မှတ်ပြီးပါပြီ")
    
    elif data == "emoji_off":
        update_call_settings(chat_id, "use_emoji", False)
        await query.edit_message_text("✅ Link mode သတ်မှတ်ပြီးပါပြီ")
    
    elif data == "call_delete":
        await query.edit_message_text("✅ Settings ဖျက်ပြီးပါပြီ")
    
    elif data == "call_back":
        await call_settings(update, context)

# AI Chat Handler (ဆဲဆိုမှုစစ်ဆေးခြင်း နှင့် AI အဖြေထုတ်ခြင်း)
async def chat_with_ai(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
        
    user_id = update.effective_user.id
    user_message = update.message.text

    if user_id not in user_locks:
        user_locks[user_id] = asyncio.Lock()

    async with user_locks[user_id]:
        msg_lower = user_message.lower()
        if any(word in msg_lower for word in bad_words):
            await update.message.reply_text("မင်းပါးစပ်ကို ပိတ်ထားစမ်း၊ လာမဆဲနဲ့! 😒")
            return

        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
        wait_message = await update.message.reply_text("⏳ _ခဏလေးနော်၊ AI စဉ်းစားနေပါတယ်..._", parse_mode='Markdown')
        
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
        ai_reply = await get_ai_response(user_message)
        
        if ai_reply:
            formatted_reply = f"🤖 *AI အဖြေ:*\n\n{ai_reply}"
            try:
                await wait_message.edit_text(formatted_reply, parse_mode='Markdown')
            except Exception:
                await wait_message.edit_text(ai_reply)
        else:
            await wait_message.edit_text("⚠️ _ဆောရီးဗျာ၊ အခုလောလောဆယ် AI နဲ့ ချိတ်ဆက်လို့မရပါ။_", parse_mode='Markdown')

if __name__ == '__main__':
    Thread(target=run_flask).start()

    TOKEN = os.environ.get("BOT_TOKEN")
    
    if TOKEN:
        application = ApplicationBuilder().token(TOKEN).build()
        
        # Command Handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("call", call_all))
        application.add_handler(CommandHandler("callset", call_settings))
        
        # Callback & Message Handlers
        application.add_handler(CallbackQueryHandler(call_button_handler))
        application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), chat_with_ai))
        
        logging.info("Bot started successfully with start button integration...")
        application.run_polling()
    else:
        logging.error("BOT_TOKEN missing in environment variables!")
