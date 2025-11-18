# Llama 3.1 Integration Guide for ATHENA-X

This guide shows you how to integrate Llama 3.1 with ATHENA-X using **two different methods**.

---

## Overview

Llama 3.1 can enhance ATHENA-X by:
- 🧠 **Reasoning about complex market scenarios**
- 📊 **Explaining trading decisions in plain English**
- 🔍 **Analyzing news and generating insights**
- 📝 **Generating synthetic training data for backtesting**
- 🎓 **Educational mode (explaining what the system is doing)**

**Note:** This is **optional** - ATHENA-X works great without it!

---

## 🔀 Two Integration Methods

### Method 1: Ollama (Easiest) ⭐
- ✅ No manual file downloads
- ✅ Ollama handles everything
- ✅ Easy API access
- ❌ Less control over parameters

### Method 2: Hugging Face Direct (Advanced)
- ✅ Full control over model
- ✅ Integrated into Python
- ✅ Can fine-tune and customize
- ❌ Manual download required (~16GB)
- ❌ More complex setup

**Recommended:** Start with **Method 1 (Ollama)** unless you need fine-tuning.

---

## 📋 Which Method Should You Use?

**Use Ollama (Method 1) if:**
- You want the easiest setup
- You're using Llama for inference only (not training)
- You want to switch models frequently
- You're okay with API calls

**Use Hugging Face (Method 2) if:**
- You want to fine-tune Llama for trading
- You need full control over model parameters
- You want to integrate deeply into Python code
- You're comfortable with ~16GB download

---

## Method 1: Ollama Setup (Recommended) ⭐

### Step 1: Install Ollama

**If you already have Ollama Docker container:**
```powershell
# Check if it's running
docker ps | grep ollama

# If not running, start it
docker start ollama

# If you don't have it, create it:
docker run -d -p 11434:11434 --name ollama ollama/ollama
```

#### Step 2: Download Llama 3.1

```powershell
# Download Llama 3.1 8B (recommended - faster, 4.7GB)
docker exec -it ollama ollama pull llama3.1:8b

# OR download Llama 3.1 70B (more powerful but slower, 40GB)
# docker exec -it ollama ollama pull llama3.1:70b
```

**Download time:** ~5-10 minutes depending on your internet speed

#### Step 3: Test the Connection

```powershell
# Test Ollama is working
curl http://localhost:11434/api/tags

# In ATHENA-X Docker container:
.\docker-run.ps1 shell

# Run the test script
python scripts/test_llama.py
```

**Expected output:**
```
✓ Ollama is running
✓ Available models: 1
  - llama3.1:8b

✓ Llama 3.1 Analysis:
Based on the given scenario, I would recommend a BUY position.
The bullish MACD crossover combined with price above both EMAs
suggests continued upward momentum...
```

---

## How to Use Llama with ATHENA-X

### 1. Trading Decision Explanation

Create `src/llm/llama_advisor.py`:

