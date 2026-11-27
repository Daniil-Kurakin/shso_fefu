import "../static/js/timepicker.js";
import "../static/js/main.js";
import "../static/js/forms.js";
import "../static/js/accordion.js";
import { initPageBuilder } from "./page-builder";
import { initRoomBooking } from "./room-booking";
import { initPassVisitors } from "./pass-visitors";

document.addEventListener("DOMContentLoaded", () => {
  initPageBuilder();
  initRoomBooking();
  initPassVisitors();
});

document.addEventListener("submit", (event) => {
  if (event.target instanceof HTMLFormElement) {
    const message = event.target.dataset.confirmSubmit;
    if (message && !window.confirm(message)) event.preventDefault();
  }
});

document.addEventListener("click", (event) => {
  if (!(event.target instanceof Element)) return;
  const message = event.target.closest<HTMLElement>("[data-confirm-click]")?.dataset.confirmClick;
  if (message && !window.confirm(message)) event.preventDefault();
});

document.addEventListener("change", (event) => {
  const control = event.target;
  if ((control instanceof HTMLInputElement || control instanceof HTMLSelectElement)
      && control.hasAttribute("data-auto-submit")) {
    control.form?.requestSubmit();
  }
});
