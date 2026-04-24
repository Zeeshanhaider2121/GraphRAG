import { cn } from "../utils/cn";

const variantClasses = {
  primary:
    "bg-accent text-white shadow-soft hover:brightness-95 focus-visible:ring-accent/40",
  secondary:
    "bg-accent-soft text-accent hover:bg-accent-soft/80 focus-visible:ring-accent/30",
  ghost: "bg-transparent text-ink hover:bg-surface focus-visible:ring-accent/30",
  danger: "bg-danger text-white hover:brightness-95 focus-visible:ring-danger/35",
};

const sizeClasses = {
  sm: "h-9 px-3 text-sm",
  md: "h-11 px-4 text-sm",
  lg: "h-12 px-5 text-base",
};

function Button({
  children,
  variant = "primary",
  size = "md",
  className = "",
  isLoading = false,
  disabled = false,
  type = "button",
  ...props
}) {
  return (
    <button
      type={type}
      disabled={disabled || isLoading}
      className={cn(
        "inline-flex items-center justify-center gap-2 rounded-xl font-semibold transition-colors focus-visible:outline-none focus-visible:ring-2 disabled:cursor-not-allowed disabled:opacity-60",
        variantClasses[variant] || variantClasses.primary,
        sizeClasses[size] || sizeClasses.md,
        className
      )}
      {...props}
    >
      {isLoading ? (
        <span className="h-4 w-4 animate-spin rounded-full border-2 border-current border-r-transparent" />
      ) : null}
      <span>{children}</span>
    </button>
  );
}

export default Button;
