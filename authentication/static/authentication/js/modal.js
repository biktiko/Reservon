// C:\Reservon\Reservon\authentication\static\authentication\js\modal.js
/**
 * Открывает модальное окно авторизации с заданным действием.
 * @param {string} action - Действие для загрузки соответствующего контента (например, 'login').
 */


const singleCodeWrapper = document.getElementById('single-code-wrapper');
const fourCodeWrapper = document.getElementById('four-code-wrapper');

document.addEventListener('DOMContentLoaded', function() {
    const isIOS = /iPhone|iPad|iPod/i.test(navigator.userAgent);
    logger.info('navigator', navigator.userAgent)
    logger.info('isIOS', isIOS)
    const singleCodeWrapper = document.getElementById('single-code-wrapper');
    const fourCodeWrapper = document.getElementById('four-code-wrapper');
    logger.info('singleCodeWrapper', singleCodeWrapper)
    logger.info('fourCodeWrapper', fourCodeWrapper)

    if (isIOS) {
        // Показываем одно поле (iOS)
        singleCodeWrapper.style.display = 'block';
        // Скрываем четыре поля
        fourCodeWrapper.style.display = 'none';
    } else {
        // Показываем четыре поля (Android, Desktop)
        singleCodeWrapper.style.display = 'none';
        fourCodeWrapper.style.display = 'flex';
    }
});

function openAuthModal(action, salonId="") {
    var modal = document.getElementById('auth-modal');
    var modalBody = document.getElementById('modal-body');

    let bodyData = { 'action': action };

    if (action === 'login_from_booking') {
        bodyData.salon_id = salonId;
    }

    fetch('/auth/load_modal/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify(bodyData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.html) {
            modalBody.innerHTML = data.html;
            modal.classList.add('show');
            modal.style.display = 'block';
            // Переназначаем обработчики событий
            attachModalEventListeners();
            // Инициализируем автофокусировку для полей ввода кода
            initializeCodeInputFocus();
            // Устанавливаем фокус на первый интерактивный элемент
            var firstInput = modal.querySelector('input, button, select, textarea, a[href]');
            if (firstInput) {
                firstInput.focus();
            }
        } else if (data.error) {
            console.error('Error loading modal content:', data.error);
        }
    })
    .catch(error => console.error('Error fetching modal content:', error));
}

/**
 * Привязывает обработчики событий к элементам внутри модального окна.
 */
function attachModalEventListeners() {
    var modal = document.getElementById('auth-modal');

    // Обработчик для кнопки закрытия
    var closeButton = modal.querySelector('.close-button');
    if (closeButton) {
        closeButton.addEventListener('click', function(event) {
            event.preventDefault();
            closeModal();
        });
    }

    // Обработчик для кнопки "Подтвердить" внутри модального окна
    var submitVerifyButton = modal.querySelector('#submit-verify-btn');
    if (submitVerifyButton) {
        submitVerifyButton.addEventListener('click', function(event) {
            event.preventDefault();
            submitVerifyCode();
        });
    }

    // Обработчик для кнопки "Отправить заново"
    var resendButton = modal.querySelector('#resend-code-btn');
    if (resendButton) {
        resendButton.addEventListener('click', function(event) {
            event.preventDefault();
            var phone_number = document.getElementById('id_phone_number').value;
            resendVerificationCode(phone_number);
        });
    }

    // Обработчик для кнопки "Войти и забронировать" или "Войти"
    var submitEnterPasswordButton = modal.querySelector('#submit-enter-password-btn');
    if (submitEnterPasswordButton) {
        submitEnterPasswordButton.addEventListener('click', function(event) {
            event.preventDefault();
            submitEnterPassword();
        });
    }

    // Обработчик для кнопки "Установить пароль"
    var submitSetPasswordButton = modal.querySelector('#submit-set-password-btn');
    if (submitSetPasswordButton) {
        submitSetPasswordButton.addEventListener('click', function(event) {
            event.preventDefault();
            submitSetPassword();
        });
    }
}

/**
 * Закрывает модальное окно авторизации.
 */
function closeModal() {
    var modal = document.getElementById('auth-modal');
    modal.classList.remove('show');
    modal.style.display = 'none';
    // Очищаем содержимое модального окна
    document.getElementById('modal-body').innerHTML = '';
    // Удаляем действие из data-атрибута
    delete modal.dataset.action;
}

/**
 * Инициализирует автофокусировку между полями ввода кода подтверждения.
 */
