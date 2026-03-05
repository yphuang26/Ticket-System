import redis
import time
import json
from app.database import SessionLocal, init_db
from app.models import Order

r = redis.Redis(host='redis', port=6379, decode_responses=True)

def process_orders():
    # 初始化資料庫
    init_db()
    print("Worker 啟動，等待訂單寫入資料庫...")
    
    while True:
        order_json = r.rpop("order_queue")
        if order_json:
            data = json.loads(order_json)
            db = SessionLocal()
            try:
                # 建立訂單物件
                new_order = Order(
                    user_id=data['user_id'],
                    event_name=data['event'],
                )
                db.add(new_order)
                db.commit() # 正式寫入 PostgreSQL
                print(f"成功寫入資料庫: User {data['user_id']}")
            except Exception as e:
                db.rollback()
                print(f"寫入失敗，錯誤原因: {e}")
            finally:
                db.close()
        else:
            time.sleep(1) # 等待新訂單

if __name__ == "__main__":
    process_orders()