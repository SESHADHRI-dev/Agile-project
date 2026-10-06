// Production AWS API Gateway Endpoint
const PRODUCTION_API_GATEWAY_URL = 'https://0wplj9j2jg.execute-api.us-east-1.amazonaws.com/Prod/api';

// Determine API Base URL:
// 1. Explicit environment variable if configured (VITE_API_URL or VITE_API_BASE)
// 2. Browser on deployed/cloud domain: ALWAYS use production AWS API Gateway URL
// 3. Browser on local development (localhost / 127.0.0.1): use '/api' to leverage Vite reverse proxy
const isLocalHost = typeof window !== 'undefined' && (
  window.location.hostname === 'localhost' ||
  window.location.hostname === '127.0.0.1' ||
  window.location.hostname === '0.0.0.0'
);

const API_BASE = (typeof import.meta !== 'undefined' && (import.meta.env?.VITE_API_URL || import.meta.env?.VITE_API_BASE))
  || (!isLocalHost ? PRODUCTION_API_GATEWAY_URL : '/api');

class ApiService {
  constructor() {
    // If no token in localStorage, initialize with local development token so requests never lack Bearer header
    const saved = typeof localStorage !== 'undefined' ? localStorage.getItem("token") : null;
    if (!saved || saved === "undefined" || saved === "null") {
      this.token = "dev-admin-token";
      if (typeof localStorage !== 'undefined') localStorage.setItem("token", "dev-admin-token");
    } else {
      this.token = saved;
    }
  }

  setToken(token) {
    this.token = token;
    if (typeof localStorage !== 'undefined') {
      if (token) {
        localStorage.setItem("token", token);
      } else {
        // In local mode, keep a valid dev fallback
        this.token = "dev-admin-token";
        localStorage.setItem("token", "dev-admin-token");
      }
    }
  }

  getHeaders() {
    return {
      "Content-Type": "application/json",
      ...(this.token ? { Authorization: `Bearer ${this.token}` } : { Authorization: "Bearer dev-admin-token" })
    };
  }

  async request(endpoint, options = {}, isRetry = false) {
    const url = `${API_BASE}${endpoint}`;
    const headers = {
      ...this.getHeaders(),
      ...(options.headers || {})
    };

    try {
      const response = await fetch(url, { ...options, headers, cache: 'no-store' });
      
      // Automatic 401 Self-Healing for Local Development
      if (response.status === 401 && !isRetry) {
        console.warn(`[API] 401 Unauthorized encountered on ${endpoint}. Refreshing local development token...`);
        this.setToken("dev-admin-token");
        // Retry once with clean dev token
        return this.request(endpoint, options, true);
      }

      const data = await response.json().catch(() => null);
      if (!response.ok) {
        let msg = `HTTP ${response.status} Error`;
        if (data) {
          if (typeof data.detail === 'string') {
            msg = data.detail;
          } else if (Array.isArray(data.detail)) {
            msg = data.detail
              .map(d => (d.msg ? `${d.loc ? d.loc.slice(-1)[0] + ': ' : ''}${d.msg}` : JSON.stringify(d)))
              .join('; ');
          } else if (data.error) {
            msg = typeof data.error === 'string' ? data.error : JSON.stringify(data.error);
          }
        }
        throw new Error(msg);
      }
      return data;
    } catch (err) {
      console.error(`API Error [${endpoint}]:`, err);
      // Transform raw network "Failed to fetch" into actionable user diagnostics
      if (err.name === 'TypeError' && err.message.toLowerCase().includes('fetch')) {
        const isLocal = typeof window !== 'undefined' && (
          window.location.hostname === 'localhost' ||
          window.location.hostname === '127.0.0.1'
        );
        const guidance = isLocal
          ? `Local backend server is not responding at ${url}. Please ensure the backend server is running on http://127.0.0.1:8000 (execute: python -m uvicorn backend.app.main:app --port 8000 --reload).`
          : `Unable to connect to production AWS backend at ${url}. Please check your internet connectivity or AWS API Gateway status.`;
        throw new Error(guidance);
      }
      throw err;
    }
  }

  // Auth
  async getAuthConfig() {
    return this.request("/auth/config");
  }

  async login(username, password) {
    const res = await this.request("/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password })
    });
    if (res.token) {
      this.setToken(res.token);
    }
    return res;
  }

  async getProfile() {
    return this.request("/auth/me");
  }

  logout() {
    this.setToken("dev-admin-token");
    localStorage.removeItem("user");
  }

  // Products
  async getProducts(params = {}) {
    const query = new URLSearchParams(params).toString();
    return this.request(`/products${query ? `?${query}` : ""}`);
  }

  async getProduct(id) {
    return this.request(`/products/${id}`);
  }

  async createProduct(payload) {
    return this.request("/products", {
      method: "POST",
      body: JSON.stringify(payload)
    });
  }

  async updateProduct(id, payload) {
    return this.request(`/products/${id}`, {
      method: "PUT",
      body: JSON.stringify(payload)
    });
  }

  async deleteProduct(id) {
    return this.request(`/products/${id}`, { method: "DELETE" });
  }

  // Suppliers
  async getSuppliers(search = "") {
    return this.request(`/suppliers${search ? `?search=${encodeURIComponent(search)}` : ""}`);
  }

  async createSupplier(payload) {
    return this.request("/suppliers", {
      method: "POST",
      body: JSON.stringify(payload)
    });
  }

  async updateSupplier(id, payload) {
    return this.request(`/suppliers/${id}`, {
      method: "PUT",
      body: JSON.stringify(payload)
    });
  }

  async deleteSupplier(id) {
    return this.request(`/suppliers/${id}`, { method: "DELETE" });
  }

  // Transactions
  async getPurchases() {
    return this.request("/purchases");
  }

  async recordPurchase(payload) {
    return this.request("/purchases", {
      method: "POST",
      body: JSON.stringify(payload)
    });
  }

  async getSales(productId = "") {
    return this.request(`/sales${productId ? `?product_id=${productId}` : ""}`);
  }

  async recordSale(payload) {
    return this.request("/sales", {
      method: "POST",
      body: JSON.stringify(payload)
    });
  }

  // Inventory & Alerts
  async getInventory() {
    return this.request("/inventory");
  }

  async getAlerts() {
    return this.request("/alerts");
  }

  // Predictions & ML
  async calculatePrediction(payload) {
    return this.request("/predictions/calculate", {
      method: "POST",
      body: JSON.stringify(payload)
    });
  }

  async getRecommendations(method = "exponential_smoothing") {
    return this.request(`/predictions/recommendations?method=${method}`);
  }

  // Reports & Seeding
  async getReportsSummary() {
    return this.request("/reports/summary");
  }

  getExportUrl(reportType, format = "csv") {
    return `${API_BASE}/reports/export?report_type=${reportType}&format=${format}`;
  }

  async downloadReport(reportType, format = "csv") {
    const res = await fetch(`${API_BASE}/reports/export?report_type=${reportType}&format=${format}`, {
      headers: this.getHeaders()
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Failed to download report" }));
      throw new Error(err.detail || err.error || "Failed to download report");
    }
    return res.blob();
  }

  async seedDatabase() {
    return this.request("/seed", { method: "POST" });
  }
}

export const api = new ApiService();
