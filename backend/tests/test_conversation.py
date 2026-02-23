"""Tests for conversation persistence layer."""

import pytest

from services.conversation.service import ConversationService


@pytest.fixture
def service(tmp_path):
    """A ConversationService instance with a temporary database."""
    service = ConversationService(tmp_path / "test_conversations.db")
    yield service
    service.close()


def test_create_conversation(service):
    conv = service.create_conversation()
    assert conv is not None
    assert conv.created_at == conv.updated_at

    conversations = service.list_conversations()
    assert len(conversations) == 1
    assert conversations[0].id == conv.id


def test_add_user_message(service):
    conv = service.create_conversation()
    msg = service.add_message(conv.id, role="user", content="Hello, world!")
    assert msg is not None
    assert msg.conversation_id == conv.id
    assert msg.role == "user"
    assert msg.content == "Hello, world!"


def test_add_assistant_message_with_thinking(service):
    conv = service.create_conversation()
    msg = service.add_message(
        conv.id,
        role="assistant",
        content="Hi! How can I help you?",
        thinking="I should greet the user and ask how I can assist.",
    )
    assert msg is not None
    assert msg.conversation_id == conv.id
    assert msg.role == "assistant"
    assert msg.content == "Hi! How can I help you?"
    assert msg.thinking == "I should greet the user and ask how I can assist."


def test_messages_ordered_by_created_at(service):
    conv = service.create_conversation()
    service.add_message(conv.id, role="user", content="First message")
    service.add_message(conv.id, role="assistant", content="Second message")
    service.add_message(conv.id, role="user", content="Third message")

    messages = service.get_conversation_messages(conv.id)
    assert len(messages) == 3
    assert messages[0].content == "First message"
    assert messages[1].content == "Second message"
    assert messages[2].content == "Third message"


def test_list_conversations_most_recent_first(service):
    conv1 = service.create_conversation()
    conv2 = service.create_conversation()

    conversations = service.list_conversations()
    assert len(conversations) == 2
    assert conversations[0].id == conv2.id  # Most recent first
    assert conversations[1].id == conv1.id
