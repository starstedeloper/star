class CaseOpening {
  constructor(config) {
    this.caseConfig = config;
    this.initElements();
    this.bindEvents();
  }

  initElements() {
    this.caseContainer = document.createElement('div');
    this.caseContainer.id = 'case-opening-container';
    this.caseContainer.className = 'case-opening';
    document.body.appendChild(this.caseContainer);
  }

  bindEvents() {
    document.getElementById('roulette-card').addEventListener('click', () => {
      this.showCaseSelection();
    });
  }

  showCaseSelection() {
    document.getElementById('cases-page').style.display = 'flex';
  }

  openCase(caseType) {
    const selectedCase = this.caseConfig.cases.find(c => c.type === caseType);
    if (!selectedCase) return;

    const wonItem = this.getRandomItem(selectedCase.items);
    this.showWonItem(wonItem);
  }

  getRandomItem(items) {
    const random = Math.random();
    let cumulativeChance = 0;

    for (const item of items) {
      cumulativeChance += item.chance;
      if (random <= cumulativeChance) {
        return item;
      }
    }

    return items[0];
  }

  showWonItem(item) {
    const html = `
      <div class="won-item">
        <div class="arrow"></div>
        <img src="images/items/${item.image}" alt="${item.name}">
        <h3>${item.name}</h3>
        <p>${item.sell_price} ⭐</p>
        <div class="item-actions">
          <button class="sell-btn">💰 Продать за ${item.sell_price} ⭐</button>
          <button class="withdraw-btn">📤 Вывести</button>
        </div>
      </div>
    `;

    this.caseContainer.innerHTML = html;
    this.bindItemActions(item);
  }

  bindItemActions(item) {
    document.querySelector('.sell-btn').addEventListener('click', () => {
      this.sellItem(item);
    });

    document.querySelector('.withdraw-btn').addEventListener('click', () => {
      this.withdrawItem(item);
    });
  }

  sellItem(item) {
    console.log(`Продано: ${item.name} за ${item.sell_price} ⭐`);
  }

  withdrawItem(item) {
    console.log(`Заявка на вывод: ${item.name}`);
  }
}

// Инициализация после загрузки конфига
fetch('config.json')
  .then(response => response.json())
  .then(config => {
    window.caseOpening = new CaseOpening(config);
  });