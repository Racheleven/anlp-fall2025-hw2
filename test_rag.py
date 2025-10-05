#!/usr/bin/env python3
"""
Test Script for Pittsburgh Events RAG System
匹兹堡活动RAG系统测试脚本

This script tests the basic functionality of the RAG system.
"""

import sys
from pathlib import Path

# Add the current directory to Python path
sys.path.append(str(Path(__file__).parent))

from rag import PittsburghEventsRAG

def test_data_loading():
    """Test data loading functionality"""
    print("🧪 Testing data loading...")
    
    try:
        rag = PittsburghEventsRAG(data_path=".", use_local_models=True)
        rag.load_data()
        
        summary = rag.get_event_summary()
        print(f"✅ Data loaded successfully!")
        print(f"   Total documents: {summary['total_documents']}")
        print(f"   Categories: {summary['categories']}")
        
        return True
    except Exception as e:
        print(f"❌ Data loading failed: {e}")
        return False

def test_vectorstore_building():
    """Test vector store building"""
    print("\n🧪 Testing vector store building...")
    
    try:
        rag = PittsburghEventsRAG(data_path=".", use_local_models=True)
        rag.load_data()
        rag.build_vectorstore()
        
        print("✅ Vector store built successfully!")
        return True
    except Exception as e:
        print(f"❌ Vector store building failed: {e}")
        return False

def test_query_functionality():
    """Test query functionality"""
    print("\n🧪 Testing query functionality...")
    
    try:
        rag = PittsburghEventsRAG(data_path=".", use_local_models=True)
        rag.load_data()
        rag.build_vectorstore()
        
        # Test queries
        test_questions = [
            "What food festivals are available?",
            "Tell me about CMU events",
            "Banana Split Festival activities"
        ]
        
        for question in test_questions:
            print(f"\n   Testing: {question}")
            result = rag.query(question)
            
            if result['answer'] and result['relevant_documents']:
                print(f"   ✅ Query successful")
                print(f"   📄 Found {len(result['relevant_documents'])} relevant documents")
            else:
                print(f"   ⚠️  Query returned limited results")
        
        print("✅ Query functionality test completed!")
        return True
    except Exception as e:
        print(f"❌ Query functionality test failed: {e}")
        return False

def test_vectorstore_save_load():
    """Test vector store save and load functionality"""
    print("\n🧪 Testing vector store save/load...")
    
    try:
        # Build and save
        rag = PittsburghEventsRAG(data_path=".", use_local_models=True)
        rag.load_data()
        rag.build_vectorstore()
        rag.save_vectorstore("test_vectorstore")
        
        # Load in new instance
        rag2 = PittsburghEventsRAG(data_path=".", use_local_models=True)
        rag2.load_vectorstore("test_vectorstore")
        
        # Test query on loaded vectorstore
        result = rag2.query("What food festivals are available?")
        
        if result['answer'] and result['relevant_documents']:
            print("✅ Vector store save/load successful!")
            return True
        else:
            print("⚠️  Vector store loaded but query failed")
            return False
            
    except Exception as e:
        print(f"❌ Vector store save/load failed: {e}")
        return False
    finally:
        # Clean up test files
        import shutil
        try:
            shutil.rmtree("test_vectorstore")
        except:
            pass

def run_comprehensive_test():
    """Run all tests"""
    print("🚀 Starting Pittsburgh Events RAG System Tests")
    print("=" * 60)
    
    tests = [
        ("Data Loading", test_data_loading),
        ("Vector Store Building", test_vectorstore_building),
        ("Query Functionality", test_query_functionality),
        ("Vector Store Save/Load", test_vectorstore_save_load)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Test Results Summary:")
    print("=" * 60)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:25} {status}")
        if result:
            passed += 1
    
    print("=" * 60)
    print(f"Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The RAG system is working correctly.")
    else:
        print("⚠️  Some tests failed. Please check the error messages above.")
    
    return passed == total

def demo_queries():
    """Demonstrate example queries"""
    print("\n🎯 Running Demo Queries")
    print("=" * 40)
    
    try:
        rag = PittsburghEventsRAG(data_path=".", use_local_models=True)
        rag.load_data()
        rag.build_vectorstore()
        
        demo_questions = [
            "What food festivals are available in Pittsburgh?",
            "Tell me about the Banana Split Festival activities",
            "What entertainment is available at Little Italy Days?",
            "When is Pittsburgh Restaurant Week?",
            "What CMU campus events are scheduled?"
        ]
        
        for i, question in enumerate(demo_questions, 1):
            print(f"\n{i}. Q: {question}")
            result = rag.query(question)
            
            # Show answer preview
            answer_preview = result['answer'][:200] + "..." if len(result['answer']) > 200 else result['answer']
            print(f"   A: {answer_preview}")
            
            # Show source count
            if result['relevant_documents']:
                print(f"   📚 Sources: {len(result['relevant_documents'])} documents")
            
    except Exception as e:
        print(f"❌ Demo queries failed: {e}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test the Pittsburgh Events RAG System")
    parser.add_argument("--demo", action="store_true", help="Run demo queries")
    parser.add_argument("--test", action="store_true", help="Run comprehensive tests")
    
    args = parser.parse_args()
    
    if args.demo:
        demo_queries()
    elif args.test:
        run_comprehensive_test()
    else:
        print("Pittsburgh Events RAG System Test Script")
        print("Usage:")
        print("  python test_rag.py --test    # Run comprehensive tests")
        print("  python test_rag.py --demo    # Run demo queries")
        print("  python test_rag.py --test --demo  # Run both")
        
        if input("\nRun comprehensive tests? (y/n): ").lower() == 'y':
            run_comprehensive_test()
        
        if input("\nRun demo queries? (y/n): ").lower() == 'y':
            demo_queries()
