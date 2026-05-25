import { create } from 'zustand';
import type { FieldInfo } from '../types';

interface SessionStore {
  currentSessionId: string | null;
  fields: FieldInfo[];
  setSession: (id: string, fields: FieldInfo[]) => void;
  clearSession: () => void;
}

export const useSessionStore = create<SessionStore>((set) => ({
  currentSessionId: null,
  fields: [],
  setSession: (id, fields) => set({ currentSessionId: id, fields }),
  clearSession: () => set({ currentSessionId: null, fields: [] }),
}));
