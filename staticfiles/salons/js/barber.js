// C:\Reservon\Reservon\salons\static\salons\js\barber.js
document.addEventListener('DOMContentLoaded', function() {

    const salonModInput = document.getElementById('salon-mod');
    let salonMod = 'null';
    if (salonModInput) {
        salonMod = salonModInput.value;
    }

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

    const uniqueBarbers = {};

    
    // Проходим по каждой категории
    for (const categoryId in barbersByCategory) {
        if (barbersByCategory.hasOwnProperty(categoryId)) {
            const barbers = barbersByCategory[categoryId];
            barbers.forEach(barber => {
                // Если мастера с таким ID еще нет в uniqueBarbers, добавляем его
                if (!uniqueBarbers[barber.id]) {
                    uniqueBarbers[barber.id] = barber;
                }
            });
        }
    }

    const uniqueBarbersArray = Object.values(uniqueBarbers);
    
    const categoryButtons = document.querySelectorAll('.category-button');
    const servicesContainer = document.querySelector('.services-container');       
    const serviceCards = servicesContainer.querySelectorAll('.service-card');

    if (typeof barbersByCategory === 'undefined') {
        console.error('barbersByCategory is undefined');
        return;
    }

    const activeBarberCard = document.getElementById('active-barber');
    const barberList = document.getElementById('barber-list');

    if(salonMod=='barber') initializeActiveBarber();
    initializeCategory();

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
        let barbers = {}
        barberList.innerHTML = ''; // Очищаем список барберов
        if(salonMod=='category'){
            barbers = barbersByCategory[currentCategoryId];
        }else{
            barbers = uniqueBarbersArray
        }
        if (barbers) {
            // Получаем выбранного барбера для текущей категории
            const selectedBarberId = selectedBarbers[currentCategoryId] || 'any';
            // Добавляем опцию "Любой мастер", если она не является выбранной
            if(salonMod == 'category'){
                if (selectedBarberId !== 'any') {
                    const anyBarberCard = createBarberCard('any', 'Любой мастер', '/static/salons/img/default-avatar.png', 'Описание или слоган');
                    barberList.appendChild(anyBarberCard);
                }
            }
            // Добавляем барберов, исключая выбранного
            barbers.forEach(barber => {

                if (barber.id !== parseInt(selectedBarberId) || salonMod=='barber'){
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
                console.log('clicked')
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

    // Обработчик для открытия списка барберов при клике на активного барбера
    activeBarberCard.addEventListener('click', function() {
        // Отображаем барберов для текущей категории
        showBarbersForCurrentCategory();
        // Переключаем видимость списка барберов
        barberList.classList.toggle('open');
    });

   function hideEmptyCategories(barberId) {
    // Выбираем все кнопки категорий

        categoryButtons.forEach(button => {
            const categoryId = button.getAttribute('data-category-id');

            // Находим все карточки услуг для данной категории и выбранного барбера
            const servicesInCategory = servicesContainer.querySelectorAll(`.service-card[data-barber-id="${barberId}"][data-category-id="${categoryId}"]`);

            // Проверяем, есть ли хотя бы одна услуга для этой категории и барбера
            const hasServices = servicesInCategory.length > 0;

            // Если есть услуги, отображаем кнопку, иначе скрываем
            if (hasServices) {
                button.style.display = ''; // Возвращаем отображение по умолчанию
            } else {
                button.style.display = 'none';
                initializeCategory();
            }
        });
    }

    // Функция для фильтрации услуг на основе выбранного барбера
    function filterServicesByBarber(barberId, categoryId) {

        serviceCards.forEach(card => {
 
            const cardBarberId = card.getAttribute('data-barber-id');
            const cardCategoryId = card.getAttribute('data-category-id');

            if(cardBarberId==barberId && categoryId==cardCategoryId){
                card.style.display = 'block';
            }else{
                card.style.display = 'none';
            }

        });
        hideEmptyCategories(barberId);
    }
    
    // Обработчик для события 'barberSelected'
    if (salonMod == 'barber') {
        document.addEventListener('barberSelected', function(e) {
            const { barberId, categoryId } = e.detail;
            filterServicesByBarber(barberId, categoryId);
        });
    }

    // Обработчик изменения категории
    categoryButtons.forEach(button => {
        button.addEventListener('click', function() {
            // Убираем класс 'selected' со всех кнопок категорий
            categoryButtons.forEach(btn => btn.classList.remove('selected'));
            // Добавляем класс 'selected' на выбранную кнопку
            this.classList.add('selected');

            // Обновляем текущую категорию
            currentCategoryId = this.getAttribute('data-category-id');

            // Обновляем активную карточку барбера для новой категории
            if(salonMod == 'category'){
                const selectedBarberId = selectedBarbers[currentCategoryId] || 'any';
                updateBarberSelectionUI(selectedBarberId);
            }else{
                const selectedBarberElement = document.querySelector('.barber-card.selected');
                const selectedBarberId = selectedBarberElement.getAttribute('data-barber-id');

                filterServicesByBarber(selectedBarberId, currentCategoryId);
            }

            // Закрываем список барберов, если он открыт
            barberList.classList.remove('open');
        });
    });

    // Инициализация текущей категории и активной карточки барбера при загрузке страницы
    function initializeCategory() {
        if (categoryButtons.length > 0) {

            // Найти первую видимую кнопку категории
            const visibleCategoryButton = Array.from(categoryButtons).find(button => {
                return window.getComputedStyle(button).display !== 'none';
            });

            // Если такая кнопка найдена, симулировать клик по ней
            if (visibleCategoryButton) {
                visibleCategoryButton.click();
            } else {
                console.warn('Нет видимых кнопок категорий для инициализации.');
            }
        }
    }

    function initializeActiveBarber() {
        const activeBarberCard = document.getElementById('active-barber');
        const barberId = activeBarberCard.getAttribute('data-barber-id');
    
        if (!barberId) {
            console.error('data-barber-id не указан в элементе #active-barber.');
            return;
        }
    
        // Найдите барбера по ID
        let barber = uniqueBarbersArray.find(b => String(b.id) === String(barberId));
    
        // Если не найден в uniqueBarbersArray, попробуйте найти в barbersByCategory
        if (!barber) {
            for (const categoryId in barbersByCategory) {
                if (barbersByCategory.hasOwnProperty(categoryId)) {
                    barber = barbersByCategory[categoryId].find(b => String(b.id) === String(barberId));
                    if (barber) break;
                }
            }
        }
    
        if (barber) {
            updateActiveBarberUI(barber);
            // Также обновите selectedBarbers, если требуется
            const initialCategoryId = getCurrentCategoryId() || Object.keys(barbersByCategory)[0];
            selectedBarbers[initialCategoryId] = barberId;
    
            // Вызовите updateBarberSelectionUI для добавления класса 'selected' к соответствующей карточке
            updateBarberSelectionUI(barberId);
    
            // Отправьте событие, если salonMod равен 'barber'
            if (salonMod === 'barber') {
                filterServicesByBarber(barberId, initialCategoryId);
            }
        } else {
            console.error(`Барбер с ID ${barberId} не найден.`);
        }
    }
    
    function updateActiveBarberUI(barber) {
        const activeBarberCard = document.getElementById('active-barber');
        activeBarberCard.querySelector('.barber-avatar').src = barber.avatar || '/static/salons/img/default-avatar.png';
        activeBarberCard.querySelector('.barber-name').textContent = barber.name;
        activeBarberCard.querySelector('.barber-description').textContent = barber.description || '';
    }

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
        let barber = null;
        if (barberId !== 'any') {
            barber = uniqueBarbersArray.find(b => String(b.id) === String(barberId));
            if (!barber) {
                // Если не найден в uniqueBarbersArray, ищем в barbersByCategory
                for (const categoryId in barbersByCategory) {
                    if (barbersByCategory.hasOwnProperty(categoryId)) {
                        barber = barbersByCategory[categoryId].find(b => String(b.id) === String(barberId));
                        if (barber) break;
                    }
                }
            }
        }
    
        if (barber) {
            activeBarberCard.querySelector('.barber-avatar').src = barber.avatar || '/static/salons/img/default-avatar.png';
            activeBarberCard.querySelector('.barber-name').textContent = barber.name;
            activeBarberCard.querySelector('.barber-description').textContent = barber.description || '';
        } else {
            activeBarberCard.querySelector('.barber-avatar').src = '/static/salons/img/default-avatar.png';
            activeBarberCard.querySelector('.barber-name').textContent = 'Любой мастер';
            activeBarberCard.querySelector('.barber-description').textContent = 'Описание или слоган';
        }
    }
    
    
});
