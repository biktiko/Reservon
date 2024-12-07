function getCookie(name) {
    var cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        var cookies = document.cookie.split(';');
        for (var i=0; i<cookies.length; i++) {
            var cookie = cookies[i].trim();
            if (cookie.substring(0,name.length+1)===(name+'=')) {
                cookieValue=decodeURIComponent(cookie.substring(name.length+1));
                break;
            }
        }
    }
    return cookieValue;
}
var csrftoken = getCookie('csrftoken');

document.addEventListener('DOMContentLoaded', function(){
    // Делает карточку мастера кликабельной
    document.querySelectorAll('.barber-small-card').forEach(function(card){
        card.addEventListener('click', function(){
            var url = this.dataset.url;
            if(url) window.location.href = url;
        });
    });

    // Редактирование поля
    document.querySelectorAll('.editable-field').forEach(function(el){
        el.style.cursor = 'pointer';
        el.addEventListener('click', function(event){
            event.stopPropagation();
            var barberId = this.dataset.barberId;
            var field = this.dataset.field;
            fetch(`/account/barbers/${barberId}/edit_field/?field=${field}`,{
                headers: {'X-Requested-With':'XMLHttpRequest'}
            })
            .then(r => r.json())
            .then(data => {
                if(data.success){
                    document.getElementById('editModal').innerHTML = data.html;
                    $('#editModal').modal('show');
                } else {
                    alert('Ошибка загрузки формы редактирования.');
                }
            });
        });
    });

    // Редактирование фото
    document.querySelectorAll('.editable-photo').forEach(function(element){
        element.addEventListener('click', function(e){
            e.stopPropagation();
            var barberId = this.dataset.barberId;
            fetch(`/account/barbers/${barberId}/edit_photo/`,{
                headers: {'X-Requested-With':'XMLHttpRequest'}
            })
            .then(r => r.json())
            .then(data => {
                if(data.success){
                    document.getElementById('editModal').innerHTML = data.html;
                    $('#editModal').modal('show');
                } else {
                    alert('Ошибка загрузки формы редактирования фото.');
                }
            });
        });
    });

    // Редактирование расписания
    document.querySelectorAll('.editable-schedule').forEach(function(element){
        element.addEventListener('click', function(e){
            e.stopPropagation();
            var barberId = this.dataset.barberId;
            var day = this.dataset.day;
            fetch(`/account/barbers/${barberId}/edit_schedule/?day=${day}`,{
                headers: {'X-Requested-With':'XMLHttpRequest'}
            })
            .then(r => r.json())
            .then(data => {
                if(data.success){
                    document.getElementById('editModal').innerHTML = data.html;
                    $('#editModal').modal('show');
                } else {
                    alert('Ошибка загрузки формы редактирования расписания.');
                }
            });
        });
    });

    // Обработка отправки формы внутри модального окна
    document.getElementById('editModal').addEventListener('submit', function(e){
        e.preventDefault();
        var form = e.target;
        var formData = new FormData(form);
        
        fetch(form.action, {
            method: 'POST',
            headers: {
                'X-Requested-With':'XMLHttpRequest',
                'X-CSRFToken': csrftoken
            },
            body: formData
        })
        .then(r => r.json())
        .then(data => {
            if(data.success){
                $('#editModal').modal('hide');
                location.reload();
            } else {
                var errorContainer = document.getElementById('form-errors');
                errorContainer.innerHTML = '';
                if (Array.isArray(data.errors)) {
                    // Для formset ошибок
                    data.errors.forEach(function(formErrors, formIndex) {
                        for (var fieldName in formErrors) {
                            formErrors[fieldName].forEach(function(err) {
                                errorContainer.innerHTML += `<div class="alert alert-danger">Форма ${formIndex+1}, поле ${fieldName}: ${err}</div>`;
                            });
                        }
                    });
                } else {
                    // Для обычных форм
                    for(var field in data.errors){
                        data.errors[field].forEach(function(err){
                            errorContainer.innerHTML += `<div class="alert alert-danger">${err}</div>`;
                        });
                    }
                }
            }
        });
    });

    // Обработка переключателей статуса
    document.addEventListener('change', function(e) {
        if (e.target && e.target.closest('.custom-switch') && e.target.type === 'checkbox') {
            var switchInput = e.target;
            var statusLabel = switchInput.closest('.form-group').querySelector('.status-label');
            if(switchInput.checked) {
                statusLabel.textContent = 'Занят';
                statusLabel.style.color = '#28a745'; // Зеленый цвет
            } else {
                statusLabel.textContent = 'Свободен';
                statusLabel.style.color = '#dc3545'; // Красный цвет
            }
        }
    });

    
    $('#editModal').on('hidden.bs.modal', function () {
        console.log(this)
        $(this).find('.modal-content').empty();
    });
    
});
