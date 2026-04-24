import { truncateText } from "../utils/formatters";

function SourceCard({ source }) {
  const scoreLabel =
    source?.score || source?.score === 0
      ? `${Math.round(Number(source.score) * 100)}% match`
      : "";

  return (
    <article className="rounded-xl border border-border bg-surface/60 px-3 py-2.5">
      <div className="mb-1 flex flex-wrap items-center gap-2">
        <h4 className="text-xs font-semibold text-ink">{source?.title || "Source"}</h4>
        {scoreLabel ? (
          <span className="rounded-full bg-accent-soft px-2 py-0.5 text-[11px] font-semibold text-accent">
            {scoreLabel}
          </span>
        ) : null}
        {source?.page || source?.page === 0 ? (
          <span className="rounded-full bg-card px-2 py-0.5 text-[11px] font-semibold text-muted">
            Page {source.page}
          </span>
        ) : null}
      </div>

      {source?.snippet ? <p className="text-xs text-muted">{truncateText(source.snippet, 220)}</p> : null}

      {source?.url ? (
        <a
          href={source.url}
          target="_blank"
          rel="noreferrer"
          className="mt-2 inline-block text-xs font-semibold text-accent underline-offset-2 hover:underline"
        >
          Open source
        </a>
      ) : null}
    </article>
  );
}

export default SourceCard;
