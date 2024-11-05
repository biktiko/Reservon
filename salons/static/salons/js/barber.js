// static/salons/js/barber.js

document.addEventListener('DOMContentLoaded', function() {
    const barberList = document.getElementById('barber-list');
    const activeBarberCard = document.getElementById('active-barber');
    const allBarberCards = Array.from(document.querySelectorAll('#barber-list .barber-card'));
    let selectedBarberId = 'any'; // По умолчанию 'Любой мастер'

    // Инициализация: скрыть список барберов
    barberList.classList.remove('open');

    // Обработчики для карточек барберов в списке
    allBarberCards.forEach(card => {
        card.addEventListener('click', function() {
            const barberId = this.getAttribute('data-barber-id');
            selectBarber(barberId);
        });
    });

    // Обработчик клика на активного барбера
    activeBarberCard.addEventListener('click', function() {
        barberList.classList.toggle('open');
        updateBarberList(); // Обновляем список при открытии/закрытии
    });

    function selectBarber(barberId) {
        selectedBarberId = barberId;
        updateActiveBarber();
        updateBarberList(); // Обновляем список после выбора барбера

        // Добавляем анимацию смены активного барбера
        activeBarberCard.classList.add('switch-animation');
        activeBarberCard.addEventListener('animationend', function() {
            activeBarberCard.classList.remove('switch-animation');
        }, { once: true });

        barberList.classList.remove('open');

        // После выбора барбера, возможно, нужно обновить доступные минуты
        // Для этого можно вызвать событие или функцию из booking.js
        // Например, использовать CustomEvent
        const event = new CustomEvent('barberSelected', { detail: { barberId } });
        document.dispatchEvent(event);
    }

    function updateActiveBarber() {
        if (selectedBarberId === 'any') {
            // 'Любой мастер' по умолчанию
            activeBarberCard.querySelector('.barber-name').textContent = 'Любой мастер';
            activeBarberCard.querySelector('.barber-description').textContent = 'Описание или слоган';
            activeBarberCard.querySelector('.barber-avatar').src = '/static/salons/img/default-avatar.png';
        } else {
            // Находим выбранного барбера
            const selectedCard = document.querySelector(`.barber-card[data-barber-id="${selectedBarberId}"]`);
            if (selectedCard) {
                activeBarberCard.querySelector('.barber-name').textContent = selectedCard.querySelector('.barber-name').textContent;
                activeBarberCard.querySelector('.barber-description').textContent = selectedCard.querySelector('.barber-description').textContent;
                activeBarberCard.querySelector('.barber-avatar').src = selectedCard.querySelector('.barber-avatar').src;
            }
        }
    }

    function updateBarberList() {
        // Скрываем активного барбера из списка
        allBarberCards.forEach(card => {
            const barberId = card.getAttribute('data-barber-id');
            if (barberId === selectedBarberId) {
                card.style.display = 'none';
            } else {
                card.style.display = 'flex';
            }
        });
    }

    // Начальное обновление активного барбера и списка
    updateActiveBarber();
    updateBarberList();
});
