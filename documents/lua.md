## Lua 腳本

通常用來嵌入到其他系統中，幫忙做邏輯控制、擴充功能或自動化。

### Lua 是什麼

Lua 是一種:

- 輕量（體積小、速度快）
- 可嵌入（常被塞進別的系統裡）
- 語法簡單（比 Python 還精簡）

常見用在:

- 遊戲（像 World of Warcraft 插件）
- Web（像 Nginx + Lua）
- 快取 / 資料庫（像 Redis）

### 為什麼用 Lua

可以嵌進系統裡跑

- Redis 用 Lua 做「原子操作」
- Nginx 用 Lua 做「動態邏輯」

效能好（比 Python 更輕）

- Lua VM 很小
- 啟動快
- 記憶體占用低

很適合做「控制邏輯」

- 遊戲 AI
- 流量控制
- 規則引擎

### Lua 在 Redis 的用法

關鍵特性: **原子性（Atomicity）**

- 一整段 Lua 腳本會「一次執行完」，中間不會被其他指令插入
- 可用來解決 Race Condition

### Lua 基本語法

變數:

```
a = 10
name = "Ping"
```

if 判斷:

```
if a > 5 then
    print("big")
else
    print("small")
end
```

function:

```
function add(a, b)
    return a + b
end
```

table: Lua 沒有 array / dict → 全部用 table

```
user = {
    name = "Ping",
    age = 25
}
```

---

## 本專案的 Lua 腳本

### 檔案位置

`app/scripts/buy_ticket.lua`

### 腳本內容

```lua
-- 原子化扣減庫存
-- 整段 Lua 在 Redis 單執行緒中不可中斷，「讀取 + 扣減」不會被其他指令插入，
-- 因此不需額外鎖就能防止超賣。
--
-- KEYS[1]：存放庫存數量的 Redis key（例如 "ticket_stock"）
-- 回傳 1 = 扣減成功，0 = 庫存耗盡

local stock = tonumber(redis.call('get', KEYS[1]))

if stock and stock > 0 then
    redis.call('decr', KEYS[1])
    return 1
else
    return 0
end
```

### 為什麼需要 Lua Script？

如果用一般的 Python 程式碼實作扣庫存，會是這樣：

```python
stock = redis.get('ticket_stock')   # 讀取
if stock > 0:
    redis.decr('ticket_stock')      # 扣減
```

這兩個步驟之間有空隙，在高並發下可能同時有多個 process 都讀到 `stock=1`，然後都執行 `decr`，導致庫存變成 `-1`（超賣）。

Lua Script 把「讀取 + 判斷 + 扣減」包成一個不可中斷的原子操作：

```
Redis 單執行緒
  └── Lua Script（讀 → 判斷 → 扣）← 整段不可中斷
```

Redis 保證執行 Lua 期間不會處理其他指令，因此無論多少個請求同時進來，庫存永遠不會低於 0。

### 如何載入與呼叫

腳本在 FastAPI 啟動時透過 `SCRIPT LOAD` 預載入 Redis，取得 SHA1 hash；之後每次購票呼叫 `EVALSHA` 執行：

```python
# app/main.py 啟動時
sha = redis.script_load(open('app/scripts/buy_ticket.lua').read())

# 購票時
result = redis.evalsha(sha, 1, 'ticket_stock')
# result == 1 → 成功，result == 0 → 售罄
```

使用 `EVALSHA` 而非 `EVAL` 的好處：腳本內容只需傳送一次，之後只傳 40 字元的 SHA1，減少網路傳輸量。
