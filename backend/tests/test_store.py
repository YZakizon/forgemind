import asyncio
import json

from app.schemas import ProfileFactPolicyUpdate
from app.services.crypto import encrypt_text_for_user
from app.services import store


class FakeMappings:
    def __init__(self, rows=None):
        self.rows = rows or []

    def one(self):
        return self.rows[0]

    def one_or_none(self):
        return self.rows[0] if self.rows else None

    def __iter__(self):
        return iter(self.rows)


class FakeResult:
    rowcount = 0

    def __init__(self, rows=None, rowcount=0):
        self.rows = rows or []
        self.rowcount = rowcount

    def mappings(self):
        return FakeMappings(self.rows)


class FakeSession:
    def __init__(self, rows=None):
        self.rows = rows or []
        self.statements: list[str] = []
        self.params_history: list[dict] = []
        self.committed = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False

    async def execute(self, statement, params):
        self.statements.append(str(statement))
        self.params = params
        self.params_history.append(params)
        return FakeResult(self.rows)

    async def commit(self):
        self.committed = True


class MissingProfileFactsSession(FakeSession):
    async def execute(self, statement, params):
        self.statements.append(str(statement))
        self.params = params
        statement_text = str(statement)
        if "user_encryption_keys" in statement_text:
            return FakeResult()
        raise RuntimeError('UndefinedTableError: relation "profile_facts" does not exist')


def test_subscription_validation_store_sql_is_complete(monkeypatch):
    session = FakeSession()

    async def noop_ensure_demo_user(user_id: str) -> None:
        return None

    monkeypatch.setattr(store, "ensure_demo_user", noop_ensure_demo_user)
    monkeypatch.setattr(store, "get_sessionmaker", lambda: lambda: session)

    asyncio.run(
        store.save_subscription_validation(
            user_id="00000000-0000-4000-8000-000000000001",
            platform="apple",
            entitlement="premium",
            valid=True,
            store_transaction_id="purchase-token",
        )
    )

    statement = session.statements[0]
    assert "store_transaction_id" in statement
    assert "VALUES (" in statement
    assert ":store_transaction_id\n                )" in statement
    assert session.committed


def test_archive_user_memories_marks_active_memories_archived(monkeypatch):
    class ArchiveSession(FakeSession):
        async def execute(self, statement, params):
            self.statements.append(str(statement))
            self.params = params
            return FakeResult(rowcount=3)

    session = ArchiveSession()
    monkeypatch.setattr(store, "get_sessionmaker", lambda: lambda: session)

    archived = asyncio.run(store.archive_user_memories("00000000-0000-4000-8000-000000000001"))

    assert archived == 3
    assert "SET status = 'archived'" in session.statements[0]
    assert "archived_at" in session.statements[0]
    assert session.committed


def test_delete_user_data_clears_user_owned_tables(monkeypatch):
    session = FakeSession()
    monkeypatch.setattr(store, "get_sessionmaker", lambda: lambda: session)

    asyncio.run(store.delete_user_data("00000000-0000-4000-8000-000000000001"))

    joined = "\n".join(session.statements)
    for table in [
        "reset_sessions",
        "mood_checkins",
        "subscriptions",
        "safety_events",
        "profile_facts",
        "memories",
        "user_encryption_keys",
        "chat_messages",
        "chat_sessions",
    ]:
        assert f"DELETE FROM {table}" in joined
    assert session.committed


def test_delete_user_data_skips_missing_profile_facts_table(monkeypatch):
    class DeleteSession(FakeSession):
        async def execute(self, statement, params):
            statement_text = str(statement)
            self.statements.append(statement_text)
            self.params = params
            if "DELETE FROM profile_facts" in statement_text:
                raise RuntimeError('UndefinedTableError: relation "profile_facts" does not exist')
            return FakeResult()

    session = DeleteSession()
    monkeypatch.setattr(store, "get_sessionmaker", lambda: lambda: session)

    asyncio.run(store.delete_user_data("00000000-0000-4000-8000-000000000001"))

    assert "DELETE FROM profile_facts" in "\n".join(session.statements)
    assert session.committed


