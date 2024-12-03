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
    updateEndTime();

    // Function to initialize Select2
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

    // Function to initialize Flatpickr
    function initializeFlatpickr() {
        flatpickr('.datetime-input', {
            enableTime: true,
            dateFormat: "d.m.Y H:i",
            locale: languageCode,
        });
    }

    // Function to update end time when start time changes
    function updateEndTime() {
        var startTimeInput = document.querySelector('#id_start_datetime');
        var endTimeDisplay = document.getElementById('end-time-display');

        if (startTimeInput && endTimeDisplay) {
            flatpickr(startTimeInput, {
                enableTime: true,
                dateFormat: 'd.m.Y H:i',
                locale: languageCode,
                onChange: function(selectedDates, dateStr, instance) {
                    var startTime = selectedDates[0];
                    if (!startTime) {
                        return;
                    }
                    var endTime = new Date(startTime.getTime() + totalDuration * 60000);
                    var formattedEndTime = flatpickr.formatDate(endTime, 'd.m.Y H:i');
                    endTimeDisplay.textContent = formattedEndTime;
                }
            });
        }
    }

    // Event listener for adding new form
    addFormButton.addEventListener('click', function(e) {
        console.log('add test');
        
        e.preventDefault();
        var newFormHtml = document.getElementById('empty-form').innerHTML.replace(/__prefix__/g, formIndex);
        var newForm = document.createElement('div');

        // var newForm = formsetContainer.firstElementChild.cloneNode(true);

        // Update the form index in the new form
        var regex = new RegExp('barber_services-(\\d+)-', 'g');
        newForm.innerHTML = newForm.innerHTML.replace(regex, 'barber_services-' + formIndex + '-');

        // Clear the input values
        var inputs = newForm.querySelectorAll('input, select, textarea');
        inputs.forEach(function(input) {
            if (input.name.endsWith('-DELETE')) {
                input.checked = false;
            } else {
                input.value = '';
            }
            if (input.type === 'checkbox' || input.type === 'radio') {
                input.checked = false;
            }
        });

        // Append the new form
        formsetContainer.appendChild(newForm);

        // Increment the total forms count
        totalFormsInput.value = ++formIndex;

        // Re-initialize Select2 and Flatpickr for new elements
        initializeSelect2();
        initializeFlatpickr();
    });

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
