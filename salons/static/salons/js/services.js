// C:\Reservon\Reservon\salons\static\salons\js\services.js
document.addEventListener('DOMContentLoaded', function() {
    const categoryButtons = document.querySelectorAll('.category-button');
    const categorySections = document.querySelectorAll('.category-section');
    const paginationContainer = document.querySelector('.pagination-container');
    const servicesPerPage = 4; // Максимум 4 услуги на страницу
    let currentPage = 1;
    let totalPages = 1;
    let allServices = [];
    let selectedServices = []; // Массив выбранных услуг

    // Элементы для отображения общей цены и продолжительности
    const totalPriceElement = document.getElementById('total-price');
    const totalDurationElement = document.getElementById('total-duration');

    // Функция для сбора всех услуг текущей выбранной категории
    function gatherServices(categoryId) {
        let servicesArray = [];
        if (categoryId === 'all') {
            categorySections.forEach(section => {
                const services = section.querySelectorAll('.service-card');
                services.forEach(service => {
                    servicesArray.push(service);
                });
            });
        } else if (categoryId === 'no-category') {
            const services = document.querySelectorAll('.category-section[data-category-id="no-category"] .service-card');
            services.forEach(service => {
                servicesArray.push(service);
            });
        } else {
            const selectedSection = document.querySelector(`.category-section[data-category-id="${categoryId}"]`);
            if (selectedSection) {
                const services = selectedSection.querySelectorAll('.service-card');
                services.forEach(service => {
                    servicesArray.push(service);
                });
            }
        }
        return servicesArray;
    }

    // Функция для отображения услуг по странице
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
        buttons.forEach(button => {
            button.classList.remove('active');
        });
        const activeButton = paginationContainer.querySelector(`.pagination-button[data-page="${page}"]`);
        if (activeButton) {
            activeButton.classList.add('active');
        }
    }

    // Функция для создания пагинационных кнопок
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

    // Инициализация пагинации для категории "Все услуги"
    function initializePagination(categoryId) {
        allServices = gatherServices(categoryId);
        totalPages = Math.ceil(allServices.length / servicesPerPage);
        currentPage = 1;
        createPaginationButtons(totalPages);
        displayServices(currentPage);
    }

    // Инициализация при загрузке страницы
    initializePagination('all');

    // Обработчики событий для кнопок категорий
    categoryButtons.forEach(button => {
        button.addEventListener('click', function() {
            // Удаляем класс 'selected' со всех кнопок
            categoryButtons.forEach(btn => btn.classList.remove('selected'));
            // Добавляем класс 'selected' на текущую кнопку
            this.classList.add('selected');

            const categoryId = this.getAttribute('data-category-id');

            // Показываем/скрываем секции категорий
            categorySections.forEach(section => {
                if (categoryId === 'all') {
                    section.classList.remove('hidden');
                } else if (categoryId === 'no-category') {
                    if (section.getAttribute('data-category-id') === 'no-category') {
                        section.classList.remove('hidden');
                    } else {
                        section.classList.add('hidden');
                    }
                } else {
                    if (section.getAttribute('data-category-id') === categoryId) {
                        section.classList.remove('hidden');
                    } else {
                        section.classList.add('hidden');
                    }
                }
            });

            // Инициализируем пагинацию для выбранной категории
            initializePagination(categoryId);

            // Сбрасываем выбранные услуги при переключении категории
            resetSelectedServices();
        });
    });

    // Функция для сброса выбранных услуг
    function resetSelectedServices() {
        selectedServices = [];
        // Убираем класс 'selected' со всех услуг
        allServices.forEach(service => {
            service.classList.remove('selected');
        });
        updateTotal();
    }

    // Обработка выбора услуг с помощью делегирования событий
    const servicesContainer = document.querySelector('.services-container');
    servicesContainer.addEventListener('click', function(event) {
        
        let target = event.target;
        const serviceCard = target.closest('.service-card');
        if (serviceCard) {
            const serviceId = serviceCard.getAttribute('data-service-id');
            const price = parseFloat(serviceCard.getAttribute('data-price'));
            const duration = parseInt(serviceCard.getAttribute('data-duration'));

            if (serviceCard.classList.contains('selected')) {
                // Если уже выбран, снимаем выделение
                serviceCard.classList.remove('selected');
                selectedServices = selectedServices.filter(service => service.id !== serviceId);
            } else {
                // Добавляем выделение
                serviceCard.classList.add('selected');
                selectedServices.push({ id: serviceId, price, duration });
            }

            updateTotal();
        }
    });

    // Функция для обновления общей цены и продолжительности
    function updateTotal() {
        let totalPrice = 0;
        let totalDuration = 0;

        selectedServices.forEach(service => {
            totalPrice += service.price;
            totalDuration += service.duration;
        });

        totalPriceElement.innerText = Math.round(totalPrice) + ' драм';
        totalDurationElement.innerText = Math.round(totalDuration / 60) + ' минут';
    }
});