def test_list_user_profile_facts_returns_empty_when_table_is_missing(monkeypatch):
    session = MissingProfileFactsSession()
    monkeypatch.setattr(store, "get_sessionmaker", lambda: lambda: session)

    facts = asyncio.run(store.list_user_profile_facts("00000000-0000-4000-8000-000000000001"))

    assert facts == []
    assert not session.committed


def test_insert_profile_facts_skips_when_table_is_missing(monkeypatch):
    session = MissingProfileFactsSession()

    async def noop_ensure_demo_user(user_id: str) -> None:
        return None

    async def fake_dek(user_id: str):
        return b"0" * 32, "test-v1"

    monkeypatch.setattr(store, "ensure_demo_user", noop_ensure_demo_user)
    monkeypatch.setattr(store, "get_or_create_user_dek", fake_dek)
    monkeypatch.setattr(store, "get_sessionmaker", lambda: lambda: session)

    asyncio.run(
        store.insert_profile_facts(
            "00000000-0000-4000-8000-000000000001",
            [
                store.ExtractedProfileFact(
                    fact_type="preference",
                    label="tone",
                    value="direct",
                    sensitivity="normal",
                    source="chat",
                    confidence=0.7,
                    expires_at=store.datetime.now(store.UTC),
                )
            ],
        )
    )

    assert not session.committed


def test_profile_fact_row_decrypts_encrypted_value():
    user_id = "00000000-0000-4000-8000-000000000001"
    dek = b"1" * 32
    encrypted = encrypt_text_for_user(user_id, "profile_facts", "value", "bikes every weekend", dek, "test-v1")
    now = store.datetime.now(store.UTC)

    fact = store._profile_fact_from_row(
        {
            "id": "fact-1",
            "user_id": user_id,
            "fact_type": "habit",
            "label": "exercise",
            "value": "",
            "value_ciphertext": encrypted.ciphertext,
            "value_nonce": encrypted.nonce,
            "value_key_id": encrypted.key_id,
            "sensitivity": "normal",
            "source": "chat",
            "confidence": 0.8,
            "created_at": now,
            "updated_at": now,
            "expires_at": now,
        },
        dek=(dek, "test-v1"),
    )

    assert fact.value == "bikes every weekend"


def test_backfill_encrypts_plaintext_profile_facts(monkeypatch):
    user_id = "00000000-0000-4000-8000-000000000001"
    rows = [{"id": "fact-1", "user_id": user_id, "value": "bikes every weekend"}]
    select_session = FakeSession(rows)
    update_session = FakeSession()
    sessions = [select_session, update_session]

    async def fake_dek(selected_user_id: str):
        assert selected_user_id == user_id
        return b"2" * 32, "test-v1"

    monkeypatch.setattr(store, "get_or_create_user_dek", fake_dek)
    monkeypatch.setattr(store, "get_sessionmaker", lambda: lambda: sessions.pop(0))

    count = asyncio.run(store._backfill_profile_fact_values(limit=10))

    assert count == 1
    assert "UPDATE profile_facts" in update_session.statements[0]
    assert update_session.params["value_hash"]
    assert update_session.params["ciphertext"] != b"bikes every weekend"


def test_save_profile_fact_policy_normalizes_terms_and_ttls(monkeypatch):
    class PolicySession(FakeSession):
        async def execute(self, statement, params):
            self.statements.append(str(statement))
            self.params = params
            self.params_history.append(params)
            return FakeResult(
                [
                    {
                        "capture_terms": json.loads(params["capture_terms"]),
                        "blocked_terms": json.loads(params["blocked_terms"]),
                        "ttl_days_by_type": json.loads(params["ttl_days_by_type"]),
                    }
                ]
            )

    session = PolicySession()
    monkeypatch.setattr(store, "get_sessionmaker", lambda: lambda: session)

    policy = asyncio.run(
        store.save_profile_fact_policy(
            ProfileFactPolicyUpdate(
                capture_terms={"health_context": ["Migraine", "migraine"]},
                blocked_terms={"all": ["Password"]},
                ttl_days_by_type={"health_context": 12, "habit": 999},
            )
        )
    )

    assert policy.capture_terms["health_context"] == ["migraine"]
    assert policy.blocked_terms["all"] == ["password"]
    assert policy.ttl_days_by_type["health_context"] == 30
    assert policy.ttl_days_by_type["habit"] == 365
    assert "profile_fact_capture_policy" in session.statements[0]
