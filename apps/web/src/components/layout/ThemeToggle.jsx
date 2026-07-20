import { Laptop, Moon, Sun } from "lucide-react";

import { Button } from "@/components/ui/button";
import { useUiStore } from "@/stores/ui-store";

const options = [
  { value: "light", label: "Light", Icon: Sun },
  { value: "dark", label: "Dark", Icon: Moon },
  { value: "system", label: "System", Icon: Laptop },
];

export function ThemeToggle() {
  const theme = useUiStore((state) => state.theme);
  const setTheme = useUiStore((state) => state.setTheme);
  const activeIndex = options.findIndex((option) => option.value === theme);
  const nextOption = options[(activeIndex + 1) % options.length];
  const ActiveIcon = options[activeIndex].Icon;

  return (
    <Button
      variant="ghost"
      size="icon"
      type="button"
      aria-label={`Switch theme. Current theme: ${options[activeIndex].label}`}
      title={`Theme: ${options[activeIndex].label}`}
      onClick={() => setTheme(nextOption.value)}
    >
      <ActiveIcon className="size-4" aria-hidden="true" />
    </Button>
  );
}
