document.addEventListener('DOMContentLoaded', function () {
    // Проверяем, что координаты заданы
    if (!window.salonCoordinates) {
        console.log("Coordinates are missing for this salon.");
        return;
    }

    // Убираем скобки и разделяем широту и долготу
    const [latitude, longitude] = window.salonCoordinates
        .replace(/[()]/g, '')  // Убираем круглые скобки
        .split(',')            // Разделяем по запятой
        .map(coord => parseFloat(coord.trim()));  // Преобразуем в числа

    // Проверяем, являются ли latitude и longitude допустимыми числами
    if (isNaN(latitude) || isNaN(longitude)) {
        console.error("Invalid coordinates:", latitude, longitude);
        return;
    }

    // Инициализация карты с использованием полученных координат
    const map = L.map('map').setView([latitude, longitude], 15);

    // Добавляем слой карты OpenStreetMap
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(map);

    // Добавляем маркер на координаты салона с информацией
    L.marker([latitude, longitude])
        .addTo(map)
        .bindPopup(`<b>${window.salonName}</b><br>${window.salonAddress}`)
        .openPopup();
});
