import os
import logging
import asyncio
import random
from datetime import datetime, timedelta
from flask import Flask
from threading import Thread
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatPermissions
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, CommandHandler, CallbackQueryHandler, filters
from apscheduler.schedulers.background import BackgroundScheduler
from huggingface_hub import InferenceClient

logging.basicConfig(level=logging.INFO)

app = Flask('')

@app.route('/')
def home():
    return "Tear AI Assistant is alive and running!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

owner_env = os.environ.get("OWNER_IDS", "")
OWNER_IDS = [int(uid.strip()) for uid in owner_env.split(",") if uid.strip().isdigit()]

call_settings_db = {}
group_settings_db = {}
known_chats = set()
known_users = set()
broadcast_messages_db = []

BOT_USERNAME = "@Call_ai_love_bot"

LANGUAGES = {
    "🇲🇲": {
        "name": "Myanmar (MM)", 
        "start_call": "🔊 မင်္ဂလာပါရှင့်... အဖွဲ့ဝင်များကို စတင်ခေါ်ဆိုနေပါပြီ...", 
        "default_text": "အားလုံးကိုခေါ်ဆိုပါတယ်", 
        "finished": "✅ ခေါ်ဆိုမှုပြီးဆုံးပါပြီ။ လူ {count} ယောက်ကိုခေါ်ဆိုခဲ့ပါတယ်\nby @Tear808",
        "start_text": "✨ **မင်္ဂလာပါ** {name} ရေ...\n\nကျွန်ုပ်သည် Tear AI လက်ထောက် Bot ဖြစ်ပါသည်။ (@Call_ai_love_bot)",
        "settings_title": "⚙️ **Call Settings Menu**",
        "btn_lang": "🌍 ဘာသာစကား: 🇲🇲",
        "btn_count": "👥 ခေါ်ဆိုမည့် အရေအတွက်: ({count} ဦး)",
        "btn_who": "🔑 ခေါ်ဆိုနိုင်သူ: ({who})",
        "btn_mode": "🎭 မုဒ်: ({mode})",
        "btn_close": "❌ ပိတ်မည်",
        "btn_stop": "🛑 ရပ်ရန်",
        "btn_delete": "🗑️ ဖျက်မည်",
        "btn_back": "🔙 နောက်သို့",
        "btn_add_group": "➕ Group ထဲသို့ထည့်ရန်",
        "select_lang": "🌍 **ဘာသာစကား (နိုင်ငံအလံ) တစ်ခုကို ရွေးချယ်ပါ:**",
        "only_group": "⚠️ ဤအမိန့်ကို Group များတွင်သာ အသုံးပြုနိုင်ပါသည်။",
        "no_members": "❌ ခေါ်ဆိုရန် အဖွဲ့ဝင် မရှိပါ။",
        "admin_only": "❌ Admin များသာ အသုံးပြုနိုင်ပါသည်။",
        "owner_only": "❌ Owner များသာ ခေါ်ဆိုနိုင်ပါသည်။",
        "call_stopped": "🛑 Call ရပ်တန့်လိုက်ပါပြီ。"
    },
    "🇺🇸": {
        "name": "English (EN)", 
        "start_call": "🔊 Hello! Starting to call members...", 
        "default_text": "Calling everyone!", 
        "finished": "✅ Call finished. Called {count} members.\nby @Tear808",
        "start_text": "✨ **Hello** {name}...\n\nI am your Tear AI Assistant bot. (@Call_ai_love_bot)",
        "settings_title": "⚙️ **Call Settings Menu**",
        "btn_lang": "🌍 Language: 🇺🇸",
        "btn_count": "👥 Call Count: ({count})",
        "btn_who": "🔑 Who can call: ({who})",
        "btn_mode": "🎭 Mode: ({mode})",
        "btn_close": "❌ Close",
        "btn_stop": "🛑 Stop",
        "btn_delete": "🗑️ Delete",
        "btn_back": "🔙 Back",
        "btn_add_group": "➕ Add to Group",
        "select_lang": "🌍 **Select a language (flag):**",
        "only_group": "⚠️ This command can only be used in groups.",
        "no_members": "❌ No members found to call.",
        "admin_only": "❌ Only admins can use this.",
        "owner_only": "❌ Only owners can call.",
        "call_stopped": "🛑 Call has been stopped."
    }
}

