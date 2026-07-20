import { LogOut, Menu } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { useAuthStore } from "@/features/auth/auth-store";
import { useUiStore } from "@/stores/ui-store";

import { ThemeToggle } from "./ThemeToggle";

export function Topbar() {
  const openSidebar = useUiStore((state) => state.openSidebar);
  const user = useAuthStore((state) => state.user);
  const signOut = useAuthStore((state) => state.signOut);
  const navigate = useNavigate();
  const [isSigningOut, setIsSigningOut] = useState(false);

  const handleSignOut = async () => {
    setIsSigningOut(true);
    try {
      await signOut();
      navigate("/login", { replace: true });
    } finally {
      setIsSigningOut(false);
    }
  };

  return (
    <header className="flex h-16 items-center justify-between border-b border-border bg-background px-4 sm:px-6">
      <Button
        variant="ghost"
        size="icon"
        type="button"
        className="lg:hidden"
        aria-label="Open navigation"
        onClick={openSidebar}
      >
        <Menu className="size-5" aria-hidden="true" />
      </Button>
      <p className="hidden text-sm text-muted-foreground lg:block">Your codebase intelligence workspace</p>
      <div className="flex items-center gap-1 sm:gap-2">
        <span className="hidden max-w-44 truncate px-2 text-sm text-muted-foreground sm:block">
          {user?.display_name}
        </span>
        <ThemeToggle />
        <Button
          variant="ghost"
          size="icon"
          type="button"
          aria-label="Sign out"
          title="Sign out"
          disabled={isSigningOut}
          onClick={handleSignOut}
        >
          <LogOut className="size-4" aria-hidden="true" />
        </Button>
      </div>
    </header>
  );
}
