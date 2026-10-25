// Apply before the first paint, including when storage is blocked.
(() => {
  let saved;
  try {
    saved = localStorage.getItem("wtr-theme");
  } catch {}
  const theme =
    saved === "dark" || saved === "light"
      ? saved
      : matchMedia("(prefers-color-scheme: dark)").matches
        ? "dark"
        : "light";
  document.documentElement.dataset.theme = theme;
  document.documentElement.style.colorScheme = theme;
})();
