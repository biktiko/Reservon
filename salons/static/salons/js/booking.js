// C:\Reservon\Reservon\salons\static\salons\js\booking.js

document.addEventListener('DOMContentLoaded', function() {
    let globalRequestId = 0;

    // Сначала объявляем salonDataElement, а затем salonId
    const salonDataElement = document.getElementById('salon-data');
    const salonId = parseInt(salonDataElement.dataset.salonId, 10);

    const salonModInput = document.getElementById('salon-mod');
    
    const salonMod = salonModInput.value;
    console.log('Salon mod is ', salonMod)

    const salonAppointmentMod = salonDataElement.dataset.appointment_mod
    console.log('Salon appointment mod is ', salonAppointmentMod)

    const isCheckDays = salonDataElement.dataset.ischeckdays
    console.log('isCheckDays is ', isCheckDays)

    const serviceDurationElement = document.getElementById('service-duration');
    const salonDefaultDuration = parseInt(serviceDurationElement.dataset.duration, 10) || 0; // В минутах

    const daySelect = document.getElementById('day-select');
    const hourSelect = document.getElementById('hour-select');
    const minuteSelect = document.getElementById('minute-select');
    const summaryText = document.getElementById('summary-text');

    const selectedDateInput = document.getElementById('selected-date'); // Скрытое поле для даты
    const selectedTimeInput = document.getElementById('selected-time'); // Скрытое поле для времени

    const reservDays = parseInt(salonDataElement.dataset.reservDays, 10) || 7;

    // Кэш для доступных минут
    const availableMinutesCache = {}; // Ключ: ${date}_${hour}, Значение: массив минут
    
    // Сбор данных о барберах
    const barbersData = {};
    const barberCards = document.querySelectorAll('.barber-card');
    
    const servicesBarbersContainer = document.querySelector('.selected-services-barbers');
    
    const bookingButton = document.getElementById('booking-button');

    const bookingButtonBefore = document.getElementById('booking-before');
    const bookingButtonAfter = document.getElementById('booking-after');

    function getCategoryNameById(categoryId) {
        const categoriesCards = Array.from(document.querySelectorAll('.category-button'));
        const card = categoriesCards.find(card => 
            parseInt(card.getAttribute('data-category-id'), 10) == categoryId
        );
        return card ? card.textContent.trim() : 'Неизвестная категория';
    }

    function getServiceNameById(serviceId) {
        const serviceCards = Array.from(document.querySelectorAll('.service-card'));
        const card = serviceCards.find(card => 
            parseInt(card.getAttribute('data-service-id'), 10) == serviceId
        );
        
        const serviceNameElement = card ? card.querySelector('.service-name') : null;
        return serviceNameElement ? serviceNameElement.textContent.trim() : 'Неизвестная услуга';
    }

    function getBarberNameById(barberId) {
        // Обработка случая "any"
        if (barberId === 'any') {
            return 'Любой мастер';
        }
    
        // Преобразование barberId к числу
        const numericBarberId = Number(barberId);
        if (isNaN(numericBarberId)) {
            return 'Любой мастер';
        }
    
        // Получение всех элементов с классом 'barber-card' внутри 'barber-list'
        const barberCards = Array.from(document.querySelectorAll('#barber-list .barber-card'));
    
        // Поиск карточки барбера с соответствующим ID
        const card = barberCards.find(card => {
            return Number(card.getAttribute('data-barber-id')) == numericBarberId;    
        });
    
        if (card) {
            const cardName = card.querySelector('.barber-name');
            if (cardName) {
                return cardName.textContent.trim();
            } else {
                return 'Любой мастер';
            }
        } else {
            return 'Любой мастер';
        }
    }

    function getCategoryDefaultDuration(categoryId) {
        const categoryElement = document.querySelector(`.category[data-category-id="${categoryId}"]`);
        if (categoryElement) {
            return parseInt(categoryElement.dataset.defaultDuration, 10) || salonDefaultDuration;
        }
        return salonDefaultDuration;
    }

    function getBarberDefaultDuration(barberId) {
        const barberElement = document.querySelector(`.barber-card[data-barber-id="${barberId}"]`);
        if (barberElement) {
            return parseInt(barberElement.dataset.defaultDuration, 10) || salonDefaultDuration;
        }
        return salonDefaultDuration;
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

    function addService(serviceId) {
        const categoryId = getCategoryIdByServiceId(serviceId);
        
        if (salonMod == "barber") {
            const barberId = getBarberIdByServiceId(serviceId);
            // Если для данной категории уже выбран барбер, не затираем его
            if (!selectedBarbersByCategory[categoryId]) {
                selectedBarbersByCategory[categoryId] = barberId;
            } else if (selectedBarbersByCategory[categoryId] !== barberId) {
                // Если выбран другой барбер, можно предложить сбросить услуги или обновить выбор
                resetServicesForCategory(categoryId);
                selectedBarbersByCategory[categoryId] = barberId;
            }
        }
    
        if (!selectedServices.includes(serviceId)) {
            selectedServices.push(serviceId);
            updateSelectedServices();
    
            // Обновляем selectedServicesByCategory
            if (categoryId) {
                if (!selectedServicesByCategory[categoryId]) {
                    selectedServicesByCategory[categoryId] = [];
                }
                selectedServicesByCategory[categoryId].push(serviceId);
            }
    
            markServiceAsSelected(serviceId, true);
        }
    }
    

    function removeService(serviceId) {
        const categoryId = getCategoryIdByServiceId(serviceId);
        if (!categoryId) return;
    
        // Удаляем услугу из массива выбранных услуг
        selectedServices = selectedServices.filter(id => id !== serviceId);
        updateSelectedServices();
    
        // Обновляем selectedServicesByCategory
        if (selectedServicesByCategory[categoryId]) {
            selectedServicesByCategory[categoryId] = selectedServicesByCategory[categoryId].filter(id => id !== serviceId);
    
            // Если услуг нет, можно удалить сам ключ из selectedServicesByCategory, но оставить selectedBarbersByCategory:
            if (selectedServicesByCategory[categoryId].length === 0) {
                delete selectedServicesByCategory[categoryId];
            }
        }
    
        // Обновляем UI для карточки услуги
        markServiceAsSelected(serviceId, false);
    
        // НЕ сбрасываем selectedBarbersByCategory, даже если услуг в категории нет!
    
        // После изменения услуг, диспатчим событие для обновления итоговой информации
        const totalPrice = calculateTotalPrice();
        const totalDuration = calculateTotalDuration();
        const event = new CustomEvent('servicesUpdated', { detail: { totalPrice, totalDuration } });
        document.dispatchEvent(event);
    }
    

    // Функция для сброса услуг в категории
    function resetServicesForCategory(categoryId) {
        if (selectedServicesByCategory[categoryId]) {
            const servicesToRemove = [...selectedServicesByCategory[categoryId]];
            servicesToRemove.forEach(serviceId => {
                removeService(serviceId);
            });
        }
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

        // Обновляем скрытые поля для выбранных барберов
        updateBookingForm();
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

    // Получение barberId по serviceId
    function getBarberIdByServiceId(serviceId) {
        const serviceCard = document.querySelector(`.service-card[data-service-id="${serviceId}"]`);
        barberId = serviceCard.dataset.barberId;

        return barberId
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
    
    document.addEventListener('servicesUpdated', function(e) {
        const { totalPrice, totalDuration } = e.detail;
        let totalServiceDuration = 0;
        if (selectedServices.length > 0) {
            totalServiceDuration = totalDuration + 5; // Добавление 5 минут один раз
        } else {
            totalServiceDuration = salonDefaultDuration;
        }

        // Обновляем итоговую информацию
        const totalPriceElem = document.getElementById('total-price');
        const totalDurationElem = document.getElementById('total-duration');
        if (totalPriceElem) totalPriceElem.innerText = Math.round(totalPrice);
        if (totalDurationElem) totalDurationElem.innerText = Math.round(totalServiceDuration);

        // Обновляем состояние кнопки
        console.log('totalDurationElem', totalDurationElem)
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

    // Комментируем код на английском:
    async function populateDays() {
        daySelect.innerHTML = '';
        const daysToCheck = [];
        for (let i = 0; i < reservDays; i++) {
            const dateObj = new Date(today);
            dateObj.setDate(today.getDate() + i);
            daysToCheck.push(dateObj);
        }

        let anyAvailableDay = false;
        // Перебираем все дни и проверяем их доступность
        for (const dateObj of daysToCheck) {
            const chosenDate = dateObj.toISOString().split('T')[0];
            
            // Проверяем доступность хотя бы одного часа (8..22)
            const isAvailable = await hasDayAvailability(salonId, chosenDate, 9, 20);
            if (!isAvailable) {
                continue; // Пропускаем день, если ни одного часа нет
            }
            
            // Если доступен, рисуем
            anyAvailableDay = true;
            const dayOption = document.createElement('div');
            dayOption.dataset.date = chosenDate;
            dayOption.innerText = dateObj.toLocaleDateString('ru-RU', { day: 'numeric', month: 'numeric', weekday: 'short' });
            dayOption.classList.add('day-option');
            dayOption.onclick = () => handleDayClick(dayOption);
            daySelect.appendChild(dayOption);
        }

        // Если вообще нет доступных дней
        if (!anyAvailableDay) {
            daySelect.innerHTML = '<div> Hет достаточно свободного времени для бронирования․ Попробуйте с другим мастером </div>';
        }

        initializeBoookingDay()
    }

    if(isCheckDays==true || isCheckDays=="True"){
        populateDays()
    }else{
        initializeBoookingDay()
    }

    // Вспомогательная функция - проверяет есть ли хоть один час
    async function hasDayAvailability(salonId, dateStr, startHour, endHour) {
        const hoursRange = [];
        for (let h = startHour; h < endHour; h++) hoursRange.push(h);
        const data = await getAvailableMinutesBatch(salonId, dateStr, hoursRange);
        
        // Если хотя бы в одном часу есть массив минут
        return Object.values(data).some(minutesArray => minutesArray && minutesArray.length > 0);
    }

    // Active first day button
    function initializeBoookingDay(){
        // Получаем элемент с ID 'day-select'
        const daysContainer = document.getElementById('day-select');

        // Проверяем, что элемент существует
        if (daysContainer) {
            // Находим первый элемент с классом 'day-option' внутри контейнера
            const firstDayOption = daysContainer.querySelector('.day-option');
            
            // Проверяем, что первый элемент найден
            if (firstDayOption) {
                // Вызываем искусственный клик на найденном элементе
                firstDayOption.click();
            }
        }
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
        const currentRequestId = ++globalRequestId;

        const hoursInfo = document.querySelector('.hours-info');
        if (hoursInfo) hoursInfo.style.display = 'block';
        hourSelect.innerHTML = '';
        minuteSelect.innerHTML = '';
        summaryText.innerText = 'Час и минута не выбраны';

        const startHour = 9;
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

        if (currentRequestId !== globalRequestId) {
            return; // Игнорируем ответ, если запрос устарел
        }

        let anyAvailable = false;
        hours.forEach(hour => {
            const availableMinutes = availableMinutesData[hour];
            if (availableMinutes && availableMinutes.length > 0) {
                const hourOption = document.createElement('div');
              
                hourOption.innerText = `≈ ${hour}:00`;
                hourOption.classList.add('hour-option');
                hourOption.onclick = () =>{
                    handleHourClick(hourOption, chosenDate, hour, availableMinutes);
                } 
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
    
        // Закомментируем чтение из кэша
        // hours.forEach(hour => {
        //     const key = `${date}_${hour}`;
        //     if (availableMinutesCache[key]) {
        //         result[hour] = availableMinutesCache[key];
        //     } else {
        //         uncachedHours.push(hour);
        //     }
        // });
    
        // Вместо этого — просто считаем все часы "не кэшированными"
        hours.forEach(hour => {
            uncachedHours.push(hour);
        });
    
        if (uncachedHours.length > 0) {
            try {
                const formData = collectBookingFormData();
                // console.log(formData)
                const responseData = JSON.stringify({
                    salon_id: salonId,
                    date: date,
                    hours: uncachedHours,
                    booking_details: formData.booking_details,
                    total_service_duration: formData.total_service_duration
                });
    
                const response = await fetch('/salons/get_available_minutes/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCookie('csrftoken')
                    },
                    body: responseData
                });
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                
                const data = await response.json();
                const fetchedMinutes = data.available_minutes || {};
                console.log("available time")
                console.table(fetchedMinutes);
    
                // Закомментируем запись в кэш
                // Object.keys(fetchedMinutes).forEach(hour => {
                //     const key = `${date}_${hour}`;
                //     availableMinutesCache[key] = fetchedMinutes[hour];
                //     result[hour] = fetchedMinutes[hour];
                // });
    
                // Вместо этого просто наполняем result без кэша:
                Object.keys(fetchedMinutes).forEach(hour => {
                    result[hour] = fetchedMinutes[hour];
                });
    
            } catch (error) {
                console.error('Ошибка при получении доступных минут:', error);
                // В случае ошибки добавляем пустые массивы
                uncachedHours.forEach(hour => {
                    result[hour] = [];
                });
            }
        }
        return result;
    }
    
    function handleHourClick(hourOption, date, hour, availableMinutes) {
        clearSelection(hourSelect);
        hourOption.classList.add('selected');

        if(salonAppointmentMod=='handle'){
            summaryText.innerText = `Дата: ${date}, Время: ${hour}:00`;
        }else{
            summaryText.style.display = 'none';
        }
        // Очищаем 'selectedTimeInput' при выборе часа
        if (selectedTimeInput) {
            selectedTimeInput.value = ''; // Оставляем пустым до выбора минуты
        }

        // Вызов функции обновления состояния кнопки
        updateBookingButtonState();

        // Показываем доступные минуты без дополнительного запроса
        if(salonAppointmentMod=='handle'){
            populateAvailableMinutes(availableMinutes, date, hour);
        }else{
            getNearestAvailableTime(salonId, date, hour)
        }
    }

    function populateAvailableMinutes(availableMinutes, date, hour) {
        const minutesInfo = document.querySelector('.minutes-info');
        if (minutesInfo) minutesInfo.style.display = 'block';
        const minuteSelect = document.getElementById('minute-select');
        const summaryText = document.getElementById('summary-text');
        minuteSelect.innerHTML = '';
        summaryText.innerText = 'Дата и час выбраны, выберите минуту';

        // const totalDurationElem = parseInt(document.getElementById('total-duration').innerHTML);
        const totalServiceDuration = calculateTotalDuration();

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

            // Calculate end time
            let endMinute = minute + totalServiceDuration;
            let endHour = hour;
            
            while(endMinute >= 60) {
                endMinute -= 60;
                endHour += 1;
            }

            const formattedEndHour = endHour.toString().padStart(2, '0');
            const formattedEndMinute = endMinute.toString().padStart(2, '0');

            const minuteOption = document.createElement('div');
            minuteOption.innerHTML = `<b>${formattedHour}:${formattedMinute}</b> - ${formattedEndHour}:${formattedEndMinute}`;

            minuteOption.classList.add('minute-option');
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
            const hourText = selectedHour.innerText.replace('≈', '').trim();
            const hour = parseInt(hourText.split(':')[0], 10);
            
            const formattedHour = hour.toString().padStart(2, '0');
            const formattedMinute = minute.toString().padStart(2, '0');

            summaryText.innerText = `Дата: ${date}, Время: ${formattedHour}:${formattedMinute}`;

            if (selectedDateInput) selectedDateInput.value = date;
            if (selectedTimeInput) selectedTimeInput.value = `${formattedHour}:${formattedMinute}`;
        }

        // Вызов функции обновления состояния кнопки
        updateBookingButtonState();
    }

    // Функция для вызова API get_nearest_available_time (возвращает Promise)
    async function getNearestAvailableTime(salonId, date, chosenHour) {
        var formData = collectBookingFormData(); // Ваша функция сбора данных из формы
        console.log('formData.booking_details')
        console.table(formData.booking_details)
        var requestData = {
            salon_id: salonId,
            date: date,
            chosen_hour: chosenHour,
            booking_details: formData.booking_details,
            total_service_duration: formData.total_service_duration
        };
        console.log("Request data (nearest available time) =", JSON.stringify(requestData));
        try {
            var response = await fetch('/salons/get_nearest_available_time/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify(requestData)
            });
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            var data = await response.json();
            console.log("Найденные варианты:", data);
            return data;
        } catch (error) {
            console.error('Ошибка при получении ближайшего времени:', error);
            throw error;
        }
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

    // Обработка события "barberSelected"
    document.addEventListener('barberSelected', function(e) {

        let { categoryId, barberId } = e.detail;
        // Сбрасываем услуги предыдущего барбера в этой категории
        if(salonMod=='category'){
            selectedBarbersByCategory[categoryId] = barberId;
            // const oldBarber = selectedBarbersByCategory[categoryId];
            // if (oldBarber && oldBarber !== barberId) resetServicesForCategory(categoryId);
        }
        updateBookingForm();

        // После изменения барбера, нужно обновить доступные минуты
        const selectedDay = daySelect.querySelector('.selected');
        const selectedHour = hourSelect.querySelector('.selected');
        if (selectedDay && selectedHour) {
            const date = selectedDay.dataset.date;
            const hour = parseInt(selectedHour.innerText.split(':')[0], 10);
            const key = `${date}_${hour}`;
            const availableMinutes = availableMinutesCache[key];
            if (availableMinutes) {
                populateAvailableMinutes(availableMinutes, date, hour);
            }
        }
        
        isCheckDays==true ? populateDays() : initializeBoookingDay()
    });

    // Обработчик клика на кнопку бронирования
    if(bookingButton){
        bookingButton.addEventListener('click', function(event) {

            // Проверяем, заполнены ли необходимые поля
            console.log('bookingButton cliccked')
            console.log(canSubmitForm())
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
    }

    if(bookingButtonBefore) bookingButtonBefore.addEventListener('click', handleAutoBooking);
    if(bookingButtonBefore) bookingButtonAfter.addEventListener('click', handleAutoBooking);

    function handleAutoBooking(event) {
        const btn = event.target;
        const match = btn.innerText.match(/(\d{2}:\d{2})/);

        if (!match) {
            alert('Невозможно определить выбранное время.');
            return;
        }
        const chosenTime = match[1];
        if (!canSubmitForm()) {
            alert('Пожалуйста, выберите дату и время для бронирования.');
            return;
        }

        if (selectedTimeInput) {
            selectedTimeInput.value = chosenTime;
        }
        
        const isAuthenticated = btn.dataset.isAuthenticated === 'true';
        if (!isAuthenticated) {
            saveBookingFormData();
            openAuthModal('login_from_booking', salonId);
            return;
        }

        // Устанавливаем выбранное время в скрытый input
        // Теперь данные, собранные функцией collectBookingFormData(), будут содержать поле time
        submitBookingForm();
    }
    

    function collectBookingFormData() {

        const formData = {
            salon_id: salonId,
            date: selectedDateInput.value,
            time: selectedTimeInput ? selectedTimeInput.value : '',
            booking_details: [],
            total_service_duration: 0
        };
    
        if (salonMod === 'barber') {
            const categories = Object.keys(selectedServicesByCategory);
        
            if (categories.length > 0) {
                categories.forEach(categoryId => {
                    const barberId = selectedBarbersByCategory[categoryId];
                    console.log('barberId', barberId);
        
                    // Список услуг по категории
                    const services = selectedServicesByCategory[categoryId] || [];
        
                    // Суммируем продолжительность выбранных услуг
                    let duration = services.reduce((acc, sId) => acc + getServiceDuration(sId), 0);
        
                    // Если нет услуг, но есть выбранный барбер, подставляем дефолт
                    if (duration === 0 && barberId) {
                        duration = getBarberDefaultDuration(barberId);
                    }
        
                    // Добавляем в formData, если что-то выбрано
                    if (services.length > 0 || barberId) {
                        formData.booking_details.push({
                            categoryId: categoryId,
                            barberId: barberId,
                            services: services.map(sId => ({
                                serviceId: sId,
                                duration: getServiceDuration(sId)
                            })),
                            duration: duration
                        });
                        formData.total_service_duration += duration;
                    }
                });
            } else {
                // Когда категорий нет, но есть выбранный барбер
                const barber = document.querySelector('.barber-card.selected');
                if (barber) {
                    const barberId = barber.dataset.barberId;
                    // Подставим дефолтную длительность для выбранного барбера (если надо)
                    const duration = getBarberDefaultDuration(barberId);
        
                    formData.booking_details.push({
                        categoryId: 'any',
                        barberId: barberId,
                        services: [],
                        duration: duration
                    });
                    formData.total_service_duration += duration;
                }
            }
        
            // Если в booking_details вообще ничего не собралось
            if (formData.booking_details.length === 0) {
                formData.total_service_duration = salonDefaultDuration;
            }
        } else {
            const categories = new Set([...Object.keys(selectedServicesByCategory), ...Object.keys(selectedBarbersByCategory)]);
            console.log('categories', categories);
            categories.forEach(categoryId => {
                let barberId = selectedBarbersByCategory[categoryId] || 'any';
                // if (barberId === 'any' & window.barbersByCatergoryWithoutAny[categoryId] !== undefined) {
                //     barberId = window.barbersByCatergoryWithoutAny[categoryId];
                // }

                let services = selectedServicesByCategory[categoryId] || [];
                let duration = 0;
                if (services.length > 0) {
                    duration = services.reduce((total, serviceId) => total + getServiceDuration(serviceId), 0);
                }
                if (duration === 0 && barberId !== 'any') {
                    duration = getCategoryDefaultDuration(categoryId);
                }
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
            if (formData.booking_details.length === 0) {
                formData.total_service_duration = salonDefaultDuration;
            }
            console.log('formData.total_service_duration', formData.total_service_duration);
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

    function canSubmitForm() {
        const date = selectedDateInput.value;
        const time = selectedTimeInput ? selectedTimeInput.value : ''; // для handler-режима

        // Разрешаем бронирование, если выбрана дата и (либо время, либо для auto режима мы можем его получить)
        return date !== '' && (salonAppointmentMod === 'auto' || time !== '');
    }



    // Обновлённая функция обновления состояния кнопок
    function updateBookingButtonState() {
        // Если отсутствует элемент для сообщений – ничего не делаем (или можно создать его динамически)
        
        if (!canSubmitForm()) {
            // Форма не заполнена: показываем сообщение и отключаем кнопки
            if (salonAppointmentMod === 'auto') {
                if (bookingButtonBefore) {
                    bookingButtonBefore.disabled = true;
                    bookingButtonBefore.classList.add('disabled');
                }
                if (bookingButtonAfter) {
                    bookingButtonAfter.disabled = true;
                    bookingButtonAfter.classList.add('disabled');
                }
                // Скрываем контейнер кнопок (если есть)
                var container = document.getElementById('booking-buttons-container');
                if (container) { container.style.display = 'none'; }
            } else {
                if (bookingButton) {
                    bookingButton.disabled = true;
                    bookingButton.classList.add('disabled');
                }
            }
            if (bookingMessage) {
                bookingMessage.innerText = 'Пожалуйста, выберите дату и время.';
                bookingMessage.classList.remove('info');
                bookingMessage.classList.add('error');
                bookingMessage.style.display = 'block';
            }
            return;
        } else {
            if (bookingMessage) {
                bookingMessage.style.display = 'none';
            }
        }
        
        // Если режим handler – просто активируем кнопку
        if (salonAppointmentMod !== 'auto') {
            if (bookingButton) {
                bookingButton.disabled = false;
                bookingButton.classList.remove('disabled');
            }
        } else {
            // Режим auto: пытаемся получить выбранный час из элемента с классом .hour-option.selected
            var hourSelectedEl = document.querySelector('.hour-option.selected');
            if (!hourSelectedEl) {
                // Если час не выбран – скрываем контейнер кнопок
                var container = document.getElementById('booking-buttons-container');
                if (container) { container.style.display = 'none'; }
                return;
            }
            // Извлекаем число из innerText (например, "≈ 11:00" или "11:00")
            var hourText = hourSelectedEl.innerText;
            var match = hourText.match(/(\d{1,2})/);
            if (!match) {
                console.error("Невозможно извлечь выбранный час из текста:", hourText);
                return;
            }
            var selectedHour = parseInt(match[1], 10);
            // Вызываем API для получения ближайших вариантов
            console.log('selectedDateInput.value', 'selectedHour');
            console.log(selectedDateInput.value, selectedHour);
            getNearestAvailableTime(salonId, selectedDateInput.value, selectedHour)
            .then(function(data) {
                // Если ни один вариант не получен, выводим ошибку
                if (!data.nearest_before && !data.nearest_after) {
                    console.error("Время недоступно");
                    return;
                }
                
                // Если оба варианта получены, проверяем их разницу
                let variantToShow = null;
                if (data.nearest_before && data.nearest_after) {
                    const [h1, m1] = data.nearest_before.replace('։', ':').split(':').map(Number);
                    const [h2, m2] = data.nearest_after.replace('։', ':').split(':').map(Number);
                    const diffMinutes = (h2 * 60 + m2) - (h1 * 60 + m1);
                    
                    // Если варианты совпадают или разница меньше порога (например, 30 минут), показываем один вариант
                    if (data.nearest_before === data.nearest_after || diffMinutes < 30) {
                        variantToShow = data.nearest_before;
                    } else {
                        // Если оба варианта различны и разница достаточно велика, показываем обе кнопки
                        bookingButtonBefore.innerText = 'Забронировать в ' + data.nearest_before;
                        bookingButtonBefore.disabled = false;
                        bookingButtonBefore.classList.remove('disabled');
                        bookingButtonBefore.style.display = '';
                        
                        bookingButtonAfter.innerText = 'Забронировать в ' + data.nearest_after;
                        bookingButtonAfter.disabled = false;
                        bookingButtonAfter.classList.remove('disabled');
                        bookingButtonAfter.style.display = '';
                        
                        const container = document.getElementById('booking-buttons-container');
                        if (container) { container.style.display = 'block'; }
                        return;
                    }
                } else if (data.nearest_before) {
                    variantToShow = data.nearest_before;
                } else if (data.nearest_after) {
                    variantToShow = data.nearest_after;
                }
                
                // Если доступен только один вариант, показываем только одну кнопку
                bookingButtonBefore.innerText = 'Забронировать в ' + variantToShow;
                bookingButtonBefore.disabled = false;
                bookingButtonBefore.classList.remove('disabled');
                bookingButtonBefore.style.display = '';
                bookingButtonAfter.style.display = 'none';
                
                const container = document.getElementById('booking-buttons-container');
                if (container) { container.style.display = 'block'; }
            })
            .catch(function(err) {
                console.error("Ошибка получения ближайшего времени:", err);
            });
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
        // Если ни одна услуга не выбрана, используем длительность по умолчанию салона.
        if (selectedServices.length === 0) {
            return salonDefaultDuration;
        }
        let total = 0;
        // Учесть длительность для выбранных услуг
        selectedServices.forEach(serviceId => {
            total += getServiceDuration(serviceId);
        });
        // Если для какой-то категории услуги не выбраны, но выбран барбер,
        // то прибавляем default duration для этой категории.
        Object.keys(selectedBarbersByCategory).forEach(categoryId => {
            if (!selectedServicesByCategory[categoryId] || selectedServicesByCategory[categoryId].length === 0) {
                total += getCategoryDefaultDuration(categoryId);
            }
        });
        // Если сумма по-прежнему равна 0, используем длительность салона
        if (total === 0) {
            total = salonDefaultDuration;
        }
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
        console.log('bodyData')
        console.log(bodyData)
    
        if (action === 'login_from_booking') {
            bodyData.salon_id = salonId;
        }
    
        fetch('/auth/load_modal/', {
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

    window.showBookingConfirmationModal = function(formData) {
        console.log(formData)
        const modal = document.getElementById('booking-confirmation-modal');
        const closeButton = modal.querySelector('.close-button');
        const confirmButton = modal.querySelector('.confirm-button');
        const cancelButton = modal.querySelector('.cancel-button');
    
        // Функция для вычисления endTime
        function calculateEndTime(formData) {
            // Если время не указано, пытаемся получить его из скрытого поля или возвращаем пустую строку
            if (!formData.time || formData.time.trim() === "") {
                const selectedTimeInput = document.getElementById('selected-time');
                if (selectedTimeInput && selectedTimeInput.value.trim() !== "") {
                    formData.time = selectedTimeInput.value.trim();
                } else {
                    return ""; // Или можно задать дефолтное время, например, "00:00"
                }
            }
            const parts = formData.time.split(":");
            if (parts.length < 2) {
                return "";
            }
            let hours = parseInt(parts[0], 10);
            let minutes = parseInt(parts[1], 10);
        
            // Если парсинг не успешен, возвращаем пустую строку
            if (isNaN(hours) || isNaN(minutes)) {
                return "";
            }
        
            minutes += formData.total_service_duration;
            hours += Math.floor(minutes / 60);
            minutes = minutes % 60;
        
            // Форматируем часы и минуты с ведущими нулями
            const formattedHours = String(hours).padStart(2, "0");
            const formattedMinutes = String(minutes).padStart(2, "0");
            return `${formattedHours}:${formattedMinutes}`;
        }
        
        formData.endTime = calculateEndTime(formData);
    
        generateBookingDetailsHTML(formData);

        modal.classList.add('show');
    
        if (closeButton) {
            closeButton.onclick = () => {
                hideBookingConfirmationModal();
            };
        }
    
        if (cancelButton) {
            cancelButton.onclick = () => {
                hideBookingConfirmationModal();
            };
        }
    
        // Важно: здесь мы перехватываем нажатие «Подтвердить»
        if (confirmButton) {
            confirmButton.onclick = () => {
                const userCommentField = document.getElementById('user-comment');
                let userComment = '';
                if (userCommentField) {
                    userComment = userCommentField.value.trim();
                }
    
                formData.user_comment = userComment;
                formData.salonMod = salonMod
                
                console.log('Отправляем данные бронирования:', formData);
                submitBookingData(formData);
            };
        }
    
        // Закрытие по клику вне
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
        if(bookingDateTime){
            bookingDateTime.innerHTML = `<h1 class="booking-date-time"><strong>Дата:</strong> ${data.date} <br> <strong>Время:</strong> ${data.time} - ${data.endTime} </h1>`;
        }else{
            location.reload()
        }
        
        // Очищаем контейнер
        bookingDetailsContainer.innerHTML = '';
        if (data.booking_details && data.booking_details.length > 0) {
            console.log(data.booking_details)
            data.booking_details.forEach((detail) => {
                const categoryName = getCategoryNameById(detail.categoryId);
                console.log(detail)
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
                    </div>`;
            });
        } else {
            bookingDetailsContainer.innerHTML = '<p><strong>Услуги и мастера не выбраны.</strong></p>';
        }
    }

    function submitBookingData(formData) {
        const salonIdForBooking = parseInt(salonDataElement.dataset.salonId, 10);
        console.log('Отправляем данные бронирования:', JSON.stringify(formData));
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
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                // Бронирование успешно выполнено
                showBookingSuccessMessage(document.getElementById('booking-confirmation-modal'));
                localStorage.removeItem('bookingFormData');
            } else if (data.error) {
                showBookingSErrorMessage(document.getElementById('booking-confirmation-modal'));
                alert(`Ошибка при бронировании: ${data.error}`);
            }
        })
        .catch(error => {
            showBookingSErrorMessage(document.getElementById('booking-confirmation-modal'));
            console.error('Ошибка при бронировании:', error);
        });
    }
    
    
    function showBookingSuccessMessage(modal) {
        const modalBody = modal.querySelector('.modal-body.booking-modal-body');
        const userNote = modal.querySelector('.user-comment-section');
        // Очищаем содержимое модального окна
        if (userNote) userNote.style.display = 'none';
        modalBody.innerHTML = 
            `<h2 id="modal-title">Бронирование подтверждено</h2>
            <p class="booking-success-message">Ваше бронирование успешно подтверждено!</p>
            <div class="close-confirmation-container">
                <button class="close-confirmation-button">Закрыть</button>
            </div>`;
    
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
                location.reload();
            };
        }
    }

    function showBookingSErrorMessage(modal) {
        const modalBody = modal.querySelector('.modal-body.booking-modal-body');
        const userNote = modal.querySelector('.user-comment-section');
        // Очищаем содержимое модального окна
        if (userNote) userNote.style.display = 'none';

        modalBody.innerHTML = 
            `<h2 style="color: red" id="modal-title">Бронирование НЕ подтвердилось!</h2>
            <p class="booking-success-message"> К сожалению, бронирование не удалось подтвердить. Возможно, это время уже занято. Попробуйте, пожалуйста, выбрать другое время или другого мастера </p>

            <div class="close-confirmation-container">
                <button class="close-confirmation-button">Закрыть</button>
            </div>`;
    
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
        // modal.style.display = 'none'; // Добавляем скрытие модального окна
        // location.reload()
    }

});

document.addEventListener('loginFromBookingSuccess', function(event) {
    
    // Если в событии передавались данные — они лежат в event.detail
    console.log('loginFromBookingSuccess event triggered');
    console.log('event.detail:', event.detail);
    // Получаем данные из localStorage
    const formDataString = localStorage.getItem('bookingFormData');
    if (formDataString) {
        const formData = JSON.parse(formDataString);
        showBookingConfirmationModal(formData);
    } else {
        console.error('No booking data found in localStorage.');
    }
});