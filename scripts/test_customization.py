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
    try:
        resp = request(
            "/auth/register",
            "POST",
            {"full_name": "Test Editor", "email": EMAIL, "password": PASSWORD, "role": "editor"},
        )
    except Exception:
        resp = request("/auth/login", "POST", {"email": EMAIL, "password": PASSWORD})

    token = resp["access_token"]
    about = {
        "heroTitle": "From DB",
        "heroSubtitle": "Saved",
        "valuesTitle": "Vals",
        "values": [],
        "milestonesTitle": "Miles",
        "milestones": [],
        "teamTitle": "Team",
        "team": [],
        "previewImage": None,
        "previewImageAlt": "Alt",
        "previewEmoji": "X",
        "previewTitle": "Title",
    }

    request("/customization/about", "PUT", {"data": about}, {"Authorization": f"Bearer {token}"})
    print(json.dumps(request("/customization", "GET"), indent=2))


if __name__ == "__main__":
    main()

