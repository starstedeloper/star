document.addEventListener('DOMContentLoaded', () => {
    const tg = window.Telegram?.WebApp;
    if (tg) {
        tg.expand();
        tg.enableClosingConfirmation();
        tg.BackButton.show();
        tg.BackButton.onClick(() => tg.close());
    }

    // Инициализируем рулетку глобально
    const roulette = new Roulette();

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
        rouletteCard: document.getElementById('roulette-card'),
        casesPage: document.getElementById('cases-page'),
        closeCasesBtn: document.getElementById('close-cases')
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
                        <!-- ИЗМЕНЕНИЕ №2: Добавлен текст к кнопкам -->
                        <button class="sell-btn" data-id="${item.id}">Продать</button>
                        <button class="withdraw-btn" data-id="${item.id}">Вывести</button>
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
                tg.sendData(JSON.stringify({ action: 'sell_item', item_id: itemId }));
            }
            
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
        if (!item) { alert("Ошибка: предмет не найден."); return; }

         if (tg) {
            tg.sendData(JSON.stringify({ action: 'withdraw_item', item_id: itemId }));
        }
        alert(`Запрос на вывод предмета "${item.name}" отправлен.`);
        
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
            
            // Получаем пул предметов для анимации и симулируем выигрыш
            const { pool, wonItem } = simulateCaseOpening(caseType);
            
            // ИЗМЕНЕНИЕ №4: Запускаем анимацию рулетки вместо alert
            await roulette.spin(pool, wonItem);

            // Отправляем данные боту ПОСЛЕ анимации
            if (tg) {
                tg.sendData(JSON.stringify({ action: 'open_case', caseType: caseType, wonItem: wonItem }));
            }

            // Обновляем баланс локально
            state.balance -= casePrice;
            updateUI();
            
            alert(`Вы выиграли: ${wonItem.name}! Нажмите "Обновить", чтобы предмет появился в инвентаре.`);

        } catch(e) {
            console.error("Ошибка при открытии кейса:", e);
        } finally {
            state.loading = false;
        }
    }

    // ИЗМЕНЕНИЕ №3: Полностью переработанная логика выпадения предметов
    function simulateCaseOpening(caseType) {
        const items = {
            common: [
                { name: "Сердце", emoji: "❤️", sell_price: 15 }, 
                { name: "Плюшевый мишка", emoji: "🧸", sell_price: 15 }
            ],
            rare: [
                { name: "Подарок", emoji: "🎁", sell_price: 25 }, 
                { name: "Роза", emoji: "🌹", sell_price: 25 }
            ],
            epic: [
                { name: "Торт", emoji: "🎂", sell_price: 50 }, 
                { name: "Букет", emoji: "💐", sell_price: 50 },
                { name: "Ракета", emoji: "🚀", sell_price: 50 }
            ],
            legendary: [
                { name: "Кубок", emoji: "🏆", sell_price: 100 }, 
                { name: "Кольцо", emoji: "💍", sell_price: 100 }, 
                { name: "Алмаз", emoji: "💎", sell_price: 100 }
            ]
        };

        let pool = [];
        // Формируем пул предметов в зависимости от типа кейса
        switch(caseType) {
            case 'common':
                pool = [...items.common, ...items.rare];
                break;
            case 'rare':
                pool = [...items.rare, ...items.epic];
                break;
            case 'epic':
                pool = [...items.epic, ...items.legendary];
                break;
            case 'legendary':
                pool = [...items.legendary, ...items.epic];
                break;
            default:
                pool = items.common;
        }

        // Выбираем случайный предмет из сформированного пула
        const wonItem = pool[Math.floor(Math.random() * pool.length)];
        
        // Возвращаем и пул для анимации, и сам выигрыш
        return { pool, wonItem };
    }

    function getCasePrice(caseType) {
        const prices = { 'common': 10, 'rare': 25, 'epic': 50, 'legendary': 100 };
        return prices[caseType] || 10;
    }

    // --- Обработчики событий ---
    elements.addStarsBtn.addEventListener('click', () => {
        if (state.isTelegram) {
            tg.openTelegramLink(`https://t.me/StarAzart_bot?start=pay_${state.userId}_100`);
        } else {
            // Для дебага в браузере
            window.open(`payment.html?user_id=${state.userId}`, '_blank');
        }
    });
    
    elements.refreshBalanceBtn.addEventListener('click', () => {
        alert('Обновление данных...');
        window.location.reload();
    });

    elements.rouletteCard.addEventListener('click', () => {
        elements.casesPage.style.display = 'flex';
    });
    
    elements.closeCasesBtn.addEventListener('click', () => {
        elements.casesPage.style.display = 'none';
    });
    
    document.querySelectorAll('.case-card').forEach(card => {
        card.addEventListener('click', () => {
            elements.casesPage.style.display = 'none';
            openCase(card.dataset.case);
        });
    });

    setTimeout(initApp, 2000); // Уменьшил задержку для скорости
});
