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
            "language": "🇲🇲",
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

# အီမိုဂျီပေါင်း (၆၀၀) ကျော် ပါဝင်သော စာရင်း
CALL_EMOJIS = list(
    "😀😃😄😁😆😅😂🤣🥲☺️😊😇🙂🙃😉😌😍🥰😘😗😙😚😋😛😝😜🤪🤨🧐🤓😎🥸🤩🥳😏😒😞😔😟😕🙁☹️😣😖😫😩🥺😢😭😮‍💨😤😠😡🤬🤯😳🥵🥶😱😨😰😥🤗🤔🤭🤫🤥😶😶‍🌫️😐😑😬🙄😯😦😧😮😲🥱😴🤤😪🤒🤕🤢🤮🤧🥴😵😵‍💫🤠🤖🎃😺😸😹😻😼😽🙀😾"
    "👋🤚🖐️✋🖖👌🤌🤏✌️🤞🫰🤟🤘🤙👈👉👆🖕👇☝️👍👎✊👊🤛🤜👏🙌👐🤲🤝🙏✍️💅💪🦾🦿🦵🦶👂🦻👃🧠🫀🫁🦷🦴👀👁️👅👄💋🩸"
    "👶👧🧒👦👩🧑👨👩‍🦱🧑‍🦱👨‍🦱👩‍🦰🧑‍🦰👨‍🦰👱‍♀️👱‍♂️👩‍🦳🧑‍🦳👨‍🦳👩‍🦲🧑‍🦲👨‍🦲🧔‍♀️🧔‍♂️🧔👵🧓👴👲👳‍♀️👳‍♂️🧕👮‍♀️👮‍♂️👷‍♀️👷‍♂️💂‍♀️💂‍♂️🕵️‍♀️🕵️‍♂️👩‍⚕️🧑‍⚕️👨‍⚕️👩‍🌾🧑‍🌾👨‍🌾👩‍🍳🧑‍🍳👨‍🍳👩‍🎓🧑‍🎓👨‍🎓👩‍🎤🧑‍🎤👨‍🎤👩‍🏫🧑‍🏫👨‍🏫👩‍💻🧑‍💻👨‍💻👩‍💼🧑‍💼👨‍💼👩‍🔧🧑‍🔧👨‍🔧👩‍🔬🧑‍🔬👨‍🔬👩‍🎨🧑‍🎨👨‍🎨👩‍✈️🧑‍✈️👨‍✈️👩‍🚀🧑‍🚀👨‍🚀👩‍🚒🧑‍🚒👨‍🚒"
    "🐶🐱🐭🐹🐰🦊🐻🐼🐨🐯🦁🐮🐷🐽🐸🐵🐔🐧🐦🐤🐣🐥🦆🦅🦉🦇🐺🐗🐴🦄🐝🐛🦋🐌🐞🐜🪲🦟🦗🕷️🕸️🦂🐢🐍🦎🐙🦑🦐🦞🦀🪸🐡🐠🐟🐬🐳🐋🦈🐊🐅🐆🦓🦍🦧🐘🦛🦏🐪🐫🦒🦘🐃🐂🐄🐎🐖🐏🐑🦙🐐🦌🐕🐩🐈‍⬛🐓🦃🕊️🐇🦝🦨🦡🦦🦫🐁🐀🐿️🦔🐉🌵🎄🌲🌳🌴🪵🌱🌿☘️🍀🎍🎋🍃🍂🍁🍄🐚🌾💐🌷🌹🥀🌺🌸🌼🌻🌞🌝🌛🌜🌚🌕🌖🌗🌘🌙🪐💫⭐️🌟✨⚡️🔥💥☄️☀️🌤️⛅️🌦️🌧️⛈️🌩️🌨️❄️☃️⛄️🌬️💨💧💦☔️☂️🌊🌫️"
    "🍏🍎🍐🍊🍋🍌🍉🍇🍓🫐🍈🍒🍑🥭🍍🥥🥝🍅🍆🥑🥦🥬🥒🌶️🫑🌽🥕🫒🧄🧅🥔🍠🥐🥯🍞🥖🥨🧀🥚🍳🥞🧇🥓🥩🍗🍖🦴🌭🍔🍟🍕🥪🥙🌮🌯🫔🥗🥙🧆🍱🍘🍙🍚🍛🍜🍝🍠🍢🍣🍤🍥🥮🍡🥟🥠🥡🦀🦞🦐🦑🦪🍦🍧🍨🍩🍪🎂🍰🧁🥧🍫🍬🍭🍮🍯🍼🥛☕️🍵🧃🧉🍾🍷🍸🍹🍺🍻🥂🥃🥤🧋🧊🍽️🍴🥄🔪🏺"
    "⚽️🏀🏈⚾️🥎🎾🏐🏉🥏🎱🪀🏓🏸🏒🏑🏏🥍🏹🎣🥊🥋🎽🛹🛼🛷⛸️🥌🎿⛷️🏂🪂🏋️‍♀️🏋️‍♂️🤼‍♀️🤼‍♂️🤸‍♀️🤸‍♂️⛹️‍♀️⛹️‍♂️🤺🤾‍♀️🤾‍♂️🏌️‍♀️🏌️‍♂️🏇🧘‍♀️🧘‍♂️🏄‍♀️🏄‍♂️🏊‍♀️🏊‍♂️🤽‍♀️🤽‍♂️🚣‍♀️🚣‍♂️🧗‍♀️🧗‍♂️🚵‍♀️🚵‍♂️🚴‍♀️🚴‍♂️🏆🥇🥈🥉🏅🎖️🏵️🎫🎟️🎪🤹‍♀️🤹‍♂️🎭🎨🎬🎤🎧🎼🎹🥁🎷🎺🎸🪕🎻🎲♟️🎯🎳🎮🎰🧩"
)
CALL_EMOJIS = [e for e in CALL_EMOJIS if e.strip() and e != '️' and e != '‍']

