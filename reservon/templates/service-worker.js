// C:\Reservon\Reservon\reservon\templates\service-worker.js
self.addEventListener('push', function(event) {
    if (event.data) {
        const data = event.data.json();
        const title = data.head || 'Новое уведомление';
        const options = {
            body: data.body || 'У вас новое бронирование!',
            icon: data.icon || '/static/main/img/notification-icon.png',
            data: data.url || '/'
        };

        event.waitUntil(
            self.registration.showNotification(title, options)
        );
    }
});

self.addEventListener('notificationclick', function(event) {
    event.notification.close();
    const url = event.notification.data;
    event.waitUntil(
        clients.openWindow(url)
    );
});
