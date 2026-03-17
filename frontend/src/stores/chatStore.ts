import { create } from "zustand";
import type { ChatResponse } from "@/types";
import { sendChatMessage } from "@/lib/api";

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  actions?: ChatResponse["actions"];
}

interface ChatState {
  messages: ChatMessage[];
  loading: boolean;
  sendMessage: (message: string) => Promise<void>;
}

export const useChatStore = create<ChatState>((set) => ({
  messages: [],
  loading: false,

  sendMessage: async (message) => {
    set((state) => ({
      messages: [...state.messages, { role: "user", content: message }],
      loading: true,
    }));
    const response = await sendChatMessage(message);
    set((state) => ({
      messages: [
        ...state.messages,
        {
          role: "assistant",
          content: response.message,
          actions: response.actions,
        },
      ],
      loading: false,
    }));
  },
}));
