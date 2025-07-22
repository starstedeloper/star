document.addEventListener('DOMContentLoaded', () => {
    console.log("App started"); // Проверка загрузки

    const tg = window.Telegram?.WebApp;
    const params = new URLSearchParams(window.location.search);

    // Отладочная информация
    console.log("URL params:", {
        user_id: params.get('user_id'),
        stars: params.get('stars'),
        inventory: params.get('inventory')
    });

    console.log("Telegram WebApp data:", tg?.initDataUnsafe?.user);

    // Простая инициализация
    document.getElementById('user-name').textContent =
        tg?.initDataUnsafe?.user?.first_name ||
        params.get('username') ||
        'Гость';

    document.getElementById('stars').textContent =
        params.get('stars') || '0';

    // Проверка работы кнопок
    document.getElementById('add-stars').addEventListener('click', () => {
        console.log("Add stars clicked");
        if (tg) {
            tg.openTelegramLink(`https://t.me/StarAzart_bot?start=pay_${params.get('user_id')}_100`);
        } else {
            window.location.href = `payment.html?user_id=${params.get('user_id')}`;
        }
    });
});

это весь апп джс? для теса