import { useState, useEffect } from 'react';
import api from '../services/api';
import { useNavigate } from 'react-router-dom';

export default function Alertas() {
  const navigate = useNavigate();
  const [alertas, setAlertas] = useState([]);
  const [estadisticas, setEstadisticas] = useState(null);
  const [loading, setLoading] = useState(true);
  const [filtroCategoria, setFiltroCategoria] = useState('');
  const [filtroEstado, setFiltroEstado] = useState('');
  const [filtroPrioridad, setFiltroPrioridad] = useState('');
  const [busqueda, setBusqueda] = useState('');
  const [mostrarModal, setMostrarModal] = useState(false);
  const [alertaDetalle, setAlertaDetalle] = useState(null);

  useEffect(() => {
    cargarDatos();
  }, [filtroCategoria, filtroEstado, filtroPrioridad]);

  const cargarDatos = async () => {
    try {
      setLoading(true);
      
      // Construir URL con filtros
      let url = '/alertas/?';
      const params = [];
      if (filtroCategoria) params.push(`categoria=${filtroCategoria}`);
      if (filtroEstado) params.push(`estado=${filtroEstado}`);
      if (filtroPrioridad) params.push(`prioridad=${filtroPrioridad}`);
      url += params.join('&');
      
      const resAlertas = await api.get(url);
      // El backend devuelve {count, results: [...]}
      const alertasArray = resAlertas.data.results || resAlertas.data;
      setAlertas(Array.isArray(alertasArray) ? alertasArray : []);
      
      // Cargar estadísticas
      const resStats = await api.get('/alertas/estadisticas/');
      setEstadisticas(resStats.data);
    } catch (error) {
      console.error('Error al cargar alertas:', error);
      alert('Error al cargar datos');
    } finally {
      setLoading(false);
    }
  };

  const marcarComoLeida = async (id) => {
    try {
      await api.post(`/alertas/${id}/marcar_leida/`);
      cargarDatos();
    } catch (error) {
      console.error('Error:', error);
      alert('Error al marcar como leída');
    }
  };

  const marcarComoResuelta = async (id) => {
    try {
      await api.post(`/alertas/${id}/marcar_resuelta/`);
      alert('Alerta marcada como resuelta');
      cargarDatos();
    } catch (error) {
      console.error('Error:', error);
      alert('Error al marcar como resuelta');
    }
  };

  const descartarAlerta = async (id) => {
    if (!confirm('¿Estás seguro de descartar esta alerta?')) return;
    
    try {
      await api.post(`/alertas/${id}/descartar/`);
      alert('Alerta descartada');
      cargarDatos();
    } catch (error) {
      console.error('Error:', error);
      alert('Error al descartar alerta');
    }
  };

  const verDetalle = (alerta) => {
    setAlertaDetalle(alerta);
    setMostrarModal(true);
    if (alerta.estado === 'PENDIENTE') {
      marcarComoLeida(alerta.id);
    }
  };

  const alertasFiltradas = alertas.filter(alerta => {
    if (!busqueda) return true;
    const busq = busqueda.toLowerCase();
    return (
      alerta.titulo?.toLowerCase().includes(busq) ||
      alerta.mensaje?.toLowerCase().includes(busq) ||
      alerta.poliza_numero?.toLowerCase().includes(busq) ||
      alerta.cliente_nombre?.toLowerCase().includes(busq)
    );
  });

  const getPrioridadColor = (prioridad) => {
    const colors = {
      'BAJA': 'bg-gray-100 text-gray-800',
      'MEDIA': 'bg-blue-100 text-blue-800',
      'ALTA': 'bg-orange-100 text-orange-800',
      'CRITICA': 'bg-red-100 text-red-800'
    };
    return colors[prioridad] || 'bg-gray-100 text-gray-800';
  };

  const getEstadoColor = (estado) => {
    const colors = {
      'PENDIENTE': 'bg-yellow-100 text-yellow-800',
      'LEIDA': 'bg-blue-100 text-blue-800',
      'RESUELTA': 'bg-green-100 text-green-800',
      'DESCARTADA': 'bg-gray-100 text-gray-800'
    };
    return colors[estado] || 'bg-gray-100 text-gray-800';
  };

  const getCategoriaIcon = (categoria) => {
    const icons = {
      'VENCIMIENTOS': '⏰',
      'COBRANZAS': '💰',
      'IMPORTACIONES': '📥',
      'PRODUCCION': '🏭',
      'SISTEMA': '⚙️'
    };
    return icons[categoria] || '📌';
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-100">
      {/* Header */}
      <div className="bg-gradient-to-r from-blue-600 via-blue-700 to-indigo-800 text-white py-12 px-6 shadow-lg">
        <div className="max-w-7xl mx-auto">
          <h1 className="text-5xl font-bold mb-2">🔔 Centro de Alertas</h1>
          <p className="text-blue-100 text-lg">Gestión centralizada de notificaciones y alertas del sistema</p>
        </div>
      </div>

      <div className="p-6 max-w-7xl mx-auto">
        {/* Estadísticas */}
        {estadisticas && (
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 mb-8">
            <div className="bg-white rounded-lg shadow p-4">
              <p className="text-xs text-gray-600 font-semibold">Total</p>
              <p className="text-3xl font-bold text-gray-900">{estadisticas.total}</p>
            </div>
            <div className="bg-gradient-to-br from-yellow-500 to-yellow-600 rounded-lg shadow p-4 text-white">
              <p className="text-xs font-semibold opacity-90">Pendientes</p>
              <p className="text-3xl font-bold">{estadisticas.pendientes}</p>
            </div>
            <div className="bg-gradient-to-br from-blue-500 to-blue-600 rounded-lg shadow p-4 text-white">
              <p className="text-xs font-semibold opacity-90">Leídas</p>
              <p className="text-3xl font-bold">{estadisticas.leidas}</p>
            </div>
            <div className="bg-gradient-to-br from-green-500 to-green-600 rounded-lg shadow p-4 text-white">
              <p className="text-xs font-semibold opacity-90">Resueltas</p>
              <p className="text-3xl font-bold">{estadisticas.resueltas}</p>
            </div>
            <div className="bg-gradient-to-br from-red-500 to-red-600 rounded-lg shadow p-4 text-white">
              <p className="text-xs font-semibold opacity-90">Críticas</p>
              <p className="text-3xl font-bold">{estadisticas.criticas}</p>
            </div>
            <div className="bg-gradient-to-br from-purple-500 to-purple-600 rounded-lg shadow p-4 text-white">
              <p className="text-xs font-semibold opacity-90">Vencidas</p>
              <p className="text-3xl font-bold">{estadisticas.vencidas}</p>
            </div>
          </div>
        )}

        {/* Filtros */}
        <div className="bg-white rounded-xl shadow-lg p-6 mb-6">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-2">Categoría</label>
              <select
                value={filtroCategoria}
                onChange={(e) => setFiltroCategoria(e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              >
                <option value="">Todas</option>
                <option value="VENCIMIENTOS">Vencimientos</option>
                <option value="COBRANZAS">Cobranzas</option>
                <option value="IMPORTACIONES">Importaciones</option>
                <option value="PRODUCCION">Producción</option>
                <option value="SISTEMA">Sistema</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-2">Estado</label>
              <select
                value={filtroEstado}
                onChange={(e) => setFiltroEstado(e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              >
                <option value="">Todos</option>
                <option value="PENDIENTE">Pendiente</option>
                <option value="LEIDA">Leída</option>
                <option value="RESUELTA">Resuelta</option>
                <option value="DESCARTADA">Descartada</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-2">Prioridad</label>
              <select
                value={filtroPrioridad}
                onChange={(e) => setFiltroPrioridad(e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              >
                <option value="">Todas</option>
                <option value="BAJA">Baja</option>
                <option value="MEDIA">Media</option>
                <option value="ALTA">Alta</option>
                <option value="CRITICA">Crítica</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-2">Buscar</label>
              <input
                type="text"
                placeholder="Buscar alertas..."
                value={busqueda}
                onChange={(e) => setBusqueda(e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>
        </div>

        {/* Lista de Alertas */}
        <div className="space-y-4">
          {loading ? (
            <div className="bg-white rounded-xl shadow-lg p-8 text-center">
              <p className="text-gray-500">Cargando alertas...</p>
            </div>
          ) : alertasFiltradas.length === 0 ? (
            <div className="bg-white rounded-xl shadow-lg p-12 text-center">
              <p className="text-5xl mb-4">✅</p>
              <p className="text-xl font-semibold text-gray-700">No hay alertas</p>
              <p className="text-gray-500 mt-2">Todo está bajo control</p>
            </div>
          ) : (
            alertasFiltradas.map((alerta) => (
              <div
                key={alerta.id}
                className={`bg-white rounded-xl shadow-lg p-6 hover:shadow-xl transition-all border-l-4 ${
                  alerta.prioridad === 'CRITICA' ? 'border-red-500' :
                  alerta.prioridad === 'ALTA' ? 'border-orange-500' :
                  alerta.prioridad === 'MEDIA' ? 'border-blue-500' : 'border-gray-300'
                }`}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <span className="text-3xl">{getCategoriaIcon(alerta.categoria)}</span>
                      <div>
                        <h3 className="text-xl font-bold text-gray-900">{alerta.titulo}</h3>
                        <div className="flex gap-2 mt-1">
                          <span className={`px-2 py-1 rounded-full text-xs font-semibold ${getPrioridadColor(alerta.prioridad)}`}>
                            {alerta.prioridad}
                          </span>
                          <span className={`px-2 py-1 rounded-full text-xs font-semibold ${getEstadoColor(alerta.estado)}`}>
                            {alerta.estado}
                          </span>
                          <span className="px-2 py-1 bg-gray-100 rounded-full text-xs font-semibold text-gray-700">
                            {alerta.categoria}
                          </span>
                        </div>
                      </div>
                    </div>
                    
                    <p className="text-gray-700 mb-3">{alerta.mensaje}</p>
                    
                    <div className="flex gap-4 text-sm text-gray-600">
                      {alerta.poliza_numero && (
                        <span>📋 Póliza: <strong>{alerta.poliza_numero}</strong></span>
                      )}
                      {alerta.cliente_nombre && (
                        <span>👤 Cliente: <strong>{alerta.cliente_nombre}</strong></span>
                      )}
                      <span>📅 {new Date(alerta.fecha_creacion).toLocaleString()}</span>
                      {alerta.dias_pendiente > 0 && (
                        <span className="text-orange-600 font-semibold">
                          ⏱️ {alerta.dias_pendiente} días pendiente
                        </span>
                      )}
                    </div>
                  </div>
                  
                  <div className="flex gap-2 ml-4">
                    <button
                      onClick={() => verDetalle(alerta)}
                      className="px-3 py-1 bg-blue-600 text-white rounded hover:bg-blue-700 text-sm font-semibold"
                    >
                      Ver
                    </button>
                    {alerta.estado === 'PENDIENTE' && (
                      <button
                        onClick={() => marcarComoLeida(alerta.id)}
                        className="px-3 py-1 bg-gray-600 text-white rounded hover:bg-gray-700 text-sm font-semibold"
                      >
                        Marcar Leída
                      </button>
                    )}
                    {(alerta.estado === 'PENDIENTE' || alerta.estado === 'LEIDA') && (
                      <>
                        <button
                          onClick={() => marcarComoResuelta(alerta.id)}
                          className="px-3 py-1 bg-green-600 text-white rounded hover:bg-green-700 text-sm font-semibold"
                        >
                          Resolver
                        </button>
                        <button
                          onClick={() => descartarAlerta(alerta.id)}
                          className="px-3 py-1 bg-red-600 text-white rounded hover:bg-red-700 text-sm font-semibold"
                        >
                          Descartar
                        </button>
                      </>
                    )}
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Modal Detalle */}
      {mostrarModal && alertaDetalle && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6 border-b bg-gradient-to-r from-blue-600 to-indigo-700 text-white">
              <div className="flex items-center justify-between">
                <h3 className="text-2xl font-bold">Detalle de Alerta</h3>
                <button
                  onClick={() => setMostrarModal(false)}
                  className="text-white hover:text-gray-200 text-2xl"
                >
                  ×
                </button>
              </div>
            </div>
            
            <div className="p-6 space-y-4">
              <div className="flex items-center gap-4">
                <span className="text-5xl">{getCategoriaIcon(alertaDetalle.categoria)}</span>
                <div>
                  <h4 className="text-2xl font-bold text-gray-900">{alertaDetalle.titulo}</h4>
                  <div className="flex gap-2 mt-2">
                    <span className={`px-3 py-1 rounded-full text-sm font-semibold ${getPrioridadColor(alertaDetalle.prioridad)}`}>
                      {alertaDetalle.prioridad}
                    </span>
                    <span className={`px-3 py-1 rounded-full text-sm font-semibold ${getEstadoColor(alertaDetalle.estado)}`}>
                      {alertaDetalle.estado}
                    </span>
                  </div>
                </div>
              </div>
              
              <div className="bg-gray-50 p-4 rounded-lg">
                <p className="text-gray-800 leading-relaxed">{alertaDetalle.mensaje}</p>
              </div>
              
              {(alertaDetalle.poliza_numero || alertaDetalle.cliente_nombre) && (
                <div className="border-t pt-4">
                  <h5 className="font-semibold text-gray-900 mb-3">Información Relacionada</h5>
                  {alertaDetalle.poliza_numero && (
                    <div className="mb-2">
                      <span className="text-gray-600">Póliza:</span>
                      <span className="ml-2 font-semibold text-gray-900">{alertaDetalle.poliza_numero}</span>
                    </div>
                  )}
                  {alertaDetalle.cliente_nombre && (
                    <div className="mb-2">
                      <span className="text-gray-600">Cliente:</span>
                      <span className="ml-2 font-semibold text-gray-900">{alertaDetalle.cliente_nombre}</span>
                      {alertaDetalle.cliente_rut && (
                        <span className="ml-2 text-gray-500">({alertaDetalle.cliente_rut})</span>
                      )}
                    </div>
                  )}
                </div>
              )}
              
              <div className="border-t pt-4">
                <h5 className="font-semibold text-gray-900 mb-3">Información Temporal</h5>
                <div className="space-y-2 text-sm">
                  <div>
                    <span className="text-gray-600">Creada:</span>
                    <span className="ml-2 text-gray-900">{new Date(alertaDetalle.fecha_creacion).toLocaleString()}</span>
                  </div>
                  {alertaDetalle.fecha_lectura && (
                    <div>
                      <span className="text-gray-600">Leída:</span>
                      <span className="ml-2 text-gray-900">{new Date(alertaDetalle.fecha_lectura).toLocaleString()}</span>
                    </div>
                  )}
                  {alertaDetalle.fecha_resolucion && (
                    <div>
                      <span className="text-gray-600">Resuelta:</span>
                      <span className="ml-2 text-gray-900">{new Date(alertaDetalle.fecha_resolucion).toLocaleString()}</span>
                    </div>
                  )}
                  {alertaDetalle.fecha_limite && (
                    <div>
                      <span className="text-gray-600">Fecha límite:</span>
                      <span className={`ml-2 font-semibold ${alertaDetalle.esta_vencida ? 'text-red-600' : 'text-gray-900'}`}>
                        {new Date(alertaDetalle.fecha_limite).toLocaleString()}
                        {alertaDetalle.esta_vencida && ' (VENCIDA)'}
                      </span>
                    </div>
                  )}
                </div>
              </div>
              
              <div className="flex gap-3 pt-4">
                {(alertaDetalle.estado === 'PENDIENTE' || alertaDetalle.estado === 'LEIDA') && (
                  <button
                    onClick={() => {
                      marcarComoResuelta(alertaDetalle.id);
                      setMostrarModal(false);
                    }}
                    className="flex-1 bg-green-600 text-white py-3 rounded-lg font-semibold hover:bg-green-700"
                  >
                    Marcar como Resuelta
                  </button>
                )}
                <button
                  onClick={() => setMostrarModal(false)}
                  className="flex-1 bg-gray-300 text-gray-700 py-3 rounded-lg font-semibold hover:bg-gray-400"
                >
                  Cerrar
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
