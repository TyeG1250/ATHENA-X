#!/bin/bash
#
# ATHENA-X GPU Support Installation Script
# Installs PyTorch with CUDA 12.x/13.x support
#

set -e

echo "=========================================="
echo "  ATHENA-X GPU Support Installation"
echo "=========================================="
echo ""

# Check if CUDA is available
if command -v nvidia-smi &> /dev/null; then
    echo "✓ NVIDIA GPU detected:"
    nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader
    echo ""

    # Get CUDA version
    CUDA_VERSION=$(nvidia-smi | grep "CUDA Version" | awk '{print $9}' | cut -d'.' -f1)
    echo "CUDA Toolkit Version: $CUDA_VERSION"
    echo ""
else
    echo "✗ No NVIDIA GPU detected or nvidia-smi not found"
    echo "Please install NVIDIA drivers first"
    exit 1
fi

# Determine PyTorch installation command based on CUDA version
if [ "$CUDA_VERSION" -ge 12 ]; then
    echo "Installing PyTorch for CUDA 12.x/13.x..."
    TORCH_INDEX="https://download.pytorch.org/whl/cu121"
else
    echo "Installing PyTorch for CUDA 11.x..."
    TORCH_INDEX="https://download.pytorch.org/whl/cu118"
fi

# Install PyTorch with CUDA support
echo ""
echo "Installing PyTorch, torchvision, and torchaudio..."
pip install --upgrade torch torchvision torchaudio --index-url $TORCH_INDEX

# Install transformers with GPU support
echo ""
echo "Installing transformers and accelerate..."
pip install transformers>=4.35.0 accelerate>=0.24.0

# Install optional GPU-accelerated packages
echo ""
echo "Installing additional GPU packages..."
pip install bitsandbytes>=0.41.0  # 4-bit quantization
pip install peft>=0.6.0  # Parameter-efficient fine-tuning

# Test GPU availability
echo ""
echo "=========================================="
echo "  Testing GPU Configuration"
echo "=========================================="
python -c "
import torch
print(f'PyTorch version: {torch.__version__}')
print(f'CUDA available: {torch.cuda.is_available()}')
if torch.cuda.is_available():
    print(f'CUDA version: {torch.version.cuda}')
    print(f'cuDNN version: {torch.backends.cudnn.version()}')
    print(f'GPU device: {torch.cuda.get_device_name(0)}')
    print(f'GPU memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB')

    # Test tensor operations
    x = torch.randn(1000, 1000).cuda()
    y = torch.randn(1000, 1000).cuda()
    z = torch.mm(x, y)
    print(f'✓ GPU tensor operations working')
else:
    print('✗ CUDA not available - check installation')
"

echo ""
echo "=========================================="
echo "  Installation Complete!"
echo "=========================================="
echo ""
echo "GPU support has been installed successfully."
echo "You can now use GPU acceleration for:"
echo "  - FinBERT sentiment analysis"
echo "  - Llama 3.1 8B fine-tuning"
echo "  - Transformer models"
echo ""
