import os
import logging
import asyncio
import random
from flask import Flask
from threading import Thread
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReactionTypeEmoji
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, CommandHandler, CallbackQueryHandler, filters
from huggingface_hub import InferenceClient

# Logging စနစ်သတ်မှတ်ခြင်း
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

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

# အင်္ဂလိပ်ဘာသာစကား သုံးသောနိုင်ငံများအတွက် English ကို သုံးပြီး ကျန်နိုင်ငံများအတွက် သက်ဆိုင်ရာဘာသာစကားများ
LANGUAGES = {
    # --- English (US & UK, Canada, Australia, etc.) ---
    "🇺🇸": {
        "name": "English (US)", "start_call": "🔊 Hello! Starting to call members...", "default_text": "Calling everyone!", 
        "finished": "✅ Call finished. Called {count} members.\nby @Tear808",
        "start_text": "✨ **Hello** {name}...\n\nI am your Tear AI Assistant bot. (@Call_ai_love_bot)",
        "settings_title": "⚙️ **Call Settings Menu**", "btn_lang": "🌍 Language: 🇺🇸", "btn_count": "👥 Call Count: ({count})",
        "btn_who": "🔑 Who can call: ({who})", "btn_mode": "🎭 Mode: ({mode})", "btn_close": "❌ Close", "btn_stop": "🛑 Stop",
        "btn_delete": "🗑️ Delete", "btn_back": "🔙 Back", "btn_add_group": "➕ Add to Group", "select_lang": "🌍 **Select a language (flag):**",
        "only_group": "⚠️ This command can only be used in groups.", "no_members": "❌ No members found to call.",
        "admin_only": "❌ Only admins can use this.", "owner_only": "❌ Only owners can call.", "call_stopped": "🛑 Call has been stopped.",
        "lang_changed": "✅ Language changed to English."
    },
    "🇬🇧": { "name": "English (UK)", "__copy__": "🇺🇸" },
    "🇨🇦": { "name": "English (Canada)", "__copy__": "🇺🇸" },
    "🇦🇺": { "name": "English (Australia)", "__copy__": "🇺🇸" },
    "🇳🇿": { "name": "English (New Zealand)", "__copy__": "🇺🇸" },
    "🇮🇪": { "name": "English (Ireland)", "__copy__": "🇺🇸" },
    "🇿🇦": { "name": "English (South Africa)", "__copy__": "🇺🇸" },
    "🇸🇬": { "name": "English (Singapore)", "__copy__": "🇺🇸" },

    # --- Myanmar ---
    "🇲🇲": {
        "name": "Myanmar (မြန်မာ)", 
        "start_call": "🔊 မင်္ဂလာပါရှင့်... အဖွဲ့ဝင်များကို စတင်ခေါ်ဆိုနေပါပြီ...", 
        "default_text": "အားလုံးကိုခေါ်ဆိုပါတယ်", 
        "finished": "✅ ခေါ်ဆိုမှုပြီးဆုံးပါပြီ။ လူ {count} ယောက်ကိုခေါ်ဆိုခဲ့ပါတယ်\nby @Tear808",
        "start_text": "✨ **မင်္ဂလာပါ** {name} ရေ...\n\nကျွန်ုပ်သည် Tear AI လက်ထောက် Bot ဖြစ်ပါသည်။ (@Call_ai_love_bot)",
        "settings_title": "⚙️ **Call & Bot Settings Menu**",
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
        "call_stopped": "🛑 Call ရပ်တန့်လိုက်ပါပြီ။",
        "lang_changed": "✅ ဘာသာစကားကို မြန်မာသို့ ပြောင်းလဲပြီးပါပြီ။"
    },
    
    # --- Chinese ---
    "🇨🇳": {
        "name": "Chinese (中文)", 
        "start_call": "🔊 大家好... 开始呼叫成员...", 
        "default_text": "呼叫所有人！", 
        "finished": "✅ 呼叫结束。共呼叫了 {count} 名成员\nby @Tear808",
        "start_text": "✨ **你好** {name}...\n\n我是你的 Tear AI 助手机器人。(@Call_ai_love_bot)",
        "settings_title": "⚙️ **呼叫与机器人设置菜单**",
        "btn_lang": "🌍 语言: 🇨🇳",
        "btn_count": "👥 呼叫人数: ({count} 人)",
        "btn_who": "🔑 谁可以呼叫: ({who})",
        "btn_mode": "🎭 模式: ({mode})",
        "btn_close": "❌ 关闭",
        "btn_stop": "🛑 停止",
        "btn_delete": "🗑️ 删除",
        "btn_back": "🔙 返回",
        "btn_add_group": "➕ 添加到群组",
        "select_lang": "🌍 **请选择一种语言 (国旗):**",
        "only_group": "⚠️ 此命令只能在群组中使用。",
        "no_members": "❌ 未找到可呼叫的成员。",
        "admin_only": "❌ 只有管理员才能使用此功能。",
        "owner_only": "❌ 只有群主才能呼叫。",
        "call_stopped": "🛑 呼叫已被停止。",
        "lang_changed": "✅ 语言已更改为中文。"
    },

    # --- Thai ---
    "🇹🇭": {
        "name": "Thai (ไทย)", 
        "start_call": "🔊 สวัสดีครับ/ค่ะ... กำลังเริ่มเรียกสมาชิก...", 
        "default_text": "เรียกทุกคน!", 
        "finished": "✅ การเรียกเสร็จสิ้น เรียกว่าสมาชิก {count} คน\nby @Tear808",
        "start_text": "✨ **สวัสดี** {name}...\n\nฉันคือบอทผู้ช่วย Tear AI ของคุณ (@Call_ai_love_bot)",
        "settings_title": "⚙️ **เมนูการตั้งค่า**",
        "btn_lang": "🌍 ภาษา: 🇹🇭",
        "btn_count": "👥 จำนวนการเรียก: ({count} คน)",
        "btn_who": "🔑 ใครเรียกได้บ้าง: ({who})",
        "btn_mode": "🎭 โหมด: ({mode})",
        "btn_close": "❌ ปิด",
        "btn_stop": "🛑 หยุด",
        "btn_delete": "🗑️ ลบ",
        "btn_back": "🔙 กลับ",
        "btn_add_group": "➕ เพิ่มลงกลุ่ม",
        "select_lang": "🌍 **โปรดเลือกภาษา (ธงชาติ):**",
        "only_group": "⚠️ คำสั่งนี้ใช้ได้เฉพาะในกลุ่มเท่านั้น",
        "no_members": "❌ ไม่พบสมาชิกที่จะเรียก",
        "admin_only": "❌ เฉพาะแอดมินเท่านั้นที่ใช้ได้",
        "owner_only": "❌ เฉพาะเจ้าของเท่านั้นที่เรียกได้",
        "call_stopped": "🛑 การเรียกถูกหยุดแล้ว",
        "lang_changed": "✅ เปลี่ยนภาษาเป็นไทยเรียบร้อยแล้ว"
    },

    # --- Japanese ---
    "🇯🇵": {
        "name": "Japanese (日本語)", 
        "start_call": "🔊 こんにちは... メンバーの呼び出しを開始します...", 
        "default_text": "全員を呼び出しています！", 
        "finished": "✅ 呼び出しが完了しました。{count} 人のメンバーを呼び出しました\nby @Tear808",
        "start_text": "✨ **こんにちは** {name}...\n\n私はあなたのTear AIアシスタントボットです。(@Call_ai_love_bot)",
        "settings_title": "⚙️ **設定メニュー**",
        "btn_lang": "🌍 言語: 🇯🇵",
        "btn_count": "👥 呼び出し数: ({count} 人)",
        "btn_who": "🔑 呼び出し権限: ({who})",
        "btn_mode": "🎭 モード: ({mode})",
        "btn_close": "❌ 閉じる",
        "btn_stop": "🛑 停止",
        "btn_delete": "🗑️ 削除",
        "btn_back": "🔙 戻る",
        "btn_add_group": "➕ グループに追加",
        "select_lang": "🌍 **言語（国旗）を選択してください:**",
        "only_group": "⚠️ このコマンドはグループでのみ使用できます。",
        "no_members": "❌ 呼び出すメンバーが見つかりません。",
        "admin_only": "❌ 管理者のみ使用できます。",
        "owner_only": "❌ オーナーのみ呼び出し可能です。",
        "call_stopped": "🛑 呼び出しが停止されました。",
        "lang_changed": "✅ 言語が日本語に変更されました。"
    },

    # --- Korean ---
    "🇰🇷": {
        "name": "Korean (한국어)", 
        "start_call": "🔊 안녕하세요... 멤버 호출을 시작합니다...", 
        "default_text": "모두를 호출합니다!", 
        "finished": "✅ 호출이 완료되었습니다. {count}명의 멤버를 호출했습니다.\nby @Tear808",
        "start_text": "✨ **안녕하세요** {name} 님...\n\n저는 Tear AI 어시스턴트 봇입니다. (@Call_ai_love_bot)",
        "settings_title": "⚙️ **설정 메뉴**",
        "btn_lang": "🌍 언어: 🇰🇷",
        "btn_count": "👥 호출 인원: ({count}명)",
        "btn_who": "🔑 호출 권한: ({who})",
        "btn_mode": "🎭 모드: ({mode})",
        "btn_close": "❌ 닫기",
        "btn_stop": "🛑 중지",
        "btn_delete": "🗑️ 삭제",
        "btn_back": "🔙 뒤로",
        "btn_add_group": "➕ 그룹에 추가",
        "select_lang": "🌍 **언어(국기)를 선택하세요:**",
        "only_group": "⚠️ 이 명령어는 그룹에서만 사용할 수 있습니다.",
        "no_members": "❌ 호출할 멤버가 없습니다.",
        "admin_only": "❌ 관리자만 사용할 수 있습니다.",
        "owner_only": "❌ 오너만 호출할 수 있습니다.",
        "call_stopped": "🛑 호출이 중지되었습니다.",
        "lang_changed": "✅ 언어가 한국어로 변경되었습니다."
    }
}

