# ==============================================================================
# ПОЛНЫЙ И ИСПРАВЛЕННЫЙ ФАЙЛ BOT.PY (СОХРАНЕНА ОРИГИНАЛЬНАЯ СТРУКТУРА)
# ==============================================================================

from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
import sqlite3
import json
import logging
import requests
import asyncio
from datetime import datetime, timedelta
import random
import urllib.parse

# Конфигурация
TOKEN = "8001659110:AAE4JyLTuX5s6zyj5F_CQoW5e-J-FGhosg4"
WEBAPP_URL = "https://star-ruddy-three.vercel.app/"
ADMIN_IDS = [8132062572]  # ID администратора
CRYPTO_PAY_TOKEN = "421215:AAjdPiEHPnyscrlkUMEICJzkonZIZJDkXo9"
CRYPTO_PAY_API = "https://pay.crypt.bot/api"
STARS_RATE = 1.4  # 1 звезда = 1.4 рубля
MIN_PAYMENT = 10  # Минимальное количество звезд для пополнения

# Инициализация
bot = Bot(token=TOKEN)
dp = Dispatcher(bot)
logging.basicConfig(level=logging.INFO)

# Инициализация базы данных
def init_db():
    with sqlite3.connect('users.db') as conn:
        cursor = conn.cursor()

        # Таблица пользователей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                stars INTEGER DEFAULT 0,
                last_active TIMESTAMP,
                registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_admin BOOLEAN DEFAULT FALSE
            )
        ''')

        # Таблица инвентаря
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                item_id INTEGER NOT NULL,
                item_name TEXT NOT NULL,
                item_image TEXT,
                emoji TEXT,
                sell_price INTEGER,
                withdraw_price INTEGER,
                obtained_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_withdrawn BOOLEAN DEFAULT FALSE,
                FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
            )
        ''')

        # Таблица платежей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS payments (
                invoice_id TEXT PRIMARY KEY,
                user_id INTEGER,
                stars INTEGER,
                amount_usd REAL,
                status TEXT CHECK(status IN ('pending', 'paid', 'expired')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                paid_at TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(user_id)
            )
        ''')

        # Таблица кейсов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                price INTEGER NOT NULL,
                image TEXT,
                emoji TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Таблица предметов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                image TEXT,
                emoji TEXT,
                sell_price INTEGER NOT NULL,
                withdraw_price INTEGER NOT NULL,
                rarity TEXT CHECK(rarity IN ('common', 'rare', 'epic', 'legendary')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Таблица предметов в кейсах
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS case_items (
                case_id INTEGER NOT NULL,
                item_id INTEGER NOT NULL,
                chance REAL NOT NULL,
                PRIMARY KEY (case_id, item_id),
                FOREIGN KEY(case_id) REFERENCES cases(id) ON DELETE CASCADE,
                FOREIGN KEY(item_id) REFERENCES items(id) ON DELETE CASCADE
            )
        ''')

        # Таблица выводов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS withdrawals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                item_id INTEGER NOT NULL,
                status TEXT CHECK(status IN ('pending', 'completed', 'rejected')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                admin_id INTEGER,
                FOREIGN KEY(user_id) REFERENCES users(user_id),
                FOREIGN KEY(item_id) REFERENCES inventory(id)
            )
        ''')

        # Создаем администратора если его нет
        for admin_id in ADMIN_IDS:
            cursor.execute('''
                INSERT OR IGNORE INTO users (user_id, is_admin)
                VALUES (?, TRUE)
            ''', (admin_id,))

        conn.commit()

# Загрузка начальных данных (кейсы и предметы)
async def load_initial_data():
    with sqlite3.connect('users.db') as conn:
        cursor = conn.cursor()
        
        # Проверяем, есть ли уже кейсы
        cursor.execute('SELECT 1 FROM cases LIMIT 1')
        if not cursor.fetchone():
            # Добавляем стандартные кейсы
            cases = [
                ('Обычный кейс', 10, 'common_case.png', '📦'),
                ('Редкий кейс', 25, 'rare_case.png', '🎁'),
                ('Эпический кейс', 50, 'epic_case.png', '💎'),
                ('Легендарный кейс', 100, 'legendary_case.png', '🏆')
            ]
            
            for case in cases:
                cursor.execute('''
                    INSERT INTO cases (name, price, image, emoji)
                    VALUES (?, ?, ?, ?)
                ''', case)
            
            # Добавляем стандартные предметы
            items = [
                ('Сердце', 'heart.png', '❤️', 15, 15, 'common'),
                ('Плюшевый мишка', 'teddy_bear.png', '🧸', 15, 15, 'common'),
                ('Подарок', 'gift.png', '🎁', 25, 25, 'rare'),
                ('Роза', 'rose.png', '🌹', 25, 25, 'rare'),
                ('Торт', 'cake.png', '🎂', 50, 50, 'epic'),
                ('Букет', 'bouquet.png', '💐', 50, 50, 'epic'),
                ('Ракета', 'rocket.png', '🚀', 50, 50, 'epic'),
                ('Кубок', 'trophy.png', '🏆', 100, 100, 'legendary'),
                ('Кольцо', 'ring.png', '💍', 100, 100, 'legendary'),
                ('Алмаз', 'diamond.png', '💎', 100, 100, 'legendary')
            ]
            
            for item in items:
                cursor.execute('''
                    INSERT INTO items (name, image, emoji, sell_price, withdraw_price, rarity)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', item)
            
            # Связываем предметы с кейсами
            case_items = [
                (1, 1, 0.18), (1, 2, 0.18), (1, 3, 0.15), (1, 4, 0.15),
                (1, 5, 0.10), (1, 6, 0.08), (1, 7, 0.07), (1, 8, 0.04),
                (1, 9, 0.03), (1, 10, 0.02),
                
                (2, 3, 0.25), (2, 4, 0.25), (2, 5, 0.20), (2, 6, 0.15),
                (2, 7, 0.10), (2, 8, 0.03), (2, 9, 0.02),
                
                (3, 5, 0.30), (3, 6, 0.25), (3, 7, 0.20), (3, 8, 0.15),
                (3, 9, 0.07), (3, 10, 0.03),
                
                (4, 8, 0.40), (4, 9, 0.35), (4, 10, 0.25)
            ]
            
            for case_item in case_items:
                cursor.execute('''
                    INSERT INTO case_items (case_id, item_id, chance)
                    VALUES (?, ?, ?)
                ''', case_item)
            
            conn.commit()

