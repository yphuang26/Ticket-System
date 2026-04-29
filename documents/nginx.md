## Nginx 介紹

Nginx 是一個高效能的 Web 伺服器，同時也常被拿來當作「反向代理（reverse proxy）」與「負載平衡器（load balancer）」。

### Nginx 在做什麼

當使用者發出請求（例如打開網站）：

```
使用者 → Nginx → 後端服務 (FastAPI / Node.js / Django / DB)
```

### 當 Web Server（靜態資源伺服器）

直接回應像是：

- HTML
- CSS
- Javascript

特點: 非常快（event-driven 架構）

### 當反向代理（Reverse Proxy）

把請求轉發給後端服務，例如：

```
/api → FastAPI
/ → 前端頁面
```

好處:

- 隱藏後端架構
- 統一入口
- 可做安全控管

### 當負載平衡（Load Balancer）

當你有多台後端：

```
Nginx
 ├── Server A
 ├── Server B
 └── Server C
```

Nginx 會幫你分流流量，例如：

- Round Robin（輪流）
- IP Hash
- Least Connections

### 處理高併發

Nginx 使用：

- 非同步（async）
- 事件驅動（event-driven）

### 實際範例

用 FastAPI 的典型架構：

```
Client → Nginx → FastAPI (Uvicorn)
```

Nginx 設定範例：

```
server {
    listen 80;

    location / {
        root /var/www/html;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
    }
}
```

意思：

- `/`: 回傳前端頁面
- `/api`: 轉給 FastAPI

---

## 本專案的 Nginx 設定

### 角色

Client 的所有流量先經過 Nginx（port 80），再轉發給 FastAPI（port 8000）：

```
Client → Nginx :80 → FastAPI :8000
```

FastAPI 只對 Docker 內部網路開放（`expose`，不對外 `ports`），外部無法繞過 Nginx 直打後端。

### Rate Limiting 設定（`nginx/default.conf`）

```nginx
# 以來源 IP 為單位，10 r/s，10MB 狀態記憶體（約可追蹤 16 萬個 IP）
limit_req_zone $binary_remote_addr zone=per_ip_limit:10m rate=10r/s;

server {
    listen 80;

    location / {
        limit_req zone=per_ip_limit burst=20 nodelay;
        limit_req_status 429;

        proxy_pass http://web:8000;
    }
}
```

**參數說明**

| 參數 | 值 | 說明 |
| --- | --- | --- |
| `rate=10r/s` | 10 req/s | 每個 IP 每秒最多通過 10 個請求 |
| `burst=20` | 20 | 允許瞬間突發最多 20 個超出 rate 的請求 |
| `nodelay` | — | 突發請求立即處理，不排隊等候；超過 burst 才拒絕 |
| `limit_req_status 429` | 429 | 超限回傳 429 Too Many Requests（預設是 503） |

**為何回傳 429 而不是 503？**

503 代表「服務不可用」，語意上是後端出問題；429 代表「請求太頻繁」，正確反映是客戶端行為被限制，語意更精確，也方便 k6 在測試中區分「被限流」與「後端錯誤」。

### 壓測下的行為

k6 container 內所有 VU 共用同一來源 IP，因此 `rate=10r/s` 是對全部 100 VU 共享的，不是每 VU 各享 10 r/s。100 VU × 60s 的壓測，理論上限約 600 次通過（實測 620 次），其餘 ~111,962 次全數被 429 攔截。詳見 [k6.md](k6.md)。
