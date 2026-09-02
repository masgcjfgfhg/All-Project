import asyncio
import time
import os
import random
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
)
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.functions.account import ReportPeerRequest
from telethon.tl.types import (
    InputReportReasonSpam,
    InputReportReasonFake,
    InputReportReasonViolence,
    InputReportReasonPornography,
    InputReportReasonChildAbuse,
    InputReportReasonCopyright,
    InputReportReasonOther
)

BOT_TOKEN = "8552724867:AAHUVQanmWfr4VK7gtwRWp0TolGiVm44UXU"
OWNER_ID = 7420519058
API_ID = 30496983
API_HASH = "d60e848f7c20c866478b628c7ceeab56"

if not os.path.exists("sessions"):
    os.makedirs("sessions")

user_cooldowns = {}
admins = {}
unlimited_admins = set() # لیست ادمین‌های VIP (بدون محدودیت)

def get_healthy_accounts_count():
    return len([f for f in os.listdir("sessions") if f.endswith(".session")])

REP_TYPE = 1
REP_TARGET = 2
REP_REASON = 3
REP_CUSTOM_TEXT = 15  
REP_JOIN = 9
REP_VIEW = 10
REP_ACC_COUNT = 4
REP_PER_ACC = 5

ADD_PHONE = 6
ADD_CODE = 7
ADD_PASS = 8

ASK_ADMIN_ID = 11
ASK_ADMIN_TIME = 12
ASK_ADMIN_UNIT = 13
ASK_DEL_ACC = 14
ASK_VIP_ID = 16
ASK_UNVIP_ID = 17

temp_clients = {}

def is_admin(user_id):
    if user_id == OWNER_ID:
        return True
    if user_id in admins:
        if time.time() < admins[user_id]:
            return True
        else:
            del admins[user_id]
            if user_id in unlimited_admins:
                unlimited_admins.remove(user_id)
    return False

def get_reason_object(reason_str):
    mapping = {
        "rsn_spam": InputReportReasonSpam(),
        "rsn_fake": InputReportReasonFake(),
        "rsn_violence": InputReportReasonViolence(),
        "rsn_porn": InputReportReasonPornography(),
        "rsn_child": InputReportReasonChildAbuse(),
        "rsn_copy": InputReportReasonCopyright(),
        "rsn_other": InputReportReasonOther(),
        "rsn_scam": InputReportReasonOther()
    }
    return mapping.get(reason_str, InputReportReasonOther())

