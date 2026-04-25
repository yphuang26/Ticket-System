import json
import logging


class JsonFormatter(logging.Formatter):
    """將 log 序列化成單行 JSON，便於日誌收集工具解析。"""

    def format(self, record: logging.LogRecord) -> str:
        log_record = {
            "timestamp": self.formatTime(record),
            "level":     record.levelname,
            "logger":    record.name,
            "module":    record.module,
            "message":   record.getMessage(),
        }

        # 支援 logger.info(..., extra={...}) 的自訂欄位
        for key, value in record.__dict__.items():
            if key not in log_record and not key.startswith("_"):
                log_record[key] = value

        return json.dumps(log_record, ensure_ascii=False, default=str)


def get_logger(name: str = "ticket_system") -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    logger.propagate = False  # 不往上傳給 root logger，避免重複輸出

    if not logger.handlers:  # 避免 hot reload 時重複掛 handler
        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)

    return logger