# Получение данных пользователя
async def get_user_data(user_id):
    with sqlite3.connect('users.db') as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Получаем баланс
        cursor.execute('SELECT stars FROM users WHERE user_id = ?', (user_id,))
        user = cursor.fetchone()

        # Получаем инвентарь
        cursor.execute('''
            SELECT 
                i.id, i.item_name as name, i.item_image as image, i.emoji, 
                i.sell_price, i.withdraw_price
            FROM inventory i
            WHERE i.user_id = ? AND i.is_withdrawn = FALSE
        ''', (user_id,))
        inventory = cursor.fetchall()

        return {
            'balance': user['stars'] if user else 0,
            'inventory': [dict(item) for item in inventory]
        }

# Создание крипто-инвойса
async def create_crypto_invoice(user_id, stars, amount_usd):
    try:
        headers = {"Crypto-Pay-API-Token": CRYPTO_PAY_TOKEN}
        payload = {
            "asset": "USDT",
            "amount": str(amount_usd),
            "description": f"Пополнение {stars} звезд",
            "paid_btn_url": f"{WEBAPP_URL}?payment_success={user_id}_{stars}",
            "payload": json.dumps({"user_id": user_id, "stars": stars})
        }

        response = requests.post(
            f"{CRYPTO_PAY_API}/createInvoice",
            headers=headers,
            json=payload
        )

        if response.status_code == 201 or response.status_code == 200:
            result = response.json().get('result')

            with sqlite3.connect('users.db') as conn:
                conn.execute('''
                    INSERT INTO payments (invoice_id, user_id, stars, amount_usd, status)
                    VALUES (?, ?, ?, ?, 'pending')
                ''', (result['invoice_id'], user_id, stars, amount_usd))
                conn.commit()

            return result
        else:
            logging.error(f"Crypto Pay error: {response.text}")
            return None

    except Exception as e:
        logging.error(f"Payment error: {e}")
        return None

