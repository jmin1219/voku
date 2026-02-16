"""
Spike S4b: Node Type Classification Accuracy

Tests whether the v2 extraction prompt can reliably classify propositions
into stance/event/intention with correct event_timeframe and supersedable.

Approach:
1. 10 diverse real user messages, hand-labeled ground truth
2. Run new extraction prompt via Groq on each
3. Compare: node_type accuracy, supersedable accuracy, decomposition quality
4. Gate: <65% three-way → fall back to binary supersedable

Usage:
    cd backend && python -m spikes.s4b_node_type_classification
"""

import asyncio
import json
import sys
from pathlib import Path
from dataclasses import dataclass

sys.path.insert(0, str(Path(__file__).parent.parent / "app"))

from services.extraction import ExtractionService
from services.providers.groq_provider import GroqProvider


@dataclass
class GroundTruth:
    """Expected proposition from a user message."""
    text_fragment: str  # Key phrase to match against extracted proposition
    node_type: str  # stance | event | intention
    supersedable: bool
    event_timeframe: str | None = None  # recent | historical | ongoing


# ── 10 Diverse Test Messages with Ground Truth ─────────────────────

TEST_CASES = [
    {
        "id": "loneliness_vancouver",
        "source": "New Life in Vancouver.md:0",
        "message": "It's a bit of a lonely night. It's 10:27pm on saturday sep 27. As you know I just moved to vancouver. I dont know anyone here. I dont have habits. Before moving here, I would hang out multiple times a week with friends or the people I spent most time with were within my apartment. It's really weird being completely independent and alone.",
        "ground_truth": [
            GroundTruth("just moved to vancouver", "event", False, "recent"),
            GroundTruth("don't know anyone", "event", False, "recent"),
            GroundTruth("don't have habits", "event", False, "recent"),
            GroundTruth("hang out multiple times a week with friends", "event", False, "historical"),
            GroundTruth("weird being completely independent and alone", "stance", True),
        ],
    },
    {
        "id": "behavioral_change",
        "source": "New Life in Vancouver.md:2",
        "message": "I was never the type of person to explore areas or go into shops alone. Today and the recent month after moving has changed things for me. I've been taking a lot of walks and shopping alone. I haven't gone out by myself to a restaurant or bar yet. Even going to the gym the first time was a big step that I'm proud of taking.",
        "ground_truth": [
            GroundTruth("never the type of person to explore areas or go into shops alone", "event", False, "historical"),
            GroundTruth("been taking a lot of walks and shopping alone", "event", False, "recent"),
            GroundTruth("haven't gone out by myself to a restaurant or bar", "event", False, "recent"),
            GroundTruth("going to the gym the first time was a big step", "event", False, "recent"),
            GroundTruth("proud of taking", "stance", True),
        ],
    },
    {
        "id": "operational_continue",
        "source": "Billy OS Development New Year's Eve.md:0",
        "message": "Its 3:50pm Wed Dec 31. I want to continue working on Billy OS. what do you think based on what you know about my current overall context",
        "ground_truth": [
            GroundTruth("continue working on Billy OS", "intention", False),
        ],
    },
    {
        "id": "pushback_demo",
        "source": "Deep Research on Voku Plans.md:4",
        "message": "you keep focusing on the demo timeline. I feel like having big picture matters more. all demos suck. you also keep bringing up not having to use graph database. sure maybe you have a point. i dont want to make decisions based on what easy. I want to make decisions based on what's right for the long term vision.",
        "ground_truth": [
            GroundTruth("big picture matters more", "stance", True),
            GroundTruth("all demos suck", "stance", True),
            GroundTruth("don't want to make decisions based on what's easy", "stance", True),
            GroundTruth("decisions based on what's right for the long term vision", "stance", True),
        ],
    },
    {
        "id": "priorities_skewed",
        "source": "Feature 8 Understanding Through Chaos.md:2",
        "message": "nothing. I just feel like my priorities have been skewed the past few days. maybe i let you listen to my orders too much. maybe you deserve a bit more say in what I plan to do.",
        "ground_truth": [
            GroundTruth("priorities have been skewed the past few days", "stance", True),
            GroundTruth("let you listen to my orders too much", "stance", True),
            GroundTruth("you deserve a bit more say in what I plan to do", "stance", True),
        ],
    },
    {
        "id": "hr_zone_correction",
        "source": "ATLAS System Startup.md:10",
        "message": "well you did tell me to target 150-155 so i thought i was supposed to go zone 3. I did finish the entire session with nasal breathing",
        "ground_truth": [
            GroundTruth("told me to target 150-155", "event", False, "recent"),
            GroundTruth("thought i was supposed to go zone 3", "stance", True),
            GroundTruth("finished the entire session with nasal breathing", "event", False, "recent"),
        ],
    },
    {
        "id": "trading_identity",
        "source": "New Year's Eve Money Talk.md:10",
        "message": "1. i think i see myself being a swing or longer timeframe trader consistently. i think i can take advantage of my ADHD like mind that has many interests. The role of money in this world matches my first principle of freedom.",
        "ground_truth": [
            GroundTruth("swing or longer timeframe trader", "stance", True),
            GroundTruth("take advantage of my ADHD like mind", "stance", True),
            GroundTruth("role of money in this world matches my first principle of freedom", "stance", True),
        ],
    },
    {
        "id": "afternoon_scrolling",
        "source": "Overcoming Afternoon Procrastination Patterns.md:0",
        "message": "It's now Jan 2 3:36pm. review system logs. I just got done having lunch and watching TV. Then I thought about my murky afternoons so stood up to get to work. instead I did some spontaneous chores and now I'm here. update daily log",
        "ground_truth": [
            GroundTruth("done having lunch and watching TV", "event", False, "recent"),
            GroundTruth("thought about my murky afternoons", "event", False, "recent"),
            GroundTruth("did some spontaneous chores", "event", False, "recent"),
        ],
    },
    {
        "id": "coping_mechanism",
        "source": "Solitude After Family Visit.md:2",
        "message": "I need a new starting point. I usually cope or get out of these positions by planning for the future.",
        "ground_truth": [
            GroundTruth("need a new starting point", "intention", False),
            GroundTruth("cope or get out of these positions by planning for the future", "stance", True),
        ],
    },
    {
        "id": "cooking_independence",
        "source": "Beginner's Meal Prep Guide.md:0",
        "message": "I'm trying to get into more cooking and meal prepping as I begin to live alone. I also want to get closer to my miele oven system. The oven system has its own baking tray and the resting grid thing you put inside the oven.",
        "ground_truth": [
            GroundTruth("get into more cooking and meal prepping", "intention", False),
            GroundTruth("begin to live alone", "event", False, "recent"),
            GroundTruth("get closer to my miele oven system", "intention", False),
        ],
    },
]


