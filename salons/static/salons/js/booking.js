// static/salons/js/booking.js

document.addEventListener('DOMContentLoaded', function() {
    const daySelect = document.getElementById('day-select');
    const hourSelect = document.getElementById('hour-select');
    const minuteSelect = document.getElementById('minute-select');
    const summaryText = document.getElementById('summary-text');

    const selectedDateInput = document.getElementById('selected-date'); // Скрытое поле для даты
    const selectedTimeInput = document.getElementById('selected-time'); // Скрытое поле для времени
    const selectedBarberInput = document.getElementById('selected-barber'); // Скрытое поле для barber_id

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

    let selectedBarberId = 'any'; // По умолчанию 'Любой мастер'

    // Управление выбранными услугами
    let selectedServices = [];

    // Объявление bookingMessage до использования в функциях
    const bookingMessage = document.getElementById('booking-message');
    if (!bookingMessage) {
        console.error('Element with ID "booking-message" not found.');
        return;
    }

    // Функции для добавления и удаления выбранных услуг
    function addService(serviceId) {
        if (!selectedServices.includes(serviceId)) {
            selectedServices.push(serviceId);
            console.log(`Service added: ${serviceId}`);
            updateSelectedServices();
            // Обновляем UI
            markServiceAsSelected(serviceId, true);
        }
    }

    function removeService(serviceId) {
        selectedServices = selectedServices.filter(id => id !== serviceId);
        console.log(`Service removed: ${serviceId}`);
        updateSelectedServices();
        // Обновляем UI
        markServiceAsSelected(serviceId, false);
    }

    function updateSelectedServices() {
        const selectedServicesContainer = document.querySelector('.selected-services');
        selectedServicesContainer.innerHTML = ''; // Очищаем текущие услуги

        selectedServices.forEach(serviceId => {
            const input = document.createElement('input');
            input.type = 'hidden';
            input.name = 'services';
            input.value = serviceId;
            selectedServicesContainer.appendChild(input);
            console.log(`Hidden input added for service: ${serviceId}`);
        });
    }

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

                // Обновление итоговой информации
                document.getElementById('total-price').innerText = totalPrice;
                document.getElementById('total-duration').innerText = totalServiceDuration;
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
        console.log(`Общая длительность обслуживания: ${totalServiceDuration} минут`);
    
        // Обновляем доступные минуты для выбранного часа, не сбрасывая выбор
        const selectedDay = daySelect.querySelector('.selected');
        const selectedHour = hourSelect.querySelector('.selected');
        if (selectedDay && selectedHour) {
            const date = selectedDay.dataset.date;
            const hour = parseInt(selectedHour.innerText.split(':')[0]);
            fetchAvailableMinutes(salonId, selectedBarberId, date, hour);
        }
    
        // Обновляем итоговую информацию
        document.getElementById('total-price').innerText = totalPrice;
        document.getElementById('total-duration').innerText = totalServiceDuration;

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
        console.log(`Выбрана дата: ${selectedDateInput.value}`);

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
            console.log(`Выбран час: ${hour}:00, минута не выбрана`);
        }

        // Вызов функции обновления состояния кнопки
        updateBookingButtonState();

        fetchAvailableMinutes(salonId, selectedBarberId, date, hour);
    }

    function fetchAvailableMinutes(salonId, barberId, date, hour) {
        // Показываем индикатор загрузки
        minuteSelect.innerHTML = '<div>Загрузка...</div>';
        summaryText.innerText = 'Загрузка доступных минут...';

        const url = `/salons/get_available_minutes/?salon_id=${salonId}&barber_id=${barberId}&date=${date}&hour=${hour}&total_service_duration=${totalServiceDuration}`;
        fetch(url)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                if (data.available_minutes) {
                    populateAvailableMinutes(data.available_minutes, date, hour);
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
        minuteSelect.innerHTML = '';
        summaryText.innerText = 'Дата и час выбраны, выберите минуту';

        if (availableMinutes.length === 0) {
            minuteSelect.innerHTML = '<div>Нет доступных минут</div>';
            // Возможно, стоит скрыть этот час из hourSelect, если все минуты заняты
            hideHourOption(hour);
            return;
        }

        availableMinutes.forEach(minute => {
            const minuteOption = document.createElement('div');
            minuteOption.innerText = `${hour}:${minute.toString().padStart(2, '0')}`;
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
            summaryText.innerText = `Дата: ${date}, Время: ${hour}:${minute.toString().padStart(2, '0')}`;

            // Обновление скрытых полей формы
            if (selectedDateInput) selectedDateInput.value = date;
            if (selectedTimeInput) selectedTimeInput.value = `${hour}:${minute.toString().padStart(2, '0')}`;
            console.log(`Выбрано время: ${selectedTimeInput.value}`);
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

    // Обработка клика на кнопку бронирования через событие submit формы
    const bookingForm = document.getElementById('booking-form');
    const bookingButton = bookingForm.querySelector('.booking-button');
    // Объявление bookingMessage уже было сделано выше

    // Функция проверки возможности отправки формы
    function canSubmitForm() {
        const date = selectedDateInput.value;
        const time = selectedTimeInput.value;
        console.log(`canSubmitForm called. Date: ${date}, Time: ${time}`);
        return date !== '' && time !== '';
    }

    // Обработчик события submit на форме
    bookingForm.addEventListener('submit', function(event) {
        console.log('Форма отправляется');
        if (!canSubmitForm()) {
            event.preventDefault();
            alert('Пожалуйста, выберите дату и время для бронирования.');
        }
    });

    // Обновлённая функция updateBookingButtonState
    function updateBookingButtonState() {
        const date = selectedDateInput.value;
        const time = selectedTimeInput.value;
        const barber = selectedBarberInput.value;
        console.log(`updateBookingButtonState called. Date: ${date}, Time: ${time}, Barber: ${barber}`);

        if (canSubmitForm()) {
            bookingButton.disabled = false;
            bookingButton.classList.remove('disabled');
            bookingMessage.style.display = 'none';
            console.log('Кнопка "Забронировать" активирована.');
        } else {
            bookingButton.disabled = true;
            bookingButton.classList.add('disabled');
            // Определяем причину отключения
            let message = '';
            if (date === '' && time === '') {
                message = 'Пожалуйста, выберите дату и время.';
            } else if (date === '') {
                message = 'Пожалуйста, выберите дату.';
            } else if (time === '') {
                message = 'Пожалуйста, выберите время.';
            }

            // Дополнительная проверка: если услуги и барберы доступны, но не выбраны
            if (date !== '' && (hasServices || hasBarbers) && (selectedServices.length === 0 || barber === 'any')) {
                message = 'Вы так же можете выбрать желанные услуги или барбера.';
            }

            console.log(`Setting booking message: ${message}`);
            bookingMessage.innerText = message;
            bookingMessage.style.display = 'block';
            console.log('Кнопка "Забронировать" отключена.');
        }
    }

    // Инициализация состояния кнопки бронирования
    updateBookingButtonState();

    // Пример функций для расчета общей цены и длительности
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

    function calculateTotalDuration() {
        let total = 0;
        selectedServices.forEach(serviceId => {
            const serviceCard = document.querySelector(`.service-card[data-service-id="${serviceId}"]`);
            if (serviceCard) {
                const duration = parseInt(serviceCard.dataset.duration) || 0; // Убедитесь, что duration передаётся в минутах
                total += duration;
            }
        });
        console.log(`Суммарная длительность услуг: ${total} минут`);
        return total;
    }
});
