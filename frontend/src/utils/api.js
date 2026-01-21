import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API_BASE = `${BACKEND_URL}/api`;

const api = axios.create({
  baseURL: API_BASE,
  timeout: 30000, // 30 second timeout
});

// Add token to requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Track if we're already redirecting to prevent multiple redirects
let isRedirecting = false;

// Handle auth errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    // Only handle auth errors, not network errors
    if (error.response?.status === 401) {
      // Check if this is a token expiry or invalid token error
      const errorDetail = error.response?.data?.detail || '';
      const isAuthError = 
        errorDetail.includes('Token has expired') ||
        errorDetail.includes('Invalid token') ||
        errorDetail.includes('User not found') ||
        errorDetail.includes('Not authenticated');
      
      if (isAuthError && !isRedirecting) {
        isRedirecting = true;
        localStorage.removeItem('token');
        localStorage.removeItem('user');
        // Use replace to prevent back button issues
        window.location.replace('/login');
      }
    }
    
    // For 403 (paused account), redirect to login
    if (error.response?.status === 403) {
      const errorDetail = error.response?.data?.detail || '';
      if (errorDetail.includes('Account is paused') && !isRedirecting) {
        isRedirecting = true;
        localStorage.removeItem('token');
        localStorage.removeItem('user');
        window.location.replace('/login');
      }
    }
    
    return Promise.reject(error);
  }
);

export default api;