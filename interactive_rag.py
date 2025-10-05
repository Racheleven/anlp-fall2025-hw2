#!/usr/bin/env python3
"""
Interactive RAG System Interface
交互式RAG系统界面

This provides a simple command-line interface for querying the Pittsburgh Events RAG system.
"""

import sys
import os
from pathlib import Path

# Add the current directory to Python path
sys.path.append(str(Path(__file__).parent))

from rag import PittsburghEventsRAG

class InteractiveRAGInterface:
    """Interactive interface for the RAG system"""
    
    def __init__(self):
        self.rag = None
        self.initialized = False
    
    def initialize_system(self, use_openai: bool = False, api_key: str = None):
        """Initialize the RAG system"""
        print("🚀 Initializing Pittsburgh Events RAG System...")
        
        try:
            self.rag = PittsburghEventsRAG(
                data_path=".",
                use_local_models=not use_openai,
                openai_api_key=api_key
            )
            
            print("📁 Loading data...")
            self.rag.load_data()
            
            print("🔍 Building vector store...")
            self.rag.build_vectorstore()
            
            if use_openai and api_key:
                print("🤖 Setting up OpenAI integration...")
                self.rag.setup_retrieval_chain()
            
            self.initialized = True
            print("✅ System initialized successfully!")
            
            # Show summary
            summary = self.rag.get_event_summary()
            print(f"\n📊 Data Summary:")
            print(f"   Total documents: {summary['total_documents']}")
            print(f"   Categories: {list(summary['categories'].keys())}")
            print(f"   File types: {list(summary['file_types'].keys())}")
            
        except Exception as e:
            print(f"❌ Error initializing system: {e}")
            return False
        
        return True
    
    def run_interactive_session(self):
        """Run the interactive query session"""
        if not self.initialized:
            print("❌ System not initialized. Please run initialize_system() first.")
            return
        
        print("\n" + "="*60)
        print("🎯 Pittsburgh Events RAG System - Interactive Mode")
        print("="*60)
        print("Type your questions about Pittsburgh events and food festivals!")
        print("Commands:")
        print("  'help' - Show this help message")
        print("  'summary' - Show data summary")
        print("  'quit' or 'exit' - Exit the program")
        print("="*60)
        
        while True:
            try:
                question = input("\n❓ Your question: ").strip()
                
                if question.lower() in ['quit', 'exit', 'q']:
                    print("👋 Goodbye!")
                    break
                elif question.lower() == 'help':
                    self.show_help()
                elif question.lower() == 'summary':
                    self.show_summary()
                elif question:
                    self.process_query(question)
                else:
                    print("Please enter a question or command.")
                    
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"❌ Error: {e}")
    
    def process_query(self, question: str):
        """Process a user query"""
        print(f"\n🔍 Searching for: {question}")
        print("-" * 50)
        
        try:
            result = self.rag.query(question)
            
            # Display answer
            print(f"💡 Answer:")
            print(result['answer'])
            
            # Display sources
            if result['relevant_documents']:
                print(f"\n📚 Sources ({len(result['relevant_documents'])} documents):")
                for i, doc in enumerate(result['relevant_documents'][:3], 1):
                    source = doc.metadata.get('source', 'Unknown')
                    filename = doc.metadata.get('filename', 'Unknown')
                    category = doc.metadata.get('category', 'Unknown')
                    print(f"   {i}. {filename} ({category})")
                    print(f"      Preview: {doc.page_content[:100]}...")
            
        except Exception as e:
            print(f"❌ Error processing query: {e}")
    
    def show_help(self):
        """Show help information"""
        print("\n📖 Help - Pittsburgh Events RAG System")
        print("-" * 40)
        print("This system can answer questions about:")
        print("• Pittsburgh food festivals and events")
        print("• CMU campus events and activities")
        print("• Downtown Pittsburgh events")
        print("• Restaurant weeks and food-related activities")
        print("\nExample questions:")
        print("• 'What food festivals are happening in Pittsburgh?'")
        print("• 'Tell me about the Banana Split Festival'")
        print("• 'What activities are available at Little Italy Days?'")
        print("• 'When is Pittsburgh Restaurant Week?'")
        print("• 'What CMU campus events are scheduled?'")
    
    def show_summary(self):
        """Show data summary"""
        if not self.initialized:
            print("❌ System not initialized.")
            return
        
        summary = self.rag.get_event_summary()
        print(f"\n📊 Data Summary:")
        print(f"   Total documents: {summary['total_documents']}")
        print(f"   Categories: {summary['categories']}")
        print(f"   File types: {summary['file_types']}")
        
        print(f"\n📁 Events by Category:")
        for category, events in summary['events_by_category'].items():
            print(f"   {category}:")
            for event, count in events.items():
                print(f"     - {event}: {count} documents")


def main():
    """Main function"""
    interface = InteractiveRAGInterface()
    
    print("🎯 Pittsburgh Events RAG System")
    print("=" * 40)
    
    # Ask user for configuration
    print("\nConfiguration options:")
    print("1. Use local models (recommended for privacy)")
    print("2. Use OpenAI API (requires API key)")
    
    choice = input("\nChoose option (1 or 2): ").strip()
    
    if choice == "2":
        api_key = input("Enter your OpenAI API key: ").strip()
        if not api_key:
            print("❌ API key required for OpenAI option.")
            return
        success = interface.initialize_system(use_openai=True, api_key=api_key)
    else:
        success = interface.initialize_system(use_openai=False)
    
    if success:
        interface.run_interactive_session()
    else:
        print("❌ Failed to initialize system.")


if __name__ == "__main__":
    main()
