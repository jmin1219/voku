"""
Golden set queries for Phase 2 retrieval evaluation.

Each query has:
- query: the natural language question
- expected_texts: substrings that MUST appear in top-k results
- excluded_texts: substrings that should NOT appear in top-k (noise check)
- k: how many results to check (default 5)
- test_type: what aspect of retrieval this tests

Categories:
- factual_recall: can we find known facts?
- stance_query: can we find beliefs/positions?
- temporal_evolution: do temporal queries surface change over time?
- topic_timeline: does retrieve_for_topic return correct current + history?
- supersession: does the system correctly identify superseded beliefs?
"""

GOLDEN_SET = [
    # --- FACTUAL RECALL ---
    {
        "id": "GS01",
        "query": "Where does the user live?",
        "expected_texts": ["Vancouver"],
        "excluded_texts": [],
        "k": 5,
        "test_type": "factual_recall",
    },
    {
        "id": "GS02",
        "query": "What is the user's educational background?",
        "expected_texts": ["Northeastern", "Columbia"],
        "excluded_texts": [],
        "k": 5,
        "test_type": "factual_recall",
    },
    {
        "id": "GS03",
        "query": "What is the user's net worth or financial situation?",
        "expected_texts": ["220K"],
        "excluded_texts": [],
        "k": 5,
        "test_type": "factual_recall",
    },

    # --- STANCE QUERIES ---
    {
        "id": "GS04",
        "query": "What does the user think about time-blocking?",
        "expected_texts": ["time-blocking", "willpower"],
        "excluded_texts": [],
        "k": 5,
        "test_type": "stance_query",
    },
    {
        "id": "GS05",
        "query": "What is the user's north star or life purpose?",
        "expected_texts": ["build tools", "see themselves"],
        "excluded_texts": [],
        "k": 5,
        "test_type": "stance_query",
    },
    {
        "id": "GS06",
        "query": "What database does the user prefer for their project?",
        "expected_texts": ["SQLite"],
        "excluded_texts": [],
        "k": 5,
        "test_type": "stance_query",
    },

    # --- TEMPORAL EVOLUTION ---
    {
        "id": "GS07",
        "query": "How has the user's social life changed since moving?",
        "expected_texts": ["lonely", "climbing"],
        "excluded_texts": [],
        "k": 10,
        "test_type": "temporal_evolution",
        "notes": "Should surface Sep 2025 loneliness AND Jan 2026 climbing gym intention",
    },
    {
        "id": "GS08",
        "query": "How has the user's project evolved over time?",
        "expected_texts": ["Billy", "Voku"],
        "excluded_texts": [],
        "k": 10,
        "test_type": "temporal_evolution",
        "notes": "Should surface BillyOS (Dec 2025) through Voku (Feb 2026)",
    },

    # --- TOPIC TIMELINE ---
    {
        "id": "GS09",
        "query": "breathing technique for exercise",
        "expected_texts": ["breathing", "nasal"],
        "excluded_texts": [],
        "k": 5,
        "test_type": "topic_timeline",
        "notes": "Oct 2025: nasal breathing priority. Feb 2026: inhalation-expansion revised.",
    },
    {
        "id": "GS10",
        "query": "afternoon productivity and energy",
        "expected_texts": ["murk"],
        "excluded_texts": [],
        "k": 5,
        "test_type": "stance_query",
    },

    # --- SUPERSESSION ---
    {
        "id": "GS11",
        "query": "What does the user think about interest rates and currency?",
        "expected_texts": ["interest rate"],
        "excluded_texts": [],
        "k": 5,
        "test_type": "supersession",
        "notes": "Prop 56 is superseded_in_conversation. Should appear but flagged.",
    },

    # --- TEMPORAL WEIGHTING ---
    {
        "id": "GS12",
        "query": "What is the user currently working on?",
        "expected_texts": ["Voku"],
        "excluded_texts": [],
        "k": 5,
        "test_type": "temporal_weighting",
        "notes": "With temporal weight, Voku (Feb 2026) should rank above BillyOS (Dec-Jan). Without temporal weight, BillyOS may dominate due to more propositions.",
    },
    {
        "id": "GS13",
        "query": "What is the user's training program?",
        "expected_texts": ["breathing", "balance"],
        "excluded_texts": [],
        "k": 5,
        "test_type": "temporal_weighting",
        "notes": "With temporal weight, Feb 2026 training updates should rank above Sep 2025.",
    },

    # --- NOISE RESISTANCE ---
    {
        "id": "GS14",
        "query": "What are the user's cooking preferences?",
        "expected_texts": ["chicken"],
        "excluded_texts": ["time-blocking", "breathing", "Voku"],
        "k": 5,
        "test_type": "noise_resistance",
        "notes": "Should find the meal prep props, not unrelated stances.",
    },
]