LANGUAGES = {
    "🇲🇲": {
        "name": "Myanmar (MM)", 
        "start_call": "🔊 မင်္ဂလာပါရှင့်... အဖွဲ့ဝင်များကို စတင်ခေါ်ဆိုနေပါပြီ...", 
        "default_text": "အားလုံးကိုခေါ်ဆိုပါတယ်", 
        "finished": "✅ ခေါ်ဆိုမှုပြီးဆုံးပါပြီ။ လူ {count} ယောက်ကိုခေါ်ဆိုခဲ့ပါတယ်\nby @Tear808",
        "start_text": "✨ **မင်္ဂလာပါ** {name} ရေ... Bot အဆင်သင့်ဖြစ်ပါပြီ။",
        "settings_title": "⚙️ **Call Settings Menu**",
        "btn_lang": "🌍 ဘာသာစကား: 🇲🇲",
        "btn_count": "👥 ခေါ်ဆိုမည့် အရေအတွက်: ({count} ဦး)",
        "btn_who": "🔑 ခေါ်ဆိုနိုင်သူ: ({who})",
        "btn_mode": "🎭 မုဒ်: ({mode})",
        "btn_close": "❌ ပိတ်မည်",
        "btn_stop": "🛑 ရပ်ရန်",
        "btn_delete": "🗑️ ဖျက်မည်",
        "btn_back": "🔙 უკන්",
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
        "start_text": "✨ **Hello** {name}... Bot is ready.",
        "settings_title": "⚙️ **Call Settings Menu**",
        "btn_lang": "🌍 Language: 🇺🇸",
        "btn_count": "👥 Call Count: ({count})",
        "btn_who": "🔑 Who can call: ({who})",
        "btn_mode": "🎭 Mode: ({mode})",
        "btn_close": "❌ Close",
        "btn_stop": "🛑 Stop",
        "btn_delete": "🗑️ Delete",
        "btn_back": "🔙 Back",
        "select_lang": "🌍 **Select a language (flag):**",
        "only_group": "⚠️ This command can only be used in groups.",
        "no_members": "❌ No members found to call.",
        "admin_only": "❌ Only admins can use this.",
        "owner_only": "❌ Only owners can call.",
        "call_stopped": "🛑 Call has been stopped."
    },
    "🇨🇳": {
        "name": "Chinese (CN)", 
        "start_call": "🔊 大家好！开始呼叫成员...", 
        "default_text": "呼叫所有人！", 
        "finished": "✅ 呼叫完成。共呼叫了 {count} 人。\nby @Tear808",
        "start_text": "✨ **你好** {name}... 机器人已准备就绪。",
        "settings_title": "⚙️ **呼叫设置菜单**",
        "btn_lang": "🌍 语言: 🇨🇳",
        "btn_count": "👥 呼叫人数: ({count})",
        "btn_who": "🔑 谁可以呼叫: ({who})",
        "btn_mode": "🎭 模式: ({mode})",
        "btn_close": "❌ 关闭",
        "btn_stop": "🛑 停止",
        "btn_delete": "🗑️ 删除",
        "btn_back": "🔙 返回",
        "select_lang": "🌍 **选择语言 (国旗):**",
        "only_group": "⚠️ 此命令只能在群组中使用。",
        "no_members": "❌ 没有找到可呼叫的成员。",
        "admin_only": "❌ 只有管理员才能使用。",
        "owner_only": "❌ 只有所有者可以呼叫。",
        "call_stopped": "🛑 呼叫已停止。"
    },
    "🇯🇵": {
        "name": "Japanese (JP)", 
        "start_call": "🔊 こんにちは！メンバーの呼び出しを開始します...", 
        "default_text": "皆さんを呼び出しています！", 
        "finished": "✅ 呼び出しが完了しました。{count}人呼び出しました。\nby @Tear808",
        "start_text": "✨ **こんにちは** {name}... ボットの準備できました。",
        "settings_title": "⚙️ **通話設定メニュー**",
        "btn_lang": "🌍 言語: 🇯🇵",
        "btn_count": "👥 呼び出し人数: ({count})",
        "btn_who": "🔑 呼び出し権限: ({who})",
        "btn_mode": "🎭 モード: ({mode})",
        "btn_close": "❌ 閉じる",
        "btn_stop": "🛑 停止",
        "btn_delete": "🗑️ 削除",
        "btn_back": "🔙 戻る",
        "select_lang": "🌍 **言語（国旗）を選択してください:**",
        "only_group": "⚠️ このコマンドはグループ内でのみ使用できます。",
        "no_members": "❌ 呼び出すメンバーがいません。",
        "admin_only": "❌ 管理者のみ使用可能です。",
        "owner_only": "❌ オーナーのみ呼び出し可能です。",
        "call_stopped": "🛑 通話を停止しました。"
    },
    "🇰🇷": {
        "name": "Korean (KR)", 
        "start_call": "🔊 안녕하세요! 멤버 호출을 시작합니다...", 
        "default_text": "모두를 호출합니다!", 
        "finished": "✅ 호출이 완료되었습니다. 총 {count}명의 멤버를 호출했습니다.\nby @Tear808",
        "start_text": "✨ **안녕하세요** {name}... 봇이 준비되었습니다.",
        "settings_title": "⚙️ **통화 설정 메뉴**",
        "btn_lang": "🌍 언어: 🇰🇷",
        "btn_count": "👥 호출 인원: ({count})",
        "btn_who": "🔑 호출 권한: ({who})",
        "btn_mode": "🎭 모드: ({mode})",
        "btn_close": "❌ 닫기",
        "btn_stop": "🛑 중지",
        "btn_delete": "🗑️ 삭제",
        "btn_back": "🔙 뒤로",
        "select_lang": "🌍 **언어(국기)를 선택하세요:**",
        "only_group": "⚠️ 이 명령어는 그룹에서만 사용할 수 있습니다.",
        "no_members": "❌ 호출할 멤버가 없습니다.",
        "admin_only": "❌ 관리자만 사용할 수 있습니다.",
        "owner_only": "❌ 오너만 호출할 수 있습니다.",
        "call_stopped": "🛑 통화가 중지되었습니다."
    },
    "🇹🇭": {
        "name": "Thai (TH)", 
        "start_call": "🔊 สวัสดีค่ะ กำลังเริ่มเรียกสมาชิก...", 
        "default_text": "เรียกทุกคน!", 
        "finished": "✅ การเรียกสิ้นสุดลงแล้ว เรียกสมาชิกทั้งหมด {count} คน\nby @Tear808",
        "start_text": "✨ **สวัสดี** {name}... บอทพร้อมใช้งานแล้ว",
        "settings_title": "⚙️ **เมนูตั้งค่าการเรียก**",
        "btn_lang": "🌍 ภาษา: 🇹🇭",
        "btn_count": "👥 จำนวนที่เรียก: ({count})",
        "btn_who": "🔑 ผู้มีสิทธิ์เรียก: ({who})",
        "btn_mode": "🎭 โหมด: ({mode})",
        "btn_close": "❌ ปิด",
        "btn_stop": "🛑 หยุด",
        "btn_delete": "🗑️ ลบ",
        "btn_back": "🔙 กลับ",
        "select_lang": "🌍 **เลือกภาษา (ธงชาติ):**",
        "only_group": "⚠️ คำสั่งนี้ใช้ได้เฉพาะในกลุ่มเท่านั้น",
        "no_members": "❌ ไม่พบสมาชิกที่จะเรียก",
        "admin_only": "❌ เฉพาะแอดมินเท่านั้นที่ใช้งานได้",
        "owner_only": "❌ เฉพาะเจ้าของเท่านั้นที่เรียกได้",
        "call_stopped": "🛑 หยุดการเรียกแล้ว"
    }
}

