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
    return "Bot is alive!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

owner_env = os.environ.get("OWNER_IDS", "")
OWNER_IDS = [int(uid.strip()) for uid in owner_env.split(",") if uid.strip().isdigit()]

call_settings_db = {}
group_settings_db = {}
known_chats = set()
known_users = set()
broadcast_messages_db = []

def get_call_settings(chat_id: int):
    if chat_id not in call_settings_db:
        call_settings_db[chat_id] = {
            "language": "🇲🇲 Myanmar (MM)",
            "call_count": 5,
            "who_can_call": "all",
            "call_mode": "emoji"
        }
    return call_settings_db[chat_id]

def get_group_settings(chat_id: int):
    if chat_id not in group_settings_db:
        group_settings_db[chat_id] = {
            "welcome_text": "✨ မင်္ဂလာပါရှင့်... {name} ရေ, Group ထဲသို့ ကြိုဆိုပါတယ်ခင်ဗျာ。",
            "link_delete": True
        }
    return group_settings_db[chat_id]

# --- 600+ Emojis ---
CALL_EMOJIS = list(
    "😀😃😄😁😆😅😂🤣🥲☺️😊😇🙂🙃😉😌😍🥰😘😗😙😚😋😛😝😜🤪🤨🧐🤓😎🥸🤩🥳😏😒😞😔😟😕🙁☹️😣😖😫😩🥺😢😭😮‍💨😤😠😡🤬🤯😳🥵🥶😱😨😰😥🤗🤔🤭🤫🤥😶😶‍🌫️😐😑😬🙄😯😦😧😮😲🥱😴🤤😪🤒🤕🤢🤮🤧🥴😵😵‍💫🤠🤖🎃😺😸😹😻😼😽🙀😾"
    "👋🤚🖐️✋🖖👌🤌🤏✌️🤞🫰🤟🤘🤙👈👉👆🖕👇☝️👍👎✊👊🤛🤜👏🙌👐🤲🤝🙏✍️💅💪🦾🦿🦵🦶👂🦻👃🧠🫀🫁🦷🦴👀👁️👅👄💋🩸"
    "👶👧🧒👦👩🧑👨👩‍🦱🧑‍🦱👨‍🦱👩‍🦰🧑‍🦰👨‍🦰👱‍♀️👱👱‍♂️👩‍🦳🧑‍🦳👨‍🦳👩‍🦲🧑‍🦲👨‍🦲🧔‍♀️🧔🧔‍♂️👵🧓👴👲👳‍♀️👳👳‍♂️🧕👮‍♀️👮👮‍♂️👷‍♀️👷👷‍♂️💂‍♀️💂💂‍♂️🕵️‍♀️🕵️🕵️‍♂️👩‍⚕️🧑‍⚕️👨‍⚕️👩‍🌾🧑‍🌾👨‍🌾👩‍🍳🧑‍🍳👨‍🍳👩‍🎓🧑‍🎓👨‍🎓👩‍🎤🧑‍🎤👨‍🎤👩‍🏫🧑‍🏫👨‍🏫👩‍🏭🧑‍🏭👨‍🏭👩‍💻🧑‍💻👨‍💻👩‍💼🧑‍💼👨‍💼👩‍🔧🧑‍🔧👨‍🔧👩‍🔬🧑‍🔬👨‍🔬👩‍🎨🧑‍🎨👨‍🎨👩‍🚒🧑‍🚒👨‍🚒👩‍✈️🧑‍✈️👨‍✈️👩‍🚀🧑‍🚀👨‍🚀👩‍⚖️🧑‍⚖️👨‍⚖️"
    "🐶🐱🐹🐰🐰🐻🐼🐻‍❄️🐨🐯🦁🐮🐷🐽🐸🐵🙈🙉🙊🐒🐔🐧🐦🐤🐣🐥🦆🦅🦉🦇🐺🐗🐴🦄🐝🪱🐛🦋🐌🐞🐜🪰🪲🪳🦟🦗🕷️🕸️🦂🐢🐍🦎🦖🦕🐙🦑🦐🦞🦀🐡🐠🐟🐬🐳🐋🦈🦭🐊🐅🐆🦓🦍🦧🦣🐘🦛🦏🐪🐫🦒🦘🦬🐃🐂🐄🐎🐖🐏🐑🦙🐐🦌🐕🐩🦮🐕‍🦺🐈🐈‍⬛🪶🐓🦃🦤🦚🦜🦢🦩🕊️🐇🦝🦡🦫🦦🦨🦥🐁🐀🐿️🦔🐾🐉🐲"
    "🍏🍎🍐🍊🍋🍌🍉🍇🍓🫐🍈🍒🍑🥭🍍🥥🥝🍅🍆🥑🥦🥬🥒🌶️🫑🌽🥕🫒🧄🧅🥔🍠🥐🥯🍞🥖🥨🧀🥚🍳🧈🥞🧇🥓🥩🍗🍖🦴🌭🍔🍟🍕🫓🥪🥙🧆🌮🌯🫔🥗🥘🫕🥫🍝🍜🍲🍛🍣🍱🥟🦪🍙🍚🍘🍥🥠🥮🍢🍡🍧🍨🍦🥧🧁🍰🎂🍮🍭🍬🍫🍿🍩🍪🌰🥜🍯🥛🍼🫖☕️🍵🧃🥤🧋🍶🍺🍻🥂🍷🥃🍸🍹🧉🍾🧊🥄🍴🍽️🥣🥡🥢🧂"
    "⚽️🏀🏈⚾️🥎🎾🏐🏉🥏🎱🪀🏓🏸🏒🏑🥍🏏🪃🥅⛳️🪁🏹🎣🤿🥊🥋🎽🛹🛼🛷⛸️🥌🎿⛷️🏂🪂🏋️‍♀️🏋️🏋️‍♂️🤼‍♀️🤼🤼‍♂️🤸‍♀️🤸🤸‍♂️⛹️‍♀️⛹️⛹️‍♂️🤺🤾‍♀️🤾🤾‍♂️🏌️‍♀️🏌️🏌️‍♂️🏇🧘‍♀️🧘🧘‍♂️🏄‍♀️🏄🏄‍♂️🏊‍♀️🏊🏊‍♂️🤽‍♀️🤽🤽‍♂️🚣‍♀️🚣🚣‍♂️🧗‍♀️🧗🧗‍♂️🚵‍♀️🚵🚵‍♂️🚴‍♀️🚴🚴‍♂️🏆🥇🥈🥉🏅🎖️🏵️🎗️🎫🎟️🎪🤹‍♀️🤹🤹‍♂️🎭🩰🎨🎬🎤🎧🎼🎹🥁🪘🎷🎺🪗🎸🪕🎻🎲♟️🎯🎳🎮🎰🧩"
    "🚗🚕🚙🚌🚎🏎️🚓🚑🚒🚐🛻🚚🚛🚜🦯🦽🦼🛴🚲🛵🏍️🛺🚨🚔🚍🚘🚖🚡🚠🚟🚃🚋🚞🚝🚄🚅🚈🚂🚆🚇🚊🚉✈️🛫🛬🛩️💺🛰️🚀🛸🚁🛶⛵️🚤🛥️🛳️⛴️🚢⚓️🪝⛽️🚧🚦🚥🚏🗺️🗿🗽🗼🏰🏯🏟️🎡🎢🎠⛲️⛱️🏖️🏝️🏜️🌋⛰️🏔️🗻🏕️⛺️🛖🏠🏡🏘️🏚️🏗️🏭🏢🏬🏣🏤🏥🏦🏨🏪🏫🏩💒🏛️⛪️🕌🕍🛕🕋⛩️🛤️🛣️🗾🎑🏞️🌅🌄🌠🎇🎆🌇🌆🏙️🌃🌉🌁"
    "🔥⚡✨🌟💫💥🎉🎊🎈💎👑💖💗💓💞💕💘💔❤️🧡💛💚💙💜🤎🖤🤍💯💬📢📣"
)
CALL_EMOJIS = [e for e in CALL_EMOJIS if e.strip() and e != '️' and e != '‍']

