import { Link } from "react-router-dom";

const quickPrompts = [
  "Summarize all uploaded docs in bullet points.",
  "Find contradictions across my sources.",
  "Generate a decision memo with cited evidence.",
];

const overviewCards = [
  {
    title: "Grounded Chat",
    description: "Ask anything and get answers linked to your retrieved source chunks.",
  },
  {
    title: "Document Control",
    description: "Review and delete indexed files from your workspace instantly.",
  },
  {
    title: "Fast Ingestion",
    description: "Upload PDFs and DOC files to continuously improve retrieval context.",
  },
];

function HomePage() {
  return (
    <section className="mx-auto max-w-5xl px-4 py-8 sm:px-6 lg:px-10">
      <article className="rounded-3xl border border-border bg-card/95 p-6 shadow-soft sm:p-8 lg:p-10">
        <p className="text-xs font-semibold uppercase tracking-[0.24em] text-muted">Workspace Overview</p>
        <h1 className="mt-3 text-3xl font-extrabold tracking-tight text-ink sm:text-4xl lg:text-5xl">
          What should we explore today?
        </h1>
        <p className="mt-3 max-w-3xl text-base text-muted sm:text-lg">
          Grok-style overview, tuned for your RAG flow. Start chatting with context, upload fresh
          files, and manage evidence-backed answers from one place.
        </p>

        <div className="mt-6 rounded-2xl border border-border bg-surface/65 p-4 sm:p-5">
          <p className="text-sm text-muted">Ask a question or choose an action:</p>
          <div className="mt-3 flex flex-wrap gap-2">
            {quickPrompts.map((prompt) => (
              <Link
                key={prompt}
                to="/chat"
                className="rounded-full border border-border bg-card px-3 py-1.5 text-xs font-medium text-muted transition-colors hover:bg-surface hover:text-ink"
              >
                {prompt}
              </Link>
            ))}
          </div>

          <div className="mt-5 flex flex-wrap gap-3">
            <Link
              to="/chat"
              className="inline-flex h-11 items-center justify-center rounded-xl bg-accent px-5 text-sm font-semibold text-white transition hover:brightness-95"
            >
              Open Chat
            </Link>
            <Link
              to="/upload"
              className="inline-flex h-11 items-center justify-center rounded-xl bg-accent-soft px-5 text-sm font-semibold text-accent transition hover:bg-accent-soft/80"
            >
              Upload Documents
            </Link>
          </div>
        </div>
      </article>

      <div className="mt-5 grid gap-4 md:grid-cols-3">
        {overviewCards.map((card) => (
          <article key={card.title} className="rounded-2xl border border-border bg-card/95 p-5 shadow-sm">
            <h2 className="text-lg font-bold text-ink">{card.title}</h2>
            <p className="mt-2 text-sm text-muted">{card.description}</p>
          </article>
        ))}
      </div>
    </section>
  );
}

export default HomePage;
