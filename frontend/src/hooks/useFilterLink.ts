import { create } from 'zustand';

interface FilterState {
  filters: Record<string, string | null>;
  setFilter: (field: string, value: string | null) => void;
  clearFilters: () => void;
  hasActiveFilters: () => boolean;
}

export const useFilterStore = create<FilterState>((set, get) => ({
  filters: {},
  setFilter: (field, value) => set((s) => ({
    filters: { ...s.filters, [field]: value },
  })),
  clearFilters: () => set({ filters: {} }),
  hasActiveFilters: () => Object.values(get().filters).some(v => v !== null),
}));
