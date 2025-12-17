import React, { useEffect, useState } from "react";
import api from "../services/api";

export default function HistorialImportaciones() {
  const [historial, setHistorial] = useState([]);
  const [loading, setLoading] = useState(true);
  const [deleting, setDeleting] = useState(null);
  const [estadisticas, setEstadisticas] = useState(null);
  const [showModal, setShowModal] = useState(false);
  const [modalData, setModalData] = useState(null);
  const [loadingModal, setLoadingModal] = useState(false);
  const [selectedSheet, setSelectedSheet] = useState(null);

  useEffect(() => {
    loadHistorial();
    loadEstadisticas();
  }, []);

  const loadHistorial = async () => {
    try {
      console.log('Historial: Llamando a /importaciones/historial/...');
      const res = await api.get("/importaciones/historial/");
      console.log('Historial: res.data:', res.data);
      
      let data = res.data;
      if (data && data.results) {
        data = data.results;
      } else if (!Array.isArray(data)) {
        console.warn('Historial: res.data no es un array, usando []');
        data = [];
      }
      
      console.log('Historial: Datos procesados:', data.length, 'registros');
      setHistorial(data);
    } catch (err) {
      console.error("Historial: Error al cargar:", err);
      console.error("Historial: Detalles:", err.response?.data);
    } finally {
      setLoading(false);
    }
  };

  const loadEstadisticas = async () => {
    try {
      const res = await api.get("/importaciones/historial-estadisticas/");
      setEstadisticas(res.data);
    } catch (err) {
      console.error("Error al cargar estadísticas:", err);
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('¿Estás seguro de que deseas eliminar esta importación?')) {
      return;
    }

    setDeleting(id);
    try {
      await api.delete(`/importaciones/historial/${id}/`);
      setHistorial(historial.filter(item => item.id !== id));
      alert('✅ Importación eliminada correctamente');
    } catch (err) {
      console.error("Error al eliminar:", err);
      alert('❌ Error al eliminar la importación: ' + (err.response?.data?.error || err.message));
    } finally {
      setDeleting(null);
    }
  };

  const handleViewData = async (id) => {
    setLoadingModal(true);
    setShowModal(true);
    setSelectedSheet(null);
    
    try {
      const res = await api.get(`/importaciones/visualizar/${id}/`);
      setModalData(res.data);
      // Seleccionar la primera hoja por defecto
      if (res.data?.excel_data?.sheets?.length > 0) {
        setSelectedSheet(res.data.excel_data.sheets[0]);
      }
    } catch (err) {
      console.error("Error al cargar datos:", err);
      alert('❌ Error al cargar los datos: ' + (err.response?.data?.error || err.message));
      setShowModal(false);
    } finally {
      setLoadingModal(false);
    }
  };

  const closeModal = () => {
    setShowModal(false);
    setModalData(null);
    setSelectedSheet(null);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-100">
      {/* Header */}
      <div className="bg-gradient-to-r from-blue-600 via-blue-700 to-indigo-800 text-white py-12 px-6 shadow-lg">
        <div className="max-w-6xl mx-auto flex justify-between items-center">
          <div>
            <h1 className="text-4xl font-bold mb-2">Historial de Importaciones</h1>
            <p className="text-blue-100 text-lg">Registro completo de todas las cargas</p>
          </div>
          <button
            onClick={loadHistorial}
            className="px-6 py-3 bg-white text-blue-600 font-semibold rounded-lg hover:shadow-lg transition-all transform hover:scale-105"
          >
            🔄 Actualizar
          </button>
        </div>
      </div>

      <div className="p-6 max-w-6xl mx-auto">
        {/* Tarjetas de Estadísticas */}
        {!loading && estadisticas && (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
            <div className="bg-gradient-to-br from-blue-50 to-blue-100 rounded-lg shadow-md p-6 border-l-4 border-blue-600">
              <p className="text-blue-600 text-sm font-semibold uppercase">Total de Pólizas</p>
              <p className="text-4xl font-bold text-blue-900 mt-2">{estadisticas.total_polizas_unicas}</p>
              <p className="text-blue-700 text-xs mt-2">Pólizas únicas en sistema</p>
            </div>

            <div className="bg-gradient-to-br from-green-50 to-green-100 rounded-lg shadow-md p-6 border-l-4 border-green-600">
              <p className="text-green-600 text-sm font-semibold uppercase">Importaciones</p>
              <p className="text-4xl font-bold text-green-900 mt-2">{estadisticas.total_importaciones}</p>
              <p className="text-green-700 text-xs mt-2">Total de cargas</p>
            </div>

            <div className="bg-gradient-to-br from-orange-50 to-orange-100 rounded-lg shadow-md p-6 border-l-4 border-orange-600">
              <p className="text-orange-600 text-sm font-semibold uppercase">Promedio</p>
              <p className="text-4xl font-bold text-orange-900 mt-2">{estadisticas.promedio_polizas_por_importacion}</p>
              <p className="text-orange-700 text-xs mt-2">Por importación</p>
            </div>

            <div className="bg-gradient-to-br from-purple-50 to-purple-100 rounded-lg shadow-md p-6 border-l-4 border-purple-600">
              <p className="text-purple-600 text-sm font-semibold uppercase">Última Carga</p>
              <p className="text-lg font-bold text-purple-900 mt-2">
                {estadisticas.ultima_importacion?.polizas || 0} polizas
              </p>
              <p className="text-purple-700 text-xs mt-2">
                {estadisticas.ultima_importacion?.fecha 
                  ? new Date(estadisticas.ultima_importacion.fecha).toLocaleDateString('es-CL')
                  : 'N/A'}
              </p>
            </div>
          </div>
        )}

        {loading && (
          <div className="flex items-center justify-center py-12">
            <div className="text-center">
              <div className="inline-block animate-spin text-4xl mb-4">⏳</div>
              <p className="text-slate-600 font-semibold">Cargando historial...</p>
            </div>
          </div>
        )}

        {!loading && historial.length === 0 && (
          <div className="bg-white rounded-xl shadow-lg p-12 text-center">
            <p className="text-4xl mb-4">📭</p>
            <p className="text-slate-600 font-semibold text-lg">No hay importaciones registradas</p>
            <p className="text-slate-500 text-sm mt-2">Los registros aparecerán aquí cuando realices tu primera carga.</p>
          </div>
        )}

        {!loading && historial.length > 0 && (
          <div className="bg-white rounded-xl shadow-lg overflow-hidden">
            <div className="bg-gradient-to-r from-slate-100 to-slate-50 p-6 border-b border-slate-200">
              <h2 className="text-2xl font-bold text-slate-800">Detalle de Importaciones ({historial.length})</h2>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gradient-to-r from-slate-100 to-slate-50">
                  <tr>
                    <th className="px-6 py-4 text-left text-sm font-semibold text-slate-700">ID</th>
                    <th className="px-6 py-4 text-left text-sm font-semibold text-slate-700">Fecha</th>
                    <th className="px-6 py-4 text-left text-sm font-semibold text-slate-700">Archivo</th>
                    <th className="px-6 py-4 text-left text-sm font-semibold text-slate-700">Insertados</th>
                    <th className="px-6 py-4 text-left text-sm font-semibold text-slate-700">Actualizados</th>
                    <th className="px-6 py-4 text-left text-sm font-semibold text-slate-700">Errores</th>
                    <th className="px-6 py-4 text-center text-sm font-semibold text-slate-700">Acciones</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200">
                  {historial.map((item, index) => (
                    <tr key={item.id} className={`hover:bg-blue-50 transition-colors duration-200 ${index % 2 === 0 ? 'bg-white' : 'bg-slate-50'}`}>
                      <td className="px-6 py-4 text-sm font-semibold text-slate-900">{item.id}</td>
                      <td className="px-6 py-4 text-sm text-slate-600">
                        {new Date(item.fecha_carga).toLocaleString()}
                      </td>
                      <td className="px-6 py-4 text-sm text-slate-600 truncate max-w-xs">
                        {(item.archivo || '').split('/').pop()}
                      </td>
                      <td className="px-6 py-4 text-sm font-bold">
                        <span className="bg-green-100 text-green-800 px-3 py-1 rounded-full">
                          {item.filas_insertadas || 0}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-sm font-bold">
                        <span className="bg-blue-100 text-blue-800 px-3 py-1 rounded-full">
                          {item.filas_actualizadas || 0}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-sm font-bold">
                        <span className={`px-3 py-1 rounded-full ${item.filas_erroneas > 0 ? 'bg-red-100 text-red-800' : 'bg-green-100 text-green-800'}`}>
                          {item.filas_erroneas || 0}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-sm text-center">
                        <div className="flex gap-2 justify-center">
                          <button
                            onClick={() => handleViewData(item.id)}
                            className="px-3 py-2 bg-blue-100 hover:bg-blue-200 text-blue-700 rounded-lg font-semibold text-sm transition-colors"
                            title="Ver datos de esta importación"
                          >
                            👁️ Ver Datos
                          </button>
                          <button
                            onClick={() => handleDelete(item.id)}
                            disabled={deleting === item.id}
                            className="px-3 py-2 bg-red-100 hover:bg-red-200 text-red-700 rounded-lg font-semibold text-sm transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                            title="Eliminar esta importación"
                          >
                            {deleting === item.id ? '⏳' : '🗑️'}
                          </button>

        {/* Modal para visualizar datos */}
        {showModal && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-lg shadow-2xl w-[95vw] h-[98vh] flex flex-col">
              {/* Header estilo Excel */}
              <div className="bg-gradient-to-r from-green-600 to-green-700 text-white px-6 py-3 flex justify-between items-center">
                <div className="flex items-center space-x-4">
                  <span className="text-2xl">📊</span>
                  <div>
                    <h2 className="text-lg font-bold">Excel Viewer</h2>
                    {modalData && (
                      <p className="text-green-100 text-xs">
                        📁 {modalData.importacion.archivo} • {modalData.total_hojas} hoja(s) • {modalData.total_filas} fila(s)
                      </p>
                    )}
                  </div>
                </div>
                <button
                  onClick={closeModal}
                  className="text-white hover:bg-white hover:bg-opacity-20 rounded p-2 transition-all"
                >
                  ✖
                </button>
              </div>

              {/* Pestañas de hojas */}
              {modalData && modalData.excel_data && (
                <div className="bg-slate-100 border-b border-slate-300 px-4 py-2 flex space-x-2 overflow-x-auto">
                  {modalData.excel_data.sheets.map((sheet) => (
                    <button
                      key={sheet}
                      onClick={() => setSelectedSheet(sheet)}
                      className={`px-4 py-2 rounded-t text-sm font-medium transition-all ${
                        selectedSheet === sheet
                          ? 'bg-white text-green-700 border-t-2 border-green-600 shadow'
                          : 'bg-slate-200 text-slate-600 hover:bg-slate-300'
                      }`}
                    >
                      📄 {sheet}
                    </button>
                  ))}
                </div>
              )}

              {/* Contenido estilo Excel */}
              <div className="flex-1 overflow-auto bg-slate-50 p-2">
                {loadingModal && (
                  <div className="flex items-center justify-center h-full">
                    <div className="text-center">
                      <div className="inline-block animate-spin text-4xl mb-4">⏳</div>
                      <p className="text-slate-600 font-semibold">Cargando Excel...</p>
                    </div>
                  </div>
                )}

                {!loadingModal && modalData && selectedSheet && modalData.excel_data.data[selectedSheet] && (
                  <div className="bg-white border border-slate-300 shadow-sm">
                    <div className="overflow-auto max-h-[calc(100vh-140px)]">
                      <table className="w-full border-collapse" style={{ fontFamily: 'Arial, sans-serif', fontSize: '13px' }}>
                        {/* Headers estilo Excel */}
                        <thead className="sticky top-0 bg-slate-200">
                          <tr>
                            {/* Columna de números de fila */}
                            <th className="bg-slate-300 border border-slate-400 px-2 py-1 text-center text-slate-600 font-semibold w-12">
                              #
                            </th>
                            {modalData.excel_data.data[selectedSheet].headers.map((header, idx) => (
                              <th 
                                key={idx}
                                className="bg-slate-200 border border-slate-400 px-3 py-2 text-left text-slate-700 font-semibold whitespace-nowrap"
                              >
                                {header}
                              </th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {modalData.excel_data.data[selectedSheet].rows.map((row, rowIdx) => (
                            <tr key={rowIdx} className="hover:bg-blue-50">
                              {/* Número de fila */}
                              <td className="bg-slate-100 border border-slate-300 px-2 py-1 text-center text-slate-600 font-semibold text-xs">
                                {rowIdx + 1}
                              </td>
                              {row.map((cell, cellIdx) => (
                                <td 
                                  key={cellIdx}
                                  className="border border-slate-300 px-3 py-2 text-slate-800 whitespace-nowrap"
                                >
                                  {cell !== null && cell !== undefined ? String(cell) : ''}
                                </td>
                              ))}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}

                {!loadingModal && (!modalData || !selectedSheet) && (
                  <div className="flex items-center justify-center h-full">
                    <div className="text-center">
                      <p className="text-4xl mb-4">📭</p>
                      <p className="text-slate-600 font-semibold">No hay datos disponibles</p>
                    </div>
                  </div>
                )}
              </div>

              {/* Footer */}
              <div className="bg-slate-100 px-6 py-3 flex justify-between items-center border-t border-slate-300">
                <div className="text-sm text-slate-600">
                  {modalData && selectedSheet && (
                    <span>
                      📊 {modalData.excel_data.data[selectedSheet].rows.length} filas × {modalData.excel_data.data[selectedSheet].headers.length} columnas
                    </span>
                  )}
                </div>
                <button
                  onClick={closeModal}
                  className="px-6 py-2 bg-green-600 hover:bg-green-700 text-white rounded font-semibold transition-colors"
                >
                  Cerrar
                </button>
              </div>
            </div>
          </div>
        )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

