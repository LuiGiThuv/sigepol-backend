import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000/api';

const tokenStorage = {
  getAccess: () => localStorage.getItem('access_token'),
  getRefresh: () => localStorage.getItem('refresh_token'),
  setTokens: ({ access, refresh }) => {
    if (access) localStorage.setItem('access_token', access);
    if (refresh) localStorage.setItem('refresh_token', refresh);
  },
  clear: () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
  },
};

// Configuración base de axios
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Interceptor para agregar el token de autenticación
api.interceptors.request.use(
  (config) => {
    const token = tokenStorage.getAccess();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Interceptor para manejar errores de respuesta
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    // Si el token expiró (401) y no hemos intentado refrescarlo
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      try {
        const refreshToken = tokenStorage.getRefresh();
        if (refreshToken) {
          const response = await axios.post(
            `${API_BASE_URL}/usuarios/token/refresh/`,
            { refresh: refreshToken }
          );
          const { access } = response.data;
          tokenStorage.setTokens({ access });
          originalRequest.headers.Authorization = `Bearer ${access}`;
          return api(originalRequest);
        }
      } catch (refreshError) {
        // Si el refresh falla, redirigir al login
        tokenStorage.clear();
        window.location.href = '/login';
        return Promise.reject(refreshError);
      }
    }

    return Promise.reject(error);
  }
);

export const authService = {
  isAuthenticated: () => Boolean(tokenStorage.getAccess()),
  login: async (username, password) => {
    const response = await api.post('/usuarios/token/', { username, password });
    tokenStorage.setTokens(response.data);
    return response.data;
  },
  logout: () => {
    tokenStorage.clear();
  },
};

export const apiClient = api;

export default api;

