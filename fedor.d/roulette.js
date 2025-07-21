class Roulette {
  constructor(items) {
    this.items = items;
    this.isSpinning = false;
    this.initDOM();
  }

  initDOM() {
    this.container = document.createElement('div');
    this.container.className = 'roulette-container';

    this.arrow = document.createElement('div');
    this.arrow.className = 'roulette-arrow';

    this.itemsContainer = document.createElement('div');
    this.itemsContainer.className = 'roulette-items';

    this.items.forEach(item => {
      const itemElement = document.createElement('div');
      itemElement.className = 'roulette-item';
      itemElement.innerHTML = `
        <img src="images/${item.image}" alt="${item.name}">
        <div class="item-chance">${Math.round(item.chance * 100)}%</div>
      `;
      this.itemsContainer.appendChild(itemElement);
    });

    this.container.appendChild(this.arrow);
    this.container.appendChild(this.itemsContainer);
    document.body.appendChild(this.container);
  }

  spin() {
    if (this.isSpinning) return;
    this.isSpinning = true;

    // Выбираем случайный предмет с учетом шансов
    const random = Math.random();
    let cumulativeChance = 0;
    let selectedIndex = 0;

    for (let i = 0; i < this.items.length; i++) {
      cumulativeChance += this.items[i].chance;
      if (random <= cumulativeChance) {
        selectedIndex = i;
        break;
      }
    }

    // Анимация прокрутки
    const itemWidth = 100;
    const targetPosition = -(selectedIndex * itemWidth);
    const spinDuration = 3000 + Math.random() * 2000; // 3-5 секунд

    this.itemsContainer.style.transition = `transform ${spinDuration/1000}s cubic-bezier(0.2, 0.1, 0.2, 1)`;
    this.itemsContainer.style.transform = `translateX(${targetPosition - 500}px)`;

    // Частицы
    this.createParticles();

    setTimeout(() => {
      this.isSpinning = false;
      this.showResult(this.items[selectedIndex]);
    }, spinDuration);
  }

  createParticles() {
    for (let i = 0; i < 50; i++) {
      const particle = document.createElement('div');
      particle.className = 'particle';
      particle.style.left = `${Math.random() * 100}%`;
      particle.style.top = `${Math.random() * 100}%`;
      particle.style.animationDelay = `${Math.random() * 0.5}s`;
      this.container.appendChild(particle);

      setTimeout(() => particle.remove(), 3000);
    }
  }

  showResult(item) {
    const result = document.createElement('div');
    result.className = 'roulette-result';
    result.innerHTML = `
      <h3>Поздравляем!</h3>
      <img src="images/${item.image}" alt="${item.name}">
      <p>${item.name}</p>
      <button class="close-roulette">Забрать</button>
    `;

    this.container.appendChild(result);
    result.querySelector('.close-roulette').addEventListener('click', () => {
      this.container.remove();
      // Здесь можно добавить предмет в инвентарь
    });
  }
}