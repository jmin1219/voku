"""
Step 4: Sample Validation — run v2 extraction on full conversations.

Tests extraction quality at conversation scale:
- Proposition count per message (too many? too few?)
- Type distribution (healthy mix of stance/event/intention?)
- Story decomposition in the wild
- AI context utilization
- Voice preservation

Usage:
    cd backend && python -m spikes.s4_sample_validation
"""

import asyncio
import json
import sys
from pathlib import Path
from collections import Counter

sys.path.insert(0, str(Path(__file__).parent.parent / "app"))

from services.parser import ConversationParser
from services.extraction import ExtractionService
from services.providers.ollama_provider import OllamaProvider

FIXTURES_DIR = Path(__file__).parent.parent / "tests" / "fixtures" / "real"
MIN_LENGTH = 50

# 3 diverse conversations (ordered smallest first for rate limit friendliness)
SAMPLE_FILES = [
    "Overcoming Afternoon Procrastination Patterns.md",  # 3 msgs — Behavioral events
    "New Life in Vancouver.md",                          # 4 msgs — Story-heavy, emotional
    "Deep Research on Voku Plans.md",                    # 16 msgs — Technical stances, pushback
]


async def extract_conversation(parser, extractor, filepath):
    """Extract from all user messages in a conversation, passing AI context."""
    messages = parser.parse_file(filepath)
    results = []
    last_ai_text = None

    for msg in messages:
        if msg.speaker != "user":
            last_ai_text = msg.text.strip()[:2000] if msg.text else None
            continue

        if len(msg.text.strip()) < MIN_LENGTH:
            last_ai_text = None
            continue

        try:
            propositions = await extractor.extract(
                msg.text.strip(),
                ai_context=last_ai_text,
            )
            results.append({
                "message_index": msg.message_index,
                "message_preview": msg.text.strip()[:150],
                "propositions": [
                    {
                        "text": p.proposition,
                        "node_type": p.node_type,
                        "event_timeframe": p.event_timeframe,
                        "supersedable": p.supersedable,
                        "confidence": p.confidence,
                    }
                    for p in propositions
                ],
                "had_ai_context": last_ai_text is not None,
            })
        except Exception as e:
            results.append({
                "message_index": msg.message_index,
                "error": str(e),
            })

        last_ai_text = None
        # No throttle needed for local Ollama
        await asyncio.sleep(0.5)

    return results


async def run_validation():
    parser = ConversationParser()
    provider = OllamaProvider()
    extractor = ExtractionService(provider)

    print("=" * 80)
    print("STEP 4: SAMPLE VALIDATION — Full Conversation Extraction")
    print("=" * 80)

    all_propositions = []

    for filename in SAMPLE_FILES:
        filepath = FIXTURES_DIR / filename
        if not filepath.exists():
            print(f"\n⚠️  {filename} not found, skipping")
            continue

        print(f"\n{'─' * 80}")
        print(f"📄 {filename}")
        print(f"{'─' * 80}")

        results = await extract_conversation(parser, extractor, filepath)

        # Per-message report
        total_props = 0
        type_counts = Counter()
        timeframe_counts = Counter()
        supersedable_count = 0
        decomposition_signals = 0
        errors = 0

        for r in results:
            if "error" in r:
                errors += 1
                print(f"\n  ❌ msg[{r['message_index']}]: {r['error'][:80]}")
                continue

            props = r["propositions"]
            total_props += len(props)
            ctx = "🔗" if r["had_ai_context"] else "  "

            print(f"\n  {ctx} msg[{r['message_index']}] → {len(props)} props | {r['message_preview'][:80]}...")

            for p in props:
                type_counts[p["node_type"]] += 1
                if p["event_timeframe"]:
                    timeframe_counts[p["event_timeframe"]] += 1
                if p["supersedable"]:
                    supersedable_count += 1
                all_propositions.append(p)

                # Detect story decomposition (event + stance from same message)
                type_char = {"stance": "S", "event": "E", "intention": "I"}[p["node_type"]]
                tf = f"/{p['event_timeframe']}" if p["event_timeframe"] else ""
                sup = "⟳" if p["supersedable"] else "▪"
                print(f"      {type_char}{tf} {sup} ({p['confidence']:.1f}) {p['text'][:90]}")

            # Check for decomposition (same message has both event and stance)
            msg_types = set(p["node_type"] for p in props)
            if "event" in msg_types and "stance" in msg_types:
                decomposition_signals += 1

        # Conversation summary
        msgs_processed = len([r for r in results if "error" not in r])
        print(f"\n  ── Summary: {filename} ──")
        print(f"  Messages processed: {msgs_processed} | Errors: {errors}")
        print(f"  Total propositions: {total_props} ({total_props/max(msgs_processed,1):.1f} per message)")
        print(f"  Types: {dict(type_counts)}")
        print(f"  Timeframes: {dict(timeframe_counts)}")
        print(f"  Supersedable: {supersedable_count}/{total_props}")
        print(f"  Story decompositions detected: {decomposition_signals} messages")

    # Global summary
    global_types = Counter(p["node_type"] for p in all_propositions)
    global_tf = Counter(p["event_timeframe"] for p in all_propositions if p["event_timeframe"])
    global_sup = sum(1 for p in all_propositions if p["supersedable"])

    print(f"\n{'=' * 80}")
    print("GLOBAL VALIDATION SUMMARY")
    print(f"{'=' * 80}")
    print(f"Total propositions: {len(all_propositions)}")
    print(f"Type distribution: {dict(global_types)}")
    print(f"  stance: {global_types.get('stance', 0)/len(all_propositions)*100:.0f}%")
    print(f"  event:  {global_types.get('event', 0)/len(all_propositions)*100:.0f}%")
    print(f"  intention: {global_types.get('intention', 0)/len(all_propositions)*100:.0f}%")
    print(f"Timeframes: {dict(global_tf)}")
    print(f"Supersedable: {global_sup}/{len(all_propositions)} ({global_sup/len(all_propositions)*100:.0f}%)")

    # Health checks
    print(f"\n--- HEALTH CHECKS ---")
    stance_pct = global_types.get('stance', 0) / len(all_propositions) * 100
    event_pct = global_types.get('event', 0) / len(all_propositions) * 100
    intention_pct = global_types.get('intention', 0) / len(all_propositions) * 100

    if stance_pct < 15:
        print(f"⚠️  Stance proportion low ({stance_pct:.0f}%) — may not have enough for temporal thesis")
    elif stance_pct > 70:
        print(f"⚠️  Stance proportion high ({stance_pct:.0f}%) — events may be misclassified as stances")
    else:
        print(f"✅ Stance proportion healthy ({stance_pct:.0f}%)")

    if event_pct < 15:
        print(f"⚠️  Event proportion low ({event_pct:.0f}%)")
    else:
        print(f"✅ Event proportion healthy ({event_pct:.0f}%)")

    if intention_pct < 5:
        print(f"ℹ️  Intention proportion low ({intention_pct:.0f}%) — normal for non-planning conversations")
    else:
        print(f"✅ Intention proportion: {intention_pct:.0f}%")


if __name__ == "__main__":
    asyncio.run(run_validation())