for flag in ["🇨🇳", "🇯🇵", "🇰🇷", "🇹🇭", "🇫🇷", "🇩🇪", "🇪🇸", "🇷🇺", "🇮🇹", "🇵🇹", "🇻🇳", "🇮🇩", "🇮🇳", "🇸🇦", "🇹🇷", "🇵🇱", "🇳🇱", "🇺🇦"]:
    if flag not in LANGUAGES:
        LANGUAGES[flag] = LANGUAGES["🇺🇸"]

def get_call_settings(chat_id: int):
    if chat_id not in call_settings_db:
        call_settings_db[chat_id] = {
            "language": "🇲🇲",
            "call_count": 5,
            "who_can_call": "all",
            "call_mode": "emoji"
        }
    return call_settings_db[chat_id]

def get_group_settings(chat_id: int):
    if chat_id not in group_settings_db:
        group_settings_db[chat_id] = {
            "welcome_text": "✨ မင်္ဂလာပါရှင့်... {name} ရေ (@{username})၊ Group ထဲသို့ ကြိုဆိုပါတယ်ခင်ဗျာ။ (@Call_ai_love_bot)",
            "welcome_video": None,
            "goodbye_text": "👋 တာ့တာပါ {name} ရေ (@{username})၊ Group ကနေ ထွက်သွားပါပြီ။ (@Call_ai_love_bot)",
            "goodbye_video": None,
            "link_delete": True
        }
    return group_settings_db[chat_id]

