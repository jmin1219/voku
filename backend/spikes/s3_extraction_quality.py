"""
Spike S3: Extraction quality on real conversation exports.

Question: Does the current extraction prompt work well on real user messages?
Method: Run extraction on 8 real user messages, evaluate proposition quality.
Success: Propositions are specific, voiced, non-redundant on real data.
Failure: Prompt needs significant rework before Milestone 1 build.
"""

import asyncio
import sys
import json

sys.path.insert(0, "app")

from pathlib import Path
from services.parser import ConversationParser
from services.extraction.extractor import ExtractionService
from services.providers.groq_provider import GroqProvider


async def run_spike():
    # Parse real conversations
    parser = ConversationParser()
    all_messages = parser.parse_directory(Path("tests/fixtures/real"))

    # Pick user messages only, with enough substance to extract from
    user_messages = [m for m in all_messages if m.speaker == "user" and len(m.text) > 50]

    # Sample 8 diverse messages (skip very short ones)
    sample = user_messages[:8]

    print(f"Testing extraction on {len(sample)} real user messages")
    print(f"Using Groq (llama-3.3-70b-versatile)")
    print("=" * 70)

    provider = GroqProvider()
    extractor = ExtractionService(provider)

    total_propositions = 0
    total_messages = 0

    for i, msg in enumerate(sample):
        print(f"\n{'─'*70}")
        print(f"MESSAGE {i+1} (from {msg.source_file}, index {msg.message_index})")
        print(f"Timestamp: {msg.timestamp}")
        print(f"Text ({len(msg.text)} chars):")
        # Show first 300 chars
        preview = msg.text[:300] + ("..." if len(msg.text) > 300 else "")
        print(f"  {preview}")
        print()

        try:
            propositions = await extractor.extract(msg.text)
            total_propositions += len(propositions)
            total_messages += 1

            print(f"  → Extracted {len(propositions)} propositions:")
            for j, p in enumerate(propositions):
                print(f"    [{j+1}] ({p.node_purpose}, {p.source_type}, conf={p.confidence})")
                print(f"        \"{p.proposition}\"")
                if p.structured_data:
                    print(f"        data: {json.dumps(p.structured_data, indent=None)[:100]}")
        except Exception as e:
            print(f"  → EXTRACTION FAILED: {e}")

    print(f"\n{'='*70}")
    print(f"SUMMARY")
    print(f"{'='*70}")
    print(f"Messages processed: {total_messages}/{len(sample)}")
    print(f"Total propositions: {total_propositions}")
    print(f"Avg per message:    {total_propositions/total_messages:.1f}" if total_messages else "N/A")
    print()
    print("QUALITY CHECKLIST (evaluate manually):")
    print("  [ ] Propositions are specific (not vague)")
    print("  [ ] User's voice preserved (not clinical)")
    print("  [ ] Non-redundant (no duplicates)")
    print("  [ ] Appropriate node_purpose labels")
    print("  [ ] structured_data used for metrics/numbers")
    print("  [ ] No hallucinated content")


if __name__ == "__main__":
    asyncio.run(run_spike())
