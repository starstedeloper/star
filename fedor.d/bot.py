from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
import sqlite3
import requests
import logging
from datetime import datetime

# Конфигурация
TOKEN = "8001659110:AAE4JyLTuX5s6zyj5F_CQoW5e-J-FGhosg4"
CRYPTO_PAY_API = "https://pay.crypt.bot/api"
CRYPTO_PAY_TOKEN = "421215:AAjdPiEHPnyscrlkUMEICJzkonZIZJDkXo9"
STARS_RATE = 1.4  # 1 звезда = 1.4 рубля
MIN_PAYMENT = 10  # Минимальное кол-во звезд
WEBAPP_URL = "https://your-domain.com/index.html"  # url web_app
# Инициализация
bot = Bot(token=TOKEN)
dp = Dispatcher(bot)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    args = message.get_args()

    if args and args.startswith('pay_'):
        try:
            _, user_id, stars = args.split('_')
            stars = int(stars)

            if stars < MIN_PAYMENT:
                await message.answer(f"❌ Минимум {MIN_PAYMENT} звезд")
                return

            await process_payment(message, user_id, stars)

        except ValueError:
            await message.answer("⚠️ Неверный формат команды")
        except Exception as e:
            logger.error(f"Ошибка в /start: {e}")
            await message.answer("❌ Ошибка сервера")

    elif args and args.startswith('success_'):
        _, user_id, stars = args.split('_')
        await message.answer(
            f"✅ Баланс пополнен на {stars} ⭐\n"
            f"Вернитесь в мини-апп и нажмите 'Обновить'"
        )

@dp.message_handler(commands=['start', 'menu'])
async def send_welcome(message: types.Message):
    # Создаем кнопку для открытия мини-приложения
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    button = types.KeyboardButton("Открыть мини-приложение", web_app=types.WebAppInfo(url=WEBAPP_URL))
    keyboard.add(button)

    await message.answer(
        "Добро пожаловать в Star Azart! 🎰\n\n"
        "Нажмите кнопку ниже, чтобы открыть мини-приложение:",
        reply_markup=keyboard
    )

async def process_payment(message: types.Message, user_id: str, stars: int):
    """Создание инвойса и обработка платежа"""
    amount_rub = round(stars * STARS_RATE, 2)

    try:
        # 1. Регистрируем пользователя
        with sqlite3.connect('users.db') as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR IGNORE INTO users (user_id, username, first_name)
                VALUES (?, ?, ?)
            ''', (user_id, message.from_user.username, message.from_user.first_name))
            conn.commit()

        # 2. Создаем инвойс в CryptoPay
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

        # 3. Сохраняем платеж
        with sqlite3.connect('users.db') as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO payments (invoice_id, user_id, stars, amount_rub, status)
                VALUES (?, ?, ?, ?, ?)
            ''', (invoice['invoice_id'], user_id, stars, amount_rub, 'pending'))
            conn.commit()

        # 4. Отправляем кнопку оплаты
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton(
            text="💳 Оплатить",
            url=invoice['pay_url']
        ))
        kb.add(types.InlineKeyboardButton(
            text="🔄 Проверить оплату",
            callback_data=f"check_{invoice['invoice_id']}"
        ))

        await message.answer(
            f"*Счет на оплату*\n\n"
            f"• Количество звезд: *{stars} ⭐*\n"
            f"• Сумма: *{amount_rub} RUB*\n"
            f"• Статус: ожидает оплаты",
            parse_mode="Markdown",
            reply_markup=kb
        )

    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка API CryptoPay: {e}")
        await message.answer("⚠️ Ошибка платежной системы")
    except Exception as e:
        logger.error(f"Ошибка process_payment: {e}")
        await message.answer("❌ Ошибка создания платежа")

@dp.callback_query_handler(lambda c: c.data.startswith('check_'))
async def check_payment(callback: types.CallbackQuery):
    invoice_id = callback.data.split('_')[1]

    try:
        # 1. Проверяем статус в CryptoPay
        headers = {"Crypto-Pay-API-Token": CRYPTO_PAY_TOKEN}
        response = requests.get(
            f"{CRYPTO_PAY_API}/getInvoices?invoice_ids={invoice_id}",
            headers=headers,
            timeout=10
        )
        response.raise_for_status()
        invoice = response.json()['result']['items'][0]

        # 2. Если оплачено - начисляем звезды
        if invoice['status'] == 'paid':
            with sqlite3.connect('users.db') as conn:
                cursor = conn.cursor()

                # Получаем данные платежа
                cursor.execute('''
                    SELECT user_id, stars FROM payments
                    WHERE invoice_id = ? AND status = 'pending'
                ''', (invoice_id,))
                payment = cursor.fetchone()

                if payment:
                    user_id, stars = payment

                    # Обновляем баланс
                    cursor.execute('''
                        UPDATE users SET stars = stars + ?
                        WHERE user_id = ?
                    ''', (stars, user_id))

                    # Меняем статус платежа
                    cursor.execute('''
                        UPDATE payments SET status = 'paid'
                        WHERE invoice_id = ?
                    ''', (invoice_id,))
                    conn.commit()

                    await callback.message.edit_text(
                        f"✅ Оплата подтверждена!\n"
                        f"Начислено: *{stars} ⭐*\n\n"
                        f"Обновите мини-приложение",
                        parse_mode="Markdown"
                    )
                else:
                    await callback.answer("Платеж уже обработан", show_alert=True)
        else:
            await callback.answer("Платеж не найден", show_alert=True)

    except Exception as e:
        logger.error(f"Ошибка check_payment: {e}")
        await callback.answer("⚠️ Ошибка проверки", show_alert=True)

if __name__ == '__main__':
    init_db()
    executor.start_polling(dp, skip_updates=True)