# --- ဘာသာစကား (၂၀) မျိုး အပြည့်အစုံ ---
LANGUAGES = {
    "🇲🇲 Myanmar (MM)": {
        "start_call": "🔊 မင်္ဂလာပါရှင့်... အဖွဲ့ဝင်များကို စတင်ခေါ်ဆိုနေပါပြီ...",
        "default_text": "အားလုံးကိုခေါ်ဆိုပါတယ်",
        "finished": "✅ ခေါ်ဆိုမှုပြီးဆုံးပါပြီ။ လူ {count} ယောက်ကိုခေါ်ဆိုခဲ့ပါတယ်\nby @Tear808"
    },
    "🇺🇸 English (EN)": {
        "start_call": "🔊 Hello! Starting to call members...",
        "default_text": "Calling everyone!",
        "finished": "✅ Call finished. Called {count} members.\nby @Tear808"
    },
    "🇨🇳 Chinese (CN)": {
        "start_call": "🔊 大家好！开始呼叫成员...",
        "default_text": "呼叫所有人！",
        "finished": "✅ 呼叫完成。共呼叫了 {count} 人。\nby @Tear808"
    },
    "🇯🇵 Japanese (JP)": {
        "start_call": "🔊 こんにちは！メンバーの呼び出しを開始します...",
        "default_text": "皆さんを呼び出しています！",
        "finished": "✅ 呼び出しが完了しました。{count}人呼び出しました。\nby @Tear808"
    },
    "🇰🇷 Korean (KR)": {
        "start_call": "🔊 안녕하세요! 멤버 호출을 시작합니다...",
        "default_text": "모두를 호출합니다!",
        "finished": "✅ 호출이 완료되었습니다. 총 {count}명의 멤버를 호출했습니다.\nby @Tear808"
    },
    "🇹🇭 Thai (TH)": {
        "start_call": "🔊 สวัสดีค่ะ กำลังเริ่มเรียกสมาชิก...",
        "default_text": "เรียกทุกคน!",
        "finished": "✅ การเรียกสิ้นสุดลงแล้ว เรียกสมาชิกทั้งหมด {count} คน\nby @Tear808"
    },
    "🇫🇷 French (FR)": {
        "start_call": "🔊 Bonjour ! Démarrage de l'appel des membres...",
        "default_text": "Appel de tout le monde !",
        "finished": "✅ Appel terminé. {count} membres appelés.\nby @Tear808"
    },
    "🇩🇪 German (DE)": {
        "start_call": "🔊 Hallo! Beginne mit dem Aufrufen der Mitglieder...",
        "default_text": "Rufe alle auf!",
        "finished": "✅ Aufruf beendet. {count} Mitglieder aufgerufen.\nby @Tear808"
    },
    "🇪🇸 Spanish (ES)": {
        "start_call": "🔊 ¡Hola! Comenzando a llamar a los miembros...",
        "default_text": "¡Llamando a todos!",
        "finished": "✅ Llamada terminada. Se llamó a {count} miembros.\nby @Tear808"
    },
    "🇷🇺 Russian (RU)": {
        "start_call": "🔊 Здравствуйте! Начинаем вызов участников...",
        "default_text": "Вызов всех!",
        "finished": "✅ Вызов завершен. Вызвано участников: {count}.\nby @Tear808"
    },
    "🇮🇹 Italian (IT)": {
        "start_call": "🔊 Salve! Inizio a chiamare i membri...",
        "default_text": "Chiamando tutti!",
        "finished": "✅ Chiamata terminata. Chiamati {count} membri.\nby @Tear808"
    },
    "🇵🇹 Portuguese (PT)": {
        "start_call": "🔊 Olá! Começando a chamar os membros...",
        "default_text": "Chamando todos!",
        "finished": "✅ Chamada terminada. {count} membros chamados.\nby @Tear808"
    },
    "🇻🇳 Vietnamese (VI)": {
        "start_call": "🔊 Xin chào! Bắt đầu gọi các thành viên...",
        "default_text": "Gọi tất cả mọi người!",
        "finished": "✅ Đã gọi xong. Đã gọi {count} thành viên.\nby @Tear808"
    },
    "🇮🇩 Indonesian (ID)": {
        "start_call": "🔊 Halo! Memulai panggilan anggota...",
        "default_text": "Memanggil semuanya!",
        "finished": "✅ Panggilan selesai. Memanggil {count} anggota.\nby @Tear808"
    },
    "🇮🇳 Hindi (HI)": {
        "start_call": "🔊 नमस्ते! सदस्यों को कॉल करना शुरू कर रहे हैं...",
        "default_text": "सभी को कॉल किया जा रहा है!",
        "finished": "✅ कॉल समाप्त। {count} सदस्यों को कॉल किया गया。\nby @Tear808"
    },
    "🇸🇦 Arabic (AR)": {
        "start_call": "🔊 أهلاً! البدء في استدعاء الأعضاء...",
        "default_text": "استدعاء الجميع!",
        "finished": "✅ انتهت الدعوة. تم استدعاء {count} عضواً.\nby @Tear808"
    },
    "🇹🇷 Turkish (TR)": {
        "start_call": "🔊 Merhaba! Üyeleri aramaya başlıyor...",
        "default_text": "Herkesi çağırıyor!",
        "finished": "✅ Çağrı tamamlandı. {count} üye çağrıldı.\nby @Tear808"
    },
    "🇵🇱 Polish (PL)": {
        "start_call": "🔊 Cześć! Rozpoczynam wywoływanie członków...",
        "default_text": "Wywołuję wszystkich!",
        "finished": "✅ Wywołanie zakończone. Wywołano {count} członków.\nby @Tear808"
    },
    "🇳🇱 Dutch (NL)": {
        "start_call": "🔊 Hallo! Begin het oproepen van leden...",
        "default_text": "Iedereen oproepen!",
        "finished": "✅ Oproep voltooid. {count} leden opgeroepen.\nby @Tear808"
    },
    "🇺🇦 Ukrainian (UK)": {
        "start_call": "🔊 Вітаю! Починаємо виклик учасників...",
        "default_text": "Виклик усіх!",
        "finished": "✅ Виклик завершено. Викликано учасників: {count}.\nby @Tear808"
    }
}

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

