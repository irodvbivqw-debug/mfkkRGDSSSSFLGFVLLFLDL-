import asyncio
import logging
import os

from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPERATORS_GROUP_ID = int(os.getenv("OPERATORS_GROUP_ID"))
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))
CHANNEL_INVITE_LINK = os.getenv("CHANNEL_INVITE_LINK")
SUPPORT_USERNAME = os.getenv("SUPPORT_USERNAME")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x]
BOT_LINK = os.getenv("BOT_LINK")

logging.basicConfig(level=logging.INFO)
bot = Bot(BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

orders = {}
order_counter = 1
all_users: set[int] = set()

# ===================== STATES =====================
class UserState(StatesGroup):
    sale_type = State()
    phone = State()
    code = State()

class OperatorState(StatesGroup):
    cancel_reason = State()

class AdminState(StatesGroup):
    broadcast = State()

# ===================== KEYBOARDS =====================
main_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🐝 Сдать билайн")],
        [KeyboardButton(text="🆘 Поддержка")]
    ],
    resize_keyboard=True
)

cancel_kb = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="❌ Отменить сдачу")]],
    resize_keyboard=True
)

def sale_type_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(text="⚡ Сдать момент", callback_data="type_moment"),
            InlineKeyboardButton(text="⏳ Сдать холд", callback_data="type_hold")
        ]]
    )

def subscription_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📣 Подписаться на канал", url=CHANNEL_INVITE_LINK)],
            [InlineKeyboardButton(text="✅ Я подписался", callback_data="check_sub")]
        ]
    )

def operator_kb(order_id):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔑 Запросить код", callback_data=f"req_{order_id}")],
            [InlineKeyboardButton(text="❌ Отменить", callback_data=f"cancel_{order_id}")]
        ]
    )

def user_kb(order_id):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📝 Введите код", callback_data=f"code_{order_id}")],
            [InlineKeyboardButton(text="❌ Отменить сдачу", callback_data=f"user_cancel_{order_id}")]
        ]
    )

def support_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💬 Написать в поддержку", url=f"https://t.me/{SUPPORT_USERNAME.lstrip('@')}")]
        ]
    )

def welcome_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔮 Вечная ссылка на OMG", url=BOT_LINK)]
        ]
    )

