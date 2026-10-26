/**
 * ==========================================================================
 * Модуль аккордеона FAQ ШСО ДВФУ
 * Доступный аккордеон с ARIA-атрибутами и плавной анимацией
 * ==========================================================================
 */

document.addEventListener('DOMContentLoaded', () => {
  initAccordions();
});

function initAccordions() {
  document.querySelectorAll('[data-accordion]').forEach((container) => {
    const items = container.querySelectorAll('[data-accordion-item]');

    items.forEach((item) => {
      const trigger = item.querySelector('[data-accordion-trigger]');
      const content = item.querySelector('[data-accordion-content]');
      const icon = item.querySelector('[data-accordion-icon]');

      if (!trigger || !content) return;

      trigger.addEventListener('click', () => {
        const isExpanded = trigger.getAttribute('aria-expanded') === 'true';

        // Если нужно закрывать другие вкладки аккордеона в том же контейнере:
        if (container.hasAttribute('data-accordion-single')) {
          items.forEach((otherItem) => {
            if (otherItem !== item) {
              const otherTrigger = otherItem.querySelector('[data-accordion-trigger]');
              const otherContent = otherItem.querySelector('[data-accordion-content]');
              const otherIcon = otherItem.querySelector('[data-accordion-icon]');
              if (otherTrigger) otherTrigger.setAttribute('aria-expanded', 'false');
              if (otherContent) otherContent.classList.add('hidden');
              if (otherIcon) otherIcon.classList.remove('rotate-180');
            }
          });
        }

        trigger.setAttribute('aria-expanded', !isExpanded);
        content.classList.toggle('hidden', isExpanded);
        if (icon) {
          icon.classList.toggle('rotate-180', !isExpanded);
        }
      });
    });
  });
}

window.SHSO = window.SHSO || {};
window.SHSO.initAccordions = initAccordions;
