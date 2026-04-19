"""
Structured logging (JSON format) + PII redaction untuk production Kasira (#10).

Zero new dependency — stdlib `logging` + `json.dumps()`. Pake `structlog` future
kalau butuh lebih banyak context (e.g. request_id automatic propagation).

Behavior:
  - ENV=production → JSON formatter (grep-friendly, Datadog/Loki ready)
  - ENV=dev → plain text formatter (human readable)
  - PIIRedactorFilter masks sensitive fields:
      * password, secret, token, authorization, api_key → [REDACTED]
      * phone (8-13 digit consecutive) → mask last 4 digits (e.g. 628***7890)
      * xendit_raw response containing api_key → strip
  - Request ID propagation via request_id_context (dari main.py middleware)
"""

import json
import logging
import os
import re
import sys
from datetime import datetime, timezone

# Pattern untuk PII detection — longgar tapi fokus ke kasus umum
_SENSITIVE_KEYS = {
    "password", "passwd", "pwd",
    "secret", "secret_key", "api_key", "apikey",
    "token", "access_token", "refresh_token", "callback_token",
    "authorization", "auth",
    "xendit_api_key", "private_key", "webhook_secret",
}
# Pattern phone Indonesia: 62xxx atau 08xxx, 8-14 digit total
_PHONE_PATTERN = re.compile(r"\b(?:62|0)\d{8,13}\b")
# Pattern JWT token (eyJ...)
_JWT_PATTERN = re.compile(r"\beyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+\b")


def _mask_phone(match: re.Match) -> str:
    """Mask phone — keep prefix + last 4 digits. 628123456789 → 628***6789"""
    phone = match.group(0)
    if len(phone) < 6:
        return "***"
    return f"{phone[:3]}***{phone[-4:]}"


def _redact_value(value):
    """Recursive redact — dict/list/str."""
    if isinstance(value, str):
        # Mask phone numbers in-place
        v = _PHONE_PATTERN.sub(_mask_phone, value)
        # Mask JWT tokens
        v = _JWT_PATTERN.sub("eyJ***REDACTED***", v)
        return v
    if isinstance(value, dict):
        return {
            k: ("[REDACTED]" if k.lower() in _SENSITIVE_KEYS else _redact_value(v))
            for k, v in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [_redact_value(x) for x in value]
    return value


class PIIRedactorFilter(logging.Filter):
    """
    Filter yg redact sensitive data di log record.
    Apply ke log msg + args + extra.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        # Redact message (after % formatting)
        try:
            if isinstance(record.msg, str):
                record.msg = _redact_value(record.msg)
        except Exception:
            pass

        # Redact args kalau structured logging dipakai
        if record.args:
            try:
                if isinstance(record.args, dict):
                    record.args = _redact_value(record.args)
                elif isinstance(record.args, tuple):
                    record.args = tuple(_redact_value(a) for a in record.args)
            except Exception:
                pass

        # Redact extra fields attached to record (structlog-style)
        for attr in list(record.__dict__.keys()):
            if attr.lower() in _SENSITIVE_KEYS:
                setattr(record, attr, "[REDACTED]")

        return True  # always pass (just mutate)


class JSONFormatter(logging.Formatter):
    """
    Output log sebagai JSON line — siap untuk Datadog/Loki ingestion.
    Include: timestamp ISO, level, logger, message, request_id, extra fields.
    """

    # Atribut stdlib LogRecord yang skip dari `extra` dump
    _STANDARD_ATTRS = {
        "name", "msg", "args", "levelname", "levelno", "pathname", "filename",
        "module", "exc_info", "exc_text", "stack_info", "lineno", "funcName",
        "created", "msecs", "relativeCreated", "thread", "threadName",
        "processName", "process", "message", "taskName",
    }

    def format(self, record: logging.LogRecord) -> str:
        # Base fields
        log_obj = {
            "ts": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Source location untuk ERROR/CRITICAL
        if record.levelno >= logging.ERROR:
            log_obj["source"] = f"{record.module}.{record.funcName}:{record.lineno}"

        # Exception info (traceback)
        if record.exc_info:
            log_obj["exc"] = self.formatException(record.exc_info)

        # Extra fields (e.g. request_id injected by middleware)
        try:
            from backend.core.request_context import request_id_context
            rid = request_id_context.get()
            if rid:
                log_obj["request_id"] = rid
        except Exception:
            pass

        # Merge any extra attributes injected via logger.info(..., extra={...})
        for key, value in record.__dict__.items():
            if key in self._STANDARD_ATTRS or key.startswith("_"):
                continue
            if key not in log_obj:
                try:
                    # Ensure JSON-serializable
                    json.dumps(value)
                    log_obj[key] = value
                except (TypeError, ValueError):
                    log_obj[key] = str(value)

        return json.dumps(log_obj, ensure_ascii=False, default=str)


def setup_logging(env: str = "production") -> None:
    """
    Configure root logger. Panggil SEKALI di main.py sebelum app start.
    Tidak akan double-setup kalau dipanggil berulang (check existing handler).
    """
    root = logging.getLogger()

    # Hindari double setup kalau dipanggil >1x
    if any(getattr(h, "_kasira_configured", False) for h in root.handlers):
        return

    # Clear existing handlers (uvicorn might install its own)
    root.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    handler._kasira_configured = True  # type: ignore[attr-defined]

    if env == "production":
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s %(levelname)s %(name)s [%(request_id)s]: %(message)s",
                defaults={"request_id": "-"},
            )
        )

    # PII redactor applied to all log records
    handler.addFilter(PIIRedactorFilter())

    root.addHandler(handler)
    root.setLevel(logging.INFO)

    # Silence overly verbose loggers
    for noisy in ("httpx", "httpcore", "sqlalchemy.engine", "asyncio"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
