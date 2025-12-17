import { useEffect, useState } from 'react';
import api from '../services/api';

export default function Dashboard() {
  const [stats, setStats] = useState({
    totalImports: 0,
    totalPolicies: 0,
    successRate: 0,
    lastImport: 'Nunca',
  });
  const [historial, setHistorial] = useState([]);
  const [loading, setLoading] = useState(true);
  
  // PASO 10: Estados para alertas
  const [alertasStats, setAlertasStats] = useState({
    totales: 0,
    pendientes: 0,
    criticas: 0,
  });
  const [ejecutandoAlertas, setEjecutandoAlertas] = useState(false);
  const [notificacion, setNotificacion] = useState(null);

  useEffect(() => {
    loadDashboardData();
    cargarEstadisticasAlertas(); // PASO 10: Cargar alertas al iniciar
  }, []);

  const loadDashboardData = async () => {
    try {
      setLoading(true);
      console.log('Dashboard: Llamando a /importaciones/historial/...');
      const res = await api.get('/importaciones/historial/');
      console.log('Dashboard: Respuesta completa:', res);
      console.log('Dashboard: res.data:', res.data);
      console.log('Dashboard: Tipo de res.data:', typeof res.data);
      
      // El endpoint puede devolver un objeto con resultados paginados o un array directo
      let data = res.data;
      if (data && data.results) {
        // Si es paginado
        data = data.results;
      } else if (!Array.isArray(data)) {
        // Si no es un array, convertirlo en array vacío
        console.warn('Dashboard: res.data no es un array, usando []');
        data = [];
      }
      
      console.log('Dashboard: Datos procesados:', data.length, 'registros');
      console.log('Dashboard: Primeros 2:', data.slice(0, 2));

      // Calcular estadísticas
      const totalImports = data.length;
      const totalPolicies = data.reduce((sum, item) => sum + (item.filas_insertadas || 0), 0);
      const totalErrors = data.reduce((sum, item) => sum + (item.filas_erroneas || 0), 0);
      const successRate = totalPolicies + totalErrors > 0 
        ? Math.round((totalPolicies / (totalPolicies + totalErrors)) * 100)
        : 0;
      const lastImport = data.length > 0 
        ? new Date(data[0].fecha_carga).toLocaleString()
        : 'Nunca';

      setStats({
        totalImports,
        totalPolicies,
        successRate,
        lastImport,
      });

      setHistorial(data.slice(0, 10)); // Mostrar últimas 10 importaciones
      console.log('Dashboard: Stats calculadas:', { totalImports, totalPolicies, successRate });
    } catch (err) {
      console.error('Dashboard: Error al cargar:', err);
      console.error('Dashboard: Detalles del error:', err.response?.data);
    } finally {
      setLoading(false);
    }
  };

  // PASO 10: Cargar estadísticas de alertas
  const cargarEstadisticasAlertas = async () => {
    try {
      const res = await api.get('/alertas/estadisticas/');
      setAlertasStats({
        totales: res.data.total || 0,
        pendientes: res.data.pendientes || 0,
        criticas: res.data.criticas || 0,
      });
    } catch (err) {
      console.error('Error al cargar estadísticas de alertas:', err);
    }
  };

  // PASO 10: Actualizar alertas de pólizas vencidas y por expirar
  const actualizarAlertasPolizas = async () => {
    try {
      setEjecutandoAlertas(true);
      const res = await api.post('/alertas/run/');
      
      // Mostrar notificación exitosa
      setNotificacion({
        tipo: 'success',
        mensaje: `✅ Alertas actualizadas - ${res.data.reportes.polizas_vencidas} vencidas, ${res.data.reportes.polizas_por_expirar} por expirar`,
      });
      
      // Recargar estadísticas de alertas
      await cargarEstadisticasAlertas();
      
      // Limpiar notificación después de 5 segundos
      setTimeout(() => setNotificacion(null), 5000);
    } catch (err) {
      console.error('Error al ejecutar reglas de alertas:', err);
      setNotificacion({
        tipo: 'error',
        mensaje: '❌ Error al actualizar alertas',
      });
      setTimeout(() => setNotificacion(null), 5000);
    } finally {
      setEjecutandoAlertas(false);
    }
  };

  const StatCard = ({ title, value, color, bgGradient, icon }) => (
    <div className={`relative overflow-hidden rounded-xl shadow-lg hover:shadow-2xl transition-all duration-300 transform hover:scale-105 p-6 ${bgGradient}`}>
      <div className="absolute top-0 right-0 opacity-100 text-5xl z-0">{icon}</div>
      <p className="relative z-10 text-white text-sm font-semibold opacity-90">{title}</p>
      <p className="relative z-10 text-4xl font-bold text-white mt-3">{value}</p>
      <div className={`relative z-10 h-1 w-12 ${color} rounded-full mt-4`}></div>
    </div>
  );

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-100">
      {/* Header Hero */}
      <div className="bg-gradient-to-r from-blue-600 via-blue-700 to-indigo-800 text-white py-12 px-6 shadow-lg">
        <div className="max-w-7xl mx-auto flex justify-between items-center">
          <div>
            <h1 className="text-5xl font-bold mb-2">Importaciones recientes</h1>
            <p className="text-blue-100 text-lg">Monitorea el estado de tus cargas de pólizas</p>
          </div>
          {/* PASO 10: Botón Actualizar Alertas de Pólizas */}
          <div className="flex flex-col items-end gap-2">
            <button
              onClick={actualizarAlertasPolizas}
              disabled={ejecutandoAlertas}
              className={`px-6 py-3 rounded-lg font-semibold transition-all duration-300 flex items-center gap-2 ${
                ejecutandoAlertas
                  ? 'bg-gray-400 cursor-not-allowed'
                  : 'bg-yellow-400 hover:bg-yellow-500 text-gray-900 hover:shadow-lg transform hover:scale-105'
              }`}
            >
              {ejecutandoAlertas ? (
                <>
                  <span className="animate-spin">⚙️</span>
                  Procesando...
                </>
              ) : (
                <>
                  🔔 Actualizar Alertas
                </>
              )}
            </button>
            {alertasStats.criticas > 0 && (
              <span className="text-red-300 text-sm font-bold">
                ⚠️ {alertasStats.criticas} alerta(s) crítica(s)
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Notificación */}
      {notificacion && (
        <div className={`fixed top-4 right-4 p-4 rounded-lg shadow-lg text-white z-50 ${
          notificacion.tipo === 'success' ? 'bg-green-500' : 'bg-red-500'
        }`}>
          {notificacion.mensaje}
        </div>
      )}

      <div className="p-6 max-w-7xl mx-auto">
        {/* Stats Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-6 gap-6 mb-10 mt-8">
          <StatCard 
            title="Total Importaciones" 
            value={stats.totalImports} 
            color="bg-blue-400"
            bgGradient="bg-gradient-to-br from-blue-500 to-blue-700"
            icon="📊"
          />
          <StatCard 
            title="Pólizas Procesadas" 
            value={stats.totalPolicies} 
            color="bg-green-400"
            bgGradient="bg-gradient-to-br from-green-500 to-green-700"
            icon="✓"
          />
          <StatCard 
            title="Tasa de Éxito" 
            value={`${stats.successRate}%`} 
            color="bg-orange-400"
            bgGradient="bg-gradient-to-br from-orange-500 to-orange-700"
            icon="🎯"
          />
          <StatCard 
            title="Última Importación" 
            value={stats.lastImport.split(' ')[0]} 
            color="bg-purple-400"
            bgGradient="bg-gradient-to-br from-purple-500 to-purple-700"
            icon="⏰"
          />
          {/* PASO 10: Tarjeta de total alertas */}
          <StatCard 
            title="Total de Alertas" 
            value={alertasStats.totales} 
            color="bg-indigo-400"
            bgGradient="bg-gradient-to-br from-indigo-500 to-indigo-700"
            icon="🔔"
          />
          {/* PASO 10: Tarjeta de alertas pendientes */}
          <StatCard 
            title="Alertas Pendientes" 
            value={alertasStats.pendientes} 
            color={alertasStats.criticas > 0 ? "bg-red-400" : "bg-yellow-400"}
            bgGradient={alertasStats.criticas > 0 ? "bg-gradient-to-br from-red-500 to-red-700" : "bg-gradient-to-br from-yellow-500 to-yellow-700"}
            icon={alertasStats.criticas > 0 ? "🔴" : "🟡"}
          />
        </div>

        {/* Historial Table */}
        <div className="bg-white rounded-xl shadow-lg overflow-hidden">
          <div className="bg-gradient-to-r from-slate-100 to-slate-50 p-6 border-b border-slate-200">
            <h2 className="text-2xl font-bold text-slate-800">Historial Reciente</h2>
            <p className="text-slate-600 text-sm mt-1">Últimas 10 importaciones</p>
          </div>

          {loading ? (
          <div className="p-6 text-center text-gray-500">Cargando...</div>
        ) : historial.length === 0 ? (
          <div className="p-6 text-center text-gray-500">No hay importaciones registradas</div>
        ) : (
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
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
      </div>
    </div>
  );
}
