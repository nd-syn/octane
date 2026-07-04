"""Tests for the service layer. Uses an in-memory SQLite database."""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.asyncio
import pytest_asyncio
from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import get_settings
from app.core.exceptions import (
    CannotMessageSelf,
    ConversationNotFound,
    EmailTaken,
    InvalidCredentials,
    NotAMember,
    TokenExpired,
    TokenInvalid,
    UserNotFound,
    UsernameTaken,
)
from app.db.base import Base
from app.db.models import Conversation, ConversationMember, Message, User
from app.services.auth import AuthService
from app.services.conversation import ConversationService
from app.services.follow import FollowService
from app.services.message import MessageService
from app.services.user import UserService


@pytest_asyncio.fixture
async def engine():
    """Create an in-memory SQLite engine for testing."""
    e = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with e.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield e
    await e.dispose()


@pytest_asyncio.fixture
async def session(engine):
    """Create a fresh session for each test."""
    sm = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    async with sm() as s:
        yield s


@pytest_asyncio.fixture
async def auth(session):
    return AuthService(session)


@pytest_asyncio.fixture
async def user_svc(session):
    return UserService(session)


@pytest_asyncio.fixture
async def follow_svc(session):
    return FollowService(session)


@pytest_asyncio.fixture
async def conv_svc(session):
    return ConversationService(session)


@pytest_asyncio.fixture
async def msg_svc(session):
    return MessageService(session)


class TestAuthService:
    async def test_signup_and_login(self, auth, session):
        user, access_token, refresh_token = await auth.signup(
            username="alice",
            email="alice@test.com",
            password="password123",
            display_name="Alice",
        )
        assert user.id is not None
        assert user.username == "alice"
        assert access_token is not None
        assert refresh_token is not None

        user2, at2, rt2 = await auth.login(
            username="alice", password="password123"
        )
        assert user2.id == user.id

    async def test_signup_duplicate_username(self, auth):
        await auth.signup(
            username="alice",
            email="alice@test.com",
            password="password123",
        )
        with pytest.raises(UsernameTaken):
            await auth.signup(
                username="alice",
                email="alice2@test.com",
                password="password123",
            )

    async def test_signup_duplicate_email(self, auth):
        await auth.signup(
            username="alice",
            email="alice@test.com",
            password="password123",
        )
        with pytest.raises(EmailTaken):
            await auth.signup(
                username="bob",
                email="alice@test.com",
                password="password123",
            )

    async def test_login_invalid_password(self, auth):
        await auth.signup(
            username="alice",
            email="alice@test.com",
            password="password123",
        )
        with pytest.raises(InvalidCredentials):
            await auth.login(username="alice", password="wrongpassword")

    async def test_refresh_token(self, auth):
        user, at, rt = await auth.signup(
            username="alice",
            email="alice@test.com",
            password="password123",
        )
        user2, at2, rt2 = await auth.refresh(rt)
        assert user2.id == user.id

    async def test_logout_revokes_refresh(self, auth):
        user, at, rt = await auth.signup(
            username="alice",
            email="alice@test.com",
            password="password123",
        )
        await auth.logout(rt)
        with pytest.raises(TokenInvalid):
            await auth.refresh(rt)


