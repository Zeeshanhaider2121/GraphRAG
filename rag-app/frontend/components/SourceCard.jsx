import { useState } from "react";
import { truncateText } from "../utils/formatters";
import MarkdownRenderer from "./MarkdownRenderer";

export default function SourceCard({ source }) {
  const [expanded, setExpanded] = useState(false);

  // Guard clause
  if (!source) return null;

  const snippet = source.snippet || "";
  const title = source.title || "Source";
  const scoreLabel =
    source.score || source.score === 0
      ? `${Math.round(Number(source.score) * 100)}% match`
      : "";
  const needsToggle = snippet.length > 500;

  // The text to display – truncated when collapsed
  const displayedText = expanded || !needsToggle
    ? snippet
    : truncateText(snippet, 500);

  return (
    <article className="rounded-xl border border-border bg-surface/60 px-3 py-2.5">
      <div className="mb-1 flex flex-wrap items-center gap-2">
        <h4 className="text-xs font-semibold text-ink">{title}</h4>
        {scoreLabel && (
          <span className="rounded-full bg-accent-soft px-2 py-0.5 text-[11px] font-semibold text-accent">
            {scoreLabel}
          </span>
        )}
        {(source.page || source.page === 0) && (
          <span className="rounded-full bg-card px-2 py-0.5 text-[11px] font-semibold text-muted">
            Page {source.page}
          </span>
        )}
      </div>

      {snippet && (
        <>
          {/* The snippet is now rendered through MarkdownRenderer so LaTeX is displayed nicely */}
          <div className="text-xs text-muted whitespace-pre-wrap">
            <MarkdownRenderer>{displayedText}</MarkdownRenderer>
          </div>
          {needsToggle && (
            <button
              onClick={() => setExpanded((prev) => !prev)}
              className="mt-1 text-xs font-semibold text-accent underline-offset-2 hover:underline"
            >
              {expanded ? "Show less" : "Show more"}
            </button>
          )}
        </>
      )}

      {source.url && (
        <a
          href={source.url}
          target="_blank"
          rel="noreferrer"
          className="mt-2 inline-block text-xs font-semibold text-accent underline-offset-2 hover:underline"
        >
          Open source
        </a>
      )}
    </article>
  );
}