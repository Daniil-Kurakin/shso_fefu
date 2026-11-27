/**
 * ШСО ДВФУ — Радиальный циферблат выбора времени (24-часовой формат)
 * Режим часов:
 *   - Внешний слой: первая половина дня (00:00 - 11:00)
 *   - Внутренний слой: вторая половина дня (12:00 - 23:00)
 * Поддержка ручного перетаскивания стрелочки зажатием (drag & drop) на тач-устройствах и мышью.
 * Автоматический переход к выбору минут после выбора часа.
 */

(function () {
  'use strict';

  class RadialTimePicker {
    constructor() {
      this.currentInput = null;
      this.selectedHour = 12;
      this.selectedMinute = 0;
      this.mode = 'hours'; // 'hours' | 'minutes'
      this.modal = null;
      this.isDragging = false;
      this.modeSwitchTimeout = null;
      this.init();
    }

    init() {
      if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => this.setup());
      } else {
        this.setup();
      }
    }

    setup() {
      this.createModal();
      this.bindInputs();

      // Наблюдатель за динамически добавляемыми элементами (например, добавление комнат в заявку)
      const observer = new MutationObserver(() => this.bindInputs());
      observer.observe(document.body, { childList: true, subtree: true });
    }

    createModal() {
      this.modal = document.getElementById('radial-timepicker-modal');

      // Закрытие по клику на фон
      this.modal.querySelector('.tp-backdrop').addEventListener('click', () => this.close());
      this.modal.querySelector('.tp-btn-cancel').addEventListener('click', () => this.close());
      this.modal.querySelector('.tp-btn-submit').addEventListener('click', () => this.apply());

      // Переключение между часами и минутами по клику на цифры в шапке
      this.modal.querySelector('.tp-digit-hour').addEventListener('click', () => this.switchMode('hours'));
      this.modal.querySelector('.tp-digit-minute').addEventListener('click', () => this.switchMode('minutes'));

      // Быстрые кнопки минут
      this.modal.querySelectorAll('.tp-preset-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
          this.selectedMinute = parseInt(e.currentTarget.getAttribute('data-min'), 10);
          this.updateDisplay();
          this.updateSelectionClasses();
          this.positionHandForMinute(this.selectedMinute);
        });
      });

      // Перетаскивание стрелки зажатием мыши / пальца на циферблате
      const clockFace = this.modal.querySelector('#tp-clock-face');

      clockFace.addEventListener('pointerdown', (e) => {
        if (e.pointerType === 'mouse' && e.button !== 0) return;
        this.isDragging = true;
        if (this.modeSwitchTimeout) {
          clearTimeout(this.modeSwitchTimeout);
          this.modeSwitchTimeout = null;
        }
        clockFace.classList.add('tp-dragging');
        clockFace.setPointerCapture(e.pointerId);
        this.handlePointer(e);
      });

      clockFace.addEventListener('pointermove', (e) => {
        if (!this.isDragging) return;
        this.handlePointer(e);
      });

      const onPointerEnd = (e) => {
        if (!this.isDragging) return;
        this.isDragging = false;
        clockFace.classList.remove('tp-dragging');
        if (clockFace.hasPointerCapture(e.pointerId)) {
          clockFace.releasePointerCapture(e.pointerId);
        }
        this.handlePointer(e);
        if (this.mode === 'hours') {
          this.modeSwitchTimeout = setTimeout(() => this.switchMode('minutes'), 180);
        }
      };

      clockFace.addEventListener('pointerup', onPointerEnd);
      clockFace.addEventListener('pointercancel', onPointerEnd);

      // ESC закрывает окно
      window.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && !this.modal.hidden) {
          this.close();
        }
      });
    }

    handlePointer(e) {
      const clockFace = this.modal.querySelector('#tp-clock-face');
      const rect = clockFace.getBoundingClientRect();
      const cx = rect.left + rect.width / 2;
      const cy = rect.top + rect.height / 2;

      const dx = e.clientX - cx;
      const dy = e.clientY - cy;

      const scale = 260 / (rect.width || 260);
      const dist = Math.hypot(dx, dy) * scale;

      let deg = (Math.atan2(dy, dx) * 180 / Math.PI) + 90;
      if (deg < 0) deg += 360;

      if (this.mode === 'hours') {
        const sector = Math.round(deg / 30) % 12;
        // Внутренний круг: 12..23 (dist < 78), внешний круг: 00..11 (dist >= 78)
        const hourVal = dist < 78 ? sector + 12 : sector;
        this.selectedHour = hourVal;
        this.updateDisplay();
        this.updateSelectionClasses();
        this.positionHandForHour(hourVal);
      } else {
        // Минуты: с шагом в 1 минуту (0..59)
        const minVal = Math.round(deg / 6) % 60;
        this.selectedMinute = minVal;
        this.updateDisplay();
        this.updateSelectionClasses();
        this.positionHandForMinute(minVal);
      }
    }

    positionHandForHour(hour) {
      const isInner = hour >= 12;
      const sector = isInner ? hour - 12 : hour;
      const radius = isInner ? 60 : 96;
      const angleDeg = (sector * 30) - 90;
      const angleRad = (angleDeg * Math.PI) / 180;
      const x = 130 + radius * Math.cos(angleRad);
      const y = 130 + radius * Math.sin(angleRad);
      this.moveHand(x, y);
    }

    positionHandForMinute(minute) {
      const radius = 96;
      const angleDeg = (minute * 6) - 90;
      const angleRad = (angleDeg * Math.PI) / 180;
      const x = 130 + radius * Math.cos(angleRad);
      const y = 130 + radius * Math.sin(angleRad);
      this.moveHand(x, y);
    }

    moveHand(x, y) {
      const line = this.modal.querySelector('#tp-hand-line');
      const head = this.modal.querySelector('#tp-hand-head');
      if (line && head) {
        line.setAttribute('x2', String(x));
        line.setAttribute('y2', String(y));
        head.setAttribute('cx', String(x));
        head.setAttribute('cy', String(y));
      }
    }

    updateSelectionClasses() {
      const container = this.modal.querySelector('#tp-numbers-container');
      if (!container) return;
      const buttons = container.querySelectorAll('.tp-num-btn');
      buttons.forEach((btn) => {
        if (this.mode === 'hours') {
          const val = parseInt(btn.dataset.hour, 10);
          btn.classList.toggle('tp-selected', val === this.selectedHour);
        } else {
          const val = parseInt(btn.dataset.min, 10);
          btn.classList.toggle('tp-selected', val === this.selectedMinute);
        }
      });
    }

    bindInputs() {
      // Ищем все input[type="time"] или input[data-timepicker="true"]
      const inputs = document.querySelectorAll('input[type="time"], input[data-timepicker="true"]');
      inputs.forEach((input) => {
        if (input.dataset.timepickerBound) return;
        input.dataset.timepickerBound = 'true';

        // Клик по полю открывает циферблат
        input.addEventListener('click', (e) => {
          e.preventDefault();
          this.open(input);
        });

        // Создаем кнопку-иконку часов рядом с инпутом, если её еще нет
        if (!input.parentElement.querySelector('.tp-clock-icon-btn')) {
          const wrapper = input.parentElement;
          if (wrapper && !wrapper.classList.contains('tp-input-wrapper')) {
            const btn = document.createElement('button');
            btn.type = 'button';
            btn.className = 'tp-clock-icon-btn';
            btn.title = 'Открыть циферблат выбора времени';
            btn.append(document.getElementById('tp-icon-template').content.cloneNode(true));
            btn.addEventListener('click', (ev) => {
              ev.preventDefault();
              this.open(input);
            });
            input.after(btn);
          }
        }
      });
    }

    open(input) {
      this.currentInput = input;
      const val = (input.value || '').trim();
      const match = val.match(/^(\d{1,2}):(\d{1,2})/);

      if (match) {
        this.selectedHour = Math.min(23, Math.max(0, parseInt(match[1], 10)));
        this.selectedMinute = Math.min(59, Math.max(0, parseInt(match[2], 10)));
      } else {
        const now = new Date();
        this.selectedHour = now.getHours();
        this.selectedMinute = Math.floor(now.getMinutes() / 5) * 5;
      }

      this.mode = 'hours';
      this.updateDisplay();
      this.renderClock();
      this.modal.hidden = false;
      document.body.style.overflow = 'hidden';
    }

    close() {
      if (this.modeSwitchTimeout) {
        clearTimeout(this.modeSwitchTimeout);
        this.modeSwitchTimeout = null;
      }
      this.isDragging = false;
      if (this.modal) {
        const clockFace = this.modal.querySelector('#tp-clock-face');
        if (clockFace) clockFace.classList.remove('tp-dragging');
        this.modal.hidden = true;
      }
      document.body.style.overflow = '';
      this.currentInput = null;
    }

    apply() {
      if (this.currentInput) {
        const hh = String(this.selectedHour).padStart(2, '0');
        const mm = String(this.selectedMinute).padStart(2, '0');
        const timeStr = `${hh}:${mm}`;
        this.currentInput.value = timeStr;

        // Генерация событий для валидации Django/браузера
        this.currentInput.dispatchEvent(new Event('input', { bubbles: true }));
        this.currentInput.dispatchEvent(new Event('change', { bubbles: true }));
      }
      this.close();
    }

    switchMode(mode) {
      if (this.modeSwitchTimeout) {
        clearTimeout(this.modeSwitchTimeout);
        this.modeSwitchTimeout = null;
      }
      this.mode = mode;
      this.updateDisplay();
      this.renderClock();
    }

    updateDisplay() {
      const hourBtn = this.modal.querySelector('.tp-digit-hour');
      const minBtn = this.modal.querySelector('.tp-digit-minute');
      const quickMin = this.modal.querySelector('#tp-minutes-quick');

      hourBtn.textContent = String(this.selectedHour).padStart(2, '0');
      minBtn.textContent = String(this.selectedMinute).padStart(2, '0');

      if (this.mode === 'hours') {
        hourBtn.classList.add('tp-active');
        minBtn.classList.remove('tp-active');
        quickMin.hidden = true;
      } else {
        hourBtn.classList.remove('tp-active');
        minBtn.classList.add('tp-active');
        quickMin.hidden = false;
      }
    }

    renderClock() {
      const container = this.modal.querySelector('#tp-numbers-container');
      container.innerHTML = '';

      const cx = 130;
      const cy = 130;

      if (this.mode === 'hours') {
        // --- РЕЖИМ ЧАСОВ: ДВА СЛОЯ ---
        // Внешний круг: первая половина дня (00..11)
        // Внутренний круг: вторая половина дня (12..23)
        const outerR = 96;
        const innerR = 60;

        // Внешний слой: 00..11
        for (let i = 0; i < 12; i++) {
          const hourVal = i;
          const angleDeg = (i * 30) - 90;
          const angleRad = (angleDeg * Math.PI) / 180;
          const x = cx + outerR * Math.cos(angleRad);
          const y = cy + outerR * Math.sin(angleRad);

          const btn = document.createElement('button');
          btn.type = 'button';
          btn.className = 'tp-num-btn tp-num-outer';
          btn.dataset.hour = String(hourVal);
          btn.style.left = `${x - 16}px`;
          btn.style.top = `${y - 16}px`;
          btn.textContent = String(hourVal).padStart(2, '0');

          if (this.selectedHour === hourVal) {
            btn.classList.add('tp-selected');
          }

          btn.addEventListener('click', (e) => {
            e.stopPropagation();
            if (this.isDragging) return;
            this.selectedHour = hourVal;
            this.updateDisplay();
            this.updateSelectionClasses();
            this.positionHandForHour(hourVal);
            if (this.modeSwitchTimeout) clearTimeout(this.modeSwitchTimeout);
            this.modeSwitchTimeout = setTimeout(() => this.switchMode('minutes'), 180);
          });

          container.appendChild(btn);
        }

        // Внутренний слой: 12..23
        for (let i = 0; i < 12; i++) {
          const hourVal = i + 12;
          const angleDeg = (i * 30) - 90;
          const angleRad = (angleDeg * Math.PI) / 180;
          const x = cx + innerR * Math.cos(angleRad);
          const y = cy + innerR * Math.sin(angleRad);

          const btn = document.createElement('button');
          btn.type = 'button';
          btn.className = 'tp-num-btn tp-num-inner';
          btn.dataset.hour = String(hourVal);
          btn.style.left = `${x - 16}px`;
          btn.style.top = `${y - 16}px`;
          btn.textContent = String(hourVal);

          if (this.selectedHour === hourVal) {
            btn.classList.add('tp-selected');
          }

          btn.addEventListener('click', (e) => {
            e.stopPropagation();
            if (this.isDragging) return;
            this.selectedHour = hourVal;
            this.updateDisplay();
            this.updateSelectionClasses();
            this.positionHandForHour(hourVal);
            if (this.modeSwitchTimeout) clearTimeout(this.modeSwitchTimeout);
            this.modeSwitchTimeout = setTimeout(() => this.switchMode('minutes'), 180);
          });

          container.appendChild(btn);
        }

        this.positionHandForHour(this.selectedHour);

      } else {
        // --- РЕЖИМ МИНУТ ---
        const r = 96;

        for (let i = 0; i < 12; i++) {
          const minVal = i * 5;
          const angleDeg = (i * 30) - 90;
          const angleRad = (angleDeg * Math.PI) / 180;
          const x = cx + r * Math.cos(angleRad);
          const y = cy + r * Math.sin(angleRad);

          const btn = document.createElement('button');
          btn.type = 'button';
          btn.className = 'tp-num-btn tp-num-minute';
          btn.dataset.min = String(minVal);
          btn.style.left = `${x - 16}px`;
          btn.style.top = `${y - 16}px`;
          btn.textContent = String(minVal).padStart(2, '0');

          if (this.selectedMinute === minVal) {
            btn.classList.add('tp-selected');
          }

          btn.addEventListener('click', (e) => {
            e.stopPropagation();
            if (this.isDragging) return;
            this.selectedMinute = minVal;
            this.updateDisplay();
            this.updateSelectionClasses();
            this.positionHandForMinute(minVal);
          });

          container.appendChild(btn);
        }

        this.positionHandForMinute(this.selectedMinute);
      }
    }
  }

  // Запуск при загрузке
  window.radialTimePicker = new RadialTimePicker();
})();