function initializeCodeInputFocus() {
    var codeInputs = document.querySelectorAll('.code-input');
    codeInputs.forEach((input, index) => {
        // Обработчик ввода символа
        input.addEventListener('input', function(e) {
            var value = e.target.value;
            if (value.length === 1 && index < codeInputs.length - 1) {
                codeInputs[index + 1].focus();
            }
        });

        // Обработчик нажатия клавиши
        input.addEventListener('keydown', function(e) {
            if (e.key === 'Backspace' && e.target.value === '' && index > 0) {
                codeInputs[index - 1].focus();
            }
        });

        // Ограничение ввода только цифр
        input.addEventListener('keypress', function(e) {
            if (!/\d/.test(e.key)) {
                e.preventDefault();
            }
        });

        // Обработка вставки полного кода
        input.addEventListener('paste', function(e) {
            e.preventDefault();
            var pasteData = e.clipboardData.getData('text').trim();
            if (/^\d{4}$/.test(pasteData)) {
                codeInputs.forEach((input, i) => {
                    input.value = pasteData[i];
                });
                submitVerifyCode();
            }
        });
    });
}

/**
 * Закрывает модальное окно при клике вне его области.
 */
window.onclick = function(event) {
    var modal = document.getElementById('auth-modal');
    if (event.target == modal) {
        closeModal();
    }
}

/**
 * Закрывает модальное окно при нажатии клавиши Esc.
 */
document.addEventListener('keydown', function(event) {
    if (event.key === 'Escape') {
        var modal = document.getElementById('auth-modal');
        if (modal.classList.contains('show')) {
            closeModal();
        }
    }
});

/**
 * Инициализирует обработчики событий при загрузке документа.
 */
document.addEventListener('DOMContentLoaded', function() {
    // Обработчик события на кнопки "Login"
    var loginButtons = document.querySelectorAll('.login-btn');
    loginButtons.forEach(function(button) {
        button.addEventListener('click', function(event) {
            event.preventDefault();
            openAuthModal('login');
        });
    });

    // Обработчик для кнопки "Далее" внутри модального окна
    document.addEventListener('click', function(event) {
        if (event.target && event.target.id === 'submit-login-btn') {
            event.preventDefault();
            submitLogin();
        }
    });

    var testSetPasswordTrigger = document.getElementById('test-set-password-trigger');
    if (testSetPasswordTrigger) {
        testSetPasswordTrigger.addEventListener('click', function(event) {
            event.preventDefault();
            openSetPasswordModal();
        });
    }

    // Обработчики для полей ввода кода (если модальное окно уже загружено)
    initializeCodeInputFocus();
});

/**
 * Отправляет запрос на вход пользователя с указанным номером телефона.
 */
function submitLogin() {
    var phone_number = document.getElementById('id_phone_number').value;
    var submitButton = document.getElementById('submit-login-btn');
    
    if (!validatePhoneNumber(phone_number)) {
        document.getElementById('login-response').innerHTML = '<p>Неверный формат номера телефона.</p>';
        return;
    }

    // Отключаем кнопку, чтобы предотвратить повторные клики
    submitButton.disabled = true;
    submitButton.innerText = 'Отправка...';

    fetch('/auth/login/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify({ 'phone_number': phone_number })
    })
    .then(response => response.json())
    .then(data => {
        console.log(data)
        if (data.google_only) {
            // Перенаправляем на Google логин
            console.log(window.googleLoginUrl)
            window.location.href=window.googleLoginUrl
        } else {
            if (data.next_step) {
                loadModalContent(data.next_step, data.phone_number);
            } else if (data.error) {
                document.getElementById('login-response').innerHTML = '<p>' + data.error + '</p>';
            }
        }
    }
    )
    .catch(error => {
        console.error('Error:', error);
        document.getElementById('login-response').innerHTML = '<p>Не удалось отправить код верификации. Пожалуйста, попробуйте позже.</p>';
    })
    .finally(() => {
        // Включаем кнопку обратно
        submitButton.disabled = false;
        submitButton.innerText = 'Далее';
    });
}

/**
 * Отправляет запрос на повторную отправку кода подтверждения.
 * @param {string} phone_number - Номер телефона пользователя.
 */
