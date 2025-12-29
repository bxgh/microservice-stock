import Taro from '@tarojs/taro';

// Base URL for the existing microservices
export const API_BASE_URL = 'https://wxalwaysup.online/api/v1';

// Generic request wrapper using Taro's native request API
const request = async <T = any>(options: {
    url: string;
    method?: 'GET' | 'POST' | 'PUT' | 'DELETE';
    data?: any;
    header?: Record<string, string>;
}): Promise<T> => {
    const { url, method = 'GET', data, header = {} } = options;

    try {
        const response = await Taro.request({
            url: `${API_BASE_URL}${url}`,
            method,
            data,
            header: {
                'Content-Type': 'application/json',
                'X-Client-Platform': 'wechat-miniprogram',
                ...header,
            },
            timeout: 10000,
        });

        if (response.statusCode >= 200 && response.statusCode < 300) {
            return response.data as T;
        } else {
            throw new Error(`Request failed with status ${response.statusCode}`);
        }
    } catch (error: any) {
        const message = error.data?.error?.message || error.errMsg || 'Network Error';

        console.error('API Error:', message);

        Taro.showToast({
            title: message.length > 15 ? '请求失败' : message,
            icon: 'none',
            duration: 2000,
        });

        throw error;
    }
};

// Export convenience methods
const client = {
    get: <T = any>(url: string, params?: any) =>
        request<T>({ url: params ? `${url}?${new URLSearchParams(params).toString()}` : url, method: 'GET' }),

    post: <T = any>(url: string, data?: any) =>
        request<T>({ url, method: 'POST', data }),

    put: <T = any>(url: string, data?: any) =>
        request<T>({ url, method: 'PUT', data }),

    delete: <T = any>(url: string) =>
        request<T>({ url, method: 'DELETE' }),
};

export default client;
