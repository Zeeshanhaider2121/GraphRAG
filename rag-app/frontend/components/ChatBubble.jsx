import { cn } from "../utils/cn";

function ChatBubble({ role = "assistant", children }) {
  const isUser = role === "user";

  return (
    <div
      className={cn(
        "rounded-2xl border px-4 py-3 text-sm leading-relaxed shadow-sm sm:text-[0.95rem]",
        isUser
          ? "border-accent bg-accent text-white"
          : "border-border bg-card text-ink"
      )}
    >
      {children}
    </div>
  );
}

export default ChatBubble;
