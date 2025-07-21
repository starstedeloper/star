document.addEventListener('DOMContentLoaded', async () => {
    const tg = window.Telegram?.WebApp;
    tg?.expand();

    // Получение данных пользователя
    const user = tg?.initDataUnsafe?.user || {};
    const userId = user.id?.toString() || '0';
    const username = user.username || user.first_name || 'Гость';

    // Инициализация интерфейса
    document.getElementById('user-name').textContent = username;

    // Состояние приложения
    const state = {
        balance: 0,
        inventory: [],
        loading: false
    };

    // Загрузка данных
    async function loadUserData() {
        try {
            state.loading = true;
            const response = await fetch(`/api/user?user_id=${userId}`);

            if (response.ok) {
                const data = await response.json();
                state.balance = data.balance || 0;
                state.inventory = data.inventory || [];
                updateUI();
            }
        } catch (error) {
            console.error('Ошибка загрузки:', error);
        } finally {
            state.loading = false;
            hideLoader();
        }
    }

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
                    <img src="images/items/${item.image}" alt="${item.name}">
                    <div class="item-name">${item.name}</div>
                    <div class="item-price">${item.sell_price} ⭐</div>
                </div>
            `).join('')
            : '<div class="empty-message">Инвентарь пуст</div>';
    }

    // Открытие кейса
    async function openCase(caseType) {
        if (state.loading) return;

        try {
            state.loading = true;
            const response = await fetch('/api/open-case', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    user_id: userId,
                    case_type: caseType
                })
            });

            if (response.ok) {
                const result = await response.json();
                state.balance = result.new_balance;
                state.inventory.push(result.item);
                updateUI();
                showWonItem(result.item);
            }
        } catch (error) {
            console.error('Ошибка:', error);
        } finally {
            state.loading = false;
        }
    }

    // Показ выигранного предмета
    function showWonItem(item) {
        const html = `
            <div class="won-item">
                <h3>🎉 Вы выиграли!</h3>
                <img src="images/items/${item.image}" alt="${item.name}">
                <div class="item-name">${item.name}</div>
                <div class="item-price">${item.sell_price} ⭐</div>
            </div>
        `;

        const container = document.createElement('div');
        container.className = 'item-popup';
        container.innerHTML = html;
        document.body.appendChild(container);

        setTimeout(() => container.remove(), 3000);
    }

    // Инициализация
    function hideLoader() {
        const loader = document.getElementById('welcome-screen');
        const app = document.getElementById('app-interface');
        if (loader) loader.style.display = 'none';
        if (app) app.style.display = 'flex';
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

    // Запуск
    loadUserData();
});