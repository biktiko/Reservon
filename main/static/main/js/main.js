document.addEventListener('DOMContentLoaded', function () {
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
  