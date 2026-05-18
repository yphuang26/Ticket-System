import redis
import time
import json
from sqlalchemy.exc import OperationalError
from app.database import SessionLocal, init_db
from app.logger import get_logger
from app.models import Order

r = redis.Redis(host='redis', port=6379, decode_responses=True)
logger = get_logger()

def process_orders():
    # PostgreSQL 啟動後可能需要數秒才就緒，retry 直到連線成功
    while True:
        try:
            init_db()
            break
        except OperationalError as e:
            logger.warning("資料庫尚未就緒，2 秒後重試", extra={"error": str(e)})
            time.sleep(2)

    logger.info("Worker 啟動，等待訂單寫入資料庫...")
    
    MAX_RETRIES = 3
    DLQ_ALERT_THRESHOLD = 5

    while True:
        # RPOP 從佇列尾端取出（main.py 用 LPUSH 推入，形成 FIFO）
        order_json = r.rpop("order_queue")

        if order_json:
            data = json.loads(order_json)
            for attempt in range(MAX_RETRIES):
                db = SessionLocal()
                try:
                    new_order = Order(
                        user_id=data['user_id'],
                        event_name=data['event'],
                    )
                    db.add(new_order)
                    db.commit()
                    logger.info("成功寫入資料庫", extra={"user_id": data["user_id"]})
                    break
                except Exception as e:
                    db.rollback()
                    if attempt < MAX_RETRIES - 1:
                        wait = 0.5 * (attempt + 1)  # 0.5s, 1.0s
                        logger.warning(f"寫入失敗，第 {attempt + 1} 次重試（{wait}s 後）", extra={"error": str(e)})
                        time.sleep(wait)
                    else:
                        r.lpush("order_queue_failed", order_json)
                        logger.error("重試 3 次仍失敗，移至 dead letter queue", extra={"error": str(e), "order": data})
                finally:
                    db.close()

            # 監控：dead letter queue 超過閾值時告警
            failed_count = r.llen("order_queue_failed")
            if failed_count >= DLQ_ALERT_THRESHOLD:
                logger.error("order_queue_failed 累積過多，需人工介入", extra={"count": failed_count})
        else:
            time.sleep(1) # 等待新訂單

if __name__ == "__main__":
    process_orders()