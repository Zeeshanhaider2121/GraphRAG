import { useState } from "react";
import Button from "../components/Button";

function SettingsPage() {
  const [citeMode, setCiteMode] = useState(true);
  const [compactView, setCompactView] = useState(false);
  const [autoScroll, setAutoScroll] = useState(true);

  return (
    <section className="mx-auto max-w-3xl px-4 py-8 sm:px-6 lg:px-8">
      <article className="rounded-3xl border border-border bg-card/95 p-6 shadow-soft sm:p-8">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-muted">Preferences</p>
        <h1 className="mt-2 text-2xl font-bold text-ink sm:text-3xl">Settings</h1>
        <p className="mt-2 text-sm text-muted">
          Configure workspace behavior for chat and retrieval experience.
        </p>

        <div className="mt-6 space-y-3">
          <label className="flex items-center justify-between rounded-xl border border-border bg-surface/60 px-4 py-3">
            <span className="text-sm font-medium text-ink">Always show source citations</span>
            <input type="checkbox" checked={citeMode} onChange={() => setCiteMode((v) => !v)} />
          </label>

          <label className="flex items-center justify-between rounded-xl border border-border bg-surface/60 px-4 py-3">
            <span className="text-sm font-medium text-ink">Compact page density</span>
            <input type="checkbox" checked={compactView} onChange={() => setCompactView((v) => !v)} />
          </label>

          <label className="flex items-center justify-between rounded-xl border border-border bg-surface/60 px-4 py-3">
            <span className="text-sm font-medium text-ink">Auto-scroll chat on new messages</span>
            <input type="checkbox" checked={autoScroll} onChange={() => setAutoScroll((v) => !v)} />
          </label>
        </div>

        <div className="mt-6">
          <Button>Save settings</Button>
        </div>
      </article>
    </section>
  );
}

export default SettingsPage;
