document.addEventListener('DOMContentLoaded', function() {

    // Сначала объявляем salonDataElement, а затем salonId
    const salonDataElement = document.getElementById('salon-data');
    if (!salonDataElement) {
        console.error('Element with id "salon-data" not found.');
        return;
    }
    const salonId = parseInt(salonDataElement.dataset.salonId, 10);

    const serviceDurationElement = document.getElementById('service-duration');
    const salonDefaultDuration = parseInt(serviceDurationElement.dataset.duration, 10) || 0; // В минутах
    
    let totalServiceDuration = salonDefaultDuration;

    const daySelect = document.getElementById('day-select');
    const hourSelect = document.getElementById('hour-select');
    const minuteSelect = document.getElementById('minute-select');
    const summaryText = document.getElementById('summary-text');
    
    const selectedDateInput = document.getElementById('selected-date'); // Скрытое поле для даты
    const selectedTimeInput = document.getElementById('selected-time'); // Скрытое поле для времени
    
    const reservDays = parseInt(salonDataElement.dataset.reservDays, 10) || 30; // Например, 30 дней вперед
    
    // Кэш для доступных минут
    const availableMinutesCache = {}; // Ключ: `${date}_${hour}`, Значение: массив минут

    // Сбор данных о барберах
    const barbersData = {};
    const barberCards = document.querySelectorAll('.barber-card');
    
    const servicesBarbersContainer = document.querySelector('.selected-services-barbers');

    function getCategoryNameById(categoryId) {
        const categoriesCards = Array.from(document.querySelectorAll('.category-button'));
        const card = categoriesCards.find(card => 
            parseInt(card.getAttribute('data-category-id'), 10) === categoryId
        );
      
        return card ? card.textContent.trim() : 'Неизвестная категория';
    }

    function getServiceNameById(serviceId) {
        const serviceCards = Array.from(document.querySelectorAll('.service-card'));
        const card = serviceCards.find(card => 
            parseInt(card.getAttribute('data-service-id'), 10) === serviceId
        );
        
        const serviceNameElement = card ? card.querySelector('.service-name') : null;
        return serviceNameElement ? serviceNameElement.textContent.trim() : 'Неизвестная услуга';
    }

    function getBarberNameById(barberId) {
        const barberCards = Array.from(document.querySelectorAll('.barber-card'));

        const card = barberCards.find(card => 
            parseInt(card.getAttribute('data-barber-id'), 10) === barberId
        );
        
        try{
            const cardName = card.querySelector('.barber-name');
            return cardName ? cardName.textContent.trim() : 'Любой мастер';
        }
        catch{
            return 'Любой мастер';
        }
    }
    

    barberCards.forEach(card => {
        const barberId = card.dataset.barberId;
        // Пропускаем опцию "Любой мастер"
        if (barberId === 'any') return;

        const barberNameElement = card.querySelector('.barber-name');
        const barberDescriptionElement = card.querySelector('.barber-description');

        const barberName = barberNameElement ? barberNameElement.innerText.trim() : 'Без имени';
        const description = barberDescriptionElement ? barberDescriptionElement.innerText.trim() : '';

        barbersData[barberId] = {
            name: barberName,
            description: description
        };
    });

    // Инициализация выбранных услуг и мастеров
    let selectedServices = [];
    let selectedServicesByCategory = {};
    let selectedBarbersByCategory = {};

    // Объявление bookingMessage до использования в функциях
    const bookingMessage = document.getElementById('booking-message');
    if (!bookingMessage) {
        console.error('Element with id "booking-message" not found.');
        return;
    }

    // Функция для добавления услуги
    function addService(serviceId) {
        if (!selectedServices.includes(serviceId)) {
            selectedServices.push(serviceId);
            updateSelectedServices();

            // Обновляем selectedServicesByCategory
            const categoryId = getCategoryIdByServiceId(serviceId);
            if (categoryId) {
                if (!selectedServicesByCategory[categoryId]) {
                    selectedServicesByCategory[categoryId] = [];
                }
                selectedServicesByCategory[categoryId].push(serviceId);
            }

            // Обновляем UI
            markServiceAsSelected(serviceId, true);
        }
    }

    // Функция для удаления услуги
    function removeService(serviceId) {
        selectedServices = selectedServices.filter(id => id !== serviceId);
        updateSelectedServices();

        // Обновляем selectedServicesByCategory
        const categoryId = getCategoryIdByServiceId(serviceId);
        if (categoryId && selectedServicesByCategory[categoryId]) {
            selectedServicesByCategory[categoryId] = selectedServicesByCategory[categoryId].filter(id => id !== serviceId);
            if (selectedServicesByCategory[categoryId].length === 0) {
                delete selectedServicesByCategory[categoryId];
            }
        }

        // Обновляем UI
        markServiceAsSelected(serviceId, false);
    }

    // Обновление скрытых полей выбранных услуг
    function updateSelectedServices() {
        const selectedServicesContainer = document.querySelector('.selected-services');
        if (!selectedServicesContainer) {
            console.error('Element with class "selected-services" not found.');
            return;
        }
        selectedServicesContainer.innerHTML = ''; // Очищаем текущие услуги

        selectedServices.forEach(serviceId => {
            const input = document.createElement('input');
            input.type = 'hidden';
            input.name = 'services';
            input.value = serviceId;
            selectedServicesContainer.appendChild(input);
        });
    }

    // Пометка услуги как выбранной или невыбранной
    function markServiceAsSelected(serviceId, isSelected) {
        const serviceCard = document.querySelector(`.service-card[data-service-id="${serviceId}"]`);
        if (serviceCard) {
            if (isSelected) {
                serviceCard.classList.add('selected');
            } else {
                serviceCard.classList.remove('selected');
            }
        }
    }

    // Получение categoryId по serviceId
    function getCategoryIdByServiceId(serviceId) {
        const serviceCard = document.querySelector(`.service-card[data-service-id="${serviceId}"]`);
        if (serviceCard) {
            return parseInt(serviceCard.dataset.categoryId, 10);
        }
        return null;
    }

    // Обработка кликов на карточках услуг через делегирование событий
    const servicesContainer = document.querySelector('.services-container');

    if (servicesContainer) {
        servicesContainer.addEventListener('click', function(e) {
            let card = e.target.closest('.service-card');
            if (card) {
                const serviceId = parseInt(card.dataset.serviceId, 10);
                if (selectedServices.includes(serviceId)) {
                    removeService(serviceId);
                } else {
                    addService(serviceId);
                }

                // После изменения услуг, отправляем событие 'servicesUpdated'
                const totalPrice = calculateTotalPrice();
                const totalDuration = calculateTotalDuration();
                const event = new CustomEvent('servicesUpdated', { detail: { totalPrice, totalDuration } });
                document.dispatchEvent(event);
            }
        });
    }

    // Обработка события обновления услуг
    document.addEventListener('servicesUpdated', function(e) {
        const { totalPrice, totalDuration } = e.detail;
        if (selectedServices.length > 0) {
            totalServiceDuration = totalDuration + 5; // Добавление 5 минут один раз
        } else {
            totalServiceDuration = salonDefaultDuration;
        }

        // Обновляем доступные минуты для выбранного часа, не сбрасывая выбор
        const selectedDay = daySelect.querySelector('.selected');
        const selectedHour = hourSelect.querySelector('.selected');
        if (selectedDay && selectedHour) {
            const date = selectedDay.dataset.date;
            const hour = parseInt(selectedHour.innerText.split(':')[0], 10);
            // Здесь мы уже получили доступные минуты через батч-запрос, поэтому дополнительный запрос не нужен
            // Убедитесь, что функция `populateAvailableMinutes` правильно обрабатывает данные
        }

        // Обновляем итоговую информацию
        const totalPriceElem = document.getElementById('total-price');
        const totalDurationElem = document.getElementById('total-duration');
        if (totalPriceElem) totalPriceElem.innerText = Math.round(totalPrice);
        if (totalDurationElem) totalDurationElem.innerText = Math.round(totalDuration);

        // Обновляем состояние кнопки
        updateBookingButtonState();
    });

    // Заполнение дней на reservDays дней вперед
    const today = new Date();

    for (let i = 0; i < reservDays; i++) {
        const dayOption = document.createElement('div');
        const date = new Date(today);
        date.setDate(today.getDate() + i);

        dayOption.dataset.date = date.toISOString().split('T')[0];
        dayOption.innerText = date.toLocaleDateString('ru-RU', { day: 'numeric', month: 'numeric', weekday: 'short' });
        dayOption.classList.add('day-option'); // Добавьте класс для стилизации
        dayOption.onclick = () => handleDayClick(dayOption);

        daySelect.appendChild(dayOption);
    }

    function handleDayClick(dayOption) {
        clearSelection(daySelect);
        dayOption.classList.add('selected');
        populateHours(dayOption.dataset.date);
        clearSelection(minuteSelect);
        summaryText.innerText = 'Час и минута не выбраны';

        // Обновляем скрытое поле даты
        if (selectedDateInput) selectedDateInput.value = dayOption.dataset.date;

        // Вызов функции обновления состояния кнопки
        updateBookingButtonState();
    }

    async function populateHours(dateString) {
        hourSelect.innerHTML = '';
        minuteSelect.innerHTML = '';
        summaryText.innerText = 'Час и минута не выбраны';
    
        const startHour = 8;
        const endHour = 22;
        const chosenDateObj = new Date(dateString);
        const chosenDate = chosenDateObj.toISOString().split('T')[0];
        const now = new Date();
        const isToday = chosenDateObj.toDateString() === now.toDateString();
    
        const hours = [];
        for (let hour = startHour; hour < endHour; hour++) {
            if (isToday && hour < now.getHours()) {
                continue; // Пропускаем уже прошедшие часы
            }
            hours.push(hour);
        }
    
        if (hours.length === 0) {
            hourSelect.innerHTML = '<div>Нет доступного времени</div>';
            return;
        }
    
        // Отправляем один запрос для всех часов
        const availableMinutesData = await getAvailableMinutesBatch(salonId, chosenDate, hours);
    
        let anyAvailable = false;
        hours.forEach(hour => {
            const availableMinutes = availableMinutesData[hour];
            if (availableMinutes && availableMinutes.length > 0) {
                const hourOption = document.createElement('div');
                hourOption.innerText = `${hour}:00`;
                hourOption.classList.add('hour-option');
                hourOption.onclick = () => handleHourClick(hourOption, chosenDate, hour, availableMinutes);
                hourSelect.appendChild(hourOption);
                anyAvailable = true;
            }
        });
    
        if (!anyAvailable) {
            hourSelect.innerHTML = '<div>Нет доступного времени</div>';
        }
    }
    
    async function getAvailableMinutesBatch(salonId, date, hours) {
        const uncachedHours = [];
        const result = {};
    
        hours.forEach(hour => {
            const key = `${date}_${hour}`;
            if (availableMinutesCache[key]) {
                result[hour] = availableMinutesCache[key];
            } else {
                uncachedHours.push(hour);
            }
        });
    
        if (uncachedHours.length > 0) {
            try {
                const response = await fetch('/salons/get_available_minutes/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCookie('csrftoken')
                    },
                    body: JSON.stringify({
                        salon_id: salonId,
                        date: date,
                        hours: uncachedHours,
                        booking_details: collectBookingFormData().booking_details,
                        total_service_duration: collectBookingFormData().total_service_duration
                    })
                });
    
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
    
                const data = await response.json();
                const fetchedMinutes = data.available_minutes || {};
    
                // Сохраняем в кэш
                Object.keys(fetchedMinutes).forEach(hour => {
                    const key = `${date}_${hour}`;
                    availableMinutesCache[key] = fetchedMinutes[hour];
                    result[hour] = fetchedMinutes[hour];
                });
            } catch (error) {
                console.error('Ошибка при получении доступных минут:', error);
                // В случае ошибки добавляем пустые массивы для затронутых часов
                uncachedHours.forEach(hour => {
                    result[hour] = [];
                });
            }
        }
    
        return result;
    }
    
    // Удаление функции getAvailableMinutesFromBackend, так как мы используем батч-запросы
    // Если она всё ещё нужна, убедитесь, что она правильно обрабатывает запросы
    
    function handleHourClick(hourOption, date, hour, availableMinutes) {
        clearSelection(hourSelect);
        hourOption.classList.add('selected');
        summaryText.innerText = `Дата: ${date}, Время: ${hour}:00`;

        // Очищаем 'selectedTimeInput' при выборе часа
        if (selectedTimeInput) {
            selectedTimeInput.value = ''; // Оставляем пустым до выбора минуты
        }

        // Вызов функции обновления состояния кнопки
        updateBookingButtonState();

        // Показываем доступные минуты без дополнительного запроса
        populateAvailableMinutes(availableMinutes, date, hour);
    }

    function getCategoryDefaultDuration(categoryId) {
        const categoryElement = document.querySelector(`.category[data-category-id="${categoryId}"]`);
        if (categoryElement) {
            return parseInt(categoryElement.dataset.defaultDuration, 10) || salonDefaultDuration;
        }
        return salonDefaultDuration;
    }

    function populateAvailableMinutes(availableMinutes, date, hour) {
        minuteSelect.innerHTML = '';
        summaryText.innerText = 'Дата и час выбраны, выберите минуту';

        if (availableMinutes.length === 0) {
            minuteSelect.innerHTML = '<div>Нет доступных минут</div>';
            hideHourOption(hour);
            return;
        }

        availableMinutes.forEach(minute => {
            // Проверяем, что minute является числом
            if (typeof minute !== 'number' || isNaN(minute) || minute < 0 || minute > 59) {
                console.error(`Invalid minute value received: ${minute}`);
                return;
            }

            // Форматируем час и минуту с ведущим нулём
            const formattedHour = hour.toString().padStart(2, '0');
            const formattedMinute = minute.toString().padStart(2, '0');

            const minuteOption = document.createElement('div');
            minuteOption.innerText = `${formattedHour}:${formattedMinute}`;
            minuteOption.classList.add('minute-option'); // Добавьте класс для стилизации
            minuteOption.onclick = () => handleMinuteClick(minuteOption, minute);
            minuteSelect.appendChild(minuteOption);
        });
    }

    function handleMinuteClick(minuteOption, minute) {
        clearSelection(minuteSelect);
        minuteOption.classList.add('selected');
        const selectedDay = daySelect.querySelector('.selected');
        const selectedHour = hourSelect.querySelector('.selected');
        if (selectedDay && selectedHour) {
            const date = selectedDay.dataset.date;
            const hour = parseInt(selectedHour.innerText.split(':')[0], 10);

            const formattedHour = hour.toString().padStart(2, '0');
            const formattedMinute = minute.toString().padStart(2, '0');

            summaryText.innerText = `Дата: ${date}, Время: ${formattedHour}:${formattedMinute}`;

            if (selectedDateInput) selectedDateInput.value = date;
            if (selectedTimeInput) selectedTimeInput.value = `${formattedHour}:${formattedMinute}`;
        }

        // Вызов функции обновления состояния кнопки
        updateBookingButtonState();
    }

    function hideHourOption(hour) {
        const hourOptions = hourSelect.querySelectorAll('.hour-option');
        hourOptions.forEach(option => {
            if (parseInt(option.innerText.split(':')[0], 10) === hour) {
                option.style.display = 'none';
            }
        });
    }

    function clearSelection(container) {
        const selected = container.querySelector('.selected');
        if (selected) selected.classList.remove('selected');
    }

    // Обработка выбора барбера через событие из barber.js
    document.addEventListener('barberSelected', function(e) {
        const { categoryId, barberId } = e.detail;
        selectedBarbersByCategory[categoryId] = barberId;
        updateBookingForm();

        // После изменения барбера, возможно, нужно обновить доступные минуты
        const selectedDay = daySelect.querySelector('.selected');
        const selectedHour = hourSelect.querySelector('.selected');
        if (selectedDay && selectedHour) {
            const date = selectedDay.dataset.date;
            const hour = parseInt(selectedHour.innerText.split(':')[0], 10);
            const availableMinutes = availableMinutesCache[`${date}_${hour}`];
            if (availableMinutes) {
                populateAvailableMinutes(availableMinutes, date, hour);
            }
        }
    });

    // Обработка клика на кнопку бронирования через событие submit формы
    const bookingForm = document.getElementById('booking-form');

    if (!bookingForm) {
        console.error('Element with id "booking-form" not found.');
        return;
    }

    const bookingButton = bookingForm.querySelector('.booking-button');
    if (!bookingButton) {
        console.error('Element with class "booking-button" not found within the booking form.');
        return;
    }

    // Обработчик клика на кнопку бронирования
    bookingButton.addEventListener('click', function(event) {
        // Проверяем, заполнены ли необходимые поля
        if (!canSubmitForm()) {

            event.preventDefault();
            // Сохраняем данные формы в localStorage
            saveBookingFormData();

            alert('Пожалуйста, выберите дату и время для бронирования.');
        } else {
            event.preventDefault(); // Предотвращаем стандартную отправку формы
            // Получаем информацию об авторизации пользователя
            const isAuthenticated = bookingButton.dataset.isAuthenticated === 'true';
            if (!isAuthenticated) {
                // Сохраняем данные формы в localStorage
                saveBookingFormData();
                // Открываем модальное окно логина и передаём действие
                openAuthModal('login_from_booking', salonId);
            } else {
                // Пользователь авторизован, отправляем форму через AJAX
                submitBookingForm();
            }
        }
    });

    function collectBookingFormData() {
        const formData = {
            salon_id: salonId,
            date: selectedDateInput.value,
            time: selectedTimeInput.value,
            booking_details: [],
            total_service_duration: 0
        };
    
        const categories = new Set([...Object.keys(selectedServicesByCategory), ...Object.keys(selectedBarbersByCategory)]);
    
        categories.forEach(categoryId => {
            const barberId = selectedBarbersByCategory[categoryId] || 'any';
            const services = selectedServicesByCategory[categoryId] || [];
            let duration = 0;
    
            if (services.length > 0) {
                duration = services.reduce((total, serviceId) => total + getServiceDuration(serviceId), 0);
            }
    
            // Если услуги не выбраны, но выбран барбер, используем default_duration категории
            if (duration === 0 && barberId !== 'any') {
                duration = getCategoryDefaultDuration(categoryId);
            }
    
            // Добавляем категорию в booking_details, если выбраны услуги или выбран барбер
            if (services.length > 0 || barberId !== 'any') {
                formData.booking_details.push({
                    categoryId: categoryId,
                    services: services.map(serviceId => ({
                        serviceId: serviceId,
                        duration: getServiceDuration(serviceId)
                    })),
                    barberId: barberId,
                    duration: duration
                });
    
                formData.total_service_duration += duration;
            }
        });
    
        // Если booking_details пустой, используем default_duration салона
        if (formData.booking_details.length === 0) {
            formData.total_service_duration = salonDefaultDuration;
        }
    
        return formData;
    }


    function submitBookingForm() {

        const formData = collectBookingFormData();
        showBookingConfirmationModal(formData);
    }

    // Функция для сохранения данных формы бронирования
    function saveBookingFormData() {
        const formData = collectBookingFormData();
        localStorage.setItem('bookingFormData', JSON.stringify(formData));
    }

    // Функция проверки возможности отправки формы
    function canSubmitForm() {
        const date = selectedDateInput.value;
        const time = selectedTimeInput.value;
        // Мы разрешаем бронирование без выбранных услуг, поэтому проверяем только дату и время
        return date !== '' && time !== '';
    }

    // Обновлённая функция updateBookingButtonState
    function updateBookingButtonState() {
        if (canSubmitForm()) {
            bookingButton.disabled = false;
            bookingButton.classList.remove('disabled');
            bookingMessage.style.display = 'none';
        } else {
            bookingButton.disabled = true;
            bookingButton.classList.add('disabled');
    
            let message = 'Пожалуйста, выберите дату и время.';
            bookingMessage.innerText = message;
            bookingMessage.classList.remove('info');
            bookingMessage.classList.add('error');
            bookingMessage.style.display = 'block';
        }
    }
    
    // Инициализация состояния кнопки бронирования
    updateBookingButtonState();

    // Функции для расчета общей цены и длительности
    function calculateTotalPrice() {
        let total = 0;
        selectedServices.forEach(serviceId => {
            const serviceCard = document.querySelector(`.service-card[data-service-id="${serviceId}"]`);
            if (serviceCard) {
                const price = parseFloat(serviceCard.dataset.price) || 0;
                total += price;
            }
        });
        return total;
    }

    function getServiceDuration(serviceId) {
        const serviceCard = document.querySelector(`.service-card[data-service-id="${serviceId}"]`);
        if (serviceCard) {
            return parseInt(serviceCard.dataset.duration, 10) || 0;
        }
        return 0;
    }

    function calculateTotalDuration() {
        let total = 0;
    
        // Учесть услуги
        selectedServices.forEach(serviceId => {
            total += getServiceDuration(serviceId);
        });
    
        // Учесть категории без услуг, но с выбранным барбером
        Object.keys(selectedBarbersByCategory).forEach(categoryId => {
            if (!selectedServicesByCategory[categoryId] || selectedServicesByCategory[categoryId].length === 0) {
                total += getCategoryDefaultDuration(categoryId);
            }
        });
    
        return total;
    }
    
    // Обновление формы бронирования
    function updateBookingForm() {
        servicesBarbersContainer.innerHTML = ''; // Очищаем контейнер

        for (const [categoryId, services] of Object.entries(selectedServicesByCategory)) {
            const barberId = selectedBarbersByCategory[categoryId] || 'any';

            // Добавляем скрытое поле для выбранного барбера в категории
            const barberInput = document.createElement('input');
            barberInput.type = 'hidden';
            barberInput.name = `barber_for_category_${categoryId}`;
            barberInput.value = barberId;
            servicesBarbersContainer.appendChild(barberInput);

            services.forEach(serviceId => {
                // Добавляем скрытое поле для услуги
                const serviceInput = document.createElement('input');
                serviceInput.type = 'hidden';
                serviceInput.name = 'services';
                serviceInput.value = serviceId;
                servicesBarbersContainer.appendChild(serviceInput);
            });
        }
    }

    function openAuthModal(action, salonId="") {
        var modal = document.getElementById('auth-modal');
        var modalBody = document.getElementById('modal-body');
    
        let bodyData = { 'action': action };
    
        if (action === 'login_from_booking') {
            bodyData.salon_id = salonId;
        }
    
        fetch(`/auth/load_modal/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify(bodyData)
        })
        .then(response => response.json())
        .then(data => {
            if (data.html) {
                modalBody.innerHTML = data.html;
                modal.classList.add('show');
                modal.style.display = 'block';
                // Переназначаем обработчики событий
                if (typeof attachModalEventListeners === 'function') {
                    attachModalEventListeners();
                }
                // Инициализируем автофокусировку для полей ввода кода
                if (typeof initializeCodeInputFocus === 'function') {
                    initializeCodeInputFocus();
                }
                // Устанавливаем фокус на первый интерактивный элемент
                var firstInput = modal.querySelector('input, button, select, textarea, a[href]');
                if (firstInput) {
                    firstInput.focus();
                }
            } else if (data.error) {
                console.error('Error loading modal content:', data.error);
            }
        })
        .catch(error => console.error('Error fetching modal content:', error));
    }

    document.addEventListener('loginFromBookingSuccess', function() {
        // Получаем данные из localStorage
        const formDataString = localStorage.getItem('bookingFormData');
        if (formDataString) {
            const formData = JSON.parse(formDataString);
            showBookingConfirmationModal(formData);
        } else {
            console.error('No booking data found in localStorage.');
        }
    });

    // Сбор данных о категориях
    const categoriesData = {};
    const categoryButtons = document.querySelectorAll('.category-button');

    categoryButtons.forEach(button => {
        const categoryId = parseInt(button.dataset.categoryId, 10);
        const categoryName = button.innerText.trim();

        categoriesData[categoryId] = {
            name: categoryName,
            defaultDuration: getCategoryDefaultDuration(categoryId)
        };
    });

    // Сбор данных об услугах
    const servicesData = {};
    const serviceCards = document.querySelectorAll('.service-card');

    serviceCards.forEach(card => {
        const serviceId = parseInt(card.dataset.serviceId, 10);
        const serviceNameElement = card.querySelector('.service-name');
        const serviceName = serviceNameElement ? serviceNameElement.innerText.trim() : 'Без названия';
        const duration = parseInt(card.dataset.duration, 10) || 0;
        const price = parseFloat(card.dataset.price.replace(',', '.')) || 0;
        const categoryId = parseInt(card.dataset.categoryId, 10);

        servicesData[serviceId] = {
            name: serviceName,
            duration: duration,
            price: price,
            categoryId: categoryId
        };
    });

    function showBookingConfirmationModal(formData) {
        const modal = document.getElementById('booking-confirmation-modal');

        const closeButton = modal.querySelector('.close-button');
        const confirmButton = modal.querySelector('.confirm-button');
        const cancelButton = modal.querySelector('.cancel-button');

        // Функция для вычисления endTime
        function calculateEndTime(formData) {
            let [hours, minutes] = formData.time.split(":").map(Number);
            minutes += formData.total_service_duration;

            hours += Math.floor(minutes / 60);
            minutes = minutes % 60;

            let formattedHours = String(hours).padStart(2, "0");
            let formattedMinutes = String(minutes).padStart(2, "0");

            return `${formattedHours}:${formattedMinutes}`;
        }

        formData.endTime = calculateEndTime(formData);
    
        // Генерируем детали бронирования
        generateBookingDetailsHTML(formData)

    
        // Показать модальное окно
        modal.classList.add('show');

        // Обработчики событий для кнопок
        if (closeButton) {
            closeButton.onclick = () => {
                hideBookingConfirmationModal();
            };
        }

        if (confirmButton) {
            confirmButton.onclick = () => {
                submitBookingData(formData);
            };
        }

        if (cancelButton) {
            cancelButton.onclick = () => {
                hideBookingConfirmationModal();
            };
        };

        // Обработчик закрытия по клику вне модального окна
        window.onclick = (event) => {
            if (event.target === modal) {
                hideBookingConfirmationModal();
            }
        };
    }
    
     // Функция для генерации HTML деталей бронирования
     function generateBookingDetailsHTML(data) {
        const modal = document.getElementById('booking-confirmation-modal');
        const bookingDetailsContainer = modal.querySelector('.booking-details');

        const bookingDateTime = modal.querySelector('.booking-date-time')
        bookingDateTime.innerHTML = `<p class="booking-date-time"><strong>Дата:</strong> ${data.date} <br> <strong>Время:</strong> ${data.time} - ${data.endTime} </p>`;
        
        // Очищаем контейнер
        bookingDetailsContainer.innerHTML = '';

        if (data.booking_details && data.booking_details.length > 0) {
            data.booking_details.forEach((detail) => {
                const categoryName = getCategoryNameById(detail.categoryId);
                const barberName = detail.barberId !== 'any' ? getBarberNameById(detail.barberId) : 'Любой мастер';

                // Создаем HTML для списка услуг
                let servicesHTML = '';
                if (detail.services && detail.services.length > 0) {
                    servicesHTML += '<p><strong>Услуги</strong></p>';
                    servicesHTML += '<div class="services-badges">';
                    detail.services.forEach((service) => {
                        const serviceName = getServiceNameById(service.serviceId);
                        servicesHTML += `<span class="service-badge">${serviceName}</span>`;
                    });
                    servicesHTML += '</div>';
                } else {
                    servicesHTML += '<p><em>Услуги не выбраны</em></p>';
                }

                // Добавляем секцию категории в контейнер
                bookingDetailsContainer.innerHTML += 
                    `<div class="category-section">
                        <h4>${categoryName}</h4>
                        <p><strong>Мастер:</strong> ${barberName}</p>
                        ${servicesHTML}
                    </div>`
                ;
            });
        } else {
            bookingDetailsContainer.innerHTML = '<p><strong>Услуги и мастера не выбраны.</strong></p>';
        }
    }

    function submitBookingData(formData) {
        const salonIdForBooking = parseInt(salonDataElement.dataset.salonId, 10);
        console.log(formData)
        fetch(`/salons/${salonIdForBooking}/book/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify(formData)
        })
        .then(response => {
            if (!response.ok) {
                const modal = document.getElementById('booking-confirmation-modal');
                showBookingSErrorMessage(modal)
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            const modal = document.getElementById('booking-confirmation-modal');
            if (data.success) {
                // Booking was successful
                showBookingSuccessMessage(modal);
                // **Clear booking data from localStorage**
                localStorage.removeItem('bookingFormData');
            } else if (data.error) {
                showBookingSErrorMessage(modal)
                alert(`Ошибка при бронировании: ${data.error}`);
            }
        })
        .catch(error => {
            const modal = document.getElementById('booking-confirmation-modal');
            showBookingSErrorMessage(modal)
            console.error('Ошибка при бронировании:', error);
        });
    }
    
    function showBookingSuccessMessage(modal) {
        const modalBody = modal.querySelector('.modal-body.booking-modal-body');

        // Очищаем содержимое модального окна
        modalBody.innerHTML = 
            `<h2 id="modal-title">Бронирование подтверждено</h2>
            <p class="booking-success-message">Ваше бронирование успешно подтверждено!</p>
            <div class="close-confirmation-container">
                <button class="close-confirmation-button">Закрыть</button>
            </div>`
        ;

        // Скрываем футер кнопок
        const modalFooter = modal.querySelector('.modal-footer.booking-modal-footer');
        if (modalFooter) {
            modalFooter.style.display = 'none';
        }

        // Добавляем обработчик события для новой кнопки "Закрыть"
        const closeConfirmationButton = modalBody.querySelector('.close-confirmation-button');
        if (closeConfirmationButton) {
            closeConfirmationButton.onclick = () => {
                hideBookingConfirmationModal();
            };
        }
    }

    function showBookingSErrorMessage(modal) {
        const modalBody = modal.querySelector('.modal-body.booking-modal-body');

        modalBody.innerHTML = 
            `<h2 style="color: red" id="modal-title">Бронирование НЕ подтвердилось!</h2>
            <p class="booking-success-message"> Вероятнее всего в это время забронировать не получится, пожалуйста, попробуйте в другое время или смените мастера </p>

            <div class="close-confirmation-container">
                <button class="close-confirmation-button">Закрыть</button>
            </div>`
        ;

        // Скрываем футер кнопок
        const modalFooter = modal.querySelector('.modal-footer.booking-modal-footer');
        if (modalFooter) {
            modalFooter.style.display = 'none';
        }

        // Добавляем обработчик события для новой кнопки "Закрыть"
        const closeConfirmationButton = modalBody.querySelector('.close-confirmation-button');
        if (closeConfirmationButton) {
            closeConfirmationButton.onclick = () => {
                hideBookingConfirmationModal();
            };
        }
    }


    // Функция для получения CSRF токена из куки
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                // Проверяем, начинается ли кука с имени
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    function hideBookingConfirmationModal() {
        const modal = document.getElementById('booking-confirmation-modal');
        modal.classList.remove('show');
    }
    
});