# --- Administrative Commands (/ban, /mute, /unmute) ---
async def ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("❌ Admin များသာ အသုံးပြုနိုင်ပါသည်။")
        return
    message = update.message
    reply = message.reply_to_message
    if not reply:
        await message.reply_text("⚠️ Ban မည့်သူ၏ မက်ဆေ့ခ်ျကို Reply လုပ်၍ အသုံးပြုပါ။")
        return
    try:
        await context.bot.ban_chat_member(chat_id=update.effective_chat.id, user_id=reply.from_user.id)
        await message.reply_text(f"🔨 အဖွဲ့ဝင် {reply.from_user.first_name} ကို Ban လိုက်ပါပြီ။")
    except Exception as e:
        await message.reply_text(f"❌ အမှားအယွင်းရှိသည်: {e}")

async def mute_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("❌ Admin များသာ အသုံးပြုနိုင်ပါသည်။")
        return
    message = update.message
    reply = message.reply_to_message
    if not reply:
        await message.reply_text("⚠️ Mute လုပ်မည့်သူ၏ မက်ဆေ့ခ်ျကို Reply လုပ်ပါ။")
        return
    try:
        permissions = ChatPermissions(can_send_messages=False)
        await context.bot.restrict_chat_member(chat_id=update.effective_chat.id, user_id=reply.from_user.id, permissions=permissions)
        await message.reply_text(f"muted 🔇 {reply.from_user.first_name} ကို စာမရေးနိုင်အောင် Mute လိုက်ပါပြီ။")
    except Exception as e:
        await message.reply_text(f"❌ အမှားအယွင်းရှိသည်: {e}")

