import React, { useState, useEffect, useMemo } from 'react';
import { BarChart, Bar, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { apiClient } from '../services/api';
import './Analytics.css';

const RISK_COLORS = {
  'BAJO': '#4caf50',
  'MEDIO': '#ff9800',
  'ALTO': '#ff5722',
  'CRÍTICO': '#c62828'
};

const PIE_COLORS = ['#8884d8', '#82ca9d', '#ffc658', '#ff7c7c', '#8dd1e1', '#d084d0'];

const Analytics = () => {
  const [status, setStatus] = useState(null);
  const [clustersData, setClustersData] = useState(null);
  const [clustersStats, setClustersStats] = useState(null);
  const [reporteLimpieza, setReporteLimpieza] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('clusters');
  const [filtroRiesgo, setFiltroRiesgo] = useState('TODOS');

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      setError(null);
      try {
        // Ejecutar todas las llamadas en paralelo
        const [statusRes, clustersRes, statsRes, limpiezaRes] = await Promise.all([
          apiClient.get('/analytics/status/'),
          apiClient.get('/analytics/clusters/'),
          apiClient.get('/analytics/cluster-stats/'),
          apiClient.get('/analytics/reporte-limpieza/')
        ]);
        
        setStatus(statusRes.data);
        setClustersData(clustersRes.data);
        setClustersStats(statsRes.data);
        setReporteLimpieza(limpiezaRes.data);
        
        // Debug: ver estructura de datos
        console.log('Status:', statusRes.data);
        console.log('Clusters Data:', clustersRes.data);
        console.log('Clusters Stats:', statsRes.data);
        console.log('Reporte Limpieza:', limpiezaRes.data);

      } catch (err) {
        console.error("Error fetching analytics data:", err);
        setError('Hubo un error al cargar los datos de analytics. Revisa la consola del backend.');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  const estadisticasRiesgo = useMemo(() => {
    if (!clustersData?.data) return { BAJO: 0, MEDIO: 0, ALTO: 0, CRÍTICO: 0 };
    return clustersData.data.reduce((acc, p) => {
      if (acc.hasOwnProperty(p.nivel_riesgo)) {
        acc[p.nivel_riesgo]++;
      }
      return acc;
    }, { BAJO: 0, MEDIO: 0, ALTO: 0, CRÍTICO: 0 });
  }, [clustersData]);

  const datosFiltrados = useMemo(() => {
    if (!clustersData?.data) return [];
    if (filtroRiesgo === 'TODOS') return clustersData.data;
    return clustersData.data.filter(p => p.nivel_riesgo === filtroRiesgo);
  }, [clustersData, filtroRiesgo]);

  // KPIs calculados desde los datos de pólizas
  const kpisCalculados = useMemo(() => {
    if (!clustersData?.data || clustersData.data.length === 0) {
      return { montoTotal: 0, montoPromedio: 0, montoMax: 0, montoMin: 0, porCluster: {} };
    }
    
    const data = clustersData.data;
    const montos = data.map(p => parseFloat(p.monto_uf) || 0);
    const montoTotal = montos.reduce((a, b) => a + b, 0);
    
    // Estadísticas por cluster
    const porCluster = {};
    data.forEach(p => {
      const c = p.cluster;
      if (!porCluster[c]) {
        porCluster[c] = { count: 0, montoTotal: 0, montos: [] };
      }
      porCluster[c].count++;
      porCluster[c].montoTotal += parseFloat(p.monto_uf) || 0;
      porCluster[c].montos.push(parseFloat(p.monto_uf) || 0);
    });
    
    // Calcular promedios por cluster
    Object.keys(porCluster).forEach(c => {
      porCluster[c].montoPromedio = porCluster[c].montoTotal / porCluster[c].count;
    });
    
    return {
      montoTotal,
      montoPromedio: montoTotal / data.length,
      montoMax: Math.max(...montos),
      montoMin: Math.min(...montos),
      porCluster
    };
  }, [clustersData]);

  // Definición de perfiles de clusters (basado en centroides del modelo)
  const CLUSTER_PROFILES = {
    0: { 
      nombre: 'Premium Moroso', 
      emoji: '⚠️',
      color: '#ff5722',
      descripcion: 'Alto valor (~593 UF), cobranzas pendientes',
      riesgo: 'ALTO',
      accion: 'Gestión de cobranza prioritaria'
    },
    1: { 
      nombre: 'Activo Sin Deuda', 
      emoji: '✅',
      color: '#4caf50',
      descripcion: 'Valor medio (~191 UF), sin cobranzas',
      riesgo: 'BAJO',
      accion: 'Candidato para upselling'
    },
    2: { 
      nombre: 'Buen Pagador', 
      emoji: '💚',
      color: '#2196f3',
      descripcion: 'Valor bajo (~33 UF), 100% pagado',
      riesgo: 'BAJO',
      accion: 'Cliente fidelizado, referidos'
    }
  };

  if (loading) {
    return <div className="p-8 text-center">Cargando y procesando datos...</div>;
  }

  if (error) {
    return (
      <div className="p-8">
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative" role="alert">
          <strong className="font-bold">Error: </strong>
          <span className="block sm:inline">{error}</span>
        </div>
      </div>
    );
  }

  return (
    <div className="p-8 bg-gray-50 min-h-screen">
      <div className="max-w-7xl mx-auto">
        <h1 className="text-3xl font-bold text-gray-900 mb-8">📊 Analytics - ML & Clustering</h1>

        <div className="flex gap-4 mb-6 border-b border-gray-200">
          {['clusters', 'overview', 'limpieza'].map(tab => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-6 py-3 font-medium transition capitalize ${
                activeTab === tab
                  ? 'border-b-2 border-blue-600 text-blue-600'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              {tab === 'clusters' ? 'Pólizas & Riesgo' : tab === 'overview' ? 'Estadísticas' : 'Calidad de Datos'}
            </button>
          ))}
        </div>

        {/* TAB 1: Pólizas & Riesgo */}
        {activeTab === 'clusters' && (
          <div className="space-y-6">
            {/* KPIs Visuales Estilo Power BI */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
              {Object.entries(estadisticasRiesgo).map(([nivel, count]) => {
                const porcentaje = ((count / (clustersData?.data?.length || 1)) * 100).toFixed(1);
                const icons = { BAJO: '✅', MEDIO: '⚠️', ALTO: '🔴', CRÍTICO: '🚨' };
                return (
                  <div 
                    key={nivel} 
                    className="relative overflow-hidden rounded-xl shadow-lg hover:shadow-2xl transition-all duration-300 transform hover:scale-105"
                    style={{ 
                      background: `linear-gradient(135deg, ${RISK_COLORS[nivel]}15 0%, ${RISK_COLORS[nivel]}30 100%)`,
                      border: `2px solid ${RISK_COLORS[nivel]}40`
                    }}
                  >
                    <div className="p-6">
                      <div className="flex items-center justify-between mb-3">
                        <span className="text-3xl">{icons[nivel]}</span>
                        <div 
                          className="px-3 py-1 rounded-full text-xs font-bold text-white"
                          style={{ backgroundColor: RISK_COLORS[nivel] }}
                        >
                          {nivel}
                        </div>
                      </div>
                      <div className="text-5xl font-extrabold mb-2" style={{color: RISK_COLORS[nivel]}}>
                        {count}
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-gray-600 font-medium">pólizas</span>
                        <span className="text-lg font-bold" style={{color: RISK_COLORS[nivel]}}>{porcentaje}%</span>
                      </div>
                      <div className="mt-3 w-full bg-gray-200 rounded-full h-2 overflow-hidden">
                        <div 
                          className="h-full rounded-full transition-all duration-500"
                          style={{ 
                            width: `${porcentaje}%`,
                            backgroundColor: RISK_COLORS[nivel]
                          }}
                        />
                      </div>
                    </div>
                    {/* Decoración visual */}
                    <div 
                      className="absolute -bottom-6 -right-6 w-24 h-24 rounded-full opacity-10"
                      style={{ backgroundColor: RISK_COLORS[nivel] }}
                    />
                  </div>
                );
              })}
            </div>

            <div className="flex gap-4 items-center">
              <label className="font-medium text-gray-700">Filtrar por Riesgo:</label>
              <select
                value={filtroRiesgo}
                onChange={(e) => setFiltroRiesgo(e.target.value)}
                className="px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
              >
                <option value="TODOS">TODOS</option>
                {Object.keys(RISK_COLORS).map(level => <option key={level} value={level}>{level}</option>)}
              </select>
            </div>

            <div className="bg-white rounded-lg shadow overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-100 border-b">
                  <tr>
                    {['#', 'Póliza', 'Cliente', 'Monto UF', 'Cluster', 'Riesgo'].map(header => (
                      <th key={header} className="p-3 text-left">{header}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {datosFiltrados.slice(0, 100).map((row, idx) => (
                    <tr key={row.numero_poliza || idx} className="border-b hover:bg-gray-50">
                      <td className="p-3">{idx + 1}</td>
                      <td className="p-3 font-mono text-xs">{row.numero_poliza}</td>
                      <td className="p-3 truncate max-w-xs">{row.cliente_nombre}</td>
                      <td className="p-3 text-right">{parseFloat(row.monto_uf).toFixed(2)}</td>
                      <td className="p-3 text-center"><span className="bg-blue-100 text-blue-800 px-2 py-1 rounded text-xs">{row.cluster}</span></td>
                      <td className="p-3 text-center">
                        <span className={`px-3 py-1 rounded text-xs font-semibold text-white`} style={{ backgroundColor: RISK_COLORS[row.nivel_riesgo] }}>
                          {row.nivel_riesgo}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <div className="p-4 text-xs text-gray-600 bg-gray-50">
                Mostrando {datosFiltrados.slice(0, 100).length} de {datosFiltrados.length} registros.
              </div>
            </div>
          </div>
        )}

        {/* TAB 2: Estadísticas */}
        {activeTab === 'overview' && (
          <div className="space-y-6">
            {/* Estado del Modelo */}
            <div className="bg-white p-6 rounded-lg shadow">
              <h3 className="font-semibold text-gray-900 mb-4">🤖 Estado de Modelo ML</h3>
              <p className={`p-3 rounded text-sm ${status?.modelos_disponibles ? 'bg-green-50 text-green-800' : 'bg-yellow-50 text-yellow-800'}`}>
                {status?.mensaje || 'Cargando...'}
              </p>
              {status?.features && (
                <div className="mt-4">
                  <span className="text-sm text-gray-600">Features utilizados:</span>
                  <div className="flex flex-wrap gap-2 mt-2">
                    {status.features.map((f, i) => (
                      <span key={i} className="bg-blue-100 text-blue-800 px-2 py-1 rounded text-xs">{f}</span>
                    ))}
                  </div>
                </div>
              )}
            </div>
            
            {/* KPIs Principales Estilo Power BI */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
              {[
                { 
                  icon: '📊', 
                  label: 'Total Pólizas', 
                  value: clustersStats?.total_polizas || clustersData?.data?.length || 0,
                  color: '#3b82f6',
                  suffix: '',
                  bg: 'from-blue-500 to-blue-600'
                },
                { 
                  icon: '🎯', 
                  label: 'Clusters Activos', 
                  value: clustersStats?.clusters?.length || 0,
                  color: '#8b5cf6',
                  suffix: '',
                  bg: 'from-purple-500 to-purple-600'
                },
                { 
                  icon: '💰', 
                  label: 'Monto Total', 
                  value: kpisCalculados.montoTotal.toLocaleString('es-CL', {maximumFractionDigits: 0}),
                  color: '#10b981',
                  suffix: ' UF',
                  bg: 'from-green-500 to-green-600'
                },
                { 
                  icon: '📈', 
                  label: 'Monto Promedio', 
                  value: kpisCalculados.montoPromedio.toFixed(2),
                  color: '#f59e0b',
                  suffix: ' UF',
                  bg: 'from-orange-500 to-orange-600'
                }
              ].map((kpi, idx) => (
                <div 
                  key={idx}
                  className={`relative overflow-hidden rounded-xl shadow-xl hover:shadow-2xl transition-all duration-300 bg-gradient-to-br ${kpi.bg} text-white p-6 transform hover:scale-105`}
                >
                  <div className="flex items-start justify-between mb-4">
                    <span className="text-5xl opacity-90">{kpi.icon}</span>
                    <div className="text-right">
                      <div className="text-xs font-semibold uppercase tracking-wider opacity-90">{kpi.label}</div>
                    </div>
                  </div>
                  <div className="text-4xl font-black mb-1">
                    {kpi.value}<span className="text-2xl font-bold opacity-80">{kpi.suffix}</span>
                  </div>
                  {/* Decoración */}
                  <div className="absolute -bottom-4 -right-4 text-9xl opacity-10">{kpi.icon}</div>
                </div>
              ))}
            </div>

            {/* KPIs Secundarios con Comparaciones Visuales */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {[
                { icon: '⬆️', label: 'Monto Máximo', value: kpisCalculados.montoMax.toFixed(2), suffix: ' UF', color1: '#ef4444', color2: '#dc2626' },
                { icon: '⬇️', label: 'Monto Mínimo', value: kpisCalculados.montoMin.toFixed(2), suffix: ' UF', color1: '#10b981', color2: '#059669' },
                { icon: '📁', label: 'Tipo de Datos', value: clustersStats?.tipo || 'N/A', suffix: '', color1: '#8b5cf6', color2: '#7c3aed' },
                { icon: '🤖', label: 'Algoritmo', value: 'K-Means', suffix: ' (k=3)', color1: '#6b7280', color2: '#4b5563' }
              ].map((kpi, idx) => (
                <div 
                  key={idx}
                  className="relative bg-white rounded-xl shadow-md hover:shadow-xl transition-all duration-300 p-5 border-l-4 overflow-hidden group"
                  style={{ borderColor: kpi.color1 }}
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-3xl group-hover:scale-110 transition-transform duration-300">{kpi.icon}</span>
                    <div className="w-10 h-10 rounded-full flex items-center justify-center text-white text-xs font-bold" style={{ background: `linear-gradient(135deg, ${kpi.color1}, ${kpi.color2})` }}>
                      {idx + 1}
                    </div>
                  </div>
                  <div className="text-xs text-gray-500 font-semibold uppercase tracking-wide mb-1">{kpi.label}</div>
                  <div className="text-2xl font-extrabold" style={{ color: kpi.color1 }}>
                    {kpi.value}<span className="text-sm font-medium opacity-70">{kpi.suffix}</span>
                  </div>
                  {/* Barra decorativa animada */}
                  <div className="absolute bottom-0 left-0 w-full h-1 opacity-0 group-hover:opacity-100 transition-opacity duration-300" style={{ background: `linear-gradient(90deg, ${kpi.color1}, ${kpi.color2})` }} />
                </div>
              ))}
            </div>

            {/* Perfiles de Clusters - Tarjetas Power BI Style */}
            <div className="bg-gradient-to-r from-gray-50 to-gray-100 p-6 rounded-2xl shadow-xl">
              <h3 className="font-bold text-gray-900 mb-6 text-xl flex items-center gap-2">
                <span className="text-3xl">🎯</span> Perfiles de Clusters
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {Object.entries(CLUSTER_PROFILES).map(([clusterId, profile]) => {
                  const clusterData = kpisCalculados.porCluster[clusterId];
                  const porcentajeTotal = ((clusterData?.count || 0) / (clustersData?.data?.length || 1) * 100).toFixed(1);
                  return (
                    <div 
                      key={clusterId} 
                      className="relative bg-white rounded-2xl shadow-lg hover:shadow-2xl transition-all duration-300 overflow-hidden border-2 transform hover:scale-105"
                      style={{ borderColor: profile.color }}
                    >
                      {/* Header con gradiente */}
                      <div 
                        className="p-6 text-white relative overflow-hidden"
                        style={{ background: `linear-gradient(135deg, ${profile.color} 0%, ${profile.color}dd 100%)` }}
                      >
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-5xl drop-shadow-lg">{profile.emoji}</span>
                          <div className="bg-white bg-opacity-30 backdrop-blur-sm px-3 py-1 rounded-full text-xs font-bold">
                            Cluster {clusterId}
                          </div>
                        </div>
                        <div className="text-2xl font-black mb-1">{profile.nombre}</div>
                        <div className="text-sm opacity-90">{profile.descripcion}</div>
                        {/* Círculo decorativo */}
                        <div className="absolute -bottom-8 -right-8 w-32 h-32 bg-white opacity-10 rounded-full" />
                      </div>
                      
                      {/* Métricas */}
                      <div className="p-6 space-y-4">
                        <div className="grid grid-cols-2 gap-4">
                          <div className="text-center p-3 bg-gradient-to-br from-blue-50 to-blue-100 rounded-xl">
                            <div className="text-3xl font-black" style={{ color: profile.color }}>
                              {clusterData?.count || 0}
                            </div>
                            <div className="text-xs text-gray-600 font-semibold uppercase">Pólizas</div>
                          </div>
                          <div className="text-center p-3 bg-gradient-to-br from-purple-50 to-purple-100 rounded-xl">
                            <div className="text-3xl font-black" style={{ color: profile.color }}>
                              {porcentajeTotal}%
                            </div>
                            <div className="text-xs text-gray-600 font-semibold uppercase">Del Total</div>
                          </div>
                        </div>
                        
                        <div className="space-y-2">
                          <div className="flex justify-between items-center p-2 bg-gray-50 rounded-lg">
                            <span className="text-xs text-gray-600 font-semibold">💵 Monto Promedio</span>
                            <span className="text-sm font-bold" style={{ color: profile.color }}>
                              {clusterData?.montoPromedio?.toFixed(2) || '0.00'} UF
                            </span>
                          </div>
                          <div className="flex justify-between items-center p-2 bg-gray-50 rounded-lg">
                            <span className="text-xs text-gray-600 font-semibold">💰 Monto Total</span>
                            <span className="text-sm font-bold" style={{ color: profile.color }}>
                              {clusterData?.montoTotal?.toLocaleString('es-CL', {maximumFractionDigits: 0}) || 0} UF
                            </span>
                          </div>
                        </div>
                        
                        {/* Acción recomendada */}
                        <div 
                          className="mt-4 p-3 rounded-xl text-center font-semibold text-sm text-white"
                          style={{ background: `linear-gradient(135deg, ${profile.color}dd, ${profile.color})` }}
                        >
                          🎯 {profile.accion}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {clustersStats?.clusters?.length > 0 && (
              <>
                {/* Gráficos Power BI Style - Fila 1 */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  <div className="bg-white p-6 rounded-xl shadow-xl border-t-4 border-blue-500">
                    <h3 className="font-bold text-gray-900 mb-4 flex items-center gap-2">
                      <span className="text-2xl">📊</span> Distribución por Cluster
                    </h3>
                    <ResponsiveContainer width="100%" height={320}>
                      <PieChart>
                        <Pie 
                          data={clustersStats.clusters.map(c => ({...c, polizas: c.cantidad_polizas || 0, name: `Cluster ${c.cluster}`}))} 
                          dataKey="polizas" 
                          nameKey="name" 
                          cx="50%" cy="50%" 
                          outerRadius={110} 
                          innerRadius={60}
                          paddingAngle={3}
                          label={({name, percent}) => `${(percent * 100).toFixed(0)}%`}
                          labelLine={{ stroke: '#999', strokeWidth: 1 }}
                        >
                          {clustersStats.clusters.map((c, i) => (
                            <Cell key={`cell-${i}`} fill={CLUSTER_PROFILES[c.cluster]?.color || PIE_COLORS[i % PIE_COLORS.length]} />
                          ))}
                        </Pie>
                        <Tooltip 
                          contentStyle={{ backgroundColor: '#fff', border: '2px solid #ddd', borderRadius: '8px', padding: '10px' }}
                          formatter={(value) => [`${value} pólizas`, 'Cantidad']}
                        />
                        <Legend 
                          verticalAlign="bottom" 
                          height={36}
                          iconType="circle"
                        />
                      </PieChart>
                    </ResponsiveContainer>
                  </div>
                  
                  <div className="bg-white p-6 rounded-xl shadow-xl border-t-4 border-purple-500">
                    <h3 className="font-bold text-gray-900 mb-4 flex items-center gap-2">
                      <span className="text-2xl">💰</span> Monto Total por Cluster
                    </h3>
                    <ResponsiveContainer width="100%" height={320}>
                      <BarChart 
                        data={Object.entries(kpisCalculados.porCluster).map(([c, data]) => ({
                          cluster: `C${c}`,
                          nombre: CLUSTER_PROFILES[c]?.nombre || `Cluster ${c}`,
                          monto: data.montoTotal || 0,
                          polizas: data.count || 0,
                          color: CLUSTER_PROFILES[c]?.color || '#8884d8'
                        }))}
                        layout="vertical"
                      >
                        <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                        <XAxis type="number" />
                        <YAxis type="category" dataKey="cluster" width={40} />
                        <Tooltip 
                          contentStyle={{ backgroundColor: '#fff', border: '2px solid #ddd', borderRadius: '8px' }}
                          formatter={(value, name) => [`${value.toLocaleString('es-CL', {maximumFractionDigits: 0})} UF`, 'Monto Total']}
                        />
                        <Bar dataKey="monto" radius={[0, 8, 8, 0]}>
                          {Object.entries(kpisCalculados.porCluster).map(([c], idx) => (
                            <Cell key={`cell-${idx}`} fill={CLUSTER_PROFILES[c]?.color || '#8884d8'} />
                          ))}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>

                {/* Gráficos Power BI Style - Fila 2 */}
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                  <div className="bg-white p-6 rounded-xl shadow-xl border-t-4 border-green-500">
                    <h3 className="font-bold text-gray-900 mb-4 flex items-center gap-2">
                      <span className="text-2xl">📈</span> Comparativa Montos
                    </h3>
                    <ResponsiveContainer width="100%" height={280}>
                      <BarChart data={Object.entries(kpisCalculados.porCluster).map(([c, data]) => ({
                        cluster: `C${c}`,
                        promedio: data.montoPromedio || 0,
                        total: (data.montoTotal || 0) / 100
                      }))}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="cluster" />
                        <YAxis />
                        <Tooltip 
                          formatter={(value, name) => [
                            name === 'promedio' ? `${value.toFixed(2)} UF` : `${(value * 100).toLocaleString('es-CL', {maximumFractionDigits: 0})} UF`,
                            name === 'promedio' ? 'Promedio' : 'Total (÷100)'
                          ]}
                        />
                        <Legend />
                        <Bar dataKey="promedio" fill="#10b981" name="Monto Promedio" radius={[8, 8, 0, 0]} />
                        <Bar dataKey="total" fill="#3b82f6" name="Monto Total (÷100)" radius={[8, 8, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>

                  <div className="bg-white p-6 rounded-xl shadow-xl border-t-4 border-orange-500">
                    <h3 className="font-bold text-gray-900 mb-4 flex items-center gap-2">
                      <span className="text-2xl">🎯</span> Concentración de Pólizas
                    </h3>
                    <ResponsiveContainer width="100%" height={280}>
                      <BarChart data={Object.entries(kpisCalculados.porCluster).map(([c, data]) => ({
                        cluster: CLUSTER_PROFILES[c]?.emoji + ' C' + c,
                        cantidad: data.count || 0
                      }))}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="cluster" />
                        <YAxis />
                        <Tooltip contentStyle={{ backgroundColor: '#fff', border: '2px solid #ddd', borderRadius: '8px' }} />
                        <Bar dataKey="cantidad" radius={[8, 8, 0, 0]}>
                          {Object.entries(kpisCalculados.porCluster).map(([c], idx) => (
                            <Cell key={`bar-${idx}`} fill={CLUSTER_PROFILES[c]?.color || '#f59e0b'} />
                          ))}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  </div>

                  <div className="bg-gradient-to-br from-indigo-50 to-purple-50 p-6 rounded-xl shadow-xl border-2 border-indigo-200">
                    <h3 className="font-bold text-gray-900 mb-4 flex items-center gap-2">
                      <span className="text-2xl">🔢</span> Métricas Clave
                    </h3>
                    <div className="space-y-4">
                      {Object.entries(kpisCalculados.porCluster).map(([c, data]) => {
                        const profile = CLUSTER_PROFILES[c];
                        const porcentaje = ((data.count / (clustersData?.data?.length || 1)) * 100).toFixed(1);
                        return (
                          <div key={c} className="bg-white rounded-lg p-4 shadow">
                            <div className="flex items-center justify-between mb-2">
                              <span className="text-2xl">{profile?.emoji}</span>
                              <span className="text-xs font-bold px-2 py-1 rounded-full text-white" style={{ backgroundColor: profile?.color }}>
                                C{c}
                              </span>
                            </div>
                            <div className="text-xs text-gray-600 mb-1">{profile?.nombre}</div>
                            <div className="flex items-baseline gap-1">
                              <span className="text-2xl font-black" style={{ color: profile?.color }}>
                                {data.count}
                              </span>
                              <span className="text-sm text-gray-500">pólizas</span>
                            </div>
                            <div className="mt-2 flex items-center gap-2">
                              <div className="flex-1 bg-gray-200 rounded-full h-2">
                                <div 
                                  className="h-full rounded-full transition-all duration-500"
                                  style={{ width: `${porcentaje}%`, backgroundColor: profile?.color }}
                                />
                              </div>
                              <span className="text-xs font-bold" style={{ color: profile?.color }}>{porcentaje}%</span>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                </div>
                
                {/* Tabla detallada */}
                <div className="bg-white rounded-lg shadow overflow-x-auto">
                  <h3 className="font-semibold text-gray-900 p-6 border-b">📋 Resumen por Cluster</h3>
                  <table className="w-full text-sm">
                    <thead className="bg-gray-100 border-b">
                      <tr>
                        <th className="p-3 text-left">Cluster</th>
                        <th className="p-3 text-left">Perfil</th>
                        <th className="p-3 text-right">Pólizas</th>
                        <th className="p-3 text-right">% Total</th>
                        <th className="p-3 text-right">Monto Prom.</th>
                        <th className="p-3 text-right">Monto Total</th>
                        <th className="p-3 text-left">Acción Sugerida</th>
                      </tr>
                    </thead>
                    <tbody>
                      {clustersStats.clusters.map((row) => {
                        const profile = CLUSTER_PROFILES[row.cluster] || {};
                        const clusterData = kpisCalculados.porCluster[row.cluster];
                        return (
                          <tr key={row.cluster} className="border-b hover:bg-gray-50">
                            <td className="p-3">
                              <span className="text-xl mr-2">{profile.emoji}</span>
                              <span className="font-semibold">Cluster {row.cluster}</span>
                            </td>
                            <td className="p-3">
                              <span className="font-medium" style={{ color: profile.color }}>{profile.nombre}</span>
                            </td>
                            <td className="p-3 text-right font-semibold">{row.cantidad_polizas || clusterData?.count || 0}</td>
                            <td className="p-3 text-right">{(row.porcentaje || 0).toFixed(1)}%</td>
                            <td className="p-3 text-right">{clusterData?.montoPromedio?.toFixed(2) || '0.00'} UF</td>
                            <td className="p-3 text-right font-semibold">{clusterData?.montoTotal?.toLocaleString('es-CL', {maximumFractionDigits: 0}) || 0} UF</td>
                            <td className="p-3">
                              <span className="text-xs px-2 py-1 rounded bg-gray-100">{profile.accion}</span>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </>
            )}
            
            {(!clustersStats?.clusters || clustersStats.clusters.length === 0) && (
              <div className="bg-yellow-50 border border-yellow-200 p-6 rounded-lg text-yellow-800">
                No hay datos de clusters disponibles. Asegúrate de que el modelo ML esté entrenado.
              </div>
            )}
          </div>
        )}

        {/* TAB 3: Calidad de Datos */}
        {activeTab === 'limpieza' && (
          <div className="space-y-6">
            {reporteLimpieza ? (
              <>
                <div className="bg-white p-6 rounded-lg shadow">
                  <h3 className="font-semibold text-gray-900 mb-4">Métrica de Limpieza General</h3>
                  <div className="w-full bg-gray-200 rounded-full h-8 overflow-hidden">
                    <div
                      className="bg-green-500 h-full flex items-center justify-center text-white font-semibold text-sm transition-all"
                      style={{ width: `${reporteLimpieza.porcentaje_limpios || 0}%` }}
                    >
                      {(reporteLimpieza.porcentaje_limpios || 0).toFixed(1)}% Datos Limpios
                    </div>
                  </div>
                  <div className="text-sm text-gray-600 mt-2">
                    {(reporteLimpieza.issues?.total_polizas || 0) - (reporteLimpieza.issues?.datos_no_confiables || 0)} de {reporteLimpieza.issues?.total_polizas || 0} registros son confiables.
                  </div>
                </div>
                <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                  <div className="bg-white p-6 rounded-lg shadow border-l-4 border-blue-500">
                    <div className="text-sm text-gray-600">Total Pólizas</div>
                    <div className="text-3xl font-bold text-blue-600">{reporteLimpieza.issues?.total_polizas || 0}</div>
                  </div>
                  <div className="bg-white p-6 rounded-lg shadow border-l-4 border-red-500">
                    <div className="text-sm text-gray-600">No Confiables</div>
                    <div className="text-3xl font-bold text-red-600">{reporteLimpieza.issues?.datos_no_confiables || 0}</div>
                  </div>
                  <div className="bg-white p-6 rounded-lg shadow border-l-4 border-yellow-500">
                    <div className="text-sm text-gray-600">Sin Cobranzas</div>
                    <div className="text-3xl font-bold text-yellow-600">{reporteLimpieza.issues?.sin_cobranzas || 0}</div>
                  </div>
                  <div className="bg-white p-6 rounded-lg shadow border-l-4 border-purple-500">
                    <div className="text-sm text-gray-600">Sin Vigencia</div>
                    <div className="text-3xl font-bold text-purple-600">{reporteLimpieza.issues?.sin_vigencia || 0}</div>
                  </div>
                  <div className="bg-white p-6 rounded-lg shadow border-l-4 border-indigo-500">
                    <div className="text-sm text-gray-600">Sin Cliente</div>
                    <div className="text-3xl font-bold text-indigo-600">{reporteLimpieza.issues?.sin_cliente || 0}</div>
                  </div>
                  <div className="bg-white p-6 rounded-lg shadow border-l-4 border-orange-500">
                    <div className="text-sm text-gray-600">Alertas Críticas</div>
                    <div className="text-3xl font-bold text-orange-600">{reporteLimpieza.issues?.alertas_criticas || 0}</div>
                  </div>
                </div>
              </>
            ) : (
              <div className="bg-yellow-50 border border-yellow-200 p-6 rounded-lg text-yellow-800">
                No hay datos de calidad disponibles. Intenta recargar la página.
              </div>
            )}
          </div>
        )}

      </div>
    </div>
  );
};

export default Analytics;
