import json
import ssl
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8000/api"
EMAIL = "editor_test@local.dev"
PASSWORD = "secret12345"


def request(path: str, method: str = "GET", body=None, headers: dict[str, str] | None = None):
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
    h = {"Content-Type": "application/json"}
    if headers:
        h.update(headers)
    req = urllib.request.Request(f"{BASE}{path}", data=data, headers=h, method=method)
    ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(req, context=ctx) as resp:
            raw = resp.read()
            if not raw:
                return None
            return json.loads(raw.decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"{method} {path} -> {e.code}: {e.read().decode()}") from e


def main() -> None:
    resp = request("/auth/login", "POST", {"email": EMAIL, "password": PASSWORD})
    token = resp["access_token"]

    settings = {
        "siteName": "Kraftista",
        "headline": "Artisan-Made\nwith Purpose",
        "email": "hello@kraftista.test",
        "phone": "+1 (555) 123-4567",
        "address": "123 Artisan Street",
        "aboutText": "About",
        "primaryColor": "#ff0000",
        "secondaryColor": "#00ff00",
        "logo": "K",
        "featuredProductIds": ["1", "2", "3", "4"],
        "faviconUrl": None,
    }

    request("/settings", "PUT", {"data": settings}, {"Authorization": f"Bearer {token}"})
    print(json.dumps(request("/settings", "GET"), indent=2))


if __name__ == "__main__":
    main()

