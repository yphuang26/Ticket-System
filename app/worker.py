import redis
import time
import json

r = redis.Redis(host='redis', port=6379, decode_responses=True)

def process_orders():
    print("Worker 啟動，等待訂單...")
    while True:
        order = r.rpop("order_queue")
        if order:
            data = json.loads(order)
            print(f"正在寫入資料庫: {data['user_id']} 的訂單")
            time.sleep(0.1) # 模擬處理訂單時間
        else:
            time.sleep(1) # 等待新訂單

if __name__ == "__main__":
    process_orders()