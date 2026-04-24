import Button from "./Button";

function ChatInput({
  value,
  onChange,
  onSubmit,
  disabled = false,
  placeholder = "Ask a question about your knowledge base...",
}) {
  const handleSubmit = (event) => {
    event.preventDefault();
    if (disabled) return;
    onSubmit();
  };

  const handleKeyDown = (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      if (!disabled) {
        onSubmit();
      }
    }
  };

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-3 sm:flex-row sm:items-end">
      <label className="w-full">
        <span className="sr-only">Message</span>
        <textarea
          value={value}
          onChange={(event) => onChange(event.target.value)}
          onKeyDown={handleKeyDown}
          rows={2}
          disabled={disabled}
          placeholder={placeholder}
          className="w-full resize-none rounded-xl border border-border bg-white px-3 py-2.5 text-sm text-ink placeholder:text-muted focus:border-accent/60 focus:outline-none focus:ring-2 focus:ring-accent/25 disabled:cursor-not-allowed disabled:opacity-60"
        />
      </label>

      <Button type="submit" disabled={disabled || !value.trim()} className="sm:w-[120px]">
        Send
      </Button>
    </form>
  );
}

export default ChatInput;
