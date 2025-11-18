#!/usr/bin/env python3
"""
Phase 4.2: Fine-tune Llama 3.1 for Forex Trading
Optimized for RTX 3080 (10GB VRAM) with 4-bit quantization and LoRA
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List
import json
import yaml
from loguru import logger
import torch

try:
    from transformers import (
        AutoTokenizer,
        AutoModelForCausalLM,
        TrainingArguments,
        Trainer,
        BitsAndBytesConfig
    )
    from datasets import Dataset
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    logger.warning("transformers/peft not installed")


class LlamaFineTuner:
    """Fine-tune Llama 3.1 8B for trading decisions"""

    def __init__(
        self,
        model_name: str = "meta-llama/Meta-Llama-3.1-8B-Instruct",
        output_dir: str = "data/models/llama-trading",
        use_4bit: bool = True
    ):
        """
        Initialize fine-tuner

        Args:
            model_name: HuggingFace model ID or local path
            output_dir: Directory to save fine-tuned model
            use_4bit: Use 4-bit quantization (required for RTX 3080)
        """
        self.model_name = model_name
        self.output_dir = Path(output_dir)
        self.use_4bit = use_4bit

        logger.info(f"Llama Fine-Tuner initialized")
        logger.info(f"  Model: {model_name}")
        logger.info(f"  4-bit quantization: {use_4bit}")
        logger.info(f"  Output: {output_dir}")

        # Check GPU
        if torch.cuda.is_available():
            gpu_name = torch.cuda.get_device_name(0)
            gpu_memory = torch.cuda.get_device_properties(0).total_memory / 1e9
            logger.success(f"  GPU: {gpu_name} ({gpu_memory:.1f} GB)")
        else:
            logger.warning("  No GPU detected - training will be very slow")

    def load_training_data(self, data_dir: str = "data/training") -> List[Dict]:
        """
        Load and prepare training data from exported CSVs

        Returns:
            List of training examples in chat format
        """
        data_path = Path(data_dir)

        if not data_path.exists():
            logger.error(f"Training data not found: {data_dir}")
            return []

        training_examples = []

        for csv_file in data_path.glob("*_training.csv"):
            symbol = csv_file.stem.replace('_training', '')
            logger.info(f"Processing {symbol}...")

            try:
                df = pd.read_csv(csv_file, index_col=0, parse_dates=True)

                # Generate training examples from data
                examples = self._create_trading_examples(df, symbol)
                training_examples.extend(examples)

                logger.info(f"  Generated {len(examples)} examples from {symbol}")

            except Exception as e:
                logger.error(f"Failed to load {csv_file}: {e}")

        logger.success(f"Total training examples: {len(training_examples)}")
        return training_examples

    def _create_trading_examples(self, df: pd.DataFrame, symbol: str, max_examples: int = 500) -> List[Dict]:
        """
        Create training examples from historical data

        Format:
        User: [Market conditions]
        Assistant: [Trading decision with reasoning]
        """
        examples = []

        # Sample evenly across the dataset
        if len(df) > max_examples:
            indices = np.linspace(0, len(df)-1, max_examples, dtype=int)
            df_sample = df.iloc[indices]
        else:
            df_sample = df

        for idx, row in df_sample.iterrows():
            # Skip if missing critical data
            if pd.isna(row.get('Label')) or pd.isna(row.get('RSI')):
                continue

            # Create market scenario
            scenario = self._format_market_scenario(row, symbol)

            # Get trading decision and reasoning
            decision, reasoning = self._format_trading_decision(row)

            # Create chat format example
            example = {
                "messages": [
                    {
                        "role": "system",
                        "content": "You are an expert forex trader analyzing market conditions and making trading decisions."
                    },
                    {
                        "role": "user",
                        "content": f"Analyze this trading scenario and recommend BUY, SELL, or HOLD:\n\n{scenario}"
                    },
                    {
                        "role": "assistant",
                        "content": f"**Decision: {decision}**\n\n{reasoning}"
                    }
                ]
            }

            examples.append(example)

        return examples

    def _format_market_scenario(self, row: pd.Series, symbol: str) -> str:
        """Format market data as a scenario"""

        scenario = f"""**Market: {symbol}**

**Price Action:**
- Current Price: {row.get('Close', 0):.5f}
- High: {row.get('High', 0):.5f}
- Low: {row.get('Low', 0):.5f}

**Technical Indicators:**
- RSI: {row.get('RSI', 50):.1f}
- MACD: {'Bullish' if row.get('MACD', 0) > row.get('MACD_Signal', 0) else 'Bearish'}
- Trend: {'Uptrend' if row.get('Trend', 0) > 0.01 else 'Downtrend' if row.get('Trend', 0) < -0.01 else 'Sideways'}
- ATR: {row.get('ATR', 0):.5f}
- Volume: {'Above average' if row.get('Volume_Ratio', 1) > 1.2 else 'Below average' if row.get('Volume_Ratio', 1) < 0.8 else 'Normal'}