```python
import requests
from typing import Dict, Any


class LlamaAdvisor:
    """Llama 3.1 trading advisor for ATHENA-X"""

    def __init__(self, model: str = "llama3.1:8b", api_url: str = "http://host.docker.internal:11434"):
        self.model = model
        self.api_url = api_url

    def explain_decision(self, decision: Dict[str, Any]) -> str:
        """
        Get plain English explanation of a trading decision

        Args:
            decision: Dictionary with agent votes, consensus, signals, etc.

        Returns:
            Human-readable explanation
        """

        prompt = f"""You are a professional trading assistant. Explain this trading decision:

Decision: {decision['action']}
Pair: {decision['symbol']}
Confidence: {decision['confidence']:.1%}

Technical Agent Vote: {decision['votes']['technical']}
Sentiment Agent Vote: {decision['votes']['sentiment']}
Risk Agent Vote: {decision['votes']['risk']}

Consensus: {decision['consensus']:.1%}

Explain in 2-3 sentences why this decision was made and what it means."""

        try:
            response = requests.post(
                f"{self.api_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False
                },
                timeout=15
            )

            if response.status_code == 200:
                return response.json().get('response', 'No explanation available')
            else:
                return "Could not generate explanation"

        except Exception as e:
            return f"Error: {e}"


    def analyze_news_impact(self, news_headline: str, symbol: str) -> Dict[str, Any]:
        """
        Analyze potential market impact of news

        Args:
            news_headline: News headline to analyze
            symbol: Trading pair (e.g., EUR_USD)

        Returns:
            Analysis with sentiment, impact, and recommendation
        """

        prompt = f"""Analyze this news for forex trading impact:

Headline: {news_headline}
Pair: {symbol}

Provide:
1. Sentiment (bullish/bearish/neutral)
2. Impact level (high/medium/low)
3. Expected price direction
4. Brief reasoning (1 sentence)

Format as JSON:
{{
  "sentiment": "...",
  "impact": "...",
  "direction": "...",
  "reasoning": "..."
}}"""

        try:
            response = requests.post(
                f"{self.api_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json"
                },
                timeout=20
            )

            if response.status_code == 200:
                import json
                result_text = response.json().get('response', '{}')
                return json.loads(result_text)
            else:
                return {"error": "API error"}

        except Exception as e:
            return {"error": str(e)}


    def generate_trading_scenarios(self, count: int = 10, pair: str = "EUR_USD") -> list:
        """
        Generate synthetic trading scenarios for training/testing

        Args:
            count: Number of scenarios to generate
            pair: Trading pair

        Returns:
            List of scenario dictionaries
        """

        prompt = f"""Generate {count} realistic forex trading scenarios for {pair}.

Each scenario should include:
- Current price and technicals (RSI, MACD, EMAs)
- Market sentiment (bullish/bearish/neutral)
- News context
- Recommended action (BUY/SELL/HOLD)
- Expected outcome

Return as JSON array."""

        try:
            response = requests.post(
                f"{self.api_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json"
                },
                timeout=60
            )

            if response.status_code == 200:
                import json
                result_text = response.json().get('response', '[]')
                return json.loads(result_text)
            else:
                return []

        except Exception as e:
            print(f"Error generating scenarios: {e}")
            return []
```

### 2. Using in Trading System

**In your orchestrator (`src/orchestration/orchestrator.py`):**

```python
from src.llm.llama_advisor import LlamaAdvisor

class ATHENAOrchestrator:
    def __init__(self, config):
        # ... existing code ...

        # Optional: Add Llama advisor
        try:
            self.llama = LlamaAdvisor()
            logger.info("Llama advisor initialized")
        except:
            self.llama = None
            logger.warning("Llama advisor not available")

    def evaluate_opportunity(self, symbol, market_data):
        # ... existing decision logic ...

        # If decision made and Llama available, get explanation
        if self.llama and decision['action'] != 'HOLD':
            explanation = self.llama.explain_decision(decision)
            logger.info(f"Llama explanation: {explanation}")
            decision['explanation'] = explanation

        return decision
```

### 3. News Analysis Enhancement

**In sentiment agent (`src/agents/sentiment_agent.py`):**

```python
def analyze_news(self, news_items):
    # ... existing news analysis ...

    # Enhance with Llama for important news
    if hasattr(self, 'llama') and self.llama:
        for item in high_impact_news:
            llama_analysis = self.llama.analyze_news_impact(
                item['headline'],
                self.current_symbol
            )
            item['llama_impact'] = llama_analysis

    return news_analysis
```

---

## Testing Llama Integration

### Basic Connection Test

```bash
# In Docker container
python scripts/test_llama.py
```

### Interactive Test

```python
# In Docker shell
python

from src.llm.llama_advisor import LlamaAdvisor

advisor = LlamaAdvisor()

# Test explanation
decision = {
    'action': 'BUY',
    'symbol': 'EUR_USD',
    'confidence': 0.75,
    'votes': {
        'technical': 'BUY',
        'sentiment': 'BUY',
        'risk': 'APPROVED'
    },
    'consensus': 0.85
}

explanation = advisor.explain_decision(decision)
print(explanation)

# Test news analysis
news = advisor.analyze_news_impact(
    "ECB raises interest rates by 25 basis points",
    "EUR_USD"
)
print(news)
```

---

## Performance Considerations

### Model Size vs Speed

| Model | Size | Speed | Quality | Best For |
|-------|------|-------|---------|----------|
| **llama3.1:8b** | 4.7GB | Fast | Good | Real-time trading |
| **llama3.1:70b** | 40GB | Slow | Excellent | Deep analysis, training |

**Recommendation:** Use `llama3.1:8b` for live trading

### CPU vs GPU

**With GPU (CUDA 13):**
- 8B model: ~50-100 tokens/sec
- Response time: 2-5 seconds

**CPU Only:**
- 8B model: ~5-10 tokens/sec
- Response time: 10-30 seconds