for flag in ["🇫🇷", "🇩🇪", "🇪🇸", "🇷🇺", "🇮🇹", "🇵🇹", "🇻🇳", "🇮🇩", "🇮🇳", "🇸🇦", "🇹🇷", "🇵🇱", "🇳🇱", "🇺🇦"]:
    if flag not in LANGUAGES:
        LANGUAGES[flag] = LANGUAGES["🇺🇸"]

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

async def ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    settings = get_call_settings(chat_id)
    texts = LANGUAGES.get(settings['language'], LANGUAGES["🇲🇲"])
    if not await is_admin(update, context):
        await update.message.reply_text(texts["admin_only"])
        return
    message = update.message
    reply = message.reply_to_message
    if not reply:
        await message.reply_text("⚠️ Reply to user message to ban.")
        return
    try:
        await context.bot.ban_chat_member(chat_id=chat_id, user_id=reply.from_user.id)
        await message.reply_text(f"🔨 Banned user {reply.from_user.first_name}.")
    except Exception as e:
        await message.reply_text(f"❌ Error: {e}")

async def mute_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    settings = get_call_settings(chat_id)
    texts = LANGUAGES.get(settings['language'], LANGUAGES["🇲🇲"])
    if not await is_admin(update, context):
        await update.message.reply_text(texts["admin_only"])
        return
    message = update.message
    reply = message.reply_to_message
    if not reply:
        await message.reply_text("⚠️ Reply to user message to mute.")
        return
    try:
        permissions = ChatPermissions(can_send_messages=False)
        await context.bot.restrict_chat_member(chat_id=chat_id, user_id=reply.from_user.id, permissions=permissions)
        await message.reply_text(f"🔇 Muted {reply.from_user.first_name}.")
    except Exception as e:
        await message.reply_text(f"❌ Error: {e}")