CALL_EMOJIS = [
    "😀", "😃", "😄", "😁", "😆", "😅", "😂", "🤣", "😊", "😇", 
    "🙂", "🙃", "😉", "😌", "😍", "🥰", "😘", "😗", "😙", "😚", 
    "😋", "😛", "😝", "😜", "🤪", "🤨", "🧐", "🤓", "😎", "🤩", 
    "🥳", "😏", "😒", "😞", "😔", "😟", "😕", "🙁", "☹️", "😣", 
    "😖", "😫", "😩", "🥺", "😢", "😭", "😤", "😠", "😡", "🤬", 
    "🤯", "😳", "🥵", "🥶", "😱", "😨", "😰", "😥", "😓", "🤗", 
    "🤔", "🤭", "🤫", "🤥", "😶", "😐", "😑", "😬", "🙄", "😯", 
    "😦", "😧", "😮", "😲", "😴", "🤤", "😪", "😵", "🤐", "🥴", 
    "🤢", "🤮", "🤧", "😷", "🤒", "🤕", "🤑", "🤠", "😈", "👿", 
    "👹", "👺", "🤡", "💩", "👻", "💀", "☠️", "👽", "👾", "🤖", 
    "🎃", "😺", "😸", "😹", "😻", "😼", "😽", "🙀", "😿", "😾", 
    "👋", "🤚", "🖐️", "✋", "🖖", "👌", "🤌", "🤏", "✌️", "🤞", 
    "🫰", "🤟", "🤘", "🤙", "👈", "👉", "👆", "🖕", "👇", "☝️", 
    "👍", "👎", "✊", "👊", "🤛", "🤜", "👏", "🙌", "👐", "🤲", 
    "🤝", "🙏", "✍️", "💅", "🤳", "💪", "🦾", "🦿", "🦵", "🦶", 
    "👂", "🦻", "👃", "🫀", "🫁", "🧠", "🦷", "🦴", "👀", "👁️", 
    "👅", "👄", "💋", "🩸", "🍏", "🍎", "🍐", "🍊", "🍋", "🍌", 
    "🍉", "🍇", "🍓", "🫐", "🍈", "🍒", "🍑", "🥭", "🍍", "🥥", 
    "🥝", "🍅", "🍆", "🥑", "🥦", "🥬", "🥒", "🌶️", "🫑", "🌽", 
    "🥕", "🫒", "🧄", "🧅", "🥔", "🍠", "🥐", "🥯", "🍞", "🥖", 
    "🥨", "🧀", "🥚", "🍳", "🥞", "🧇", "🥓", "🥩", "🍗", "🍖", 
    "🌭", "🍔", "🍟", "🍕", "🥪", "🌮", "🌯", "🫔", "🥙", "🧆", 
    "🥘", "🍝", "🍜", "🍲", "🍛", "🍣", "🍱", "🥟", "🦪", "🍢", 
    "🍙", "🍚", "🍘", "🍥", "🥠", "🥮", "🍡", "🍧", "🍨", "🍦", 
    "🥧", "🧁", "🍰", "🎂", "🍮", "🍭", "🍬", "🍫", "🍿", "🍩", 
    "🍪", "🌰", "🥜", "🍯", "🥛", "🍼", "☕", "🍵", "🍶", "🍾", 
    "🍷", "🍸", "🍹", "🍺", "🍻", "🥂", "🥃", "🥤", "🧋", "🧃", 
    "🧉", "🧊", "🥢", "🍽️", "🍴", "🥄", "🔪", "🏺", "🌍", "🌎", 
    "🌏", "🌐", "🗺️", "🗾", "🧭", "🏔️", "⛰️", "🌋", "🗻", "🏕️", 
    "🏖️", "🏜️", "🏝️", "🏞️", "🏟️", "🏛️", "🏗️", "🧱", "🪨", "🪵", 
    "🛖", "🏘️", "🏚️", "🏠", "🏡", "🏢", "🏣", "🏤", "🏥", "🏦", 
    "🏨", "🏩", "🏪", "🏫", "🏬", "🏭", "🏯", "🏰", "💒", "🗼", 
    "🗽", "⛪", "🕌", "🛕", "🕍", "⛩️", "🕋", "⛲", "⛺", "🌁", 
    "🌃", "🏙️", "🌄", "🌅", "🌆", "🌇", "🌉", "♨️", "🎠", "🎡", 
    "🎢", "💈", "🎪", "🚂", "🚃", "🚄", "🚅", "🚆", "🚇", "🚊", 
    "🚝", "🚞", "🚋", "🚌", "🚍", "🚎", "🚐", "🚑", "🚒", "🚓", 
    "🚔", "🚕", "🚖", "🚗", "🚘", "🚙", "🚚", "🚛", "🚜", "🏎️", 
    "🏍️", "🛵", "🛺", "🚲", "🛴", "🛹", "🛼", "🚏", "🛣️", "🛤️", 
    "🛢️", "⛽", "🚨", "🚥", "🚦", "🛑", "🚧", "⚓", "⛵", "🛶", 
    "🚢", "✈️", "🛩️", "🛫", "🛬", "🪂", "💺", "🚁", "🚟", "🚠", 
    "🚡", "🛰️", "🚀", "🛸", "🛎️", "🧳", "⌛", "⏳", "⌚", "⏰", 
    "⏱️", "⏲️", "🕰️", "🌡️", "☀️", "🌝", "🌞", "🪐", "⭐", "🌟", 
    "🌠", "🌌", "☁️", "⛅", "⛈️", "🌤️", "🌥️", "🌦️", "🌧️", "🌨️", 
    "🌩️", "🌪️", "🌫️", "🌬️", "🌀", "🌈", "🌂", "☔", "⚡", "❄️", 
    "☃️", "⛄", "🔥", "💧", "🌊", "🎄", "🎆", "🎇", "🧨", "✨", 
    "🎈", "🎉", "🎊", "🎋", "🎍", "🎎", "🎏", "🎐", "🎑", "🧧", 
    "🎀", "🎁", "🏆", "🏅", "🥇", "🥈", "🥉", "⚽", "⚾", "🥎", 
    "🏀", "🏐", "🏈", "🏉", "🎾", "🥏", "🎳", "🏏", "🏑", "🏒", 
    "🥍", "🏸", "🥌", "🛷", "⛸️", "🥼", "🦺", "🪖", "🪡", "🧶", 
    "🥽", "🎽", "🥋", "🥊", "🤿"
]