# Открытие кейса
async def open_case(user_id, case_id):
    with sqlite3.connect('users.db') as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            # Проверяем, есть ли у пользователя достаточно звезд
            cursor.execute('SELECT stars FROM users WHERE user_id = ?', (user_id,))
            user = cursor.fetchone()
            if not user:
                return None, "Пользователь не найден"

            cursor.execute('SELECT price FROM cases WHERE id = ?', (case_id,))
            case = cursor.fetchone()
            if not case:
                return None, "Кейс не найден"

            if user['stars'] < case['price']:
                return None, "Недостаточно звезд"

            # Выбираем случайный предмет из кейса
            cursor.execute('''
                SELECT i.id, i.name, i.image, i.emoji, i.sell_price, i.withdraw_price
                FROM case_items ci
                JOIN items i ON ci.item_id = i.id
                WHERE ci.case_id = ?
                ORDER BY RANDOM() LIMIT 1
            ''', (case_id,))
            won_item = cursor.fetchone()

            if not won_item:
                return None, "В кейсе нет предметов"

            # Добавляем предмет в инвентарь
            cursor.execute('''
                INSERT INTO inventory 
                (user_id, item_id, item_name, item_image, emoji, sell_price, withdraw_price)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, won_item['id'], won_item['name'], won_item['image'], 
                 won_item['emoji'], won_item['sell_price'], won_item['withdraw_price']))

            # Снимаем звезды
            cursor.execute('''
                UPDATE users SET stars = stars - ? WHERE user_id = ?
            ''', (case['price'], user_id))

            conn.commit()

            return dict(won_item), None

        except Exception as e:
            conn.rollback()
            logging.error(f"Error opening case: {e}")
            return None, "Ошибка при открытии кейса"

# Продажа предмета
async def sell_item(user_id, item_id):
    with sqlite3.connect('users.db') as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            # Проверяем, есть ли предмет у пользователя
            cursor.execute('''
                SELECT id, sell_price FROM inventory 
                WHERE id = ? AND user_id = ? AND is_withdrawn = FALSE
            ''', (item_id, user_id))
            item = cursor.fetchone()

            if not item:
                return False, "Предмет не найден"

            # Добавляем звезды
            cursor.execute('''
                UPDATE users SET stars = stars + ? WHERE user_id = ?
            ''', (item['sell_price'], user_id))

            # Удаляем предмет из инвентаря
            cursor.execute('''
                DELETE FROM inventory WHERE id = ?
            ''', (item_id,))

            conn.commit()

            return True, None

        except Exception as e:
            conn.rollback()
            logging.error(f"Error selling item: {e}")
            return False, "Ошибка при продаже предмета"

# Запрос на вывод предмета
async def request_withdrawal(user_id, item_id):
    with sqlite3.connect('users.db') as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            # Проверяем, есть ли предмет у пользователя
            cursor.execute('''
                SELECT id FROM inventory 
                WHERE id = ? AND user_id = ? AND is_withdrawn = FALSE
            ''', (item_id, user_id))
            item = cursor.fetchone()

            if not item:
                return False, "Предмет не найден"

            # Создаем запрос на вывод
            cursor.execute('''
                INSERT INTO withdrawals (user_id, item_id, status)
                VALUES (?, ?, 'pending')
            ''', (user_id, item_id))

            # Помечаем предмет как выводимый
            cursor.execute('''
                UPDATE inventory SET is_withdrawn = TRUE WHERE id = ?
            ''', (item_id,))

            conn.commit()

            return True, None

        except Exception as e:
            conn.rollback()
            logging.error(f"Error requesting withdrawal: {e}")
            return False, "Ошибка при запросе вывода"

# Проверка платежей
async def check_payments():
    while True:
        try:
            with sqlite3.connect('users.db') as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # Получаем все pending платежи
                cursor.execute('''
                    SELECT * FROM payments 
                    WHERE status = 'pending' 
                    AND created_at > datetime('now', '-1 hour')
                ''')
                pending_payments = cursor.fetchall()

                headers = {"Crypto-Pay-API-Token": CRYPTO_PAY_TOKEN}

                for payment in pending_payments:
                    # Проверяем статус платежа в Crypto Pay
                    response = requests.get(
                        f"{CRYPTO_PAY_API}/getInvoices?invoice_ids={payment['invoice_id']}",
                        headers=headers
                    )

                    if response.status_code == 200:
                        invoice = response.json().get('result', {}).get('items', [{}])[0]

                        if invoice.get('status') == 'paid':
                            # Обновляем баланс пользователя
                            cursor.execute('''
                                UPDATE users 
                                SET stars = stars + ? 
                                WHERE user_id = ?
                            ''', (payment['stars'], payment['user_id']))

                            # Обновляем статус платежа
                            cursor.execute('''
                                UPDATE payments 
                                SET status = 'paid', paid_at = CURRENT_TIMESTAMP
                                WHERE invoice_id = ?
                            ''', (payment['invoice_id'],))

                            conn.commit()

                            # Уведомляем пользователя
                            await bot.send_message(
                                payment['user_id'],
                                f"✅ Ваш баланс пополнен на {payment['stars']} ⭐"
                            )

                        elif invoice.get('status') == 'expired':
                            # Помечаем платеж как просроченный
                            cursor.execute('''
                                UPDATE payments 
                                SET status = 'expired'
                                WHERE invoice_id = ?
                            ''', (payment['invoice_id'],))
                            conn.commit()

        except Exception as e:
            logging.error(f"Payment check error: {e}")

        await asyncio.sleep(60)  # Проверяем каждую минуту

# ==============================================================================
# НАЧАЛО ИСПРАВЛЕНИЙ
# ==============================================================================

# Общая функция для вызова при запросе оплаты
async def process_payment_request(user_id, stars_to_pay):
    if stars_to_pay < MIN_PAYMENT:
        await bot.send_message(user_id, f"Минимальная сумма пополнения: {MIN_PAYMENT} ⭐")
        return

    amount_usd = round(stars_to_pay * STARS_RATE, 2)
    invoice = await create_crypto_invoice(user_id, stars_to_pay, amount_usd)

    if invoice:
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton(
            text="💳 Оплатить сейчас",
            url=invoice['pay_url']
        ))
        await bot.send_message(
            user_id,
            f"💎 Счет на {stars_to_pay} ⭐ ({amount_usd:.2f} USDT)\n\n"
            f"Ссылка для оплаты действительна 1 час.",
            reply_markup=kb
        )
    else:
        await bot.send_message(user_id, "❌ Не удалось создать счет, попробуйте позже")

@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name

    with sqlite3.connect('users.db') as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO users (user_id, username, first_name, last_name, last_active)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id) DO UPDATE SET
            username = excluded.username,
            first_name = excluded.first_name,
            last_name = excluded.last_name,
            last_active = CURRENT_TIMESTAMP
        ''', (user_id, username, message.from_user.first_name, message.from_user.last_name))

        if cursor.rowcount > 0:
            conn.execute('UPDATE users SET stars = stars + 10 WHERE user_id = ?', (user_id,))
            conn.execute('''
                INSERT INTO inventory (user_id, item_id, item_name, item_image, emoji, sell_price, withdraw_price)
                SELECT ?, id, name, image, emoji, sell_price, withdraw_price
                FROM items WHERE rarity = 'common' ORDER BY RANDOM() LIMIT 1
            ''', (user_id,))
            await message.answer("🎉 Вы получили стартовый бонус: 10 ⭐ и случайный предмет!")
        conn.commit()

    # ИЗМЕНЕНИЕ №1: Проверяем аргументы (deep link) для оплаты
    args = message.get_args()
    if args and args.startswith('pay_'):
        try:
            parts = args.split('_')
            if len(parts) == 3:
                await process_payment_request(user_id, int(parts[2]))
            else:
                await message.answer("Ошибка в ссылке для оплаты.")
        except (ValueError, IndexError):
            await message.answer("Некорректная ссылка для оплаты.")
        return # Важно: завершаем, чтобы не отправлять WebApp

    # ИЗМЕНЕНИЕ №2: Если это обычный /start, передаем ВСЕ данные в URL
    user_data = await get_user_data(user_id)
    inventory_json_str = json.dumps(user_data['inventory'])
    inventory_encoded = urllib.parse.quote(inventory_json_str)
    
    webapp_url = (
        f"{WEBAPP_URL}?"
        f"user_id={user_id}&"
        f"stars={user_data['balance']}&"
        f"inventory={inventory_encoded}"
    )

    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(types.KeyboardButton(
        "🎰 Открыть мини-приложение",
        web_app=types.WebAppInfo(url=webapp_url)
    ))

    await message.answer(
        f"🌟 Добро пожаловать в Star Azart, {message.from_user.first_name}!\n\n"
        "Нажмите кнопку ниже, чтобы открыть игровое приложение:",
        reply_markup=keyboard
    )

