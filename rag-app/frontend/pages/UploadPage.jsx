import { useMemo, useState } from "react";
import Button from "../components/Button";
import Input from "../components/Input";
import UploadProgress from "../components/UploadProgress";
import { useUpload } from "../hooks/useUpload";
import { formatFileSize } from "../utils/formatters";

const ACCEPTED_EXTENSIONS = [".pdf", ".doc", ".docx"];

function UploadPage() {
  const [selectedFile, setSelectedFile] = useState(null);
  const { uploadProgress, isUploading, error, successMessage, uploadFile, resetStatus } = useUpload();

  const acceptedTypesLabel = useMemo(() => ACCEPTED_EXTENSIONS.join(", "), []);

  const handleFileSelect = (event) => {
    const file = event.target.files?.[0] || null;
    setSelectedFile(file);
    resetStatus();
  };

  const handleUpload = async (event) => {
    event.preventDefault();
    if (!selectedFile || isUploading) return;
    await uploadFile(selectedFile);
  };

  return (
    <section className="mx-auto max-w-3xl px-4 py-8 sm:px-6 lg:px-8">
      <div className="rounded-3xl border border-border bg-card/95 p-6 shadow-soft sm:p-8">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-muted">Ingestion</p>
        <h1 className="mt-2 text-2xl font-bold text-ink sm:text-3xl">Upload Knowledge Documents</h1>
        <p className="mt-2 text-sm text-muted">
          Add files to the RAG index. Supported formats: {acceptedTypesLabel}.
        </p>

        <form onSubmit={handleUpload} className="mt-6 space-y-4">
          <Input
            type="file"
            accept={ACCEPTED_EXTENSIONS.join(",")}
            onChange={handleFileSelect}
            disabled={isUploading}
          />

          {selectedFile ? (
            <div className="rounded-xl border border-border bg-surface/70 p-3 text-sm">
              <p className="font-semibold text-ink">{selectedFile.name}</p>
              <p className="text-xs text-muted">Size: {formatFileSize(selectedFile.size)}</p>
            </div>
          ) : null}

          {(isUploading || uploadProgress > 0) && (
            <UploadProgress progress={uploadProgress} isUploading={isUploading} />
          )}

          {error ? <p className="rounded-lg bg-danger/10 px-3 py-2 text-sm text-danger">{error}</p> : null}

          {successMessage ? (
            <p className="rounded-lg bg-accent-soft px-3 py-2 text-sm font-medium text-accent">
              {successMessage}
            </p>
          ) : null}

          <div className="flex flex-wrap gap-3">
            <Button type="submit" isLoading={isUploading} disabled={!selectedFile}>
              Upload file
            </Button>
            <Button
              type="button"
              variant="ghost"
              onClick={() => {
                setSelectedFile(null);
                resetStatus();
              }}
              disabled={isUploading && uploadProgress > 0}
            >
              Reset
            </Button>
          </div>
        </form>
      </div>
    </section>
  );
}

export default UploadPage;
