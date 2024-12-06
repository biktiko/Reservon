// static/account/js/salon_masters.js

function getCookie(name) {
    var cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        var cookies = document.cookie.split(';');
        for (var i = 0; i < cookies.length; i++) {
            var cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}
var csrftoken = getCookie('csrftoken');

document.addEventListener('DOMContentLoaded', function() {
    // Редактирование поля (имя, описание, категории)
    
    document.querySelectorAll('.editable-field').forEach(function(el) {
        el.addEventListener('click', function() {
            var barberId = this.dataset.barberId;
            var field = this.dataset.field;
            fetch(`/account/barbers/${barberId}/edit_field/?field=${field}`, {
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    document.getElementById('editModal').innerHTML = data.html;
                    $('#editModal').modal('show');
                } else {
                    alert('Ошибка загрузки формы редактирования.');
                }
            });
        });
    });

    // Редактирование фотографии
    document.querySelectorAll('.editable-photo').forEach(function(element) {
        element.addEventListener('click', function() {
            var barberId = this.dataset.barberId; // Обязательно объявить здесь barberId
            fetch(`/account/barbers/${barberId}/edit_photo/`, {
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    document.getElementById('editModal').innerHTML = data.html;
                    $('#editModal').modal('show');
                } else {
                    alert('Ошибка загрузки формы редактирования фото.');
                }
            });
        });
    });
    
    // Редактирование расписания
    document.querySelectorAll('.editable-schedule').forEach(function(element) {
        element.addEventListener('click', function() {
            var barberId = this.dataset.barberId;
            var day = this.dataset.day;

            fetch(`/account/barbers/${barberId}/edit_schedule/?day=${day}`)
                .then(response => response.json())
                .then(data => {
                    document.getElementById('editModal').innerHTML = data.html;
                    $('#editModal').modal('show');
                });
        });
    });

    // Обработка отправки форм внутри модального окна
    document.getElementById('editModal').addEventListener('submit', function(e) {
        e.preventDefault();
        var form = e.target;
        var formData = new FormData(form);
    
        fetch(form.action, {
            method: 'POST',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': csrftoken
            },
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                location.reload();
            } else {
                var errorContainer = document.getElementById('form-errors');
                errorContainer.innerHTML = '';
                for (var field in data.errors) {
                    data.errors[field].forEach(function(err) {
                        errorContainer.innerHTML += `<div class="alert alert-danger">${err}</div>`;
                    });
                }
            }
        });
    });
});
