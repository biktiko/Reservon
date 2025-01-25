function createBarberCard(id, name, avatar, description, duration) {
    const card = document.createElement('div');
    card.classList.add('barber-card');
    card.setAttribute('data-barber-id', id);
    card.setAttribute('data-default-duration', duration);

    const img = document.createElement('img');
    img.src = avatar;
    img.alt = name;
    img.classList.add('barber-avatar');
    card.appendChild(img);

    const infoDiv = document.createElement('div');
    infoDiv.classList.add('barber-info');

    const nameElement = document.createElement('h4');
    nameElement.classList.add('barber-name');
    nameElement.textContent = name;
    infoDiv.appendChild(nameElement);

    const descElement = document.createElement('p');
    descElement.classList.add('barber-description');
    descElement.textContent = description;
    infoDiv.appendChild(descElement);

    card.appendChild(infoDiv);

    card.addEventListener('click', () => selectBarber(id));
    return card;
}