for k, v in list(LANGUAGES.items()):
    if "__copy__" in v:
        LANGUAGES[k] = LANGUAGES[v["__copy__"]]

other_flags = [
    "🇫🇷", "🇩🇪", "🇪🇸", "🇷🇺", "🇮🇹", "🇵🇹", "🇻🇳", "🇮🇩", "🇮🇳", "🇸🇦", "🇹🇷", 
    "🇵🇱", "🇳🇱", "🇺🇦", "🇧🇷", "🇲🇽", "🇦🇷", "🇪🇬", "🇵🇭", "🇵🇰", "🇧🇩", "🇮🇷", 
    "🇮🇶", "🇸🇪", "🇳🇴", "🇩🇰", "🇫🇮", "🇬🇷", "🇨🇿", "🇭🇺", "🇷🇴", "🇧🇬", "🇭🇷", 
    "🇷🇸", "🇸🇰", "🇸🇮", "🇪🇪", "🇱🇻", "🇱🇹", "🇨🇭", "🇦🇹", "🇧🇪", "🇱🇺", "🇮🇸", 
    "🇨🇱", "🇨🇴", "🇵🇪", "🇻🇪", "🇪🇨", "🇨🇺", "🇩🇴", "🇬🇹", "🇭🇳", "🇸🇻", "🇨🇷", 
    "🇵🇦", "🇺🇾", "🇧🇴", "🇵🇾", "🇳🇵", "🇱🇰", "🇧🇹", "🇲🇻", "🇦🇫", "🇰🇿", "🇺🇿", 
    "🇹🇲", "🇰🇬", "🇹🇯", "🇦🇿", "🇦🇲", "🇬🇪", "🇨🇾", "🇱🇧", "🇯🇴", "🇸🇾", "🇮🇱", 
    "🇵🇸", "🇾🇪", "🇴🇲", "🇦🇪", "🇶🇦", "🇧🇭", "🇰🇼", "🇱🇾", "🇹🇳", "🇩🇿", 
    "🇲🇦", "🇸🇩", "🇸🇸", "🇪🇹", "🇰🇪", "🇹🇿", "🇺🇬", "🇷🇼", "🇧🇮", "🇸🇴", 
    "🇩🇯", "🇪🇷", "🇳🇬", "🇬🇭", "🇨🇲", "🇨🇮", "🇸🇳", "🇲🇱", "🇧🇫", "🇳🇪", 
    "🇹🇩", "🇬🇼", "🇬🇳", "🇸🇱", "🇱🇷", "🇹🇬", "🇧🇯", "🇨🇬", "🇨🇩", "🇬🇦", 
    "🇬🇶", "🇨🇫", "🇦🇴", "🇿🇲", "🇿🇼", "🇲🇼", "🇲🇿", "🇧🇼", "🇳🇦", "🇱🇸", "🇸🇿", 
    "🇲🇺", "🇸🇨", "🇰🇲", "🇲🇬"
]