async def unmute_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("❌ Admin များသာ အသုံးပြုနိုင်ပါသည်။")
        return
    message = update.message
    reply = message.reply_to_message
    if not reply:
        await message.reply_text("⚠️ Unmute လုပ်မည့်သူ၏ မက်ဆေ့ခ်ျကို Reply လုပ်ပါ။")
        return
    try:
        permissions = ChatPermissions(can_send_messages=True, can_send_media_messages=True, can_send_other_messages=True, can_add_web_page_previews=True)
        await context.bot.restrict_chat_member(chat_id=update.effective_chat.id, user_id=reply.from_user.id, permissions=permissions)
        await message.reply_text(f"🔊 {reply.from_user.first_name} ကို Mute ဖြုတ်ပေးလိုက်ပါပြီ။")
    except Exception as e:
        await message.reply_text(f"❌ အမှားအယွင်းရှိသည်: {e}")

# --- Broadcast Command (/bcast) ---
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in OWNER_IDS:
        return
    if not context.args:
        await update.message.reply_text("⚠️ ပို့လိုသည့် စာသားကို ထည့်ပါ။ ဥပမာ: /bcast မင်္ဂလာပါ")
        return
    bcast_text = " ".join(context.args)
    sent_count = 0
    for chat_id in list(known_chats):
        try:
            msg = await context.bot.send_message(chat_id, f"📢 **ကြေငြာချက်**\n\n{bcast_text}", parse_mode="Markdown")
            broadcast_messages_db.append({"chat_id": chat_id, "message_id": msg.message_id, "time": datetime.now()})
            sent_count += 1
            await asyncio.sleep(0.1)
        except:
            pass
    await update.message.reply_text(f"✅ Groupပေါင်း {sent_count} ခုသို့ ပို့ပြီးပါပြီ။")

