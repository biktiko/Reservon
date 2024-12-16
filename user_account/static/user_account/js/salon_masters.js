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
            fetch(`/user_account/barbers/${barberId}/edit_field/?field=${field}`,{
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
            fetch(`/user_account/barbers/${barberId}/edit_photo/`,{
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
            fetch(`/user_account/barbers/${barberId}/edit_schedule/?day=${day}`,{
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
        // Проверяем, есть ли forms-container
        if (document.getElementById('forms-container')) {
            removeEmptyForms();
        }
        submitForm();
    });

    function submitForm() {
        const form = document.getElementById('edit-form');
    
        // if (!form) return; // Нет формы - нет сабмита
        var formData = new FormData(form);
        fetch(form.action, {
            method: 'POST',
            headers: {
                'X-Requested-With':'XMLHttpRequest',
                'X-CSRFToken':csrftoken
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
                if (errorContainer) {
                    errorContainer.innerHTML = '';
                    if (Array.isArray(data.errors)) {
                        data.errors.forEach(function(formErrors, formIndex) {
                            for (var fieldName in formErrors) {
                                formErrors[fieldName].forEach(function(err) {
                                    errorContainer.innerHTML += `<div class="alert alert-danger">Форма ${formIndex+1}, поле ${fieldName}: ${err}</div>`;
                                });
                            }
                        });
                    } else {
                        for(var field in data.errors){
                            data.errors[field].forEach(function(err){
                                errorContainer.innerHTML += `<div class="alert alert-danger">${err}</div>`;
                            });
                        }
                    }
                }
            }
        });
    }

    // Обработка переключателей статуса
    document.addEventListener('change', function(e) {
        if (e.target && e.target.closest('.custom-switch') && e.target.type === 'checkbox') {
            var switchInput = e.target;
            var statusLabel = switchInput.closest('.form-group')?.querySelector('.status-label');
            if (statusLabel) {
                if(switchInput.checked) {
                    statusLabel.textContent = 'Занят';
                    statusLabel.style.color = '#28a745'; // Зеленый цвет
                } else {
                    statusLabel.textContent = 'Свободен';
                    statusLabel.style.color = '#dc3545'; // Красный цвет
                }
            }
        }
    });

    document.getElementById('editModal').addEventListener('click', function(e) {
        const formsContainer = document.getElementById('forms-container');
        if (e.target && e.target.id === 'mark-holiday-button') {
            
            if (formsContainer) {
                formsContainer.innerHTML = '';
                const totalFormsInput = document.getElementById('id_form-TOTAL_FORMS');
                if (totalFormsInput) totalFormsInput.value = 0;
            }
        
            const form = document.getElementById('edit-form');
            const day = formsContainer.dataset.day; 
            const hiddenDayInput = document.createElement('input');
            hiddenDayInput.type = 'hidden';
            hiddenDayInput.name = 'day';
            hiddenDayInput.value = day;
            form.appendChild(hiddenDayInput);
            submitForm(); 
        }
             
        if (e.target && e.target.id === 'add-time-button') {
            addNewForm();
        }
    });

    function addNewForm() {
        const formsContainer = document.getElementById('forms-container');
        if (!formsContainer) return;
        const totalFormsInput = document.getElementById('id_form-TOTAL_FORMS');
        let formIndex = parseInt(totalFormsInput.value);

        const newFormHtml = `
          <div class="single-form">
            <input type="hidden" name="form-${formIndex}-id" id="id_form-${formIndex}-id">
            <div class="form-row">
              <div class="col-half">
                <div class="form-group">
                  <label for="id_form-${formIndex}-start_time">Начало:</label>
                  <input type="time" name="form-${formIndex}-start_time" class="form-control" id="id_form-${formIndex}-start_time">
                </div>
              </div>
              <div class="col-half">
                <div class="form-group">
                  <label for="id_form-${formIndex}-end_time">Конец:</label>
                  <input type="time" name="form-${formIndex}-end_time" class="form-control" id="id_form-${formIndex}-end_time">
                </div>
              </div>
            </div>
            <div class="form-group" style="margin-top:10px;">
              <div class="switch-container">
                <span class="switch-label-left">Свободен</span>
                <label class="switch">
                  <input type="checkbox" name="form-${formIndex}-is_available" id="id_form-${formIndex}-is_available" checked>
                  <span class="slider"></span>
                </label>
                <span class="switch-label-right">Занят</span>
              </div>
            </div>
            <hr>
          </div>
        `;
        formsContainer.insertAdjacentHTML('beforeend', newFormHtml);
        totalFormsInput.value = formIndex + 1;
    }

    function removeEmptyForms() {
        const formsContainer = document.getElementById('forms-container');
        if (!formsContainer) return;
        const totalFormsInput = document.getElementById('id_form-TOTAL_FORMS');
        let total = parseInt(totalFormsInput.value);

        let forms = formsContainer.querySelectorAll('.single-form');
        let index = 0;
        forms.forEach((f,originalIndex) => {
            let start = f.querySelector(`[name="form-${originalIndex}-start_time"]`)?.value;
            let end = f.querySelector(`[name="form-${originalIndex}-end_time"]`)?.value;
            if((!start || start.trim() === '') && (!end || end.trim() === '')){
                // пустая форма - удаляем
                f.remove();
                total -=1;
            } else {
                // обновляем индексы форм
                f.querySelectorAll('input, select, textarea').forEach(inp => {
                    inp.name = inp.name.replace(`form-${originalIndex}-`, `form-${index}-`);
                    inp.id = inp.id.replace(`form-${originalIndex}-`, `form-${index}-`);
                });
                index++;
            }
        });
        totalFormsInput.value = index;
    }

});
