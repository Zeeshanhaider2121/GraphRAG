import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import Button from "../components/Button";
import ChatInput from "../components/ChatInput";
import ChatMessage from "../components/ChatMessage";
import ChatBubble from "../components/ChatBubble";
import Loader from "../components/Loader";
import { useChat } from "../hooks/useChat";

const starterPrompts = [
  "Summarize key points from my uploaded documents.",
  "What are the top risks mentioned in the latest report?",
  "Compare findings across multiple sources with citations.",
];

function ChatPage() {
  const [inputValue, setInputValue] = useState("");
  const messagesEndRef = useRef(null);
  const { messages, isLoading, error, sendMessage, clearChat } = useChat();

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  const handleSubmit = async () => {
    if (!inputValue.trim() || isLoading) return;
    const query = inputValue;
    setInputValue("");
    await sendMessage(query);
  };

  return (
    <section className="mx-auto flex h-[calc(100vh-4.5rem)] max-w-5xl flex-col px-4 pb-5 pt-4 sm:px-6 lg:h-[calc(100vh-2rem)] lg:px-8">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-border bg-card/95 px-4 py-3">
        <div>
          <h1 className="text-lg font-bold text-ink sm:text-xl">Ask your knowledge base</h1>
          <p className="text-xs text-muted sm:text-sm">
            Grok-style flow with grounded answers and source citations.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Link
            to="/upload"
            className="inline-flex h-9 items-center justify-center rounded-xl bg-accent-soft px-3 text-sm font-semibold text-accent transition-colors hover:bg-accent-soft/80"
          >
            Upload Docs
          </Link>
          <Button
            variant="ghost"
            size="sm"
            onClick={clearChat}
            disabled={messages.length === 0 || isLoading}
          >
            Clear chat
          </Button>
        </div>
      </div>

      <div className="flex min-h-0 flex-1 flex-col overflow-hidden rounded-2xl border border-border bg-card/95 shadow-soft">
        <div className="message-scroll flex-1 space-y-4 overflow-y-auto p-4 sm:p-6">
          {messages.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-border bg-surface/70 p-6">
              <h2 className="text-xl font-semibold text-ink">What do you want to learn today?</h2>
              <p className="mt-2 max-w-2xl text-sm text-muted">
                Start with a question, or upload new documents so answers stay grounded in your own
                context.
              </p>

              <div className="mt-4 flex flex-wrap gap-2">
                {starterPrompts.map((prompt) => (
                  <button
                    key={prompt}
                    type="button"
                    onClick={() => setInputValue(prompt)}
                    className="rounded-full border border-border bg-card px-3 py-1.5 text-xs font-medium text-muted transition-colors hover:bg-surface hover:text-ink"
                  >
                    {prompt}
                  </button>
                ))}
              </div>

              <div className="mt-4">
                <Link
                  to="/upload"
                  className="inline-flex h-10 items-center justify-center rounded-xl bg-accent px-4 text-sm font-semibold text-white transition-colors hover:brightness-95"
                >
                  Upload Documents
                </Link>
              </div>
            </div>
          ) : null}

          {messages.map((message) => (
            <ChatMessage key={message.id} message={message} />
          ))}

          {isLoading ? (
            <div className="flex gap-3">
              <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-surface text-[11px] font-bold uppercase text-accent">
                AI
              </div>
              <div className="max-w-2xl">
                <ChatBubble role="assistant">
                  <Loader label="Thinking..." />
                </ChatBubble>
              </div>
            </div>
          ) : null}

          <div ref={messagesEndRef} />
        </div>

        {error ? (
          <div className="border-t border-border bg-danger/10 px-4 py-2 text-sm text-danger sm:px-6">
            {error}
          </div>
        ) : null}

        <div className="border-t border-border bg-card p-3 sm:p-4">
          <ChatInput
            value={inputValue}
            onChange={setInputValue}
            onSubmit={handleSubmit}
            disabled={isLoading}
          />
        </div>
      </div>
    </section>
  );
}

export default ChatPage;
