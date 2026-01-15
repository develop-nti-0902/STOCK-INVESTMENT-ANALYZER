import axios from 'axios';

// APIベースURL (環境変数から取得、デフォルトはlocalhost)
const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000';

// Axiosインスタンスの作成
const apiClient = axios.create({
    baseURL: API_BASE_URL,
    timeout: 60000, // 60秒（銘柄マスタ更新は時間がかかる可能性があるため）
    headers: {
        'Content-Type': 'application/json',
    },
});

// レスポンスインターセプター (エラーハンドリング)
apiClient.interceptors.response.use(
    (response) => response,
    (error) => {
        if (error.response) {
            // サーバーからのエラーレスポンス
            console.error('API Error:', error.response.data);
        } else if (error.request) {
            // リクエストが送信されたがレスポンスがない
            console.error('No response from server');
        } else {
            // リクエスト設定時のエラー
            console.error('Request setup error:', error.message);
        }
        return Promise.reject(error);
    }
);

/**
 * 銘柄マスタAPI
 */
export const stockMasterApi = {
    /**
     * 銘柄マスタを更新
     * @param {number} batchSize - バッチサイズ (デフォルト: 500)
     * @returns {Promise<{message: string, updated_count: number}>}
     */
    refresh: async (batchSize = 500) => {
        const response = await apiClient.post(`/api/v1/stock-master/refresh`, null, {
            params: { batch_size: batchSize },
        });
        return response.data;
    },

    /**
     * 銘柄マスタをサンプルデータで更新 (テスト用)
     * @param {number} sampleSize - サンプルサイズ (デフォルト: 100)
     * @param {number} batchSize - バッチサイズ (デフォルト: 500)
     * @returns {Promise<{message: string, updated_count: number}>}
     */
    refreshSample: async (sampleSize = 100, batchSize = 500) => {
        const response = await apiClient.post(`/api/v1/stock-master/refresh/sample`, null, {
            params: { sample_size: sampleSize, batch_size: batchSize },
        });
        return response.data;
    },

    /**
     * 全アクティブ銘柄を取得
     * @returns {Promise<{symbols: string[], count: number}>}
     */
    getAllActiveSymbols: async () => {
        const response = await apiClient.get(`/api/v1/stock-master/symbols`);
        return response.data;
    },

    /**
     * 市場別の銘柄を取得
     * @param {string} market - 市場名 (例: 'Prime', 'Standard', 'Growth')
     * @returns {Promise<{symbols: string[], count: number}>}
     */
    getSymbolsByMarket: async (market) => {
        const response = await apiClient.get(`/api/v1/stock-master/symbols/market`, {
            params: { market },
        });
        return response.data;
    },

    /**
     * 銘柄マスタをリセット (全削除)
     * @returns {Promise<{message: string, deleted_count: number}>}
     */
    reset: async () => {
        const response = await apiClient.delete(`/api/v1/stock-master/reset`);
        return response.data;
    },
};

/**
 * ヘルスチェック
 * @returns {Promise<{status: string}>}
 */
export const healthCheck = async () => {
    const response = await apiClient.get('/health');
    return response.data;
};

export default apiClient;
