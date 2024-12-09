document.addEventListener('DOMContentLoaded', function() {
    const categoryButtons = document.querySelectorAll('.category-button');
    const categorySections = document.querySelectorAll('.category-section');

    let selectedServices = {}; // Ключ: categoryId, Значение: массив выбранных услуг
    let selectedBarbers = {}; // Ключ: categoryId, Значение: выбранный барбер

    // Элементы для отображения общей цены и продолжительности
    const totalPriceElement = document.getElementById('total-price');
    const totalDurationElement = document.getElementById('total-duration');

    // Переменные для пагинации
    const paginationContainer = document.querySelector('.pagination-container');
    const servicesPerPage = 4;
    let currentPage = 1;
    let totalPages = 1;
    let allServices = [];

    // Контейнер для скрытых полей бронирования
    const servicesBarbersContainer = document.querySelector('.selected-services-barbers');

    // Инициализация при загрузке страницы
    initializeCategorySelection();

    // Обработчики событий для кнопок категорий
    function initializeCategorySelection() {
        // Устанавливаем первую категорию как выбранную
        if (categoryButtons.length > 0) {
            categoryButtons[0].classList.add('selected');
            const firstCategoryId = categoryButtons[0].getAttribute('data-category-id');
            showCategory(firstCategoryId);
            initializePagination(firstCategoryId);
        }

        categoryButtons.forEach(button => {
            button.addEventListener('click', function() {
                // Удаляем класс 'selected' со всех кнопок
                categoryButtons.forEach(btn => btn.classList.remove('selected'));
                // Добавляем класс 'selected' на текущую кнопку
                this.classList.add('selected');

                const categoryId = this.getAttribute('data-category-id');
                showCategory(categoryId);
                initializePagination(categoryId);
                // При смене категории сбрасываем выбранного барбера (по желанию)
                // Например:
                // selectedBarbers[categoryId] = 'any';
                // updateBarberSelectionUI('any', categoryId);
            });
        });
    }

    function showCategory(categoryId) {
        // Показываем/скрываем секции категорий
        categorySections.forEach(section => {
            if (section.getAttribute('data-category-id') === categoryId) {
                section.classList.remove('hidden');
            } else {
                section.classList.add('hidden');
            }
        });
    }

    function gatherServices(categoryId) {
        let servicesArray = [];
        const selectedSection = document.querySelector(`.category-section[data-category-id="${categoryId}"]`);
        if (selectedSection) {
            const services = selectedSection.querySelectorAll('.service-card');
            services.forEach(service => {
                servicesArray.push(service);
            });
        }
        return servicesArray;
    }

    function displayServices(page) {
        const start = (page - 1) * servicesPerPage;
        const end = start + servicesPerPage;

        // Скрываем все услуги
        allServices.forEach(service => {
            service.classList.add('hidden');
        });

        // Отображаем услуги текущей страницы
        const servicesToShow = allServices.slice(start, end);
        servicesToShow.forEach(service => {
            service.classList.remove('hidden');
        });

        // Обновляем активный стиль для пагинации
        const buttons = paginationContainer.querySelectorAll('.pagination-button');
        buttons.forEach(button => button.classList.remove('active'));
        const activeButton = paginationContainer.querySelector(`.pagination-button[data-page="${page}"]`);
        if (activeButton) {
            activeButton.classList.add('active');
        }
    }

    function createPaginationButtons(total) {
        paginationContainer.innerHTML = ''; // Очищаем существующие кнопки

        if (total <= 1) {
            paginationContainer.classList.add('hidden'); // Скрываем пагинацию
            return;
        } else {
            paginationContainer.classList.remove('hidden'); // Показываем пагинацию
        }

        for (let i = 1; i <= total; i++) {
            const button = document.createElement('button');
            button.classList.add('pagination-button');
            button.textContent = i;
            button.setAttribute('data-page', i);
            if (i === 1) {
                button.classList.add('active');
            }
            button.addEventListener('click', function() {
                currentPage = parseInt(this.getAttribute('data-page'));
                displayServices(currentPage);
            });
            paginationContainer.appendChild(button);
        }
    }

    function initializePagination(categoryId) {
        allServices = gatherServices(categoryId);
        totalPages = Math.ceil(allServices.length / servicesPerPage);
        currentPage = 1;
        createPaginationButtons(totalPages);
        displayServices(currentPage);
    }

    // Обработка выбора услуг с помощью делегирования событий
    const servicesContainer = document.querySelector('.services-container');
    servicesContainer.addEventListener('click', function(event) {
        let target = event.target;
        const serviceCard = target.closest('.service-card');
        if (serviceCard) {
            const serviceId = serviceCard.getAttribute('data-service-id');
            const categoryId = serviceCard.getAttribute('data-category-id'); // Теперь присутствует
            const price = parseFloat(serviceCard.getAttribute('data-price'));
            const duration = parseInt(serviceCard.getAttribute('data-duration'));

            if (!selectedServices[categoryId]) {
                selectedServices[categoryId] = [];
            }

            const existingServiceIndex = selectedServices[categoryId].findIndex(service => service.id === serviceId);

            if (existingServiceIndex > -1) {
                // Если уже выбран, снимаем выделение
                serviceCard.classList.remove('selected');
                selectedServices[categoryId].splice(existingServiceIndex, 1);
            } else {
                // Добавляем выделение
                serviceCard.classList.add('selected');
                selectedServices[categoryId].push({ id: serviceId, price, duration });
            }

            updateTotal();
            updateBookingForm();
        }
    });

    // Функция для обновления общей цены и продолжительности
    function updateTotal() {
        let totalPrice = 0;
        let totalDuration = 0;

        for (let categoryId in selectedServices) {
            selectedServices[categoryId].forEach(service => {
                totalPrice += service.price;
                totalDuration += service.duration;
            });
        }

        totalPriceElement.innerText = Math.round(totalPrice) + ' драм';
        totalDurationElement.innerText = Math.round(totalDuration) + ' минут';
    }

    // Функция для обновления скрытых полей бронирования
    function updateBookingForm() {
        servicesBarbersContainer.innerHTML = ''; // Очищаем контейнер

        for (let categoryId in selectedServices) {
            const services = selectedServices[categoryId];
            const barberId = selectedBarbers[categoryId] || 'any';

            services.forEach(service => {
                // Добавляем скрытое поле для услуги
                const serviceInput = document.createElement('input');
                serviceInput.type = 'hidden';
                serviceInput.name = 'services';
                serviceInput.value = service.id;
                servicesBarbersContainer.appendChild(serviceInput);

                // Добавляем скрытое поле для барбера, связанного с услугой
                const barberInput = document.createElement('input');
                barberInput.type = 'hidden';
                barberInput.name = `barber_for_service_${service.id}`;
                barberInput.value = barberId;
                servicesBarbersContainer.appendChild(barberInput);
            });
        }
    }
});
