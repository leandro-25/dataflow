import { create } from 'zustand';
import { Source } from '../types';

interface AppState {
  // Sources
  sources: Source[];
  setSources: (sources: Source[]) => void;
  
  // Sidebar
  sidebarOpen: boolean;
  toggleSidebar: () => void;
  
  // Current page
  currentPage: string;
  setCurrentPage: (page: string) => void;
}

export const useAppStore = create<AppState>((set) => ({
  sources: [],
  setSources: (sources) => set({ sources }),
  
  sidebarOpen: true,
  toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
  
  currentPage: 'home',
  setCurrentPage: (page) => set({ currentPage: page }),
}));