for flag in other_flags:
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

CALL_EMOJIS = [
    "😀", "😃", "😄", "😁", "😆", "😅", "😂", "🤣", "😊", "😇", "🙂", "🙃", "😉", "😌", "😍", "🥰", "😘", "😗", "😙", "😚",
    "😋", "😛", "😝", "😜", "🤪", "🤨", "🧐", "🤓", "😎", "🤩", "🥳", "😏", "😒", "😞", "😔", "😟", "😕", "🙁", "☹️", "😣",
    "😖", "😫", "😩", "🥺", "😢", "😭", "😤", "😠", "😡", "🤬", "🤯", "😳", "🥵", "🥶", "😱", "😨", "😰", "😥", "😓", "🤗",
    "🤔", "🤭", "🤫", "🤥", "😶", "😐", "😑", "😬", "🙄", "😯", "😦", "😧", "😮", "😲", "🥱", "😴", "🤤", "😪", "😵", "🤐",
    "🥴", "🤢", "🤮", "🤧", "😷", "🤒", "🤕", "🤑", "🤠", "😈", "👿", "👹", "👺", "🤡", "💩", "👻", "💀", "☠️", "👽", "👾",
    "🤖", "🎃", "😺", "😸", "😹", "😻", "😼", "😽", "🙀", "😿", "😾", "👋", "🤚", "🖐️", "✋", "🖖", "👌", "🤌", "🤏", "✌️",
    "🤞", "🫰", "🤟", "🤘", "🤙", "👈", "👉", "👆", "🖕", "👇", "☝️", "👍", "👎", "✊", "👊", "🤛", "🤜", "👏", "🙌", "👐",
    "🤲", "🤝", "🙏", "✍️", "💅", "🤳", "💪", "🦾", "🦿", "🦵", "🦶", "👂", "🦻", "👃", "🧠", "🦷", "🦴", "👀", "👁️", "👅",
    "👄", "💋", "👶", "👧", "🧒", "👦", "👩", "🧑", "👨", "👩‍🦱", "🧑‍🦱", "👨‍🦱", "👩‍🦰", "🧑‍🦰", "👨‍🦰", "👱‍♀️", "👱", "👱‍♂️", "👩‍🦳",
    "🧑‍🦳", "👨‍🦳", "👩‍🦲", "🧑‍🦲", "👨‍🦲", "🧔", "🧔‍♀️", "🧔‍♂️", "👵", "🧓", "👴", "👲", "👳‍♀️", "👳", "👳‍♂️", "🧕", "👮‍♀️", "👮", "👮‍♂️", "👷‍♀️",
    "👷", "👷‍♂️", "💂‍♀️", "💂", "💂‍♂️", "🕵️‍♀️", "🕵️", "🕵️‍♂️", "👩‍⚕️", "🧑‍⚕️", "👨‍⚕️", "👩‍🌾", "🧑‍🌾", "👨‍🌾", "👩‍🍳", "🧑‍🍳", "👨‍🍳", "👩‍🎓", "🧑‍🎓", "👨‍🎓",
    "👩‍🎤", "🧑‍🎤", "👨‍🎤", "👩‍🏫", "🧑‍🏫", "👨‍🏫", "👩‍🏭", "🧑‍🏭", "👨‍🏭", "👩‍💻", "🧑‍💻", "👨‍💻", "👩‍💼", "🧑‍💼", "👨‍💼", "👩‍🔧", "🧑‍🔧", "👨‍🔧", "👩‍🔬", "🧑‍🔬",
    "👨‍🔬", "👩‍🎨", "🧑‍🎨", "👨‍🎨", "👩‍🚒", "🧑‍🚒", "👨‍🚒", "👩‍✈️", "🧑‍✈️", "👨‍✈️", "👩‍🚀", "🧑‍🚀", "👨‍🚀", "👩‍⚖️", "🧑‍⚖️", "👨‍⚖️", "👰‍♀️", "👰", "👰‍♂️", "🤵‍♀️",
    "🤵", "🤵‍♂️", "👸", "🤴", "🦸‍♀️", "🦸", "🦸‍♂️", "🦹‍♀️", "🦹", "🦹‍♂️", "🤶", "🎅", "🧑‍🎄", "🧙‍♀️", "🧙", "🧙‍♂️", "🧚‍♀️", "🧚", "🧚‍♂️", "🧛‍♀️",
    "🧛", "🧛‍♂️", "🧜‍♀️", "🧜", "🧜‍♂️", "🧝‍♀️", "🧝", "🧝‍♂️", "🧞‍♀️", "🧞", "🧞‍♂️", "🧟‍♀️", "🧟", "🧟‍♂️", "💆‍♀️", "💆", "💆‍♂️", "💇‍♀️", "💇", "💇‍♂️",
    "🚶‍♀️", "🚶", "🚶‍♂️", "🧍‍♀️", "🧍", "🧍‍♂️", "🧎‍♀️", "🧎", "🧎‍♂️", "🧑‍🦯", "👩‍🦯", "👨‍🦯", "🧑‍🦼", "👩‍🦼", "👨‍🦼", "🧑‍🦽", "👩‍🦽", "👨‍🦽",
    "❤️", "🧡", "💛", "💚", "💙", "💜", "🖤", "🤍", "🤎", "💔", "❤️‍🔥", "❤️‍🩹", "💕", "💞", "💓", "💗", "💖", "💘", "💝", "💟",
    "🚀", "🛸", "🛰️", "⛵", "🛶", "🚤", "🛥️", "🛳️", "⛴️", "🚢", "✈️", "🛩️", "🛫", "🛬", "🪂", "💺", "🚁", "🚟", "🚠", "🚡",
    "🏠", "🏡", "🏘️", "🏚️", "🏗️", "🏭", "🏢", "🏬", "🏣", "🏤", "🏥", "🏦", "🏨", "🏪", "🏫", "🏩", "💒",
    "🔥", "⭐", "🌟", "💫", "✨", "☄️", "☀️", "🌤️", "⛅", "🌥️", "🌦️", "🌧️", "⛈️", "🌩️", "🌨️", "❄️", "☃️", "⛄", "🌬️", "💨",
    "💧", "💦", "☔", "☂️", "🌊", "🌫️", "🍏", "🍎", "🍐", "🍊", "🍋", "🍌", "🍉", "🍇", "🍓", "🫐", "🍈", "🍒", "🍑", "🥭",
    "🍍", "🥥", "🥝", "🍅", "🍆", "🥑", "🥦", "🥬", "🥒", "🌶️", "🫑", "🌽", "🥕", "🫒", "🥔", "🍠", "🥐", "🥯", "🍞",
    "🥖", "🥨", "🧀", "🥚", "🍳", "🥞", "🧇", "🥓", "🥩", "🍗", "🍖", "🌭", "🍔", "🍟", "🍕", "🥪", "🫔", "🌮", "🌯",
    "🥗", "🥘", "🥫", "🍝", "🍜", "🍲", "🍛", "🍣", "🍱", "🥟", "🦪", "🍢", "🍙", "🍚", "🍘", "🍥",
    "🥠", "🥮", "🍡", "🍧", "🍨", "🍦", "🥧", "🧁", "🍰", "🎂", "🍮", "🍭", "🍬", "🍫", "🍿", "🍩", "🍪", "🌰", "🍯",
    "🥛", "🍼", "☕", "🍵", "🧃", "🥤", "🧋", "🍶", "🍺", "🍻", "🍷", "🍸", "🍹", "🍾", "🥃", "🧊", "🥢", "🍽️",
    "⚽", "🏀", "🏈", "⚾", "🥎", "🎾", "🏐", "🏉", "🥏", "🎱", "🪀", "🏓", "🏸", "🏒", "🏑", "🏏", "🥍", "🏹", "🎣", "🤿",
    "🥊", "🥋", "🛹", "🛼", "🛷", "⛸️", "🥌", "🎿", "⛷️", "🏂", "🏋️‍♀️", "🏋️", "🏋️‍♂️", "🤼‍♀️", "🤼", "🤼‍♂️", "🤸‍♀️", "🤸", "🤸‍♂️",
    "🚴‍♀️", "🚴", "🚴‍♂️", "🚵‍♀️", "🚵", "🚵‍♂️", "🧗‍♀️", "🧗", "🧗‍♂️", "🏌️‍♀️", "🏌️", "🏌️‍♂️", "🧘‍♀️", "🧘", "🧘‍♂️", "🏄‍♀️", "🏄", "🏄‍♂️", "🏊‍♀️", "🏊",
    "🏆", "🥇", "🥈", "🥉", "🏅", "🎖️", "🏵️", "🎗️", "🎫", "🎟️", "🎪", "🤹‍♀️", "🤹", "🤹‍♂️", "🎭", "🩰", "🎨", "🎬", "🎤", "🎧",
    "🎼", "🎹", "🥁", "🎷", "🎺", "🎸", "🪕", "🎻", "🎲", "♟️", "🎯", "🎳", "🎮", "🎰", "🧩", "🚗", "🚕", "🚙", "🚌", "🚎",
    "🏎️", "🚓", "🚑", "🚒", "🚐", "🛻", "🚚", "🚛", "🚜", "🦯", "🦽", "🦼", "🛴", "🚲", "🛵", "🏍️", "🛺", "🚨", "🚔", "🚍"
]

