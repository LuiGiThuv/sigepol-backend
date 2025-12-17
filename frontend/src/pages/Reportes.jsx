import { useState, useEffect } from 'react';
import api from '../services/api';

export default function Reportes() {
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('automaticos'); // 'automaticos' o 'exportar'
  
  // PASO 9: Reportes Automáticos
  const [reporteVencidas, setReporteVencidas] = useState(null);
  const [reportePorExpirar, setReportePorExpirar] = useState(null);
  const [reporteProduccion, setReporteProduccion] = useState(null);
  const [reporteTopClientes, setReporteTopClientes] = useState(null);
  const [loadingReportes, setLoadingReportes] = useState({
    vencidas: false,
    porExpirar: false,
    produccion: false,
    topClientes: false,
  });
  
  const [filtrosPolizas, setFiltrosPolizas] = useState({
    estado: '',
    fecha_inicio_desde: '',
    fecha_inicio_hasta: '',
    fecha_venc_desde: '',
    fecha_venc_hasta: '',
    cliente_rut: '',
    formato: 'excel'
  });
  const [filtrosHistorial, setFiltrosHistorial] = useState({
    fecha_desde: '',
    fecha_hasta: '',
    formato: 'excel'
  });

  // Cargar reportes automáticos al montar
  useEffect(() => {
    if (activeTab === 'automaticos') {
      cargarReportesAutomaticos();
    }
  }, [activeTab]);

  // PASO 9: Cargar todos los reportes automáticos
  const cargarReportesAutomaticos = async () => {
    await Promise.all([
      cargarReporteVencidas(),
      cargarReportePorExpirar(),
      cargarReporteProduccion(),
      cargarReporteTopClientes(),
    ]);
  };

  const cargarReporteVencidas = async () => {
    setLoadingReportes(prev => ({...prev, vencidas: true}));
    try {
      const res = await api.get('/reportes/polizas-vencidas/');
      setReporteVencidas(res.data);
    } catch (err) {
      console.error('Error al cargar reporte de vencidas:', err);
    } finally {
      setLoadingReportes(prev => ({...prev, vencidas: false}));
    }
  };

  const cargarReportePorExpirar = async () => {
    setLoadingReportes(prev => ({...prev, porExpirar: true}));
    try {
      const res = await api.get('/reportes/polizas-por-expirar/');
      setReportePorExpirar(res.data);
    } catch (err) {
      console.error('Error al cargar reporte de por expirar:', err);
    } finally {
      setLoadingReportes(prev => ({...prev, porExpirar: false}));
    }
  };

  const cargarReporteProduccion = async () => {
    setLoadingReportes(prev => ({...prev, produccion: true}));
    try {
      const res = await api.get('/reportes/produccion-mensual/');
      setReporteProduccion(res.data);
    } catch (err) {
      console.error('Error al cargar reporte de producción:', err);
    } finally {
      setLoadingReportes(prev => ({...prev, produccion: false}));
    }
  };

  const cargarReporteTopClientes = async () => {
    setLoadingReportes(prev => ({...prev, topClientes: true}));
    try {
      const res = await api.get('/reportes/top-clientes/');
      setReporteTopClientes(res.data);
    } catch (err) {
      console.error('Error al cargar reporte de top clientes:', err);
    } finally {
      setLoadingReportes(prev => ({...prev, topClientes: false}));
    }
  };

  // Descargar reportes como CSV
  const descargarCSV = (datos, nombre) => {
    try {
      let csv = '';
      
      if (nombre === 'vencidas' && reporteVencidas?.polizas) {
        csv = 'Cliente,RUT,Póliza,Vencimiento,Días de Atraso,Estado,Prima UF\n';
        reporteVencidas.polizas.forEach(p => {
          csv += `"${p.cliente}","${p.rut}","${p.poliza}","${p.vencimiento}",${p.dias_atraso},"${p.estado}",${p.prima_uf}\n`;
        });
      } else if (nombre === 'porExpirar' && reportePorExpirar?.polizas) {
        csv = 'Cliente,RUT,Póliza,Vencimiento,Días Restantes,Recomendación,Prima UF,Estado\n';
        reportePorExpirar.polizas.forEach(p => {
          csv += `"${p.cliente}","${p.rut}","${p.poliza}","${p.vencimiento}",${p.dias_restantes},"${p.recomendacion}",${p.prima_uf},"${p.estado}"\n`;
        });
      } else if (nombre === 'topClientes' && reporteTopClientes?.clientes) {
        csv = 'Posición,Cliente,RUT,Total UF,Cantidad Pólizas,% Participación,Prima Promedio\n';
        reporteTopClientes.clientes.forEach(c => {
          csv += `${c.posicion},"${c.cliente}","${c.rut}",${c.total_uf},${c.cantidad_polizas},${c.participacion_porcentaje}%,${c.prima_promedio}\n`;
        });
      }
      
      const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
      const link = document.createElement('a');
      const url = URL.createObjectURL(blob);
      link.setAttribute('href', url);
      link.setAttribute('download', `${nombre}_${new Date().toISOString().split('T')[0]}.csv`);
      link.click();
    } catch (err) {
      console.error('Error al descargar CSV:', err);
      alert('Error al descargar el reporte');
    }
  };

  const handleExportarPolizas = async () => {
    try {
      setLoading(true);
      
      // Construir query params
      const params = new URLSearchParams();
      Object.entries(filtrosPolizas).forEach(([key, value]) => {
        if (value) params.append(key, value);
      });

      const response = await api.get(`/importaciones/exportar-polizas/?${params.toString()}`, {
        responseType: 'blob'
      });

      // Crear link de descarga
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      
      const extension = filtrosPolizas.formato === 'csv' ? 'csv' : 'xlsx';
      link.setAttribute('download', `polizas_${new Date().getTime()}.${extension}`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      
      alert('Reporte de pólizas exportado exitosamente');
    } catch (error) {
      console.error('Error al exportar pólizas:', error);
      alert('Error al exportar pólizas: ' + (error.response?.data?.error || error.message));
    } finally {
      setLoading(false);
    }
  };

  const handleExportarHistorial = async () => {
    try {
      setLoading(true);
      
      const params = new URLSearchParams();
      Object.entries(filtrosHistorial).forEach(([key, value]) => {
        if (value) params.append(key, value);
      });

      const response = await api.get(`/importaciones/exportar-historial/?${params.toString()}`, {
        responseType: 'blob'
      });

      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      
      const extension = filtrosHistorial.formato === 'csv' ? 'csv' : 'xlsx';
      link.setAttribute('download', `historial_${new Date().getTime()}.${extension}`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      
      alert('Reporte de historial exportado exitosamente');
    } catch (error) {
      console.error('Error al exportar historial:', error);
      alert('Error al exportar historial: ' + (error.response?.data?.error || error.message));
    } finally {
      setLoading(false);
    }
  };

  const limpiarFiltrosPolizas = () => {
    setFiltrosPolizas({
      estado: '',
      fecha_inicio_desde: '',
      fecha_inicio_hasta: '',
      fecha_venc_desde: '',
      fecha_venc_hasta: '',
      cliente_rut: '',
      formato: 'excel'
    });
  };

  const limpiarFiltrosHistorial = () => {
    setFiltrosHistorial({
      fecha_desde: '',
      fecha_hasta: '',
      formato: 'excel'
    });
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-100">
      {/* Header */}
      <div className="bg-gradient-to-r from-blue-600 via-blue-700 to-indigo-800 text-white py-12 px-6 shadow-lg">
        <div className="max-w-7xl mx-auto">
          <h1 className="text-5xl font-bold mb-2">📊 Reportes del Sistema</h1>
          <p className="text-blue-100 text-lg">Reportes automáticos y exportación personalizada</p>
        </div>
      </div>

      <div className="p-6 max-w-7xl mx-auto">
        {/* Tabs */}
        <div className="flex gap-4 mb-8 bg-white rounded-lg shadow-md p-2">
          <button
            onClick={() => setActiveTab('automaticos')}
            className={`flex-1 py-3 px-4 rounded-lg font-semibold transition-all ${
              activeTab === 'automaticos'
                ? 'bg-gradient-to-r from-blue-500 to-blue-700 text-white shadow-lg'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            📈 Reportes Automáticos
          </button>
          <button
            onClick={() => setActiveTab('exportar')}
            className={`flex-1 py-3 px-4 rounded-lg font-semibold transition-all ${
              activeTab === 'exportar'
                ? 'bg-gradient-to-r from-blue-500 to-blue-700 text-white shadow-lg'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            ⬇️ Exportar Reportes
          </button>
        </div>

        {/* TAB 1: Reportes Automáticos (PASO 9) */}
        {activeTab === 'automaticos' && (
          <div className="space-y-6">
            {/* PASO 9.1: Pólizas Vencidas */}
            <div className="bg-white rounded-xl shadow-lg overflow-hidden">
              <div className="bg-gradient-to-r from-red-500 to-red-700 p-6">
                <h2 className="text-2xl font-bold text-white flex items-center gap-2">
                  📘 Pólizas Vencidas
                </h2>
                <p className="text-red-100 text-sm mt-1">Pólizas que ya han excedido su fecha de vencimiento</p>
              </div>
              <div className="p-6">
                {loadingReportes.vencidas ? (
                  <div className="text-center py-8"><p className="text-gray-500">Cargando...</p></div>
                ) : reporteVencidas?.polizas?.length > 0 ? (
                  <div>
                    <div className="mb-4 flex justify-between items-center">
                      <span className="text-lg font-bold text-red-700">Total: {reporteVencidas.total} pólizas vencidas</span>
                      <button
                        onClick={() => descargarCSV(reporteVencidas, 'vencidas')}
                        className="bg-red-500 hover:bg-red-700 text-white px-4 py-2 rounded-lg font-semibold transition-all"
                      >
                        📥 Descargar CSV
                      </button>
                    </div>
                    <div className="overflow-x-auto">
                      <table className="w-full text-sm">
                        <thead className="bg-red-50">
                          <tr>
                            <th className="px-4 py-3 text-left font-semibold text-gray-700">Cliente</th>
                            <th className="px-4 py-3 text-left font-semibold text-gray-700">RUT</th>
                            <th className="px-4 py-3 text-left font-semibold text-gray-700">Póliza</th>
                            <th className="px-4 py-3 text-left font-semibold text-gray-700">Vencimiento</th>
                            <th className="px-4 py-3 text-center font-semibold text-gray-700">Días de Atraso</th>
                            <th className="px-4 py-3 text-left font-semibold text-gray-700">Prima (UF)</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-200">
                          {reporteVencidas.polizas.slice(0, 10).map((p) => (
                            <tr key={p.id} className="hover:bg-red-50">
                              <td className="px-4 py-3 font-semibold text-gray-900">{p.cliente}</td>
                              <td className="px-4 py-3 text-gray-700">{p.rut}</td>
                              <td className="px-4 py-3 text-gray-700">{p.poliza}</td>
                              <td className="px-4 py-3 text-gray-700">{p.vencimiento}</td>
                              <td className="px-4 py-3 text-center">
                                <span className="bg-red-100 text-red-800 px-3 py-1 rounded-full font-bold">{p.dias_atraso}d</span>
                              </td>
                              <td className="px-4 py-3 text-gray-700 font-semibold">{p.prima_uf.toFixed(2)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                    {reporteVencidas.total > 10 && (
                      <p className="text-sm text-gray-500 mt-4">Mostrando 10 de {reporteVencidas.total} pólizas</p>
                    )}
                  </div>
                ) : (
                  <div className="text-center py-8">
                    <p className="text-gray-500 text-lg">✅ No hay pólizas vencidas</p>
                  </div>
                )}
              </div>
            </div>

            {/* PASO 9.2: Pólizas por Expirar */}
            <div className="bg-white rounded-xl shadow-lg overflow-hidden">
              <div className="bg-gradient-to-r from-yellow-500 to-yellow-700 p-6">
                <h2 className="text-2xl font-bold text-white flex items-center gap-2">
                  📙 Pólizas por Expirar (30 días)
                </h2>
                <p className="text-yellow-100 text-sm mt-1">Pólizas que vencerán en los próximos 30 días</p>
              </div>
              <div className="p-6">
                {loadingReportes.porExpirar ? (
                  <div className="text-center py-8"><p className="text-gray-500">Cargando...</p></div>
                ) : reportePorExpirar?.polizas?.length > 0 ? (
                  <div>
                    <div className="mb-4 flex justify-between items-center">
                      <span className="text-lg font-bold text-yellow-700">Total: {reportePorExpirar.total} pólizas por expirar</span>
                      <button
                        onClick={() => descargarCSV(reportePorExpirar, 'porExpirar')}
                        className="bg-yellow-500 hover:bg-yellow-700 text-white px-4 py-2 rounded-lg font-semibold transition-all"
                      >
                        📥 Descargar CSV
                      </button>
                    </div>
                    <div className="overflow-x-auto">
                      <table className="w-full text-sm">
                        <thead className="bg-yellow-50">
                          <tr>
                            <th className="px-4 py-3 text-left font-semibold text-gray-700">Cliente</th>
                            <th className="px-4 py-3 text-left font-semibold text-gray-700">RUT</th>
                            <th className="px-4 py-3 text-left font-semibold text-gray-700">Póliza</th>
                            <th className="px-4 py-3 text-left font-semibold text-gray-700">Vencimiento</th>
                            <th className="px-4 py-3 text-center font-semibold text-gray-700">Días Restantes</th>
                            <th className="px-4 py-3 text-left font-semibold text-gray-700">Recomendación</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-200">
                          {reportePorExpirar.polizas.slice(0, 10).map((p) => (
                            <tr key={p.id} className="hover:bg-yellow-50">
                              <td className="px-4 py-3 font-semibold text-gray-900">{p.cliente}</td>
                              <td className="px-4 py-3 text-gray-700">{p.rut}</td>
                              <td className="px-4 py-3 text-gray-700">{p.poliza}</td>
                              <td className="px-4 py-3 text-gray-700">{p.vencimiento}</td>
                              <td className="px-4 py-3 text-center">
                                <span className={`px-3 py-1 rounded-full font-bold ${
                                  p.dias_restantes <= 5 ? 'bg-red-100 text-red-800' : 'bg-yellow-100 text-yellow-800'
                                }`}>
                                  {p.dias_restantes}d
                                </span>
                              </td>
                              <td className="px-4 py-3 text-sm italic text-gray-600">{p.recomendacion}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                    {reportePorExpirar.total > 10 && (
                      <p className="text-sm text-gray-500 mt-4">Mostrando 10 de {reportePorExpirar.total} pólizas</p>
                    )}
                  </div>
                ) : (
                  <div className="text-center py-8">
                    <p className="text-gray-500 text-lg">✅ No hay pólizas por expirar en los próximos 30 días</p>
                  </div>
                )}
              </div>
            </div>

            {/* PASO 9.3: Producción Mensual */}
            <div className="bg-white rounded-xl shadow-lg overflow-hidden">
              <div className="bg-gradient-to-r from-green-500 to-green-700 p-6">
                <h2 className="text-2xl font-bold text-white flex items-center gap-2">
                  📗 Producción Mensual
                </h2>
                <p className="text-green-100 text-sm mt-1">Análisis de producción del mes actual vs. mes anterior</p>
              </div>
              <div className="p-6">
                {loadingReportes.produccion ? (
                  <div className="text-center py-8"><p className="text-gray-500">Cargando...</p></div>
                ) : reporteProduccion ? (
                  <div className="space-y-6">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                      {/* Producción Actual */}
                      <div className="bg-gradient-to-br from-green-50 to-green-100 p-6 rounded-lg border border-green-200">
                        <h3 className="text-lg font-bold text-green-800 mb-4">📅 {reporteProduccion.mes}</h3>
                        <div className="space-y-3">
                          <div>
                            <p className="text-sm text-gray-600">Prima Total (UF)</p>
                            <p className="text-3xl font-bold text-green-700">{reporteProduccion.produccion_actual.total_prima_uf.toFixed(0)}</p>
                          </div>
                          <div>
                            <p className="text-sm text-gray-600">Pólizas Emitidas</p>
                            <p className="text-2xl font-bold text-green-700">{reporteProduccion.produccion_actual.cantidad_polizas}</p>
                          </div>
                          <div>
                            <p className="text-sm text-gray-600">Prima Promedio</p>
                            <p className="text-lg font-semibold text-green-700">{reporteProduccion.produccion_actual.prima_promedio.toFixed(2)} UF</p>
                          </div>
                        </div>
                      </div>

                      {/* Variación */}
                      <div className="bg-gradient-to-br from-blue-50 to-blue-100 p-6 rounded-lg border border-blue-200">
                        <h3 className="text-lg font-bold text-blue-800 mb-4">📊 Variación</h3>
                        <div className="space-y-3">
                          <div>
                            <p className="text-sm text-gray-600">Prima (Diferencia)</p>
                            <p className={`text-2xl font-bold ${reporteProduccion.variacion.prima_uf >= 0 ? 'text-green-700' : 'text-red-700'}`}>
                              {reporteProduccion.variacion.prima_uf >= 0 ? '+' : ''}{reporteProduccion.variacion.prima_uf.toFixed(0)} UF
                            </p>
                            <p className={`text-sm font-semibold ${reporteProduccion.variacion.prima_porcentaje >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                              {reporteProduccion.variacion.prima_porcentaje >= 0 ? '+' : ''}{reporteProduccion.variacion.prima_porcentaje}%
                            </p>
                          </div>
                          <div>
                            <p className="text-sm text-gray-600">Pólizas (Diferencia)</p>
                            <p className={`text-lg font-bold ${reporteProduccion.variacion.polizas >= 0 ? 'text-green-700' : 'text-red-700'}`}>
                              {reporteProduccion.variacion.polizas >= 0 ? '+' : ''}{reporteProduccion.variacion.polizas}
                            </p>
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Cartera */}
                    <div className="bg-indigo-50 p-6 rounded-lg border border-indigo-200">
                      <h3 className="text-lg font-bold text-indigo-800 mb-4">💼 Cartera Vigente</h3>
                      <div>
                        <p className="text-sm text-gray-600">Pólizas Vigentes en el Sistema</p>
                        <p className="text-3xl font-bold text-indigo-700">{reporteProduccion.cartera.total_vigentes}</p>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="text-center py-8">
                    <p className="text-gray-500 text-lg">Error al cargar el reporte</p>
                  </div>
                )}
              </div>
            </div>

            {/* PASO 9.4: Top Clientes */}
            <div className="bg-white rounded-xl shadow-lg overflow-hidden">
              <div className="bg-gradient-to-r from-purple-500 to-purple-700 p-6">
                <h2 className="text-2xl font-bold text-white flex items-center gap-2">
                  📕 Top Clientes por Producción
                </h2>
                <p className="text-purple-100 text-sm mt-1">Ranking de clientes según producción del mes actual</p>
              </div>
              <div className="p-6">
                {loadingReportes.topClientes ? (
                  <div className="text-center py-8"><p className="text-gray-500">Cargando...</p></div>
                ) : reporteTopClientes?.clientes?.length > 0 ? (
                  <div>
                    <div className="mb-4 flex justify-between items-center">
                      <span className="text-lg font-bold text-purple-700">Top {reporteTopClientes.total_ranking} Clientes</span>
                      <button
                        onClick={() => descargarCSV(reporteTopClientes, 'topClientes')}
                        className="bg-purple-500 hover:bg-purple-700 text-white px-4 py-2 rounded-lg font-semibold transition-all"
                      >
                        📥 Descargar CSV
                      </button>
                    </div>
                    <div className="overflow-x-auto">
                      <table className="w-full text-sm">
                        <thead className="bg-purple-50">
                          <tr>
                            <th className="px-4 py-3 text-center font-semibold text-gray-700">Pos.</th>
                            <th className="px-4 py-3 text-left font-semibold text-gray-700">Cliente</th>
                            <th className="px-4 py-3 text-left font-semibold text-gray-700">RUT</th>
                            <th className="px-4 py-3 text-right font-semibold text-gray-700">Total (UF)</th>
                            <th className="px-4 py-3 text-center font-semibold text-gray-700">Pólizas</th>
                            <th className="px-4 py-3 text-right font-semibold text-gray-700">% Participación</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-200">
                          {reporteTopClientes.clientes.map((c) => (
                            <tr key={c.cliente_id} className="hover:bg-purple-50">
                              <td className="px-4 py-3 text-center">
                                <span className="bg-purple-100 text-purple-800 px-3 py-1 rounded-full font-bold">#{c.posicion}</span>
                              </td>
                              <td className="px-4 py-3 font-semibold text-gray-900">{c.cliente}</td>
                              <td className="px-4 py-3 text-gray-700">{c.rut}</td>
                              <td className="px-4 py-3 text-right font-semibold text-gray-900">{c.total_uf.toFixed(2)}</td>
                              <td className="px-4 py-3 text-center font-semibold text-gray-700">{c.cantidad_polizas}</td>
                              <td className="px-4 py-3 text-right">
                                <div className="flex items-center justify-end gap-2">
                                  <div className="w-16 bg-gray-200 rounded-full h-2">
                                    <div
                                      className="bg-purple-500 h-2 rounded-full"
                                      style={{width: `${Math.min(c.participacion_porcentaje * 5, 100)}%`}}
                                    ></div>
                                  </div>
                                  <span className="font-bold text-purple-700 w-12 text-right">{c.participacion_porcentaje}%</span>
                                </div>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                ) : (
                  <div className="text-center py-8">
                    <p className="text-gray-500 text-lg">No hay clientes con producción este mes</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* TAB 2: Exportar Reportes (Original) */}
        {activeTab === 'exportar' && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          
          {/* Card: Exportar Pólizas */}
          <div className="bg-white rounded-xl shadow-lg overflow-hidden">
            <div className="bg-gradient-to-r from-green-500 to-green-700 p-6">
              <h2 className="text-2xl font-bold text-white flex items-center gap-2">
                📋 Exportar Pólizas
              </h2>
              <p className="text-green-100 text-sm mt-1">Filtra y descarga pólizas en Excel o CSV</p>
            </div>

            <div className="p-6 space-y-4">
              {/* Estado */}
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-2">Estado</label>
                <select
                  value={filtrosPolizas.estado}
                  onChange={(e) => setFiltrosPolizas({...filtrosPolizas, estado: e.target.value})}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent"
                >
                  <option value="">Todos los estados</option>
                  <option value="VIGENTE">Vigente</option>
                  <option value="VENCIDA">Vencida</option>
                  <option value="CANCELADA">Cancelada</option>
                </select>
              </div>

              {/* Fechas de Inicio */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-semibold text-gray-700 mb-2">Inicio Desde</label>
                  <input
                    type="date"
                    value={filtrosPolizas.fecha_inicio_desde}
                    onChange={(e) => setFiltrosPolizas({...filtrosPolizas, fecha_inicio_desde: e.target.value})}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent"
                  />
                </div>
                <div>
                  <label className="block text-sm font-semibold text-gray-700 mb-2">Inicio Hasta</label>
                  <input
                    type="date"
                    value={filtrosPolizas.fecha_inicio_hasta}
                    onChange={(e) => setFiltrosPolizas({...filtrosPolizas, fecha_inicio_hasta: e.target.value})}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent"
                  />
                </div>
              </div>

              {/* Fechas de Vencimiento */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-semibold text-gray-700 mb-2">Venc. Desde</label>
                  <input
                    type="date"
                    value={filtrosPolizas.fecha_venc_desde}
                    onChange={(e) => setFiltrosPolizas({...filtrosPolizas, fecha_venc_desde: e.target.value})}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent"
                  />
                </div>
                <div>
                  <label className="block text-sm font-semibold text-gray-700 mb-2">Venc. Hasta</label>
                  <input
                    type="date"
                    value={filtrosPolizas.fecha_venc_hasta}
                    onChange={(e) => setFiltrosPolizas({...filtrosPolizas, fecha_venc_hasta: e.target.value})}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent"
                  />
                </div>
              </div>

              {/* RUT Cliente */}
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-2">RUT Cliente</label>
                <input
                  type="text"
                  placeholder="Ej: 12345678-9"
                  value={filtrosPolizas.cliente_rut}
                  onChange={(e) => setFiltrosPolizas({...filtrosPolizas, cliente_rut: e.target.value})}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent"
                />
              </div>

              {/* Formato */}
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-2">Formato</label>
                <select
                  value={filtrosPolizas.formato}
                  onChange={(e) => setFiltrosPolizas({...filtrosPolizas, formato: e.target.value})}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent"
                >
                  <option value="excel">Excel (.xlsx)</option>
                  <option value="csv">CSV (.csv)</option>
                </select>
              </div>

              {/* Botones */}
              <div className="flex gap-3 pt-4">
                <button
                  onClick={handleExportarPolizas}
                  disabled={loading}
                  className="flex-1 bg-gradient-to-r from-green-500 to-green-700 text-white py-3 px-6 rounded-lg font-semibold hover:from-green-600 hover:to-green-800 transition-all shadow-lg hover:shadow-xl disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {loading ? '⏳ Exportando...' : '⬇️ Exportar Pólizas'}
                </button>
                <button
                  onClick={limpiarFiltrosPolizas}
                  className="px-6 py-3 bg-gray-200 text-gray-700 rounded-lg font-semibold hover:bg-gray-300 transition-all"
                >
                  🔄 Limpiar
                </button>
              </div>
            </div>
          </div>

          {/* Card: Exportar Historial */}
          <div className="bg-white rounded-xl shadow-lg overflow-hidden">
            <div className="bg-gradient-to-r from-purple-500 to-purple-700 p-6">
              <h2 className="text-2xl font-bold text-white flex items-center gap-2">
                📅 Exportar Historial
              </h2>
              <p className="text-purple-100 text-sm mt-1">Descarga el historial de importaciones</p>
            </div>

            <div className="p-6 space-y-4">
              {/* Fecha Desde */}
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-2">Fecha Desde</label>
                <input
                  type="date"
                  value={filtrosHistorial.fecha_desde}
                  onChange={(e) => setFiltrosHistorial({...filtrosHistorial, fecha_desde: e.target.value})}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                />
              </div>

              {/* Fecha Hasta */}
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-2">Fecha Hasta</label>
                <input
                  type="date"
                  value={filtrosHistorial.fecha_hasta}
                  onChange={(e) => setFiltrosHistorial({...filtrosHistorial, fecha_hasta: e.target.value})}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                />
              </div>

              {/* Formato */}
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-2">Formato</label>
                <select
                  value={filtrosHistorial.formato}
                  onChange={(e) => setFiltrosHistorial({...filtrosHistorial, formato: e.target.value})}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                >
                  <option value="excel">Excel (.xlsx)</option>
                  <option value="csv">CSV (.csv)</option>
                </select>
              </div>

              {/* Botones */}
              <div className="flex gap-3 pt-4">
                <button
                  onClick={handleExportarHistorial}
                  disabled={loading}
                  className="flex-1 bg-gradient-to-r from-purple-500 to-purple-700 text-white py-3 px-6 rounded-lg font-semibold hover:from-purple-600 hover:to-purple-800 transition-all shadow-lg hover:shadow-xl disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {loading ? '⏳ Exportando...' : '⬇️ Exportar Historial'}
                </button>
                <button
                  onClick={limpiarFiltrosHistorial}
                  className="px-6 py-3 bg-gray-200 text-gray-700 rounded-lg font-semibold hover:bg-gray-300 transition-all"
                >
                  🔄 Limpiar
                </button>
              </div>

              {/* Info adicional */}
              <div className="mt-6 p-4 bg-purple-50 rounded-lg border border-purple-200">
                <p className="text-sm text-purple-800">
                  <strong>💡 Tip:</strong> Si no seleccionas fechas, se exportarán todos los registros disponibles.
                </p>
              </div>
            </div>
          </div>
        </div>
        )}

        {/* Información de ayuda */}
        <div className="mt-8 bg-white rounded-xl shadow-lg p-6">
          <h3 className="text-xl font-bold text-gray-800 mb-4">ℹ️ Información sobre Reportes</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-sm text-gray-700">
            <div>
              <h4 className="font-semibold text-green-700 mb-2">📋 Reporte de Pólizas</h4>
              <ul className="list-disc list-inside space-y-1">
                <li>Exporta todas las pólizas del sistema</li>
                <li>Filtra por estado (Vigente, Vencida, Cancelada)</li>
                <li>Filtra por rangos de fechas de inicio y vencimiento</li>
                <li>Busca por RUT de cliente específico</li>
                <li>Incluye información del cliente asociado</li>
              </ul>
            </div>
            <div>
              <h4 className="font-semibold text-purple-700 mb-2">📅 Reporte de Historial</h4>
              <ul className="list-disc list-inside space-y-1">
                <li>Exporta el historial completo de importaciones</li>
                <li>Filtra por rango de fechas de carga</li>
                <li>Incluye estadísticas de cada importación</li>
                <li>Muestra filas insertadas, actualizadas y con errores</li>
                <li>Calcula la tasa de éxito automáticamente</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
