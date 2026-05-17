from fastapi.testclient import TestClient

from app.main import app
from app.services.auth import DEMO_USER_ID, issue_access_token
from app.schemas import DataControlResponse, UserDataExport
from app.services import store


client = TestClient(app)


def bearer(user_id: str = DEMO_USER_ID) -> dict[str, str]:
    return {"Authorization": f"Bearer {issue_access_token(user_id)}"}


def test_data_controls_require_authentication():
    response = client.get(f"/users/{DEMO_USER_ID}/export")
    assert response.status_code == 401


def test_data_controls_reject_mismatched_user(monkeypatch):
    async def fake_export(user_id: str) -> UserDataExport:
        return UserDataExport(user_id=user_id)

    monkeypatch.setattr(store, "export_user_data", fake_export)

    other_user = "00000000-0000-4000-8000-000000000002"
    response = client.get(f"/users/{DEMO_USER_ID}/export", headers=bearer(other_user))

    assert response.status_code == 403


def test_data_controls_allow_matching_token(monkeypatch):
    async def fake_archive(user_id: str) -> int:
        assert user_id == DEMO_USER_ID
        return 2

    monkeypatch.setattr(store, "archive_user_memories", fake_archive)

    response = client.post(f"/memories/archive?user_id={DEMO_USER_ID}", headers=bearer())

    assert response.status_code == 200
    assert DataControlResponse(**response.json()).detail == "Archived 2 active memories."


def test_demo_login_issues_demo_user_token():
    response = client.post("/auth/login", json={"provider": "google", "identity_token": "demo-token"})

    assert response.status_code == 200
    assert response.json()["user_id"] == DEMO_USER_ID
