import { useState, useEffect } from 'react';
import api from '../services/api';

export default function Cobranzas() {
  const [cobranzas, setCobranzas] = useState([]);
  const [estadisticas, setEstadisticas] = useState(null);
  const [loading, setLoading] = useState(true);
  const [filtroEstado, setFiltroEstado] = useState('');
  const [busqueda, setBusqueda] = useState('');
  const [mostrarModal, setMostrarModal] = useState(false);
  const [cobranzaSeleccionada, setCobranzaSeleccionada] = useState(null);
  const [formPago, setFormPago] = useState({
    fecha_pago: new Date().toISOString().split('T')[0],
    metodo_pago: '',
    numero_documento: '',
    valor_uf: '',
    observaciones: ''
  });

  useEffect(() => {
    // Verificar autenticación antes de cargar
    if (!localStorage.getItem('access_token')) {
      console.warn('⚠️ No hay token de autenticación. Redirigiendo a login...');
      window.location.href = '/login';
      return;
    }
    cargarDatos();
  }, [filtroEstado]);

  const cargarDatos = async () => {
    try {
      setLoading(true);
      
      // Cargar cobranzas con filtro de estado si aplica
      const params = {};
      if (filtroEstado) {
        params.estado = filtroEstado;
      }
      const resCob = await api.get('/cobranzas/', { params });
      console.log('Cobranzas recibidas:', resCob.data);
      
      // El backend devuelve {count, results: [...]}
      // Extraer solo el array de results
      const cobranzasArray = resCob.data.results || resCob.data;
      setCobranzas(Array.isArray(cobranzasArray) ? cobranzasArray : []);
      
      // Cargar estadísticas
      const resStats = await api.get('/cobranzas/estadisticas/');
      setEstadisticas(resStats.data);
    } catch (error) {
      console.error('Error al cargar cobranzas:', error);
      alert('Error al cargar datos');
    } finally {
      setLoading(false);
    }
  };

  const abrirModalPago = (cobranza) => {
    setCobranzaSeleccionada(cobranza);
    setFormPago({
      fecha_pago: new Date().toISOString().split('T')[0],
      metodo_pago: '',
      numero_documento: '',
      valor_uf: '',
      observaciones: ''
    });
    setMostrarModal(true);
  };

  const registrarPago = async (e) => {
    e.preventDefault();
    try {
      await api.post(`/cobranzas/${cobranzaSeleccionada.id}/registrar_pago/`, formPago);
      alert('Pago registrado exitosamente');
      setMostrarModal(false);
      cargarDatos();
    } catch (error) {
      console.error('Error al registrar pago:', error);
      alert('Error al registrar pago: ' + (error.response?.data?.error || error.message));
    }
  };

  const cancelarCobranza = async (id, motivo) => {
    if (!motivo) {
      motivo = prompt('Ingrese el motivo de cancelación:');
      if (!motivo) return;
    }
    
    try {
      await api.post(`/cobranzas/${id}/cancelar/`, { motivo });
      alert('Cobranza cancelada');
      cargarDatos();
    } catch (error) {
      console.error('Error al cancelar:', error);
      alert('Error al cancelar: ' + (error.response?.data?.error || error.message));
    }
  };

  const cobranzasFiltradas = cobranzas.filter(cob => {
    if (!busqueda) return true;
    const busq = busqueda.toLowerCase();
    return (
      cob.poliza_numero?.toLowerCase().includes(busq) ||
      cob.cliente_nombre?.toLowerCase().includes(busq) ||
      cob.cliente_rut?.toLowerCase().includes(busq)
    );
  });

  const getEstadoBadge = (estado) => {
    const badges = {
      'PENDIENTE': 'bg-yellow-100 text-yellow-800',
      'EN_PROCESO': 'bg-blue-100 text-blue-800',
      'PAGADA': 'bg-green-100 text-green-800',
      'VENCIDA': 'bg-red-100 text-red-800',
      'CANCELADA': 'bg-gray-100 text-gray-800'
    };
    return badges[estado] || 'bg-gray-100 text-gray-800';
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-100">
      {/* Header */}
      <div className="bg-gradient-to-r from-blue-600 via-blue-700 to-indigo-800 text-white py-12 px-6 shadow-lg">
        <div className="max-w-7xl mx-auto">
          <h1 className="text-5xl font-bold mb-2">💰 Gestión de Cobranzas</h1>
          <p className="text-blue-100 text-lg">Control de pagos y cobranzas de pólizas</p>
        </div>
      </div>

      <div className="p-6 max-w-7xl mx-auto">
        {/* Estadísticas */}
        {estadisticas && (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
            <div className="bg-gradient-to-br from-blue-500 to-blue-700 rounded-xl shadow-lg p-6 text-white">
              <p className="text-sm font-semibold opacity-90">Total Cobranzas</p>
              <p className="text-4xl font-bold mt-2">{estadisticas.total_cobranzas}</p>
            </div>
            <div className="bg-gradient-to-br from-yellow-500 to-yellow-700 rounded-xl shadow-lg p-6 text-white">
              <p className="text-sm font-semibold opacity-90">Pendientes</p>
              <p className="text-4xl font-bold mt-2">{estadisticas.pendientes}</p>
              <p className="text-xs mt-2 opacity-80">{estadisticas.monto_pendiente_uf.toFixed(2)} UF</p>
            </div>
            <div className="bg-gradient-to-br from-green-500 to-green-700 rounded-xl shadow-lg p-6 text-white">
              <p className="text-sm font-semibold opacity-90">Pagadas</p>
              <p className="text-4xl font-bold mt-2">{estadisticas.pagadas}</p>
              <p className="text-xs mt-2 opacity-80">{estadisticas.monto_pagado_uf.toFixed(2)} UF</p>
            </div>
            <div className="bg-gradient-to-br from-red-500 to-red-700 rounded-xl shadow-lg p-6 text-white">
              <p className="text-sm font-semibold opacity-90">Vencidas</p>
              <p className="text-4xl font-bold mt-2">{estadisticas.vencidas}</p>
              <p className="text-xs mt-2 opacity-80">Tasa Cobro: {estadisticas.tasa_cobro}%</p>
            </div>
          </div>
        )}

        {/* Filtros */}
        <div className="bg-white rounded-xl shadow-lg p-6 mb-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-2">Filtrar por Estado</label>
              <select
                value={filtroEstado}
                onChange={(e) => setFiltroEstado(e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              >
                <option value="">Todos los estados</option>
                <option value="PENDIENTE">Pendiente</option>
                <option value="EN_PROCESO">En Proceso</option>
                <option value="PAGADA">Pagada</option>
                <option value="VENCIDA">Vencida</option>
                <option value="CANCELADA">Cancelada</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-2">Buscar</label>
              <input
                type="text"
                placeholder="Buscar por póliza, cliente o RUT..."
                value={busqueda}
                onChange={(e) => setBusqueda(e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>
        </div>

        {/* Tabla de Cobranzas */}
        <div className="bg-white rounded-xl shadow-lg overflow-hidden">
          <div className="bg-gradient-to-r from-slate-100 to-slate-50 p-6 border-b">
            <h2 className="text-2xl font-bold text-slate-800">Listado de Cobranzas</h2>
            <p className="text-sm text-slate-600 mt-1">
              {cobranzasFiltradas.length} cobranzas encontradas
              {filtroEstado && ` (filtradas por: ${filtroEstado})`}
              {busqueda && ` (búsqueda: "${busqueda}")`}
            </p>
          </div>

          {loading ? (
            <div className="p-8 text-center text-gray-500">Cargando...</div>
          ) : cobranzasFiltradas.length === 0 ? (
            <div className="p-8 text-center text-gray-500">No hay cobranzas registradas</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gradient-to-r from-slate-100 to-slate-50">
                  <tr>
                    <th className="px-6 py-4 text-left text-sm font-semibold text-slate-700">ID</th>
                    <th className="px-6 py-4 text-left text-sm font-semibold text-slate-700">Póliza</th>
                    <th className="px-6 py-4 text-left text-sm font-semibold text-slate-700">Cliente</th>
                    <th className="px-6 py-4 text-left text-sm font-semibold text-slate-700">Monto UF</th>
                    <th className="px-6 py-4 text-left text-sm font-semibold text-slate-700">F. Emisión</th>
                    <th className="px-6 py-4 text-left text-sm font-semibold text-slate-700">F. Vencimiento</th>
                    <th className="px-6 py-4 text-left text-sm font-semibold text-slate-700">Días</th>
                    <th className="px-6 py-4 text-left text-sm font-semibold text-slate-700">Estado</th>
                    <th className="px-6 py-4 text-left text-sm font-semibold text-slate-700">Acciones</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200">
                  {cobranzasFiltradas.map((cob) => (
                    <tr key={cob.id} className="hover:bg-slate-50 transition-colors">
                      <td className="px-6 py-4 text-sm text-gray-900">{cob.id}</td>
                      <td className="px-6 py-4 text-sm font-medium text-gray-900">{cob.poliza_numero}</td>
                      <td className="px-6 py-4 text-sm text-gray-700">
                        <div>{cob.cliente_nombre}</div>
                        <div className="text-xs text-gray-500">{cob.cliente_rut}</div>
                      </td>
                      <td className="px-6 py-4 text-sm font-semibold text-gray-900">{parseFloat(cob.monto_uf).toFixed(2)}</td>
                      <td className="px-6 py-4 text-sm text-gray-700">{new Date(cob.fecha_emision).toLocaleDateString()}</td>
                      <td className="px-6 py-4 text-sm text-gray-700">{new Date(cob.fecha_vencimiento).toLocaleDateString()}</td>
                      <td className="px-6 py-4 text-sm">
                        <span className={`font-semibold ${cob.dias_vencimiento < 0 ? 'text-red-600' : cob.dias_vencimiento <= 7 ? 'text-yellow-600' : 'text-green-600'}`}>
                          {cob.dias_vencimiento > 0 ? `${cob.dias_vencimiento}d` : cob.dias_vencimiento < 0 ? `${Math.abs(cob.dias_vencimiento)}d vencido` : 'Hoy'}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-sm">
                        <span className={`px-3 py-1 rounded-full text-xs font-semibold ${getEstadoBadge(cob.estado)}`}>
                          {cob.estado.replace('_', ' ')}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-sm">
                        <div className="flex gap-2">
                          {cob.estado === 'PENDIENTE' && (
                            <>
                              <button
                                onClick={() => abrirModalPago(cob)}
                                className="px-3 py-1 bg-green-600 text-white rounded hover:bg-green-700 text-xs font-semibold"
                              >
                                Pagar
                              </button>
                              <button
                                onClick={() => cancelarCobranza(cob.id)}
                                className="px-3 py-1 bg-red-600 text-white rounded hover:bg-red-700 text-xs font-semibold"
                              >
                                Cancelar
                              </button>
                            </>
                          )}
                          {cob.estado === 'PAGADA' && cob.fecha_pago && (
                            <span className="text-xs text-gray-600">
                              Pagado: {new Date(cob.fecha_pago).toLocaleDateString()}
                            </span>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {/* Modal Registrar Pago */}
      {mostrarModal && cobranzaSeleccionada && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-2xl p-8 max-w-md w-full mx-4">
            <h3 className="text-2xl font-bold mb-4 text-gray-800">Registrar Pago</h3>
            <div className="mb-4 p-4 bg-blue-50 rounded-lg">
              <p className="text-sm text-gray-700"><strong>Póliza:</strong> {cobranzaSeleccionada.poliza_numero}</p>
              <p className="text-sm text-gray-700"><strong>Cliente:</strong> {cobranzaSeleccionada.cliente_nombre}</p>
              <p className="text-sm text-gray-700"><strong>Monto:</strong> {parseFloat(cobranzaSeleccionada.monto_uf).toFixed(2)} UF</p>
            </div>
            
            <form onSubmit={registrarPago} className="space-y-4">
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-2">Fecha de Pago</label>
                <input
                  type="date"
                  value={formPago.fecha_pago}
                  onChange={(e) => setFormPago({...formPago, fecha_pago: e.target.value})}
                  className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                  required
                />
              </div>
              
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-2">Método de Pago</label>
                <select
                  value={formPago.metodo_pago}
                  onChange={(e) => setFormPago({...formPago, metodo_pago: e.target.value})}
                  className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                  required
                >
                  <option value="">Seleccione...</option>
                  <option value="TRANSFERENCIA">Transferencia Bancaria</option>
                  <option value="CHEQUE">Cheque</option>
                  <option value="EFECTIVO">Efectivo</option>
                  <option value="TARJETA">Tarjeta</option>
                  <option value="DEBITO_AUTOMATICO">Débito Automático</option>
                </select>
              </div>
              
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-2">Valor UF (opcional)</label>
                <input
                  type="number"
                  step="0.01"
                  placeholder="Ej: 38000.50"
                  value={formPago.valor_uf}
                  onChange={(e) => setFormPago({...formPago, valor_uf: e.target.value})}
                  className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                />
              </div>
              
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-2">N° Documento</label>
                <input
                  type="text"
                  placeholder="N° transferencia, cheque, etc."
                  value={formPago.numero_documento}
                  onChange={(e) => setFormPago({...formPago, numero_documento: e.target.value})}
                  className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                />
              </div>
              
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-2">Observaciones</label>
                <textarea
                  value={formPago.observaciones}
                  onChange={(e) => setFormPago({...formPago, observaciones: e.target.value})}
                  className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                  rows="3"
                />
              </div>
              
              <div className="flex gap-3 pt-4">
                <button
                  type="submit"
                  className="flex-1 bg-green-600 text-white py-3 rounded-lg font-semibold hover:bg-green-700 transition-all"
                >
                  Confirmar Pago
                </button>
                <button
                  type="button"
                  onClick={() => setMostrarModal(false)}
                  className="flex-1 bg-gray-300 text-gray-700 py-3 rounded-lg font-semibold hover:bg-gray-400 transition-all"
                >
                  Cancelar
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
