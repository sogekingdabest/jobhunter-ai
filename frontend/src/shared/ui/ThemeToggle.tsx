import { Icon } from "./Icon";
import { useTheme } from "../../app/providers/useTheme";
import type { ThemePreference } from "../../app/providers/theme-context";

const nextPreference: Record<ThemePreference, ThemePreference> = {
  system: "light",
  light: "dark",
  dark: "system",
};

const labels: Record<ThemePreference, string> = {
  system: "Use light theme",
  light: "Use dark theme",
  dark: "Use system theme",
};

export function ThemeToggle() {
  const { preference, resolvedTheme, setPreference } = useTheme();

  return (
    <button
      aria-label={`${labels[preference]}. Current preference: ${preference}`}
      className="icon-button"
      onClick={() => {
        setPreference(nextPreference[preference]);
      }}
      type="button"
    >
      <Icon className="size-5" name={resolvedTheme === "dark" ? "moon" : "sun"} />
    </button>
  );
}
