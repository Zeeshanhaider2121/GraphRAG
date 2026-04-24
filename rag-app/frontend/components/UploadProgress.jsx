function UploadProgress({ progress = 0, isUploading = false }) {
  return (
    <div className="rounded-xl border border-border bg-surface/70 p-3">
      <div className="mb-2 flex items-center justify-between text-xs font-semibold">
        <span className="text-ink">{isUploading ? "Uploading..." : "Upload complete"}</span>
        <span className="text-muted">{progress}%</span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-card">
        <div
          className="h-full rounded-full bg-accent transition-all duration-300"
          style={{ width: `${Math.min(progress, 100)}%` }}
        />
      </div>
    </div>
  );
}

export default UploadProgress;
