"""Test LLM proposition extraction with Groq provider."""

import asyncio
import json
import sys
from pathlib import Path

# Add the app directory to path so we can import services
sys.path.insert(0, str(Path(__file__).parent / "app"))

from services.providers.groq_provider import GroqProvider


async def test_extraction():
    """Send a test conversation turn to Groq and parse the response."""
    
    provider = GroqProvider()
    
    # Test conversation turn
    turn_content = """
    Did a 5K run today, 24:30. Used negative splits—really helped 
    me finish strong. I think starting too fast burns me out, but 
    pacing with the first mile slow fixed it. Felt great.
    """
    
    # Build extraction prompt based on DESIGN_V03.md section 7.1
    prompt = f"""Given this conversation turn from the user:
"{turn_content.strip()}"

Context from recent conversation:
"User has been training for running consistently, focusing on improving 5K times."

Research depth: 5 (0=minimal, 10=maximum extraction)

Extract atomic propositions. Each proposition should:
- Be self-contained (understandable without context)
- Replace pronouns with explicit references ("I" → "User")
- Contain ONE claim, fact, preference, or insight
- Be 20-80 words

Return ONLY valid JSON in this exact format:
{{
  "propositions": [
    {{
      "content": "...",
      "title": "descriptive-kebab-case-title",
      "type": "fact|belief|preference|goal|insight|decision",
      "confidence": 0.0-1.0,
      "temporal_marker": "ongoing|point-in-time|null"
    }}
  ],
  "store_decision": true,
  "skip_reason": ""
}}

Be precise. Use lowercase kebab-case for titles. Return valid JSON only."""

    print("=" * 80)
    print("SENDING TO GROQ:")
    print("=" * 80)
    print(prompt)
    print("\n" + "=" * 80)
    print("WAITING FOR RESPONSE...")
    print("=" * 80 + "\n")
    
    try:
        response = await provider.complete(prompt)
        
        print("RAW RESPONSE:")
        print("=" * 80)
        print(response)
        print("=" * 80 + "\n")
        
        # Try to parse as JSON
        try:
            parsed = json.loads(response)
            print("PARSED JSON:")
            print("=" * 80)
            print(json.dumps(parsed, indent=2))
            print("=" * 80 + "\n")
            
            if "propositions" in parsed:
                print(f"Successfully extracted {len(parsed['propositions'])} propositions:")
                for i, prop in enumerate(parsed["propositions"], 1):
                    print(f"\n{i}. {prop.get('title', 'NO TITLE')}")
                    print(f"   Type: {prop.get('type', 'UNKNOWN')}")
                    print(f"   Confidence: {prop.get('confidence', 0.0)}")
                    print(f"   Content: {prop.get('content', 'NO CONTENT')[:100]}...")
        
        except json.JSONDecodeError as e:
            print("ERROR: Response is not valid JSON")
            print(f"Parse error: {e}")
            print("\nAttempting to extract JSON from response...")
            
            # Sometimes LLMs wrap JSON in markdown code blocks
            if "```json" in response:
                json_start = response.find("```json") + 7
                json_end = response.find("```", json_start)
                json_str = response[json_start:json_end].strip()
            elif response.strip().startswith("```"):
                # Generic code block without language specifier
                lines = response.strip().split('\n')
                json_str = '\n'.join(lines[1:-1])  # Remove first and last ```
            else:
                json_str = response
            
            try:
                parsed = json.loads(json_str)
                print("✅ Successfully extracted JSON from code block!")
                print(json.dumps(parsed, indent=2))
                print("\n" + "=" * 80)
                
                if "propositions" in parsed:
                    print(f"✅ Extracted {len(parsed['propositions'])} propositions:")
                    for i, prop in enumerate(parsed["propositions"], 1):
                        print(f"\n{i}. {prop.get('title', 'NO TITLE')}")
                        print(f"   Type: {prop.get('type', 'UNKNOWN')}")
                        print(f"   Confidence: {prop.get('confidence', 0.0)}")
                        print(f"   Temporal: {prop.get('temporal_marker', 'null')}")
                        print(f"   Content: {prop.get('content', 'NO CONTENT')}")
            except Exception as parse_err:
                print(f"❌ Still couldn't parse JSON: {parse_err}")
    
    except Exception as e:
        print(f"ERROR during LLM call: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_extraction())