def get_report_text(reason, custom_text=None):
    if custom_text:
        return custom_text

    texts = {
        "rsn_spam": ["This account is sending unsolicited spam messages to users."],
        "rsn_fake": ["This entity is impersonating an official brand to deceive users. Please label as Fake."],
        "rsn_scam": ["Scam channel pretending to be a verified project to steal funds."],
        "rsn_violence": ["This channel is promoting violence and physical harm against individuals."],
        "rsn_porn": ["Posting explicit adult content and pornography."],
        "rsn_child": ["This account is sharing child abuse material. Please ban immediately."],
        "rsn_copy": ["This channel is distributing copyrighted material without permission."],
        "rsn_other": ["Engaging in illegal activities and violating platform rules."]
    }
    return random.choice(texts.get(reason, texts["rsn_other"]))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # قفل امنیتی: مسدود کردن کامل افراد غیر ادمین
    if not is_admin(user_id):
        text = "⛔️ شما اجازه استفاده از این ربات را ندارید."
        if update.callback_query:
            await update.callback_query.edit_message_text(text)
        else:
            await update.message.reply_text(text)
        return ConversationHandler.END

    keyboard = [
        [
            InlineKeyboardButton("Add Account", callback_data="add_acc"),
            InlineKeyboardButton("Reports", callback_data="open_reports_menu")
        ]
    ]
    if user_id == OWNER_ID:
        keyboard.append([
            InlineKeyboardButton("Bot Services", callback_data="admin_services"),
            InlineKeyboardButton("Show Status", callback_data="admin_status")
        ])
        keyboard.append([InlineKeyboardButton("Owner Panel", callback_data="owner_panel")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    text = "Hello, Welcome to Reporter Bot!"
    
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup)
    else:
        await update.message.reply_text(text, reply_markup=reply_markup)
    return ConversationHandler.END

async def main_menu_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id
    await query.answer()
    
    if not is_admin(user_id):
        await query.edit_message_text("⛔️ دسترسی غیرمجاز.")
        return ConversationHandler.END
        
    if query.data == "open_reports_menu":
        if user_id != OWNER_ID and user_id not in unlimited_admins and user_id in user_cooldowns:
            if time.time() < user_cooldowns[user_id]:
                left_mins = int((user_cooldowns[user_id] - time.time()) / 60)
                msg = f"⏱ شما در محدودیت هستید. لطفاً {left_mins} دقیقه دیگر تلاش کنید."
                await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="back_to_main")]]))
                return ConversationHandler.END
                
        reports_keyboard = [
            [InlineKeyboardButton("TeleThon ( CH/GP )", callback_data="rep_telethon_ch"), InlineKeyboardButton("TeleThon ( BOT )", callback_data="rep_telethon_bot")],
            [InlineKeyboardButton("NO Text Telethon ( Scam )", callback_data="rep_scam")],
            [InlineKeyboardButton("Mass Report - Fast", callback_data="rep_mass")],
            [InlineKeyboardButton("Private Report", callback_data="rep_pv"), InlineKeyboardButton("Report Profile ( AC )", callback_data="rep_prof_ac")],
            [InlineKeyboardButton("Back", callback_data="back_to_main")]
        ]
        await query.edit_message_text("متد ریپورت خود را انتخاب کنید:", reply_markup=InlineKeyboardMarkup(reports_keyboard))
        
    elif query.data == "owner_panel" and user_id == OWNER_ID:
        panel_kb = [
            [InlineKeyboardButton("Accounts Status", callback_data="panel_status"), InlineKeyboardButton("Test Accounts", callback_data="panel_test_accs")],
            [InlineKeyboardButton("Delete Account", callback_data="panel_del_acc_btn")],
            [InlineKeyboardButton("Admins List", callback_data="panel_admins")],
            [InlineKeyboardButton("Add Admin", callback_data="panel_add_admin"), InlineKeyboardButton("Delete Admin", callback_data="panel_del_admin")],
            [InlineKeyboardButton("🌟 VIP Admin (No Limit)", callback_data="panel_vip_admin"), InlineKeyboardButton("⏱ Normal Admin", callback_data="panel_unvip_admin")],
            [InlineKeyboardButton("Back", callback_data="back_to_main")]
        ]
        await query.edit_message_text("پنل مدیریت مالک ربات:\nلطفاً از دکمه‌های زیر استفاده کنید:", reply_markup=InlineKeyboardMarkup(panel_kb))

    elif query.data == "panel_test_accs" and user_id == OWNER_ID:
        await query.edit_message_text("در حال بررسی وضعیت اکانت‌ها...\n(این عملیات ممکن است کمی زمان ببرد)")
        alive = 0
        dead = 0
        for file in os.listdir("sessions"):
            if file.endswith(".session"):
                phone = file.replace(".session", "")
                client = TelegramClient(f"sessions/{phone}", API_ID, API_HASH)
                try:
                    await client.connect()
                    if await client.is_user_authorized():
                        alive += 1
                    else:
                        dead += 1
                        os.remove(f"sessions/{file}")
                    await client.disconnect()
                except:
                    dead += 1
                    if os.path.exists(f"sessions/{file}"):
                        os.remove(f"sessions/{file}")
        
        text = f"بررسی سلامت اکانت‌ها به پایان رسید.\nسالم و فعال: {alive} اکانت\nخراب و حذف شده: {dead} اکانت"
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="owner_panel")]]))
        
    elif query.data == "panel_admins" and user_id == OWNER_ID:
        if not admins:
            txt = "هیچ ادمینی وجود ندارد."
        else:
            txt = "لیست ادمین‌ها:\n"
            for aid, ext in admins.items():
                if time.time() < ext:
                    left = int((ext - time.time()) / 60)
                    vip_status = " 🌟 (VIP)" if aid in unlimited_admins else " ⏱ (عادی)"
                    if left > 60:
                        txt += f"- ID: {aid} ({left // 60} ساعت و {left % 60} دقیقه){vip_status}\n"
                    else:
                        txt += f"- ID: {aid} ({left} دقیقه){vip_status}\n"
        await query.edit_message_text(txt, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="owner_panel")]]))

    elif query.data == "panel_del_admin" and user_id == OWNER_ID:
        if not admins:
            await query.edit_message_text("لیست ادمین‌ها خالی است.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="owner_panel")]]))
            return
        kb = [[InlineKeyboardButton(f"حذف ادمین: {aid}", callback_data=f"deladm_{aid}")] for aid in admins.keys()]
        kb.append([InlineKeyboardButton("Back", callback_data="owner_panel")])
        await query.edit_message_text("برای حذف، روی ادمین مورد نظر کلیک کنید:", reply_markup=InlineKeyboardMarkup(kb))
        
    elif query.data.startswith("deladm_") and user_id == OWNER_ID:
        target_id = int(query.data.split("_")[1])
        if target_id in admins:
            del admins[target_id]
        if target_id in unlimited_admins:
            unlimited_admins.remove(target_id)
        kb = [[InlineKeyboardButton(f"حذف ادمین: {aid}", callback_data=f"deladm_{aid}")] for aid in admins.keys()]
        kb.append([InlineKeyboardButton("Back", callback_data="owner_panel")])
        text_msg = "ادمین با موفقیت حذف شد." if admins else "همه ادمین‌ها حذف شدند."
        await query.edit_message_text(text_msg, reply_markup=InlineKeyboardMarkup(kb))

    elif query.data == "panel_status":
        txt = f"اکانت‌های متصل شده و سالم: {get_healthy_accounts_count()} عدد"
        await query.edit_message_text(txt, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="owner_panel")]]))
        
    elif query.data == "back_to_main":
        await start(update, context)