hf_token = os.environ.get("HF_TOKEN")
client = InferenceClient(api_key=hf_token) if hf_token else None

async def track_chats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user
    if chat:
        known_chats.add(chat.id)
    if user and chat and chat.type == "private":
        known_users.add(user.id)

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

async def set_welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if update.effective_chat.type == "private":
        await update.message.reply_text("⚠️ ဤအမိန့်ကို Group များတွင်သာ အသုံးပြုနိုင်ပါသည်။")
        return
    if not await is_admin(update, context):
        await update.message.reply_text("❌ Admin များသာ အသုံးပြုနိုင်ပါသည်။")
        return
    
    settings = get_group_settings(chat_id)
    reply = update.message.reply_to_message
    
    if reply and reply.video:
        settings["welcome_video"] = reply.video.file_id
        await update.message.reply_text("✅ ဤ Group အတွက် Welcome ဗီဒီယိုကို သိမ်းဆည်းပြီးပါပြီ (@Call_ai_love_bot)။")
        return
        
    if context.args:
        new_text = " ".join(context.args)
        settings["welcome_text"] = f"{new_text} (@Call_ai_love_bot)"
        await update.message.reply_text(f"✅ Welcome စာသားအသစ်ကို သိမ်းဆည်းပြီးပါပြီ。\n\nပုံစံ - {settings['welcome_text']}")
    else:
        await update.message.reply_text("⚠️ ကျေးဇူးပြု၍ စာသားထည့်ပါ သို့မဟုတ် ဗီဒီယိုကို Reply လုပ်ပြီး /setwelcome ဟု ပို့ပါ။")

