import { useState } from 'react';
import { BookOpen, Download, Table, FileSpreadsheet, Search, Code, X, Play } from 'lucide-react';
import { useQuery, useMutation } from 'react-query';
import * as XLSX from 'xlsx';
import { catalogApi } from '../api';
import { CatalogTable } from '../types';
import toast from 'react-hot-toast';
import clsx from 'clsx';

export function CatalogPage() {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedTable, setSelectedTable] = useState<string | null>(null);
  const [showQueryModal, setShowQueryModal] = useState(false);
  const [sqlQuery, setSqlQuery] = useState('SELECT * FROM ');
  const [queryResult, setQueryResult] = useState<{ columns: string[], data: any[], row_count: number } | null>(null);

  const { data: tablesData, isLoading } = useQuery('catalog', catalogApi.listTables);
  const { data: tableInfo } = useQuery(
    ['tableInfo', selectedTable],
    () => catalogApi.getTableInfo(selectedTable!),
    { enabled: !!selectedTable }
  );
  const { data: tableData } = useQuery(
    ['tableData', selectedTable],
    () => catalogApi.getTableData(selectedTable!, 100, 0),
    { enabled: !!selectedTable }
  );

  const queryMutation = useMutation(
    (sql: string) => catalogApi.executeQuery(sql),
    {
      onSuccess: (data) => {
        setQueryResult(data);
        toast.success(`Query executada! ${data.row_count} linhas retornadas`);
      },
      onError: (error: any) => {
        toast.error(error.response?.data?.detail || 'Erro na query');
      },
    }
  );

  const tables = tablesData?.tables || [];
  const filteredTables = tables.filter((t: CatalogTable) => 
    t.name.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const getTypeBadge = (type: string) => {
    const styles = {
      raw: 'bg-gray-100 text-gray-800',
      staging: 'bg-yellow-100 text-yellow-800',
      dimension: 'bg-blue-100 text-blue-800',
      fact: 'bg-green-100 text-green-800',
      other: 'bg-gray-100 text-gray-800',
    };
    const labels = {
      raw: 'RAW', staging: 'STG', dimension: 'DIM', fact: 'FATO', other: 'OUTRO',
    };
    return (
      <span className={clsx('px-2 py-1 rounded text-xs font-medium', styles[type as keyof typeof styles] || styles.other)}>
        {labels[type as keyof typeof labels] || type.toUpperCase()}
      </span>
    );
  };

  const exportToCSV = () => {
    if (!tableData?.data || !selectedTable) return;
    
    const headers = tableData.columns.join(',');
    const rows = tableData.data.map((row: any) => 
      tableData.columns.map(col => {
        const val = row[col];
        if (val === null) return '';
        if (typeof val === 'string' && val.includes(',')) return `"${val}"`;
        return String(val);
      }).join(',')
    );
    
    const csv = [headers, ...rows].join('\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `${selectedTable}.csv`;
    link.click();
    toast.success('CSV exportado!');
  };

  const exportToExcel = () => {
    if (!tableData?.data || !selectedTable) return;
    
    const worksheet = XLSX.utils.json_to_sheet(tableData.data);
    const workbook = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(workbook, worksheet, selectedTable);
    XLSX.writeFile(workbook, `${selectedTable}.xlsx`);
    toast.success('Excel exportado!');
  };

  const handleExecuteQuery = () => {
    if (!sqlQuery.trim()) return;
    queryMutation.mutate(sqlQuery);
  };

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Catálogo de Dados</h1>
          <p className="text-gray-600 mt-1">Explore todas as tabelas no warehouse</p>
        </div>
        <button 
          onClick={() => setShowQueryModal(true)}
          className="flex items-center gap-2 bg-gray-800 hover:bg-gray-900 text-white px-4 py-2 rounded-lg font-medium transition-colors"
        >
          <Code size={18} />
          Query SQL
        </button>
      </div>

      {/* Search */}
      <div className="mb-6">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={20} />
          <input
            type="text"
            placeholder="Buscar tabelas..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
          />
        </div>
      </div>

      {/* Tables Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {isLoading ? (
          <div className="col-span-3 flex justify-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
          </div>
        ) : filteredTables.map((table: CatalogTable) => (
          <div 
            key={table.name} 
            className={clsx(
              "bg-white rounded-lg shadow p-4 cursor-pointer transition-all hover:shadow-lg",
              selectedTable === table.name && "ring-2 ring-primary-500"
            )}
            onClick={() => setSelectedTable(selectedTable === table.name ? null : table.name)}
          >
            <div className="flex justify-between items-start mb-3">
              <div className="flex items-center gap-2">
                <Table className="w-5 h-5 text-gray-400" />
                <code className="font-medium text-gray-900">{table.name}</code>
              </div>
              {getTypeBadge(table.type)}
            </div>
            <div className="flex justify-between text-sm text-gray-600">
              <span>{table.rows.toLocaleString()} linhas</span>
              <span>{table.columns} colunas</span>
            </div>
          </div>
        ))}
      </div>

      {/* Table Details */}
      {selectedTable && (
        <div className="mt-6 bg-white rounded-lg shadow p-6">
          <div className="flex justify-between items-center mb-4">
            <div>
              <h2 className="text-lg font-semibold text-gray-900">{selectedTable}</h2>
              {tableInfo && (
                <p className="text-sm text-gray-600">{tableInfo.row_count.toLocaleString()} linhas • {tableInfo.columns.length} colunas</p>
              )}
            </div>
            <div className="flex gap-2">
              <button 
                onClick={exportToCSV}
                disabled={!tableData?.data}
                className="flex items-center gap-2 px-3 py-1.5 text-gray-700 bg-gray-100 hover:bg-gray-200 disabled:opacity-50 rounded-lg text-sm font-medium"
              >
                <Download size={16} /> CSV
              </button>
              <button 
                onClick={exportToExcel}
                disabled={!tableData?.data}
                className="flex items-center gap-2 px-3 py-1.5 text-gray-700 bg-gray-100 hover:bg-gray-200 disabled:opacity-50 rounded-lg text-sm font-medium"
              >
                <FileSpreadsheet size={16} /> Excel
              </button>
              <button 
                onClick={() => { setSqlQuery(`SELECT * FROM ${selectedTable} LIMIT 100`); setShowQueryModal(true); }}
                className="flex items-center gap-2 px-3 py-1.5 text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg text-sm font-medium"
              >
                <Code size={16} /> Query
              </button>
            </div>
          </div>
          
          {/* Schema */}
          {tableInfo && (
            <div className="mb-6">
              <h3 className="text-sm font-medium text-gray-700 mb-2">Schema</h3>
              <div className="border rounded-lg overflow-hidden">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Coluna</th>
                      <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Tipo</th>
                      <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Nullable</th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {tableInfo.columns.map((col: any, idx: number) => (
                      <tr key={idx}>
                        <td className="px-4 py-2 text-sm font-medium text-gray-900">{col.name}</td>
                        <td className="px-4 py-2 text-sm text-gray-600"><code className="bg-gray-100 px-1 py-0.5 rounded">{col.type}</code></td>
                        <td className="px-4 py-2 text-sm text-gray-600">{col.nullable ? 'Sim' : 'Não'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Data Preview */}
          {tableData && (
            <div>
              <h3 className="text-sm font-medium text-gray-700 mb-2">Preview (100 linhas)</h3>
              <div className="border rounded-lg overflow-auto max-h-96">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50 sticky top-0">
                    <tr>
                      {tableData.columns.map((col: string) => (
                        <th key={col} className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase whitespace-nowrap">{col}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {tableData.data.map((row: any, idx: number) => (
                      <tr key={idx}>
                        {tableData.columns.map((col: string) => (
                          <td key={col} className="px-4 py-2 text-sm text-gray-900 whitespace-nowrap">
                            {row[col] === null ? <span className="text-gray-400 italic">null</span> : String(row[col]).slice(0, 50)}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Query SQL Modal */}
      {showQueryModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-6xl mx-4 max-h-[90vh] overflow-hidden">
            <div className="flex justify-between items-center p-6 border-b">
              <h2 className="text-xl font-bold text-gray-900">Query SQL</h2>
              <button onClick={() => { setShowQueryModal(false); setQueryResult(null); }} className="text-gray-400 hover:text-gray-600">
                <X size={24} />
              </button>
            </div>
            <div className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Query (apenas SELECT)</label>
                <textarea
                  value={sqlQuery}
                  onChange={(e) => setSqlQuery(e.target.value)}
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500 font-mono text-sm"
                  rows={4}
                  placeholder="SELECT * FROM tabela LIMIT 100"
                />
              </div>
              <div className="flex justify-end">
                <button
                  onClick={handleExecuteQuery}
                  disabled={queryMutation.isLoading || !sqlQuery.trim()}
                  className="flex items-center gap-2 px-4 py-2 bg-primary-600 hover:bg-primary-700 disabled:bg-gray-400 text-white rounded-lg font-medium"
                >
                  {queryMutation.isLoading ? <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div> : <Play size={18} />}
                  Executar
                </button>
              </div>
              
              {queryResult && (
                <div>
                  <div className="flex justify-between items-center mb-2">
                    <h3 className="font-medium">Resultado ({queryResult.row_count} linhas)</h3>
                    <button
                      onClick={() => {
                        const headers = queryResult.columns.join(',');
                        const rows = queryResult.data.map(row => 
                          queryResult.columns.map(col => {
                            const val = row[col];
                            if (val === null) return '';
                            if (typeof val === 'string' && val.includes(',')) return `"${val}"`;
                            return String(val);
                          }).join(',')
                        );
                        const csv = [headers, ...rows].join('\n');
                        const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
                        const link = document.createElement('a');
                        link.href = URL.createObjectURL(blob);
                        link.download = 'query_result.csv';
                        link.click();
                      }}
                      className="flex items-center gap-1 px-3 py-1 text-sm text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg"
                    >
                      <Download size={14} /> Exportar CSV
                    </button>
                  </div>
                  <div className="border rounded-lg overflow-auto max-h-96">
                    <table className="min-w-full divide-y divide-gray-200">
                      <thead className="bg-gray-50 sticky top-0">
                        <tr>
                          {queryResult.columns.map((col) => (
                            <th key={col} className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase whitespace-nowrap">{col}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody className="bg-white divide-y divide-gray-200">
                        {queryResult.data.map((row, idx) => (
                          <tr key={idx}>
                            {queryResult.columns.map((col) => (
                              <td key={col} className="px-4 py-2 text-sm text-gray-900 whitespace-nowrap">
                                {row[col] === null ? <span className="text-gray-400 italic">null</span> : String(row[col]).slice(0, 50)}
                              </td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
