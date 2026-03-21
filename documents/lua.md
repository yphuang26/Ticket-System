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