async def set_goodbye(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if update.effective_chat.type == "private":
        await update.message.reply_text("⚠️ ဤအမိန့်ကို Group များတွင်သာ အသုံးပြုနိုင်ပါသည်။")
        return
    if not await is_admin(update, context):
        await update.message.reply_text("❌ Admin များသာ အသုံးပြုနိုင်ပါသည်။")
        return
    
    settings = get_group_settings(chat_id)
    reply = update.message.reply_to_message
    
    if reply and reply.video:
        settings["goodbye_video"] = reply.video.file_id
        await update.message.reply_text("✅ ဤ Group အတွက် Goodbye ဗီဒီယိုကို သိမ်းဆည်းပြီးပါပြီ (@Call_ai_love_bot)။")
        return
        
    if context.args:
        new_text = " ".join(context.args)
        settings["goodbye_text"] = f"{new_text} (@Call_ai_love_bot)"
        await update.message.reply_text(f"✅ Goodbye စာသားအသစ်ကို သိမ်းဆည်းပြီးပါပြီ。\n\nပုံစံ - {settings['goodbye_text']}")
    else:
        await update.message.reply_text("⚠️ ကျေးဇူးပြု၍ စာသားထည့်ပါ သို့မဟုတ် ဗီဒီယိုကို Reply လုပ်ပြီး /setgoodbye ဟု ပို့ပါ။")

async def delete_video_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if update.effective_chat.type == "private":
        await update.message.reply_text("⚠️ ဤအမိန့်ကို Group များတွင်သာ အသုံးပြုနိုင်ပါသည်။")
        return
    if not await is_admin(update, context):
        await update.message.reply_text("❌ Admin များသာ အသုံးပြုနိုင်ပါသည်။")
        return
    
    settings = get_group_settings(chat_id)
    command = update.message.text.lower()
    
    if "/video1" in command:
        settings["welcome_video"] = None
        await update.message.reply_text("🗑️ ဤ Group ၏ ပထမကြိုဆိုဗီဒီယို (Welcome Video) ကို ဖြုတ်ချလိုက်ပါပြီ (@Call_ai_love_bot)။")
    elif "/video2" in command:
        settings["goodbye_video"] = None
        await update.message.reply_text("🗑️ ဤ Group ၏ နှုတ်ဆက်ဗီဒီယို (Goodbye Video) ကို ဖြုတ်ချလိုက်ပါပြီ (@Call_ai_love_bot)။")

async def welcome_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for member in update.message.new_chat_members:
        if member.id == context.bot.id:
            continue
        chat_id = update.effective_chat.id
        settings = get_group_settings(chat_id)
        name = member.first_name or "User"
        username = f"@{member.username}" if member.username else name
        
        caption = settings["welcome_text"].replace("{name}", name).replace("{username}", username)
        settings_call = get_call_settings(chat_id)
        texts = LANGUAGES.get(settings_call['language'], LANGUAGES["🇲🇲"])
        keyboard = [[InlineKeyboardButton(texts["btn_delete"], callback_data="delete_msg")]]
        
        try:
            if settings["welcome_video"]:
                await update.message.reply_video(video=settings["welcome_video"], caption=caption, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
            else:
                await update.message.reply_text(text=caption, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        except:
            pass

async def goodbye_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    member = update.message.left_chat_member
    if member and member.id != context.bot.id:
        chat_id = update.effective_chat.id
        settings = get_group_settings(chat_id)
        name = member.first_name or "User"
        username = f"@{member.username}" if member.username else name
        
        caption = settings["goodbye_text"].replace("{name}", name).replace("{username}", username)
        settings_call = get_call_settings(chat_id)
        texts = LANGUAGES.get(settings_call['language'], LANGUAGES["🇲🇲"])
        keyboard = [[InlineKeyboardButton(texts["btn_delete"], callback_data="delete_msg")]]
        
        try:
            if settings["goodbye_video"]:
                await context.bot.send_video(chat_id=chat_id, video=settings["goodbye_video"], caption=caption, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
            else:
                await context.bot.send_message(chat_id=chat_id, text=caption, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        except:
            pass

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await track_chats(update, context)
    message = update.message
    if not message:
        return
    chat = update.effective_chat
    user = update.effective_user
    text = message.text or message.caption or ""

    if chat.type in ["group", "supergroup"]:
        if "http://" in text or "https://" in text or "t.me/" in text or "www." in text:
            if user.id not in OWNER_IDS:
                try:
                    await message.delete()
                    return
                except:
                    pass

    if user and not user.is_bot:
        try:
            rc_emojis = ["👍", "❤️", "🔥", "✨", "👏", "🎉"]
            await context.bot.set_message_reaction(chat_id=chat.id, message_id=message.message_id, reaction=random.choice(rc_emojis))
        except:
            pass

    is_private = chat.type == "private"
    is_ai_command = text.startswith("/ai")
    
    if is_private or is_ai_command:
        prompt = text.replace("/ai", "").strip() if is_ai_command else text
        if not prompt:
            return
        if client:
            try:
                response = client.chat.completions.create(
                    model="meta-llama/Meta-Llama-3-8B-Instruct",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=500
                )
                await message.reply_text(response.choices[0].message.content)
            except Exception as e:
                await message.reply_text(f"❌ AI Error: {e}")

async def call_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await track_chats(update, context)
    chat_id = update.effective_chat.id
    user = update.effective_user
    message = update.message
    
    if update.effective_chat.type == "private":
        settings = get_call_settings(chat_id)
        texts = LANGUAGES.get(settings['language'], LANGUAGES["🇲🇲"])
        await message.reply_text(texts["only_group"])
        return

    settings = get_call_settings(chat_id)
    texts = LANGUAGES.get(settings['language'], LANGUAGES["🇲🇲"])

    if settings["who_can_call"] == "owner" and user.id not in OWNER_IDS:
        await message.reply_text(texts["owner_only"])
        return
    elif settings["who_can_call"] == "admin" and not await is_admin(update, context):
        await message.reply_text(texts["admin_only"])
        return

    call_text = " ".join(context.args) if context.args else texts["default_text"]
    try:
        admins = await context.bot.get_chat_administrators(chat_id)
        members = [admin.user for admin in admins]
    except:
        members = []
    
    if not members:
        await message.reply_text(texts["no_members"])
        return
    
    call_keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(texts["btn_stop"], callback_data="stop_call")],
        [InlineKeyboardButton(texts["btn_delete"], callback_data="delete_msg")]
    ])
    await message.reply_text(texts["start_call"], reply_markup=call_keyboard)
    
    sent_count = 0
    message_buffer = []
    chunk_size = settings['call_count']
    
    for member in members:
        if member.is_bot:
            continue
        name = member.first_name or "User"
        if settings["call_mode"] == "emoji":
            emoji = random.choice(CALL_EMOJIS) if CALL_EMOJIS else "✨"
            mention = f"{emoji} [{name}](tg://user?id={member.id})"
        else:
            mention = f"[{name}](tg://user?id={member.id})"
        message_buffer.append(mention)
        
        if len(message_buffer) >= chunk_size:
            await context.bot.send_message(chat_id, "\n".join(message_buffer) + f"\n\n{call_text}", parse_mode="Markdown")
            message_buffer = []
            await asyncio.sleep(0.2)
        sent_count += 1
    
    if message_buffer:
        await context.bot.send_message(chat_id, "\n".join(message_buffer) + f"\n\n{call_text}", parse_mode="Markdown")
    await message.reply_text(texts["finished"].format(count=sent_count))

async def call_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = query.message.chat.id if query else update.effective_chat.id
    settings = get_call_settings(chat_id)
    texts = LANGUAGES.get(settings['language'], LANGUAGES["🇲🇲"])
    
    bot_info = await context.bot.get_me()
    bot_username = bot_info.username
    add_group_url = f"https://t.me/{bot_username}?startgroup=true"

    keyboard = [
        [InlineKeyboardButton(texts["btn_add_group"], url=add_group_url)],
        [InlineKeyboardButton(texts["btn_lang"], callback_data="set_lang_menu")],
        [InlineKeyboardButton(texts["btn_count"].format(count=settings['call_count']), callback_data="call_count")],
        [InlineKeyboardButton(texts["btn_who"].format(who=settings['who_can_call']), callback_data="call_who")],
        [InlineKeyboardButton(texts["btn_mode"].format(mode=settings['call_mode']), callback_data="call_mode")],
        [InlineKeyboardButton(texts["btn_close"], callback_data="delete_msg")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if query:
        try:
            await query.message.edit_text(texts["settings_title"], reply_markup=reply_markup, parse_mode='Markdown')
        except:
            await query.message.reply_text(texts["settings_title"], reply_markup=reply_markup, parse_mode='Markdown')
    else:
        await update.message.reply_text(texts["settings_title"], reply_markup=reply_markup, parse_mode='Markdown')

async def call_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    chat_id = query.message.chat.id
    settings = get_call_settings(chat_id)
    
    if data == "delete_msg":
        try:
            await query.message.delete()
        except:
            pass
    elif data == "stop_call":
        texts = LANGUAGES.get(settings['language'], LANGUAGES["🇲🇲"])
        try:
            await query.message.edit_text(texts["call_stopped"])
        exce