# --- Background Job: 24-Hour Ad Deletion ---
def cleanup_old_broadcasts(application):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    async def delete_jobs():
        now = datetime.now()
        global broadcast_messages_db
        remaining = []
        for item in broadcast_messages_db:
            if now - item["time"] > timedelta(hours=24):
                try:
                    await application.bot.delete_message(chat_id=item["chat_id"], message_id=item["message_id"])
                except:
                    pass
            else:
                remaining.append(item)
        broadcast_messages_db = remaining

    loop.run_until_complete(delete_jobs())

# --- Unified Message Handler ---
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await track_chats(update, context)
    message = update.message
    if not message:
        return

    chat = update.effective_chat
    user = update.effective_user
    text = message.text or message.caption or ""

    # Link ဖျက်စနစ်
    if chat.type in ["group", "supergroup"]:
        if "http://" in text or "https://" in text or "t.me/" in text or "www." in text:
            if user.id not in OWNER_IDS:
                try:
                    await message.delete()
                    return
                except:
                    pass

    # Reaction (Rc) ပေးစနစ်
    if user and not user.is_bot:
        try:
            rc_emojis = ["👍", "❤️", "🔥", "✨", "👏", "🎉"]
            chosen_emoji = random.choice(rc_emojis)
            await context.bot.set_message_reaction(
                chat_id=chat.id,
                message_id=message.message_id,
                reaction=chosen_emoji
            )
        except Exception as e:
            logging.error(f"Reaction error: {e}")

    # AI စနစ် (Private Chat ဆိုလျှင် တန်းဖြေ၊ Group ဆိုလျှင် /ai ဖြင့် မေးလျှင်ဖြေ)
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
                answer = response.choices[0].message.content
                await message.reply_text(answer)
            except Exception as e:
                await message.reply_text(f"❌ AI အမှားအယွင်းရှိသည်: {e}")
        else:
            await message.reply_text("⚠️ Hugging Face Token မထည့်ရသေးပါ။")

