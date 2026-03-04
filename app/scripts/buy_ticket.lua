-- KEYS[1]: 票券的 Key (例如 "ticket_count")
-- ARGV[1]: 使用者 ID (選填)

local stock = tonumber(redis.call('get', KEYS[1]))

if stock and stock > 0 then
    redis.call('decr', KEYS[1])
    return 1 -- 購買成功
else
    return 0 -- 購買失敗
end