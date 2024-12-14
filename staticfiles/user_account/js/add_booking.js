// account/static/account/js/add_booking.js
document.addEventListener('DOMContentLoaded', function() {
    var bookingForm = document.getElementById('admin-booking-form');
    var formMessages = document.getElementById('form-messages');

    if (bookingForm) {
        bookingForm.addEventListener('submit', function(e) {
            e.preventDefault();

            var formData = new FormData(bookingForm);

            fetch(bookingForm.action, {
                method: 'POST',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                },
                body: formData,
            })
            .then(response => {
                if (!response.ok) {
                    return response.json().then(data => { throw data; });
                }
                return response.json();
            })
            .then(data => {
                if (data.success) {
                    formMessages.innerHTML = '<div class="alert alert-success">' + data.message + '</div>';
                    bookingForm.reset();
                    $('#addBookingModal').modal('hide');
                    location.reload();
                }
            })
            .catch(error => {
                if (error.errors) {
                    var errors = JSON.parse(error.errors);
                    var errorMessages = '';
                    for (var field in errors) {
                        errors[field].forEach(function(err) {
                            errorMessages += '<div class="alert alert-danger">' + err.message + '</div>';
                        });
                    }
                    formMessages.innerHTML = errorMessages;
                } else {
                    formMessages.innerHTML = '<div class="alert alert-danger">Произошла ошибка при отправке формы.</div>';
                }
                console.error('Error:', error);
            });
        });
    }
});