def match_proposition_to_ground_truth(
    extracted_text: str, ground_truths: list[GroundTruth]
) -> GroundTruth | None:
    """Find the best matching ground truth for an extracted proposition."""
    extracted_lower = extracted_text.lower()
    best_match = None
    best_overlap = 0

    for gt in ground_truths:
        # Check if ground truth key phrase appears in extracted text
        if gt.text_fragment.lower() in extracted_lower:
            overlap = len(gt.text_fragment)
            if overlap > best_overlap:
                best_overlap = overlap
                best_match = gt

    return best_match


async def run_spike():
    provider = GroqProvider()
    extractor = ExtractionService(provider)

    print("=" * 80)
    print("SPIKE S4b: NODE TYPE CLASSIFICATION ACCURACY")
    print("=" * 80)

    total_gt = 0
    type_correct = 0
    type_total = 0
    supersedable_correct = 0
    supersedable_total = 0
    timeframe_correct = 0
    timeframe_total = 0
    unmatched_extracted = 0
    unmatched_gt = 0

    for case in TEST_CASES:
        print(f"\n--- {case['id']} ({case['source']}) ---")
        print(f"  Message: {case['message'][:120]}...")

        try:
            propositions = await extractor.extract(case["message"])
        except Exception as e:
            print(f"  ❌ EXTRACTION FAILED: {e}")
            continue

        print(f"  Extracted {len(propositions)} propositions (expected {len(case['ground_truth'])})")

        gt_matched = set()
        total_gt += len(case["ground_truth"])

        for prop in propositions:
            match = match_proposition_to_ground_truth(prop.proposition, case["ground_truth"])

            if match is None:
                print(f"    ⚪ UNMATCHED: [{prop.node_type}] {prop.proposition[:80]}")
                unmatched_extracted += 1
                continue

            gt_idx = case["ground_truth"].index(match)
            gt_matched.add(gt_idx)

            # Node type accuracy
            type_total += 1
            type_ok = prop.node_type == match.node_type
            if type_ok:
                type_correct += 1

            # Supersedable accuracy
            supersedable_total += 1
            sup_ok = prop.supersedable == match.supersedable
            if sup_ok:
                supersedable_correct += 1

            # Event timeframe accuracy (events only)
            if match.node_type == "event" and match.event_timeframe:
                timeframe_total += 1
                tf_ok = prop.event_timeframe == match.event_timeframe
                if tf_ok:
                    timeframe_correct += 1
            else:
                tf_ok = None

            status = "✅" if type_ok else "❌"
            sup_status = "✅" if sup_ok else "❌"
            tf_str = f" tf:{prop.event_timeframe}{'✅' if tf_ok else '❌' if tf_ok is not None else ''}" if prop.node_type == "event" else ""

            print(f"    {status} type:{prop.node_type}(exp:{match.node_type}) "
                  f"{sup_status} sup:{prop.supersedable}(exp:{match.supersedable}){tf_str}")
            print(f"       → {prop.proposition[:80]}")

        # Count unmatched ground truths
        for i, gt in enumerate(case["ground_truth"]):
            if i not in gt_matched:
                unmatched_gt += 1
                print(f"    🔴 MISSED GT: [{gt.node_type}] {gt.text_fragment}")

    # Summary
    print(f"\n{'=' * 80}")
    print("SPIKE S4b RESULTS")
    print(f"{'=' * 80}")
    print(f"\nNode type accuracy:    {type_correct}/{type_total} = {type_correct/type_total*100:.1f}%" if type_total else "N/A")
    print(f"Supersedable accuracy: {supersedable_correct}/{supersedable_total} = {supersedable_correct/supersedable_total*100:.1f}%" if supersedable_total else "N/A")
    print(f"Timeframe accuracy:    {timeframe_correct}/{timeframe_total} = {timeframe_correct/timeframe_total*100:.1f}%" if timeframe_total else "N/A")
    print(f"\nUnmatched extracted: {unmatched_extracted} (props with no ground truth match)")
    print(f"Missed ground truth: {unmatched_gt}/{total_gt} (expected props not found)")

    print(f"\n--- GATE CHECK ---")
    if type_total > 0:
        type_pct = type_correct / type_total * 100
        sup_pct = supersedable_correct / supersedable_total * 100 if supersedable_total else 0
        if type_pct >= 65:
            print(f"✅ Three-way classification: {type_pct:.1f}% >= 65% threshold. PROCEED with trichotomy.")
        elif sup_pct >= 80:
            print(f"⚠️  Three-way: {type_pct:.1f}% < 65%. But supersedable: {sup_pct:.1f}% >= 80%. FALLBACK to binary.")
        else:
            print(f"❌ Three-way: {type_pct:.1f}% < 65%. Supersedable: {sup_pct:.1f}% < 80%. RETHINK needed.")


if __name__ == "__main__":
    asyncio.run(run_spike())