class TestUserService:
    async def test_get_by_id(self, auth, user_svc, session):
        user, _, _ = await auth.signup(
            username="alice",
            email="alice@test.com",
            password="password123",
        )
        found = await user_svc.get_by_id(user.id)
        assert found.username == "alice"

    async def test_get_by_id_not_found(self, user_svc):
        with pytest.raises(UserNotFound):
            await user_svc.get_by_id(999)

    async def test_get_by_username(self, auth, user_svc):
        await auth.signup(
            username="alice",
            email="alice@test.com",
            password="password123",
        )
        found = await user_svc.get_by_username("alice")
        assert found.email == "alice@test.com"

    async def test_search(self, auth, user_svc):
        await auth.signup(username="alice", email="alice@test.com", password="password123")
        await auth.signup(username="bob", email="bob@test.com", password="password123")
        await auth.signup(username="charlie", email="charlie@test.com", password="password123")

        users, total = await user_svc.search("ali")
        assert total == 1
        assert users[0].username == "alice"

        users, total = await user_svc.search("b")
        assert total == 1

        users, total = await user_svc.search("z")
        assert total == 0

    async def test_update_profile(self, auth, user_svc, session):
        user, _, _ = await auth.signup(
            username="alice", email="alice@test.com", password="password123",
        )
        updated = await user_svc.update_profile(
            user, display_name="Alice Updated", bio="Hello!"
        )
        assert updated.display_name == "Alice Updated"
        assert updated.bio == "Hello!"


class TestFollowService:
    async def test_follow(self, auth, follow_svc):
        alice, _, _ = await auth.signup(
            username="alice", email="alice@test.com", password="password123",
        )
        bob, _, _ = await auth.signup(
            username="bob", email="bob@test.com", password="password123",
        )
        follow = await follow_svc.follow(alice, bob.id)
        assert follow.status == "accepted"

    async def test_follow_self(self, auth, follow_svc):
        alice, _, _ = await auth.signup(
            username="alice", email="alice@test.com", password="password123",
        )
        with pytest.raises(CannotMessageSelf):
            await follow_svc.follow(alice, alice.id)

    async def test_unfollow(self, auth, follow_svc):
        alice, _, _ = await auth.signup(
            username="alice", email="alice@test.com", password="password123",
        )
        bob, _, _ = await auth.signup(
            username="bob", email="bob@test.com", password="password123",
        )
        await follow_svc.follow(alice, bob.id)
        await follow_svc.unfollow(alice, bob.id)
        following, total = await follow_svc.get_following(alice)
        assert total == 0

    async def test_get_followers_and_following(self, auth, follow_svc):
        alice, _, _ = await auth.signup(
            username="alice", email="alice@test.com", password="password123",
        )
        bob, _, _ = await auth.signup(
            username="bob", email="bob@test.com", password="password123",
        )
        charlie, _, _ = await auth.signup(
            username="charlie", email="charlie@test.com", password="password123",
        )
        await follow_svc.follow(alice, bob.id)
        await follow_svc.follow(charlie, bob.id)

        followers, total = await follow_svc.get_followers(bob)
        assert total == 2

        await follow_svc.follow(bob, alice.id)
        following, total = await follow_svc.get_following(bob)
        assert total == 1


class TestConversationService:
    async def test_create_direct(self, auth, conv_svc):
        alice, _, _ = await auth.signup(
            username="alice", email="alice@test.com", password="password123",
        )
        bob, _, _ = await auth.signup(
            username="bob", email="bob@test.com", password="password123",
        )
        conv = await conv_svc.get_or_create_direct(alice, bob.id)
        assert conv.type == "direct"
        assert len(conv.members) == 2

    async def test_create_direct_with_self(self, auth, conv_svc):
        alice, _, _ = await auth.signup(
            username="alice", email="alice@test.com", password="password123",
        )
        with pytest.raises(CannotMessageSelf):
            await conv_svc.get_or_create_direct(alice, alice.id)

    async def test_create_direct_existing(self, auth, conv_svc):
        alice, _, _ = await auth.signup(
            username="alice", email="alice@test.com", password="password123",
        )
        bob, _, _ = await auth.signup(
            username="bob", email="bob@test.com", password="password123",
        )
        conv1 = await conv_svc.get_or_create_direct(alice, bob.id)
        conv2 = await conv_svc.get_or_create_direct(alice, bob.id)
        assert conv1.id == conv2.id

    async def test_list_conversations(self, auth, conv_svc):
        alice, _, _ = await auth.signup(
            username="alice", email="alice@test.com", password="password123",
        )
        bob, _, _ = await auth.signup(
            username="bob", email="bob@test.com", password="password123",
        )
        charlie, _, _ = await auth.signup(
            username="charlie", email="charlie@test.com", password="password123",
        )
        await conv_svc.get_or_create_direct(alice, bob.id)
        await conv_svc.get_or_create_direct(alice, charlie.id)

        convs, total = await conv_svc.list_conversations(alice)
        assert total == 2

    async def test_get_conversation_not_member(self, auth, conv_svc):
        alice, _, _ = await auth.signup(
            username="alice", email="alice@test.com", password="password123",
        )
        bob, _, _ = await auth.signup(
            username="bob", email="bob@test.com", password="password123",
        )
        charlie, _, _ = await auth.signup(
            username="charlie", email="charlie@test.com", password="password123",
        )
        conv = await conv_svc.get_or_create_direct(alice, bob.id)
        with pytest.raises(NotAMember):
            await conv_svc.get_conversation(conv.id, charlie)


