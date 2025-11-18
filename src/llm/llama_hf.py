"""
Llama 3.1 Direct Integration via Hugging Face Transformers
Use Llama model files stored locally in data/models/
"""

from typing import Dict, Any, Optional
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
from pathlib import Path
import json


class LlamaHuggingFace:
    """
    Direct Llama 3.1 integration using Hugging Face transformers
    Loads model from local files in data/models/
    """

    def __init__(
        self,
        model_path: str = "data/models/meta-llama/Meta-Llama-3.1-8B-Instruct",
        device: str = "auto",
        load_in_4bit: bool = True,
        max_new_tokens: int = 512
    ):
        """
        Initialize Llama model from local files

        Args:
            model_path: Path to model files (downloaded from HF)
            device: "cuda", "cpu", or "auto"
            load_in_4bit: Use 4-bit quantization (saves memory)
            max_new_tokens: Maximum tokens to generate
        """

        self.model_path = Path(model_path)
        self.max_new_tokens = max_new_tokens
        self.device = device

        print(f"Loading Llama 3.1 from: {self.model_path}")

        # Check if model exists
        if not self.model_path.exists():
            raise FileNotFoundError(
                f"Model not found at {self.model_path}\n"
                f"Download it with: python scripts/download_llama_hf.py"
            )

        # Load tokenizer
        print("Loading tokenizer...")
        self.tokenizer = AutoTokenizer.from_pretrained(
            str(self.model_path),
            local_files_only=True
        )

        # Load model with optional quantization
        print(f"Loading model (4-bit: {load_in_4bit})...")
        if load_in_4bit and torch.cuda.is_available():
            from transformers import BitsAndBytesConfig

            quantization_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_use_double_quant=True,
                bnb_4bit_quant_type="nf4"
            )

            self.model = AutoModelForCausalLM.from_pretrained(
                str(self.model_path),
                quantization_config=quantization_config,
                device_map="auto",
                local_files_only=True
            )
        else:
            self.model = AutoModelForCausalLM.from_pretrained(
                str(self.model_path),
                device_map=device,
                torch_dtype=torch.float16,
                local_files_only=True
            )

        # Create pipeline
        self.pipe = pipeline(
            "text-generation",
            model=self.model,
            tokenizer=self.tokenizer,
            max_new_tokens=max_new_tokens,
            do_sample=True,
            temperature=0.7,
            top_p=0.95
        )

        print("✓ Llama 3.1 loaded and ready!")

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """
        Generate text from prompt

        Args:
            prompt: User prompt
            system_prompt: Optional system prompt

        Returns:
            Generated text
        """

        # Format prompt (Llama 3.1 chat template)
        if system_prompt:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ]
        else:
            messages = [
                {"role": "user", "content": prompt}
            ]

        # Apply chat template
        formatted_prompt = self.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True
        )

        # Generate
        outputs = self.pipe(formatted_prompt)
        generated_text = outputs[0]["generated_text"]

        # Extract only the assistant's response
        assistant_response = generated_text.split("<|start_header_id|>assistant<|end_header_id|>")[-1]
        assistant_response = assistant_response.split("<|eot_id|>")[0].strip()

        return assistant_response

    def explain_decision(self, decision: Dict[str, Any]) -> str:
        """Get plain English explanation of trading decision"""

        system_prompt = "You are a professional forex trading assistant. Explain trading decisions clearly and concisely."

        prompt = f"""Explain this trading decision in 2-3 sentences:

Decision: {decision['action']}
Pair: {decision['symbol']}
Confidence: {decision['confidence']:.1%}

Agent Votes:
- Technical: {decision['votes']['technical']}
- Sentiment: {decision['votes']['sentiment']}
- Risk: {decision['votes']['risk']}

Consensus: {decision['consensus']:.1%}

Explain why this decision was made:"""

        return self.generate(prompt, system_prompt)

    def analyze_news_impact(self, news_headline: str, symbol: str) -> Dict[str, Any]:
        """Analyze market impact of news"""

        system_prompt = "You are a forex market analyst. Analyze news impact on currency pairs."

        prompt = f"""Analyze this news for trading impact on {symbol}:

Headline: {news_headline}

Provide analysis in JSON format:
{{
  "sentiment": "bullish/bearish/neutral",
  "impact": "high/medium/low",
  "direction": "up/down/sideways",
  "reasoning": "Brief explanation"
}}

Return ONLY valid JSON, no other text:"""

        response = self.generate(prompt, system_prompt)

        # Try to parse JSON
        try:
            # Clean response (remove markdown code blocks if present)
            response = response.replace("```json", "").replace("```", "").strip()
            return json.loads(response)
        except json.JSONDecodeError:
            return {
                "sentiment": "neutral",
                "impact": "unknown",
                "direction": "sideways",
                "reasoning": "Could not parse analysis",
                "raw_response": response
            }

    def generate_trading_scenarios(
        self,
        count: int = 10,
        pair: str = "EUR_USD"
    ) -> list:
        """Generate synthetic trading scenarios"""

        system_prompt = "You are a forex trading scenario generator."

        prompt = f"""Generate {count} realistic trading scenarios for {pair}.

Each scenario should include:
- price (number)
- rsi (0-100)
- macd (bullish/bearish)
- trend (uptrend/downtrend/sideways)
- sentiment (positive/negative/neutral)
- news (brief context)
- action (BUY/SELL/HOLD)

Return as JSON array with {count} scenarios.
Return ONLY valid JSON, no other text:"""

        response = self.generate(prompt, system_prompt)

        try:
            response = response.replace("```json", "").replace("```", "").strip()
            return json.loads(response)
        except json.JSONDecodeError:
            print(f"Could not parse scenarios: {response[:200]}")
            return []


class LlamaAdvisorHF:
    """
    Adapter class that provides same interface as LlamaAdvisor (Ollama)
    but uses Hugging Face models
    """

    def __init__(self, model_path: str = "data/models/meta-llama/Meta-Llama-3.1-8B-Instruct"):
        self.llama = LlamaHuggingFace(model_path=model_path)

    def explain_decision(self, decision: Dict[str, Any]) -> str:
        return self.llama.explain_decision(decision)

    def analyze_news_impact(self, news_headline: str, symbol: str) -> Dict[str, Any]:
        return self.llama.analyze_news_impact(news_headline, symbol)

    def generate_trading_scenarios(self, count: int = 10, pair: str = "EUR_USD") -> list:
        return self.llama.generate_trading_scenarios(count, pair)


# Example usage
if __name__ == "__main__":
    print("Testing Llama HF Integration...")

    try:
        # Initialize
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

        print("\n" + "=" * 60)
        print("Testing Decision Explanation:")
        print("=" * 60)
        explanation = advisor.explain_decision(decision)
        print(explanation)

        # Test news analysis
        print("\n" + "=" * 60)
        print("Testing News Analysis:")
        print("=" * 60)
        news = advisor.analyze_news_impact(
            "ECB raises interest rates by 25 basis points",
            "EUR_USD"
        )
        print(json.dumps(news, indent=2))

    except Exception as e:
        print(f"\n✗ Error: {e}")
        print("\nMake sure you've downloaded the model:")
        print("  python scripts/download_llama_hf.py")