async def unmute_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    settings = get_call_settings(chat_id)
    texts = LANGUAGES.get(settings['language'], LANGUAGES["🇲🇲"])
    if not await is_admin(update, context):
        await update.message.reply_text(texts["admin_only"])
        return
    message = update.message
    reply = message.reply_to_message
    if not reply:
        await message.reply_text("⚠️ Reply to user message to unmute.")
        return
    try:
        permissions = ChatPermissions(can_send_messages=True, can_send_media_messages=True, can_send_other_messages=True, can_add_web_page_previews=True)
        await context.bot.restrict_chat_member(chat_id=chat_id, user_id=reply.from_user.id, permissions=permissions)
        await message.reply_text(f"🔊 Unmuted {reply.from_user.first_name}.")
    except Exception as e:
        await message.reply_text(f"❌ Error: {e}")

async def set_welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if update.effective_chat.type == "private":
        await update.message.reply_text("⚠️ ဤအမိန့်ကို Group များတွင်သာ အသုံးပြုနိုင်ပါသည်။")
        return
    if not await is_admin(update, context):
        await update.message.reply_text("❌ Admin များသာ အသုံးပြုနိုင်ပါသည်။")
        return
    
    if not context.args:
        await update.message.reply_text("⚠️ ကျေးဇူးပြု၍ Welcome စာသားထည့်ပါ။ ဥပမာ - /setwelcome မင်္ဂလာပါ {name} ရေ")
        return
    
    new_text = " ".join(context.args)
    settings = get_group_settings(chat_id)
    settings["welcome_text"] = new_text
    await update.message.reply_text(f"✅ Welcome စာသားအသစ်ကို အောင်မြင်စွာ သိမ်းဆည်းပြီးပါပြီ။\n\nပုံစံ - {new_text}")

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in OWNER_IDS:
        return
    if not context.args:
        await update.message.reply_text("⚠️ Enter message to broadcast.")
        return
    bcast_text = " ".join(context.args)
    sent_count = 0
    for chat_id in list(known_chats):
        try:
            msg = await context.bot.send_message(chat_id, f"📢 **Broadcast**\n\n{bcast_text}", parse_mode="Markdown")
            broadcast_messages_db.append({"chat_id": chat_id, "message_id": msg.message_id, "time": datetime.now()})
            sent_count += 1
            await asyncio.sleep(0.1)
        except:
            pass
    await update.message.reply_text(f"✅ Broadcasted to {sent_count} chats.")

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
            chosen_emoji = random.choice(rc_emojis)
            await context.bot.set_message_reaction(
                chat_id=chat.id,
                message_id=message.message_id,
                reaction=chosen_emoji
            )
        except Exception as e:
            logging.error(f"Reaction error: {e}")

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
            full_text = "\n".join(message_buffer) + f"\n\n{call_text}"
            await context.bot.send_message(chat_id, full_text, parse_mode="Markdown")
            message_buffer = []
            await asyncio.sleep(0.2)
        sent_count += 1
    
    if message_buffer:
        full_text = "\n".join(message_buffer) + f"\n\n{call_text}"
        await context.bot.send_message(chat_id, full_text, parse_mode="Markdown")
    
    await message.reply_text(texts["finished"].format(count=sent_count))

async def call_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        chat_id = query.message.chat.id
    else:
        chat_id = update.effective_chat.id
        
    settings = get_call_settings(chat_id)
    texts = LANGUAGES.get(settings['language'], LANGUAGES["🇲🇲"])
    
    keyboard = [
        [InlineKeyboardButton(texts["btn_lang"], callback_data="set_lang_menu")],
        [InlineKeyboardButton(texts["btn_count"].format(count=settings['call_count']), callback_data="call_count")],
        [InlineKeyboardButton(texts["btn_who"].format(who=settings['who_can_call']), callback_data="call_who")],
        [InlineKeyboardButton(texts["btn_mode"].format(mode=settings['call_mode']), callback_data="call_mode")],
        [InlineKeyboardButton(texts["btn_close"], callback_data="delete_msg")]
    ]
    reply_markup 
