import { useCallback, useState } from "react";
import { uploadDocument } from "../services/uploadApi";
import { getApiErrorMessage } from "../utils/errors";

export function useUpload() {
  const [uploadProgress, setUploadProgress] = useState(0);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState("");
  const [successMessage, setSuccessMessage] = useState("");

  const uploadFile = useCallback(async (file) => {
    if (!file) return null;

    setIsUploading(true);
    setUploadProgress(0);
    setError("");
    setSuccessMessage("");

    try {
      const response = await uploadDocument(file, (progressEvent) => {
        if (!progressEvent?.total) return;
        const progress = Math.round((progressEvent.loaded / progressEvent.total) * 100);
        setUploadProgress(progress);
      });

      setUploadProgress(100);
      setSuccessMessage(response?.message || `${file.name} uploaded successfully.`);
      return response;
    } catch (errorResponse) {
      const message = getApiErrorMessage(errorResponse, "Upload failed. Please try again.");
      setError(message);
      throw errorResponse;
    } finally {
      setIsUploading(false);
    }
  }, []);

  const resetStatus = useCallback(() => {
    setUploadProgress(0);
    setError("");
    setSuccessMessage("");
  }, []);

  return {
    uploadProgress,
    isUploading,
    error,
    successMessage,
    uploadFile,
    resetStatus,
  };
}
