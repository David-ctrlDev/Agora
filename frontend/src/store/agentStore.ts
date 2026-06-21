import { create } from "zustand";

interface AgentStore {
  activeConversationId: number | null;
  setActiveConversationId: (id: number) => void;
  isOpen: boolean;
  open: () => void;
  close: () => void;
  toggle: () => void;
}

export const useAgentStore = create<AgentStore>((set) => ({
  activeConversationId: null,
  setActiveConversationId: (id) => set({ activeConversationId: id }),
  isOpen: false,
  open: () => set({ isOpen: true }),
  close: () => set({ isOpen: false }),
  toggle: () => set((state) => ({ isOpen: !state.isOpen })),
}));
