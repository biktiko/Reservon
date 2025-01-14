// C:\Reservon\Reservon\salons\static\salons\js\barber.js

document.addEventListener('DOMContentLoaded', function() {
    // 1) Определяем режим
    const salonModInput = document.getElementById('salon-mod');
    let salonMod = salonModInput ? salonModInput.value.trim() : 'category';

    // 2) barbersByCategory JSON
    const barbersByCategoryElement = document.getElementById('barbers-by-category');
    let barbersByCategory = {};
    if (barbersByCategoryElement) {
        try {
            barbersByCategory = JSON.parse(barbersByCategoryElement.textContent);
        } catch (error) {
            console.error('Ошибка при парсинге barbersByCategory JSON:', error);
        }
    }

    // 3) DOM-элементы
    const activeBarberCard = document.getElementById('active-barber');
    const barberList = document.getElementById('barber-list');
    const categoryButtons = document.querySelectorAll('.category-button');

    // Глобальный барбер (для режима barber)

    // Локальные барберы по категориям (для режима category)
    let selectedBarbers = {};

    let currentCategoryId = null;

    // -----------------------------
    // Утилиты

    function getCurrentCategoryId() {
        const btn = document.querySelector('.category-button.selected');
        return btn ? btn.getAttribute('data-category-id') : null;
    }

    function createBarberCard(barberId, name, avatar, description) {
        const card = document.createElement('div');
        card.classList.add('barber-card');
        card.dataset.barberId = barberId;

        const img = document.createElement('img');
        img.src = avatar;
        img.alt = name;
        img.classList.add('barber-avatar');
        card.appendChild(img);

        const infoDiv = document.createElement('div');
        infoDiv.classList.add('barber-info');

        const nEl = document.createElement('h4');
        nEl.classList.add('barber-name');
        nEl.textContent = name;
        infoDiv.appendChild(nEl);

        const dEl = document.createElement('p');
        dEl.classList.add('barber-description');
        dEl.textContent = description;
        infoDiv.appendChild(dEl);

        card.appendChild(infoDiv);

        // Клик = выбрать барбера
        card.addEventListener('click', () => {
            if (salonMod === 'barber') {
                selectedBarbers[currentCategoryId]= barberId;
                updateBarberSelectionUI(barberId);
                // Создаём событие, чтобы booking.js знал о смене барбера
                let catId = getCurrentCategoryId() || '';
                let event = new CustomEvent('barberSelected', { detail: { categoryId: catId, barberId } });
                document.dispatchEvent(event);
                barberList.classList.remove('open');
            } else {
                // режим category
                const catId = getCurrentCategoryId();
                if (catId) {
                    selectedBarbers[catId] = barberId;
                    updateBarberSelectionUI(barberId);
                    // Событие
                    const event = new CustomEvent('barberSelected', { detail: { categoryId: catId, barberId } });
                    document.dispatchEvent(event);
                    barberList.classList.remove('open');
                }
            }
        });

        return card;
    }

    function showOnlySelectedCategory(categoryId) {
        const allSections = document.querySelectorAll('.category-section');
        allSections.forEach(section => {
            if (section.dataset.categoryId === categoryId) {
                section.style.display = 'block';
            } else {
                section.style.display = 'none';
            }
        });
    }
    

    function highlightSelected(barberId) {
        barberList.querySelectorAll('.barber-card').forEach(card => {
            card.classList.remove('selected');
        });
        const sel = barberList.querySelector(`[data-barber-id="${barberId}"]`);
        if (sel) sel.classList.add('selected');
    }

    function updateBarberSelectionUI(barberId) {
        highlightSelected(barberId);
        const catId = getCurrentCategoryId();
        let barber = null;
        if (catId && barbersByCategory[catId]) {
            barber = barbersByCategory[catId].find(b => String(b.id) === String(barberId));
        }
        if (!barber || barberId === 'any') {
            // Любой мастер
            activeBarberCard.querySelector('.barber-avatar').src = '/static/salons/img/default-avatar.png';
            activeBarberCard.querySelector('.barber-name').textContent = 'Любой мастер';
            activeBarberCard.querySelector('.barber-description').textContent = 'Описание или слоган';
        } else {
            activeBarberCard.querySelector('.barber-avatar').src = barber.avatar || '/static/salons/img/default-avatar.png';
            activeBarberCard.querySelector('.barber-name').textContent = barber.name;
            activeBarberCard.querySelector('.barber-description').textContent = barber.description || '';
        }
    }

    // Показываем карточки барберов для текущей категории
    function showBarbersForCurrentCategory(isClick=False) {
        console.log('showbarbersForcurrentcategory')
        currentCategoryId = getCurrentCategoryId();
        barberList.innerHTML = '';
        if (!currentCategoryId || !barbersByCategory[currentCategoryId]) {
            barberList.innerHTML = '<p>Нет доступных мастеров для выбранной категории.</p>';
            return;
        }
        const barbers = barbersByCategory[currentCategoryId];
        if (!barbers || barbers.length === 0) {
            barberList.innerHTML = '<p>Нет доступных мастеров для выбранной категории.</p>';
            return;
        }
    
        let chosenBarberId = selectedBarbers[currentCategoryId] || 'any';
        
        if (salonMod === 'category' && chosenBarberId !== 'any') {
            // Добавить карточку "Любой мастер", чтобы пользователь мог вернуться
            const anyCard = createBarberCard('any', 'Любой мастер', '/static/salons/img/default-avatar.png', 'Описание или слоган');
            barberList.appendChild(anyCard);
        }
            
        if (isClick) {
            barbers.forEach(b => {
                if (String(b.id) !== String(chosenBarberId)) {
                    barberList.appendChild(createBarberCard(b.id, b.name, b.avatar, b.description));
                }
            });
        } else {
            barbers.forEach(b => {
                barberList.appendChild(createBarberCard(b.id, b.name, b.avatar, b.description));
            });
        }
        
    }
    
    // Фильтруем услуги
    function hideEmptyCategories() {
        // Если хотим скрывать категории без услуг
        if (salonMod !== 'barber') return;
        const categorySections = document.querySelectorAll('.category-section');
        categorySections.forEach(section => {
            const serviceCards = section.querySelectorAll('.service-card');
            let hasVisible = false;
            serviceCards.forEach(sCard => {
                console.log(section, sCard.style.display)
                if (sCard.style.display !== 'none') hasVisible = true;
            });
            if (!hasVisible) {
                section.style.display = 'none';
            } else {
                section.style.display = 'block';
            }
        });
    }

    function filterServicesByBarber(barberId, categoryId) {
        const section = document.querySelector(`.category-section[data-category-id="${categoryId}"]`);
        if (!section) return;
        const serviceCards = section.querySelectorAll('.service-card');
    
        serviceCards.forEach(card => {
            const sBarbers = card.getAttribute('data-barber-ids');
            if (!sBarbers) {
                card.style.display = 'none';
                return;
            }
            const arr = sBarbers.split(',').map(id => id.trim());
            if (barberId === 'any') {
                card.style.display = 'block';
            } else if (arr.includes(String(barberId))) {
                card.style.display = 'block';
            } else {
                card.style.display = 'none';
            }
        });
        hideEmptyCategories()
        // но тогда учтите, что она может скрыть всю категорию (if no visible services).
    }
    
    // При клике на activeBarberCard — открываем список
    activeBarberCard.addEventListener('click', function() {
        console.log('activeBarberCard')
        showBarbersForCurrentCategory(isClick=true);
        barberList.classList.toggle('open');
    });

    // При клике на категорию
    categoryButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            categoryButtons.forEach(b => b.classList.remove('selected'));
            btn.classList.add('selected');

            currentCategoryId = btn.getAttribute('data-category-id');

            // Обновляем список барберов
            if (salonMod === 'barber') {
                // Только для режима barber вызываем фильтрацию
                updateBarberSelectionUI(selectedBarbers[currentCategoryId]);
                filterServicesByBarber(selectedBarbers[currentCategoryId], currentCategoryId);
                showOnlySelectedCategory(currentCategoryId);
            } else {
                // РЕЖИМ "category":
                // -- НИКАКОЙ фильтрации услуг не делаем --
                // Просто обновим UI "Любого мастера" (или выбранного в этой категории)
                const chosenB = selectedBarbers[currentCategoryId] || 'any';
                updateBarberSelectionUI(chosenB);
                showBarbersForCurrentCategory();
            }

            barberList.classList.remove('open');
        });
    });

    // Событие barberSelected (для режима barber)
    if (salonMod === 'barber') {
        document.addEventListener('barberSelected', e => {
            const { categoryId, barberId } = e.detail;
            // Фильтруем услуги для этого барбера
            filterServicesByBarber(barberId, categoryId);
        });
    }

    // Инициализация
    if (salonMod === 'barber') {
        categoryButtons[0].click();
        const categoryId = categoryButtons[0].dataset.categoryId;
        const barbers = barbersByCategory[categoryId];
        if (barbers && barbers.length > 0) {
            selectedBarbers[currentCategoryId] = barbers[0].id; // Устанавливаем первого барбера как выбранного
            updateBarberSelectionUI(selectedBarbers[currentCategoryId]);
            filterServicesByBarber(selectedBarbers[currentCategoryId], categoryId);
        }
    }
});