# ================== ADD ACCOUNT ==================
async def add_acc_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id): return ConversationHandler.END
    await query.edit_message_text("شماره تلفن اکانت تلگرام را با پیش‌شماره (مثلاً +989123456789) وارد کنید:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Cancel", callback_data="cancel_conv")]]))
    return ADD_PHONE

async def acc_receive_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    phone = update.message.text.replace(" ", "").replace("+", "")
    context.user_data['acc_phone'] = phone
    msg = await update.message.reply_text("در حال اتصال به سرور تلگرام و ارسال کد...")
    
    try:
        client = TelegramClient(f"sessions/{phone}", API_ID, API_HASH)
        await client.connect()
        if not await client.is_user_authorized():
            send_code_result = await client.send_code_request(phone)
            context.user_data['phone_code_hash'] = send_code_result.phone_code_hash
            temp_clients[phone] = client
            await msg.edit_text("کد ۵ رقمی ارسال شده به تلگرام را وارد کنید:\n(کد را دقیقاً ارسال کنید)", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Cancel", callback_data="cancel_conv")]]))
            return ADD_CODE
        else:
            await client.disconnect()
            await msg.edit_text("این اکانت از قبل لاگین شده و در دیتابیس موجود است.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Main Menu", callback_data="back_to_main")]]))
            return ConversationHandler.END
    except Exception as e:
        await msg.edit_text(f"خطا در ارسال کد:\n{str(e)}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Cancel", callback_data="cancel_conv")]]))
        return ConversationHandler.END

async def acc_receive_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    code = update.message.text
    phone = context.user_data['acc_phone']
    phone_code_hash = context.user_data['phone_code_hash']
    client = temp_clients.get(phone)
    
    msg = await update.message.reply_text("در حال بررسی کد...")
    try:
        await client.sign_in(phone=phone, code=code, phone_code_hash=phone_code_hash)
        await client.disconnect()
        del temp_clients[phone]
        await msg.edit_text("اکانت با موفقیت لاگین و به دیتابیس اضافه شد!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Main Menu", callback_data="back_to_main")]]))
        return ConversationHandler.END
    except SessionPasswordNeededError:
        await msg.edit_text("این اکانت دارای تایید دو مرحله‌ای است. لطفاً رمز (Password) را ارسال کنید:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Cancel", callback_data="cancel_conv")]]))
        return ADD_PASS
    except Exception as e:
        await msg.edit_text(f"کد اشتباه است یا مشکلی پیش آمد:\n{str(e)}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Cancel", callback_data="cancel_conv")]]))
        return ADD_CODE

