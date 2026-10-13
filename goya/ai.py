# -*- coding: utf-8 -*-
"""دستیار هوش مصنوعی استودیو — کلاینت سازگار با OpenAI

با هر سرویس متن‌بازی که اندپوینت /v1/chat/completions داشته باشد کار می‌کند:
Ollama (http://localhost:11434/v1)، LM Studio (http://localhost:1234/v1)،
llama.cpp server، vLLM، LocalAI و…
فقط کتابخانه‌ی استاندارد — استریم SSE با urllib و پارس دستی خط‌های «data:».
"""

import json
import urllib.error
import urllib.request


class AiError(Exception):
    """خطای قابل نمایش به کاربر (اتصال، پاسخ بد، مدل ناموجود و…)"""


def _join_url(base, path):
    base = (base or "").strip().rstrip("/")
    if not base:
        raise AiError("آدرس سرویس خالی است — در تنظیمات، نشانی سرویس را بنویس")
    # قرارداد رایج: اگر کاربر فقط ریشه را داد، /v1 را خودمان می‌گذاریم
    if not base.endswith("/v1"):
        base += "/v1"
    return base + path


def _request(base, path, api_key, payload=None, timeout=120):
    url = _join_url(base, path)
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = "Bearer " + api_key
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url, data=data, headers=headers, method="POST" if data else "GET")
    try:
        return urllib.request.urlopen(req, timeout=timeout)
    except urllib.error.HTTPError as e:
        try:
            detail = e.read().decode("utf-8", "replace").strip()[:300]
        except OSError:
            detail = ""
        raise AiError("سرویس خطای {} داد: {}".format(e.code, detail or "بدون توضیح")) from None
    except urllib.error.URLError as e:
        raise AiError(
            "اتصال به سرویس برقرار نشد ({}) — مطمئن شو سرویس روشن است و نشانی/پورت درست است".format(e.reason)
        ) from None
    except OSError as e:
        raise AiError("خطای شبکه: {}".format(e)) from None


def list_models(base, api_key=""):
    """فهرست مدل‌های موجود روی سرویس (GET /v1/models)"""
    with _request(base, "/models", api_key, timeout=15) as resp:
        data = json.loads(resp.read().decode("utf-8", "replace"))
    ids = [str(m.get("id", "")).strip() for m in data.get("data", [])]
    ids = sorted(x for x in ids if x)
    if not ids:
        raise AiError("سرویس هیچ مدلی معرفی نکرد — اول روی سرویس مدل دانلود/بارگذاری کن")
    return ids


def chat_stream(base, api_key, model, messages, on_chunk, stop_flag=None, temperature=0.4):
    """درخواست chat/completions با استریم.

    هر قطعه‌ی متن به on_chunk(piece) داده می‌شود؛ متن کامل برمی‌گردد.
    اگر سرویس استریم را پشتیبانی نکند، پاسخ کامل را یک‌جا به on_chunk می‌دهد.
    """
    if not (model or "").strip():
        raise AiError("مدل انتخاب نشده — در تنظیمات، مدل را بنویس یا از فهرست انتخاب کن")
    payload = {
        "model": model.strip(),
        "messages": messages,
        "stream": True,
        "temperature": temperature,
    }
    raw_lines = []
    full = []
    with _request(base, "/chat/completions", api_key, payload, timeout=300) as resp:
        for raw in resp:
            line = raw.decode("utf-8", "replace").strip()
            raw_lines.append(line)
            if not line.startswith("data:"):
                continue
            data = line[5:].strip()
            if data == "[DONE]":
                break
            try:
                obj = json.loads(data)
            except ValueError:
                continue
            if obj.get("error"):
                raise AiError(str(obj["error"])[:300])
            choice = (obj.get("choices") or [{}])[0]
            delta = choice.get("delta") or {}
            piece = delta.get("content") or choice.get("text") or ""
            if piece:
                full.append(piece)
                try:
                    on_chunk(piece)
                except Exception:
                    pass  # خطای رابط نباید دریافت را قطع کند
            if stop_flag is not None and stop_flag.get("stop"):
                break

    if full:
        return "".join(full)

    # سرویس استریم را پشتیبانی نکرد — کل بدنه را به‌عنوان پاسخ JSON معمولی بخوان
    body = "\n".join(raw_lines).strip()
    if not body:
        raise AiError("سرویس پاسخ خالی داد")
    try:
        obj = json.loads(body)
        if obj.get("error"):
            raise AiError(str(obj["error"])[:300])
        text = ((obj.get("choices") or [{}])[0].get("message") or {}).get("content") or ""
        if text:
            try:
                on_chunk(text)
            except Exception:
                pass
            return text
    except ValueError:
        pass
    raise AiError("پاسخ سرویس قابل خواندن نبود — احتمالاً این سرویس chat/completions ندارد")
