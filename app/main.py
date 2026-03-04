from fastapi import FastAPI
import redis

app = FastAPI()

# 連接 Redis
r = redis.Redis(host='redis', port=6379, decode_responses=True)

@app.on_event("startup")
async def startup_event():
    # 初始化庫存: 設定票數為 10 張
    r.set("ticket_stock", 10)

@app.post("/buy")
async def buy_ticket():
    # 讀取 Lua 腳本
    lua_script = open("app/scripts/buy_ticket.lua", "r").read()

    # 執行 Lua 腳本 (確保原子性)
    result = r.eval(lua_script, 1, "ticket_stock")

    if result == 1:
        return {"status": "success", "message": "搶票成功!"}
    else:
        return {"status": "fail", "message": "已售罄"}

@app.get("/stock")
async def get_stock():
    # 讀取庫存
    stock = r.get("ticket_stock")
    return {"remaining_stock": stock}