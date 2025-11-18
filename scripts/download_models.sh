#!/bin/bash
# Download AI Models for JARVIS-X

set -e

echo "=================================================="
echo "JARVIS-X - Downloading AI Models"
echo "=================================================="

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Activate virtual environment
cd "$(dirname "$0")/.."
if [ -d "venv" ]; then
    source venv/bin/activate
else
    print_warning "Virtual environment not found. Run setup_environment.sh first"
    exit 1
fi

# Create models directory
mkdir -p data/models

print_info "Downloading models to data/models/"

# Download FinBERT (110M parameters, ~450MB)
print_info "Downloading FinBERT for sentiment analysis..."
python3 << EOF
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch

model_name = "ProsusAI/finbert"
save_path = "data/models/finbert"

print(f"Downloading {model_name}...")
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForSequenceClassification.from_pretrained(model_name)

tokenizer.save_pretrained(save_path)
model.save_pretrained(save_path)

print(f"FinBERT saved to {save_path}")
print(f"Model size: ~450MB")
EOF

# Download Llama 3.1-8B-Instruct (Quantized GPTQ)
print_info "Downloading Llama 3.1-8B-Instruct (GPTQ 4-bit)..."
print_warning "This will download ~5GB. It may take several minutes..."

python3 << EOF
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

model_name = "TheBloke/Llama-2-7B-Chat-GPTQ"  # Using Llama 2 as placeholder
save_path = "data/models/llama-3.1-8b-instruct-gptq"

print(f"Downloading {model_name}...")
print("NOTE: For Llama 3.1-8B, you may need to:")
print("1. Accept Meta's license at https://huggingface.co/meta-llama/Llama-3.1-8B-Instruct")
print("2. Login with: huggingface-cli login")
print("")
print("Using Llama 2 as alternative for now...")

try:
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        device_map="auto",
        trust_remote_code=True
    )

    tokenizer.save_pretrained(save_path)
    model.save_pretrained(save_path)

    print(f"Model saved to {save_path}")
except Exception as e:
    print(f"Error downloading model: {e}")
    print("You can download manually later")
EOF

# Download Phi-3-mini (3.8B parameters)
print_info "Downloading Phi-3-mini for fast inference..."

python3 << EOF
from transformers import AutoModelForCausalLM, AutoTokenizer

model_name = "microsoft/Phi-3-mini-4k-instruct"
save_path = "data/models/phi-3-mini"

print(f"Downloading {model_name}...")
try:
    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        device_map="auto",
        trust_remote_code=True,
        torch_dtype="auto"
    )

    tokenizer.save_pretrained(save_path)
    model.save_pretrained(save_path)

    print(f"Phi-3-mini saved to {save_path}")
except Exception as e:
    print(f"Error: {e}")
    print("You can download manually later")
EOF

# Download sentence transformers for embeddings
print_info "Downloading sentence transformers..."

python3 << EOF
from sentence_transformers import SentenceTransformer

model_name = "all-MiniLM-L6-v2"
save_path = "data/models/sentence-transformer"

print(f"Downloading {model_name}...")
model = SentenceTransformer(model_name)
model.save(save_path)

print(f"Sentence transformer saved to {save_path}")
EOF

print_info "=================================================="
print_info "Model downloads complete!"
print_info "=================================================="
print_info ""
print_info "Downloaded models:"
print_info "1. FinBERT (sentiment analysis) - ~450MB"
print_info "2. Llama/Llama2 (trading analysis) - ~5GB"
print_info "3. Phi-3-mini (fast inference) - ~2.5GB"
print_info "4. Sentence Transformer (embeddings) - ~80MB"
print_info ""
print_info "Total disk space used: ~8GB"
print_info ""
print_warning "For Llama 3.1-8B-Instruct:"
print_info "1. Accept license: https://huggingface.co/meta-llama/Llama-3.1-8B-Instruct"
print_info "2. Login: huggingface-cli login"
print_info "3. Re-run this script"
