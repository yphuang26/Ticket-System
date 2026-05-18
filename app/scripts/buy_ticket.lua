-- 原子化扣減庫存並推入訂單佇列
-- 整段 Lua 在 Redis 單執行緒中不可中斷，DECR 與 LPUSH 作為一個整體執行，
-- 不存在「庫存扣了但訂單沒進佇列」的中間狀態。
--
-- KEYS[1]：ticket_stock
-- KEYS[2]：order_queue
-- ARGV[1]：order JSON 字串
-- 回傳 1 = 成功，0 = 庫存耗盡

local stock = tonumber(redis.call('get', KEYS[1]))

if stock and stock > 0 then
    redis.call('decr', KEYS[1])
    redis.call('lpush', KEYS[2], ARGV[1])
    return 1
else
    return 0
end
