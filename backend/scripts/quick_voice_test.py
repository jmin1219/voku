"""Quick validation of prompt improvements."""
import asyncio
from app.services.extraction import ExtractionService
from app.services.providers.groq_provider import GroqProvider


async def test_voice_preservation():
    provider = GroqProvider()
    extractor = ExtractionService(provider)
    
    text = """The feared self: lazy slob, continuous masturbation, spending inherited money gambling, engaging in all vices available. 'If I just let myself be myself.' The pattern noticed: 'I need to be strict with myself or I'll go out of control' — said about productivity, drinking, multiple domains."""
    
    print("Testing voice preservation after prompt update...")
    print(f"\nOriginal phrase to preserve: 'all vices available'")
    
    propositions = await extractor.extract(text)
    
    print(f"\n✅ Extracted {len(propositions)} propositions:\n")
    for i, p in enumerate(propositions, 1):
        print(f"{i}. {p.proposition}")
        
    # Check if exact phrase preserved
    for p in propositions:
        if "all vices available" in p.proposition:
            print(f"\n✅ EXACT PHRASE PRESERVED")
            return
        elif "all vices" in p.proposition:
            print(f"\n⚠️ PARTIAL: Got 'all vices' but lost 'available'")
            return
    
    print(f"\n❌ Phrase not found in any proposition")


if __name__ == "__main__":
    asyncio.run(test_voice_preservation())
