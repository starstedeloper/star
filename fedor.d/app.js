document.addEventListener('DOMContentLoaded', () => {
    const tg = window.Telegram?.WebApp;
    if (tg) {
        tg.expand();
        tg.enableClosingConfirmation();
    }

    // 1. Получаем данные из URL параметров
    const params = new URLSearchParams(window.location.search);
    const userId = params.get('user_id') || (tg?.initDataUnsafe?.user?.id || '0');
    const username = tg?.initDataUnsafe?.user?.first_name || 'Гость';
    const stars = params.get('stars') || '0';
    let inventory = [];

    try {
        inventory = JSON.parse(params.get('inventory') || [];
    } catch (e) {
        console.error('Ошибка парсинга инвентаря:', e);
        inventory = [];
    }

    // 2. Устанавливаем данные в интерфейс
    document.getElementById('user-name').textContent = username;
    document.getElementById('stars').textContent = stars;

    // 3. Рендерим инвентарь
    const renderInventory = () => {
        const container = document.getElementById('inventory-items');
        if (inventory.length > 0) {
            container.innerHTML = inventory.map(item => `
                <div class="item-card">
                    <div class="item-emoji">${item.emoji || '🎁'}</div>
                    <div class="item-name">${item.name}</div>
                    <div class="item-price">${item.sell_price} ⭐</div>
                    <div class="item-buttons">
                        <button class="sell-btn">💰</button>
                        <button class="withdraw-btn">📤</button>
                    </div>
                </div>
            `).join('');
        } else {
            container.innerHTML = '<div class="empty-message">Инвентарь пуст</div>';
        }
    };

    // 4. Функция открытия кейса
    const openCase = (caseType) => {
        if (tg) {
            tg.sendData(JSON.stringify({
                action: 'open_case',
                case_type: caseType,
                user_id: userId
            }));
        } else {
            alert('Функция доступна только в Telegram');
        }
    };

    // 5. Обработчики событий
    document.getElementById('add-stars').addEventListener('click', () => {
        if (tg) {
            tg.openTelegramLink(`https://t.me/StarAzart_bot?start=pay_${userId}_100`);
        } else {
            window.location.href = `payment.html?user_id=${userId}`;
        }
    });

    document.querySelectorAll('.case-card').forEach(card => {
        card.addEventListener('click', () => {
            const caseType = card.dataset.case;
            openCase(caseType);
        });
    });

    // 6. Инициализация интерфейса
    renderInventory();

    // 7. Скрываем загрузчик и показываем основной интерфейс
    setTimeout(() => {
        document.getElementById('welcome-screen').style.display = 'none';
        document.getElementById('app-interface').style.display = 'flex';
    }, 1000);
});