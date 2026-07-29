import asyncio
import logging
import os
import re

from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPERATORS_GROUP_ID = int(os.getenv("OPERATORS_GROUP_ID"))
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))
CHANNEL_INVITE_LINK = os.getenv("CHANNEL_INVITE_LINK")
SUPPORT_USERNAME = os.getenv("SUPPORT_USERNAME")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x]
BOT_LINK = os.getenv("BOT_LINK")
FAQ_LINK = "https://t.me/+uu37yAQxUFM2YzMy"

logging.basicConfig(level=logging.INFO)
bot = Bot(BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

orders = {}
order_counter = 1
all_users: set[int] = set()
pinned_users: set[int] = set()

# Хранилище балансов пользователей (user_id -> float)
user_balances = {}

BEELINE_PREFIXES = {
    "900", "902", "903", "904", "905", "906", "908", "909", 
    "950", "951", "953", "960", "961", "962", "963", "964", 
    "965", "966", "967", "968", "969", "976", "980", "983", "986"
}

def is_beeline_number(phone_str: str) -> bool:
    digits = re.sub(r'\D', '', phone_str)
    if len(digits) == 11 and digits[0] in ('7', '8'):
        prefix = digits[1:4]
        return prefix in BEELINE_PREFIXES
    return False

# ===================== STATES =====================
class UserState(StatesGroup):
    sale_type = State()
    phone = State()
    code = State()
    withdraw_amount = State()

class OperatorState(StatesGroup):
    cancel_reason = State()
    credit_amount = State()  # Для ввода суммы зачёта

class AdminState(StatesGroup):
    broadcast = State()

# ===================== KEYBOARDS =====================
BTN_SUBMIT = "Сдать билайн"
BTN_PROFILE = "Мой профиль"
BTN_SUPPORT = "Написать в поддержку"
BTN_CANCEL = "❌ Отменить сдачу"

def main_kb():
    builder = ReplyKeyboardBuilder()
    builder.button(
        text=BTN_SUBMIT,
        style="success",
        icon_custom_emoji_id="5409227184340476957"
    )
    builder.button(
        text=BTN_PROFILE,
        style="primary",
        icon_custom_emoji_id="5415594207068822547"
    )
    builder.button(
        text=BTN_SUPPORT,
        style="danger",
        icon_custom_emoji_id="5444965061749644170"
    )
    builder.adjust(1, 2)
    return builder.as_markup(resize_keyboard=True)

cancel_kb = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text=BTN_CANCEL)]],
    resize_keyboard=True
)

def sale_type_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(
                text="Сдать момент - 17$",
                callback_data="type_moment",
                icon_custom_emoji_id="5431449001532594346",
                style="danger"
            ),
            InlineKeyboardButton(
                text="Сдать холд - 23$",
                callback_data="type_hold",
                icon_custom_emoji_id="5433737699410319194",
                style="primary"
            )
        ]]
    )

def subscription_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text="Подписаться на канал",
                url=CHANNEL_INVITE_LINK,
                icon_custom_emoji_id="5444965061749644170",
                style="danger"
            )],
            [InlineKeyboardButton(
                text="Я подписался",
                callback_data="check_sub",
                icon_custom_emoji_id="5413482938585063042",
                style="success"
            )]
        ]
    )

def operator_kb(order_id):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Зачесть",
                    callback_data=f"credit_{order_id}",
                    icon_custom_emoji_id="5413482938585063042",
                    style="success"
                ),
                InlineKeyboardButton(
                    text="Запросить код",
                    callback_data=f"req_{order_id}",
                    icon_custom_emoji_id="5242628160297641831",
                    style="primary"
                )
            ],
            [
                InlineKeyboardButton(
                    text="Отменить",
                    callback_data=f"cancel_{order_id}",
                    icon_custom_emoji_id="5465665476971471368",
                    style="danger"
                )
            ]
        ]
    )

def user_kb(order_id):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text="Ввести код",
                callback_data=f"code_{order_id}",
                icon_custom_emoji_id="5334882760735598374",
                style="primary"
            )],
            [InlineKeyboardButton(
                text="Отменить сдачу",
                callback_data=f"user_cancel_{order_id}",
                icon_custom_emoji_id="5465665476971471368",
                style="danger"
            )]
        ]
    )

