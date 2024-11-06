// static/salons/js/gallery.js

document.addEventListener('DOMContentLoaded', function() {
    // Получаем данные из json_script
    const imageUrlsElement = document.getElementById('image-urls');
    let imageUrls = [];

    if (imageUrlsElement) {
        try {
            imageUrls = JSON.parse(imageUrlsElement.textContent);
            console.log('imageUrls:', imageUrls); // Для отладки
        } catch (e) {
            console.error('Ошибка при парсинге JSON из json_script:', e);
        }
    } else {
        console.error('Элемент с ID "image-urls" не найден.');
    }

    let currentIndex = 0; // Индекс текущего изображения

    // Функция для установки основного изображения
    window.setMainImage = function(url) {
        const mainImage = document.getElementById('mainImage');
        if (!mainImage) {
            console.error('Элемент с ID "mainImage" не найден.');
            return;
        }
        if (!url) {
            console.error('URL изображения не задан.');
            return;
        }
        mainImage.src = url;
        currentIndex = imageUrls.indexOf(url);
        if (currentIndex === -1) {
            currentIndex = 0; // Если URL не найден, устанавливаем первый элемент
            if (imageUrls.length > 0) {
                mainImage.src = imageUrls[0];
            }
        }
        updateSelectedThumbnail();
    };

    // Функция для перехода к следующему изображению
    window.nextImage = function() {
        if (imageUrls.length === 0) return;
        currentIndex = (currentIndex + 1) % imageUrls.length;
        const mainImage = document.getElementById('mainImage');
        if (mainImage) {
            mainImage.src = imageUrls[currentIndex];
            updateSelectedThumbnail();
        } else {
            console.error('Элемент с ID "mainImage" не найден.');
        }
    };

    // Функция для перехода к предыдущему изображению
    window.prevImage = function() {
        if (imageUrls.length === 0) return;
        currentIndex = (currentIndex - 1 + imageUrls.length) % imageUrls.length;
        const mainImage = document.getElementById('mainImage');
        if (mainImage) {
            mainImage.src = imageUrls[currentIndex];
            updateSelectedThumbnail();
        } else {
            console.error('Элемент с ID "mainImage" не найден.');
        }
    };

    // Функция для обновления класса 'selected' у миниатюры
    function updateSelectedThumbnail() {
        const thumbnails = document.querySelectorAll('.thumbnail-images img');
        thumbnails.forEach(img => {
            // Сравниваем абсолютные URL
            const imgSrc = new URL(img.src, window.location.origin).href;
            const currentSrc = imageUrls.length > 0 ? new URL(imageUrls[currentIndex], window.location.origin).href : '';
            if (imgSrc === currentSrc) {
                img.classList.add('selected');
            } else {
                img.classList.remove('selected');
            }
        });
    }

    // Устанавливаем начальное изображение
    if (imageUrls.length > 0) {
        const mainImage = document.getElementById('mainImage');
        if (mainImage) {
            mainImage.src = imageUrls[0];
            currentIndex = 0;
            updateSelectedThumbnail();
        } else {
            console.error('Элемент с ID "mainImage" не найден.');
        }
    } else {
        console.warn('Массив imageUrls пуст.');
    }
});
