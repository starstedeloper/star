document.addEventListener('DOMContentLoaded', async () => {
  // Инициализация Telegram WebApp
  const tg = window.Telegram?.WebApp;
  tg?.expand();

  // Получаем данные пользователя из Telegram
  const userData = tg?.initDataUnsafe?.user || {};
  const userId = userData.id.toString();
  const username = userData.username || `${userData.first_name || 'Гость'}${userData.last_name ? ' ' + userData.last_name : ''}`;

  // Инициализация UI
  document.getElementById('user-name').textContent = username;

  // Состояние приложения
  let state = {
    balance: 0,
    inventory: [],
    isLoading: false
  };

  // Элементы интерфейса
  const balanceEl = document.getElementById('stars');
  const inventoryEl = document.getElementById('inventory-items');
  const addStarsBtn = document.getElementById('add-stars');
  const refreshBtn = document.getElementById('refresh-balance');
  const rouletteCard = document.getElementById('roulette-card');
  const closeCasesBtn = document.getElementById('close-cases');
  const casesPage = document.getElementById('cases-page');
  const casesContainer = document.querySelector('.cases-container');

  // Инициализация CaseOpening
  let caseOpeningSystem;
  fetch('config.json')
    .then(response => response.json())
    .then(config => {
      caseOpeningSystem = new CaseOpening(config);
    });

  // Загрузка данных пользователя
  async function loadUserData() {
    try {
      state.isLoading = true;
      const response = await fetch(`/api/user?user_id=${userId}`);
      if (response.ok) {
        const data = await response.json();
        state.balance = data.balance;
        state.inventory = data.inventory;
        updateUI();
      }
    } catch (error) {
      console.error('Ошибка загрузки данных:', error);
      // Fallback для демонстрации
      state.balance = 100;
      state.inventory = [];
      updateUI();
    } finally {
      state.isLoading = false;
    }
  }

  // Обновление интерфейса
  function updateUI() {
    balanceEl.textContent = state.balance;
    renderInventory();
  }

  // Рендер инвентаря
  function renderInventory() {
    inventoryEl.innerHTML = state.inventory.length > 0
      ? state.inventory.map(item => `
        <div class="item-card" data-item-id="${item.id}">
          <img src="images/items/${item.image}" alt="${item.name}">
          <div class="item-name">${item.name}</div>
          <div class="item-actions">
            <button class="sell-btn" data-price="${item.sell_price}">💰 ${item.sell_price}⭐</button>
            <button class="withdraw-btn">📤 Вывести</button>
          </div>
        </div>
      `).join('')
      : '<div class="empty-message">Инвентарь пуст</div>';

    // Навешиваем обработчики
    document.querySelectorAll('.sell-btn').forEach(btn => {
      btn.addEventListener('click', async () => {
        const itemId = btn.closest('.item-card').dataset.itemId;
        const price = parseInt(btn.dataset.price);
        if (confirm(`Продать предмет за ${price} ⭐?`)) {
          await sellItem(itemId, price);
        }
      });
    });
  }

  // Продажа предмета
  async function sellItem(itemId, price) {
    try {
      const response = await fetch('/api/sell-item', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          user_id: userId,
          item_id: itemId
        })
      });

      if (response.ok) {
        state.balance += price;
        state.inventory = state.inventory.filter(item => item.id !== itemId);
        updateUI();
        showAlert(`Предмет продан за ${price} ⭐`);
      }
    } catch (error) {
      console.error('Ошибка продажи:', error);
      showAlert('Ошибка при продаже предмета', true);
    }
  }

  // Показать уведомление
  function showAlert(message, isError = false) {
    const alert = document.createElement('div');
    alert.className = `payment-alert ${isError ? 'error' : ''}`;
    alert.textContent = message;
    document.body.appendChild(alert);

    setTimeout(() => {
      alert.remove();
    }, 3000);
  }

  // Открытие кейса
  async function openCase(caseType) {
    if (state.isLoading) return;

    try {
      state.isLoading = true;

      // Проверяем баланс (в реальном приложении нужно проверять цену кейса)
      if (state.balance < 74.5) {
        showAlert('Недостаточно средств!', true);
        return;
      }

      const response = await fetch('/api/open-case', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          user_id: userId,
          case_type: caseType
        })
      });

      if (response.ok) {
        const result = await response.json();
        state.balance -= 74.5; // Вычитаем стоимость кейса
        state.inventory.push(result.item); // Добавляем предмет в инвентарь
        updateUI();

        // Показываем выигрыш через систему кейсов
        caseOpeningSystem.showWonItem(result.item);
      }
    } catch (error) {
      console.error('Ошибка открытия кейса:', error);
      showAlert('Ошибка при открытии кейса', true);
    } finally {
      state.isLoading = false;
    }
  }

  // Обработчики событий
  addStarsBtn.addEventListener('click', () => {
    if (tg) {
      tg.openTelegramLink(`https://t.me/StarAzart_bot?start=addstars_${userId}`);
    } else {
      window.location.href = `payment.html?user_id=${userId}`;
    }
  });

  refreshBtn.addEventListener('click', loadUserData);

  rouletteCard.addEventListener('click', () => {
    casesPage.style.display = 'flex';
  });

  closeCasesBtn.addEventListener('click', () => {
    casesPage.style.display = 'none';
  });

  // Обработчики для кейсов
  casesContainer.addEventListener('click', (e) => {
    const caseCard = e.target.closest('.case-card');
    if (caseCard) {
      const caseType = caseCard.dataset.case;
      openCase(caseType);
      casesPage.style.display = 'none';
    }
  });

  // Первоначальная загрузка
  loadUserData();
});

// Вспомогательная функция для показа алертов
function showAlert(message, isError = false) {
  const alert = document.createElement('div');
  alert.className = `payment-alert ${isError ? 'error' : ''}`;
  alert.textContent = message;
  document.body.appendChild(alert);

  setTimeout(() => {
    alert.remove();
  }, 3000);
}