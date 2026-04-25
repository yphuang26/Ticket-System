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