# Обработка данных из веб-приложения
@dp.message_handler(content_types=['web_app_data'])
async def handle_web_app_data(message: types.Message):
    try:
        data = json.loads(message.web_app_data.data)
        user_id = message.from_user.id
        action = data.get('action')

        if action == 'open_case':
            case_id = data.get('case_id')
            if not case_id:
                # В реальном приложении можно не отвечать, чтобы не спамить
                return
            
            won_item, error = await open_case(user_id, case_id)
            if error:
                # Можно отправить сообщение об ошибке, но лучше не спамить
                logging.warning(f"Case opening error for user {user_id}: {error}")
                return
            # Можно отправить сообщение о выигрыше, но фронтенд уже показал его
            # await message.answer(f"🎉 Вы открыли кейс и получили: {won_item['name']}!")

        elif action == 'sell_item':
            # ИЗМЕНЕНИЕ №3: Используем item_id вместо itemName
            item_id = data.get('item_id')
            if not item_id:
                return

            success, error = await sell_item(user_id, item_id)
            if not success:
                logging.warning(f"Failed to sell item {item_id} for user {user_id}: {error}")

        elif action == 'withdraw_item':
            # ИЗМЕНЕНИЕ №4: Используем item_id
            item_id = data.get('item_id')
            if not item_id:
                return

            success, error = await request_withdrawal(user_id, item_id)
            if not success:
                logging.warning(f"Failed to withdraw item {item_id} for user {user_id}: {error}")
            else:
                # Уведомляем администраторов
                for admin_id in ADMIN_IDS:
                    try:
                        await bot.send_message(
                            admin_id,
                            f"🆕 Новый запрос на вывод предмета от пользователя @{message.from_user.username or message.from_user.id}\n"
                            f"ID предмета: {item_id}"
                        )
                    except Exception as e:
                        logging.error(f"Error notifying admin: {e}")

    except json.JSONDecodeError:
        logging.error("JSONDecodeError in web_app_data")
    except Exception as e:
        logging.error(f"WebApp error: {e}")

