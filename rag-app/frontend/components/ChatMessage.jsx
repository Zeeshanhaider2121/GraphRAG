import ChatBubble from "./ChatBubble";
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

function ChatMessage({ message }) {
  const isUser = message.role === "user";
  const hasSources = Array.isArray(message.sources) && message.sources.length > 0;

  return (
    <article className={cn("flex gap-3", isUser ? "justify-end" : "justify-start")}>
      {!isUser ? <Avatar role={message.role} /> : null}

      <div className={cn("max-w-3xl", isUser ? "items-end" : "items-start")}>
        <ChatBubble role={message.role}>
          <p className="whitespace-pre-wrap">{message.text}</p>
        </ChatBubble>

        {hasSources ? (
          <div className="mt-2 space-y-2">
            <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted">Sources</p>
            <div className="grid gap-2">
              {message.sources.map((source) => (
                <SourceCard key={source.id} source={source} />
              ))}
            </div>
          </div>
        ) : null}

        <p className={cn("mt-1 text-xs text-muted", isUser ? "text-right" : "text-left")}>
          {formatMessageTime(message.timestamp)}
        </p>
      </div>

      {isUser ? <Avatar role={message.role} /> : null}
    </article>
  );
}

export default ChatMessage;
