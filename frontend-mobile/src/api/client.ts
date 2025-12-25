import axios from 'axios';

// Create Axios Instance
export const apiClient = axios.create({
    baseURL: '/api', // Nginx proxy will handle routing to /api/baostock, /api/akshare, etc.
    timeout: 30000,
    headers: {
        'Content-Type': 'application/json',
    },
});

// Request Interceptor
apiClient.interceptors.request.use(
    (config) => {
        // Check if we need to route to a specific service
        // In our Nginx config:
        // /api/baostock/ -> http://baostock-api:8000/api/v1/
        // /api/akshare/  -> http://akshare-api:8000/api/v1/
        // /api/wencai/   -> http://pywencai-api:8000/api/v1/

        // We expect the caller to pass the full path starting with /baostock, /akshare, or /wencai
        return config;
    },
    (error) => {
        return Promise.reject(error);
    }
);

// Response Interceptor
apiClient.interceptors.response.use(
    (response) => {
        return response.data;
    },
    (error) => {
        // Standard error handling
        if (error.response) {
            console.error('API Error:', error.response.data);
        } else {
            console.error('Network Error:', error.message);
        }
        return Promise.reject(error);
    }
);
