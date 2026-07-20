import { Command } from "lucide-react";
import { Link } from "react-router-dom";

export function Brand() {
  return (
    <Link to="/welcome" className="flex items-center gap-2 rounded-md font-semibold tracking-tight">
      <span className="grid size-8 place-items-center rounded-lg bg-primary text-primary-foreground">
        <Command className="size-4" aria-hidden="true" />
      </span>
      <span>CodePilot AI</span>
    </Link>
  );
}
