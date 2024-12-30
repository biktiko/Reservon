function toggleSidebar() {
    const sidebar = document.querySelector('.sidebar');
    if (!sidebar) return;
    sidebar.classList.toggle('open');
    console.log('toggleSidebar: ', sidebar.classList.contains('open') ? 'Opened' : 'Closed');
}

function closeSidebar() {
    const sidebar = document.querySelector('.sidebar');
    if (!sidebar) return;
    sidebar.classList.remove('open');
    console.log('closeSidebar: Closed');
}

document.addEventListener('DOMContentLoaded', function() {
    const menuButton = document.querySelector('.menu-button');
    const closeButton = document.getElementById('close-sidebar-button');

    // Обработчик для кнопки открытия Sidebar
    if (menuButton) {
        menuButton.addEventListener('click', function(e) {
            e.preventDefault(); // Предотвращаем переход по ссылке, если используется <a>
            console.log('Кнопка "Меню" нажата');
            toggleSidebar();
        });
    }

    // Обработчик для кнопки закрытия Sidebar
    if (closeButton) {
        closeButton.addEventListener('click', function(e) {
            e.preventDefault(); // Предотвращаем переход по ссылке
            console.log('Кнопка "Закрыть" нажата');
            closeSidebar();
        });
    }

    // Закрытие sidebar при нажатии на ссылку внутри меню (только на мобильных)
    document.querySelectorAll('.sidebar ul li a').forEach(function(link) {
        link.addEventListener('click', function() {
            if (window.innerWidth <= 768) {
                closeSidebar();
            }
        });
    });

    // Опционально: Закрытие Sidebar при нажатии на клавишу ESC
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            closeSidebar();
        }
    });
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