# --- Call All System (0.2s speed) ---
async def call_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await track_chats(update, context)
    chat_id = update.effective_chat.id
    user = update.effective_user
    message = update.message
    
    if update.effective_chat.type == "private":
        await message.reply_text("⚠️ ဤအမိန့်ကို Group များတွင်သာ အသုံးပြုနိုင်ပါသည်။")
        return

    settings = get_call_settings(chat_id)
    if settings["who_can_call"] == "owner" and user.id not in OWNER_IDS:
        await message.reply_text("❌ Owner များသာ ခေါ်ဆိုနိုင်ပါသည်။")
        return
    elif settings["who_can_call"] == "admin" and not await is_admin(update, context):
        await message.reply_text("❌ Admin များသာ ခေါ်ဆိုနိုင်ပါသည်။")
        return

    lang_texts = LANGUAGES.get(settings['language'], LANGUAGES["🇲🇲 Myanmar (MM)"])
    call_text = " ".join(context.args) if context.args else lang_texts["default_text"]
    
    try:
        admins = await context.bot.get_chat_administrators(chat_id)
        members = [admin.user for admin in admins if admin.user.username]
    except:
        members = []
    
    if not members:
        await message.reply_text("❌ ခေါ်ဆိုရန် အဖွဲ့ဝင် မရှိပါ။")
        return
    
    call_keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🛑 ရပ်ရန်", callback_data="stop_call")],
        [InlineKeyboardButton("🗑️ ဖျက်မည်", callback_data="delete_msg")]
    ])
    
    await message.reply_text(lang_texts["start_call"], reply_markup=call_keyboard)
    
    sent_count = 0
    message_buffer = []
    
    for member in members:
        username = f"@{member.username}"
        if settings["call_mode"] == "emoji":
            emoji = random.choice(CALL_EMOJIS) if CALL_EMOJIS else "✨"
            mention = f"{emoji} [{username}](tg://user?id={member.id})"
        else:
            mention = f"[{username}](tg://user?id={member.id})"
            
        message_buffer.append(mention)
        
        if len(message_buffer) >= settings['call_count']:
            full_text = "\n".join(message_buffer) + f"\n\n{call_text}"
            await context.bot.send_message(chat_id, full_text, parse_mode="Markdown")
            message_buffer = []
            await asyncio.sleep(0.2)  # 0.2 စက္ကန့် အမြန်နှုန်း
        sent_count += 1
    
    if message_buffer:
        full_text = "\n".join(message_buffer) + f"\n\n{call_text}"
        await context.bot.send_message(chat_id, full_text, parse_mode="Markdown")
    
    await message.reply_text(lang_texts["finished"].format(count=sent_count))

async def call_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    settings = get_call_settings(chat_id)
    
    keyboard = [
        [InlineKeyboardButton(f"🌍 ဘာသာစကား: ({settings['language'].split()[0]})", callback_data="call_lang")],
        [InlineKeyboardButton(f"👥 ခေါ်ဆိုလူဦးရေ: ({settings['call_count']})", callback_data="call_count")],
        [InlineKeyboardButton(f"🔑 ခေါ်ဆိုနိုင်သူ: ({settings['who_can_call']})", callback_data="call_who")],
        [InlineKeyboardButton(f"🎭 Emoji / Link: ({settings['call_mode']})", callback_data="call_mode")],
        [InlineKeyboardButton("❌ Delete", callback_data="delete_msg")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    query = update.callback_query
    if query:
        try:
            await query.message.edit_text("⚙️ **Call Settings Menu**", reply_markup=reply_markup, parse_mode='Markdown')
        except:
            await query.message.reply_text("⚙️ **Call Settings Menu**", reply_markup=reply_markup, parse_mode='Markdown')
    else:
        await update.message.reply_text("⚙️ **Call Settings Menu**", reply_markup=reply_markup, parse_mode='Markdown')

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
        try:
            await query.message.edit_text("🛑 Call ရပ်တန့်လိုက်ပါပြီ။")
        except:
            pass
    elif data == "call_lang":
        lang_keys = list(LANGUAGES.keys())
        current_lang = settings['language']
        next_index = (lang_keys.index(current_lang) + 1) % len(lang_keys) if current_lang in lang_keys else 0
        settings['language'] = lang_keys[next_index]
        await call_settings(update, context)
    elif data == "call_count":
        counts = [3, 5, 7, 10, 15]
        curr = settings['call_count']
        next_idx = (counts.index(curr) + 1) % len(counts) if curr in counts else 0
        settings['call_count'] = counts[next_idx]
        await call_settings(update, context)
    elif data == "call_who":
        whos = ["all", "admin", "owner"]
        curr = settings['who_can_call']
        next_idx
