import { Link, useLocation } from 'react-router-dom';
import { 
  Database, 
  Download, 
  Filter, 
  Box, 
  LayoutGrid, 
  BarChart3, 
  GitBranch, 
  BookOpen, 
  Settings,
  Play,
  ChevronLeft,
  ChevronRight
} from 'lucide-react';
import { useAppStore } from '../../stores';
import clsx from 'clsx';

const menuItems = [
  { id: 'home', label: 'Home', icon: LayoutGrid, path: '/' },
  { id: 'sources', label: 'Fontes de Dados', icon: Database, path: '/sources' },
  { id: 'ingestions', label: 'Ingestões', icon: Download, path: '/ingestions' },
  { id: 'staging', label: 'Staging', icon: Filter, path: '/staging' },
  { id: 'dimensions', label: 'Dimensões', icon: Box, path: '/dimensions' },
  { id: 'facts', label: 'Fatos', icon: Box, path: '/facts' },
  { id: 'metrics', label: 'Métricas', icon: BarChart3, path: '/metrics' },
  { id: 'dashboards', label: 'Dashboards', icon: LayoutGrid, path: '/dashboards' },
  { id: 'pipeline', label: 'Pipeline', icon: GitBranch, path: '/pipeline' },
  { id: 'catalog', label: 'Catálogo', icon: BookOpen, path: '/catalog' },
];

export function Sidebar() {
  const location = useLocation();
  const { sidebarOpen, toggleSidebar } = useAppStore();

  return (
    <aside 
      className={clsx(
        "bg-gray-900 text-white transition-all duration-300 flex flex-col",
        sidebarOpen ? "w-64" : "w-16"
      )}
    >
      <div className="p-4 flex items-center justify-between">
        {sidebarOpen && (
          <div className="flex items-center gap-2">
            <Database className="w-6 h-6 text-primary-400" />
            <span className="font-bold text-lg">Dataflow</span>
          </div>
        )}
        <button 
          onClick={toggleSidebar}
          className="p-1 hover:bg-gray-800 rounded-lg transition-colors"
        >
          {sidebarOpen ? <ChevronLeft size={20} /> : <ChevronRight size={20} />}
        </button>
      </div>

      <nav className="flex-1 px-2 py-4 space-y-1">
        {menuItems.map((item) => {
          const Icon = item.icon;
          const isActive = location.pathname === item.path || 
                          (item.path !== '/' && location.pathname.startsWith(item.path));
          
          return (
            <Link
              key={item.id}
              to={item.path}
              className={clsx(
                "flex items-center gap-3 px-3 py-2 rounded-lg transition-colors",
                isActive 
                  ? "bg-primary-600 text-white" 
                  : "text-gray-400 hover:bg-gray-800 hover:text-white"
              )}
              title={!sidebarOpen ? item.label : undefined}
            >
              <Icon size={20} />
              {sidebarOpen && <span>{item.label}</span>}
            </Link>
          );
        })}
      </nav>

      <div className="p-2 border-t border-gray-800">
        <Link
          to="/settings"
          className={clsx(
            "flex items-center gap-3 px-3 py-2 rounded-lg text-gray-400 hover:bg-gray-800 hover:text-white transition-colors",
            !sidebarOpen && "justify-center"
          )}
          title={!sidebarOpen ? "Configurações" : undefined}
        >
          <Settings size={20} />
          {sidebarOpen && <span>Configurações</span>}
        </Link>
      </div>
    </aside>
  );
}
