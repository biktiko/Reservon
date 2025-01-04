document.addEventListener('DOMContentLoaded', function () {

    const modalContent = document.getElementById('auth-modal');
    modalContent.style.display = 'none';

    const menuToggle = document.getElementById('menu-toggle');
    const navigation = document.getElementById('navigation');
    const navLinks = navigation.querySelectorAll('a');
    
    menuToggle.addEventListener('click', function () {
      navigation.classList.toggle('active');
      menuToggle.classList.toggle('active');
    });
  
    navLinks.forEach(function (link) {
      link.addEventListener('click', function () {
        navigation.classList.remove('active');
        menuToggle.classList.remove('active');
      });
    });
  });
  
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

