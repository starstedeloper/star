document.addEventListener('DOMContentLoaded', async () => {
  const tg = window.Telegram?.WebApp;
  const userId = tg?.initDataUnsafe?.user?.id || 'test_user';

  // Загрузка данных
  let balance = 1000;
  let inventory = [];

  function updateBalance(value) {
    balance = value;
    document.getElementById('stars').textContent = balance;
  }

  function updateInventory(items) {
    inventory = items;
    renderInventory();
  }

  function renderInventory() {
    const container = document.getElementById('inventory-items');
    container.innerHTML = inventory.length ? inventory.map(item => `
      <div class="item-card">
        <img src="images/${item.image}" alt="${item.name}">
        <div class="item-name">${item.name}</div>
        <div class="item-actions">
          <button class="sell-btn" data-price="${item.price}">💰 ${item.price}⭐</button>
          <button class="withdraw-btn">📤 Вывести</button>
        </div>
      </div>
    `).join('') : '<div class="empty-message">Инвентарь пуст</div>';

    // Навешиваем обработчики
    document.querySelectorAll('.sell-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        if (confirm(`Продать за ${btn.dataset.price} ⭐?`)) {
          updateBalance(balance + parseInt(btn.dataset.price));
          // Удаляем предмет из инвентаря
        }
      });
    });
  }

  // Инициализация рулетки
  const caseItems = [
    { name: "Сердце", image: "heart.png", price: 15, chance: 0.2 },
    { name: "Календарь", image: "calendar.png", price: 87, chance: 0.1 },
    { name: "Торт", image: "cake.png", price: 50, chance: 0.3 }
  ];

  document.getElementById('roulette-card').addEventListener('click', () => {
    if (balance < 74.5) {
      alert('Недостаточно средств!');
      return;
    }
    updateBalance(balance - 74.5);
    new Roulette(caseItems).spin();
  });

  // Первоначальная загрузка
  updateBalance(1000);
  updateInventory([]);
});