# test_imports.py
try:
    import chainlit
    print("✓ chainlit imported")
except ImportError as e:
    print(f"✗ chainlit failed: {e}")

try:
    from livekit import agents
    print("✓ livekit.agents imported")
    print(f"Available: {[x for x in dir(agents) if not x.startswith('_')]}")
except ImportError as e:
    print(f"✗ livekit.agents failed: {e}")

try:
    from groq import Groq
    print("✓ groq imported")
except ImportError as e:
    print(f"✗ groq failed: {e}")