**If you have GPU, enable it in Ollama:**
```powershell
# Stop existing container
docker stop ollama
docker rm ollama

# Restart with GPU support
docker run -d --gpus all -p 11434:11434 --name ollama ollama/ollama
docker exec -it ollama ollama pull llama3.1:8b
```

---

## Method 2: Hugging Face Direct Integration 🤗

If you want full control and plan to fine-tune Llama for trading.

### Step 1: Get Hugging Face Access

1. **Create HF account:** https://huggingface.co/join
2. **Accept Llama license:** https://huggingface.co/meta-llama/Meta-Llama-3.1-8B-Instruct
3. **Get access token:** https://huggingface.co/settings/tokens (create "Read" token)
4. **Login via CLI:**
   ```bash
   pip install huggingface_hub
   huggingface-cli login
   # Paste your token when prompted
   ```

### Step 2: Download Model Files

**Option A: Using provided script (recommended):**

```powershell
# In ATHENA-X container
.\docker-run.ps1 shell

# Run download script
python scripts/download_llama_hf.py
```

This will:
- Download Llama 3.1 8B Instruct (~16GB)
- Save to `data/models/meta-llama/Meta-Llama-3.1-8B-Instruct/`
- Take 10-30 minutes depending on internet speed

**Option B: Manual download:**

```bash
# Install dependencies
pip install huggingface_hub transformers torch

# Download model
python -c "
from huggingface_hub import snapshot_download

model_path = snapshot_download(
    repo_id='meta-llama/Meta-Llama-3.1-8B-Instruct',
    cache_dir='data/models',
    resume_download=True
)
print(f'Downloaded to: {model_path}')
"
```

**Model files structure:**
```
data/models/
└── meta-llama/
    └── Meta-Llama-3.1-8B-Instruct/
        ├── config.json
        ├── pytorch_model.bin (or .safetensors files)
        ├── tokenizer.json
        ├── tokenizer_config.json
        └── ... other files
```

### Step 3: Install Dependencies

```bash
# Required packages
pip install transformers torch accelerate bitsandbytes

# For GPU (CUDA 12/13)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

### Step 4: Test Hugging Face Integration

```python
# Test script
python -c "
from src.llm.llama_hf import LlamaAdvisorHF

# Initialize (will load model from data/models/)
advisor = LlamaAdvisorHF()

# Test decision explanation
decision = {
    'action': 'BUY',
    'symbol': 'EUR_USD',
    'confidence': 0.75,
    'votes': {
        'technical': 'BUY',
        'sentiment': 'BUY',
        'risk': 'APPROVED'
    },
    'consensus': 0.85
}

explanation = advisor.explain_decision(decision)
print('Explanation:', explanation)
"
```

### Step 5: Use in ATHENA-X

**Using Hugging Face instead of Ollama:**

```python
# In your orchestrator or agents
from src.llm.llama_hf import LlamaAdvisorHF

class ATHENAOrchestrator:
    def __init__(self, config):
        # ... existing code ...

        # Use Hugging Face Llama (instead of Ollama)
        try:
            self.llama = LlamaAdvisorHF(
                model_path="data/models/meta-llama/Meta-Llama-3.1-8B-Instruct"
            )
            logger.info("Llama HF advisor initialized")
        except Exception as e:
            self.llama = None
            logger.warning(f"Llama not available: {e}")
```

### Pros & Cons of Hugging Face Method

**Pros:**
- ✅ Full model control (temperature, top_p, etc.)
- ✅ Can fine-tune for trading-specific tasks
- ✅ No external API dependencies
- ✅ Faster inference (no network overhead)
- ✅ Works offline

**Cons:**
- ❌ Large download (16GB for 8B model)
- ❌ Requires more RAM (8-16GB)
- ❌ More complex setup
- ❌ GPU recommended for good performance

### Memory Requirements

| Model Size | Precision | RAM Required | GPU VRAM | Speed (tokens/sec) |
|------------|-----------|--------------|----------|-------------------|
| **8B** | FP16 | 16GB | 8GB | 20-50 |
| **8B** | 4-bit | 4GB | 4GB | 15-40 |
| **70B** | FP16 | 140GB | 80GB | 2-5 |
| **70B** | 4-bit | 40GB | 40GB | 1-3 |

**Recommendation:** Use **8B with 4-bit quantization** for best balance.

### 4-bit Quantization (Saves Memory)

Already enabled by default in `LlamaHuggingFace`:

```python
advisor = LlamaAdvisorHF()  # Automatically uses 4-bit if GPU available
```

To disable quantization (requires more VRAM):

```python
from src.llm.llama_hf import LlamaHuggingFace

