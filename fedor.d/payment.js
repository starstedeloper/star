document.addEventListener('DOMContentLoaded', () => {
    const params = new URLSearchParams(window.location.search);
    const userId = params.get('user_id');
    const tg = window.Telegram?.WebApp;

    // Элементы
    const backBtn = document.getElementById('back-button');
    const presetBtns = document.querySelectorAll('.preset-option');
    const customInput = document.getElementById('custom-stars');
    const preview = document.getElementById('amount-preview');
    const payBtn = document.getElementById('pay-button');

    // Настройки
    const RATE = 1.4;
    let selectedStars = 0;

    // Инициализация
    function updatePreview() {
        const rubles = (selectedStars * RATE).toFixed(2);
        preview.textContent = `${selectedStars} ⭐ = ${rubles} ₽`;
        preview.style.display = selectedStars > 0 ? 'block' : 'none';
    }

    // Обработчики
    backBtn.addEventListener('click', () => {
        if (tg) tg.close();
        else window.history.back();
    });

    presetBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            selectedStars = parseInt(btn.dataset.stars);
            customInput.value = selectedStars;
            updatePreview();
        });
    });

    customInput.addEventListener('input', () => {
        selectedStars = Math.max(10, parseInt(customInput.value) || 0);
        customInput.value = selectedStars;
        updatePreview();
    });

    payBtn.addEventListener('click', () => {
        if (selectedStars < 10) {
            alert('Минимум 10 звезд');
            return;
        }

        const url = `https://t.me/StarAzart_bot?start=pay_${userId}_${selectedStars}`;
        if (tg) tg.openTelegramLink(url);
        else window.open(url, '_blank');
    });

    // Старт
    updatePreview();
});