export function initRoomBooking() {
  const container = document.getElementById("premises-container");
  const add = document.getElementById("add-premise-btn");
  const total = document.querySelector<HTMLInputElement>("#id_premises-TOTAL_FORMS");
  if (!container || !add || !total) return;

  function renumber() {
    const items = container!.querySelectorAll(".premise-item");
    items.forEach((item, index) => {
      item.querySelectorAll("[id], [name], [for], [aria-describedby]").forEach((element) => {
        for (const attribute of ["id", "name", "for", "aria-describedby"]) {
          const value = element.getAttribute(attribute);
          if (value) element.setAttribute(attribute, value.replace(/premises-\d+-/g, `premises-${index}-`));
        }
      });
      const badge = item.querySelector(".premise-index");
      if (badge) badge.textContent = String(index + 1);
    });
    total!.value = String(items.length);
  }

  container.addEventListener("click", (event) => {
    if (!(event.target instanceof Element)) return;
    const item = event.target.closest(".remove-premise-btn")?.closest(".premise-item");
    if (!item || container.querySelectorAll(".premise-item").length <= 1) return;
    item.remove();
    renumber();
  });

  add.addEventListener("click", () => {
    const items = container.querySelectorAll(".premise-item");
    const clone = items[items.length - 1]?.cloneNode(true);
    if (!(clone instanceof HTMLElement)) return;

    clone.querySelectorAll("input").forEach((input) => {
      if (input.type === "checkbox") input.checked = false;
      else input.value = "";
      delete input.dataset.timepickerBound;
    });
    clone.querySelectorAll(".tp-clock-icon-btn").forEach((button) => button.remove());
    container.append(clone);
    renumber();
  });
}
