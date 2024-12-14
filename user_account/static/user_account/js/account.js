
function toggleSidebar() {
    var sidebar = document.querySelector('.sidebar');
    var overlay = document.querySelector('.overlay');
    sidebar.classList.toggle('active');
    overlay.classList.toggle('active');
}


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