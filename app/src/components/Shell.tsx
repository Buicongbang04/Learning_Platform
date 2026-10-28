import { useEffect, useState, type ReactNode } from "react";
import { Link, NavLink, useLocation } from "react-router-dom";
import { ChevronRight, GraduationCap, LayoutDashboard, Menu, Moon } from "lucide-react";
import { TRACKS } from "../content";
import { trackStats, useProgress } from "../progress";
import { button, cx, Icon } from "./ui";

const navItem = (active: boolean) =>
  cx(
    "flex h-10 w-full cursor-pointer items-center gap-2.5 rounded-xl px-3 text-sm outline-hidden transition-colors",
    active
      ? "bg-secondary font-medium text-foreground"
      : "text-foreground/70 hover:bg-item-hover hover:text-foreground focus-visible:bg-item-hover focus-visible:text-foreground",
  );

function useDarkMode() {
  const [dark, setDark] = useState(() => document.documentElement.classList.contains("dark"));
  const toggle = () => {
    const next = !dark;
    document.documentElement.classList.toggle("dark", next);
    try {
      localStorage.setItem("theme", next ? "dark" : "light");
    } catch {
      /* chế độ riêng tư: chỉ đổi cho phiên này */
    }
    setDark(next);
  };
  return { dark, toggle };
}

function Sidebar({ onNavigate }: { onNavigate?: () => void }) {
  const { pathname } = useLocation();
  const progress = useProgress();
  const { dark, toggle } = useDarkMode();
  return (
    <>
      <div className="flex h-16 shrink-0 items-center gap-2.5 border-b border-border px-5">
        <span className="grid size-8 place-items-center rounded-lg bg-primary text-primary-foreground">
          <GraduationCap className="size-4" aria-hidden />
        </span>
        <span className="text-sm font-semibold">Học tập</span>
      </div>
      <nav className="flex flex-1 flex-col gap-1 overflow-y-auto px-3 py-3" aria-label="Điều hướng chính">
        <Link to="/" onClick={onNavigate} aria-current={pathname === "/" ? "page" : undefined} className={navItem(pathname === "/")}>
          <LayoutDashboard className="size-4 shrink-0" aria-hidden />
          <span className="min-w-0 flex-1 truncate">Tổng quan</span>
        </Link>
        <div className="mt-4">
          <p className="flex h-10 items-center px-3 text-xs font-medium tracking-wide text-muted uppercase">Lộ trình</p>
          <div className="flex flex-col gap-1">
            {TRACKS.map((track) => {
              if (track.status === "soon") {
                return (
                  <span key={track.id} aria-disabled="true" className="flex h-10 w-full items-center gap-2.5 rounded-xl px-3 text-sm text-foreground/70">
                    <Icon name={track.icon} className="size-4 shrink-0" />
                    <span className="min-w-0 flex-1 truncate">{track.name}</span>
                    <span className="shrink-0 text-xs text-muted">Sắp có</span>
                  </span>
                );
              }
              const active = pathname.startsWith(`/t/${track.id}`);
              const percent = progress.status === "ready" ? `${trackStats(track, progress.of(track.id)).percent}%` : "";
              return (
                <NavLink key={track.id} to={`/t/${track.id}`} onClick={onNavigate} className={navItem(active)}>
                  <Icon name={track.icon} className="size-4 shrink-0" />
                  <span className="min-w-0 flex-1 truncate">{track.name}</span>
                  <span className={cx("shrink-0 text-xs tabular-nums", active ? "text-foreground" : "text-muted")}>{percent}</span>
                </NavLink>
              );
            })}
          </div>
        </div>
      </nav>
      <div className="border-t border-border px-3 py-3">
        <button
          type="button"
          role="switch"
          aria-checked={dark}
          onClick={toggle}
          className="flex h-10 w-full cursor-pointer items-center gap-2.5 rounded-xl px-3 text-sm text-foreground/70 outline-hidden transition-colors hover:bg-item-hover hover:text-foreground focus-visible:bg-item-hover focus-visible:text-foreground"
        >
          <Moon className="size-4 shrink-0" aria-hidden />
          <span className="flex-1 text-left">Giao diện tối</span>
          <span className={cx("relative h-5 w-9 rounded-full transition-colors", dark ? "bg-primary" : "bg-foreground/15")}>
            <span className={cx("absolute top-0.5 size-4 rounded-full bg-surface shadow-sm transition-all", dark ? "left-4.5" : "left-0.5")} />
          </span>
        </button>
      </div>
    </>
  );
}

export function Crumbs({ items }: { items: { to: string; label: string }[] }) {
  return (
    <nav aria-label="Đường dẫn" className="flex h-8 min-w-0 items-center gap-1.5 text-sm text-muted">
      {items.map((item) => (
        <span key={item.to} className="flex min-w-0 items-center gap-1.5">
          <Link to={item.to} className="inline-flex h-8 min-w-0 items-center truncate outline-hidden hover:text-foreground focus-visible:text-foreground">
            {item.label}
          </Link>
          <ChevronRight className="size-3.5 shrink-0" aria-hidden />
        </span>
      ))}
    </nav>
  );
}

export function Shell({ header, children, fill = false }: { header: ReactNode; children: ReactNode; fill?: boolean }) {
  const [menuOpen, setMenuOpen] = useState(false);
  const { pathname } = useLocation();

  useEffect(() => setMenuOpen(false), [pathname]);
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => event.key === "Escape" && setMenuOpen(false);
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, []);

  return (
    <div className={cx("flex min-h-screen", fill && "lg:h-screen lg:overflow-hidden")} data-menu-open={menuOpen ? "" : undefined}>
      <aside className="sticky top-0 hidden h-screen w-64 shrink-0 flex-col bg-surface lg:flex">
        <Sidebar />
      </aside>
      <div className="nav-scrim fixed inset-0 z-39 bg-black/15 lg:hidden" onClick={() => setMenuOpen(false)} />
      <aside className="nav-drawer fixed inset-y-0 left-0 z-40 flex w-70 flex-col bg-surface shadow-modal dark:border-r dark:border-border lg:hidden" aria-label="Menu" inert={!menuOpen}>
        <button type="button" className="sr-only" onClick={() => setMenuOpen(false)}>
          Đóng menu
        </button>
        <Sidebar onNavigate={() => setMenuOpen(false)} />
      </aside>
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-16 shrink-0 items-center gap-2 border-b border-border bg-surface px-4 sm:px-6">
          <button type="button" className={cx(button.icon, "-ml-1 lg:hidden")} aria-label="Mở menu" onClick={() => setMenuOpen(true)}>
            <Menu className="size-5" aria-hidden />
          </button>
          {header}
        </header>
        <main className={cx("flex-1", fill ? "p-3 sm:p-4 lg:min-h-0" : "px-4 py-5 sm:px-6 sm:py-6")}>{children}</main>
      </div>
    </div>
  );
}
