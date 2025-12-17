import React, { useEffect, useState } from "react";
import api from "../services/api";

export default function Auditorias() {
  const [auditorias, setAuditorias] = useState([]);
  const [logAccesos, setLogAccesos] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState("acciones");

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      
      // Cargar auditorías
      const auditRes = await api.get("/auditorias/acciones/");
      const auditData = auditRes.data.results || auditRes.data || [];
      setAuditorias(Array.isArray(auditData) ? auditData.slice(0, 100) : []);

      // Cargar logs de acceso
      const logRes = await api.get("/auditorias/logs/");
      const logData = logRes.data.results || logRes.data || [];
      setLogAccesos(Array.isArray(logData) ? logData.slice(0, 100) : []);

      // Cargar estadísticas
      const statsRes = await api.get("/auditorias/admin-stats/");
      setStats(statsRes.data);
    } catch (err) {
      console.error("Error al cargar auditorías:", err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-100">
      {/* Header */}
      <div className="bg-gradient-to-r from-blue-600 via-blue-700 to-indigo-800 text-white py-12 px-6 shadow-lg">
        <div className="max-w-7xl mx-auto flex justify-between items-center">
          <div>
            <h1 className="text-4xl font-bold mb-2">🔐 Auditorías del Sistema</h1>
            <p className="text-blue-100 text-lg">Registro completo de acciones y accesos</p>
          </div>
          <button
            onClick={loadData}
            className="px-6 py-3 bg-white text-blue-600 font-semibold rounded-lg hover:shadow-lg transition-all transform hover:scale-105"
          >
            🔄 Actualizar
          </button>
        </div>
      </div>

      <div className="p-6 max-w-7xl mx-auto">
        {/* Estadísticas */}
        {stats && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
            <div className="bg-white rounded-xl shadow-lg p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-slate-600 text-sm font-medium">Total Usuarios</p>
                  <p className="text-4xl font-bold text-blue-600 mt-2">{stats.total_usuarios || 0}</p>
                </div>
                <span className="text-5xl">👥</span>
              </div>
            </div>

            <div className="bg-white rounded-xl shadow-lg p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-slate-600 text-sm font-medium">Acciones Registradas</p>
                  <p className="text-4xl font-bold text-green-600 mt-2">{stats.total_acciones || 0}</p>
                </div>
                <span className="text-5xl">📝</span>
              </div>
            </div>

            <div className="bg-white rounded-xl shadow-lg p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-slate-600 text-sm font-medium">Accesos Registrados</p>
                  <p className="text-4xl font-bold text-purple-600 mt-2">{stats.total_accesos || 0}</p>
                </div>
                <span className="text-5xl">🔑</span>
              </div>
            </div>
          </div>
        )}

        {/* Tabs */}
        <div className="bg-white rounded-xl shadow-lg overflow-hidden mb-8">
          <div className="flex border-b border-slate-200">
            <button
              onClick={() => setActiveTab("acciones")}
              className={`flex-1 py-4 px-6 font-semibold transition-colors ${
                activeTab === "acciones"
                  ? "bg-blue-100 text-blue-700 border-b-2 border-blue-600"
                  : "text-slate-600 hover:text-blue-600"
              }`}
            >
              📝 Acciones ({auditorias.length})
            </button>
            <button
              onClick={() => setActiveTab("accesos")}
              className={`flex-1 py-4 px-6 font-semibold transition-colors ${
                activeTab === "accesos"
                  ? "bg-blue-100 text-blue-700 border-b-2 border-blue-600"
                  : "text-slate-600 hover:text-blue-600"
              }`}
            >
              🔐 Accesos ({logAccesos.length})
            </button>
          </div>

          {/* Tab: Acciones */}
          {activeTab === "acciones" && (
            <div className="p-6">
              {loading ? (
                <div className="text-center py-12">
                  <div className="inline-block animate-spin text-4xl mb-4">⏳</div>
                  <p className="text-slate-600 font-semibold">Cargando acciones...</p>
                </div>
              ) : auditorias.length === 0 ? (
                <div className="text-center py-12">
                  <p className="text-4xl mb-4">📭</p>
                  <p className="text-slate-600 font-semibold">No hay acciones registradas</p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead className="bg-slate-100">
                      <tr>
                        <th className="px-6 py-4 text-left text-sm font-semibold text-slate-700">Usuario</th>
                        <th className="px-6 py-4 text-left text-sm font-semibold text-slate-700">Acción</th>
                        <th className="px-6 py-4 text-left text-sm font-semibold text-slate-700">Modelo</th>
                        <th className="px-6 py-4 text-left text-sm font-semibold text-slate-700">Fecha</th>
                        <th className="px-6 py-4 text-left text-sm font-semibold text-slate-700">Detalles</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-200">
                      {auditorias.map((item) => (
                        <tr key={item.id} className="hover:bg-slate-50 transition-colors">
                          <td className="px-6 py-4 text-sm font-semibold text-slate-900">
                            {item.usuario_username || 'N/A'}
                          </td>
                          <td className="px-6 py-4 text-sm">
                            <span className={`px-3 py-1 rounded-full font-semibold ${
                              item.accion?.toLowerCase() === 'create' ? 'bg-green-100 text-green-800' :
                              item.accion?.toLowerCase() === 'update' ? 'bg-blue-100 text-blue-800' :
                              item.accion?.toLowerCase() === 'delete' ? 'bg-red-100 text-red-800' :
                              'bg-slate-100 text-slate-800'
                            }`}>
                              {item.accion?.toUpperCase() || 'OTRO'}
                            </span>
                          </td>
                          <td className="px-6 py-4 text-sm text-slate-600">{item.modelo}</td>
                          <td className="px-6 py-4 text-sm text-slate-600">
                            {item.fecha_hora ? new Date(item.fecha_hora).toLocaleString('es-ES') : 'N/A'}
                          </td>
                          <td className="px-6 py-4 text-sm text-slate-600 truncate max-w-xs">
                            {item.descripcion || '...'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}

          {/* Tab: Accesos */}
          {activeTab === "accesos" && (
            <div className="p-6">
              {loading ? (
                <div className="text-center py-12">
                  <div className="inline-block animate-spin text-4xl mb-4">⏳</div>
                  <p className="text-slate-600 font-semibold">Cargando accesos...</p>
                </div>
              ) : logAccesos.length === 0 ? (
                <div className="text-center py-12">
                  <p className="text-4xl mb-4">📭</p>
                  <p className="text-slate-600 font-semibold">No hay accesos registrados</p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead className="bg-slate-100">
                      <tr>
                        <th className="px-6 py-4 text-left text-sm font-semibold text-slate-700">Usuario</th>
                        <th className="px-6 py-4 text-left text-sm font-semibold text-slate-700">Acción</th>
                        <th className="px-6 py-4 text-left text-sm font-semibold text-slate-700">IP</th>
                        <th className="px-6 py-4 text-left text-sm font-semibold text-slate-700">Estado</th>
                        <th className="px-6 py-4 text-left text-sm font-semibold text-slate-700">Fecha</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-200">
                      {logAccesos.map((item) => (
                        <tr key={item.id} className="hover:bg-slate-50 transition-colors">
                          <td className="px-6 py-4 text-sm font-semibold text-slate-900">
                            {item.usuario_username || 'Anónimo'}
                          </td>
                          <td className="px-6 py-4 text-sm text-slate-600">{item.endpoint || item.accion}</td>
                          <td className="px-6 py-4 text-sm text-slate-600">{item.ip_address}</td>
                          <td className="px-6 py-4 text-sm">
                            <span className={`px-3 py-1 rounded-full font-semibold ${
                              item.resultado === 'EXITOSO' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                            }`}>
                              {item.resultado === 'EXITOSO' ? '✅ Exitoso' : '❌ Fallido'}
                            </span>
                          </td>
                          <td className="px-6 py-4 text-sm text-slate-600">
                            {item.timestamp ? new Date(item.timestamp).toLocaleString('es-ES') : 'N/A'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
