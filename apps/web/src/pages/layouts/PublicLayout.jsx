import { ArrowRight } from "lucide-react";
import { Link, Outlet } from "react-router-dom";

import { Brand } from "@/components/layout/Brand";
import { ThemeToggle } from "@/components/layout/ThemeToggle";
import { Button } from "@/components/ui/button";

export function PublicLayout() {
  return (
    <div className="min-h-screen bg-background">
      <header className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        <Brand />
        <div className="flex items-center gap-2">
          <ThemeToggle />
          <Button asChild size="sm">
            <Link to="/login">
              Enter workspace
              <ArrowRight className="size-3.5" aria-hidden="true" />
            </Link>
          </Button>
        </div>
      </header>
      <Outlet />
    </div>
  );
}
