import {
  BarChart, Bar, LineChart, Line, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
  AreaChart, Area
} from 'recharts';

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884D8', '#82CA9D'];

/** Agrupa os itens que excedem o limite em uma entrada unica "Outros" */
export function aplicarLimite(data: any[], limiteItens: any): any[] {
  const lista = Array.isArray(data) ? data : [];
  const limite = Number(limiteItens);
  if (!limite || limite <= 0 || lista.length <= limite) return lista;
  const visiveis = lista.slice(0, Math.max(0, limite - 1));
  const resto = lista.slice(Math.max(0, limite - 1));
  const soma = resto.reduce((acc: number, d: any) => acc + (Number(d?.value) || 0), 0);
  return [...visiveis, { name: `Outros (${resto.length})`, value: soma }];
}

export function renderComponente(component: any, index: number) {
  const { type, config = {} } = component;
  const dadosGrafico = aplicarLimite(config.data, config.limite_itens);
  const mostrarLegenda = config.mostrar_legenda !== false;
  const mostrarRotulosPie = config.mostrar_rotulos !== false;

  switch (type) {
    case 'kpi':
      return (
        <div className="bg-white rounded-lg shadow p-6 flex flex-col items-center justify-center h-full">
          <div className="text-3xl font-bold text-primary-600">{config.value || '0'}</div>
          <div className="text-sm text-gray-500 mt-2">{config.label || 'KPI'}</div>
          {config.change !== undefined && config.change !== null && (
            <div className={`text-xs mt-1 ${config.change >= 0 ? 'text-green-500' : 'text-red-500'}`}>
              {config.change >= 0 ? '+' : ''}{config.change}%
            </div>
          )}
        </div>
      );

    case 'chart_line':
      return (
        <div className="bg-white rounded-lg shadow p-4 h-full overflow-hidden">
          <h4 className="text-sm font-medium text-gray-700 mb-2">{config.title || 'Gráfico de Linha'}</h4>
          <ResponsiveContainer width="100%" height="85%">
            <LineChart data={dadosGrafico}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" />
              <YAxis />
              <Tooltip />
              {mostrarLegenda && <Legend />}
              <Line type="monotone" dataKey="value" stroke="#0088FE" />
            </LineChart>
          </ResponsiveContainer>
        </div>
      );

    case 'chart_bar':
      return (
        <div className="bg-white rounded-lg shadow p-4 h-full overflow-hidden">
          <h4 className="text-sm font-medium text-gray-700 mb-2">{config.title || 'Gráfico de Barras'}</h4>
          <ResponsiveContainer width="100%" height="85%">
            <BarChart data={dadosGrafico}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" interval={0} angle={dadosGrafico.length > 6 ? -25 : 0} textAnchor={dadosGrafico.length > 6 ? 'end' : 'middle'} height={dadosGrafico.length > 6 ? 50 : 30} />
              <YAxis />
              <Tooltip />
              {mostrarLegenda && <Legend />}
              <Bar dataKey="value" fill="#00C49F" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      );

    case 'chart_pie':
      return (
        <div className="bg-white rounded-lg shadow p-4 h-full overflow-hidden">
          <h4 className="text-sm font-medium text-gray-700 mb-2">{config.title || 'Gráfico de Pizza'}</h4>
          <ResponsiveContainer width="100%" height="85%">
            <PieChart>
              <Pie
                data={dadosGrafico}
                cx="50%"
                cy="50%"
                labelLine={mostrarRotulosPie}
                label={mostrarRotulosPie ? ({ name, percent }) => `${name} ${((percent || 0) * 100).toFixed(0)}%` : false}
                outerRadius={70}
                fill="#8884d8"
                dataKey="value"
              >
                {dadosGrafico.map((entry: any, index: number) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip />
              {mostrarLegenda && <Legend />}
            </PieChart>
          </ResponsiveContainer>
        </div>
      );

    case 'chart_area':
      return (
        <div className="bg-white rounded-lg shadow p-4 h-full overflow-hidden">
          <h4 className="text-sm font-medium text-gray-700 mb-2">{config.title || 'Gráfico de Área'}</h4>
          <ResponsiveContainer width="100%" height="85%">
            <AreaChart data={dadosGrafico}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" />
              <YAxis />
              <Tooltip />
              {mostrarLegenda && <Legend />}
              <Area type="monotone" dataKey="value" stroke="#8884D8" fill="#8884D8" />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      );

    case 'table':
      return (
        <div className="bg-white rounded-lg shadow p-4 h-full overflow-auto">
          <h4 className="text-sm font-medium text-gray-700 mb-2">{config.title || 'Tabela'}</h4>
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                {(config.columns || []).map((col: string, idx: number) => (
                  <th key={idx} className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                    {col}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {(config.data || []).slice(0, 10).map((row: any, rowIdx: number) => (
                <tr key={rowIdx}>
                  {(config.columns || []).map((col: string, colIdx: number) => (
                    <td key={colIdx} className="px-3 py-2 text-sm text-gray-900">{row[col]}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );

    case 'text':
      return (
        <div className="bg-white rounded-lg shadow p-4 h-full">
          <h4 className="text-sm font-medium text-gray-700 mb-2">{config.title}</h4>
          <p className="text-sm text-gray-600 whitespace-pre-wrap">{config.content}</p>
        </div>
      );

    default:
      return (
        <div className="bg-gray-50 rounded-lg p-4 h-full flex items-center justify-center">
          <span className="text-gray-400">Componente não suportado: {type}</span>
        </div>
      );
  }
}
