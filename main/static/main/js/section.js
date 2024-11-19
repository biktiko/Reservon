document.addEventListener('DOMContentLoaded', function() {
    const closeIntroBtn = document.getElementById('close-intro');
    const introSection = document.getElementById('intro-section');

    // Проверяем, скрыта ли секция ранее
    if (localStorage.getItem('introHidden') === 'true') {
        introSection.style.display = 'none';
    }

    closeIntroBtn.addEventListener('click', function() {
        introSection.style.display = 'none';
        localStorage.setItem('introHidden', 'true');
    });
});
