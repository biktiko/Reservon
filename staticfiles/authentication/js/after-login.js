// authentication/static/authentication/js/after_login.js

document.addEventListener('DOMContentLoaded', function() {
    // Проверяем, есть ли данные бронирования в localStorage
    const bookingFormData = localStorage.getItem('bookingFormData');
    if (bookingFormData) {
        // Проверяем, находится ли пользователь на странице бронирования
        if (window.location.pathname.startsWith('/salons/')) {
            const bookingForm = document.getElementById('booking-form');
            if (bookingForm) {
                restoreBookingFormData(JSON.parse(bookingFormData));
                // Опционально: автоматически отправляем форму
                bookingForm.submit();
                // Или показываем данные пользователю для подтверждения
            }
        }
        // Очищаем данные из localStorage
        localStorage.removeItem('bookingFormData');
    }
});

// Функция для восстановления данных формы бронирования
function restoreBookingFormData(formData) {
    selectedDateInput.value = formData.date;
    selectedTimeInput.value = formData.time;
    selectedBarberInput.value = formData.barber;
    selectedServices = formData.services || [];

    // Восстанавливаем выбранные услуги в интерфейсе
    selectedServices.forEach(serviceId => {
        markServiceAsSelected(serviceId, true);
    });

    // Обновляем UI
    updateBookingButtonState();
    console.log('Booking form data restored:', formData);
}

// after_login.js

document.addEventListener('DOMContentLoaded', function() {
    // Проверяем, есть ли флаг перенаправления на бронирование
    const params = new URLSearchParams(window.location.search);
    if (params.get('redirect_to_booking') === 'true') {
        // Здесь можно вызвать функцию подтверждения бронирования
        confirmBooking();
    }
});

function confirmBooking() {
    // Реализуйте логику подтверждения бронирования
    // Например, показать уведомление пользователю
    alert('Ваше бронирование подтверждено!');
    // Или перенаправить на страницу бронирования
    window.location.href = `/salons/${data.salon_id}/book/`;

}
