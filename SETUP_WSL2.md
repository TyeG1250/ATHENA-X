# WSL2 Setup Guide for ATHENA-X

## Why WSL2?

WSL2 is recommended for ATHENA-X because:
- ✅ Better Docker performance
- ✅ Native Linux environment for scripts
- ✅ CUDA support for GPU acceleration
- ✅ Better compatibility with Python packages

## Installation Steps

### 1. Enable WSL2 (PowerShell as Administrator)

```powershell
# Enable WSL
wsl --install

# Or manually:
dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart
dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart

# Restart your computer
```

### 2. Set WSL2 as Default

```powershell
wsl --set-default-version 2
```

### 3. Install Ubuntu 24.04

```powershell
# Option 1: From Microsoft Store
# Search for "Ubuntu 24.04 LTS" and install

# Option 2: Command line
wsl --install -d Ubuntu-24.04
```

### 4. Verify Installation

```bash
wsl -l -v
# Should show Ubuntu-24.04 with VERSION 2
```

### 5. Access WSL2

```powershell
wsl
# Or
ubuntu
```

## ATHENA-X Setup in WSL2

Once in WSL2, navigate to your project:

```bash
cd /mnt/g/Users/TMG/ATHENA-X

# Run setup
./scripts/setup_environment.sh
```

## Alternative: Run on Windows

ATHENA-X can also run on Windows with:
- Python 3.10+ installed
- Docker Desktop for Windows
- Git Bash or PowerShell

Just note that some scripts may need minor adjustments for Windows paths.

## Current Status

- ✅ Phase 1 code is cross-platform compatible
- ⚠️ WSL2 setup needed for optimal performance
- ✅ Can proceed with Phase 2 on either platform
