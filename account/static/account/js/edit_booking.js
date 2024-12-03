// account/static/account/js/edit_bookings.js
document.addEventListener('DOMContentLoaded', function() {
    var formsetContainer = document.getElementById('formset-container');
    var totalFormsInput = document.getElementById('id_barber_services-TOTAL_FORMS');
    var addFormButton = document.getElementById('add-form-button');
    var formIndex = parseInt(totalFormsInput.value);
    var totalDuration = window.totalDuration || 0;
    var languageCode = window.languageCode || 'ru';

    initializeSelect2();
    initializeFlatpickr();

    // Обновляем время окончания для всех существующих форм
    var forms = document.querySelectorAll('.barber-service-form');
    forms.forEach(function(form) {
        updateEndTime(form);
    });

    // Function to initialize Select2
    function initializeSelect2() {
        $('.services-select').select2({
            width: '100%',
            placeholder: 'Выберите услуги',
            allowClear: true,
        }).on('change', function() {
            var form = $(this).closest('.barber-service-form')[0];
            var selectedServices = $(this).val();

            if (selectedServices && selectedServices.length > 0) {
                // Запрос на получение длительности и цены
                $.ajax({
                    url: '{% url "get_services_duration_and_price" %}',
                    data: {
                        'service_ids': selectedServices.join(',')
                    },
                    success: function(data) {
                        if (data.total_duration) {
                            // Обновляем длительность в data-атрибуте формы
                            form.dataset.duration = data.total_duration;

                            // Обновляем отображение длительности
                            var durationDisplay = form.querySelector('.category-summary .duration');
                            if (durationDisplay) {
                                durationDisplay.textContent = 'Длительность: ' + data.total_duration + ' минут';
                            }

                            // Пересчитываем время окончания
                            var startInput = form.querySelector('.start-datetime');
                            var endInput = form.querySelector('.end-datetime');
                            var startTime = startInput._flatpickr.selectedDates[0];
                            if (startTime) {
                                var endTime = new Date(startTime.getTime() + data.total_duration * 60000);
                                endInput._flatpickr.setDate(endTime);
                            }
                        }

                        if (data.total_price) {
                            // Обновляем цену в data-атрибуте формы
                            form.dataset.price = data.total_price;

                            // Обновляем отображение цены
                            var priceDisplay = form.querySelector('.category-summary .price');
                            if (priceDisplay) {
                                priceDisplay.textContent = 'Цена: ' + data.total_price + ' ₽';
                            }
                        }

                        // Обновляем общую информацию
                        updateBookingSummary();
                    }
                });
            } else {
                form.dataset.duration = '0';
                form.dataset.price = '0';

                // Обновляем отображение длительности и цены
                var durationDisplay = form.querySelector('.category-summary .duration');
                if (durationDisplay) {
                    durationDisplay.textContent = 'Длительность: 0 минут';
                }
                var priceDisplay = form.querySelector('.category-summary .price');
                if (priceDisplay) {
                    priceDisplay.textContent = 'Цена: 0 ₽';
                }

                // Обновляем общую информацию
                updateBookingSummary();
            }
        });

        $('.barber-select').select2({
            width: '100%',
            placeholder: 'Выберите мастера',
            allowClear: true,
        });
    }

    // Function to initialize Flatpickr
    function initializeFlatpickr() {
        // Инициализация для всех полей времени начала
        $('.start-datetime').each(function() {
            flatpickr(this, {
                enableTime: true,
                dateFormat: "d.m.Y H:i",
                locale: languageCode,
                onChange: function(selectedDates, dateStr, instance) {
                    var form = instance.input.closest('.barber-service-form');
                    var duration = parseFloat(form.dataset.duration) || 0;
                    var startTime = selectedDates[0];
                    var endInput = form.querySelector('.end-datetime');

                    if (startTime && duration && endInput && endInput._flatpickr) {
                        var endTime = new Date(startTime.getTime() + duration * 60000);
                        endInput._flatpickr.setDate(endTime);
                    }
                }
            });
        });

        // Инициализация для всех полей времени окончания
        $('.end-datetime').each(function() {
            flatpickr(this, {
                enableTime: true,
                dateFormat: "d.m.Y H:i",
                locale: languageCode,
                onChange: function(selectedDates, dateStr, instance) {
                    var form = instance.input.closest('.barber-service-form');
                    var duration = parseFloat(form.dataset.duration) || 0;
                    var endTime = selectedDates[0];
                    var startInput = form.querySelector('.start-datetime');

                    if (endTime && duration && startInput && startInput._flatpickr) {
                        var startTime = new Date(endTime.getTime() - duration * 60000);
                        startInput._flatpickr.setDate(startTime);
                    }
                }
            });
        });
    }

    // Function to update end time when start time changes
    function updateEndTime(form) {
        var startInput = form.querySelector('.start-datetime');
        var endInput = form.querySelector('.end-datetime');

        if (startInput && endInput) {
            var duration = parseFloat(form.dataset.duration) || 0;
            var startTime = startInput._flatpickr.selectedDates[0];

            if (startTime && duration) {
                var endTime = new Date(startTime.getTime() + duration * 60000);
                endInput._flatpickr.setDate(endTime);
            }
        }
    }

    // Function to update booking summary
    function updateBookingSummary() {
        var totalDuration = 0;
        var totalPrice = 0;

        var forms = document.querySelectorAll('.barber-service-form');

        forms.forEach(function(form) {
            var duration = parseFloat(form.dataset.duration) || 0;
            totalDuration += duration;

            var price = parseFloat(form.dataset.price) || 0;
            totalPrice += price;
        });

        // Update the summary display
        document.getElementById('total-duration').textContent = totalDuration + ' минут';
        document.getElementById('total-price').textContent = totalPrice + ' ₽';
    }

    // Event listener for adding new form
    if (addFormButton) {
        addFormButton.addEventListener('click', function(e) {
            e.preventDefault();
            var newFormHtml = document.getElementById('empty-form').innerHTML.replace(/__prefix__/g, formIndex);
            var newForm = document.createElement('div');
            newForm.innerHTML = newFormHtml;
            newForm.classList.add('barber-service-form');
            newForm.dataset.duration = '0';
            newForm.dataset.price = '0';
    
            // Append the new form
            formsetContainer.appendChild(newForm);
    
            // Increment the total forms count
            totalFormsInput.value = ++formIndex;
    
            // Re-initialize Select2 and Flatpickr for new elements
            initializeSelect2();
            initializeFlatpickr();
    
            // Update end time for the new form
            updateEndTime(newForm);
            updateBookingSummary();
    
            // Обновляем имена и идентификаторы полей в новой форме
            updateFormIndexes();
        });
    }

    // Функция для обновления имён и идентификаторов полей
    function updateFormIndexes() {
        var forms = formsetContainer.querySelectorAll('.barber-service-form');
        forms.forEach(function(form, index) {
            form.querySelectorAll('input, select, textarea').forEach(function(input) {
                if (input.name) {
                    input.name = input.name.replace(/barber_services-\d+-/, 'barber_services-' + index + '-');
                    input.id = 'id_' + input.name;
                }
            });
        });
        // Обновляем общее количество форм
        totalFormsInput.value = forms.length;
    }


    // Event listener for removing a form
    formsetContainer.addEventListener('click', function(e) {
        if (e.target && (e.target.classList.contains('remove-form-button') || e.target.closest('.remove-form-button'))) {
            e.preventDefault();
            var button = e.target.closest('.remove-form-button');
            var form = button.closest('.barber-service-form');
            var deleteInput = form.querySelector('input[name$="-DELETE"]');
            if (deleteInput) {
                deleteInput.checked = true;
            }
            form.style.display = 'none';
    
            // Обновляем общую информацию
            updateBookingSummary();
    
            // Обновляем индексы форм
            updateFormIndexes();
        }
    });

    // Confirmation before deleting booking
    var deleteForm = document.getElementById('delete-booking-form');
    if (deleteForm) {
        var deleteButton = deleteForm.querySelector('.delete-button');

        deleteButton.addEventListener('click', function(e) {
            e.preventDefault();
            var confirmDelete = confirm('Вы уверены, что хотите удалить это бронирование?');
            if (confirmDelete) {
                deleteForm.submit();
            }
        });
    }
});