function resendVerificationCode(phone_number) {
    var resendButton = document.getElementById('resend-code-btn');
    resendButton.disabled = true;
    resendButton.innerText = 'Отправка...';

    fetch('/auth/resend_verification_code/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify({ 'phone_number': phone_number })
    })
    .then(response => {
        if (response.status === 429) { // Too Many Requests
            return response.json().then(data => { throw new Error(data.error); });
        }
        return response.json();
    })
    .then(data => {
        if (data.message) {
            document.getElementById('verify-response').innerHTML = '<p>' + data.message + '</p>';
            startResendCooldown(resendButton);
        } else if (data.error) {
            document.getElementById('verify-response').innerHTML = '<p>' + data.error + '</p>';
            resendButton.disabled = false;
            resendButton.innerText = 'Отправить заново';
        }
    })
    .catch(error => {
        console.error('Error:', error);
        document.getElementById('verify-response').innerHTML = '<p>' + error.message + '</p>';
        resendButton.disabled = false;
        resendButton.innerText = 'Отправить заново';
    });
}

/**
 * Запускает таймер ожидания перед повторной отправкой кода подтверждения.
 * @param {HTMLElement} button - Кнопка "Отправить заново".
 */
function startResendCooldown(button) {
    var cooldown = 60; // 60 секунд
    var interval = setInterval(function() {
        cooldown--;
        if (cooldown > 0) {
            button.innerText = 'Отправить заново (' + cooldown + 's)';
        } else {
            clearInterval(interval);
            button.disabled = false;
            button.innerText = 'Отправить заново';
        }
    }, 1000);
}

/**
 * Загружает контент для следующего шага процесса авторизации.
 * @param {string} step - Название следующего шага (например, 'verify_code').
 * @param {string} phone_number - Номер телефона пользователя.
 */
function loadModalContent(step, phone_number) {
    var modal = document.getElementById('auth-modal');
    var modalBody = document.getElementById('modal-body');

    fetch('/auth/get_form/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify({ 'step': step, 'phone_number': phone_number })
    })
    .then(response => response.json())
    .then(data => {
        if (data.html) {
            modalBody.innerHTML = data.html;
            // Переназначаем обработчики событий
            attachModalEventListeners();
            // Инициализируем автофокусировку для новых полей ввода кода
            initializeCodeInputFocus();
        } else if (data.error) {
            console.error('Error loading modal content:', data.error);
        }
    })
    .catch(error => console.error('Error loading modal content:', error));
}

/**
 * Отправляет запрос на подтверждение введённого кода.
 */
function submitVerifyCode() {

    const phone_number = document.getElementById('id_phone_number').value;
    let code = '';

    if (isIOS) {
        // Собираем код из одного поля
        code = document.getElementById('single-code-input').value;
    } else {
        // Собираем код из 4 полей
        code =
            document.getElementById('code-1').value +
            document.getElementById('code-2').value +
            document.getElementById('code-3').value +
            document.getElementById('code-4').value;
    }

    // Дополнительная проверка: 4 или 6 цифр — зависит от того, какой длины у вас фактический код
    // Ниже пример на 4 цифры:
    if (code.length !== 4 || !/^\d{4}$/.test(code)) {
        document.getElementById('verify-response').innerHTML = '<p>Пожалуйста, введите корректный код из 4 цифр.</p>';
        return;
    }

    const submitButton = document.getElementById('submit-verify-btn');
    submitButton.disabled = true;
    submitButton.innerText = 'Подтверждение...';

    fetch('/auth/verify_code/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify({ 'phone_number': phone_number, 'code': code })
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(errData => {
                throw new Error(errData.error || 'Неизвестная ошибка');
            });
        }
        return response.json();
    })
    .then(data => {
        if (data.success) {
            if (data.redirect_to_booking) {
                // Закрываем модалку
                closeModal(); 
                // Доп. действия...
                const event = new Event('loginFromBookingSuccess');
                document.dispatchEvent(event);
            } else {
                closeModal();
                location.reload();
            }
        } else if (data.next_step) {
            // Переход к следующему шагу
            loadModalContent(data.next_step, data.phone_number);
        } else if (data.error) {
            document.getElementById('verify-response').innerHTML = '<p>' + data.error + '</p>';
        }
    })
    .catch(error => {
        console.error('Error:', error);
        document.getElementById('verify-response').innerHTML = '<p>Не удалось подтвердить код. Пожалуйста, попробуйте позже.</p>';
    })
    .finally(() => {
        submitButton.disabled = false;
        submitButton.innerText = 'Подтвердить';
    });
}

