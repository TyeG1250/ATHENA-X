# Quick Answer: Llama 3.1 Setup

## Your Question:
> "or do i download the model via huggingface and put it in the model folder?"

## Short Answer:

**It depends on what you already have!**

---

## Check What You Have

Run this command:

```powershell
docker ps -a | findstr llama
# or
docker ps -a | findstr ollama
```

### Scenario 1: You See "ollama" Container ✅

**You already have Ollama!**
- ✅ **NO need to download from Hugging Face**
- ✅ **NO need to put files in models folder**
- Ollama manages everything automatically

**What to do:**
```powershell
# Start Ollama (if not running)
docker start ollama

# Download model (Ollama handles it)
docker exec -it ollama ollama pull llama3.1:8b

# Test it
.\docker-run.ps1 shell
python scripts/test_llama.py
```

**Done!** No manual downloads needed.

---

### Scenario 2: No Ollama Container ❓

**Two options:**

#### Option A: Install Ollama (Easiest) ⭐

```powershell
# Create Ollama container
docker run -d -p 11434:11434 --name ollama ollama/ollama

# Download model
docker exec -it ollama ollama pull llama3.1:8b

# Test
curl http://localhost:11434/api/tags
```

**Pros:** Easy, no manual downloads
**Cons:** Runs as separate service

---

#### Option B: Download from Hugging Face (Advanced)

**YES, download model files and put in `data/models/` folder**

**Steps:**

1. **Get Hugging Face Access:**
   - Create account: https://huggingface.co/join
   - Accept license: https://huggingface.co/meta-llama/Meta-Llama-3.1-8B-Instruct
   - Get token: https://huggingface.co/settings/tokens

2. **Login:**
   ```bash
   pip install huggingface_hub
   huggingface-cli login
   # Paste your token
   ```

3. **Download Model (16GB):**
   ```powershell
   .\docker-run.ps1 shell

   # Run download script
   python scripts/download_llama_hf.py
   ```

   This downloads to:
   ```
   data/models/meta-llama/Meta-Llama-3.1-8B-Instruct/
   ```

4. **Install Dependencies:**
   ```bash
   pip install transformers torch accelerate bitsandbytes
   ```

5. **Test:**
   ```python
   from src.llm.llama_hf import LlamaAdvisorHF
   advisor = LlamaAdvisorHF()
   ```

**Pros:** Full control, can fine-tune
**Cons:** 16GB download, more complex

---

## Comparison

| Feature | Ollama | Hugging Face |
|---------|--------|--------------|
| **Setup** | ✅ Easy | ❌ Complex |
| **Download Size** | 5GB (managed) | 16GB (manual) |
| **Control** | Basic | Full |
| **Fine-tuning** | ❌ No | ✅ Yes |
| **Speed** | Fast | Faster (no API) |
| **Best For** | Quick start | Advanced users |

---

## My Recommendation

**Since you said "i downloaded the local llama 3.1 through docker":**

You probably have **Ollama** already. Just run:

```powershell
# Check if you have it
docker ps | findstr ollama

# If yes, pull the model
docker exec -it ollama ollama pull llama3.1:8b

# Test it
.\docker-run.ps1 shell
python scripts/test_llama.py
```

**If this works → You're done! No Hugging Face download needed.**

---

## When to Use Hugging Face Method?

Use Hugging Face (download to `data/models/`) only if:
- ✅ You want to fine-tune Llama for trading
- ✅ You need full control over model parameters
- ✅ You want to modify the model
- ✅ You want offline operation (no external services)

Otherwise, **stick with Ollama** - it's much easier!

---

## Full Documentation

For complete details on both methods:
- See **`LLAMA_INTEGRATION.md`**
- Method 1: Ollama (recommended)
- Method 2: Hugging Face (advanced)

---

## Quick Test

To find out which method you're using:

```powershell
# Test Ollama
curl http://localhost:11434/api/tags

# If that works → You have Ollama
# If that fails → You need to choose a method
```

---

**TL;DR:**

- **Have Ollama?** → No HF download needed
- **Want easy setup?** → Use Ollama (Method 1)
- **Want fine-tuning control?** → Download from HF to `data/models/` (Method 2)
