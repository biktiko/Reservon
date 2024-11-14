// static/salons/js/booking.js

document.addEventListener('DOMContentLoaded', function() {
    const daySelect = document.getElementById('day-select');
    const hourSelect = document.getElementById('hour-select');
    const minuteSelect = document.getElementById('minute-select');
    const summaryText = document.getElementById('summary-text');

    const selectedDateInput = document.getElementById('selected-date'); // Скрытое поле для даты
    const selectedTimeInput = document.getElementById('selected-time'); // Скрытое поле для времени
    const selectedBarberInput = document.getElementById('selected-barber'); // Скрытое поле для barber_id
    const barberSelectionContainer = document.querySelector('.barber-selection');

    if (barberSelectionContainer) {
        document.addEventListener('barberSelected', function(e) {
            const barberId = e.detail.barberId;
            selectedBarberId = barberId;
            selectedBarberInput.value = selectedBarberId;
        
            console.log(`Selected barber ID from custom event: ${selectedBarberId}`);
        
            // Обновляем доступные минуты при выборе барбера
            const selectedDay = daySelect.querySelector('.selected');
            const selectedHour = hourSelect.querySelector('.selected');
            if (selectedDay && selectedHour) {
                const date = selectedDay.dataset.date;
                const hour = parseInt(selectedHour.innerText.split(':')[0]);
                fetchAvailableMinutes(salonId, selectedBarberId, date, hour);
            }
        
            // Обновляем состояние кнопки бронирования
            updateBookingButtonState();
        });
    } else {
        console.error('Element with class "barber-selection" not found.');
    }


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
            updateSelectedServices();
            // Обновляем UI
            markServiceAsSelected(serviceId, true);
        }
    }

    function removeService(serviceId) {
        selectedServices = selectedServices.filter(id => id !== serviceId);
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

    console.log(`Updated totalServiceDuration: ${totalServiceDuration}`);

    
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

        fetchAvailableMinutes(salonId, selectedBarberId, date, hour);
    }

    function fetchAvailableMinutes(salonId, barberId, date, hour) {
        // Показываем индикатор загрузки
        minuteSelect.innerHTML = '<div>Загрузка...</div>';
        summaryText.innerText = 'Загрузка доступных минут...';
    
        // Приведение к числу
        const numericTotalServiceDuration = Number(totalServiceDuration);
        if (isNaN(numericTotalServiceDuration)) {
            console.error(`totalServiceDuration is not a number: ${totalServiceDuration}`);
            minuteSelect.innerHTML = '<div>Ошибка при расчёте длительности</div>';
            return;
        }
    
        console.log(`Fetching available minutes with total_service_duration=${numericTotalServiceDuration}`);
    
        const url = `/salons/get_available_minutes/?salon_id=${salonId}&barber_id=${barberId}&date=${date}&hour=${hour}&total_service_duration=${numericTotalServiceDuration}`;
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

            // Создаём локальное время без суффикса Z
            const localDateTime = new Date(`${date}T${formattedHour}:${formattedMinute}:00`);
            console.log(`localDateTime:`, localDateTime);

            if (isNaN(localDateTime.getTime())) {
                console.error(`Invalid DateTime for date: ${date}, hour: ${hour}, minute: ${minute}`);
                return;
            }

            // Получаем локальные часы и минуты
            const localHour = localDateTime.getHours();
            const localMinute = localDateTime.getMinutes();

            // Проверка валидности локальных часов и минут
            if (isNaN(localHour) || isNaN(localMinute)) {
                console.error(`Invalid local time after conversion: localHour=${localHour}, localMinute=${localMinute}`);
                return;
            }

            const minuteOption = document.createElement('div');
            minuteOption.innerText = `${localHour}:${localMinute.toString().padStart(2, '0')}`;
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

            // Форматируем час и минуту с ведущим нулём
            const formattedHour = hour.toString().padStart(2, '0');
            const formattedMinute = minute.toString().padStart(2, '0');

            const localDateTime = new Date(`${date}T${formattedHour}:${formattedMinute}:00`);
            
            // Проверка валидности локального времени
            if (isNaN(localDateTime.getTime())) {
                console.error(`Invalid local DateTime: ${formattedHour}:${formattedMinute}`);
                return;
            }

            // Конвертируем локальное время в UTC
            const utcDateTime = new Date(localDateTime.getTime() - (localDateTime.getTimezoneOffset() * 60000));
            const utcDate = utcDateTime.toISOString().split('T')[0];
            const utcTime = utcDateTime.getUTCHours().toString().padStart(2, '0') + ':' + utcDateTime.getUTCMinutes().toString().padStart(2, '0');

            // Отображаем локальное время в summaryText
            const localDate = localDateTime.toLocaleDateString('ru-RU');
            const localTime = localDateTime.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' });
            summaryText.innerText = `Дата: ${localDate}, Время: ${localTime}`;

            // Обновление скрытых полей формы с UTC временем
            if (selectedDateInput) selectedDateInput.value = utcDate;
            if (selectedTimeInput) selectedTimeInput.value = `${utcTime}`;
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

    //  обработчик клика на кнопку бронирования
    bookingButton.addEventListener('click', function(event) {
        // Проверяем, заполнены ли необходимые поля
        if (!canSubmitForm()) {
            event.preventDefault();
            // Сохраняем данные формы в localStorage
            saveBookingFormData();
            alert('Пожалуйста, выберите дату и время для бронирования.');
        } else {
            // Получаем информацию об авторизации пользователя
            const isAuthenticated = bookingButton.dataset.isAuthenticated === 'true';
            if (!isAuthenticated) {
                event.preventDefault(); // Предотвращаем отправку формы
                // Открываем модальное окно логина и передаём действие
                openAuthModal('login_from_booking');
                // logger.debug('User not login')
            } else {
                // Пользователь авторизован, форма отправится автоматически
                console.log('User login')
            }
        }
    });

    // Функция для сохранения данных формы бронирования
    function saveBookingFormData() {
        const formData = {
            date: selectedDateInput.value,
            time: selectedTimeInput.value,
            barber: selectedBarberInput.value,
            services: selectedServices,
            // Добавьте другие необходимые поля
        };
        localStorage.setItem('bookingFormData', JSON.stringify(formData));
        console.log('Booking form data saved to localStorage:', formData);
    }

    // Функция проверки возможности отправки формы
    function canSubmitForm() {
        const date = selectedDateInput.value;
        const time = selectedTimeInput.value;
        return date !== '' && time !== '';
    }

    // Обработчик события submit на форме
    bookingForm.addEventListener('submit', function(event) {
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

        if (canSubmitForm()) {
            bookingButton.disabled = false;
            bookingButton.classList.remove('disabled');

            // Проверяем, нужно ли показывать рекомендации
            if (hasServices || hasBarbers) {
                let missing = [];
                if (hasServices && selectedServices.length === 0) {
                    missing.push('услуги');
                }
                if (hasBarbers && barber === 'any') {
                    missing.push('мастера');
                }

                if (missing.length > 0) {
                    let message = '';
                    let messageType = 'info'; // Тип сообщения - рекомендация

                    if (missing.length === 2) {
                        message = 'Вы так же можете выбрать желанные услуги и мастера.';
                    } else if (missing.length === 1) {
                        if (missing[0] === 'услуги') {
                            message = 'Вы так же можете выбрать желанные услуги.';
                        } else if (missing[0] === 'мастера') {
                            message = 'Вы так же можете выбрать желанного мастера.';
                        }
                    }

                    bookingMessage.innerText = message;
                    bookingMessage.classList.remove('error');
                    bookingMessage.classList.add(messageType);
                    bookingMessage.style.display = 'block';
                } else {
                    // Все необходимые опции выбраны
                    bookingMessage.style.display = 'none';
                    bookingMessage.classList.remove('error', 'info');
                }
            } else {
                // Нет услуг и барберов, скрываем сообщение
                bookingMessage.style.display = 'none';
                bookingMessage.classList.remove('error', 'info');
            }

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
                const duration = parseInt(serviceCard.dataset.duration, 10) || 0;
                total += duration;
            }
        });
        return total;
    }
});