function submitSetPassword() {
    var phone_number = document.getElementById('id_phone_number').value;
    var password = document.getElementById('id_password').value;
    var password_confirm = document.getElementById('id_password_confirm').value;
    var submitButton = document.getElementById('submit-set-password-btn');

    if (!password || !password_confirm) {
        document.getElementById('set-password-response').innerHTML = '<p style="color: red;">Все поля обязательны.</p>';
        return;
    }

    if (password !== password_confirm) {
        document.getElementById('set-password-response').innerHTML = '<p style="color: red;">Пароли не совпадают.</p>';
        return;
    }

    if (password.length < 6) {
        document.getElementById('set-password-response').innerHTML = '<p style="color: red;">Пароль должен быть не менее 6 символов.</p>';
        return;
    }

    // Отключаем кнопку, чтобы предотвратить повторные клики
    submitButton.disabled = true;
    submitButton.innerText = 'Установка пароля...';

    fetch('/auth/set_password/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify({ 
            'phone_number': phone_number, 
            'password': password, 
            'password_confirm': password_confirm 
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            if (data.redirect_to_booking) {
                closeModal();
                const event = new Event('loginFromBookingSuccess');
                document.dispatchEvent(event);

            } else {
                closeModal();
                window.location.href = '/';
            }
        } else if (data.error) {
            document.getElementById('set-password-response').innerHTML = `<p style="color: red;">${data.error}</p>`;
        }
    })
    .catch(error => {
        console.error('Error:', error);
        document.getElementById('set-password-response').innerHTML = '<p style="color: red;">Не удалось установить пароль. Пожалуйста, попробуйте позже.</p>';
    })
    .finally(() => {
        // Включаем кнопку обратно
        submitButton.disabled = false;
        submitButton.innerText = 'Завершить регистрацию';
    });
}

/**
 * Отправляет запрос на вход пользователя с установленным паролем.
 */
function submitEnterPassword() {
    var phone_number = document.getElementById('id_phone_number').value;
    var password = document.getElementById('id_password').value;
    var submitButton = document.getElementById('submit-enter-password-btn');

    if (!password) {
        document.getElementById('enter-password-response').innerHTML = '<p style="color: red;">Пароль обязателен.</p>';
        return;
    }

    // Отключаем кнопку, чтобы предотвратить повторные клики
    submitButton.disabled = true;
    submitButton.innerText = 'Вход...';

    fetch('/auth/enter_password/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify({ 'phone_number': phone_number, 'password': password })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            if (data.redirect_to_booking) {
                closeModal();
                // Отправляем событие об успешном логине для продолжения бронирования
                const event = new Event('loginFromBookingSuccess');
                document.dispatchEvent(event);
            } else {
                closeModal();
                location.reload();
            }
        } else if (data.error) {
            document.getElementById('enter-password-response').innerHTML = `<p style="color: red;">${data.error}</p>`;
        }
    })
    .catch(error => {
        console.error('Error:', error);
        document.getElementById('enter-password-response').innerHTML = '<p style="color: red;">Не удалось войти. Пожалуйста, попробуйте позже.</p>';
    })
    .finally(() => {
        // Включаем кнопку обратно
        submitButton.disabled = false;
        submitButton.innerText = 'Войти';
    });
}

/**
 * Валидирует формат номера телефона.
 * @param {string} phone_number - Номер телефона для валидации.
 * @returns {boolean} - Возвращает true, если номер валиден, иначе false.
 */
function validatePhoneNumber(phone_number) {
    var regex = /^\+374\d{8}$/;
    var isValid = regex.test(phone_number) || phone_number === "+15005550007";
    return isValid;
}

/**
 * Получает значение cookie по имени.
 * @param {string} name - Имя cookie.
 * @returns {string|null} - Значение cookie или null, если не найдено.
 */
function getCookie(name) {
    var cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        var cookies = document.cookie.split(';');
        for (var i = 0; i < cookies.length; i++) {
            var cookie = cookies[i].trim();
            // Проверяем, соответствует ли эта cookie искомому имени
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

function openSetPasswordModal() {
    console.log('test')
    var modal = document.getElementById('auth-modal');
    var modalBody = document.getElementById('modal-body');

    // Определите HTML содержимое формы установки пароля
    var setPasswordHTML = 
`<h2>Введите пароль</h2>
<form id="enter-password-form">
    <input type="hidden" id="id_phone_number" value="{{ phone_number }}">
    
    <div class="form-group">
        <label for="id_password">Пароль:</label>
        <input type="password" name="password" id="id_password" required>
    </div>
    
    <button type="button" id="submit-enter-password-btn">
            Войти и забронировать
     
    </button>
    
    <div class="forgot-password">
        <a href="#" id="forgot-password-link">Забыли пароль?</a>
    </div>
</form>
<div id="enter-password-response"></div>`
    ;

    // Устанавливаем HTML содержимое модального окна
    modalBody.innerHTML = setPasswordHTML;
    modal.classList.add('show');
    modal.style.display = 'block';

}