# salons/forms.py
from __future__ import annotations

import json
import re
from decimal import Decimal
from typing import Any, Dict

from django import forms
from django.core.exceptions import ValidationError


class FriendlyJSONWidget(forms.Textarea):
    """Textarea that accepts a simple shorthand and auto-converts to JSON.

    - Plain number => {"default": <number>}
    - key:value pairs separated by comma/semicolon or new lines => {key: number, ...}
    - Valid JSON stays as-is.
    """

    def __init__(self, attrs: Dict[str, Any] | None = None):
        default_attrs = {
            "rows": 6,
            "class": "vLargeTextField friendly-json-autofmt",
            "placeholder": "1500 | Взрослые: 2000, Дети: 1000 | {\"VIP\": 5000}",
        }
        if attrs:
            default_attrs.update(attrs)
        super().__init__(default_attrs)

    class Media:
        js = ("salons/js/friendly_json_autofmt.js",)


class FriendlyJSONField(forms.JSONField):
    """JSON field that can parse user-friendly shorthand.

    Accepted inputs:
    - Plain number: "1500" -> {"default": 1500}
    - Pairs: "короткая: 1200, длинная: 1800" -> {"короткая": 1200, "длинная": 1800}
    - Lines: "дети=1000\nвзрослые=1500" -> {"дети": 1000, "взрослые": 1500}
    - Valid JSON string passes through
    """

    widget = FriendlyJSONWidget
    _num_re = re.compile(r"^\s*[-+]?\d+(?:[.,]\d+)?\s*$")

    def prepare_value(self, value: Any) -> str:
        if value in (None, ""):
            return ""
        try:
            return json.dumps(value, indent=2, ensure_ascii=False)
        except Exception:
            return str(value)

    def to_python(self, value: Any) -> Any:
        # Let super handle already-parsed dict/list/None
        if isinstance(value, (dict, list)) or value in (None, ""):
            return super().to_python(value)

        if isinstance(value, (int, float, Decimal)):
            return {"default": value}

        if isinstance(value, str):
            raw = value.strip()
            # валидный JSON
            if raw.startswith("{") or raw.startswith("["):
                return json.loads(raw)
            # одиночное число
            if self._num_re.match(raw):
                return {"default": self._to_number(raw)}
            # пары ключ:значение
            parts = [p for p in re.split(r"[\n;,]", raw) if p.strip()]
            data: Dict[str, Any] = {}
            for part in parts:
                if ":" in part:
                    k, v = part.split(":", 1)
                elif "=" in part:
                    k, v = part.split("=", 1)
                else:
                    continue
                k = k.strip().strip('"').strip("'")
                v = v.strip()
                data[k] = self._to_number(v)
            if data:
                return data

        raise ValidationError("Введите JSON или формат: ключ: значение")

    @staticmethod
    def _to_number(text: str) -> Any:
        t = text.strip().replace(",", ".")
        # true/false/null/"строки"
        try:
            return json.loads(t)
        except Exception:
            pass
        try:
            return float(t) if "." in t else int(t)
        except Exception:
            return t
