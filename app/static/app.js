const REFRESH_INTERVAL_MS = 3000;

async function fetchStock() {
  try {
    const res = await fetch('/stock');
    const data = await res.json();

    document.getElementById('stock').textContent = data.remaining_stock;
    document.getElementById('updated').textContent =
      '最後更新：' + new Date().toLocaleTimeString('zh-TW');
  } catch (e) {
    document.getElementById('stock').textContent = '?';
    document.getElementById('updated').textContent = '無法連線';
  }
}

fetchStock();
setInterval(fetchStock, REFRESH_INTERVAL_MS);
