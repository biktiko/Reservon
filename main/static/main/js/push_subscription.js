// static/main/js/push_subscription.js

document.addEventListener('DOMContentLoaded', function() {
    const publicVapidKey = "BP-1Jkn85ndvrY2m0_F2KArCKEBmw0vPp9BjPPjreL-WORMW3GUjTLPbQ1teQT5A_-sgu2Lfn59Gtb5S69X_Dho"; 

    // Для сравнения двух Uint8Array
    function arraysAreEqual(a1, a2) {
        if (!a1 || !a2 || a1.length !== a2.length) return false;
        for (let i = 0; i < a1.length; i++) {
            if (a1[i] !== a2[i]) return false;
        }
        return true;
    }

    // Функция для конвертации ключа из base64url в Uint8Array
    function urlBase64ToUint8Array(base64String) {
        const padding = '='.repeat((4 - base64String.length % 4) % 4);
        const base64 = (base64String + padding)
            .replace(/-/g, '+')
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

    async function subscribeUser(registration) {
        try {
            const newKey = urlBase64ToUint8Array(publicVapidKey);

            // Проверяем, нет ли уже подписки в браузере
            const existingSubscription = await registration.pushManager.getSubscription();
            if (existingSubscription) {
                const oldKey = existingSubscription.options.applicationServerKey;
                // Если ключи совпадают, переиспользуем существующую подписку
                if (arraysAreEqual(oldKey, newKey)) {
                    // console.log('Уже есть подписка с тем же ключом, отправим её на сервер...');
                    sendSubscriptionToServer(existingSubscription);
                    return;
                } else {
                    // Ключи не совпадают, значит отписываемся и подписываемся заново
                    await existingSubscription.unsubscribe();
                    // console.log('Старая подписка отписана, ключи различались.');
                }
            }

            // Создаём новую подписку
            const subscribeOptions = {
                userVisibleOnly: true,
                applicationServerKey: newKey
            };
            // console.log('Подписываемся с новым ключом:', subscribeOptions);

            const pushSubscription = await registration.pushManager.subscribe(subscribeOptions);
            // console.log('Получена новая подписка на push:', pushSubscription);

            // Отправляем подписку на сервер
            sendSubscriptionToServer(pushSubscription);
        } catch (error) {
            console.error('Ошибка при подписке на push:', error);
        }
    }

    function sendSubscriptionToServer(subscription) {

        if (subscription.endpoint.includes('wns2-par02p.notify.windows.com')) {   // Так как сейчас все равно не работает пуш в браузере временно отключим их вовсе
            // console.log('Пропускаем Windows WNS подписку, так как pywebpush не поддерживает aud');
            subscription.unsubscribe();
            return;
        }

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
                // console.log('Подписка успешно зарегистрирована на сервере.');
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

    // ручное отписывания пользователя
    async function unsubscribeUser() {
        try {
            const registration = await navigator.serviceWorker.ready;
            const subscription = await registration.pushManager.getSubscription();
    
            if (subscription) {
                const success = await subscription.unsubscribe();
                if (success) {
                    console.log('Подписка успешно отписана.');

                    // Запрос на сервер для удаления записи из БД
                    await fetch('/unsubscribe/', {
                        method: 'POST',
                        body: JSON.stringify({ endpoint: subscription.endpoint }),
                        headers: {
                            'Content-Type': 'application/json'
                        }
                    });
                } else {
                    console.log('Не удалось отписаться от подписки.');
                }
            } else {
                console.log('Нет активных подписок для отписки.');
            }
        } catch (error) {
            console.error('Ошибка при отписке:', error);
        }
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
