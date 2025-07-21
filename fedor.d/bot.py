from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
import sqlite3
import requests
import logging
from datetime import datetime

# ===== КОНФИГУРАЦИЯ =====
TOKEN = "8001659110:AAE4JyLTuX5s6zyj5F_CQoW5e-J-FGhosg4"
CRYPTO_PAY_API = "https://pay.crypt.bot/api"
CRYPTO_PAY_TOKEN = "421215:AAjdPiEHPnyscrlkUMEICJzkonZIZJDkXo9"
STARS_RATE = 1.4  # 1 звезда = 1.4 рубля
MIN_PAYMENT = 10  # Минимальное кол-во звезд
WEBAPP_URL = "https://star-ruddy-three.vercel.app/"

# ===== ИНИЦИАЛИЗАЦИЯ =====
bot = Bot(token=TOKEN)
dp = Dispatcher(bot)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ===== БАЗА ДАННЫХ =====
def init_db():
    with sqlite3.connect('users.db') as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                stars INTEGER DEFAULT 0,
                last_active TIMESTAMP
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS payments (
                invoice_id TEXT PRIMARY KEY,
                user_id INTEGER,
                stars INTEGER,
                amount_rub REAL,
                status TEXT CHECK(status IN ('pending', 'paid', 'expired')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(user_id)
            )
        ''')
        conn.commit()

# ===== ОСНОВНЫЕ КОМАНДЫ =====
@dp.message_handler(commands=['start', 'menu'])
async def unified_start(message: types.Message):
    args = message.get_args()

    if args:
        if args.startswith('pay_'):
            try:
                _, user_id, stars = args.split('_')
                stars = int(stars)
                if stars < MIN_PAYMENT:
                    await message.answer(f"❌ Минимум {MIN_PAYMENT} звезд")
                    return
                await process_payment(message, user_id, stars)
            except Exception as e:
                logger.error(f"Payment error: {e}")
                await message.answer("❌ Ошибка обработки запроса")
        elif args.startswith('success_'):
            _, user_id, stars = args.split('_')
            await message.answer(
                f"✅ Баланс пополнен на {stars} ⭐\n"
                f"Вернитесь в мини-приложение и нажмите 'Обновить'"
            )
    else:
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        keyboard.add(types.KeyboardButton(
            "🎰 Открыть мини-приложение",
            web_app=types.WebAppInfo(url=WEBAPP_URL)
        ))

        await message.answer(
            "🌟 Добро пожаловать в Star Azart! 🌟\n\n"
            "Испытайте удачу в наших эксклюзивных кейсах!",
            reply_markup=keyboard
        )

# ===== ОПЛАТА =====
async def process_payment(message: types.Message, user_id: str, stars: int):
    amount_rub = round(stars * STARS_RATE, 2)

    try:
        # 1. Регистрация пользователя
        with sqlite3.connect('users.db') as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR IGNORE INTO users (user_id, username, first_name)
                VALUES (?, ?, ?)
            ''', (user_id, message.from_user.username, message.from_user.first_name))
            conn.commit()

        # 2. Создание инвойса
        headers = {"Crypto-Pay-API-Token": CRYPTO_PAY_TOKEN}
        payload = {
            "asset": "USDT",
            "amount": str(amount_rub),
            "description": f"Пополнение {stars} звезд (ID: {user_id})",
            "paid_btn_url": f"https://t.me/StarAzart_bot?start=success_{user_id}_{stars}",
            "allow_anonymous": False
        }

        response = requests.post(
            f"{CRYPTO_PAY_API}/createInvoice",
            headers=headers,
            json=payload,
            timeout=10
        )
        response.raise_for_status()
        invoice = response.json()['result']

        # 3. Сохранение платежа
        with sqlite3.connect('users.db') as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO payments (invoice_id, user_id, stars, amount_rub, status)
                VALUES (?, ?, ?, ?, ?)
            ''', (invoice['invoice_id'], user_id, stars, amount_rub, 'pending'))
            conn.commit()

        # 4. Отправка кнопок оплаты
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton(
            text="💳 Оплатить сейчас",
            url=invoice['pay_url']
        ))
        kb.add(types.InlineKeyboardButton(
            text="🔄 Проверить оплату",
            callback_data=f"check_{invoice['invoice_id']}"
        ))

        await message.answer(
            f"💎 *Счет на оплату* 💎\n\n"
            f"• Звезды: *{stars} ⭐*\n"
            f"• Сумма: *{amount_rub} ₽*\n"
            f"• Статус: ожидает оплаты\n\n"
            f"Оплатите в течение 15 минут",
            parse_mode="Markdown",
            reply_markup=kb
        )

    except requests.exceptions.RequestException as e:
        logger.error(f"CryptoPay API error: {e}")
        await message.answer("⚠️ Ошибка соединения с платежной системой")
    except Exception as e:
        logger.error(f"Payment processing error: {e}")
        await message.answer("❌ Не удалось создать платеж")

# ===== ПРОВЕРКА ОПЛАТЫ =====
@dp.callback_query_handler(lambda c: c.data.startswith('check_'))
async def check_payment(callback: types.CallbackQuery):
    invoice_id = callback.data.split('_')[1]

    try:
        # 1. Проверка статуса
        headers = {"Crypto-Pay-API-Token": CRYPTO_PAY_TOKEN}
        response = requests.get(
            f"{CRYPTO_PAY_API}/getInvoices?invoice_ids={invoice_id}",
            headers=headers,
            timeout=10
        )
        response.raise_for_status()
        invoice = response.json()['result']['items'][0]

        # 2. Если оплачено
        if invoice['status'] == 'paid':
            with sqlite3.connect('users.db') as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT user_id, stars FROM payments
                    WHERE invoice_id = ? AND status = 'pending'
                ''', (invoice_id,))
                payment = cursor.fetchone()

                if payment:
                    user_id, stars = payment
                    # Обновление баланса
                    cursor.execute('''
                        UPDATE users SET stars = stars + ?
                        WHERE user_id = ?
                    ''', (stars, user_id))
                    # Обновление статуса
                    cursor.execute('''
                        UPDATE payments SET status = 'paid'
                        WHERE invoice_id = ?
                    ''', (invoice_id,))
                    conn.commit()

                    await callback.message.edit_text(
                        f"🎉 *Оплата подтверждена!*\n\n"
                        f"На ваш счет зачислено: *{stars} ⭐*\n\n"
                        f"Обновите мини-приложение для отображения баланса",
                        parse_mode="Markdown"
                    )
                else:
                    await callback.answer("Платеж уже обработан", show_alert=True)
        else:
            await callback.answer("Платеж не найден или еще не обработан", show_alert=True)

    except Exception as e:
        logger.error(f"Payment check error: {e}")
        await callback.answer("⚠️ Ошибка проверки платежа", show_alert=True)

# ===== ЗАПУСК =====
if __name__ == '__main__':
    init_db()
    logger.info("Бот Star Azart запущен и готов к работе!")
    executor.start_polling(dp, skip_updates=True)