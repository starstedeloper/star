document.addEventListener('DOMContentLoaded', async () => {
    const tg = window.Telegram?.WebApp;
    tg?.expand();

    // Получаем данные пользователя из URL или WebApp
    const params = new URLSearchParams(window.location.search);
    const userId = params.get('user_id') || tg?.initDataUnsafe?.user?.id || '0';
    const username = tg?.initDataUnsafe?.user?.first_name || 'Гость';

    // Инициализация интерфейса
    document.getElementById('user-name').textContent = username;

    // Состояние приложения
    const state = {
        balance: parseInt(params.get('stars')) || 0,
        inventory: JSON.parse(params.get('inventory') || '[]'),
        loading: false
    };

    // Обновление интерфейса
    function updateUI() {
        document.getElementById('stars').textContent = state.balance;
        renderInventory();
    }

    // Рендер инвентаря
    function renderInventory() {
        const container = document.getElementById('inventory-items');
        container.innerHTML = state.inventory.length > 0
            ? state.inventory.map(item => `
                <div class="item-card">
                    <div class="item-emoji">${item.emoji || '🎁'}</div>
                    <div class="item-name">${item.name}</div>
                    <div class="item-price">${item.sell_price} ⭐</div>
                    <div class="item-buttons">
                        <button class="sell-btn" data-id="${item.id}">💰</button>
                        <button class="withdraw-btn" data-id="${item.id}">📤</button>
                    </div>
                </div>
            `).join('')
            : '<div class="empty-message">Инвентарь пуст</div>';
    }

    // Открытие кейса
    async function openCase(caseType) {
        if (state.loading) return;

        try {
            state.loading = true;

            if (state.balance < 10) {  // Пример цены кейса
                alert('Недостаточно звезд!');
                return;
            }

            // Отправляем данные боту через WebApp
            if (tg) {
                tg.sendData(JSON.stringify({
                    action: 'open_case',
                    case_type: caseType,
                    user_id: userId
                }));
            } else {
                alert('Действие доступно только в Telegram');
            }
        } catch (error) {
            console.error('Ошибка:', error);
        } finally {
            state.loading = false;
        }
    }

    // Обработчики событий
    document.getElementById('add-stars').addEventListener('click', () => {
        if (tg) {
            tg.openTelegramLink(`https://t.me/StarAzart_bot?start=pay_${userId}_100`);
        } else {
            window.location.href = `payment.html?user_id=${userId}`;
        }
    });

    document.querySelectorAll('.case-card').forEach(card => {
        card.addEventListener('click', () => openCase(card.dataset.case));
    });

    // Инициализация
    updateUI();
});