def support_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text="Написать в поддержку",
                url=f"https://t.me/{SUPPORT_USERNAME.lstrip('@')}",
                icon_custom_emoji_id="5361837567463399422",
                style="primary"
            )]
        ]
    )

def faq_btn():
    return InlineKeyboardButton(
        text="FAQ",
        url=FAQ_LINK,
        icon_custom_emoji_id="5314504236132747481",
        style="danger"
    )

def welcome_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text="Вечная ссылка на OMG",
                url=BOT_LINK,
                icon_custom_emoji_id="5361837567463399422",
                style="primary"
            )],
            [faq_btn()]
        ]
    )

def profile_inline_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💸 Вывести баланс",
                    callback_data="withdraw_start",
                    icon_custom_emoji_id="5382199784075448966"
                )
            ]
        ]
    )

def withdraw_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⚡️ Вывести весь баланс",
                    callback_data="withdraw_all",
                    icon_custom_emoji_id="5456140674028019486",
                    style="danger"
                ),
                InlineKeyboardButton(
                    text="🧾 Указать сумму",
                    callback_data="withdraw_custom",
                    icon_custom_emoji_id="5444856076954520455",
                    style="success"
                )
            ]
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

async def send_welcome(target, name: str, user_id: int):
    name_esc = escape(name)
    await target.answer(
        f'<tg-emoji emoji-id="5413694143601842851">👋</tg-emoji> <b>Привет, {name_esc}! Выбери действие:</b>',
        parse_mode="HTML",
        reply_markup=main_kb()
    )
    
    pinned_msg = await target.answer(
        f'<tg-emoji emoji-id="5361837567463399422">🔮</tg-emoji> <b>Вечная ссылка на бота</b>\n\n'
        "Актуальную ссылку на бота всегда можно найти по кнопке ниже.\n"
        "Не теряйте нас, даже при блокировке.",
        parse_mode="HTML",
        reply_markup=welcome_kb()
    )
    
    if user_id not in pinned_users:
        try:
            await bot.pin_chat_message(
                chat_id=pinned_msg.chat.id,
                message_id=pinned_msg.message_id,
                disable_notification=True
            )
            pinned_users.add(user_id)
            await bot.delete_message(chat_id=pinned_msg.chat.id, message_id=pinned_msg.message_id + 1)
        except Exception:
            pass

# ===================== /start =====================
@dp.message(Command("start"))
async def start(message: types.Message, state: FSMContext):
    await state.clear()
    if not await is_subscribed(message.from_user.id):
        await message.answer(
            '<tg-emoji emoji-id="5274099962655816924">❗️</tg-emoji> <b>Для использования бота необходимо подписаться на канал:</b>',
            parse_mode="HTML",
            reply_markup=subscription_kb()
        )
        return
    all_users.add(message.from_user.id)
    await send_welcome(message, message.from_user.first_name or "друг", message.from_user.id)

# ===================== SUBSCRIPTION =====================
@dp.callback_query(F.data == "check_sub")
async def check_subscription(callback: types.CallbackQuery, state: FSMContext):
    if not await is_subscribed(callback.from_user.id):
        await callback.answer("❌ Вы ещё не подписаны на канал!", show_alert=True)
        return
    all_users.add(callback.from_user.id)
    await callback.message.delete()
    await send_welcome(callback.message, callback.from_user.first_name or "друг", callback.from_user.id)
    await callback.answer()

# ===================== PROFILE =====================
@dp.message(F.text == BTN_PROFILE)
async def profile(message: types.Message):
    user_id = message.from_user.id
    user_orders = [o for o in orders.values() if o.get("user_id") == user_id]
    
    paid_count = len([o for o in user_orders if o.get("status") == "paid"])
    cancelled_count = len([o for o in user_orders if o.get("status") == "cancelled"])
    
    user_balance = user_balances.get(user_id, 0.0)
    username = f"@{message.from_user.username}" if message.from_user.username else f"id:{user_id}"

    text = (
        f'<b><tg-emoji emoji-id="5472178859300363509">🏖️</tg-emoji> Профиль {username}</b>\n\n'
        f'<b><tg-emoji emoji-id="5233326571099534068">💸</tg-emoji> Баланс {user_balance:.1f} USDT</b>\n\n'
        f'<b><tg-emoji emoji-id="5298520596945070277">📊</tg-emoji> Всего сдано <code>~ ~ ~</code></b>\n\n'
        f'<blockquote><b><tg-emoji emoji-id="5395348109192601035">👌</tg-emoji> Которые выплчены {paid_count}\n'
        f'<tg-emoji emoji-id="5409023834818878389">👎</tg-emoji> Которые отменили {cancelled_count}</b></blockquote>'
    )

    # Показываем кнопку "Вывести баланс" только если баланс > 0
    markup = profile_inline_kb() if user_balance > 0 else None

    await message.answer(text, parse_mode="HTML", reply_markup=markup)

