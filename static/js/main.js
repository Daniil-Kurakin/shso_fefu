/**
 * ==========================================================================
 * Главный JS-модуль сайта ШСО ДВФУ
 * Управление уведомлениями, мобильной навигацией и базовой интерактивностью
 * ==========================================================================
 */

document.addEventListener('DOMContentLoaded', () => {
  initFlashMessages();
  initMobileNav();
});

/**
 * Автоматическое скрытие flash-уведомлений через 5 секунд с плавным затуханием
 */
function initFlashMessages() {
  const alerts = document.querySelectorAll('[data-auto-dismiss]');
  alerts.forEach((alert) => {
    const delay = parseInt(alert.getAttribute('data-auto-dismiss'), 10) || 5000;
    setTimeout(() => {
      alert.style.transition = 'opacity 0.4s ease-out, transform 0.4s ease-out';
      alert.style.opacity = '0';
      alert.style.transform = 'translateY(-8px)';
      setTimeout(() => alert.remove(), 400);
    }, delay);
  });
}

/**
 * Управление мобильным меню навигации
 */
function initMobileNav() {
  const toggleBtn = document.querySelector('[data-mobile-menu-toggle]');
  const menu = document.querySelector('[data-mobile-menu]');

  if (!toggleBtn || !menu) return;

  toggleBtn.addEventListener('click', () => {
    const isExpanded = toggleBtn.getAttribute('aria-expanded') === 'true';
    toggleBtn.setAttribute('aria-expanded', !isExpanded);
    menu.classList.toggle('hidden');
  });

  // Закрытие мобильного меню по нажатию клавиши Escape
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && !menu.classList.contains('hidden')) {
      toggleBtn.setAttribute('aria-expanded', 'false');
      menu.classList.add('hidden');
    }
  });
}

/**
 * Получение CSRF-токена из cookie для безопасных AJAX/fetch запросов
 */
function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === name + '=') {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}

window.SHSO = window.SHSO || {};
window.SHSO.getCookie = getCookie;
