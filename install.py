#!/usr/bin/env python3
"""
Installation Script for Pittsburgh Events RAG System
匹兹堡活动RAG系统安装脚本

This script helps install all required dependencies for the RAG system.
"""

import subprocess
import sys
import os
from pathlib import Path

def run_command(command, description):
    """Run a command and handle errors"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed:")
        print(f"   Error: {e.stderr}")
        return False

def check_python_version():
    """Check if Python version is compatible"""
    print("🐍 Checking Python version...")
    
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print(f"❌ Python 3.8+ required. Current version: {version.major}.{version.minor}")
        return False
    
    print(f"✅ Python {version.major}.{version.minor}.{version.micro} is compatible")
    return True

def install_dependencies():
    """Install required dependencies"""
    print("\n📦 Installing dependencies...")
    
    # Check if requirements.txt exists
    requirements_file = Path("requirements.txt")
    if not requirements_file.exists():
        print("❌ requirements.txt not found!")
        return False
    
    # Install dependencies
    success = run_command(
        f"{sys.executable} -m pip install -r requirements.txt",
        "Installing Python packages"
    )
    
    return success

def verify_installation():
    """Verify that key packages are installed"""
    print("\n🔍 Verifying installation...")
    
    required_packages = [
        "pandas",
        "numpy", 
        "langchain",
        "faiss-cpu",
        "sentence-transformers"
    ]
    
    all_installed = True
    
    for package in required_packages:
        try:
            __import__(package.replace("-", "_"))
            print(f"✅ {package} is installed")
        except ImportError:
            print(f"❌ {package} is not installed")
            all_installed = False
    
    return all_installed

def test_basic_functionality():
    """Test basic functionality after installation"""
    print("\n🧪 Testing basic functionality...")
    
    try:
        # Test imports
        import pandas as pd
        import numpy as np
        from langchain.text_splitter import RecursiveCharacterTextSplitter
        from langchain.embeddings import HuggingFaceEmbeddings
        from langchain.vectorstores import FAISS
        
        print("✅ All core imports successful")
        
        # Test basic functionality
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000)
        print("✅ Text splitter created successfully")
        
        embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
        print("✅ Embeddings model loaded successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ Basic functionality test failed: {e}")
        return False

def create_environment_setup():
    """Create environment setup instructions"""
    print("\n📝 Creating environment setup guide...")
    
    setup_guide = """
# Environment Setup Guide

## Option 1: Using pip (Recommended)

```bash
# Install dependencies
pip install -r requirements.txt

# Run the system
python interactive_rag.py
```

## Option 2: Using conda

```bash
# Create conda environment
conda create -n pittsburgh-rag python=3.9

# Activate environment
conda activate pittsburgh-rag

# Install dependencies
pip install -r requirements.txt

# Run the system
python interactive_rag.py
```

## Option 3: Using virtual environment

```bash
# Create virtual environment
python -m venv pittsburgh-rag-env

# Activate environment (Linux/Mac)
source pittsburgh-rag-env/bin/activate

# Activate environment (Windows)
pittsburgh-rag-env\\Scripts\\activate

# Install dependencies
pip install -r requirements.txt

# Run the system
python interactive_rag.py
```

## Troubleshooting

1. **CUDA issues**: If you have CUDA available, you can install `faiss-gpu` instead of `faiss-cpu`
2. **Memory issues**: Reduce chunk_size in the code if you encounter memory problems
3. **Model download issues**: The first run will download models (~400MB), ensure stable internet connection
"""
    
    with open("SETUP_GUIDE.md", "w", encoding="utf-8") as f:
        f.write(setup_guide)
    
    print("✅ Setup guide created: SETUP_GUIDE.md")

def main():
    """Main installation function"""
    print("🚀 Pittsburgh Events RAG System - Installation Script")
    print("=" * 60)
    
    # Check Python version
    if not check_python_version():
        print("\n❌ Installation aborted due to Python version incompatibility")
        return False
    
    # Install dependencies
    if not install_dependencies():
        print("\n❌ Installation aborted due to dependency installation failure")
        return False
    
    # Verify installation
    if not verify_installation():
        print("\n❌ Installation verification failed")
        return False
    
    # Test basic functionality
    if not test_basic_functionality():
        print("\n❌ Basic functionality test failed")
        return False
    
    # Create setup guide
    create_environment_setup()
    
    print("\n" + "=" * 60)
    print("🎉 Installation completed successfully!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Run the interactive interface: python interactive_rag.py")
    print("2. Or run tests: python test_rag.py --test")
    print("3. Check SETUP_GUIDE.md for detailed usage instructions")
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        if not success:
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n👋 Installation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Installation failed with error: {e}")
        sys.exit(1)
