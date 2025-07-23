class Roulette {
    constructor() {
        this.container = null;
        this.itemsContainer = null;
        this.resultContainer = null;
        this.isSpinning = false;
        // Элементы создаются один раз при инициализации
        this._createDOM();
    }

    _createDOM() {
        // Создаем главный контейнер для рулетки
        this.container = document.createElement('div');
        this.container.className = 'roulette-container';

        // Создаем стрелку-указатель
        const arrow = document.createElement('div');
        arrow.className = 'roulette-arrow';

        // Создаем обертку для ленты с предметами
        this.itemsContainer = document.createElement('div');
        this.itemsContainer.className = 'roulette-items';

        // Создаем контейнер для отображения результата
        this.resultContainer = document.createElement('div');
        this.resultContainer.className = 'roulette-result';

        // Собираем все элементы вместе и добавляем на страницу (изначально скрыто)
        this.container.appendChild(arrow);
        this.container.appendChild(this.itemsContainer);
        this.container.appendChild(this.resultContainer);
        document.body.appendChild(this.container);
    }

    /**
     * Запускает анимацию рулетки
     * @param {Array} itemsPool - Массив предметов для показа в ленте.
     * @param {Object} wonItem - Предмет, на котором нужно остановиться.
     * @returns {Promise} - Завершается, когда анимация окончена.
     */
    spin(itemsPool, wonItem) {
        return new Promise((resolve) => {
            if (this.isSpinning) return resolve();
            this.isSpinning = true;

            // 1. Готовим ленту для анимации
            // Повторяем пул предметов много раз, чтобы лента была длинной
            const repeatedPool = Array(10).fill(itemsPool).flat();
            // Находим индекс выигрышного предмета ближе к концу ленты
            const finalIndex = repeatedPool.length - itemsPool.length + itemsPool.findIndex(item => item.name === wonItem.name);

            // Генерируем HTML для ленты
            this.itemsContainer.innerHTML = repeatedPool.map(item => `
                <div class="roulette-item">
                    <div class="roulette-item-emoji">${item.emoji || '🎁'}</div>
                    <div class="roulette-item-name">${item.name}</div>
                </div>
            `).join('');
            
            // 2. Показываем рулетку и сбрасываем ее состояние
            this.container.style.display = 'flex';
            this.resultContainer.style.display = 'none';
            this.itemsContainer.style.transition = 'none';
            this.itemsContainer.style.transform = 'translateX(0px)';

            // 3. Рассчитываем позицию для остановки
            // requestAnimationFrame гарантирует, что расчеты произойдут после отрисовки
            requestAnimationFrame(() => {
                const itemElementWidth = this.itemsContainer.querySelector('.roulette-item').offsetWidth + 10; // Ширина + gap
                const containerWidth = this.container.offsetWidth;

                // Цель - отцентровать выигрышный предмет под стрелкой
                const targetPosition = - (finalIndex * itemElementWidth) + (containerWidth / 2) - (itemElementWidth / 2);
                
                // Добавляем небольшое случайное смещение, чтобы остановка не была всегда в одном и том же пикселе
                const randomOffset = (Math.random() - 0.5) * itemElementWidth * 0.8;
                const finalPosition = targetPosition + randomOffset;
                const spinDuration = 5000; // 5 секунд

                // 4. Запускаем CSS-анимацию прокрутки
                setTimeout(() => {
                    this.itemsContainer.style.transition = `transform ${spinDuration / 1000}s cubic-bezier(0.2, 0.8, 0.2, 1)`;
                    this.itemsContainer.style.transform = `translateX(${finalPosition}px)`;
                }, 100);


                // 5. Показываем результат после завершения анимации
                setTimeout(() => {
                    this._showResult(wonItem);
                    this.isSpinning = false;
                    resolve(); // Завершаем Promise
                }, spinDuration + 200);
            });
        });
    }

    _showResult(item) {
        // Показываем красивый попап с результатом
        this.resultContainer.innerHTML = `
            <h3>Вы выиграли!</h3>
            <div class="result-emoji">${item.emoji || '🎁'}</div>
            <p class="result-name">${item.name}</p>
            <p class="result-price">${item.sell_price} ⭐</p>
            <button class="close-roulette">Забрать</button>
        `;
        this.resultContainer.style.display = 'flex';

        // Добавляем обработчик на кнопку "Забрать", который сработает один раз
        this.resultContainer.querySelector('.close-roulette').addEventListener('click', () => {
            this.container.style.display = 'none';
        }, { once: true });
    }
}
