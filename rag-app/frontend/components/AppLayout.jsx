import { useEffect, useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import { cn } from "../utils/cn";

const primaryLinks = [
  {
    to: "/",
    label: "Home",
    icon: (
      <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M3 10.5 12 3l9 7.5" />
        <path d="M5 9.5V21h14V9.5" />
      </svg>
    ),
  },
  {
    to: "/chat",
    label: "Chat",
    icon: (
      <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M4 5h16v10H7l-3 3V5z" />
      </svg>
    ),
  },
  {
    to: "/documents",
    label: "Documents",
    icon: (
      <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M6 3h9l3 3v15H6V3z" />
        <path d="M15 3v4h4" />
        <path d="M9 12h6M9 16h6" />
      </svg>
    ),
  },
];

const accountLinks = [
  {
    to: "/settings",
    label: "Settings",
    icon: (
      <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M12 15.5a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7Z" />
        <path d="m19.4 15 1.2 2-2.1 2.1-2-1.2a7.7 7.7 0 0 1-2 .8L14 21h-3l-.5-2.3a7.7 7.7 0 0 1-2-.8l-2 1.2L4.4 17l1.2-2a7.8 7.8 0 0 1 0-2l-1.2-2 2.1-2.1 2 1.2a7.7 7.7 0 0 1 2-.8L11 3h3l.5 2.3a7.7 7.7 0 0 1 2 .8l2-1.2L20.6 7l-1.2 2a7.8 7.8 0 0 1 0 2Z" />
      </svg>
    ),
  },
  {
    to: "/login",
    label: "Login",
    icon: (
      <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M10 17H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5" />
        <path d="m14 7 5 5-5 5" />
        <path d="M19 12H8" />
      </svg>
    ),
  },
  {
    to: "/signup",
    label: "Signup",
    icon: (
      <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
        <circle cx="8.5" cy="7" r="4" />
        <path d="M20 8v6M17 11h6" />
      </svg>
    ),
  },
];

function SidebarLinkList({ links, onItemClick }) {
  return (
    <div className="space-y-1.5">
      {links.map((link) => (
        <NavLink
          key={link.to}
          to={link.to}
          onClick={onItemClick}
          className={({ isActive }) =>
            cn(
              "group flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-semibold transition-colors",
              isActive
                ? "bg-accent text-white"
                : "text-muted hover:bg-surface hover:text-ink"
            )
          }
        >
          <span className="shrink-0">{link.icon}</span>
          <span>{link.label}</span>
        </NavLink>
      ))}
    </div>
  );
}

function SidebarAccount({ onItemClick }) {
  return (
    <div className="mt-4 border-t border-border/70 px-3 pb-4 pt-4">
      <p className="px-3 text-[11px] font-semibold uppercase tracking-[0.18em] text-muted">Account</p>
      <div className="mt-2">
        <SidebarLinkList links={accountLinks} onItemClick={onItemClick} />
      </div>
    </div>
  );
}

function SidebarCard() {
  return (
    <article className="mx-3 mt-4 rounded-2xl border border-border bg-accent-soft/75 p-4">
      <p className="text-sm font-bold text-ink">RAG Workspace</p>
      <p className="mt-2 text-sm text-muted">
        Chat with indexed data, upload inside chat, and manage citations confidently.
      </p>
    </article>
  );
}

function AppLayout() {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const location = useLocation();

  useEffect(() => {
    setIsSidebarOpen(false);
  }, [location.pathname]);

  useEffect(() => {
    const onKeyDown = (event) => {
      if (event.key === "Escape") {
        setIsSidebarOpen(false);
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  return (
    <div className="relative min-h-screen overflow-x-hidden">
      <div className="pointer-events-none absolute left-0 top-0 h-[24rem] w-[24rem] rounded-full bg-accent/10 blur-3xl" />
      <div className="pointer-events-none absolute bottom-[-4rem] right-[-2rem] h-[20rem] w-[20rem] rounded-full bg-[#b7dcca] blur-3xl" />

      <div className="relative z-10 flex min-h-screen">
        <aside className="hidden w-72 shrink-0 border-r border-border/80 bg-card/85 backdrop-blur-sm lg:flex lg:flex-col">
          <div className="border-b border-border/80 px-6 py-6">
            <p className="text-xs font-semibold uppercase tracking-[0.22em] text-muted">GraphRAG</p>
            <p className="mt-1 text-2xl font-extrabold text-ink">Knowledge Workspace</p>
          </div>

          <div className="flex min-h-0 flex-1 flex-col overflow-y-auto py-3">
            <div className="px-3">
              <SidebarLinkList links={primaryLinks} />
            </div>
            <div className="mt-auto">
              <SidebarCard />
              <SidebarAccount />
            </div>
          </div>
        </aside>

        <div className="flex min-h-screen min-w-0 flex-1 flex-col">
          <header className="sticky top-0 z-20 border-b border-border/80 bg-page/90 px-4 py-3 backdrop-blur-sm lg:hidden">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-muted">
                  GraphRAG
                </p>
                <p className="text-base font-bold text-ink">Knowledge Workspace</p>
              </div>

              <button
                type="button"
                onClick={() => setIsSidebarOpen((open) => !open)}
                className="inline-flex h-10 w-10 items-center justify-center rounded-lg border border-border bg-card text-ink"
                aria-label="Toggle sidebar"
                aria-expanded={isSidebarOpen}
              >
                <svg
                  viewBox="0 0 24 24"
                  className="h-5 w-5"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                >
                  <path d="M3 7h18M3 12h18M3 17h18" />
                </svg>
              </button>
            </div>
          </header>

          <main className="relative z-10 flex-1">
            <Outlet />
          </main>
        </div>
      </div>

      {isSidebarOpen ? (
        <div className="fixed inset-0 z-40 bg-ink/30 lg:hidden" onClick={() => setIsSidebarOpen(false)} />
      ) : null}

      <aside
        className={cn(
          "fixed left-0 top-0 z-50 flex h-screen w-72 flex-col border-r border-border/80 bg-card/95 shadow-xl backdrop-blur-sm transition-transform lg:hidden",
          isSidebarOpen ? "translate-x-0" : "-translate-x-full"
        )}
      >
        <div className="flex items-center justify-between border-b border-border/80 px-6 py-6">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.22em] text-muted">GraphRAG</p>
            <p className="mt-1 text-2xl font-extrabold text-ink">Workspace</p>
          </div>
          <button
            type="button"
            onClick={() => setIsSidebarOpen(false)}
            className="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-border bg-card text-ink"
            aria-label="Close sidebar"
          >
            <svg
              viewBox="0 0 24 24"
              className="h-4 w-4"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              <path d="m6 6 12 12M18 6 6 18" />
            </svg>
          </button>
        </div>

        <div className="flex min-h-0 flex-1 flex-col overflow-y-auto py-3">
          <div className="px-3">
            <SidebarLinkList links={primaryLinks} onItemClick={() => setIsSidebarOpen(false)} />
          </div>
          <div className="mt-auto">
            <SidebarCard />
            <SidebarAccount onItemClick={() => setIsSidebarOpen(false)} />
          </div>
        </div>
      </aside>
    </div>
  );
}

export default AppLayout;
