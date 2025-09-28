"""
Simple Ollama Test
Test Ollama connection and basic functionality
"""

import os
import requests
import asyncio
from dotenv import load_dotenv

load_dotenv()

async def test_ollama_connection():
    """
    Test basic Ollama connection and functionality
    """
    print("🔗 Testing Ollama Connection")
    print("=" * 40)
    
    ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    ollama_model = os.getenv("OLLAMA_MODEL", "llama3.1")
    
    print(f"✅ Ollama URL: {ollama_url}")
    print(f"✅ Ollama Model: {ollama_model}")
    
    # Test 1: Check if Ollama server is running
    print("\n1️⃣ Testing Ollama Server Connection")
    print("-" * 30)
    
    try:
        response = requests.get(f"{ollama_url}/api/tags", timeout=5)
        if response.status_code == 200:
            models = response.json().get("models", [])
            model_names = [model["name"] for model in models]
            print(f"✅ Ollama server is running")
            print(f"✅ Available models: {model_names}")
            
            if ollama_model not in model_names:
                print(f"⚠️  Model '{ollama_model}' not found. Available models: {model_names}")
                if model_names:
                    # Use the full model name with tag
                    ollama_model = model_names[0]
                    print(f"✅ Using model: {ollama_model}")
        else:
            print(f"❌ Ollama server responded with status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Ollama server not available: {e}")
        return False
    
    # Test 2: Test basic query
    print("\n2️⃣ Testing Basic Query")
    print("-" * 30)
    
    try:
        test_prompt = "Hello! Please respond with 'Ollama is working correctly.'"
        response = requests.post(
            f"{ollama_url}/api/generate",
            json={
                "model": ollama_model,
                "prompt": test_prompt,
                "stream": False
            },
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            response_text = result.get("response", "")
            print(f"✅ Query successful!")
            print(f"📝 Response: {response_text[:100]}...")
            return True
        else:
            print(f"❌ Query failed with status {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Query failed: {e}")
        return False

def main():
    """
    Main test function
    """
    print("🚀 Ollama Integration Test")
    print("=" * 50)
    
    # Run the test
    success = asyncio.run(test_ollama_connection())
    
    if success:
        print("\n🎉 Ollama integration test completed successfully!")
        print("\nNext steps:")
        print("1. Run the full graph integration test: python test_graph_integration.py")
        print("2. Test the API endpoints")
        print("3. Build your first graph!")
    else:
        print("\n❌ Ollama integration test failed!")
        print("\nTroubleshooting:")
        print("1. Make sure Ollama server is running: ollama serve")
        print("2. Check if the model is available: ollama list")
        print("3. Pull the model if needed: ollama pull llama3.1")

if __name__ == "__main__":
    main()
