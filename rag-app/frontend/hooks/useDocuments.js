import { useCallback, useEffect, useState } from "react";
import {
  deleteDocument as deleteDocumentRequest,
  fetchDocuments,
} from "../services/documentsApi";
import { mapDocumentListResponse } from "../features/documents/documentMappers";
import { getApiErrorMessage } from "../utils/errors";

export function useDocuments() {
  const [documents, setDocuments] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [deletingId, setDeletingId] = useState("");

  const refreshDocuments = useCallback(async () => {
    setIsLoading(true);
    setError("");
    try {
      const payload = await fetchDocuments();
      setDocuments(mapDocumentListResponse(payload));
    } catch (errorResponse) {
      setError(getApiErrorMessage(errorResponse, "Could not load documents."));
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    refreshDocuments();
  }, [refreshDocuments]);

  const removeDocument = useCallback(async (docId) => {
    if (!docId) return;
    setDeletingId(docId);
    setError("");
    try {
      await deleteDocumentRequest(docId);
      setDocuments((current) => current.filter((doc) => doc.id !== docId));
    } catch (errorResponse) {
      setError(getApiErrorMessage(errorResponse, "Could not delete this document."));
    } finally {
      setDeletingId("");
    }
  }, []);

  return {
    documents,
    isLoading,
    error,
    isDeleting: deletingId,
    refreshDocuments,
    deleteDocument: removeDocument,
  };
}
