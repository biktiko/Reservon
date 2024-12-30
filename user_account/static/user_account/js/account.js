function toggleSidebar() {
    const sidebar = document.querySelector('.sidebar');
    if (!sidebar) return;
    sidebar.classList.toggle('open');
}

function closeSidebar() {
    const sidebar = document.querySelector('.sidebar');
    if (!sidebar) return;
    sidebar.classList.remove('open');
}

// Пример использования:
document.addEventListener('DOMContentLoaded', () => {
    const menuButton = document.querySelector('.menu-button');
    const closeButton = document.getElementById('close-sidebar-button');

    // Открыть/закрыть
    if (menuButton) {
        menuButton.addEventListener('click', () => {
            toggleSidebar();
        });
    }

    // Закрыть
    if (closeButton) {
        closeButton.addEventListener('click', () => {
            closeSidebar();
        });
    }
});


// Скрипт для открытия и закрытия модального окна
document.addEventListener('DOMContentLoaded', function() {
    var modal = document.getElementById('salon-modal');
    var btn = document.getElementById('change-salon-button');
    var span = document.getElementsByClassName('close-button')[0];

    if(btn) {
        btn.onclick = function() {
            modal.style.display = 'block';
        }
    }

    if(span) {
        span.onclick = function() {
            modal.style.display = 'none';
        }
    }

    window.onclick = function(event) {
        if(event.target == modal) {
            modal.style.display = 'none';
        }
    }
});