import anthropic
from dotenv import load_dotenv

load_dotenv()

client = anthropic.Anthropic()

with client.messages.stream(
    model="claude-sonnet-4-20250514",
    max_tokens=256,
    messages=[{"role": "user", "content": "What is motor learning in one paragraph?"}],
) as stream:
    for text in stream.text_stream:
        print(text, end="", flush=True)

print()  # final newline
