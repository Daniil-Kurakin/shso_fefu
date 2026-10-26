/**
 * ШСО ДВФУ — Радиальный циферблат выбора времени (24-часовой формат)
 * Режим часов:
 *   - Внешний слой: первая половина дня (00:00 - 11:00)
 *   - Внутренний слой: вторая половина дня (12:00 - 23:00)
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
      if (document.getElementById('radial-timepicker-modal')) return;

      const modalHtml = `
        <div id="radial-timepicker-modal" class="tp-modal-overlay" style="display:none;" role="dialog" aria-modal="true" aria-labelledby="tp-title">
          <div class="tp-backdrop"></div>
          <div class="tp-dialog">
            <div class="tp-header">
              <span id="tp-title" class="tp-title">Выбор времени</span>
              <div class="tp-time-display">
                <button type="button" class="tp-digits tp-digit-hour" data-mode="hours">12</button>
                <span class="tp-colon">:</span>
                <button type="button" class="tp-digits tp-digit-minute" data-mode="minutes">00</button>
              </div>
            </div>

            <div class="tp-clock-wrap">
              <div class="tp-clock-face" id="tp-clock-face">
                <svg id="tp-hand-svg" class="tp-hand-svg" viewBox="0 0 260 260">
                  <line id="tp-hand-line" x1="130" y1="130" x2="130" y2="34" stroke="#0045B5" stroke-width="2"/>
                  <circle id="tp-hand-head" cx="130" cy="34" r="16" fill="#0045B5" fill-opacity="0.2"/>
                  <circle cx="130" cy="130" r="4" fill="#0045B5"/>
                </svg>
                <div id="tp-numbers-container" class="tp-numbers-container"></div>
              </div>
            </div>

            <div id="tp-minutes-quick" class="tp-minutes-quick" style="display:none;">
              <button type="button" class="tp-preset-btn" data-min="00">:00</button>
              <button type="button" class="tp-preset-btn" data-min="15">:15</button>
              <button type="button" class="tp-preset-btn" data-min="30">:30</button>
              <button type="button" class="tp-preset-btn" data-min="45">:45</button>
            </div>

            <div class="tp-actions">
              <button type="button" class="tp-btn-cancel">Отмена</button>
              <button type="button" class="tp-btn-submit">Готово</button>
            </div>
          </div>
        </div>
      `;

      document.body.insertAdjacentHTML('beforeend', modalHtml);
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
          this.renderClock();
        });
      });

      // ESC закрывает окно
      window.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && this.modal.style.display !== 'none') {
          this.close();
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
            btn.innerHTML = `
              <svg width="18" height="18" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <circle cx="12" cy="12" r="10" stroke-width="2"/>
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6l4 2"/>
              </svg>
            `;
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
      this.modal.style.display = 'flex';
      document.body.style.overflow = 'hidden';
    }

    close() {
      if (this.modal) {
        this.modal.style.display = 'none';
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
        quickMin.style.display = 'none';
      } else {
        hourBtn.classList.remove('tp-active');
        minBtn.classList.add('tp-active');
        quickMin.style.display = 'flex';
      }
    }

    renderClock() {
      const container = this.modal.querySelector('#tp-numbers-container');
      container.innerHTML = '';

      const cx = 130;
      const cy = 130;
      let activeX = cx;
      let activeY = cy;

      if (this.mode === 'hours') {
        // --- РЕЖИМ ЧАСОВ: ДВА СЛОЯ ---
        // Внешний круг: первая половина дня (00..11)
        // Внутренний круг: вторая половина дня (12..23)
        const outerR = 96;
        const innerR = 60;

        // Внешний слой: 00..11
        for (let i = 0; i < 12; i++) {
          const hourVal = i; // 0..11
          const angleDeg = (i * 30) - 90;
          const angleRad = (angleDeg * Math.PI) / 180;
          const x = cx + outerR * Math.cos(angleRad);
          const y = cy + outerR * Math.sin(angleRad);

          const btn = document.createElement('button');
          btn.type = 'button';
          btn.className = 'tp-num-btn tp-num-outer';
          btn.style.left = `${x - 16}px`;
          btn.style.top = `${y - 16}px`;
          btn.textContent = String(hourVal).padStart(2, '0');

          if (this.selectedHour === hourVal) {
            btn.classList.add('tp-selected');
            activeX = x;
            activeY = y;
          }

          btn.addEventListener('click', (e) => {
            e.stopPropagation();
            this.selectedHour = hourVal;
            this.updateDisplay();
            this.renderClock();
            // Плавный переход к выбору минут через 150мс
            setTimeout(() => this.switchMode('minutes'), 160);
          });

          container.appendChild(btn);
        }

        // Внутренний слой: 12..23
        for (let i = 0; i < 12; i++) {
          const hourVal = i + 12; // 12..23
          const angleDeg = (i * 30) - 90;
          const angleRad = (angleDeg * Math.PI) / 180;
          const x = cx + innerR * Math.cos(angleRad);
          const y = cy + innerR * Math.sin(angleRad);

          const btn = document.createElement('button');
          btn.type = 'button';
          btn.className = 'tp-num-btn tp-num-inner';
          btn.style.left = `${x - 16}px`;
          btn.style.top = `${y - 16}px`;
          btn.textContent = String(hourVal);

          if (this.selectedHour === hourVal) {
            btn.classList.add('tp-selected');
            activeX = x;
            activeY = y;
          }

          btn.addEventListener('click', (e) => {
            e.stopPropagation();
            this.selectedHour = hourVal;
            this.updateDisplay();
            this.renderClock();
            // Плавный переход к выбору минут через 150мс
            setTimeout(() => this.switchMode('minutes'), 160);
          });

          container.appendChild(btn);
        }

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
          btn.style.left = `${x - 16}px`;
          btn.style.top = `${y - 16}px`;
          btn.textContent = String(minVal).padStart(2, '0');

          if (this.selectedMinute === minVal) {
            btn.classList.add('tp-selected');
            activeX = x;
            activeY = y;
          }

          btn.addEventListener('click', (e) => {
            e.stopPropagation();
            this.selectedMinute = minVal;
            this.updateDisplay();
            this.renderClock();
          });

          container.appendChild(btn);
        }

        // Если выбрана минута не кратная 5, позиционируем стрелку точно
        if (this.selectedMinute % 5 !== 0) {
          const angleDeg = (this.selectedMinute * 6) - 90;
          const angleRad = (angleDeg * Math.PI) / 180;
          activeX = cx + r * Math.cos(angleRad);
          activeY = cy + r * Math.sin(angleRad);
        }
      }

      // Обновляем линию и наконечник стрелки
      const line = this.modal.querySelector('#tp-hand-line');
      const head = this.modal.querySelector('#tp-hand-head');
      if (line && head) {
        line.setAttribute('x2', String(activeX));
        line.setAttribute('y2', String(activeY));
        head.setAttribute('cx', String(activeX));
        head.setAttribute('cy', String(activeY));
      }
    }
  }

  // Запуск при загрузке
  window.radialTimePicker = new RadialTimePicker();
})();
