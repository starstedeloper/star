document.addEventListener('DOMContentLoaded', () => {
    // Инициализация Telegram WebApp
    const tg = window.Telegram?.WebApp;
    if (tg) {
        tg.expand();
        tg.enableClosingConfirmation();
        tg.BackButton.show();
        tg.BackButton.onClick(() => tg.close());
    }

    // Состояние приложения
    const state = {
        userId: '0',
        username: 'Гость',
        balance: 0,
        inventory: [],
        loading: false,
        isTelegram: !!tg
    };

    // DOM элементы
    const elements = {
        welcomeScreen: document.getElementById('welcome-screen'),
        appInterface: document.getElementById('app-interface'),
        userName: document.getElementById('user-name'),
        starsBalance: document.getElementById('stars'),
        inventoryItems: document.getElementById('inventory-items'),
        addStarsBtn: document.getElementById('add-stars'),
        refreshBalanceBtn: document.getElementById('refresh-balance'),
        rouletteCard: document.getElementById('roulette-card')
    };

    // Инициализация приложения
    async function initApp() {
        try {
            // Получаем данные из URL или Telegram WebApp
            const params = new URLSearchParams(window.location.search);

            state.userId = params.get('user_id') || (tg?.initDataUnsafe?.user?.id || '0');
            state.username = params.get('username') || tg?.initDataUnsafe?.user?.first_name || 'Гость';
            state.balance = parseInt(params.get('stars') || '0');

            try {
                state.inventory = JSON.parse(params.get('inventory') || '[]');
            } catch (e) {
                console.error('Ошибка парсинга инвентаря:', e);
                state.inventory = [];
            }

            // Обновляем UI
            updateUI();

            // Показываем основной интерфейс
            showMainInterface();

            // Для отладки
            console.log('App initialized with:', state);

        } catch (error) {
            console.error('Initialization error:', error);
            // Показываем интерфейс даже при ошибке
            showMainInterface();
        }
    }

    // Обновление интерфейса
    function updateUI() {
        elements.userName.textContent = state.username;
        elements.starsBalance.textContent = state.balance;
        renderInventory();
    }

    // Рендер инвентаря
    function renderInventory() {
        elements.inventoryItems.innerHTML = state.inventory.length > 0
            ? state.inventory.map(item => `
                <div class="item-card">
                    <div class="item-emoji">${item.emoji || '🎁'}</div>
                    <div class="item-name">${item.name}</div>
                    <div class="item-price">${item.sell_price} ⭐</div>
                    <div class="item-buttons">
                        <button class="sell-btn" data-id="${item.name}">💰</button>
                        <button class="withdraw-btn" data-id="${item.name}">📤</button>
                    </div>
                </div>
            `).join('')
            : '<div class="empty-message">Инвентарь пуст</div>';

        // Добавляем обработчики для кнопок
        document.querySelectorAll('.sell-btn').forEach(btn => {
            btn.addEventListener('click', () => sellItem(btn.dataset.id));
        });

        document.querySelectorAll('.withdraw-btn').forEach(btn => {
            btn.addEventListener('click', () => withdrawItem(btn.dataset.id));
        });
    }

    // Показать основной интерфейс
    function showMainInterface() {
        elements.welcomeScreen.style.display = 'none';
        elements.appInterface.style.display = 'flex';
    }

    // Функции для работы с предметами
    async function sellItem(itemName) {
        if (state.loading) return;
        state.loading = true;

        try {
            const item = state.inventory.find(i => i.name === itemName);
            if (!item) return;

            // Здесь должна быть логика продажи через бота
            alert(`Предмет "${item.name}" продан за ${item.sell_price} ⭐`);

            // Обновляем состояние
            state.balance += item.sell_price;
            state.inventory = state.inventory.filter(i => i.name !== itemName);
            updateUI();

        } finally {
            state.loading = false;
        }
    }

    async function withdrawItem(itemName) {
        if (state.loading) return;
        alert(`Запрос на вывод предмета "${itemName}" отправлен`);
    }

    // Открытие кейса
    async function openCase(caseType) {
        if (state.loading) return;
        state.loading = true;

        try {
            // Проверяем баланс
            const casePrice = getCasePrice(caseType);
            if (state.balance < casePrice) {
                alert('Недостаточно звезд для открытия этого кейса!');
                return;
            }

            // Здесь должна быть логика открытия кейса через бота
            const wonItem = simulateCaseOpening(caseType);
            alert(`Вы выиграли: ${wonItem.name} (${wonItem.sell_price} ⭐)`);

            // Обновляем состояние
            state.balance -= casePrice;
            state.inventory.push(wonItem);
            updateUI();

        } finally {
            state.loading = false;
        }
    }

    // Симуляция открытия кейса (для демо)
    function simulateCaseOpening(caseType) {
        const commonItems = [
            { name: "Сердце", emoji: "❤️", sell_price: 15 },
            { name: "Плюшевый мишка", emoji: "🧸", sell_price: 15 },
            { name: "Подарок", emoji: "🎁", sell_price: 25 },
            { name: "Роза", emoji: "🌹", sell_price: 25 },
            { name: "Торт", emoji: "🎂", sell_price: 50 },
            { name: "Букет", emoji: "💐", sell_price: 50 },
            { name: "Ракета", emoji: "🚀", sell_price: 50 },
            { name: "Кубок", emoji: "🏆", sell_price: 100 },
            { name: "Кольцо", emoji: "💍", sell_price: 100 },
            { name: "Алмаз", emoji: "💎", sell_price: 100 }
        ];

        // Простая логика - чем дороже кейс, тем лучше шансы
        const index = Math.floor(Math.random() * commonItems.length * (caseType === 'legendary' ? 0.3 : caseType === 'epic' ? 0.5 : 0.8));
        return commonItems[Math.min(index, commonItems.length - 1)];
    }

    function getCasePrice(caseType) {
        const prices = {
            'common': 10,
            'rare': 25,
            'epic': 50,
            'legendary': 100
        };
        return prices[caseType] || 10;
    }

    // Обработчики событий
    elements.addStarsBtn.addEventListener('click', () => {
        if (state.isTelegram) {
            tg.openTelegramLink(`https://t.me/StarAzart_bot?start=pay_${state.userId}_100`);
        } else {
            window.location.href = `payment.html?user_id=${state.userId}`;
        }
    });

    elements.refreshBalanceBtn.addEventListener('click', async () => {
        // Здесь должна быть логика обновления баланса
        alert('Баланс обновлен');
    });

    elements.rouletteCard.addEventListener('click', () => {
        document.getElementById('cases-page').style.display = 'flex';
    });

    document.getElementById('close-cases').addEventListener('click', () => {
        document.getElementById('cases-page').style.display = 'none';
    });

    document.querySelectorAll('.case-card').forEach(card => {
        card.addEventListener('click', () => {
            document.getElementById('cases-page').style.display = 'none';
            openCase(card.dataset.case);
        });
    });

    // Запуск приложения с задержкой для анимации
    setTimeout(initApp, 1000);
});