llama = LlamaHuggingFace(
    model_path="data/models/meta-llama/Meta-Llama-3.1-8B-Instruct",
    load_in_4bit=False  # Use full precision (16GB VRAM)
)
```

---

## Configuration

Add to `config/settings.yaml`:

```yaml
llm:
  enabled: true  # Set to false to disable

  # Choose provider: "ollama" or "huggingface"
  provider: "ollama"  # or "huggingface"

  # Ollama settings (if using Method 1)
  ollama:
    model: "llama3.1:8b"
    api_url: "http://host.docker.internal:11434"  # Docker host
    timeout: 15  # seconds

  # Hugging Face settings (if using Method 2)
  huggingface:
    model_path: "data/models/meta-llama/Meta-Llama-3.1-8B-Instruct"
    load_in_4bit: true  # Use 4-bit quantization to save memory
    max_new_tokens: 512

  # What to use Llama for
  use_for:
    explanations: true  # Explain trading decisions
    news_analysis: true  # Enhance news sentiment
    scenario_generation: false  # For training data (slow)
```

---

## Use Cases

### 1. **Live Trading Explanations**
Get human-readable explanations of why trades are made:
```
Decision: BUY EUR_USD
Explanation: "The consensus shows strong bullish signals with
technical indicators confirming an uptrend. Risk parameters
are within acceptable limits, suggesting a favorable entry point."
```

### 2. **News Impact Analysis**
Automatically analyze breaking news:
```
Headline: "Fed hints at rate pause"
Impact: HIGH | Sentiment: BULLISH for EUR_USD
Reasoning: "Dollar weakness expected from dovish Fed stance"
```

### 3. **Training Data Generation**
Generate thousands of synthetic scenarios for backtesting:
```python
scenarios = advisor.generate_trading_scenarios(count=1000)
# Use for training/validation
```

### 4. **Educational Mode**
Learn what the system is thinking:
```
"Technical Agent voted BUY because RSI shows oversold
conditions (32) and price bounced off 50 EMA support..."
```

---

## Troubleshooting

### Ollama Not Responding

```powershell
# Check if Ollama is running
docker ps | grep ollama

# Check logs
docker logs ollama

# Restart Ollama
docker restart ollama

# Test connection
curl http://localhost:11434/api/tags
```

### Slow Responses

- Use `llama3.1:8b` instead of `70b`
- Increase timeout in config
- Enable GPU acceleration
- Reduce prompt length

### Connection Refused from Docker

Use `host.docker.internal` instead of `localhost`:
```python
api_url = "http://host.docker.internal:11434"
```

### Out of Memory

```powershell
# Check Ollama memory usage
docker stats ollama

# Restart with memory limit
docker stop ollama
docker rm ollama
docker run -d -p 11434:11434 --memory="8g" --name ollama ollama/ollama
```

---

## Optional: Fine-Tuning for Trading

If you want to fine-tune Llama 3.1 specifically for trading (advanced):

1. Generate training data (trading scenarios + outcomes)
2. Use QLoRA/LoRA for efficient fine-tuning
3. Load custom adapter in Ollama

See `PHASE_4_MODEL_TRAINING.md` for details (to be created).

---

## Summary

**To Get Started:**

```powershell
# 1. Start Ollama (if not running)
docker ps | grep ollama

# 2. Download model
docker exec -it ollama ollama pull llama3.1:8b

# 3. Test connection
.\docker-run.ps1 shell
python scripts/test_llama.py

# 4. (Optional) Integrate into agents
# See code examples above
```

**Benefits:**
- ✅ Human-readable trading explanations
- ✅ Enhanced news analysis
- ✅ Synthetic data generation
- ✅ Educational insights

**Remember:** This is **optional** - ATHENA-X works excellently without it!

---

## Next Steps

1. ✅ Test Llama connection: `python scripts/test_llama.py`
2. ⏳ Create `src/llm/llama_advisor.py` (copy code above)
3. ⏳ Add to config: `llm.enabled: true`
4. ⏳ Test explanations with sample decisions
5. ⏳ Integrate into orchestrator (optional)

For questions or issues, check Ollama docs: https://ollama.ai/