# ===================== HELPERS =====================
async def is_subscribed(user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status in ("member", "administrator", "creator")
    except Exception:
        return False

def escape(text: str) -> str:
    for ch in r"\_*[]()~`>#+-=|{}.!":
        text = text.replace(ch, f"\\{ch}")
    return text

async def send_welcome(target, name: str):
    name_esc = escape(name)
    await target.answer(
        f"<tg-emoji emoji-id=\"5413694143601842851\">👋</tg-emoji> Привет, {name_esc}! Выбери действие:",
        parse_mode="HTML",
        reply_markup=main_kb
    )
    await target.answer(
        "🔮 *Вечная ссылка на бота*\n\n"
        "Актуальную ссылку на бота всегда можно найти по кнопке ниже\\.\n"
        "Не теряйте нас, даже при блокировке бота\\.",
        parse_mode="MarkdownV2",
        reply_markup=welcome_kb()
    )

# ===================== /start =====================
@dp.message(Command("start"))
async def start(message: types.Message, state: FSMContext):
    await state.clear()
    if not await is_subscribed(message.from_user.id):
        await message.answer(
            "⚠️ **Для использования бота необходимо подписаться на канал:**",
            parse_mode="MarkdownV2",
            reply_markup=subscription_kb()
        )
        return
    all_users.add(message.from_user.id)
    await send_welcome(message, message.from_user.first_name or "друг")

# ===================== SUBSCRIPTION =====================
@dp.callback_query(F.data == "check_sub")
async def check_subscription(callback: types.CallbackQuery, state: FSMContext):
    if not await is_subscribed(callback.from_user.id):
        await callback.answer("❌ Вы ещё не подписаны на канал!", show_alert=True)
        return
    all_users.add(callback.from_user.id)
    await callback.message.delete()
    await send_welcome(callback.message, callback.from_user.first_name or "друг")
    await callback.answer()

# ===================== SUPPORT =====================
@dp.message(F.text == "🆘 Поддержка")
async def support(message: types.Message):
    await message.answer(
        "**Нажмите кнопку ниже:**",
        parse_mode="MarkdownV2",
        reply_markup=support_kb()
    )

# ===================== BILKA =====================
@dp.message(F.text == "🐝 Сдать билайн")
async def bilka(message: types.Message, state: FSMContext):
    await state.set_state(UserState.sale_type)
    await message.answer(
        "**Билайн — выберите тип:**",
        parse_mode="MarkdownV2",
        reply_markup=sale_type_kb()
    )

@dp.callback_query(F.data.in_({"type_moment", "type_hold"}))
async def choose_sale_type(callback: types.CallbackQuery, state: FSMContext):
    sale_type = "Момент" if callback.data == "type_moment" else "Холд"
    await state.update_data(sale_type=sale_type)
    await state.set_state(UserState.phone)
    await callback.message.edit_text(
        f"**Тип:** {sale_type}",
        parse_mode="MarkdownV2"
    )
    await callback.message.answer(
        "📱 **Введите номер телефона:**",
        parse_mode="MarkdownV2",
        reply_markup=cancel_kb
    )
    await callback.answer()

# ===================== PHONE / CODE =====================
@dp.message(UserState.phone)
async def save_phone(message: types.Message, state: FSMContext):
    if message.text == "❌ Отменить сдачу":
        await state.clear()
        await message.answer("❌ **Сдача отменена\\.**", parse_mode="MarkdownV2", reply_markup=main_kb)
        return

    global order_counter
    username = f"@{message.from_user.username}" if message.from_user.username else f"id:{message.from_user.id}"
    order_id = order_counter
    order_counter += 1

    data = await state.get_data()
    sale_type = data.get("sale_type", "не указан")

    orders[order_id] = {
        "user_id": message.from_user.id,
        "phone": message.text,
        "username": username,
        "sale_type": sale_type,
        "status": "waiting_operator"
    }

    await bot.send_message(
        OPERATORS_GROUP_ID,
        f"**Новая заявка \\#{order_id}**\n"
        f"━━━━━━━━━━━━━━\n"
        f"👤 {escape(username)}\n"
        f"📱 {escape(message.text)}\n"
        f"🔖 {sale_type}",
        parse_mode="MarkdownV2",
        reply_markup=operator_kb(order_id)
    )

    await state.clear()
    await message.answer(
        "✅ **Номер принят\\.**\n\n"
        "> Ожидайте запроса кода от оператора\\.",
        parse_mode="MarkdownV2",
        reply_markup=main_kb
    )

@dp.callback_query(F.data.startswith("req_"))
async def request_code(callback: types.CallbackQuery):
    order_id = int(callback.data.split("_")[1])
    order = orders.get(order_id)
    if not order:
        return
    order["status"] = "waiting_code"
    await bot.send_message(
        order["user_id"],
        "🔔 **Оператор запрашивает код\\!**\n\n"
        "> Нажмите кнопку ниже и введите полученный код\\.",
        parse_mode="MarkdownV2",
        reply_markup=user_kb(order_id)
    )
    await callback.answer("Отправлено")

@dp.callback_query(F.data.startswith("code_"))
async def enter_code(callback: types.CallbackQuery, state: FSMContext):
    order_id = int(callback.data.split("_")[1])
    await state.update_data(order_id=order_id)
    await state.set_state(UserState.code)
    await callback.message.answer("📝 **Введите код:**", parse_mode="MarkdownV2")
    await callback.answer()

@dp.message(UserState.code)
async def receive_code(message: types.Message, state: FSMContext):
    data = await state.get_data()
    order_id = data["order_id"]
    order = orders[order_id]

    await bot.send_message(
        OPERATORS_GROUP_ID,
        f"**Код по заявке \\#{order_id}**\n"
        f"━━━━━━━━━━━━━━\n"
        f"📝 {escape(message.text)}",
        parse_mode="MarkdownV2",
        reply_markup=operator_kb(order_id)
    )
    order["status"] = "waiting_operator"
    await message.answer("✅ **Код отправлен\\.**", parse_mode="MarkdownV2")
    await state.clear()

# ===================== CANCEL (OPERATOR) =====================
@dp.callback_query(F.data.startswith("cancel_"))
async def cancel_start(callback: types.CallbackQuery, state: FSMContext):
    order_id = int(callback.data.split("_")[1])
    await state.update_data(order_id=order_id)
    await state.set_state(OperatorState.cancel_reason)
    await callback.message.reply(
        "✏️ **Введите причину отмены** \\(ответом на это сообщение\\):",
        parse_mode="MarkdownV2"
    )
    await callback.answer()

@dp.message(OperatorState.cancel_reason)
async def cancel_finish(message: types.Message, state: FSMContext):
    data = await state.get_data()
    order_id = data["order_id"]
    order = orders.get(order_id)
    if order:
        await bot.send_message(
            order["user_id"],
            f"❌ **Ваша заявка \\#{order_id} отменена\\.**\n\n"
            f"> 📋 Причина: {escape(message.text)}",
            parse_mode="MarkdownV2"
        )
        order["status"] = "cancelled"
    await message.answer(
        f"✅ **Заявка \\#{order_id} отменена\\.** Пользователь уведомлён\\.",
        parse_mode="MarkdownV2"
    )
    await state.clear()

# ===================== USER CANCEL =====================
@dp.callback_query(F.data.startswith("user_cancel_"))
async def user_cancel(callback: types.CallbackQuery, state: FSMContext):
    order_id = int(callback.data.split("_")[2])
    order = orders.get(order_id)
    if order:
        order["status"] = "cancelled"
        await bot.send_message(
            OPERATORS_GROUP_ID,
            f"⚠️ **Заявка \\#{order_id} отменена пользователем** {escape(order['username'])}",
            parse_mode="MarkdownV2"
        )
    await callback.message.edit_text("❌ **Заявка отменена\\.**", parse_mode="MarkdownV2")
    await callback.answer()
    await state.clear()

# ===================== ADMIN =====================
@dp.message(Command("admin"))
async def admin_panel(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("⛔ Нет доступа\\.", parse_mode="MarkdownV2")
        return
    await message.answer(
        f"🛠 **Админ\\-панель**\n\n"
        f"👥 Пользователей в базе: **{len(all_users)}**\n\n"
        f"`/broadcast` — рассылка всем пользователям",
        parse_mode="MarkdownV2"
    )

@dp.message(Command("broadcast"))
async def broadcast_start(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("⛔ Нет доступа\\.", parse_mode="MarkdownV2")
        return
    await state.set_state(AdminState.broadcast)
    await message.answer(
        "📢 **Введите сообщение для рассылки\\.**\n\n"
        "> Поддерживаются текст, фото, видео\\.\n\n"
        "Для отмены — /cancel",
        parse_mode="MarkdownV2"
    )

@dp.message(Command("cancel"), AdminState.broadcast)
async def broadcast_cancel(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ **Рассылка отменена\\.**", parse_mode="MarkdownV2")

@dp.message(AdminState.broadcast)
async def broadcast_do(message: types.Message, state: FSMContext):
    await state.clear()
    sent = 0
    failed = 0
    await message.answer(f"⏳ **Начинаю рассылку** {len(all_users)} пользователям\\.\\.\\.", parse_mode="MarkdownV2")
    for user_id in list(all_users):
        try:
            await message.copy_to(user_id)
            sent += 1
            await asyncio.sleep(0.05)
        except Exception:
            failed += 1
    await message.answer(
        f"✅ **Рассылка завершена\\!**\n\n"
        f"📨 Отправлено: **{sent}**\n"
        f"❌ Ошибок: **{failed}**",
        parse_mode="MarkdownV2"
    )

# ===================== MAIN =====================
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
