import { useState, useEffect } from 'react';
import { apiClient } from '../services/api';

export default function AdminPanel() {
  const [usuarios, setUsuarios] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [editingUser, setEditingUser] = useState(null);
  const [newRole, setNewRole] = useState('');
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [createForm, setCreateForm] = useState({
    username: '',
    email: '',
    password: '',
    password2: '',
    first_name: '',
    role: 'comercial'
  });

  useEffect(() => {
    fetchUsuarios();
  }, []);

  const fetchUsuarios = async () => {
    try {
      setLoading(true);
      // Usar endpoint admin para obtener lista de usuarios
      const response = await apiClient.get('/usuarios/admin/');
      console.log('Response completo:', response.data);
      
      // DRF retorna respuesta paginada: { count, next, previous, results }
      let usuariosList = [];
      if (Array.isArray(response.data)) {
        usuariosList = response.data;
      } else if (response.data.results && Array.isArray(response.data.results)) {
        usuariosList = response.data.results;
      } else if (typeof response.data === 'object' && response.data.count !== undefined) {
        // Es un objeto paginado, usar results
        usuariosList = response.data.results || [];
      } else if (typeof response.data === 'object') {
        // Convertir object values a array
        const values = Object.values(response.data).filter(item => 
          typeof item === 'object' && item !== null && item.id !== undefined
        );
        usuariosList = values;
      }
      
      console.log('Usuarios procesados:', usuariosList);
      setUsuarios(usuariosList);
    } catch (err) {
      console.error('Error al cargar usuarios:', err);
      setError('Error al cargar usuarios: ' + (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  };

  const handleChangeRole = async (userId, role) => {
    try {
      // Usar endpoint admin change_role
      await apiClient.post(`/usuarios/admin/${userId}/change_role/`, { role });
      setEditingUser(null);
      fetchUsuarios();
      alert('Rol actualizado correctamente');
    } catch (err) {
      alert('Error al cambiar rol: ' + (err.response?.data?.detail || err.message));
    }
  };

  const handleToggleActive = async (userId, currentStatus) => {
    try {
      // Usar endpoint admin activate/deactivate
      const endpoint = currentStatus ? 'deactivate' : 'activate';
      await apiClient.post(`/usuarios/admin/${userId}/${endpoint}/`);
      fetchUsuarios();
      alert(`Usuario ${!currentStatus ? 'activado' : 'desactivado'}`);
    } catch (err) {
      alert('Error al cambiar estado del usuario');
    }
  };

  const handleCreateUser = async (e) => {
    e.preventDefault();
    try {
      if (!createForm.username || !createForm.email || !createForm.password) {
        alert('Por favor completa todos los campos requeridos');
        return;
      }
      
      if (createForm.password !== createForm.password2) {
        alert('Las contraseñas no coinciden');
        return;
      }
      
      await apiClient.post('/usuarios/admin/', {
        username: createForm.username,
        email: createForm.email,
        password: createForm.password,
        password2: createForm.password2,
        first_name: createForm.first_name,
        role: createForm.role
      });
      
      alert('✅ Usuario creado correctamente');
      setShowCreateForm(false);
      setCreateForm({
        username: '',
        email: '',
        password: '',
        password2: '',
        first_name: '',
        role: 'comercial'
      });
      fetchUsuarios();
    } catch (err) {
      console.error('Error:', err);
      alert('Error al crear usuario: ' + (err.response?.data?.detail || err.message));
    }
  };

  const handleCreateFormChange = (field, value) => {
    setCreateForm(prev => ({
      ...prev,
      [field]: value
    }));
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 to-slate-800 p-8">
      <div className="max-w-7xl mx-auto">
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-white mb-2">Panel de Administración</h1>
          <p className="text-slate-400">Gestión de usuarios y configuraciones del sistema</p>
        </div>

        {/* Estadísticas */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
            <h3 className="text-slate-400 text-sm font-medium">Total Usuarios</h3>
            <p className="text-4xl font-bold text-white mt-2">{usuarios.length}</p>
          </div>
          <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
            <h3 className="text-slate-400 text-sm font-medium">Activos</h3>
            <p className="text-4xl font-bold text-green-400 mt-2">
              {usuarios.filter(u => u.is_active).length}
            </p>
          </div>
          <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
            <h3 className="text-slate-400 text-sm font-medium">Inactivos</h3>
            <p className="text-4xl font-bold text-red-400 mt-2">
              {usuarios.filter(u => !u.is_active).length}
            </p>
          </div>
          <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
            <h3 className="text-slate-400 text-sm font-medium">Administradores</h3>
            <p className="text-4xl font-bold text-blue-400 mt-2">
              {usuarios.filter(u => u.role === 'admin').length}
            </p>
          </div>
        </div>

        {/* Botón para crear usuario */}
        <div className="mb-6 flex justify-end">
          <button
            onClick={() => setShowCreateForm(!showCreateForm)}
            className="px-6 py-3 bg-green-600 hover:bg-green-700 text-white font-semibold rounded-lg transition-colors flex items-center gap-2"
          >
            {showCreateForm ? '✕ Cancelar' : '➕ Crear Nuevo Usuario'}
          </button>
        </div>

        {/* Formulario de creación */}
        {showCreateForm && (
          <div className="bg-slate-800 rounded-lg border border-slate-700 p-6 mb-8">
            <h3 className="text-xl font-bold text-white mb-6">Crear Nuevo Usuario</h3>
            <form onSubmit={handleCreateUser} className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">Usuario</label>
                <input
                  type="text"
                  value={createForm.username}
                  onChange={(e) => handleCreateFormChange('username', e.target.value)}
                  placeholder="nombre_usuario"
                  className="w-full bg-slate-700 border border-slate-600 text-white px-4 py-2 rounded-lg focus:border-blue-500 focus:outline-none"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">Email</label>
                <input
                  type="email"
                  value={createForm.email}
                  onChange={(e) => handleCreateFormChange('email', e.target.value)}
                  placeholder="usuario@example.com"
                  className="w-full bg-slate-700 border border-slate-600 text-white px-4 py-2 rounded-lg focus:border-blue-500 focus:outline-none"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">Contraseña</label>
                <input
                  type="password"
                  value={createForm.password}
                  onChange={(e) => handleCreateFormChange('password', e.target.value)}
                  placeholder="••••••••"
                  className="w-full bg-slate-700 border border-slate-600 text-white px-4 py-2 rounded-lg focus:border-blue-500 focus:outline-none"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">Confirmar Contraseña</label>
                <input
                  type="password"
                  value={createForm.password2}
                  onChange={(e) => handleCreateFormChange('password2', e.target.value)}
                  placeholder="••••••••"
                  className="w-full bg-slate-700 border border-slate-600 text-white px-4 py-2 rounded-lg focus:border-blue-500 focus:outline-none"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">Nombre Completo</label>
                <input
                  type="text"
                  value={createForm.first_name}
                  onChange={(e) => handleCreateFormChange('first_name', e.target.value)}
                  placeholder="Juan Pérez"
                  className="w-full bg-slate-700 border border-slate-600 text-white px-4 py-2 rounded-lg focus:border-blue-500 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">Rol</label>
                <select
                  value={createForm.role}
                  onChange={(e) => handleCreateFormChange('role', e.target.value)}
                  className="w-full bg-slate-700 border border-slate-600 text-white px-4 py-2 rounded-lg focus:border-blue-500 focus:outline-none"
                >
                  <option value="comercial">Usuario Comercial</option>
                  <option value="auditor">Auditor</option>
                  <option value="admin">Administrador</option>
                </select>
              </div>

              <div className="flex gap-3 md:col-span-2">
                <button
                  type="submit"
                  className="flex-1 px-6 py-2 bg-green-600 hover:bg-green-700 text-white font-semibold rounded-lg transition-colors"
                >
                  ✓ Crear Usuario
                </button>
                <button
                  type="button"
                  onClick={() => setShowCreateForm(false)}
                  className="flex-1 px-6 py-2 bg-slate-700 hover:bg-slate-600 text-white font-semibold rounded-lg transition-colors"
                >
                  ✕ Cancelar
                </button>
              </div>
            </form>
          </div>
        )}

        {/* Tabla de Usuarios */}
        <div className="bg-slate-800 rounded-lg border border-slate-700 overflow-hidden">
          <div className="p-6 border-b border-slate-700">
            <h2 className="text-xl font-bold text-white">Usuarios del Sistema</h2>
          </div>

          {loading ? (
            <div className="p-12 text-center text-slate-400">Cargando usuarios...</div>
          ) : error ? (
            <div className="p-12 text-center text-red-400">{error}</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-slate-900">
                  <tr>
                    <th className="px-6 py-3 text-left text-sm font-semibold text-slate-300">Usuario</th>
                    <th className="px-6 py-3 text-left text-sm font-semibold text-slate-300">Email</th>
                    <th className="px-6 py-3 text-left text-sm font-semibold text-slate-300">Rol</th>
                    <th className="px-6 py-3 text-left text-sm font-semibold text-slate-300">Estado</th>
                    <th className="px-6 py-3 text-left text-sm font-semibold text-slate-300">Creado</th>
                    <th className="px-6 py-3 text-left text-sm font-semibold text-slate-300">Acciones</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-700">
                  {usuarios.map((user) => (
                    <tr key={user.id} className="hover:bg-slate-700/50 transition">
                      <td className="px-6 py-4">
                        <div>
                          <p className="font-medium text-white">{user.username}</p>
                          <p className="text-sm text-slate-400">{user.full_name}</p>
                        </div>
                      </td>
                      <td className="px-6 py-4 text-slate-300">{user.email}</td>
                      <td className="px-6 py-4">
                        {editingUser === user.id ? (
                          <select
                            value={newRole}
                            onChange={(e) => setNewRole(e.target.value)}
                            className="bg-slate-700 text-white px-2 py-1 rounded text-sm"
                          >
                            <option value="admin">Administrador</option>
                            <option value="comercial">Usuario Comercial</option>
                            <option value="auditor">Auditor</option>
                          </select>
                        ) : (
                          <span className="inline-block px-3 py-1 rounded-full text-sm font-medium bg-blue-900 text-blue-200">
                            {user.role_display}
                          </span>
                        )}
                      </td>
                      <td className="px-6 py-4">
                        <span
                          className={`inline-block px-3 py-1 rounded-full text-sm font-medium ${
                            user.is_active
                              ? 'bg-green-900 text-green-200'
                              : 'bg-red-900 text-red-200'
                          }`}
                        >
                          {user.is_active ? 'Activo' : 'Inactivo'}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-slate-400 text-sm">
                        {new Date(user.created_at).toLocaleDateString('es-ES')}
                      </td>
                      <td className="px-6 py-4">
                        <div className="flex gap-2">
                          {editingUser === user.id ? (
                            <>
                              <button
                                onClick={() => handleChangeRole(user.id, newRole)}
                                className="px-3 py-1 bg-green-600 hover:bg-green-700 text-white text-sm rounded transition"
                              >
                                Guardar
                              </button>
                              <button
                                onClick={() => setEditingUser(null)}
                                className="px-3 py-1 bg-slate-600 hover:bg-slate-700 text-white text-sm rounded transition"
                              >
                                Cancelar
                              </button>
                            </>
                          ) : (
                            <>
                              <button
                                onClick={() => {
                                  setEditingUser(user.id);
                                  setNewRole(user.role);
                                }}
                                className="px-3 py-1 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded transition"
                              >
                                Cambiar Rol
                              </button>
                              <button
                                onClick={() => handleToggleActive(user.id, user.is_active)}
                                className={`px-3 py-1 text-white text-sm rounded transition ${
                                  user.is_active
                                    ? 'bg-red-600 hover:bg-red-700'
                                    : 'bg-green-600 hover:bg-green-700'
                                }`}
                              >
                                {user.is_active ? 'Desactivar' : 'Activar'}
                              </button>
                            </>
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
    </div>
  );
}
