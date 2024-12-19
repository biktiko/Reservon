// static/main/js/push_subscription.js

document.addEventListener('DOMContentLoaded', function() {
    const publicVapidKey = 'LS0tLS1CRUdJTiBQVUJMSUMgS0VZLS0tLS0KTUZrd0V3WUhLb1pJemowQ0FRWUlLb1pJemowREFRY0RRZ0FFU2pXOXNSaXhDcllDK2JuOEJtd2MybnJ1bkwrMQo0MHRSR2VGalBOOVVOd0E3NnNiUTFRUWdXeFA4NHd2cW1xNXZ4R1plaFJVQnA4QnhFWmY4TlNwYW1nPT0KLS0tLS1FTkQgUFVCTElDIEtFWS0tLS0tCg';

    // Функция для конвертации ключа из base64 в Uint8Array
    function urlBase64ToUint8Array(base64String) {
        const padding = '='.repeat((4 - base64String.length % 4) % 4);
        const base64 = (base64String + padding)
            .replace(/\-/g, '+')
            .replace(/_/g, '/');

        const rawData = window.atob(base64);
        const outputArray = new Uint8Array(rawData.length);

        for (let i = 0; i < rawData.length; ++i) {
            outputArray[i] = rawData.charCodeAt(i);
        }
        return outputArray;
    }

    // Регистрация Service Worker
    if ('serviceWorker' in navigator) {
        registerServiceWorker();
    } else {
        console.warn('Service workers не поддерживаются в этом браузере.');
    }

    function registerServiceWorker() {
        navigator.serviceWorker.register('/service-worker.js')
            .then(function(registration) {
                console.log('Service Worker зарегистрирован с областью:', registration.scope);
                subscribeUser(registration);
            })
            .catch(function(error) {
                console.error('Ошибка при регистрации Service Worker:', error);
            });
    }

      // Подписка пользователя на push-уведомления
      function subscribeUser(registration) {
        const subscribeOptions = {
            userVisibleOnly: true,
            applicationServerKey: urlBase64ToUint8Array(publicVapidKey)
        };

        registration.pushManager.subscribe(subscribeOptions)
            .then(function(pushSubscription) {
                console.log('Получена подписка на push:', pushSubscription);
                sendSubscriptionToServer(pushSubscription);
            })
            .catch(function(error) {
                console.error('Ошибка при подписке на push:', error);
            });
    }

    // Отправка подписки на сервер
    function sendSubscriptionToServer(subscription) {
        fetch('/salons/subscribe_push/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken') // Убедитесь, что CSRF-токен передаётся корректно
            },
            body: JSON.stringify(subscription)
        })
        .then(function(response) {
            if (response.ok) {
                console.log('Подписка успешно зарегистрирована на сервере.');
            } else {
                console.error('Ошибка при отправке подписки на сервер.');
            }
        })
        .catch(function(error) {
            console.error('Ошибка при отправке подписки на сервер:', error);
        });
    }

    // Функция для получения CSRF-токена
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                // Проверяем, начинается ли куки с нужного имени
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
});