async def acc_receive_pass(update: Update, context: ContextTypes.DEFAULT_TYPE):
    password = update.message.text
    phone = context.user_data['acc_phone']
    client = temp_clients.get(phone)
    msg = await update.message.reply_text("در حال تایید رمز...")
    try:
        await client.sign_in(password=password)
        await client.disconnect()
        del temp_clients[phone]
        await msg.edit_text("اکانت با موفقیت لاگین و به دیتابیس اضافه شد!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Main Menu", callback_data="back_to_main")]]))
        return ConversationHandler.END
    except Exception as e:
        await msg.edit_text(f"رمز اشتباه است:\n{str(e)}\nمجدداً ارسال کنید:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Cancel", callback_data="cancel_conv")]]))
        return ADD_PASS

# ================== REPORT CONVERSATION ==================
async def report_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id): return ConversationHandler.END
    
    if get_healthy_accounts_count() == 0:
        await query.edit_message_text("هیچ اکانتی در دیتابیس موجود نیست. ابتدا از طریق Add Account اکانت اضافه کنید.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="back_to_main")]]))
        return ConversationHandler.END
        
    context.user_data['method'] = query.data
    target_type_kb = [
        [InlineKeyboardButton("Report Channel/Group", callback_data="tt_channel")],
        [InlineKeyboardButton("Report Posts", callback_data="tt_post")],
        [InlineKeyboardButton("Report Profile/Account", callback_data="tt_account")],
        [InlineKeyboardButton("Cancel", callback_data="cancel_conv")]
    ]
    await query.edit_message_text("نوع تارگت را مشخص کنید:", reply_markup=InlineKeyboardMarkup(target_type_kb))
    return REP_TYPE

async def receive_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['target_type'] = query.data
    
    msg = "لینک کانال یا گروه را ارسال کنید:" if query.data in ["tt_channel", "tt_post"] else "شماره اکانت یا آیدی عددی اکانت شخص را ارسال کنید:"
    await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Cancel", callback_data="cancel_conv")]]))
    return REP_TARGET

async def receive_target(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['target'] = update.message.text
    reasons_kb = [
        [InlineKeyboardButton("Spam", callback_data="rsn_spam"), InlineKeyboardButton("Fake", callback_data="rsn_fake")],
        [InlineKeyboardButton("Violence", callback_data="rsn_violence"), InlineKeyboardButton("Pornography", callback_data="rsn_porn")],
        [InlineKeyboardButton("Child Abuse", callback_data="rsn_child"), InlineKeyboardButton("Copyright", callback_data="rsn_copy")],
        [InlineKeyboardButton("Other", callback_data="rsn_other"), InlineKeyboardButton("Scam", callback_data="rsn_scam")],
        [InlineKeyboardButton("Cancel", callback_data="cancel_conv")]
    ]
    await update.message.reply_text("دلیل ریپورت را انتخاب کنید:", reply_markup=InlineKeyboardMarkup(reasons_kb))
    return REP_REASON

async def receive_reason(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['reason'] = query.data
    
    custom_text_kb = [
        [InlineKeyboardButton("ندارم (استفاده از متن ربات)", callback_data="no_custom_text")],
        [InlineKeyboardButton("Cancel", callback_data="cancel_conv")]
    ]
    await query.edit_message_text(
        "آیا متن ریپورت اختصاصی (به زبان انگلیسی) دارید؟\nاگر دارید همین الان متن را ارسال کنید.\nدر غیر این صورت روی دکمه «ندارم» کلیک کنید:", 
        reply_markup=InlineKeyboardMarkup(custom_text_kb)
    )
    return REP_CUSTOM_TEXT

async def receive_custom_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    is_callback = False
    if update.callback_query and update.callback_query.data == "no_custom_text":
        await update.callback_query.answer()
        context.user_data['custom_text'] = None
        msg_target = update.callback_query
        is_callback = True
    else:
        context.user_data['custom_text'] = update.message.text
        msg_target = update.message
        
    ttype = context.user_data['target_type']
    
    if ttype in ["tt_channel", "tt_post"]:
        join_kb = [
            [InlineKeyboardButton("بله، جوین بشه", callback_data="join_yes"), InlineKeyboardButton("نه، جوین نشه", callback_data="join_no")],
            [InlineKeyboardButton("Cancel", callback_data="cancel_conv")]
        ]
        text = "آیا اکانت‌ها قبل از ریپورت، در کانال/گروه جوین شوند؟"
        if is_callback:
            await msg_target.edit_message_text(text, reply_markup=InlineKeyboardMarkup(join_kb))
        else:
            await msg_target.reply_text(text, reply_markup=InlineKeyboardMarkup(join_kb))
        return REP_JOIN
    else:
        text = f"تعداد اکانت برای عملیات (موجودی: {get_healthy_accounts_count()}):"
        if is_callback:
            await msg_target.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Cancel", callback_data="cancel_conv")]]))
        else:
            await msg_target.reply_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Cancel", callback_data="cancel_conv")]]))
        return REP_ACC_COUNT

async def receive_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['do_join'] = query.data
    view_kb = [
        [InlineKeyboardButton("بله، ویو بزنه", callback_data="view_yes"), InlineKeyboardButton("نه، ویو نزنه", callback_data="view_no")],
        [InlineKeyboardButton("Cancel", callback_data="cancel_conv")]
    ]
    await query.edit_message_text("آیا اکانت‌ها پست‌ها را ویو بزنند؟", reply_markup=InlineKeyboardMarkup(view_kb))
    return REP_VIEW

async def receive_view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['do_view'] = query.data
    await query.edit_message_text(f"تعداد اکانت برای عملیات (موجودی: {get_healthy_accounts_count()}):", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Cancel", callback_data="cancel_conv")]]))
    return REP_ACC_COUNT

async def receive_acc_count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.text.isdigit():
        await update.message.reply_text("فقط عدد ارسال کنید:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Cancel", callback_data="cancel_conv")]]))
        return REP_ACC_COUNT
        
    req_count = int(update.message.text)
    available = get_healthy_accounts_count()
    if req_count > available:
        await update.message.reply_text(f"تعداد بیشتر از موجودی شماست ({available}). عدد کمتری وارد کنید:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Cancel", callback_data="cancel_conv")]]))
        return REP_ACC_COUNT
        
    context.user_data['count'] = req_count
    ttype = context.user_data['target_type']
    max_r = 1 if ttype == "tt_post" else 3
    
    await update.message.reply_text(f"هر اکانت چند بار ریپورت ارسال کند؟ (حداکثر: {max_r})", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Cancel", callback_data="cancel_conv")]]))
    return REP_PER_ACC

async def receive_per_acc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.text.isdigit():
        return REP_PER_ACC
        
    reports_per_acc = int(update.message.text)
    ttype = context.user_data['target_type']
    max_r = 1 if ttype == "tt_post" else 3
    
    if reports_per_acc > max_r:
        await update.message.reply_text(f"بیشتر از {max_r} مجاز نیست. عدد کمتری وارد کنید:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Cancel", callback_data="cancel_conv")]]))
        return REP_PER_ACC
        
    user_id = update.effective_user.id
    acc_count = context.user_data['count']
    target_link = context.user_data['target']
    reason_code = context.user_data['reason']
    custom_text = context.user_data.get('custom_text')
    report_reason_obj = get_reason_object(reason_code)
    
    msg = await update.message.reply_text("درحال اجرای ریپورت واقعی و برقراری ارتباط با سرور تلگرام...")
    
    # اعمال محدودیت برای ادمین‌های عادی (غیر VIP و غیر مالک)
    if user_id != OWNER_ID and user_id not in unlimited_admins:
        user_cooldowns[user_id] = time.time() + (20 * 60)
        
    approved = 0
    all_sessions = [f for f in os.listdir("sessions") if f.endswith(".session")][:acc_count]
    
    for idx, session_file in enumerate(all_sessions, 1):
        phone = session_file.replace(".session", "")
        client = TelegramClient(f"sessions/{phone}", API_ID, API_HASH)
        
        try:
            await client.connect()
            if not await client.is_user_authorized():
                await client.disconnect()
                continue
                
            try:
                target_entity = await client.get_entity(target_link)
            except ValueError:
                target_entity = target_link
                
            if context.user_data.get('do_join') == 'join_yes' and ttype in ["tt_channel", "tt_post"]:
                try:
                    await client(JoinChannelRequest(target_entity))
                    await asyncio.sleep(1)
                except Exception:
                    pass
                    
            if context.user_data.get('do_view') == 'view_yes' and ttype in ["tt_channel", "tt_post"]:
                try:
                    msgs = await client.get_messages(target_entity, limit=10)
                    if msgs:
                        await client.send_read_acknowledge(target_entity, max_id=msgs[0].id)
                    await asyncio.sleep(1)
                except Exception:
                    pass
                    
            for _ in range(reports_per_acc):
                try:
                    report_text = get_report_text(reason_code, custom_text)
                    await client(ReportPeerRequest(peer=target_entity, reason=report_reason_obj, message=report_text))
                    approved += 1
                    await asyncio.sleep(1)
                except Exception:
                    pass
                    
            await client.disconnect()
            
        except Exception:
            if client.is_connected():
                await client.disconnect()
        
        percent = int((idx / acc_count) * 100)
        live_text = f"گزارش زنده:\nاکانت بررسی شده: {idx} از {acc_count}\nگزارش‌های موفق ارسالی به سرور: {approved}\nدرصد پیشرفت: {percent}%"
        if idx % 2 == 0 or idx == acc_count:
            try:
                await msg.edit_text(live_text)
            except Exception:
                pass
                
    final_text = "عملیات ریپورت واقعی با موفقیت پایان یافت."
    if user_id != OWNER_ID and user_id not in unlimited_admins:
        final_text += "\n⏱ شما به مدت ۲۰ دقیقه محدود شدید."
        
    await msg.reply_text(final_text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Main Menu", callback_data="back_to_main")]]))
    return ConversationHandler.END

# ================== OWNER CONVERSATION ==================
async def admin_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if len(admins) >= 14:
        await query.edit_message_text("ظرفیت ادمین‌ها پر است (حداکثر ۱۴ نفر).", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="owner_panel")]]))
        return ConversationHandler.END
    await query.edit_message_text("آیدی عددی کاربر را بفرستید:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Cancel", callback_data="cancel_owner_action")]]))
    return ASK_ADMIN_ID

