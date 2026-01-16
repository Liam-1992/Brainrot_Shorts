from __future__ import annotations

import json
import sys
import urllib.request


def _get(url: str) -> dict:
    with urllib.request.urlopen(url) as response:
        payload = response.read().decode("utf-8")
        return json.loads(payload)


def _post(url: str, body: dict) -> dict:
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req) as response:
        payload = response.read().decode("utf-8")
        return json.loads(payload)


def main() -> int:
    base = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
    print("Health:", _get(f"{base}/health"))
    print("Templates:", _get(f"{base}/templates"))
    print("Assets:", _get(f"{base}/assets/list?type=bg_clips"))
    print("Hook score:", _post(f"{base}/score_hook", {"hook_text": "This secret will shock you"}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
