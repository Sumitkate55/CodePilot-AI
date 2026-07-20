import { LoaderCircle } from "lucide-react";

export function LoadingScreen({ label = "Loading CodePilot AI" }) {
  return (
    <main className="grid min-h-screen place-items-center bg-background p-6" aria-live="polite">
      <div className="flex items-center gap-3 text-sm font-medium text-muted-foreground">
        <LoaderCircle className="size-5 animate-spin text-primary" aria-hidden="true" />
        <span>{label}</span>
      </div>
    </main>
  );
}