# Команды администратора (без изменений)
@dp.message_handler(commands=['admin'])
async def admin_panel(message: types.Message):
    user_id = message.from_user.id
    if user_id not in ADMIN_IDS:
        await message.answer("❌ У вас нет прав администратора")
        return

    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(
        "📊 Статистика",
        callback_data="admin_stats"
    ))
    keyboard.add(types.InlineKeyboardButton(
        "📝 Запросы на вывод",
        callback_data="admin_withdrawals"
    ))

    await message.answer(
        "👑 Панель администратора",
        reply_markup=keyboard
    )

# Обработка callback-запросов (без изменений)
@dp.callback_query_handler(lambda c: c.data.startswith('admin_'))
async def process_admin_callback(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    if user_id not in ADMIN_IDS:
        await bot.answer_callback_query(callback_query.id, "У вас нет прав администратора")
        return

    action = callback_query.data

    if action == 'admin_stats':
        with sqlite3.connect('users.db') as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) as users FROM users')
            total_users = cursor.fetchone()['users']
            cursor.execute('SELECT SUM(stars) as stars FROM users')
            total_stars = cursor.fetchone()['stars'] or 0
            cursor.execute("SELECT COUNT(*) as payments, SUM(amount_usd) as amount FROM payments WHERE status = 'paid'")
            payments = cursor.fetchone()
            total_payments = payments['payments'] or 0
            total_amount = payments['amount'] or 0
            cursor.execute('SELECT COUNT(*) as cases_opened FROM inventory')
            cases_opened = cursor.fetchone()['cases_opened']
            await bot.send_message(user_id, f"📊 Статистика:\n\n👥 Пользователей: {total_users}\n💫 Всего звезд: {total_stars}\n"
                                          f"💰 Платежей: {total_payments} на сумму {total_amount:.2f} USDT\n🎁 Открыто кейсов: {cases_opened}")
        await bot.answer_callback_query(callback_query.id)

    elif action == 'admin_withdrawals':
        with sqlite3.connect('users.db') as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT w.id, u.username, u.first_name, i.item_name, i.emoji, w.created_at
                FROM withdrawals w
                JOIN users u ON w.user_id = u.user_id
                JOIN inventory i ON w.item_id = i.id
                WHERE w.status = 'pending' ORDER BY w.created_at
            ''')
            withdrawals = cursor.fetchall()
            if not withdrawals:
                await bot.send_message(user_id, "Нет активных запросов на вывод")
                return
            for withdrawal in withdrawals:
                keyboard = types.InlineKeyboardMarkup()
                keyboard.add(
                    types.InlineKeyboardButton("✅ Подтвердить", callback_data=f"approve_{withdrawal['id']}"),
                    types.InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_{withdrawal['id']}")
                )
                await bot.send_message(user_id, f"🔄 Запрос на вывод #{withdrawal['id']}\n\n"
                                                 f"👤 Пользователь: {withdrawal['first_name']} (@{withdrawal['username']})\n"
                                                 f"🎁 Предмет: {withdrawal['emoji']} {withdrawal['item_name']}\n"
                                                 f"🕒 Дата: {withdrawal['created_at']}", reply_markup=keyboard)
        await bot.answer_callback_query(callback_query.id)

@dp.callback_query_handler(lambda c: c.data.startswith('approve_') or c.data.startswith('reject_'))
async def process_withdrawal_action(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    if user_id not in ADMIN_IDS:
        return await bot.answer_callback_query(callback_query.id, "У вас нет прав")
        
    action, withdrawal_id_str = callback_query.data.split('_')
    withdrawal_id = int(withdrawal_id_str)

    with sqlite3.connect('users.db') as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('''
            SELECT w.id, w.user_id, i.id as item_inventory_id, i.item_name, i.emoji
            FROM withdrawals w JOIN inventory i ON w.item_id = i.id
            WHERE w.id = ? AND w.status = 'pending'
        ''', (withdrawal_id,))
        info = cursor.fetchone()
        if not info:
            return await bot.answer_callback_query(callback_query.id, "Запрос уже обработан или не найден")

        if action == 'approve':
            cursor.execute("UPDATE withdrawals SET status = 'completed', completed_at = CURRENT_TIMESTAMP, admin_id = ? WHERE id = ?", (user_id, withdrawal_id))
            conn.commit()
            await bot.send_message(info['user_id'], f"✅ Ваш запрос на вывод предмета {info['emoji']} {info['item_name']} одобрен!")
            await callback_query.message.edit_text(f"{callback_query.message.text}\n\n✅ ОДОБРЕНО админом @{callback_query.from_user.username}")
        elif action == 'reject':
            cursor.execute("UPDATE withdrawals SET status = 'rejected', completed_at = CURRENT_TIMESTAMP, admin_id = ? WHERE id = ?", (user_id, withdrawal_id))
            cursor.execute("UPDATE inventory SET is_withdrawn = FALSE WHERE id = ?", (info['item_inventory_id'],))
            conn.commit()
            await bot.send_message(info['user_id'], f"❌ Ваш запрос на вывод предмета {info['emoji']} {info['item_name']} отклонен.")
            await callback_query.message.edit_text(f"{callback_query.message.text}\n\n❌ ОТКЛОНЕНО админом @{callback_query.from_user.username}")
    
    await bot.answer_callback_query(callback_query.id, "Действие выполнено")

# Запуск бота
if __name__ == '__main__':
    init_db()
    loop = asyncio.get_event_loop()
    loop.create_task(load_initial_data())
    loop.create_task(check_payments())
    executor.start_polling(dp, skip_updates=True)