**Moving Averages:**
- SMA 20: {row.get('SMA_20', 0):.5f}
- SMA 50: {row.get('SMA_50', 0):.5f}
- Price vs SMA 20: {'Above' if row.get('Close', 0) > row.get('SMA_20', 0) else 'Below'}

**Bollinger Bands:**
- Upper: {row.get('BB_Upper', 0):.5f}
- Middle: {row.get('BB_Middle', 0):.5f}
- Lower: {row.get('BB_Lower', 0):.5f}
- Position: {'Near upper band' if row.get('Close', 0) > row.get('BB_Middle', 0) else 'Near lower band'}
"""

        return scenario

    def _format_trading_decision(self, row: pd.Series) -> tuple:
        """Format the trading decision and reasoning"""

        label = row.get('Label', 0)
        rsi = row.get('RSI', 50)
        trend = row.get('Trend', 0)
        regime = row.get('Regime', 1)

        # Decision
        if label == 1:
            decision = "BUY"
        elif label == -1:
            decision = "SELL"
        else:
            decision = "HOLD"

        # Reasoning
        reasons = []

        # RSI reasoning
        if rsi > 70:
            reasons.append(f"RSI at {rsi:.1f} indicates overbought conditions")
        elif rsi < 30:
            reasons.append(f"RSI at {rsi:.1f} indicates oversold conditions")
        else:
            reasons.append(f"RSI at {rsi:.1f} shows neutral momentum")

        # Trend reasoning
        if trend > 0.01:
            reasons.append("Strong uptrend confirmed by moving averages")
        elif trend < -0.01:
            reasons.append("Strong downtrend confirmed by moving averages")
        else:
            reasons.append("Market is ranging without clear trend")

        # Regime reasoning
        regime_names = {0: "bearish", 1: "neutral", 2: "bullish"}
        reasons.append(f"Market regime is {regime_names.get(regime, 'neutral')}")

        # Price action
        if row.get('Close', 0) > row.get('SMA_20', 0):
            reasons.append("Price trading above short-term moving average")
        else:
            reasons.append("Price trading below short-term moving average")

        reasoning = " | ".join(reasons)

        return decision, reasoning

    def prepare_dataset(self, examples: List[Dict]) -> Dataset:
        """Prepare HuggingFace dataset"""

        # Convert to chat format strings
        formatted_examples = []

        for example in examples:
            # Apply chat template format
            formatted = {
                "text": self._format_chat(example["messages"])
            }
            formatted_examples.append(formatted)

        dataset = Dataset.from_list(formatted_examples)
        logger.info(f"Prepared dataset: {len(dataset)} examples")

        return dataset

    def _format_chat(self, messages: List[Dict]) -> str:
        """Format messages in Llama 3.1 chat format"""

        formatted = ""

        for msg in messages:
            role = msg["role"]
            content = msg["content"]

            if role == "system":
                formatted += f"<|start_header_id|>system<|end_header_id|>\n\n{content}<|eot_id|>"
            elif role == "user":
                formatted += f"<|start_header_id|>user<|end_header_id|>\n\n{content}<|eot_id|>"
            elif role == "assistant":
                formatted += f"<|start_header_id|>assistant<|end_header_id|>\n\n{content}<|eot_id|>"

        return formatted

    def load_model_and_tokenizer(self):
        """Load model with 4-bit quantization and LoRA"""

        if not TRANSFORMERS_AVAILABLE:
            logger.error("transformers/peft not installed")
            logger.error("Install with: pip install transformers peft accelerate bitsandbytes")
            return None, None

        logger.info("Loading tokenizer...")
        tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        tokenizer.pad_token = tokenizer.eos_token
        tokenizer.padding_side = "right"

        logger.info("Loading model with 4-bit quantization...")

        # 4-bit quantization config (for RTX 3080 with 10GB VRAM)
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_use_double_quant=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.float16
        )

        model = AutoModelForCausalLM.from_pretrained(
            self.model_name,
            quantization_config=bnb_config,
            device_map="auto",
            torch_dtype=torch.float16,
            trust_remote_code=True
        )

        # Prepare for k-bit training
        model = prepare_model_for_kbit_training(model)

        # LoRA config (low-rank adaptation for efficient fine-tuning)
        lora_config = LoraConfig(
            r=16,  # Rank
            lora_alpha=32,  # Scaling factor
            target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
            lora_dropout=0.05,
            bias="none",
            task_type="CAUSAL_LM"
        )

        model = get_peft_model(model, lora_config)

        trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
        all_params = sum(p.numel() for p in model.parameters())

        logger.success(f"Model loaded with LoRA")
        logger.info(f"  Trainable params: {trainable_params:,} ({trainable_params/all_params:.2%})")
        logger.info(f"  All params: {all_params:,}")

        return model, tokenizer

    def train(
        self,
        dataset: Dataset,
        model,
        tokenizer,
        epochs: int = 3,
        batch_size: int = 2,
        learning_rate: float = 2e-4
    ):
        """
        Fine-tune the model

        Args:
            dataset: Training dataset
            model: Model to fine-tune
            tokenizer: Tokenizer
            epochs: Number of training epochs
            batch_size: Batch size (keep small for RTX 3080)
            learning_rate: Learning rate
        """

        # Training arguments optimized for RTX 3080
        training_args = TrainingArguments(
            output_dir=str(self.output_dir),
            num_train_epochs=epochs,
            per_device_train_batch_size=batch_size,
            gradient_accumulation_steps=8,  # Effective batch size = 2 * 8 = 16
            optim="paged_adamw_8bit",  # Memory-efficient optimizer
            learning_rate=learning_rate,
            weight_decay=0.01,
            fp16=True,  # Mixed precision training
            logging_steps=10,
            save_strategy="epoch",
            save_total_limit=2,
            warmup_ratio=0.03,
            lr_scheduler_type="cosine",
            report_to="none",  # Disable wandb/tensorboard
            max_grad_norm=0.3,
            group_by_length=True,
        )

        # Tokenization function
        def tokenize_function(examples):
            return tokenizer(
                examples["text"],
                truncation=True,
                max_length=512,
                padding="max_length"
            )

        # Tokenize dataset
        logger.info("Tokenizing dataset...")
        tokenized_dataset = dataset.map(tokenize_function, batched=True)

        # Trainer
        trainer = Trainer(
            model=model,
            args=training_args,
            train_dataset=tokenized_dataset,
            data_collator=lambda data: {
                'input_ids': torch.stack([f['input_ids'] for f in data]),
                'attention_mask': torch.stack([f['attention_mask'] for f in data]),
                'labels': torch.stack([f['input_ids'] for f in data])
            }
        )

        # Train
        logger.info("Starting training...")
        logger.info(f"  Epochs: {epochs}")
        logger.info(f"  Batch size: {batch_size}")
        logger.info(f"  Gradient accumulation: {training_args.gradient_accumulation_steps}")
        logger.info(f"  Effective batch size: {batch_size * training_args.gradient_accumulation_steps}")
        logger.info(f"  Learning rate: {learning_rate}")

        trainer.train()

        logger.success("✓ Training complete!")

        # Save model
        logger.info("Saving model...")
        trainer.save_model()
        tokenizer.save_pretrained(str(self.output_dir))

        logger.success(f"✓ Model saved to {self.output_dir}")

        return trainer


if __name__ == "__main__":
    print("=" * 60)
    print("  ATHENA-X Phase 4.2: Fine-tune Llama 3.1 for Trading")
    print("  Optimized for RTX 3080 (10GB VRAM)")
    print("=" * 60)
    print()

    if not TRANSFORMERS_AVAILABLE:
        print("✗ Required packages not installed")
        print()
        print("Install with:")
        print("  pip install transformers peft accelerate bitsandbytes")
        print()
        exit(1)

    # Check CUDA
    if not torch.cuda.is_available():
        print("⚠️  WARNING: No CUDA GPU detected")
        print("   Fine-tuning without GPU will be extremely slow")
        print()
        response = input("Continue anyway? (y/N): ")
        if response.lower() != 'y':
            print("Exiting...")
            exit(0)

    # Initialize
    finetuner = LlamaFineTuner(
        model_name="meta-llama/Meta-Llama-3.1-8B-Instruct",
        output_dir="data/models/llama-trading",
        use_4bit=True
    )

    # Load training data
    print("\nLoading training data...")
    training_examples = finetuner.load_training_data(data_dir="data/training")

    if not training_examples:
        print("\n✗ No training data found")
        print("\nRun Phase 4.1 first:")
        print("  python scripts/export_questdb_training_data.py")
        exit(1)

    # Prepare dataset
    print("\nPreparing dataset...")
    dataset = finetuner.prepare_dataset(training_examples)

    # Load model
    print("\nLoading Llama 3.1 8B with 4-bit quantization...")
    model, tokenizer = finetuner.load_model_and_tokenizer()

    if model is None:
        print("\n✗ Failed to load model")
        exit(1)

    # Train
    print("\nStarting fine-tuning...")
    print("This will take 1-3 hours depending on data size")
    print()

    trainer = finetuner.train(
        dataset=dataset,
        model=model,
        tokenizer=tokenizer,
        epochs=3,
        batch_size=2,  # Small batch for RTX 3080
        learning_rate=2e-4
    )

    print()
    print("=" * 60)
    print("✓ Phase 4.2 Complete: Llama 3.1 Fine-tuned for Trading")
    print("=" * 60)
    print(f"Model saved to: data/models/llama-trading/")
    print()
    print("Next steps:")
    print("  1. Test model: python scripts/test_finetuned_llama.py")
    print("  2. Integrate into ATHENA-X: Phase 4.4")
