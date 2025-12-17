import { useState, useEffect } from 'react';
import {
  BrowserRouter,
  Routes,
  Route,
  Navigate,
  Link,
  useLocation,
  useNavigate,
} from 'react-router-dom';
import UploadExcel from './pages/UploadExcel';
import HistorialImportaciones from './pages/HistorialImportaciones';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import Analytics from './pages/Analytics';
import Reportes from './pages/Reportes';
import Cobranzas from './pages/Cobranzas';
import Alertas from './pages/Alertas';
import AdminPanel from './pages/AdminPanel';
import Auditorias from './pages/Auditorias';
import { authService, apiClient } from './services/api';

/**
 * Componente para proteger rutas basado en roles
 */
function RoleBasedRoute({ children, allowedRoles }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    const fetchUser = async () => {
      try {
        const response = await apiClient.get('/usuarios/me/');
        const userData = response.data;
        setUser(userData);
        if (!allowedRoles.includes(userData.role)) {
          navigate('/dashboard', { replace: true });
        }
      } catch (err) {
        console.error('Error fetching user:', err);
        navigate('/login', { replace: true });
      } finally {
        setLoading(false);
      }
    };

    if (!authService.isAuthenticated()) {
      navigate('/login', { replace: true });
    } else {
      fetchUser();
    }
  }, [allowedRoles, navigate]);

  if (loading) {
    return <div className="flex justify-center items-center h-screen">Cargando...</div>;
  }

  if (!user || !allowedRoles.includes(user.role)) {
    return <Navigate to="/dashboard" replace />;
  }

  return children;
}

function Navigation() {
  const location = useLocation();
  const navigate = useNavigate();
  const [menuAbierto, setMenuAbierto] = useState(null);
  const [user, setUser] = useState(null);

  useEffect(() => {
    const fetchUser = async () => {
      try {
        const response = await apiClient.get('/usuarios/me/');
        setUser(response.data);
      } catch (err) {
        console.error('Error fetching user:', err);
      }
    };

    if (authService.isAuthenticated()) {
      fetchUser();
    }
  }, []);

  const handleLogout = () => {
    authService.logout();
    navigate('/login', { replace: true });
  };

  const toggleMenu = (menu) => {
    setMenuAbierto(menuAbierto === menu ? null : menu);
  };

  if (!authService.isAuthenticated()) {
    return null;
  }

  const getRoleDisplay = (role) => {
    const roleMap = {
      'admin': 'Administrador',
      'comercial': 'Usuario Comercial',
      'auditor': 'Auditor / Viewer'
    };
    return roleMap[role] || role;
  };

  const MenuItem = ({ label, submenu, requiredRoles }) => {
    // Ocultar menú si usuario no tiene rol requerido
    if (requiredRoles && user && !requiredRoles.includes(user.role)) {
      return null;
    }

    const isActive = submenu.some(item => location.pathname === item.path);
    const isOpen = menuAbierto === label;

    return (
      <div className="relative group">
        <button
          onClick={() => toggleMenu(label)}
          className={`${
            isActive
              ? 'border-blue-500 text-gray-900'
              : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'
          } inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium gap-1`}
        >
          {label}
          <span className="text-xs">{isOpen ? '▲' : '▼'}</span>
        </button>
        {isOpen && (
          <div className="absolute left-0 mt-0 w-48 bg-white border border-gray-300 shadow-lg z-50">
            {submenu.map((item) => (
              <Link
                key={item.path}
                to={item.path}
                className={`${
                  location.pathname === item.path
                    ? 'bg-blue-50 text-blue-700'
                    : 'text-gray-700 hover:bg-gray-100'
                } block px-4 py-2 text-sm`}
                onClick={() => setMenuAbierto(null)}
              >
                {item.label}
              </Link>
            ))}
          </div>
        )}
      </div>
    );
  };

  return (
    <nav className="bg-white shadow-sm border-b border-gray-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          <div className="flex items-center gap-8">
            <Link to="/" className="font-bold text-lg text-blue-600">
              SIGEPOL
            </Link>
            <div className="hidden md:flex space-x-1">
              {/* Dashboard */}
              <Link
                to="/dashboard"
                className={`${
                  location.pathname === '/dashboard'
                    ? 'border-blue-500 text-gray-900'
                    : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'
                } inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium`}
              >
                Dashboard
              </Link>

              {/* Cobranzas - Todos */}
              <MenuItem
                label="Cobranzas"
                submenu={[
                  { label: 'Gestionar', path: '/cobranzas' },
                  { label: 'Alertas', path: '/alertas' },
                ]}
              />

              {/* Reportes */}
              <Link
                to="/reportes"
                className={`${
                  location.pathname === '/reportes'
                    ? 'border-blue-500 text-gray-900'
                    : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'
                } inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium`}
              >
                Reportes
              </Link>

              {/* Analytics - Admin, Comercial y Auditor */}
              {user && ['admin', 'comercial', 'auditor'].includes(user.role) && (
                <Link
                  to="/analytics"
                  className={`${
                    location.pathname === '/analytics'
                      ? 'border-blue-500 text-gray-900'
                      : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'
                  } inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium`}
                >
                  Analytics
                </Link>
              )}

              {/* Auditorías - Admin y Auditor */}
              {user && ['admin', 'auditor'].includes(user.role) && (
                <Link
                  to="/auditorias"
                  className={`${
                    location.pathname === '/auditorias'
                      ? 'border-blue-500 text-gray-900'
                      : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'
                  } inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium`}
                >
                  🔐 Auditorías
                </Link>
              )}

              {/* Importaciones - Admin, Comercial y Auditor (Auditor solo ve historial) */}
              {user && ['admin', 'comercial', 'auditor'].includes(user.role) && (
                <MenuItem
                  label="Importaciones"
                  submenu={
                    user.role === 'auditor'
                      ? [{ label: 'Historial', path: '/historial-importaciones' }]
                      : [
                          { label: 'Subir', path: '/upload' },
                          { label: 'Historial', path: '/historial-importaciones' },
                        ]
                  }
                  requiredRoles={['admin', 'comercial', 'auditor']}
                />
              )}
            </div>
          </div>

          {/* User Info and Logout */}
          <div className="flex items-center gap-4">
            {user && user.role === 'admin' && (
              <Link
                to="/admin"
                className={`px-4 py-2 text-sm font-medium rounded-md transition ${
                  location.pathname === '/admin'
                    ? 'bg-yellow-600 text-white'
                    : 'bg-yellow-500 text-white hover:bg-yellow-600'
                }`}
              >
                ⚙️ Administración
              </Link>
            )}
            {user && (
              <div className="text-right">
                <div className="text-sm font-medium text-gray-900">{user.username}</div>
                <div className="text-xs text-gray-500">{getRoleDisplay(user.role)}</div>
              </div>
            )}
            <button
              onClick={handleLogout}
              className="px-4 py-2 text-sm font-medium text-white bg-red-600 hover:bg-red-700 rounded-md"
            >
              Salir
            </button>
          </div>
        </div>
      </div>
    </nav>
  );
}

