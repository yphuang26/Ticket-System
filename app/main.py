import json
import redis
from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator
from app.logger import get_logger

app = FastAPI()

# 初始化監控儀器
Instrumentator().instrument(app).expose(app)

# 連接 Redis
r = redis.Redis(host='redis', port=6379, decode_responses=True)
logger = get_logger()


@app.on_event("startup")
async def startup_event():
    # 初始化庫存: 設定票數為 10 張
    r.set("ticket_stock", 10)
    logger.info("服務啟動完成，ticket_stock 初始化為 10")

@app.post("/buy")
async def buy_ticket(user_id: str = "user_default"):
    # 讀取 Lua 腳本
    with open("app/scripts/buy_ticket.lua", "r", encoding="utf-8") as script_file:
        lua_script = script_file.read()

    # 執行 Lua 腳本 (確保原子性)
    result = r.eval(lua_script, 1, "ticket_stock")

    if result == 1:
        order_data = json.dumps({"user_id": user_id, "event": "concert_AAA"})
        r.lpush("order_queue", order_data)
        logger.info("搶票成功", extra={"user_id": user_id})
        return {"status": "success", "message": "搶票成功，訂單處理中"}
    else:
        logger.warning("搶票失敗 (已售罄)", extra={"user_id": user_id})
        return {"status": "fail", "message": "已售罄"}

@app.get("/stock")
async def get_stock():
    # 讀取庫存
    stock = r.get("ticket_stock")
    logger.info(f"查詢庫存 remaining_stock={stock}")
    return {"remaining_stock": stock}