# ===================== WITHDRAW =====================
@dp.callback_query(F.data == "withdraw_start")
async def withdraw_start(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    user_balance = user_balances.get(user_id, 0.0)

    if user_balance <= 0:
        await callback.answer("У вас нулевой баланс!", show_alert=True)
        return

    text = (
        f'<tg-emoji emoji-id="5420323339723881652">⚠️</tg-emoji> '
        f'<b>Вы выводите баланс с бота ({user_balance:.1f} USDT), как желаете вывести?</b>'
    )

    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=withdraw_kb()
    )
    await callback.answer()

@dp.callback_query(F.data == "withdraw_all")
async def withdraw_all_handler(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    user_balance = user_balances.get(user_id, 0.0)
    
    if user_balance <= 0:
        await callback.answer("У вас нулевой баланс!", show_alert=True)
        return

    user_balances[user_id] = 0.0
    await callback.message.answer(f"✅ <b>Заявка на вывод всего баланса ({user_balance:.1f} USDT) принята!</b>", parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data == "withdraw_custom")
async def withdraw_custom_handler(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(UserState.withdraw_amount)
    await callback.message.answer("📝 <b>Введите сумму для вывода:</b>", parse_mode="HTML")
    await callback.answer()

@dp.message(UserState.withdraw_amount)
async def process_withdraw_amount(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    user_balance = user_balances.get(user_id, 0.0)

    try:
        amount = float(message.text.replace(",", "."))
        if amount <= 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ <b>Пожалуйста, введите корректное число.</b>", parse_mode="HTML")
        return

    if amount > user_balance:
        await message.answer(f"❌ <b>Запрошенная сумма превышает ваш баланс ({user_balance:.1f} USDT).</b>", parse_mode="HTML")
        return

    user_balances[user_id] = user_balance - amount
    await state.clear()
    await message.answer(f"✅ <b>Заявка на вывод суммы {amount:.1f} USDT принята!</b>", parse_mode="HTML")

# ===================== CREDIT (OPERATOR) =====================
@dp.callback_query(F.data.startswith("credit_"))
async def credit_start(callback: types.CallbackQuery, state: FSMContext):
    order_id = int(callback.data.split("_")[1])
    order = orders.get(order_id)
    if not order:
        await callback.answer("Заявка не найдена!", show_alert=True)
        return

    await state.update_data(order_id=order_id)
    await state.set_state(OperatorState.credit_amount)
    await callback.message.reply(
        f"💵 <b>Введите сумму зачёта для заявки #{order_id} (в USDT):</b>",
        parse_mode="HTML"
    )
    await callback.answer()

@dp.message(OperatorState.credit_amount)
async def credit_finish(message: types.Message, state: FSMContext):
    data = await state.get_data()
    order_id = data.get("order_id")
    order = orders.get(order_id)

    if not order:
        await message.answer("❌ <b>Заявка не найдена.</b>", parse_mode="HTML")
        await state.clear()
        return

    try:
        amount = float(message.text.replace(",", "."))
        if amount <= 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ <b>Введите корректное число.</b>", parse_mode="HTML")
        return

    user_id = order["user_id"]
    user_balances[user_id] = user_balances.get(user_id, 0.0) + amount
    order["status"] = "paid"

    # Уведомляем сдатчика
    await bot.send_message(
        user_id,
        f'🎉 <b>На ваш баланс зачтено {amount:.1f} USDT</b>',
        parse_mode="HTML"
    )

    await message.answer(
        f"✅ <b>Заявка #{order_id} зачтена на сумму {amount:.1f} USDT!</b>",
        parse_mode="HTML"
    )
    await state.clear()

# ===================== SUPPORT =====================
@dp.message(F.text == BTN_SUPPORT)
async def support(message: types.Message):
    await message.answer(
        "<b>Нажмите кнопку ниже:</b>",
        parse_mode="HTML",
        reply_markup=support_kb()
    )

# ===================== BILKA =====================
@dp.message(F.text == BTN_SUBMIT)
async def bilka(message: types.Message, state: FSMContext):
    await state.set_state(UserState.sale_type)
    await message.answer(
        '<tg-emoji emoji-id="5965361771987342650">🫵</tg-emoji> <b>Билайн — выберите тип:</b>',
        parse_mode="HTML",
        reply_markup=sale_type_kb()
    )

@dp.callback_query(F.data.in_({"type_moment", "type_hold"}))
async def choose_sale_type(callback: types.CallbackQuery, state: FSMContext):
    if callback.data == "type_moment":
        sale_type = "Момент"
        type_emoji = '<tg-emoji emoji-id="5431449001532594346">⚡️</tg-emoji>'
    else:
        sale_type = "Холд"
        type_emoji = '<tg-emoji emoji-id="5433737699410319194">🥶</tg-emoji>'

    await state.update_data(sale_type=sale_type)
    await state.set_state(UserState.phone)
    
    await callback.message.edit_text(
        f"{type_emoji} <b>Тип:</b> {sale_type}",
        parse_mode="HTML"
    )
    
    await callback.message.answer(
        '<tg-emoji emoji-id="5467539229468793355">📞</tg-emoji> <b>Введите номер телефона:</b>',
        parse_mode="HTML",
        reply_markup=cancel_kb
    )
    await callback.answer()

# ===================== PHONE / CODE =====================
@dp.message(UserState.phone)
async def save_phone(message: types.Message, state: FSMContext):
    if message.text == BTN_CANCEL or "Отменить" in message.text:
        await state.clear()
        await message.answer(
            '<tg-emoji emoji-id="5465665476971471368">❌</tg-emoji> <b>Заявка отменена. Для выхода в главное меню /start</b>',
            parse_mode="HTML",
            reply_markup=main_kb()
        )
        return

    if not is_beeline_number(message.text):
        await message.answer(
            '<tg-emoji emoji-id="5465665476971471368">❌</tg-emoji> <b>Некорректный номер телефона!</b>\n\n'
            "<blockquote>Пожалуйста, введите корректный номер оператора <b>Билайн</b> "
            "начинающийся с +7, 7 или 8 (например: <code>+79031234567</code>).</blockquote>",
            parse_mode="HTML"
        )
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
        f"<b>Новая заявка #{order_id}</b>\n"
        f"━━━━━━━━━━━━━━\n"
        f"👤 {username}\n"
        f"📱 {message.text}\n"
        f"🔖 {sale_type}",
        parse_mode="HTML",
        reply_markup=operator_kb(order_id)
    )

    await state.clear()
    await message.answer(
        '<tg-emoji emoji-id="5413482938585063042">👍</tg-emoji> <b>Номер принят.</b>\n\n'
        "<blockquote>Ожидайте запроса кода от оператора</blockquote>",
        parse_mode="HTML",
        reply_markup=main_kb()
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
        '<tg-emoji emoji-id="5242628160297641831">🔔</tg-emoji> <b>Оператор запрашивает код!</b>\n\n'
        '<blockquote>Нажмите кнопку ниже и введите полученный код.</blockquote>',
        parse_mode="HTML",
        reply_markup=user_kb(order_id)
    )
    await callback.answer("Отправлено")

@dp.callback_query(F.data.startswith("code_"))
async def enter_code(callback: types.CallbackQuery, state: FSMContext):
    order_id = int(callback.data.split("_")[1])
    await state.update_data(order_id=order_id)
    await state.set_state(UserState.code)
    await callback.message.answer(
        '<tg-emoji emoji-id="5334882760735598374">📝</tg-emoji> <b>Введите код:</b>',
        parse_mode="HTML"
    )
    await callback.answer()

@dp.message(UserState.code)
async def receive_code(message: types.Message, state: FSMContext):
    data = await state.get_data()
    order_id = data["order_id"]
    order = orders[order_id]

    await bot.send_message(
        OPERATORS_GROUP_ID,
        f"<b>Код по заявке #{order_id}</b>\n"
        f"━━━━━━━━━━━━━━\n"
        f"📝 {message.text}",
        parse_mode="HTML",
        reply_markup=operator_kb(order_id)
    )
    order["status"] = "waiting_operator"
    await message.answer(
        '<tg-emoji emoji-id="5427009714745517609">✅</tg-emoji> <b>Код отправлен!</b>\n\n'
        '<blockquote>Ожидайте запроса второго кода.</blockquote>',
        parse_mode="HTML"
    )
    await state.clear()

# ===================== CANCEL (OPERATOR) =====================
@dp.callback_query(F.data.startswith("cancel_"))
async def cancel_start(callback: types.CallbackQuery, state: FSMContext):
    order_id = int(callback.data.split("_")[1])
    await state.update_data(order_id=order_id)
    await state.set_state(OperatorState.cancel_reason)
    await callback.message.reply(
        "✏️ <b>Введите причину отмены</b> (ответом на это сообщение):",
        parse_mode="HTML"
    )
    await callback.answer()

@dp.message(OperatorState.cancel_reason)
async def cancel_finish(message: types.Message, state: FSMContext):
    data = await state.get_data()
    order_id = data.get("order_id")
    order = orders.get(order_id)
    if order:
        await bot.send_message(
            order["user_id"],
            f'<tg-emoji emoji-id="5465665476971471368">❌</tg-emoji> <b>Ваша заявка #{order_id} отменена</b>\n\n'
            f'<blockquote><tg-emoji emoji-id="5334882760735598374">📝</tg-emoji> <b>Причина:</b> {message.text}</blockquote>\n\n'
            f"Вы можете сдать номер заново.",
            parse_mode="HTML"
        )
        order["status"] = "cancelled"
    await message.answer(
        f"✅ <b>Заявка #{order_id} отменена.</b> Пользователь уведомлен.",
        parse_mode="HTML"
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
            f"⚠️ <b>Заявка #{order_id} отменена пользователем</b> {order['username']}",
            parse_mode="HTML"
        )
    await callback.message.edit_text(
        '<tg-emoji emoji-id="5465665476971471368">❌</tg-emoji> <b>Заявка отменена. Для выхода в главное меню /start</b>',
        parse_mode="HTML"
    )
    await callback.answer()
    await state.clear()

# ===================== ADMIN =====================
@dp.message(Command("admin"))
async def admin_panel(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("⛔ Нет доступа.", parse_mode="HTML")
        return
    await message.answer(
        f"🛠 <b>Админ-панель</b>\n\n"
        f"👥 Пользователей в базе: <b>{len(all_users)}</b>\n\n"
        f"<code>/broadcast</code> — рассылка всем пользователям",
        parse_mode="HTML"
    )

@dp.message(Command("broadcast"))
async def broadcast_start(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("⛔ Нет доступа.", parse_mode="HTML")
        return
    await state.set_state(AdminState.broadcast)
    await message.answer(
        "📢 <b>Введите сообщение для рассылки.</b>\n\n"
        "<blockquote>Поддерживаются текст, фото, видео.\nДля отмены — /cancel</blockquote>",
        parse_mode="HTML"
    )

@dp.message(Command("cancel"), AdminState.broadcast)
async def broadcast_cancel(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ <b>Рассылка отменена.</b>", parse_mode="HTML")

@dp.message(AdminState.broadcast)
async def broadcast_do(message: types.Message, state: FSMContext):
    await state.clear()
    sent = 0
    failed = 0
    await message.answer(f"⏳ <b>Начинаю рассылку</b> {len(all_users)} пользователям...", parse_mode="HTML")
    for user_id in list(all_users):
        try:
            await message.copy_to(user_id)
            sent += 1
            await asyncio.sleep(0.05)
        except Exception:
            failed += 1
    await message.answer(
        f"✅ <b>Рассылка завершена!</b>\n\n"
        f"📨 Отправлено: <b>{sent}</b>\n"
        f"❌ Ошибок: <b>{failed}</b>",
        parse_mode="HTML"
    )

# ===================== MAIN =====================
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
