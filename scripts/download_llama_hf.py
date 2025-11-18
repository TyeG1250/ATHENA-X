#!/usr/bin/env python3
"""
Download Llama 3.1 model from Hugging Face
Stores in data/models/ for direct use in ATHENA-X
"""

import os
from pathlib import Path
from huggingface_hub import snapshot_download


def download_llama_model(
    model_id: str = "meta-llama/Meta-Llama-3.1-8B-Instruct",
    cache_dir: str = "data/models",
    use_auth_token: bool = True
):
    """
    Download Llama 3.1 model from Hugging Face

    Args:
        model_id: Hugging Face model ID
        cache_dir: Where to store model files
        use_auth_token: Whether to use HF auth token (required for Llama)

    Note:
        You need to:
        1. Accept Meta's license at: https://huggingface.co/meta-llama/Meta-Llama-3.1-8B-Instruct
        2. Get HF token: https://huggingface.co/settings/tokens
        3. Set token: huggingface-cli login
    """

    print("=" * 60)
    print("  Llama 3.1 Model Download")
    print("=" * 60)
    print(f"\nModel: {model_id}")
    print(f"Destination: {cache_dir}")
    print()

    # Create cache directory
    Path(cache_dir).mkdir(parents=True, exist_ok=True)

    # Check for auth token
    if use_auth_token:
        token_file = Path.home() / ".cache" / "huggingface" / "token"
        if not token_file.exists():
            print("⚠️  WARNING: No Hugging Face token found!")
            print()
            print("To download Llama 3.1, you need to:")
            print("1. Create account: https://huggingface.co/join")
            print("2. Accept license: https://huggingface.co/meta-llama/Meta-Llama-3.1-8B-Instruct")
            print("3. Get token: https://huggingface.co/settings/tokens")
            print("4. Login: huggingface-cli login")
            print()
            return False

    print("Downloading model... (this will take 10-30 minutes)")
    print("Model size: ~16GB")
    print()

    try:
        model_path = snapshot_download(
            repo_id=model_id,
            cache_dir=cache_dir,
            resume_download=True,
            local_files_only=False
        )

        print()
        print("=" * 60)
        print("✓ Download complete!")
        print("=" * 60)
        print(f"\nModel saved to: {model_path}")
        print()
        print("You can now use Llama 3.1 directly in ATHENA-X")
        print("See: LLAMA_INTEGRATION.md for usage examples")
        print()

        return True

    except Exception as e:
        print()
        print("=" * 60)
        print("✗ Download failed!")
        print("=" * 60)
        print(f"\nError: {e}")
        print()

        if "gated repo" in str(e).lower() or "unauthorized" in str(e).lower():
            print("This model requires authorization.")
            print()
            print("Steps to fix:")
            print("1. Visit: https://huggingface.co/meta-llama/Meta-Llama-3.1-8B-Instruct")
            print("2. Click 'Agree and access repository'")
            print("3. Get your token: https://huggingface.co/settings/tokens")
            print("4. Run: huggingface-cli login")
            print("5. Paste your token")
            print("6. Run this script again")
            print()

        return False


def download_quantized_model(
    model_id: str = "TheBloke/Llama-2-7B-Chat-GPTQ",
    cache_dir: str = "data/models"
):
    """
    Download quantized (smaller) version

    Quantized models:
    - 4-bit GPTQ: ~4GB (faster, less RAM)
    - Full precision: ~16GB (slower, more RAM)
    """

    print("Downloading quantized model (4GB instead of 16GB)...")

    try:
        model_path = snapshot_download(
            repo_id=model_id,
            cache_dir=cache_dir,
            resume_download=True
        )

        print(f"✓ Downloaded to: {model_path}")
        return True

    except Exception as e:
        print(f"✗ Error: {e}")
        return False


if __name__ == "__main__":
    import sys

    print()
    print("Choose download option:")
    print("1. Llama 3.1 8B Instruct (16GB) - Official Meta model")
    print("2. Llama 3.1 8B GPTQ (4GB) - Quantized, faster")
    print("3. Cancel")
    print()

    choice = input("Enter choice (1-3): ").strip()

    if choice == "1":
        download_llama_model()
    elif choice == "2":
        download_quantized_model()
    else:
        print("Cancelled.")
        sys.exit(0)