import { Outlet } from 'react-router-dom';

function AppLayout() {
  return (
    <div className="min-h-screen bg-gray-50">
      <Navigation />
      <main className="py-8 container mx-auto">
        <Outlet />
      </main>
    </div>
  );
}

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        
        {/* Rutas Protegidas con Layout */}
        <Route element={<AppLayout />}>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<Dashboard />} />
          
          {/* Cobranzas */}
          <Route path="/cobranzas" element={<Cobranzas />} />
          <Route
            path="/alertas"
            element={
              <RoleBasedRoute allowedRoles={['admin', 'comercial']}>
                <Alertas />
              </RoleBasedRoute>
            }
          />
          
          {/* Reportes */}
          <Route path="/reportes" element={<Reportes />} />
          
          {/* Analytics */}
          <Route
            path="/analytics"
            element={
              <RoleBasedRoute allowedRoles={['admin', 'comercial', 'auditor']}>
                <Analytics />
              </RoleBasedRoute>
            }
          />

          {/* Auditorías */}
          <Route
            path="/auditorias"
            element={
              <RoleBasedRoute allowedRoles={['admin', 'auditor']}>
                <Auditorias />
              </RoleBasedRoute>
            }
          />
          
          {/* Importaciones */}
          <Route
            path="/upload"
            element={
              <RoleBasedRoute allowedRoles={['admin', 'comercial']}>
                <UploadExcel />
              </RoleBasedRoute>
            }
          />
          <Route
            path="/historial-importaciones"
            element={
              <RoleBasedRoute allowedRoles={['admin', 'comercial', 'auditor']}>
                <HistorialImportaciones />
              </RoleBasedRoute>
            }
          />
          
          {/* Admin Panel */}
          <Route
            path="/admin"
            element={
              <RoleBasedRoute allowedRoles={['admin']}>
                <AdminPanel />
              </RoleBasedRoute>
            }
          />
          
          {/* Fallback a Dashboard */}
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
