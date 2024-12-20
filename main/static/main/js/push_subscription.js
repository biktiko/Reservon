// static/main/js/push_subscription.js

document.addEventListener('DOMContentLoaded', function() {
    const publicVapidKey = "BP-1Jkn85ndvrY2m0_F2KArCKEBmw0vPp9BjPPjreL-WORMW3GUjTLPbQ1teQT5A_-sgu2Lfn59Gtb5S69X_Dho"; 

    // Функция для конвертации ключа из base64url в Uint8Array
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

    function subscribeUser(registration) {
        const subscribeOptions = {
            userVisibleOnly: true,
            applicationServerKey: urlBase64ToUint8Array(publicVapidKey)
        };

        console.log(subscribeOptions)

        registration.pushManager.subscribe(subscribeOptions)
            .then(function(pushSubscription) {
                console.log('Получена подписка на push:', pushSubscription);
                sendSubscriptionToServer(pushSubscription);
            })
            .catch(function(error) {
                console.error('Ошибка при подписке на push:', error);
            });
    }

    function sendSubscriptionToServer(subscription) {
        fetch('/subscribe_push/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            credentials: 'same-origin',  // для включения cookies
            body: JSON.stringify(subscription)
        })
        .then(function(response) {
            if (response.ok) {
                console.log('Подписка успешно зарегистрирована на сервере.');
            } else {
                response.json().then(data => {
                    console.error('Ошибка при отправке подписки на сервер:', data);
                });
            }
        })
        .catch(function(error) {
            console.error('Ошибка при отправке подписки на сервер:', error);
        });
    }

    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();

                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
});
