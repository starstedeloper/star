document.addEventListener('DOMContentLoaded', () => {
    const tg = window.Telegram?.WebApp;
    const userId = new URLSearchParams(window.location.search).get('user_id');

    // Элементы интерфейса
    const backButton = document.getElementById('back-button');
    const presetOptions = document.querySelectorAll('.preset-option');
    const customStarsInput = document.getElementById('custom-stars');
    const amountPreview = document.getElementById('amount-preview');
    const payButton = document.getElementById('pay-button');
    const paymentStatus = document.getElementById('payment-status');
    const invoiceInfo = document.getElementById('invoice-info');
    const checkPayment = document.getElementById('check-payment');
    const cancelPayment = document.getElementById('cancel-payment');

    // Курс 1.4 рубля за звезду
    const STARS_RATE = 1.4;
    let currentStars = 0;

    // Навигация
    backButton.addEventListener('click', () => {
        window.location.href = `index.html?user_id=${userId}`;
    });

    // Пресеты звезд
    presetOptions.forEach(option => {
        option.addEventListener('click', function() {
            currentStars = parseInt(this.getAttribute('data-stars'));
            customStarsInput.value = currentStars;
            updateAmountPreview();
            this.classList.add('active');

            // Удаляем активный класс у других кнопок
            presetOptions.forEach(btn => {
                if(btn !== this) btn.classList.remove('active');
            });
        });
    });

    // Кастомный ввод
    customStarsInput.addEventListener('input', function() {
        currentStars = parseInt(this.value) || 0;

        // Сбрасываем активный пресет если вводим вручную
        presetOptions.forEach(btn => btn.classList.remove('active'));

        updateAmountPreview();
    });

    function updateAmountPreview() {
        const rub = Math.round(currentStars * STARS_RATE);
        amountPreview.textContent = `${currentStars} ⭐ = ${rub} ₽`;
        amountPreview.style.display = currentStars > 0 ? 'block' : 'none';
    }

    // Создание инвойса
    payButton.addEventListener('click', async () => {
        if (currentStars < 10) {
            alert('Минимальная сумма - 10 звезд');
            return;
        }

        if (tg) {
            // Открываем бота для оплаты
            tg.openTelegramLink(`https://t.me/StarAzart_bot?start=pay_${userId}_${currentStars}`);
        } else {
            window.open(`https://t.me/StarAzart_bot?start=pay_${userId}_${currentStars}`, '_blank');
        }
    });

    // Инициализация
    updateAmountPreview();
});