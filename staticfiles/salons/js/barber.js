// static/salons/js/barber.js

document.addEventListener('DOMContentLoaded', function() {
    // Переменные для хранения выбранных барберов по категориям
    let selectedBarbers = {}; // Ключ: categoryId, Значение: barberId

    // Получаем данные барберов по категориям из глобальной переменной
    // Определена в шаблоне salon-services.html
    // Например: const barbersByCategory = {"category_1": [...], "category_2": [...]}
    
    // Обработчики для кнопок категорий
    const categoryButtons = document.querySelectorAll('.category-button');
    const barbersContainer = document.getElementById('barbers-container'); // Контейнер для барберов

    // Инициализируем выбор барберов при загрузке первой категории
    if (categoryButtons.length > 0) {
        const firstCategoryButton = categoryButtons[0];
        const firstCategoryId = firstCategoryButton.getAttribute('data-category-id');
        showBarbersForCategory(firstCategoryId);
        firstCategoryButton.classList.add('selected');
    }

    // Обработчики для кнопок категорий
    categoryButtons.forEach(button => {
        button.addEventListener('click', function() {
            // Удаляем класс 'selected' со всех кнопок
            categoryButtons.forEach(btn => btn.classList.remove('selected'));
            // Добавляем класс 'selected' на текущую кнопку
            this.classList.add('selected');

            const categoryId = this.getAttribute('data-category-id');
            showBarbersForCategory(categoryId);
        });
    });

    // Функция для отображения барберов для выбранной категории
    function showBarbersForCategory(categoryId) {
        barbersContainer.innerHTML = ''; // Очищаем контейнер

        const barbers = barbersByCategory[`category_${categoryId}`];
        if (barbers && barbers.length > 0) {
            // Добавляем опцию "Любой мастер"
            const anyBarberCard = createBarberCard('any', 'Любой мастер', '/static/salons/img/default-avatar.png', 'Описание или слоган', categoryId);
            barbersContainer.appendChild(anyBarberCard);

            // Добавляем барберов
            barbers.forEach(barber => {
                const barberCard = createBarberCard(
                    barber.id,
                    barber.name,
                    barber.avatar || '/static/salons/img/default-avatar.png',
                    barber.description || '',
                    categoryId
                );
                barbersContainer.appendChild(barberCard);
            });

            // Добавляем обработчики событий на новые карточки барберов
            addBarberCardEventListeners();
        } else {
            // Если барберов нет, отображаем сообщение
            barbersContainer.innerHTML = '<p>Нет доступных мастеров для выбранной категории.</p>';
        }
    }

    // Функция для создания карточки барбера
    function createBarberCard(barberId, name, avatarUrl, description, categoryId) {
        const card = document.createElement('div');
        card.classList.add('barber-card');
        card.setAttribute('data-barber-id', barberId);
        card.setAttribute('data-category-id', categoryId);

        const img = document.createElement('img');
        img.src = avatarUrl;
        img.alt = name;
        img.classList.add('barber-avatar');

        const infoDiv = document.createElement('div');
        infoDiv.classList.add('barber-info');

        const nameElem = document.createElement('h4');
        nameElem.classList.add('barber-name');
        nameElem.textContent = name;

        const descElem = document.createElement('p');
        descElem.classList.add('barber-description');
        descElem.textContent = description;

        infoDiv.appendChild(nameElem);
        infoDiv.appendChild(descElem);

        card.appendChild(img);
        card.appendChild(infoDiv);

        return card;
    }

    // Функция для добавления обработчиков событий на карточки барберов
    function addBarberCardEventListeners() {
        const barberCards = document.querySelectorAll('.barber-card');
        barberCards.forEach(card => {
            card.addEventListener('click', function() {
                const categoryId = this.getAttribute('data-category-id');
                const barberId = this.getAttribute('data-barber-id');
                selectBarberForCategory(categoryId, barberId);
            });
        });
    }

    // Функция для выбора барбера для категории
    function selectBarberForCategory(categoryId, barberId) {
        selectedBarbers[categoryId] = barberId;
        updateBarberSelectionUI(categoryId, barberId);

        // После выбора барбера, возможно, нужно обновить доступные минуты
        // Отправляем кастомное событие с деталями выбора
        const event = new CustomEvent('barberSelected', { detail: { categoryId, barberId } });
        document.dispatchEvent(event);
    }

    // Функция для обновления UI после выбора барбера
    function updateBarberSelectionUI(categoryId, barberId) {
        // Убираем выделение со всех барберов в данной категории
        document.querySelectorAll(`.barber-card[data-category-id="${categoryId}"]`).forEach(card => {
            card.classList.remove('selected');
        });
        // Выделяем выбранного барбера
        const selectedCard = document.querySelector(`.barber-card[data-category-id="${categoryId}"][data-barber-id="${barberId}"]`);
        if (selectedCard) {
            selectedCard.classList.add('selected');
        }
    }
});
