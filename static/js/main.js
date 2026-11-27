/**
 * ==========================================================================
 * Главный JS-модуль сайта ШСО ДВФУ
 * Управление уведомлениями, мобильной навигацией и базовой интерактивностью
 * ==========================================================================
 */

document.addEventListener('DOMContentLoaded', () => {
  initFlashMessages();
  initDisclosures();
  initShareButtons();
});

/**
 * Автоматическое скрытие flash-уведомлений через 5 секунд с плавным затуханием
 */
function initFlashMessages() {
  const alerts = document.querySelectorAll('[data-auto-dismiss]');
  alerts.forEach((alert) => {
    alert.querySelector('[data-dismiss-alert]')?.addEventListener('click', () => alert.remove());
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
function initDisclosures() {
  document.querySelectorAll('[data-disclosure]').forEach((group, index) => {
    const owned = (selector) => [...group.querySelectorAll(selector)]
      .find((node) => node.closest('[data-disclosure]') === group);
    const button = owned('[data-disclosure-toggle]');
    const panel = owned('[data-disclosure-panel]');
    if (!button || !panel) return;

    panel.id ||= 'disclosure-' + index;
    button.setAttribute('aria-controls', panel.id);
    const setOpen = (open, restoreFocus = false) => {
      panel.hidden = !open;
      button.setAttribute('aria-expanded', String(open));
      if (open && panel.getAttribute('role') === 'dialog') panel.querySelector('textarea')?.focus();
      if (!open && restoreFocus) button.focus();
    };
    button.addEventListener('click', () => setOpen(panel.hidden));
    panel.querySelector('[data-disclosure-close]')?.addEventListener('click', () => setOpen(false, true));
    panel.addEventListener('click', (event) => {
      if (event.target === panel && panel.hasAttribute('data-dismiss-backdrop')) setOpen(false, true);
    });
    if (group.hasAttribute('data-dismiss-outside')) {
      document.addEventListener('click', (event) => {
        if (!group.contains(event.target)) setOpen(false);
      });
    }
    group.addEventListener('keydown', (event) => {
      if (panel.hidden || event.defaultPrevented) return;
      if (event.key === 'Escape') {
        event.preventDefault();
        setOpen(false, true);
      }
      if (event.key === 'Tab' && panel.getAttribute('role') === 'dialog') {
        const controls = panel.querySelectorAll('textarea, button');
        const first = controls[0];
        const last = controls[controls.length - 1];
        if (event.shiftKey ? document.activeElement === first : document.activeElement === last) {
          event.preventDefault();
          (event.shiftKey ? last : first)?.focus();
        }
      }
    });
  });
}

function initShareButtons() {
  document.querySelectorAll('[data-copy-url]').forEach((button) => {
    if (!navigator.clipboard) {
      button.hidden = true;
      return;
    }
    let timer;
    button.addEventListener('click', async () => {
      try {
        await navigator.clipboard.writeText(window.location.href);
      } catch {
        return;
      }
      const label = button.querySelector('[data-copy-label]');
      const copied = button.querySelector('[data-copied-label]');
      label.hidden = true;
      copied.hidden = false;
      clearTimeout(timer);
      timer = setTimeout(() => {
        label.hidden = false;
        copied.hidden = true;
      }, 2500);
    });
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
