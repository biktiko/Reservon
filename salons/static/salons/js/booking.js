document.addEventListener('DOMContentLoaded', function() {
    const daySelect = document.getElementById('day-select');
    const hourSelect = document.getElementById('hour-select');
    const minuteSelect = document.getElementById('minute-select');
    const summaryText = document.getElementById('summary-text');

    const selectedDateInput = document.getElementById('selected-date'); // Скрытое поле для даты
    const selectedTimeInput = document.getElementById('selected-time'); // Скрытое поле для времени

    const barberSelectionContainer = document.querySelector('.barber-selection');
    const servicesBarbersContainer = document.querySelector('.selected-services-barbers');

    // Инициализация выбранных услуг и мастеров
    let selectedServices = [];
    let selectedServicesByCategory = {};
    let selectedBarbersByCategory = {};

    // Получение данных из Django через data-атрибуты
    const salonDataElement = document.getElementById('salon-data');
    if (!salonDataElement) {
        console.error('Element with ID "salon-data" not found.');
        return;
    }

    const salonId = parseInt(salonDataElement.dataset.salonId);
    const reservDays = parseInt(salonDataElement.dataset.reservDays);
    const hasServices = salonDataElement.dataset.hasServices === 'true';
    const hasBarbers = salonDataElement.dataset.hasBarbers === 'true';

    const workingHoursElement = document.getElementById('opening-hours');
    if (!workingHoursElement) {
        console.error('Element with ID "opening-hours" not found.');
        return;
    }
    let workingHours;
    try {
        workingHours = JSON.parse(workingHoursElement.textContent);
        console.log('Working hours:', workingHours); // Отладочное сообщение
    } catch (error) {
        console.error('Ошибка при парсинге JSON для "opening-hours":', error);
        return;
    }

    const serviceDurationElement = document.getElementById('service-duration');
    if (!serviceDurationElement) {
        console.error('Element with ID "service-duration" not found.');
        return;
    }
    const salonDefaultDuration = parseInt(serviceDurationElement.dataset.duration); // В минутах
    let totalServiceDuration = salonDefaultDuration; // Начальное значение

    // Объявление bookingMessage до использования в функциях
    const bookingMessage = document.getElementById('booking-message');
    if (!bookingMessage) {
        console.error('Element with ID "booking-message" not found.');
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
            return serviceCard.dataset.categoryId;
        }
        return null;
    }

    // Обработка кликов на карточках услуг через делегирование событий
    const servicesContainer = document.querySelector('.services-container');

    if (servicesContainer) {
        servicesContainer.addEventListener('click', function(e) {
            let card = e.target.closest('.service-card');
            if (card) {
                const serviceId = card.dataset.serviceId;
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
    } else {
        console.error('Element with class "services-container" not found.');
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
            const hour = parseInt(selectedHour.innerText.split(':')[0]);
            fetchAvailableMinutes(salonId, date, hour);
        }

        // Обновляем итоговую информацию
        const totalPriceElem = document.getElementById('total-price');
        const totalDurationElem = document.getElementById('total-duration');
        if (totalPriceElem) totalPriceElem.innerText = Math.round(totalPrice) + ' драм';
        if (totalDurationElem) totalDurationElem.innerText = Math.round(totalDuration) + ' минут';

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

    function populateHours(dateString) {
        hourSelect.innerHTML = '';
        minuteSelect.innerHTML = '';
        summaryText.innerText = 'Час и минута не выбраны';

        const day = new Date(dateString).toLocaleDateString('en-US', { weekday: 'long' }).toLowerCase();
        const salonHoursForDay = workingHours[day];
        if (!salonHoursForDay) {
            hourSelect.innerHTML = '<div>Салон закрыт в этот день</div>';
            return;
        }

        const openingTime = salonHoursForDay.open || '09:00';
        const closingTime = salonHoursForDay.close || '18:00';

        const openingHour = parseInt(openingTime.split(':')[0]);
        const closingHour = parseInt(closingTime.split(':')[0]);

        // Генерируем часы в рабочем диапазоне
        for (let hour = openingHour; hour < closingHour; hour++) {
            const hourOption = document.createElement('div');
            hourOption.innerText = `${hour}:00`;
            hourOption.classList.add('hour-option'); // Добавляем класс для стилизации
            hourOption.onclick = () => handleHourClick(hourOption, dateString, hour);
            hourSelect.appendChild(hourOption);
        }
    }

    function handleHourClick(hourOption, date, hour) {
        clearSelection(hourSelect);
        hourOption.classList.add('selected');
        summaryText.innerText = `Дата: ${date}, Время: ${hour}:00`;

        // Очищаем 'selectedTimeInput' при выборе часа
        if (selectedTimeInput) {
            selectedTimeInput.value = ''; // Оставляем пустым до выбора минуты
        }

        // Вызов функции обновления состояния кнопки
        updateBookingButtonState();

        fetchAvailableMinutes(salonId, date, hour);
    }

    function fetchAvailableMinutes(salonId, date, hour) {
        // Показываем индикатор загрузки
        minuteSelect.innerHTML = '<div>Загрузка...</div>';
        summaryText.innerText = 'Загрузка доступных минут...';

        // Собираем данные о выбранных барберах и услугах
        const bookingDetails = [];
        for (const [categoryId, services] of Object.entries(selectedServicesByCategory)) {
            const barberId = selectedBarbersByCategory[categoryId] || 'any'; // Выбранный мастер для категории
            const duration = services.reduce((total, serviceId) => total + getServiceDuration(serviceId), 0);

            bookingDetails.push({
                categoryId: categoryId,
                services: services.map(serviceId => ({
                    serviceId: serviceId,
                    duration: getServiceDuration(serviceId)
                })),
                barberId: barberId,
                duration: duration
            });
        }

        const totalServiceDuration = calculateTotalDuration() || salonDefaultDuration; // Используем длительность по умолчанию, если нет выбранных услуг

        // Логирование отправляемых данных
        console.log('Отправляемые данные:', {
            salon_id: salonId,
            date: date,
            hour: hour,
            booking_details: bookingDetails,
            total_service_duration: totalServiceDuration
        });

        const url = `/salons/get_available_minutes/`;
        fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken') // Убедитесь, что CSRF-токен корректно получен
            },
            body: JSON.stringify({
                salon_id: salonId,
                date: date,
                hour: hour,
                booking_details: bookingDetails,
                total_service_duration: totalServiceDuration
            })
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            if (data.available_minutes) {
                populateAvailableMinutes(data.available_minutes, date, hour);
            } else if (data.error) {
                alert(`Ошибка: ${data.error}`);
                minuteSelect.innerHTML = '<div>Нет доступных минут</div>';
            } else {
                minuteSelect.innerHTML = '<div>Нет доступных минут</div>';
            }
        })
        .catch(error => {
            console.error('Ошибка при получении доступных минут:', error);
            minuteSelect.innerHTML = '<div>Ошибка при загрузке минут</div>';
        });
    }

    function populateAvailableMinutes(availableMinutes, date, hour) {
        console.log('populateAvailableMinutes called with:', availableMinutes, date, hour);
        minuteSelect.innerHTML = '';
        summaryText.innerText = 'Дата и час выбраны, выберите минуту';

        if (availableMinutes.length === 0) {
            minuteSelect.innerHTML = '<div>Нет доступных минут</div>';
            hideHourOption(hour);
            return;
        }

        availableMinutes.forEach(minute => {
            console.log(`Processing minute: ${minute}`);
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
            const hour = parseInt(selectedHour.innerText.split(':')[0]);

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
            if (parseInt(option.innerText.split(':')[0]) === hour) {
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
    });

    // Обработка клика на кнопку бронирования через событие submit формы
    const bookingForm = document.getElementById('booking-form');
    if (!bookingForm) {
        console.error('Element with ID "booking-form" not found.');
        return;
    }

    const bookingButton = bookingForm.querySelector('.booking-button');

    if (!bookingButton) {
        console.error('Element with class "booking-button" not found inside booking-form.');
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

    function submitBookingForm() {
        const formData = {
            salon_id: salonId,
            date: selectedDateInput.value,
            time: selectedTimeInput.value,
            booking_details: []
        };

        if (Object.keys(selectedServicesByCategory).length > 0) {
            for (const [categoryId, services] of Object.entries(selectedServicesByCategory)) {
                const barberId = selectedBarbersByCategory[categoryId] || 'any';
                const duration = services.reduce((total, serviceId) => total + getServiceDuration(serviceId), 0);

                formData.booking_details.push({
                    categoryId: categoryId,
                    services: services.map(serviceId => ({
                        serviceId: serviceId,
                        duration: getServiceDuration(serviceId)
                    })),
                    barberId: barberId,
                    duration: duration
                });
            }
            formData.total_service_duration = calculateTotalDuration() + 5; // Добавляем 5 минут
        } else {
            // Нет выбранных услуг, используем длительность по умолчанию
            formData.total_service_duration = salonDefaultDuration;
        }

        fetch(`/salons/${salonId}/book/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify(formData)
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                // Бронирование успешно
                showBookingConfirmation(data);
            } else if (data.error) {
                alert(`Ошибка при бронировании: ${data.error}`);
            }
        })
        .catch(error => {
            console.error('Ошибка при бронировании:', error);
        });
    }

    // Функция для сохранения данных формы бронирования
    function saveBookingFormData() {
        const formData = {
            date: selectedDateInput.value || '',
            time: selectedTimeInput.value || '',
            barbers: selectedBarbersByCategory,
            services: selectedServices
            // Можно добавить другие необходимые поля
        };
        localStorage.setItem('bookingFormData', JSON.stringify(formData));
        console.log('Booking form data saved to localStorage:', formData);
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
        const date = selectedDateInput.value;
        const time = selectedTimeInput.value;

        if (canSubmitForm()) {
            bookingButton.disabled = false;
            bookingButton.classList.remove('disabled');
            bookingMessage.style.display = 'none';
        } else {
            bookingButton.disabled = true;
            bookingButton.classList.add('disabled');

            // Определяем причину отключения
            let message = '';
            let messageType = 'error'; // Тип сообщения - ошибка

            if (date === '' && time === '') {
                message = 'Пожалуйста, выберите дату и время.';
            } else if (date === '') {
                message = 'Пожалуйста, выберите дату.';
            } else if (time === '') {
                message = 'Пожалуйста, выберите время.';
            }

            bookingMessage.innerText = message;
            bookingMessage.classList.remove('info');
            bookingMessage.classList.add(messageType);
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
        selectedServices.forEach(serviceId => {
            total += getServiceDuration(serviceId);
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

    // Функция для отображения модального окна подтверждения бронирования
    function showBookingConfirmation(data) {
        // Реализуйте отображение модального окна с деталями бронирования
        alert('Бронирование успешно создано!');
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

    // Функция для открытия модального окна авторизации
    function openAuthModal(action, salonId) {
        // Реализуйте логику открытия модального окна авторизации
        console.log(`Открываем модальное окно для ${action} в салоне ${salonId}`);
    }
});
