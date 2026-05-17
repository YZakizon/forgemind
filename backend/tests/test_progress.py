from datetime import UTC, datetime

from app.main import progress_summary
from app.schemas import MoodCheckin
from app.services.store import _progress_themes_from_checkins


def checkin(label: str) -> MoodCheckin:
    return MoodCheckin(
        id=f"id-{label}",
        user_id="00000000-0000-4000-8000-000000000001",
        label=label,
        intensity=7,
        created_at=datetime.now(UTC),
    )


def test_progress_summary_falls_back_when_store_unavailable():
    summary = progress_summary("user-1")
    assert summary.user_id == "user-1"
    assert summary.themes == []


def test_progress_themes_are_derived_from_recent_checkins():
    themes = _progress_themes_from_checkins(
        [
            checkin("Work pressure"),
            checkin("Work pressure"),
            checkin("Sleep"),
        ]
    )
    assert themes[0].label == "Work pressure"
    assert themes[0].tone == "High"
    assert themes[1].label == "Sleep"
