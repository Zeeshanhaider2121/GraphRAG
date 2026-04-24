import { useCallback } from "react";
import { sendQuery } from "../services/chatApi";
import { getApiErrorMessage } from "../utils/errors";
import {
  createAssistantErrorMessage,
  createUserMessage,
  mapQueryResponseToAssistantMessage,
} from "../features/chat/chatMappers";
import { useChatStore } from "../features/chat/chatStore";

export function useChat() {
  const messages = useChatStore((state) => state.messages);
  const isLoading = useChatStore((state) => state.isLoading);
  const error = useChatStore((state) => state.error);
  const appendMessage = useChatStore((state) => state.appendMessage);
  const setLoading = useChatStore((state) => state.setLoading);
  const setError = useChatStore((state) => state.setError);
  const clearMessages = useChatStore((state) => state.clearMessages);

  const sendMessage = useCallback(
    async (text) => {
      const query = text.trim();
      if (!query) return;

      appendMessage(createUserMessage(query));
      setLoading(true);
      setError("");

      try {
        const response = await sendQuery({ query, topK: 5 });
        const assistantMessage = mapQueryResponseToAssistantMessage(response, query);
        appendMessage(assistantMessage);
      } catch (errorResponse) {
        const errorMessage = getApiErrorMessage(
          errorResponse,
          "The assistant is temporarily unavailable. Please try again."
        );
        setError(errorMessage);
        appendMessage(createAssistantErrorMessage(errorMessage));
      } finally {
        setLoading(false);
      }
    },
    [appendMessage, setError, setLoading]
  );

  const clearChat = useCallback(() => {
    clearMessages();
    setError("");
  }, [clearMessages, setError]);

  return {
    messages,
    isLoading,
    error,
    sendMessage,
    clearChat,
  };
}
