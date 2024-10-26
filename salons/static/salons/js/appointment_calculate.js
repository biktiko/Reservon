// Динамический расчет стоимости и времени
function calculateTotal() {
    let totalPrice = parseFloat("{{ salon.default_price }}");
    let totalDuration = parseInt("{{ salon.default_duration }}");

    document.querySelectorAll('#services input[type="checkbox"]').forEach(service => {
        if (service.checked) {
            totalPrice += parseFloat(service.dataset.price);
            totalDuration += parseInt(service.dataset.duration);
        }
    });

    document.getElementById('total-price').innerText = totalPrice.toFixed(2);
    document.getElementById('total-duration').innerText = totalDuration;
}

// Инициализация календаря FullCalendar
document.addEventListener('DOMContentLoaded', function() {
    let calendarEl = document.getElementById('calendar');
    let calendar = new FullCalendar.Calendar(calendarEl, {
        initialView: 'dayGridWeek',
        selectable: true,
        select: function(info) {
            // Обработка выбора даты
            let date = info.startStr;
            document.querySelector('#selected-date').value = date;
        }
    });
    calendar.render();

    // Инициализация таймпикера Timepicker.js
    const timePicker = new TimePicker(document.getElementById('time-picker'), {
        onSelect: function(selectedTime) {
            // Обработка выбранного времени
            document.querySelector('#selected-time').value = selectedTime;
        }
    });
});

document.addEventListener('DOMContentLoaded', function () {
    const daySelect = document.getElementById('day-select');
    const hourSelect = document.getElementById('hour-select');
    const minuteSelect = document.getElementById('minute-select');
    const summaryText = document.getElementById('summary-text');

    const workingHours = "{{ salon.opening_hours|safe }}";  // Загружаем рабочие часы салона из шаблона
    const serviceDuration =" {{ service_duration }}"; // Продолжительность услуги, добавленная сервером
    
    // 1. Заполнение дней на 7 дней вперед
    const today = new Date();
    for (let i = 0; i < 7; i++) {
        const dayOption = document.createElement('div');
        const date = new Date(today);
        date.setDate(today.getDate() + i);

        dayOption.innerText = date.toLocaleDateString('ru-RU', { weekday: 'short', day: 'numeric', month: 'numeric' });
        dayOption.dataset.date = date.toISOString().split('T')[0];
        dayOption.onclick = () => handleDayClick(dayOption);

        daySelect.appendChild(dayOption);
    }

    function handleDayClick(dayOption) {
        clearSelection(daySelect);
        dayOption.classList.add('selected');
        populateHours(dayOption.dataset.date);
        clearSelection(minuteSelect);
    }

    function populateHours(dateString) {
        hourSelect.innerHTML = '';
        const day = new Date(dateString).toLocaleDateString('en-US', { weekday: 'long' }).toLowerCase();
        const opening = workingHours[day]?.open || '09:00';
        const closing = workingHours[day]?.close || '18:00';

        for (let hour = parseInt(opening.split(':')[0]); hour < parseInt(closing.split(':')[0]); hour++) {
            const hourOption = document.createElement('div');
            hourOption.innerText = `${hour}:00`;
            hourOption.onclick = () => handleHourClick(hourOption, dateString, hour);
            hourSelect.appendChild(hourOption);
        }
    }

    function handleHourClick(hourOption, date, hour) {
        clearSelection(hourSelect);
        hourOption.classList.add('selected');
        populateMinutes(date, hour);
    }

    function populateMinutes(date, hour) {
        minuteSelect.innerHTML = '';
        const interval = 5;
        const maxMinutes = 60 - serviceDuration % 60;
        
        for (let minute = 0; minute < maxMinutes; minute += interval) {
            const minuteOption = document.createElement('div');
            minuteOption.innerText = minute.toString().padStart(2, '0');
            minuteOption.onclick = () => handleMinuteClick(minuteOption, date, hour, minute);
            minuteSelect.appendChild(minuteOption);
        }
    }

    function handleMinuteClick(minuteOption, date, hour, minute) {
        clearSelection(minuteSelect);
        minuteOption.classList.add('selected');
        summaryText.innerText = `Дата: ${date}, Время: ${hour}:${minute.toString().padStart(2, '0')}`;
    }

    function clearSelection(container) {
        const selected = container.querySelector('.selected');
        if (selected) selected.classList.remove('selected');
    }
});
