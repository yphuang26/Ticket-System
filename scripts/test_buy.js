import http from 'k6/http';
import { check, sleep } from 'k6';

// 測試設定
export const options = {
    vus: 100, // 模擬 100 個虛擬用戶同時在線
    duration: '5s', // 測試持續 5 秒
};

export default function() {
    const url = 'http://web:8000/buy';

    // 發送 POST 請求搶票
    const res = http.post(url);

    // 驗證回傳狀態是否為 200
    check(res, {
        'status is 200': (r) => r.status === 200,
    });

    // 模擬用戶行為間隔 (0-2 秒)
    sleep(Math.random() * 2);
}