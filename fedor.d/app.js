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
        inventory = JSON.parse(params.get('inventory') || '[]');
    } catch (e) {
        console.error('Ошибка парсинга инвентаря:', e);
        inventory = [];
    }

    // 2. Устанавливаем начальное состояние
    const state = {
        balance: parseInt(stars) || 0,
        inventory: inventory,
        loading: false
    };

    // 3. Обновляем интерфейс
    function updateUI() {
        document.getElementById('user-name').textContent = username;
        document.getElementById('stars').textContent = state.balance;
        renderInventory();
    }

    // 4. Рендерим инвентарь
    function renderInventory() {
        const container = document.getElementById('inventory-items');
        container.innerHTML = state.inventory.length > 0
            ? state.inventory.map(item => `
                <div class="item-card">
                    <div class="item-emoji">${item.emoji || '🎁'}</div>
                    <div class="item-name">${item.name}</div>
                    <div class="item-price">${item.sell_price} ⭐</div>
                </div>
            `).join('')
            : '<div class="empty-message">Инвентарь пуст</div>';
    }

    // 5. Функция открытия кейса (упрощенная версия)
    function openCase(caseType) {
        if (state.loading) return;
        alert(`Открытие кейса ${caseType} будет доступно после настройки бота`);
    }

    // 6. Показываем основной интерфейс
    function showMainInterface() {
        document.getElementById('welcome-screen').style.display = 'none';
        document.getElementById('app-interface').style.display = 'flex';
        updateUI();
    }

    // 7. Обработчики событий
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

    // 8. Инициализация приложения
    setTimeout(() => {
        showMainInterface();

        // Для отладки
        console.log('App initialized with:', {
            userId: userId,
            balance: state.balance,
            inventory: state.inventory
        });
    }, 1000);
});