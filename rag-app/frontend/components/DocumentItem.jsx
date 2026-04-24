import Button from "./Button";
import { formatDate, formatFileSize } from "../utils/formatters";

function DocumentItem({ document, onDelete, isDeleting }) {
  return (
    <li className="flex flex-col gap-4 rounded-xl border border-border bg-card p-4 sm:flex-row sm:items-center sm:justify-between">
      <div className="space-y-1">
        <h3 className="text-base font-semibold text-ink">{document.name}</h3>
        <p className="text-sm text-muted">Source: {document.source || "N/A"}</p>
        <div className="flex flex-wrap gap-4 text-xs text-muted">
          <span>Created: {formatDate(document.createdAt)}</span>
          <span>Updated: {formatDate(document.updatedAt || document.createdAt)}</span>
          <span>Size: {formatFileSize(document.size)}</span>
        </div>
      </div>

      <Button
        variant="danger"
        size="sm"
        isLoading={Boolean(isDeleting)}
        onClick={() => onDelete(document.id)}
      >
        Delete
      </Button>
    </li>
  );
}

export default DocumentItem;
