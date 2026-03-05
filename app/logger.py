import json
import logging


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_record = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "module": record.module,
            "message": record.getMessage(),
        }

        # 支援 logger.info(..., extra={...}) 的自訂欄位
        for key, value in record.__dict__.items():
            if key not in log_record and not key.startswith("_"):
                log_record[key] = value

        return json.dumps(log_record, ensure_ascii=False, default=str)


def get_logger(name: str = "ticket_system") -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    if not logger.handlers:  # 避免 hot reload 或重複 import 時重複掛 handler
        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)

    return logger
