export function initPassVisitors() {
  const list = document.querySelector<HTMLElement>("[data-visitor-list]");
  const total = document.querySelector<HTMLInputElement>("#id_visitors-TOTAL_FORMS");
  const template = document.querySelector<HTMLTemplateElement>("#empty-visitor-template");
  const add = document.querySelector<HTMLButtonElement>("#add-visitor-btn");
  const passType = document.querySelector<HTMLSelectElement>("#id_pass_type");
  if (!list || !total || !template || !add || !passType) return;

  const visibleRows = () => [...list.querySelectorAll<HTMLElement>("[data-visitor-row]")].filter((row) => {
    row.hidden = row.querySelector<HTMLInputElement>('[name$="-DELETE"]')?.checked ?? false;
    return !row.hidden;
  });

  const refresh = () => {
    add.hidden = passType.value !== "group";
    const rows = visibleRows();
    rows.forEach((row, index) => {
      row.querySelector("[data-visitor-index]")!.textContent = String(index + 1);
      row.querySelector<HTMLButtonElement>("[data-remove-visitor]")!.hidden = rows.length === 1;
    });
  };

  add.addEventListener("click", () => {
    const index = Number(total.value);
    const fragment = document.createElement("template");
    fragment.innerHTML = template.innerHTML.replaceAll("__prefix__", String(index));
    const name = fragment.content.querySelector<HTMLInputElement>('[name$="-full_name"]');
    list.append(fragment.content);
    total.value = String(index + 1);
    refresh();
    name?.focus();
  });

  list.addEventListener("click", (event) => {
    if (!(event.target instanceof Element) || visibleRows().length <= 1) return;
    const row = event.target.closest("[data-remove-visitor]")?.closest("[data-visitor-row]");
    const deleted = row?.querySelector<HTMLInputElement>('[name$="-DELETE"]');
    if (!row || !deleted) return;
    deleted.checked = true;
    for (const field of row.querySelectorAll<HTMLInputElement | HTMLSelectElement>("input, select")) {
      if (field !== deleted) field.disabled = true;
    }
    refresh();
    if (add.hidden) visibleRows()[0]?.querySelector<HTMLInputElement>('[name$="-full_name"]')?.focus();
    else add.focus();
  });

  passType.addEventListener("change", refresh);
  refresh();
}
