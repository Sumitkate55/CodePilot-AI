import { FolderPlus, LayoutDashboard, PanelLeftClose, PanelLeftOpen } from "lucide-react";
import { NavLink } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { useUiStore } from "@/stores/ui-store";

import { Brand } from "./Brand";

const navigation = [
  { label: "Dashboard", to: "/dashboard", Icon: LayoutDashboard },
  { label: "Add repository", to: "/repositories/new", Icon: FolderPlus },
];

export function Sidebar() {
  const sidebarOpen = useUiStore((state) => state.sidebarOpen);
  const closeSidebar = useUiStore((state) => state.closeSidebar);
  const toggleSidebar = useUiStore((state) => state.toggleSidebar);

  return (
    <>
      {sidebarOpen ? (
        <button
          type="button"
          className="fixed inset-0 z-30 bg-slate-950/30 lg:hidden"
          aria-label="Close navigation"
          onClick={closeSidebar}
        />
      ) : null}
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-40 flex w-72 -translate-x-full flex-col border-r border-border bg-card p-4 transition-transform lg:static lg:translate-x-0",
          sidebarOpen && "translate-x-0",
        )}
      >
        <div className="flex items-center justify-between">
          <Brand />
          <Button
            variant="ghost"
            size="icon"
            type="button"
            aria-label="Collapse navigation"
            className="lg:hidden"
            onClick={closeSidebar}
          >
            <PanelLeftClose className="size-4" aria-hidden="true" />
          </Button>
        </div>
        <nav className="mt-8 flex flex-1 flex-col gap-1" aria-label="Workspace navigation">
          {navigation.map(({ label, to, Icon }) => (
            <NavLink
              key={to}
              to={to}
              end
              onClick={closeSidebar}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium text-muted-foreground transition-colors hover:bg-muted hover:text-foreground",
                  isActive && "bg-muted text-foreground",
                )
              }
            >
              <Icon className="size-4" aria-hidden="true" />
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="hidden border-t border-border pt-4 lg:block">
          <Button variant="ghost" size="sm" type="button" onClick={toggleSidebar}>
            <PanelLeftOpen className="size-4" aria-hidden="true" />
            Navigation
          </Button>
        </div>
      </aside>
    </>
  );
}