async def admin_receive_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.text.isdigit(): return ASK_ADMIN_ID
    context.user_data['new_admin_id'] = int(update.message.text)
    await update.message.reply_text("زمان را به صورت عدد وارد کنید:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Cancel", callback_data="cancel_owner_action")]]))
    return ASK_ADMIN_TIME

async def admin_receive_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.text.isdigit(): return ASK_ADMIN_TIME
    context.user_data['new_admin_time'] = float(update.message.text)
    unit_kb = [
        [InlineKeyboardButton("دقیقه", callback_data="au_m")], [InlineKeyboardButton("ساعت", callback_data="au_h")],
        [InlineKeyboardButton("روز", callback_data="au_d")], [InlineKeyboardButton("Cancel", callback_data="cancel_owner_action")]
    ]
    await update.message.reply_text("واحد زمان:", reply_markup=InlineKeyboardMarkup(unit_kb))
    return ASK_ADMIN_UNIT

async def admin_receive_unit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    new_id = context.user_data['new_admin_id']
    amount = context.user_data['new_admin_time']
    unit = query.data.split("_")[1]
    
    secs = amount * 60 if unit == 'm' else amount * 3600 if unit == 'h' else amount * 86400
    admins[new_id] = time.time() + secs
    await query.edit_message_text(f"کاربر {new_id} با موفقیت به لیست ادمین‌های عادی (با محدودیت ۲۰ دقیقه‌ای) اضافه شد.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back to Panel", callback_data="owner_panel")]]))
    return ConversationHandler.END

