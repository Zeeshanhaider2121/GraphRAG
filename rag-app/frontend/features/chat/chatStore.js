import { create } from "zustand";

export const useChatStore = create((set) => ({
  messages: [],
  isLoading: false,
  error: "",
  appendMessage: (message) =>
    set((state) => ({
      messages: [...state.messages, message],
    })),
  setLoading: (isLoading) => set({ isLoading }),
  setError: (error) => set({ error }),
  clearMessages: () => set({ messages: [] }),
}));
