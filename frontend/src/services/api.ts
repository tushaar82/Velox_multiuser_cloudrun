import axios, { type AxiosInstance, type AxiosError } from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000';

class ApiClient {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Request interceptor to add auth token
    this.client.interceptors.request.use(
      (config) => {
        const token = localStorage.getItem('auth_token');
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
      },
      (error) => Promise.reject(error)
    );

    // Response interceptor to handle errors and token refresh
    this.client.interceptors.response.use(
      (response) => response,
      async (error: AxiosError) => {
        const originalRequest = error.config as any;

        if (error.response?.status === 401 && !originalRequest._retry) {
          originalRequest._retry = true;

          try {
            // Try to refresh the token
            const response = await this.client.post('/auth/refresh');
            const newToken = response.data.token;
            
            if (newToken) {
              localStorage.setItem('auth_token', newToken);
              originalRequest.headers.Authorization = `Bearer ${newToken}`;
              return this.client(originalRequest);
            }
          } catch (refreshError) {
            // Refresh failed, logout user
            localStorage.removeItem('auth_token');
            window.location.href = '/login';
            return Promise.reject(refreshError);
          }
        }

        if (error.response?.status === 401) {
          // Token expired or invalid and refresh failed
          localStorage.removeItem('auth_token');
          window.location.href = '/login';
        }
        
        return Promise.reject(error);
      }
    );
  }

  // Authentication
  async login(email: string, password: string) {
    const response = await this.client.post('/auth/login', { email, password });
    return response.data;
  }

  async register(email: string, password: string, role: string) {
    const response = await this.client.post('/auth/register', { email, password, role });
    return response.data;
  }

  async logout() {
    const response = await this.client.post('/auth/logout');
    return response.data;
  }

  async refreshSession() {
    const response = await this.client.post('/auth/refresh');
    return response.data;
  }

  // User Management
  async getUser() {
    const response = await this.client.get('/users/me');
    return response.data;
  }

  async inviteInvestor(accountId: string, email: string) {
    const response = await this.client.post(`/users/accounts/${accountId}/invite`, { email });
    return response.data;
  }

  async acceptInvitation(invitationId: string) {
    const response = await this.client.post(`/users/invitations/${invitationId}/accept`);
    return response.data;
  }

  async revokeInvestorAccess(accountId: string, userId: string) {
    const response = await this.client.delete(`/users/accounts/${accountId}/access/${userId}`);
    return response.data;
  }

  async getAccountUsers(accountId: string) {
    const response = await this.client.get(`/users/accounts/${accountId}/users`);
    return response.data;
  }

  async getInvestorAccounts() {
    const response = await this.client.get('/users/investor/accounts');
    return response.data;
  }

  // Broker Connections
  async connectBroker(accountId: string, brokerName: string, credentials: any) {
    const response = await this.client.post(`/brokers/connect`, {
      account_id: accountId,
      broker_name: brokerName,
      credentials,
    });
    return response.data;
  }

  async disconnectBroker(connectionId: string) {
    const response = await this.client.delete(`/brokers/${connectionId}`);
    return response.data;
  }

  async getBrokerStatus(connectionId: string) {
    const response = await this.client.get(`/brokers/${connectionId}/status`);
    return response.data;
  }

  async getBrokerConnections(accountId: string) {
    const response = await this.client.get(`/brokers/connections/${accountId}`);
    return response.data;
  }

  async listBrokers() {
    const response = await this.client.get('/brokers/available');
    return response.data;
  }

  // Strategies
  async listStrategies() {
    const response = await this.client.get('/strategies');
    return response.data;
  }

  async getStrategy(strategyId: string) {
    const response = await this.client.get(`/strategies/${strategyId}`);
    return response.data;
  }

  async activateStrategy(accountId: string, strategyId: string, config: any) {
    const response = await this.client.post('/strategies/activate', {
      account_id: accountId,
      strategy_id: strategyId,
      config,
    });
    return response.data;
  }

  async pauseStrategy(activeStrategyId: string) {
    const response = await this.client.post(`/strategies/${activeStrategyId}/pause`);
    return response.data;
  }

  async resumeStrategy(activeStrategyId: string) {
    const response = await this.client.post(`/strategies/${activeStrategyId}/resume`);
    return response.data;
  }

  async stopStrategy(activeStrategyId: string) {
    const response = await this.client.post(`/strategies/${activeStrategyId}/stop`);
    return response.data;
  }

  async getActiveStrategies(accountId: string, tradingMode?: string) {
    const params = tradingMode ? { trading_mode: tradingMode } : {};
    const response = await this.client.get(`/strategies/active/${accountId}`, { params });
    return response.data;
  }

  // Risk Management
  async setMaxLossLimit(accountId: string, tradingMode: string, limit: number) {
    const response = await this.client.post('/risk/loss-limit', {
      account_id: accountId,
      trading_mode: tradingMode,
      max_loss_limit: limit,
    });
    return response.data;
  }

  async getRiskLimits(accountId: string, tradingMode: string) {
    const response = await this.client.get(`/risk/loss-limit/${accountId}/${tradingMode}`);
    return response.data;
  }

  async acknowledgeLimitBreach(accountId: string, tradingMode: string, newLimit?: number) {
    const response = await this.client.post('/risk/acknowledge-breach', {
      account_id: accountId,
      trading_mode: tradingMode,
      new_limit: newLimit,
    });
    return response.data;
  }

  async getStrategyLimits(tradingMode: string) {
    const response = await this.client.get(`/risk/strategy-limits/${tradingMode}`);
    return response.data;
  }

  async setStrategyLimits(tradingMode: string, maxStrategies: number) {
    const response = await this.client.post('/risk/strategy-limits', {
      trading_mode: tradingMode,
      max_concurrent_strategies: maxStrategies,
    });
    return response.data;
  }

  // Orders
  async submitOrder(order: any) {
    const response = await this.client.post('/orders', order);
    return response.data;
  }

  async cancelOrder(orderId: string) {
    const response = await this.client.delete(`/orders/${orderId}`);
    return response.data;
  }

  async getOrders(accountId: string, tradingMode?: string) {
    const params = tradingMode ? { trading_mode: tradingMode } : {};
    const response = await this.client.get(`/orders/${accountId}`, { params });
    return response.data;
  }

  async getOrderStatus(orderId: string) {
    const response = await this.client.get(`/orders/${orderId}/status`);
    return response.data;
  }

  // Positions
  async getPositions(accountId: string, tradingMode?: string) {
    const params = tradingMode ? { trading_mode: tradingMode } : {};
    const response = await this.client.get(`/positions/${accountId}`, { params });
    return response.data;
  }

  async closePosition(positionId: string) {
    const response = await this.client.post(`/positions/${positionId}/close`);
    return response.data;
  }

  async updateTrailingStopLoss(positionId: string, config: any) {
    const response = await this.client.put(`/positions/${positionId}/trailing-stop`, config);
    return response.data;
  }

  async getRiskMetrics(accountId: string, tradingMode: string) {
    const response = await this.client.get(`/positions/${accountId}/risk-metrics`, {
      params: { trading_mode: tradingMode },
    });
    return response.data;
  }

  // Backtesting
  async startBacktest(config: any) {
    const response = await this.client.post('/backtests', config);
    return response.data;
  }

  async getBacktestStatus(backtestId: string) {
    const response = await this.client.get(`/backtests/${backtestId}/status`);
    return response.data;
  }

  async getBacktestResults(backtestId: string) {
    const response = await this.client.get(`/backtests/${backtestId}/results`);
    return response.data;
  }

  async listBacktests(strategyId: string) {
    const response = await this.client.get(`/backtests/strategy/${strategyId}`);
    return response.data;
  }

  // Analytics
  async getPerformanceMetrics(accountId: string, tradingMode: string, period: string) {
    const response = await this.client.get(`/analytics/${accountId}/metrics`, {
      params: { trading_mode: tradingMode, period },
    });
    return response.data;
  }

  async getEquityCurve(accountId: string, tradingMode: string, startDate: string, endDate: string) {
    const response = await this.client.get(`/analytics/${accountId}/equity-curve`, {
      params: { trading_mode: tradingMode, start_date: startDate, end_date: endDate },
    });
    return response.data;
  }

  async getStrategyBreakdown(accountId: string, tradingMode: string) {
    const response = await this.client.get(`/analytics/${accountId}/strategy-breakdown`, {
      params: { trading_mode: tradingMode },
    });
    return response.data;
  }

  async getTradeAnalysis(accountId: string, tradingMode: string) {
    const response = await this.client.get(`/analytics/${accountId}/trade-analysis`, {
      params: { trading_mode: tradingMode },
    });
    return response.data;
  }

  async exportReport(accountId: string, tradingMode: string, format: string) {
    const response = await this.client.get(`/analytics/${accountId}/export`, {
      params: { trading_mode: tradingMode, format },
      responseType: 'blob',
    });
    return response.data;
  }

  async compareToBenchmark(accountId: string, benchmarkIndex: string) {
    const response = await this.client.get(`/analytics/${accountId}/benchmark`, {
      params: { benchmark: benchmarkIndex },
    });
    return response.data;
  }

  // Symbol Mapping
  async uploadSymbolMapping(brokerName: string, file: File) {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('broker_name', brokerName);
    const response = await this.client.post('/api/symbol-mappings/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  }

  async getSymbolMappings(brokerName: string) {
    const response = await this.client.get(`/api/symbol-mappings/${brokerName}`);
    return response.data;
  }

  async validateSymbol(brokerName: string, standardSymbol: string) {
    const response = await this.client.get(`/api/symbol-mappings/${brokerName}/${standardSymbol}/validate`);
    return response.data;
  }

  async deleteSymbolMapping(brokerName: string, standardSymbol: string) {
    const response = await this.client.delete(`/api/symbol-mappings/${brokerName}/${standardSymbol}`);
    return response.data;
  }

  async clearBrokerMappings(brokerName: string) {
    const response = await this.client.delete(`/api/symbol-mappings/${brokerName}`);
    return response.data;
  }

  // Notifications
  async getNotifications(userId: string) {
    const response = await this.client.get(`/notifications/${userId}`);
    return response.data;
  }

  async markNotificationRead(notificationId: string) {
    const response = await this.client.put(`/notifications/${notificationId}/read`);
    return response.data;
  }

  async updateNotificationPreferences(userId: string, preferences: any) {
    const response = await this.client.put(`/notifications/${userId}/preferences`, preferences);
    return response.data;
  }

  async getNotificationPreferences(userId: string) {
    const response = await this.client.get(`/notifications/${userId}/preferences`);
    return response.data;
  }

  // Admin
  async getSystemHealth() {
    const response = await this.client.get('/admin/health');
    return response.data;
  }

  async getAllUsers() {
    const response = await this.client.get('/admin/users');
    return response.data;
  }

  async disableUser(userId: string) {
    const response = await this.client.post(`/admin/users/${userId}/disable`);
    return response.data;
  }

  async enableUser(userId: string) {
    const response = await this.client.post(`/admin/users/${userId}/enable`);
    return response.data;
  }

  async getAuditLogs(filters?: any) {
    const response = await this.client.get('/admin/audit-logs', { params: filters });
    return response.data;
  }

  async generateDailyReport(date: string) {
    const response = await this.client.get('/admin/reports/daily', {
      params: { date },
      responseType: 'blob',
    });
    return response.data;
  }
}

export const apiClient = new ApiClient();