async def vip_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("آیدی عددی ادمینی که می‌خواهید به حالت 🌟 VIP (بدون محدودیت) دربیاید را وارد کنید:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Cancel", callback_data="cancel_owner_action")]]))
    return ASK_VIP_ID

async def vip_receive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.text.isdigit(): return ASK_VIP_ID
    target_id = int(update.message.text)
    unlimited_admins.add(target_id)
    if target_id in user_cooldowns:
        del user_cooldowns[target_id]
    await update.message.reply_text(f"ادمین {target_id} اکنون 🌟 VIP است و هیچ محدودیت زمانی ندارد.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back to Panel", callback_data="owner_panel")]]))
    return ConversationHandler.END

async def unvip_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("آیدی عددی ادمینی که می‌خواهید به حالت ⏱ عادی (محدودیت ۲۰ دقیقه‌ای) برگردد را وارد کنید:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Cancel", callback_data="cancel_owner_action")]]))
    return ASK_UNVIP_ID

async def unvip_receive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.text.isdigit(): return ASK_UNVIP_ID
    target_id = int(update.message.text)
    if target_id in unlimited_admins:
        unlimited_admins.remove(target_id)
    await update.message.reply_text(f"ادمین {target_id} به حالت ⏱ عادی برگشت.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back to Panel", callback_data="owner_panel")]]))
    return ConversationHandler.END

