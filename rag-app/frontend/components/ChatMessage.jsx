import ChatBubble from "./ChatBubble";
import MarkdownRenderer from "./MarkdownRenderer";
import SourceCard from "./SourceCard";
import { cn } from "../utils/cn";
import { formatMessageTime } from "../utils/formatters";

function Avatar({ role }) {
  const isUser = role === "user";
  return (
    <div
      className={cn(
        "flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-[11px] font-bold uppercase",
        isUser ? "bg-accent text-white" : "bg-surface text-accent"
      )}
    >
      {isUser ? "You" : "AI"}
    </div>
  );
}

export default function ChatMessage({ message }) {
  const isUser = message.role === "user";
  const hasSourceBox = message.sourceBox && message.sourceBox.trim().length > 0;
  const safeSources = (message.sources || []).filter(Boolean);

  return (
    <article className={cn("flex gap-3", isUser ? "justify-end" : "justify-start")}>
      {!isUser && <Avatar role={message.role} />}

      <div className={cn("max-w-3xl", isUser ? "items-end" : "items-start")}>

        {/* ✅ Pass message.text as a plain string — ChatBubble routes it to MarkdownRenderer */}
        <ChatBubble role={message.role}>{message.text}</ChatBubble>

        {/* ✅ sourceBox now rendered through MarkdownRenderer so LaTeX shows here too */}
        {hasSourceBox && (
          <div className="mt-2 rounded-xl border border-border bg-surface p-3 text-xs text-muted">
            <MarkdownRenderer>{message.sourceBox}</MarkdownRenderer>
          </div>
        )}

        {/* Source Cards */}
        {safeSources.length > 0 && (
          <div className="mt-2 space-y-2">
            <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted">
              Sources
            </p>
            <div className="grid gap-2">
              {safeSources.map((source) => (
                <SourceCard key={source.id} source={source} />
              ))}
            </div>
          </div>
        )}

        <p className={cn("mt-1 text-xs text-muted", isUser ? "text-right" : "text-left")}>
          {formatMessageTime(message.timestamp)}
        </p>
      </div>

      {isUser && <Avatar role={message.role} />}
    </article>
  );
}