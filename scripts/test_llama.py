#!/usr/bin/env python3
"""
ATHENA-X - Llama 3.1 Integration Test
Tests connection to local Llama 3.1 model for trading analysis
"""

import requests
import json
from typing import Dict, Any


def test_ollama_connection(model: str = "llama3.1:8b") -> bool:
    """Test connection to Ollama Llama 3.1 model"""

    print("Testing Ollama connection...")
    print(f"Model: {model}")
    print("=" * 60)

    # Test 1: Check if Ollama is running
    try:
        response = requests.get("http://localhost:11434/api/tags")
        if response.status_code == 200:
            models = response.json().get('models', [])
            print(f"✓ Ollama is running")
            print(f"✓ Available models: {len(models)}")
            for m in models:
                print(f"  - {m['name']}")
        else:
            print("✗ Ollama not responding")
            return False
    except requests.exceptions.ConnectionError:
        print("✗ Cannot connect to Ollama (is it running on port 11434?)")
        return False

    # Test 2: Simple trading question
    print("\n" + "=" * 60)
    print("Testing trading analysis with Llama 3.1...")
    print("=" * 60)

    prompt = """You are a professional forex trader. Analyze this scenario:

Market: EUR/USD
Current Price: 1.0850
20 EMA: 1.0830
50 EMA: 1.0800
RSI: 65
MACD: Bullish crossover
Volume: Above average
News: ECB hints at rate hold

Should we BUY, SELL, or HOLD? Provide a brief 2-3 sentence analysis."""

    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False
            },
            timeout=30
        )

        if response.status_code == 200:
            result = response.json()
            analysis = result.get('response', '')

            print("\n✓ Llama 3.1 Analysis:")
            print("-" * 60)
            print(analysis)
            print("-" * 60)
            print(f"\nTokens: {result.get('eval_count', 'N/A')}")
            print(f"Time: {result.get('total_duration', 0) / 1e9:.2f}s")

            return True
        else:
            print(f"✗ API error: {response.status_code}")
            return False

    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def generate_trading_scenario() -> Dict[str, Any]:
    """Generate a synthetic trading scenario using Llama"""

    scenario_prompt = """Generate a realistic forex trading scenario with the following format:

{
  "pair": "EUR_USD",
  "price": 1.0850,
  "technical": {
    "trend": "uptrend",
    "rsi": 65,
    "macd": "bullish"
  },
  "sentiment": "positive",
  "news": "ECB rate decision pending",
  "recommendation": "BUY",
  "reasoning": "Brief explanation"
}

Generate one scenario in valid JSON format only, no other text:"""

    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "llama3.1:8b",
                "prompt": scenario_prompt,
                "stream": False,
                "format": "json"
            },
            timeout=30
        )

        if response.status_code == 200:
            result = response.json()
            scenario_text = result.get('response', '')

            # Try to parse JSON
            try:
                scenario = json.loads(scenario_text)
                print("\n✓ Generated Trading Scenario:")
                print(json.dumps(scenario, indent=2))
                return scenario
            except json.JSONDecodeError:
                print("✗ Could not parse JSON response")
                print(f"Raw response: {scenario_text}")
                return {}
        else:
            print(f"✗ API error: {response.status_code}")
            return {}

    except Exception as e:
        print(f"✗ Error generating scenario: {e}")
        return {}


if __name__ == "__main__":
    print("=" * 60)
    print("  ATHENA-X - Llama 3.1 Integration Test")
    print("=" * 60)
    print()

    # Test connection
    if test_ollama_connection():
        print("\n" + "=" * 60)
        print("Llama 3.1 is working correctly!")
        print("=" * 60)

        # Test scenario generation
        print("\n" + "=" * 60)
        print("Testing Scenario Generation...")
        print("=" * 60)
        generate_trading_scenario()

    else:
        print("\n" + "=" * 60)
        print("Llama 3.1 Setup Instructions:")
        print("=" * 60)
        print("""
1. Install Ollama:
   - Visit: https://ollama.ai/download
   - Or: docker run -d -p 11434:11434 --name ollama ollama/ollama

2. Download Llama 3.1:
   docker exec -it ollama ollama pull llama3.1:8b

3. Verify:
   curl http://localhost:11434/api/tags

4. Run this test again
""")
