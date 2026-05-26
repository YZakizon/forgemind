import asyncio

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
    def __init__(self):
        self.statements: list[str] = []
        self.committed = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False

    async def execute(self, statement, params):
        self.statements.append(str(statement))
        self.params = params
        return FakeResult()

    async def commit(self):
        self.committed = True


class MissingProfileFactsSession(FakeSession):
    async def execute(self, statement, params):
        self.statements.append(str(statement))
        self.params = params
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
        "chat_messages",
        "chat_sessions",
    ]:
        assert f"DELETE FROM {table}" in joined
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

    monkeypatch.setattr(store, "ensure_demo_user", noop_ensure_demo_user)
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
