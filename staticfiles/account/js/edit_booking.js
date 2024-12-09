// account/static/account/js/edit_bookings.js
document.addEventListener('DOMContentLoaded', function() {
    var formsetContainer = document.getElementById('formset-container');
    var totalFormsInput = document.getElementById('id_barber_services-TOTAL_FORMS');
    var addFormButton = document.getElementById('add-form-button');
    var refreshDataButton = document.getElementById('refresh-data-button'); // Кнопка "Обновить данные"
    var formIndex = parseInt(totalFormsInput.value);
    var languageCode = window.languageCode || 'ru';

    initializeSelect2(formsetContainer);
    initializeFlatpickr(formsetContainer);

    // Обновляем длительность и время окончания для всех существующих форм
    var forms = document.querySelectorAll('.barber-service-form');
    forms.forEach(function(form) {
        updateDurationDisplay(form);
        updateEndTime(form);
    });

    // Функция инициализации Select2
    function initializeSelect2(context) {
        context = context || document;

        $(context).find('.services-select').select2({
            width: '100%',
            placeholder: 'Выберите услуги',
            allowClear: true,
        });

        $(context).find('.barber-select').select2({
            width: '100%',
            placeholder: 'Выберите мастера',
            allowClear: true,
            templateResult: formatBarberOption,
            templateSelection: formatBarberOption,
        });
    }

    // Функция для форматирования опций Select2 с аватарками мастеров
    function formatBarberOption(option) {
        if (!option.id) {
            return option.text;
        }
        var imgSrc = $(option.element).data('avatar-url') || '/static/salons/img/default-avatar.png';
        var barberName = option.text; // Убедитесь, что в `__str__` модели Barber только имя
        var $option = $('<span><img src="' + imgSrc + '" class="barber-avatar-select2" /> ' + barberName + '</span>');
        return $option;
    }

     // Функция инициализации Flatpickr
     function initializeFlatpickr(context) {
        context = context || document;

        // Инициализация для всех полей времени начала
        $(context).find('.start-datetime').flatpickr({
            enableTime: true,
            dateFormat: "d.m.Y H:i",
            locale: languageCode,
            onChange: function(selectedDates, dateStr, instance) {
                var form = instance.input.closest('.barber-service-form');
                updateDurationDisplay(form);
                updateBookingTime();
            }
        });

        // Инициализация для всех полей времени окончания
        $(context).find('.end-datetime').flatpickr({
            enableTime: true,
            dateFormat: "d.m.Y H:i",
            locale: languageCode,
            onChange: function(selectedDates, dateStr, instance) {
                var form = instance.input.closest('.barber-service-form');
                updateDurationDisplay(form);
                updateBookingTime();
            }
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

    // Функция обновления времени окончания на основе времени начала и длительности
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

     // Обработчик события для добавления новой формы
     if (addFormButton) {
        addFormButton.addEventListener('click', function(e) {
            e.preventDefault();
            var formCount = parseInt(totalFormsInput.value);
            var newFormHtml = document.getElementById('empty-form').innerHTML.replace(/__prefix__/g, formCount);

            console.log('Добавляем форму:', newFormHtml);

            // Создаём новый <div class="barber-service-form">
            var newForm = document.createElement('div');
            newForm.classList.add('barber-service-form');
            newForm.dataset.duration = '0';
            newForm.dataset.price = '0';
            newForm.innerHTML = newFormHtml;

            console.log('Форма добавлена:', newForm);

            // Добавляем новую форму в контейнер
            formsetContainer.appendChild(newForm);

            // Увеличиваем индекс форм
            formIndex++;
            totalFormsInput.value = formIndex;

            // Инициализируем Select2 и Flatpickr только для новых элементов
            initializeSelect2(newForm);
            initializeFlatpickr(newForm);
            console.log('Инициализирован Select2 и Flatpickr для новой формы.');

            // Обновляем индексы форм
            updateFormIndexes();
            console.log('Обновлены индексы форм.');
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
            updateBookingTime();
            updateInvolvedBarbers();

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

    // Функция для обновления списка задействованных мастеров
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

        // Обновляем отображение
        var barbersRow = document.querySelector('.barbers-row');
        barbersRow.innerHTML = '';

        barbersSet.forEach(function(barberId) {
            var barberOption = document.querySelector('.barber-select option[value="' + barberId + '"]');
            if (barberOption) {
                var barberName = barberOption.textContent;
                var barberAvatar = barberOption.getAttribute('data-avatar-url') || '/static/salons/img/default-avatar.png';

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
            }
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
