import Button from "../components/Button";
import DocumentItem from "../components/DocumentItem";
import Loader from "../components/Loader";
import { useDocuments } from "../hooks/useDocuments";

function DocumentsPage() {
  const { documents, isLoading, error, isDeleting, refreshDocuments, deleteDocument } = useDocuments();

  return (
    <section className="mx-auto max-w-5xl px-4 py-8 sm:px-6 lg:px-8">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-muted">Knowledge Base</p>
          <h1 className="text-2xl font-bold text-ink sm:text-3xl">Manage Documents</h1>
        </div>

        <Button variant="secondary" onClick={refreshDocuments} isLoading={isLoading}>
          Refresh list
        </Button>
      </div>

      <div className="rounded-2xl border border-border bg-card/95 p-4 shadow-soft sm:p-6">
        {isLoading ? (
          <Loader label="Loading documents..." className="py-6" />
        ) : error ? (
          <div className="space-y-3 rounded-xl bg-danger/10 p-4">
            <p className="text-sm text-danger">{error}</p>
            <Button size="sm" onClick={refreshDocuments}>
              Try again
            </Button>
          </div>
        ) : documents.length === 0 ? (
          <div className="rounded-xl border border-dashed border-border bg-surface/70 p-6 text-center">
            <h2 className="text-lg font-semibold text-ink">No documents yet</h2>
            <p className="mt-1 text-sm text-muted">
              Upload files from the Upload page to populate your RAG knowledge base.
            </p>
          </div>
        ) : (
          <ul className="space-y-3">
            {documents.map((document) => (
              <DocumentItem
                key={document.id}
                document={document}
                isDeleting={isDeleting === document.id}
                onDelete={deleteDocument}
              />
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}

export default DocumentsPage;
