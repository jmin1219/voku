from datetime import datetime
from pathlib import Path

from services.parser import ConversationParser

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "real"


def test_parse_single_conversation_basic():
    # Arrange
    parser = ConversationParser()
    filepath = FIXTURES_DIR / "Deep Research on Voku Plans.md"

    # Act
    messages = parser.parse_file(filepath)

    # Assert
    assert len(messages) > 0
    assert messages[0].speaker == "user"
    assert messages[1].speaker == "assistant"


def test_parse_base64_image_stripped():
    # Arrange
    parser = ConversationParser()
    filepath = FIXTURES_DIR / "Z2 Training Base Walking.md"

    # Act
    messages = parser.parse_file(filepath)
    usr_msg = messages[0]

    # Assert
    assert "base64" not in usr_msg.text
    assert "data:image" not in usr_msg.text

    assert "training protocol" in usr_msg.text


def test_parse_thinking_blocks_extracted():
    # Arrange
    parser = ConversationParser()
    filepath = FIXTURES_DIR / "Deep Research on Voku Plans.md"

    # Act
    messages = parser.parse_file(filepath)
    assistant_msg = [m for m in messages if m.speaker == "assistant"]
    first_msg = assistant_msg[0]

    # Assert
    assert "Thought process" not in first_msg.text

    assert first_msg.assistant_reasoning is not None
    assert "contextual information" in first_msg.assistant_reasoning

    user_msg = [m for m in messages if m.speaker == "user"]
    assert user_msg[0].assistant_reasoning is None


def test_parse_us_locale_timestamp():
    # Arrange
    parser = ConversationParser()
    filepath = FIXTURES_DIR / "Deep Research on Voku Plans.md"

    # Act
    messages = parser.parse_file(filepath)
    expected = datetime(2026, 2, 10, 21, 53, 12)  # Feb 10, 2026, 9:53:12 PM

    # Assert
    assert messages[0].timestamp == expected


def test_parse_session_id_from_link():
    # Arrange
    parser = ConversationParser()
    filepath = FIXTURES_DIR / "Deep Research on Voku Plans.md"

    # Act
    messages = parser.parse_file(filepath)

    # Assert
    assert messages[0].session_id == "9a9c2191-84b1-4e48-9906-76509116bc8b"

    for msg in messages:
        assert (
            msg.session_id == messages[0].session_id
        )  # All messages should have the same session ID


def test_parse_empty_messages_skipped():
    pass


def test_parse_directory():
    # Arrange
    parser = ConversationParser()

    messages = parser.parse_directory(FIXTURES_DIR)

    assert len(messages) > 0
    session_ids = set(m.session_id for m in messages)
    assert len(session_ids) == 3  # One per fixture file


def test_parse_footer_stripped():
    parser = ConversationParser()
    filepath = FIXTURES_DIR / "Deep Research on Voku Plans.md"

    messages = parser.parse_file(filepath)
    last_msg = messages[-1]

    assert "Claude Exporter" not in last_msg.text
    assert "ai-chat-exporter" not in last_msg.text


def test_roundtrip_known_output():
    # TODO: create small synthetic fixture with exact expected output
    pass


def test_char_offsets_match_source():
    parser = ConversationParser()
    filepath = FIXTURES_DIR / "Deep Research on Voku Plans.md"

    raw_text = filepath.read_text(encoding="utf-8")
    messages = parser.parse_file(filepath)

    for msg in messages:
        sliced = raw_text[msg.source_char_start:msg.source_char_end]
        assert msg.text in sliced
