import { Play, Activity } from 'lucide-react';
import { useAppStore } from '../../stores';

export function Header() {
  const { sidebarOpen } = useAppStore();

  return (
    <header className="bg-white border-b border-gray-200 h-16 flex items-center justify-between px-6 sticky top-0 z-10">
      <div className={sidebarOpen ? "" : "ml-4"}>
        <Activity className="w-5 h-5 text-green-500 inline mr-2" />
        <span className="text-sm text-gray-600">Sistema pronto</span>
      </div>
      
      <button className="flex items-center gap-2 bg-primary-600 hover:bg-primary-700 text-white px-4 py-2 rounded-lg font-medium transition-colors">
        <Play size={18} />
        <span>Executar Pipeline</span>
      </button>
    </header>
  );
}