class TestMessageService:
    async def test_send_and_get_messages(self, auth, conv_svc, msg_svc):
        alice, _, _ = await auth.signup(
            username="alice", email="alice@test.com", password="password123",
        )
        bob, _, _ = await auth.signup(
            username="bob", email="bob@test.com", password="password123",
        )
        conv = await conv_svc.get_or_create_direct(alice, bob.id)

        msg = await msg_svc.send_message(conv.id, alice, "Hello Bob!")
        assert msg.sender_id == alice.id
        assert msg.conversation_id == conv.id

        msg2 = await msg_svc.send_message(conv.id, bob, "Hey Alice!")
        assert msg2.sender_id == bob.id

        messages, total = await msg_svc.get_messages(conv.id, alice)
        assert total == 2
        assert len(messages) == 2

    async def test_send_to_nonexistent_conversation(self, msg_svc, auth):
        alice, _, _ = await auth.signup(
            username="alice", email="alice@test.com", password="password123",
        )
        with pytest.raises(ConversationNotFound):
            await msg_svc.send_message(999, alice, "Hello!")

    async def test_delete_message(self, auth, conv_svc, msg_svc):
        alice, _, _ = await auth.signup(
            username="alice", email="alice@test.com", password="password123",
        )
        bob, _, _ = await auth.signup(
            username="bob", email="bob@test.com", password="password123",
        )
        conv = await conv_svc.get_or_create_direct(alice, bob.id)
        msg = await msg_svc.send_message(conv.id, alice, "Hello Bob!")
        await msg_svc.delete_message(conv.id, msg.id, alice)

        messages, total = await msg_svc.get_messages(conv.id, alice)
        assert total == 0

    async def test_message_encryption(self, auth, conv_svc, msg_svc):
        """Verify messages are encrypted at rest in the database."""
        alice, _, _ = await auth.signup(
            username="alice", email="alice@test.com", password="password123",
        )
        bob, _, _ = await auth.signup(
            username="bob", email="bob@test.com", password="password123",
        )
        conv = await conv_svc.get_or_create_direct(alice, bob.id)
        await msg_svc.send_message(conv.id, alice, "Secret message")

        msg_db = await msg_svc.session.get(Message, 1)
        assert msg_db is not None
        assert msg_db.ciphertext != b"Secret message"
        assert len(msg_db.ciphertext) > 0

        content = await msg_svc.decrypt_message_content(conv, msg_db)
        assert content == "Secret message"

    async def test_mark_read(self, auth, conv_svc, msg_svc):
        alice, _, _ = await auth.signup(
            username="alice", email="alice@test.com", password="password123",
        )
        bob, _, _ = await auth.signup(
            username="bob", email="bob@test.com", password="password123",
        )
        conv = await conv_svc.get_or_create_direct(alice, bob.id)
        msg = await msg_svc.send_message(conv.id, alice, "Hello!")

        await msg_svc.mark_read(conv.id, msg.id, bob)
        unread = await conv_svc.get_unread_count(conv.id, bob.id)
        assert unread == 0