async def del_acc_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("شماره اکانتی که قصد حذف آن را دارید دقیقاً وارد کنید (مثلاً 989123456789):", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Cancel", callback_data="cancel_owner_action")]]))
    return ASK_DEL_ACC

async def del_acc_receive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    phone = update.message.text.replace(" ", "").replace("+", "")
    target_file = f"sessions/{phone}.session"
    
    if os.path.exists(target_file):
        os.remove(target_file)
        await update.message.reply_text("اکانت مورد نظر با موفقیت از سیستم حذف شد.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back to Panel", callback_data="owner_panel")]]))
    else:
        await update.message.reply_text("این شماره در دیتابیس یافت نشد.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back to Panel", callback_data="owner_panel")]]))
    return ConversationHandler.END

async def cancel_conv_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    phone = context.user_data.get('acc_phone')
    if phone and phone in temp_clients:
        await temp_clients[phone].disconnect()
        del temp_clients[phone]
        
    await query.edit_message_text("عملیات لغو شد.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Main Menu", callback_data="back_to_main")]]))
    return ConversationHandler.END

async def cancel_owner_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text("عملیات لغو شد.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back to Panel", callback_data="owner_panel")]]))
    return ConversationHandler.END

if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    add_acc_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(add_acc_start, pattern="^add_acc$")],
        states={
            ADD_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, acc_receive_phone)],
            ADD_CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, acc_receive_code)],
            ADD_PASS: [MessageHandler(filters.TEXT & ~filters.COMMAND, acc_receive_pass)]
        },
        fallbacks=[CallbackQueryHandler(cancel_conv_callback, pattern="^cancel_conv$")]
    )
    
    report_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(report_start, pattern="^rep_")],
        states={
            REP_TYPE: [CallbackQueryHandler(receive_type, pattern="^tt_")],
            REP_TARGET: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_target)],
            REP_REASON: [CallbackQueryHandler(receive_reason, pattern="^rsn_")],
            REP_CUSTOM_TEXT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_custom_text),
                CallbackQueryHandler(receive_custom_text, pattern="^no_custom_text$")
            ],
            REP_JOIN: [CallbackQueryHandler(receive_join, pattern="^join_")],
            REP_VIEW: [CallbackQueryHandler(receive_view, pattern="^view_")],
            REP_ACC_COUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_acc_count)],
            REP_PER_ACC: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_per_acc)]
        },
        fallbacks=[CallbackQueryHandler(cancel_conv_callback, pattern="^cancel_conv$")]
    )
    
    owner_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(admin_start, pattern="^panel_add_admin$"),
            CallbackQueryHandler(del_acc_start, pattern="^panel_del_acc_btn$"),
            CallbackQueryHandler(vip_start, pattern="^panel_vip_admin$"),
            CallbackQueryHandler(unvip_start, pattern="^panel_unvip_admin$")
        ],
        states={
            ASK_ADMIN_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_receive_id)],
            ASK_ADMIN_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_receive_time)],
            ASK_ADMIN_UNIT: [CallbackQueryHandler(admin_receive_unit, pattern="^au_")],
            ASK_DEL_ACC: [MessageHandler(filters.TEXT & ~filters.COMMAND, del_acc_receive)],
            ASK_VIP_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, vip_receive)],
            ASK_UNVIP_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, unvip_receive)]
        },
        fallbacks=[CallbackQueryHandler(cancel_owner_callback, pattern="^cancel_owner_action$")]
    )
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(add_acc_conv)
    app.add_handler(report_conv)
    app.add_handler(owner_conv)
    app.add_handler(CallbackQueryHandler(main_menu_buttons))
    
    app.run_polling()