# ရိုးရှင်းသော Reaction ပေးနိုင်သော အဓိက အီမိုဂျီများ (Telegram supported emojis)
REACTION_EMOJIS = ["👍", "❤️", "🔥", "🥰", "👏", "😁", "🎉", "🤩", "💯"]

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

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    if chat:
        known_chats.add(chat.id)
    if user:
        known_users.add(user.id)
        
    settings = get_call_settings(chat.id)
    texts = LANGUAGES.get(settings['language'], LANGUAGES["🇲🇲"])
    name = user.first_name if user else "User"
    await update.message.reply_text(texts["start_text"].format(name=name), parse_mode='Markdown')

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await track_chats(update, context)
    message = update.message
    if not message:
        return
    chat = update.effective_chat
    user = update.effective_user
    text = message.text or message.caption or ""

    # Group ထဲတွင် စကားပြောလျှင် အီမိုဂျီဖြင့် Reaction ပေးခြင်း (Auto Reaction)
    if chat.type in ["group", "supergroup"] and user and not user.is_bot:
        try:
            chosen_emoji = random.choice(REACTION_EMOJIS)
            await context.bot.set_message_reaction(
                chat_id=chat.id,
                message_id=message.message_id,
                reaction=[ReactionTypeEmoji(emoji=chosen_emoji)]
            )
        except Exception as e:
            logger.error(f"Reaction Error: {e}")

    if chat.type in ["group", "supergroup"]:
        if any(link in text.lower() for link in ["http://", "https://", "t.me/", "www."]):
            if user and user.id not in OWNER_IDS:
                try:
                    await message.delete()
                    return
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
                logger.error(f"AI Error: {e}")

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
        emoji = random.choice(CALL_EMOJIS) if CALL_EMOJIS else "✨"
        mention = f"{emoji} [{name}](tg://user?id={member.id})"
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
    texts = LANGUAGES.get(settings))
    
    application.add_handler(CallbackQueryHandler(call_button_handler))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), message_handler))

    logger.info("Bot is starting...")
    application.run_polling()

if __name__ == '__main__':
    main()
