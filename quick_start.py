#!/usr/bin/env python3
"""
Quick Start Script for Pittsburgh Events RAG System
匹兹堡活动RAG系统快速启动脚本

This script provides a quick way to get started with the RAG system.
"""

import sys
import os
from pathlib import Path

def check_dependencies():
    """Check if required dependencies are installed"""
    print("🔍 Checking dependencies...")
    
    required_packages = [
        "pandas",
        "numpy",
        "langchain", 
        "faiss-cpu",
        "sentence-transformers"
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace("-", "_"))
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package} (missing)")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n⚠️  Missing packages: {', '.join(missing_packages)}")
        print("Please run: python install.py")
        return False
    
    print("✅ All dependencies are installed!")
    return True

def quick_demo():
    """Run a quick demonstration"""
    print("\n🎯 Running Quick Demo")
    print("=" * 40)
    
    try:
        from rag import PittsburghEventsRAG
        
        # Initialize system
        print("🚀 Initializing RAG system...")
        rag = PittsburghEventsRAG(data_path=".", use_local_models=True)
        
        # Load data
        print("📁 Loading data...")
        rag.load_data()
        
        # Build vector store
        print("🔍 Building vector store...")
        rag.build_vectorstore()
        
        # Get summary
        summary = rag.get_event_summary()
        print(f"\n📊 Data Summary:")
        print(f"   Total documents: {summary['total_documents']}")
        print(f"   Categories: {list(summary['categories'].keys())}")
        
        # Demo queries
        demo_questions = [
            # "What food festivals are available in Pittsburgh?",
            # "Tell me about the Banana Split Festival",
            # "What activities are at Little Italy Days?",
            "When is Boozy Bingo"
        ]
        
        print(f"\n🎯 Demo Queries:")
        for i, question in enumerate(demo_questions, 1):
            print(f"\n{i}. Q: {question}")
            result = rag.query(question)
            
            # Show answer preview
            answer_preview = result['answer'][:150] + "..." if len(result['answer']) > 150 else result['answer']
            print(f"   A: {answer_preview}")
            
            if result['relevant_documents']:
                print(f"   📚 Sources: {len(result['relevant_documents'])} documents")
        
        print(f"\n✅ Demo completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        return False

def interactive_mode():
    """Start interactive mode"""
    print("\n🎯 Starting Interactive Mode")
    print("=" * 40)
    
    try:
        from interactive_rag import InteractiveRAGInterface
        
        interface = InteractiveRAGInterface()
        
        # Initialize with local models
        success = interface.initialize_system(use_openai=False)
        
        if success:
            interface.run_interactive_session()
        else:
            print("❌ Failed to initialize interactive mode")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Interactive mode failed: {e}")
        return False

def main():
    """Main function"""
    print("🚀 Pittsburgh Events RAG System - Quick Start")
    print("=" * 50)
    
    # Check dependencies
    # if not check_dependencies():
    #     print("\n❌ Please install dependencies first:")
    #     print("   python install.py")
    #     return
    
    print("\nWhat would you like to do?")
    print("1. Run quick demo")
    print("2. Start interactive mode")
    print("3. Run tests")
    print("4. Exit")
    
    while True:
        try:
            choice = input("\nEnter your choice (1-4): ").strip()
            
            if choice == "1":
                quick_demo()
                break
            elif choice == "2":
                interactive_mode()
                break
            elif choice == "3":
                print("\n🧪 Running tests...")
                os.system("python test_rag.py --test")
                break
            elif choice == "4":
                print("👋 Goodbye!")
                break
            else:
                print("Please enter a valid choice (1-4)")
                
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
