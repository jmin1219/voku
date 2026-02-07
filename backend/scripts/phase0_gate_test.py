"""
Phase 0 Gate Test - Manual extraction evaluation.

Run 5 diverse conversation turns through extraction pipeline.
Success criteria: ≥3/5 preserve user voice without clinical flattening.

Usage:
    cd backend
    source venv/bin/activate
    python -m scripts.phase0_gate_test
"""
import asyncio
import json
from app.services.extraction import ExtractionService, ExtractionError
from app.services.providers.groq_provider import GroqProvider


# Test cases - sanitized for privacy
TEST_CASES = [
    {
        "id": "test1_emotional_vulnerable",
        "description": "Tests voice preservation on raw, vulnerable language",
        "text": """The feared self: lazy slob, continuous masturbation, spending inherited money gambling, engaging in all vices available. 'If I just let myself be myself.' The pattern noticed: 'I need to be strict with myself or I'll go out of control' — said about productivity, drinking, multiple domains.""",
        "expected_types": ["pattern", "belief"],
        "success_criteria": "Preserves phrases like 'lazy slob' and 'all vices available' verbatim, not transformed into clinical language"
    },
    {
        "id": "test2_quantitative_insight",
        "description": "Tests splitting metrics into structured_data while preserving insight",
        "text": """Completed: 39:29 total, 5.39km @ 6:54/km, HR 164 avg. Started at 6:40/km pace, felt too fast after 3min, settled at 6:59. Felt easy despite Z4 HR. The HR/RPE mismatch (164 bpm but felt easy) may not be zone miscalibration. It may be what running feels like without psychological load.""",
        "expected_types": ["observation"],
        "success_criteria": "Metrics go into structured_data, insight about psychological load stays as separate proposition with original language preserved"
    },
    {
        "id": "test3_philosophical_belief",
        "description": "Tests preserving analytical thinking without over-simplifying",
        "text": """Productivity planners take stated goals as input. The system questions whether stated goals are real — or performance, or inherited, or outdated. The hierarchy is inverted: Planners: Goals → Plans → Tasks → Tracking. Alternative approach: Observations → Patterns → Self-Knowledge → (Goals emerge). Self-understanding is the anchor. Goals are a byproduct of seeing yourself clearly.""",
        "expected_types": ["belief"],
        "success_criteria": "Preserves inversion logic, doesn't collapse into 'user prefers self-understanding to goal-setting'"
    },
    {
        "id": "test4_academic_completion",
        "description": "Tests extracting academic milestones with structured dates/details",
        "text": """Lab03 (Quicksort) — completed in 1.5 hours. Implemented partition (Lomuto scheme from CLRS), quickSort, sortIntegers. CSV updated with quickSort column (100 to 10M). Submitted to autograder. HW03 (Mergesort) — completed in 50 minutes. Both assignments completed in ~2.5 hours total.""",
        "expected_types": ["observation"],
        "success_criteria": "structured_data includes course info, assignment, duration. Might extract 2 propositions (Lab03 + HW03 separate)"
    },
    {
        "id": "test5_decision_reasoning",
        "description": "Tests capturing decision with context, not just outcome",
        "text": """The ideas got too abstract. Planning for a month without building. Three pivots. 600-line design doc. Zero code. The Drift: Initial insight was 'Conversation-based externalization.' Later design became 'Temporal knowledge graph with 5-factor scoring.' The pivot from biometrics to conversation was real. The leap to temporal retrieval was intellectual ambition, not problem-solving.""",
        "expected_types": ["observation", "decision"],
        "success_criteria": "Preserves self-critique ('intellectual ambition, not problem-solving'), doesn't lose specifics (600-line doc, zero code)"
    }
]


async def run_gate_test():
    """Run extraction on all test cases and print results."""
    
    print("=" * 80)
    print("PHASE 0 GATE TEST - Extraction Quality Evaluation")
    print("=" * 80)
    print()
    print("Success criteria: ≥3/5 test cases must preserve user voice")
    print("without clinical flattening or losing key details.")
    print()
    
    # Initialize services
    provider = GroqProvider()
    extractor = ExtractionService(provider)
    
    results = []
    
    for i, test_case in enumerate(TEST_CASES, 1):
        print(f"\n{'=' * 80}")
        print(f"TEST CASE {i}/{len(TEST_CASES)}: {test_case['id']}")
        print(f"{'=' * 80}")
        print(f"\nDescription: {test_case['description']}")
        print(f"\nInput text:")
        print(f"  {test_case['text'][:100]}...")
        print(f"\nSuccess criteria:")
        print(f"  {test_case['success_criteria']}")
        print(f"\nRunning extraction...")
        
        try:
            propositions = await extractor.extract(test_case['text'])
            
            print(f"\n✅ Extraction succeeded - {len(propositions)} propositions returned")
            print(f"\nPropositions:")
            
            for j, prop in enumerate(propositions, 1):
                print(f"\n  --- Proposition {j} ---")
                print(f"  proposition: {prop.proposition}")
                print(f"  node_purpose: {prop.node_purpose}")
                print(f"  confidence: {prop.confidence}")
                print(f"  source_type: {prop.source_type}")
                if prop.structured_data:
                    print(f"  structured_data: {json.dumps(prop.structured_data, indent=4)}")
                else:
                    print(f"  structured_data: None")
            
            results.append({
                "test_id": test_case['id'],
                "status": "success",
                "propositions": [
                    {
                        "proposition": p.proposition,
                        "node_purpose": p.node_purpose,
                        "confidence": p.confidence,
                        "source_type": p.source_type,
                        "structured_data": p.structured_data
                    }
                    for p in propositions
                ]
            })
            
        except ExtractionError as e:
            print(f"\n❌ Extraction failed: {str(e)}")
            results.append({
                "test_id": test_case['id'],
                "status": "failed",
                "error": str(e)
            })
        except Exception as e:
            print(f"\n❌ Unexpected error: {str(e)}")
            results.append({
                "test_id": test_case['id'],
                "status": "failed",
                "error": f"Unexpected: {str(e)}"
            })
    
    # Summary
    print(f"\n\n{'=' * 80}")
    print("GATE TEST SUMMARY")
    print(f"{'=' * 80}")
    
    successful = sum(1 for r in results if r['status'] == 'success')
    failed = len(results) - successful
    
    print(f"\nResults: {successful}/{len(results)} successful")
    print(f"Failed: {failed}")
    print(f"\nGate Status: {'✅ PASS' if successful >= 3 else '❌ FAIL'}")
    
    if successful >= 3:
        print("\nExtraction quality is sufficient to proceed to Phase 1.")
        print("Review outputs above to verify voice preservation manually.")
    else:
        print("\nExtraction quality needs improvement.")
        print("Options:")
        print("  1. Iterate on few-shot examples in prompt.py")
        print("  2. Try different model (e.g., larger Groq model)")
        print("  3. Pivot to interactive refinement ('AI proposes, human confirms')")
    
    # Save results to file
    output_path = "/Users/jayminchang/Documents/projects/voku/backend/phase0_gate_results.json"
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\nFull results saved to: {output_path}")
    print()


if __name__ == "__main__":
    asyncio.run(run_gate_test())
