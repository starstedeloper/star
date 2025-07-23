document.addEventListener('DOMContentLoaded', () => {
    const tg = window.Telegram?.WebApp;
    if (tg) {
        tg.expand();
        tg.enableClosingConfirmation();
        tg.BackButton.show();
        tg.BackButton.onClick(() => tg.close());
    }

    const state = {
        userId: '0',
        username: 'Гость',
        balance: 0,
        inventory: [],
        loading: false,
        isTelegram: !!tg
    };

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

    function initApp() {
        try {
            const params = new URLSearchParams(window.location.search);
            
            state.userId = params.get('user_id') || (tg?.initDataUnsafe?.user?.id || '0');
            state.username = tg?.initDataUnsafe?.user?.first_name || 'Гость';
            state.balance = parseInt(params.get('stars') || '0');
            
            try {
                const inventoryParam = params.get('inventory');
                if (inventoryParam) {
                    // Декодируем инвентарь из URL
                    state.inventory = JSON.parse(decodeURIComponent(inventoryParam));
                } else {
                    state.inventory = [];
                }
            } catch (e) {
                console.error('Ошибка парсинга инвентаря:', e);
                state.inventory = [];
            }

            updateUI();
            showMainInterface();

            console.log('App initialized with state:', state);

        } catch (error) {
            console.error('Initialization error:', error);
            showMainInterface();
        }
    }

    function updateUI() {
        elements.userName.textContent = state.username;
        elements.starsBalance.textContent = state.balance;
        renderInventory();
    }

    function renderInventory() {
        elements.inventoryItems.innerHTML = state.inventory.length > 0
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

        document.querySelectorAll('.sell-btn').forEach(btn => {
            btn.addEventListener('click', () => sellItem(parseInt(btn.dataset.id)));
        });

        document.querySelectorAll('.withdraw-btn').forEach(btn => {
            btn.addEventListener('click', () => withdrawItem(parseInt(btn.dataset.id)));
        });
    }

    function showMainInterface() {
        elements.welcomeScreen.style.setProperty('display', 'none', 'important');
        elements.appInterface.style.setProperty('display', 'flex', 'important');
    }

    async function sellItem(itemId) {
        if (state.loading) return;
        state.loading = true;

        try {
            const item = state.inventory.find(i => i.id === itemId);
            if (!item) {
                alert("Ошибка: предмет не найден.");
                state.loading = false;
                return;
            }

            if (tg) {
                // Отправляем ID предмета боту
                tg.sendData(JSON.stringify({ action: 'sell_item', item_id: itemId }));
            }
            
            // Оптимистичное обновление: сразу меняем UI
            alert(`Предмет "${item.name}" продан за ${item.sell_price} ⭐`);
            state.balance += item.sell_price;
            state.inventory = state.inventory.filter(i => i.id !== itemId);
            updateUI();

        } finally {
            state.loading = false;
        }
    }

    async function withdrawItem(itemId) {
        if (state.loading) return;
        
        const item = state.inventory.find(i => i.id === itemId);
        if (!item) {
            alert("Ошибка: предмет не найден.");
            return;
        }

         if (tg) {
            // Отправляем ID предмета боту
            tg.sendData(JSON.stringify({ action: 'withdraw_item', item_id: itemId }));
        }
        alert(`Запрос на вывод предмета "${item.name}" отправлен администратору.`);
        
        // Оптимистичное обновление: убираем предмет из списка
        state.inventory = state.inventory.filter(i => i.id !== itemId);
        updateUI();
    }

    async function openCase(caseType) {
        if (state.loading) return;
        state.loading = true;

        try {
            const casePrice = getCasePrice(caseType);
            if (state.balance < casePrice) {
                alert('Недостаточно звезд для открытия этого кейса!');
                return;
            }

            const wonItem = simulateCaseOpening(caseType);
            
            if (tg) {
                tg.sendData(JSON.stringify({ action: 'open_case', caseType: caseType, wonItem: wonItem }));
            }

            alert(`Вы выиграли: ${wonItem.name} (${wonItem.sell_price} ⭐)`);

            state.balance -= casePrice;
            // ВАЖНО: Мы не знаем ID, который создастся в БД.
            // После открытия кейса лучше всего перезагружать приложение,
            // чтобы получить инвентарь с настоящими ID.
            // Для этого можно использовать кнопку "Обновить".
            // Для оптимистичного обновления можно добавить временный ID, но это рискованно.
            // wonItem.id = Date.now(); // Временный ID для UI
            // state.inventory.push(wonItem);
            updateUI();
            alert("Ваш инвентарь будет обновлен. Нажмите кнопку 'Обновить', чтобы увидеть новый предмет.");


        } finally {
            state.loading = false;
        }
    }

    function simulateCaseOpening(caseType) {
        const commonItems = [
            { name: "Сердце", emoji: "❤️", sell_price: 15 }, { name: "Плюшевый мишка", emoji: "🧸", sell_price: 15 },
            { name: "Подарок", emoji: "🎁", sell_price: 25 }, { name: "Роза", emoji: "🌹", sell_price: 25 },
            { name: "Торт", emoji: "🎂", sell_price: 50 }, { name: "Букет", emoji: "💐", sell_price: 50 },
            { name: "Ракета", emoji: "🚀", sell_price: 50 }, { name: "Кубок", emoji: "🏆", sell_price: 100 },
            { name: "Кольцо", emoji: "💍", sell_price: 100 }, { name: "Алмаз", emoji: "💎", sell_price: 100 }
        ];
        // Эта логика симуляции остается на клиенте для быстрого ответа
        const rand = Math.random();
        let index;
        if (caseType === 'legendary' && rand < 0.3) { index = Math.floor(Math.random() * 2) + 8; }
        else if (caseType === 'epic' && rand < 0.5) { index = Math.floor(Math.random() * 3) + 5; }
        else { index = Math.floor(Math.random() * 5); }
        return commonItems[index];
    }

    function getCasePrice(caseType) {
        const prices = { 'common': 10, 'rare': 25, 'epic': 50, 'legendary': 100 };
        return prices[caseType] || 10;
    }

    elements.addStarsBtn.addEventListener('click', () => {
        if (state.isTelegram) {
            // Эта ссылка теперь будет правильно обработана ботом
            tg.openTelegramLink(`https://t.me/StarAzart_bot?start=pay_${state.userId}_100`);
        } else {
            window.location.href = `payment.html?user_id=${state.userId}`;
        }
    });
    
    elements.refreshBalanceBtn.addEventListener('click', () => {
        alert('Обновление данных...');
        // Перезагрузка - самый надежный способ синхронизации в данной архитектуре
        window.location.reload();
    });

    // Обработчики для открытия/закрытия страницы кейсов
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
    setTimeout(initApp, 5000);
});