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

- Round Robin（輪流
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
