import { useEffect, useState } from "react";
import { Monitor, Moon, Sun } from "lucide-react";
export type ThemePreference = "system" | "dark" | "light";
export const themeKey = "wtr-theme";
export function readTheme(): ThemePreference {
  try {
    const saved = localStorage.getItem(themeKey);
    return saved === "dark" || saved === "light" ? saved : "system";
  } catch {
    return "system";
  }
}
export function ThemeSwitch() {
  const [preference, setPreference] = useState<ThemePreference>(readTheme);
  useEffect(() => {
    const query = window.matchMedia("(prefers-color-scheme: dark)");
    const apply = () => {
      const theme =
        preference === "system"
          ? query.matches
            ? "dark"
            : "light"
          : preference;
      document.documentElement.dataset.theme = theme;
      document.documentElement.style.colorScheme = theme;
    };
    apply();
    query.addEventListener("change", apply);
    return () => query.removeEventListener("change", apply);
  }, [preference]);
  return (
    <label className="theme-switch">
      {preference === "dark" ? (
        <Moon size={14} />
      ) : preference === "light" ? (
        <Sun size={14} />
      ) : (
        <Monitor size={14} />
      )}
      <span className="sr-only">Theme</span>
      <select
        value={preference}
        onChange={(event) => {
          const next = event.target.value as ThemePreference;
          setPreference(next);
          try {
            if (next === "system") localStorage.removeItem(themeKey);
            else localStorage.setItem(themeKey, next);
          } catch {
            /* Theme still works when storage is unavailable. */
          }
        }}
      >
        <option value="system">System</option>
        <option value="dark">Dark</option>
        <option value="light">Light</option>
      </select>
    </label>
  );
}
