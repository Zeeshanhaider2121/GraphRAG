import { cn } from "../utils/cn";

function Input({ label, error, className = "", ...props }) {
  return (
    <label className="block w-full">
      {label ? <span className="mb-2 block text-sm font-semibold text-ink">{label}</span> : null}
      <input
        className={cn(
          "w-full rounded-xl border border-border bg-white px-3 py-2.5 text-sm text-ink placeholder:text-muted focus:border-accent/60 focus:outline-none focus:ring-2 focus:ring-accent/25",
          error ? "border-danger focus:border-danger focus:ring-danger/20" : "",
          className
        )}
        {...props}
      />
      {error ? <span className="mt-1 block text-xs text-danger">{error}</span> : null}
    </label>
  );
}

export default Input;
