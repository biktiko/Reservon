// account/static/account/js/edit_bookings.js
document.addEventListener('DOMContentLoaded', function() {
    var formsetContainer = document.getElementById('formset-container');
    var totalFormsInput = document.getElementById('id_barber_services-TOTAL_FORMS');
    var addFormButton = document.getElementById('add-form-button');
    var refreshDataButton = document.getElementById('refresh-data-button'); // Новая кнопка "Обновить данные"
    var formIndex = parseInt(totalFormsInput.value);
    var totalDuration = window.totalDuration || 0;
    var languageCode = window.languageCode || 'ru';

    initializeSelect2();
    initializeFlatpickr();

    // Обновляем длительность и время окончания для всех существующих форм
    var forms = document.querySelectorAll('.barber-service-form');
    forms.forEach(function(form) {
        updateDurationDisplay(form);
    });

    // Функция инициализации Select2
    function initializeSelect2() {
        $('.services-select').select2({
            width: '100%',
            placeholder: 'Выберите услуги',
            allowClear: true,
        });

        $('.barber-select').select2({
            width: '100%',
            placeholder: 'Выберите мастера',
            allowClear: true,
        });
    }

    // Функция инициализации Flatpickr
    function initializeFlatpickr() {
        // Инициализация для всех полей времени начала
        $('.start-datetime').each(function() {
            flatpickr(this, {
                enableTime: true,
                dateFormat: "d.m.Y H:i",
                locale: languageCode,
                onChange: function(selectedDates, dateStr, instance) {
                    var form = instance.input.closest('.barber-service-form');
                    updateDurationDisplay(form);
                    updateBookingTime();
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
                    updateDurationDisplay(form);
                    updateBookingTime();
                }
            });
        });
    }

    // Функция обновления отображения длительности при изменении времени
    function updateDurationDisplay(form) {
        var startInput = form.querySelector('.start-datetime');
        var endInput = form.querySelector('.end-datetime');
        var startTime = startInput._flatpickr.selectedDates[0];
        var endTime = endInput._flatpickr.selectedDates[0];

        if (startTime && endTime) {
            var duration = (endTime - startTime) / 60000; // Длительность в минутах
            if (duration < 0) duration = 0;
            form.dataset.duration = duration;

            var durationDisplay = form.querySelector('.category-summary .duration');
            if (durationDisplay) {
                durationDisplay.textContent = 'Длительность: ' + duration.toFixed(0) + ' минут';
            }

            // Обновляем общую информацию
            updateBookingSummary();
        }
    }

    // Функция обновления общего времени бронирования
    function updateBookingTime() {
        var earliestStart = null;
        var latestEnd = null;
    
        var forms = document.querySelectorAll('.barber-service-form');
    
        forms.forEach(function(form) {
            var startInput = form.querySelector('.start-datetime');
            var endInput = form.querySelector('.end-datetime');
    
            var startTime = startInput._flatpickr.selectedDates[0];
            var endTime = endInput._flatpickr.selectedDates[0];
    
            if (startTime && (!earliestStart || startTime < earliestStart)) {
                earliestStart = startTime;
            }
            if (endTime && (!latestEnd || endTime > latestEnd)) {
                latestEnd = endTime;
            }
        });
    
        if (earliestStart && latestEnd) {
            var bookingTimeElem = document.querySelector('.booking-time');
            var startStr = flatpickr.formatDate(earliestStart, 'd.m.Y H:i');
            var endStr = flatpickr.formatDate(latestEnd, 'H:i');
    
            bookingTimeElem.textContent = startStr + ' - ' + endStr;
        }
    }
    

    // Функция обновления общей информации о бронировании
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

        // Обновляем отображение общей длительности и цены
        document.getElementById('total-duration').textContent = totalDuration.toFixed(0) + ' минут';
        document.getElementById('total-price').textContent = totalPrice.toFixed(0) + ' ֏';
    }

    // Обработчик события для добавления новой формы
    if (addFormButton) {
        addFormButton.addEventListener('click', function(e) {
            e.preventDefault();
            var formCount = parseInt(totalFormsInput.value);
            var newFormHtml = document.getElementById('empty-form').innerHTML.replace(/__prefix__/g, formCount);
    
            // Вставляем новую форму в контейнер
            $('#formset-container').append(newFormHtml);
    
            // Увеличиваем индекс форм
            formIndex++;
            totalFormsInput.value = formIndex;
    
            // Переинициализируем Select2 и Flatpickr для новых элементов
            initializeSelect2();
            initializeFlatpickr();
    
            // Обновляем индексы форм
            updateFormIndexes();
        });
    }
    

    // Функция для обновления имён и идентификаторов полей
    function updateFormIndexes() {
        var forms = formsetContainer.querySelectorAll('.barber-service-form');
        forms.forEach(function(form, index) {
            form.querySelectorAll('input, select, textarea').forEach(function(input) {
                if (input.name) {
                    var name = input.name.replace(/barber_services-\d+-/, 'barber_services-' + index + '-');
                    var id = 'id_' + name;
                    input.name = name;
                    input.id = id;
                }
            });
        });
        // Обновляем общее количество форм
        totalFormsInput.value = forms.length;
    }

    // Обработчик события для удаления формы
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

    // Обработчик события для кнопки "Обновить данные" на всё бронирование
    if (refreshDataButton) {
        refreshDataButton.addEventListener('click', function(e) {
            e.preventDefault();
            updateAllCategoriesData();
        });
    }

    // Функция для обновления данных всех категорий (цен)
    function updateAllCategoriesData() {
        var forms = document.querySelectorAll('.barber-service-form');
        var requests = [];
    
        forms.forEach(function(form) {
            var servicesSelect = form.querySelector('.services-select');
            var selectedServices = $(servicesSelect).val();
    
            if (selectedServices && selectedServices.length > 0) {
                // Создаём запрос на получение цены выбранных услуг
                var request = $.ajax({
                    url: window.getServicesDurationAndPriceUrl,
                    data: {
                        'service_ids': selectedServices.join(',')
                    },
                    success: function(data) {
                        if (data.total_price) {
                            form.dataset.price = data.total_price;
    
                            // Обновляем отображение цены категории
                            var priceDisplay = form.querySelector('.category-summary .price');
                            if (priceDisplay) {
                                priceDisplay.textContent = 'Цена: ' + data.total_price + ' ֏';
                            }
                        }
                    }
                });
    
                requests.push(request);
            } else {
                form.dataset.price = '0';
    
                // Обновляем отображение цены категории
                var priceDisplay = form.querySelector('.category-summary .price');
                if (priceDisplay) {
                    priceDisplay.textContent = 'Цена: 0 ֏';
                }
            }
    
            // Обновляем длительность категории
            updateDurationDisplay(form);
        });
    
        // После завершения всех запросов обновляем общую информацию
        $.when.apply($, requests).done(function() {
            updateBookingSummary();
            updateBookingTime();
            updateInvolvedBarbers();
        });
    }

    function updateInvolvedBarbers() {
        var barbersSet = new Set();
        var forms = document.querySelectorAll('.barber-service-form');
    
        forms.forEach(function(form) {
            var barberSelect = form.querySelector('.barber-select');
            var selectedBarberId = barberSelect.value;
            if (selectedBarberId) {
                barbersSet.add(selectedBarberId);
            }
        });
    
        // Теперь обновляем отображение
        var barbersRow = document.querySelector('.barbers-row');
        barbersRow.innerHTML = '';
    
        barbersSet.forEach(function(barberId) {
            var barberOption = document.querySelector('.barber-select option[value="' + barberId + '"]');
            var barberName = barberOption.textContent;
            var barberAvatar = barberOption.getAttribute('data-avatar-url') || '/static/salons/img/default-avatar.png';
    
            // Убираем название салона из имени мастера (если есть)
            barberName = barberName.replace(/\s*\(.*\)$/, '');
    
            var barberItem = document.createElement('div');
            barberItem.classList.add('barber-item');
    
            var barberImg = document.createElement('img');
            barberImg.src = barberAvatar;
            barberImg.alt = barberName;
            barberImg.classList.add('barber-avatar-summary');
    
            var barberSpan = document.createElement('span');
            barberSpan.classList.add('barber-name');
            barberSpan.textContent = barberName;
    
            barberItem.appendChild(barberImg);
            barberItem.appendChild(barberSpan);
    
            barbersRow.appendChild(barberItem);
        });
    
        // Если мастера не выбраны
        if (barbersSet.size === 0) {
            barbersRow.innerHTML = '<p>Нет задействованных мастеров</p>';
        }
    }
    
    

    // Подтверждение перед удалением бронирования
    var deleteForm = document.getElementById('delete-booking-form');
    if (deleteForm) {
        var deleteButton = deleteForm.querySelector('.delete-button');

        if (deleteButton) {
            deleteButton.addEventListener('click', function(e) {
                e.preventDefault();
                var confirmDelete = confirm('Вы уверены, что хотите удалить это бронирование?');
                if (confirmDelete) {
                    deleteForm.submit();
                }
            });
        }
    }
});
