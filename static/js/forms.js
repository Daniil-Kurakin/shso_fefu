/**
 * ==========================================================================
 * Модуль интерактивных форм ШСО ДВФУ
 * Переключение видимости пароля, предпросмотр изображений, подсчет символов
 * ==========================================================================
 */

document.addEventListener('DOMContentLoaded', () => {
  initPasswordToggles();
  initImagePreviews();
  initCharacterCounters();
});

/**
 * Переключение видимости пароля по кнопке «глаз»
 */
function initPasswordToggles() {
  document.querySelectorAll('[data-toggle-password]').forEach((btn) => {
    btn.addEventListener('click', () => {
      const targetSelector = btn.getAttribute('data-toggle-password');
      const input = document.querySelector(targetSelector);
      if (!input) return;

      const isPassword = input.type === 'password';
      input.type = isPassword ? 'text' : 'password';

      const showIcon = btn.querySelector('[data-icon-show]');
      const hideIcon = btn.querySelector('[data-icon-hide]');
      if (showIcon && hideIcon) {
        showIcon.classList.toggle('hidden', isPassword);
        hideIcon.classList.toggle('hidden', !isPassword);
      }
      btn.setAttribute('aria-label', isPassword ? 'Скрыть пароль' : 'Показать пароль');
    });
  });
}

/**
 * Предпросмотр загружаемого изображения (логотип отряда, обложка новости)
 */
function initImagePreviews() {
  document.querySelectorAll('input[type="file"][data-preview-target]').forEach((input) => {
    input.addEventListener('change', () => {
      const targetSelector = input.getAttribute('data-preview-target');
      const preview = document.querySelector(targetSelector);
      if (!preview || !input.files || !input.files[0]) return;

      const file = input.files[0];
      if (!file.type.startsWith('image/')) return;

      const reader = new FileReader();
      reader.onload = (e) => {
        preview.src = e.target.result;
        preview.classList.remove('hidden');
      };
      reader.readAsDataURL(file);
    });
  });
}

/**
 * Подсчет оставшихся / введенных символов в полях ввода (анонс, описание)
 */
function initCharacterCounters() {
  document.querySelectorAll('[data-char-counter]').forEach((input) => {
    const targetSelector = input.getAttribute('data-char-counter');
    const counterDisplay = document.querySelector(targetSelector);
    if (!counterDisplay) return;

    const maxLength = parseInt(input.getAttribute('maxlength'), 10);

    const updateCount = () => {
      const currentLength = input.value.length;
      if (maxLength) {
        counterDisplay.textContent = `${currentLength} / ${maxLength}`;
        if (currentLength >= maxLength) {
          counterDisplay.classList.add('text-red-500');
        } else {
          counterDisplay.classList.remove('text-red-500');
        }
      } else {
        counterDisplay.textContent = `${currentLength} символов`;
      }
    };

    input.addEventListener('input', updateCount);
    updateCount();
  });
}

window.SHSO = window.SHSO || {};
window.SHSO.forms = {
  initPasswordToggles,
  initImagePreviews,
  initCharacterCounters,
};
