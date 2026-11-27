export function initPageBuilder() {
  const total = document.querySelector<HTMLInputElement>("#id_blocks-TOTAL_FORMS");
  const container = document.getElementById("blocks-container");
  const add = document.getElementById("add-block-btn");
  const template = document.querySelector<HTMLTemplateElement>("#empty-block-template");
  if (!total || !container || !add || !template) return;

  function updateBadges() {
    container!.querySelectorAll(".block-number-badge").forEach((badge, index) => {
      badge.textContent = String(index + 1);
    });
  }

  add.addEventListener("click", () => {
    const count = Number(total.value);
    const fragment = document.createElement("template");
    fragment.innerHTML = template.innerHTML.replaceAll("__prefix__", String(count));
    const order = fragment.content.querySelector<HTMLInputElement>('input[name$="-order"]');
    if (order) order.value = String(count);
    container.append(fragment.content);
    total.value = String(count + 1);
    updateBadges();
  });

  container.addEventListener("click", (event) => {
    if (!(event.target instanceof Element)) return;
    const card = event.target.closest(".remove-block-btn")?.closest(".block-card");
    if (!card) return;
    card.remove();
    updateBadges();
  });
}
