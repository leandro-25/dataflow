import { useEffect, useState } from 'react';
import { X, Folder, FileText, ArrowUp, Loader2, Check, HardDrive, FolderOpen } from 'lucide-react';
import clsx from 'clsx';
import toast from 'react-hot-toast';
import { filesystemApi, FileSystemEntry } from '../api';

interface FileBrowserModalProps {
  open: boolean;
  title: string;
  acceptExtensions?: string[];
  selectDirectory?: boolean;
  onClose: () => void;
  onSelect: (path: string) => void;
}

interface Crumb {
  label: string;
  path: string;
}

const formatSize = (size: number | null): string => {
  if (size === null || size === undefined) return '';
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
  if (size < 1024 * 1024 * 1024) return `${(size / (1024 * 1024)).toFixed(1)} MB`;
  return `${(size / (1024 * 1024 * 1024)).toFixed(1)} GB`;
};

const buildBreadcrumbs = (path: string): Crumb[] => {
  const crumbs: Crumb[] = [{ label: 'Este Computador', path: '' }];
  if (!path) return crumbs;

  const normalized = path.replace(/\//g, '\\');
  const parts = normalized.split('\\').filter(Boolean);
  let acc = '';

  parts.forEach((part, i) => {
    if (i === 0) {
      acc = part.endsWith(':') ? part + '\\' : '\\' + part;
    } else {
      acc = acc.endsWith('\\') ? acc + part : acc + '\\' + part;
    }
    crumbs.push({ label: i === 0 ? part.toUpperCase() : part, path: acc });
  });

  return crumbs;
};

export function FileBrowserModal({
  open,
  title,
  acceptExtensions,
  selectDirectory = false,
  onClose,
  onSelect,
}: FileBrowserModalProps) {
  const [currentPath, setCurrentPath] = useState('');
  const [parentPath, setParentPath] = useState<string | null>(null);
  const [entries, setEntries] = useState<FileSystemEntry[]>([]);
  const [shortcuts, setShortcuts] = useState<{ name: string; path: string }[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const [selectedFolder, setSelectedFolder] = useState<string | null>(null);

  useEffect(() => {
    if (open) {
      load('');
    }
  }, [open]);

  const load = async (path: string) => {
    setLoading(true);
    setSelectedFile(null);
    setSelectedFolder(null);
    try {
      const data = await filesystemApi.list(path || undefined);
      setCurrentPath(data.path);
      setParentPath(data.parent);
      setEntries(data.entries);
      setShortcuts(data.shortcuts);
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Erro ao listar pasta');
    } finally {
      setLoading(false);
    }
  };

  if (!open) return null;

  const matchesFilter = (entry: FileSystemEntry) => {
    if (entry.is_dir) return true;
    if (!acceptExtensions || acceptExtensions.length === 0) return true;
    return acceptExtensions.some(ext => entry.name.toLowerCase().endsWith(ext));
  };

  const handleRowClick = (entry: FileSystemEntry) => {
    if (entry.is_dir) {
      if (selectDirectory) {
        setSelectedFolder(entry.path);
        setSelectedFile(null);
      }
      return;
    }
    if (!matchesFilter(entry)) return;
    setSelectedFile(entry.path);
    setSelectedFolder(null);
  };

  const handleRowDoubleClick = (entry: FileSystemEntry) => {
    if (entry.is_dir) {
      load(entry.path);
    } else if (matchesFilter(entry)) {
      onSelect(entry.path);
    }
  };

  const handleConfirm = () => {
    if (selectDirectory) {
      onSelect(selectedFolder || currentPath);
    } else if (selectedFile) {
      onSelect(selectedFile);
    }
  };

  const hasSelection = selectDirectory ? true : !!selectedFile;

  const crumbs = buildBreadcrumbs(currentPath);

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-[60]">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-2xl mx-4 h-[80vh] flex flex-col">
        <div className="flex justify-between items-center p-4 border-b">
          <h2 className="text-lg font-bold text-gray-900">{title}</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X size={22} />
          </button>
        </div>

        <div className="px-4 py-2 border-b bg-gray-50 space-y-2">
          <div className="flex items-center gap-1 text-sm overflow-x-auto whitespace-nowrap">
            {crumbs.map((crumb, idx) => (
              <span key={idx} className="flex items-center gap-1">
                {idx > 0 && <span className="text-gray-400">›</span>}
                <button
                  type="button"
                  onClick={() => load(crumb.path)}
                  className="text-primary-600 hover:text-primary-800 hover:underline"
                >
                  {crumb.label}
                </button>
              </span>
            ))}
            {!currentPath && (
              <>
                <span className="text-gray-400 mx-1">›</span>
                <span className="text-gray-500">Unidades</span>
              </>
            )}
          </div>

          {shortcuts.length > 0 && (
            <div className="flex items-center gap-2 flex-wrap">
              {shortcuts.map((sc) => (
                <button
                  key={sc.path}
                  type="button"
                  onClick={() => load(sc.path)}
                  className="flex items-center gap-1.5 text-xs px-2 py-1 bg-white border border-gray-200 rounded-md hover:border-primary-400 hover:text-primary-700 transition-colors"
                >
                  <FolderOpen size={13} />
                  {sc.name}
                </button>
              ))}
              {selectDirectory && currentPath && (
                <span className="text-xs text-gray-500 ml-auto font-mono truncate max-w-[240px]" title={currentPath}>
                  Pasta atual: {currentPath}
                </span>
              )}
            </div>
          )}
        </div>

        <div className="flex-1 overflow-y-auto">
          {loading ? (
            <div className="flex justify-center items-center h-full">
              <Loader2 size={28} className="animate-spin text-primary-600" />
            </div>
          ) : entries.length === 0 ? (
            <div className="p-8 text-center text-sm text-gray-500">Pasta vazia</div>
          ) : (
            <ul className="divide-y divide-gray-100">
              {parentPath !== null && (
                <li>
                  <button
                    type="button"
                    onClick={() => load(parentPath)}
                    className="w-full flex items-center gap-3 px-4 py-2 hover:bg-gray-50 text-left"
                  >
                    <ArrowUp size={18} className="text-gray-500" />
                    <span className="text-sm text-gray-600 italic">..</span>
                  </button>
                </li>
              )}
              {entries.map((entry) => {
                const allowed = matchesFilter(entry);
                const isSelFile = selectedFile === entry.path;
                const isSelFolder = selectDirectory && selectedFolder === entry.path;

                if (!allowed && !entry.is_dir) {
                  return (
                    <li key={entry.path} className="flex items-center gap-3 px-4 py-2 opacity-40 cursor-not-allowed">
                      <FileText size={18} className="text-gray-300" />
                      <span className="text-sm text-gray-400 flex-1">{entry.name}</span>
                      <span className="text-xs text-gray-300">{formatSize(entry.size)}</span>
                    </li>
                  );
                }

                return (
                  <li key={entry.path}>
                    <button
                      type="button"
                      onClick={() => handleRowClick(entry)}
                      onDoubleClick={() => handleRowDoubleClick(entry)}
                      className={clsx(
                        'w-full flex items-center gap-3 px-4 py-2 text-left transition-colors',
                        isSelFile || isSelFolder ? 'bg-primary-50' : 'hover:bg-gray-50'
                      )}
                    >
                      {entry.is_dir ? (
                        <Folder size={18} className={isSelFolder ? 'text-primary-600' : 'text-yellow-500'} />
                      ) : (
                        <FileText size={18} className="text-blue-400" />
                      )}
                      <span className={clsx('text-sm flex-1 truncate', isSelFile || isSelFolder ? 'text-primary-800 font-medium' : 'text-gray-700')}>
                        {entry.name}
                      </span>
                      <span className="text-xs text-gray-400">{formatSize(entry.size)}</span>
                      {entry.is_dir && !selectDirectory && (
                        <span className="text-xs text-gray-400">abrir ›</span>
                      )}
                    </button>
                  </li>
                );
              })}
            </ul>
          )}
        </div>

        <div className="p-4 border-t flex items-center gap-3">
          <HardDrive size={16} className="text-gray-400" />
          <input
            type="text"
            readOnly
            value={selectDirectory ? (selectedFolder || currentPath || '') : (selectedFile || '')}
            placeholder="Nenhum item selecionado — clique em um arquivo"
            className="flex-1 px-3 py-2 border border-gray-200 rounded-lg bg-gray-50 text-xs font-mono text-gray-600 truncate"
          />
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg font-medium transition-colors text-sm"
          >
            Cancelar
          </button>
          <button
            type="button"
            onClick={handleConfirm}
            disabled={!hasSelection || loading}
            className="flex items-center gap-2 px-4 py-2 bg-primary-600 hover:bg-primary-700 disabled:opacity-40 text-white rounded-lg font-medium transition-colors text-sm"
          >
            <Check size={16} />
            {selectDirectory ? (selectedFolder ? 'Usar esta pasta' : 'Usar pasta atual') : 'Selecionar'}
          </button>
        </div>
      </div>
    </div>
  );
}
