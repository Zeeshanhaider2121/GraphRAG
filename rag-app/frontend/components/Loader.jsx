import { cn } from "../utils/cn";

function Loader({ label = "Loading...", className = "" }) {
  return (
    <div className={cn("flex items-center gap-3 text-sm text-muted", className)}>
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-accent border-r-transparent" />
      <span>{label}</span>
    </div>
  );
}

export default Loader;
