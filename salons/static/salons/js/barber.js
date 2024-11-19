document.addEventListener('DOMContentLoaded', function() {
    let selectedBarbers = {}; // Ключ: categoryId, Значение: barberId

    // Получение данных барберов из JSON
    const barbersByCategoryElement = document.getElementById('barbers-by-category');
    let barbersByCategory = {};
    if (barbersByCategoryElement) {
        try {
            barbersByCategory = JSON.parse(barbersByCategoryElement.textContent);
        } catch (error) {
            console.error('Ошибка при парсинге barbersByCategory JSON:', error);
        }
    } else {
        console.error('Element with ID "barbers-by-category" not found.');
    }

    if (typeof barbersByCategory === 'undefined') {
        console.error('barbersByCategory is undefined');
        return;
    }

    const activeBarberCard = document.getElementById('active-barber');
    const barberList = document.getElementById('barber-list');

    // Текущая выбранная категория
    let currentCategoryId = null;

    // Получение текущей выбранной категории
    function getCurrentCategoryId() {
        const selectedCategoryButton = document.querySelector('.category-button.selected');
        if (selectedCategoryButton) {
            return selectedCategoryButton.getAttribute('data-category-id');
        }
        return null;
    }

    // Отображение барберов для текущей категории
    function showBarbersForCurrentCategory() {
        currentCategoryId = getCurrentCategoryId();
        barberList.innerHTML = ''; // Очищаем список барберов
    
        const barbers = barbersByCategory[`category_${currentCategoryId}`];
        if (barbers && barbers.length > 0) {
            // Получаем выбранного барбера для текущей категории
            const selectedBarberId = selectedBarbers[currentCategoryId] || 'any';
    
            // Добавляем опцию "Любой мастер", если она не является выбранной
            if (selectedBarberId !== 'any') {
                const anyBarberCard = createBarberCard('any', 'Любой мастер', '/static/salons/img/default-avatar.png', 'Описание или слоган');
                barberList.appendChild(anyBarberCard);
            }
    
            // Добавляем барберов, исключая выбранного
            barbers.forEach(barber => {
                if (barber.id !== selectedBarberId) {
                    const barberCard = createBarberCard(
                        barber.id,
                        barber.name,
                        barber.avatar || '/static/salons/img/default-avatar.png',
                        barber.description || ''
                    );
                    barberList.appendChild(barberCard);
                }
            });
    
            // Добавляем обработчики событий на новые карточки барберов
            addBarberCardEventListeners();
    
        } else {
            barberList.innerHTML = '<p>Нет доступных мастеров для выбранной категории.</p>';
        }
    }

    // Функция для создания карточки барбера
    function createBarberCard(id, name, avatar, description) {
        const card = document.createElement('div');
        card.classList.add('barber-card');
        card.setAttribute('data-barber-id', id);
    
        const img = document.createElement('img');
        img.src = avatar;
        img.alt = name;
        img.classList.add('barber-avatar');
        card.appendChild(img);
    
        const infoDiv = document.createElement('div');
        infoDiv.classList.add('barber-info');
    
        const nameElement = document.createElement('h4');
        nameElement.classList.add('barber-name');
        nameElement.textContent = name;
        infoDiv.appendChild(nameElement);
    
        const descElement = document.createElement('p');
        descElement.classList.add('barber-description');
        descElement.textContent = description;
        infoDiv.appendChild(descElement);
    
        card.appendChild(infoDiv);
    
        return card;
    }
    

    // Функция для добавления обработчиков событий на карточки барберов
    function addBarberCardEventListeners() {
        const barberCards = barberList.querySelectorAll('.barber-card');
        barberCards.forEach(card => {
            card.addEventListener('click', function() {
                const barberId = this.getAttribute('data-barber-id');
                selectBarberForCurrentCategory(barberId);
            });
        });
    }

    // Функция для выбора барбера для текущей категории
    function selectBarberForCurrentCategory(barberId) {
        currentCategoryId = getCurrentCategoryId();
        selectedBarbers[currentCategoryId] = barberId;
        updateBarberSelectionUI(barberId);

        // Отправляем событие, чтобы booking.js мог его обработать
        const event = new CustomEvent('barberSelected', { detail: { categoryId: currentCategoryId, barberId } });
        document.dispatchEvent(event);

        // Закрываем список барберов после выбора
        barberList.classList.remove('open');
    }

    // Функция для обновления UI после выбора барбера
    function updateBarberSelectionUI(barberId) {
        // Убираем выделение со всех карточек барберов
        barberList.querySelectorAll('.barber-card').forEach(card => {
            card.classList.remove('selected');
        });

        // Выделяем выбранного барбера
        const selectedCard = barberList.querySelector(`.barber-card[data-barber-id="${barberId}"]`);
        if (selectedCard) {
            selectedCard.classList.add('selected');
        }

        // Обновляем активную карточку барбера
        const barbers = barbersByCategory[`category_${currentCategoryId}`];
        let barber = null;
        if (barberId !== 'any') {
            barber = barbers.find(b => b.id == barberId);
        }

        if (barber) {
            activeBarberCard.querySelector('.barber-avatar').src = barber.avatar || '/static/salons/img/default-avatar.png';
            activeBarberCard.querySelector('.barber-name').textContent = barber.name;
            activeBarberCard.querySelector('.barber-description').textContent = barber.description || '';
        } else {
            // Если выбран "Любой мастер"
            activeBarberCard.querySelector('.barber-avatar').src = '/static/salons/img/default-avatar.png';
            activeBarberCard.querySelector('.barber-name').textContent = 'Любой мастер';
            activeBarberCard.querySelector('.barber-description').textContent = 'Описание или слоган';
        }
    }

    // Обработчик для открытия списка барберов при клике на активного барбера
    activeBarberCard.addEventListener('click', function() {
        // Отображаем барберов для текущей категории
        showBarbersForCurrentCategory();

        // Переключаем видимость списка барберов
        barberList.classList.toggle('open');
    });

    // Обработчик изменения категории
    const categoryButtons = document.querySelectorAll('.category-button');
    categoryButtons.forEach(button => {
        button.addEventListener('click', function() {
            // Убираем класс 'selected' со всех кнопок категорий
            categoryButtons.forEach(btn => btn.classList.remove('selected'));
            // Добавляем класс 'selected' на выбранную кнопку
            this.classList.add('selected');

            // Обновляем текущую категорию
            currentCategoryId = this.getAttribute('data-category-id');

            // Обновляем активную карточку барбера для новой категории
            const selectedBarberId = selectedBarbers[currentCategoryId] || 'any';
            updateBarberSelectionUI(selectedBarberId);

            // Закрываем список барберов, если он открыт
            barberList.classList.remove('open');
        });
    });

    // Инициализация текущей категории и активной карточки барбера при загрузке страницы
    if (categoryButtons.length > 0) {
        categoryButtons[0].click();
    }
});
