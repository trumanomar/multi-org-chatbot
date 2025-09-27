import requests

OLLAMA_API_URL = "http://localhost:11434/api/chat"  # default Ollama endpoint

def ollama_chat(user_query: str, context: str = "", system_prompt: str = "") -> str:
    payload = {
        "model": "llama3",  # غيّرها للموديل اللي عندك (مثلاً mistral, llama2)
        "messages": []
    }

    if system_prompt:
        payload["messages"].append({"role": "system", "content": system_prompt})

    if context:
        user_query = f"Context:\n{context}\n\nQuestion:\n{user_query}"

    payload["messages"].append({"role": "user", "content": user_query})

    try:
        response = requests.post(OLLAMA_API_URL, json=payload, stream=False)
        response.raise_for_status()
        data = response.json()

        if "message" in data and "content" in data["message"]:
            return data["message"]["content"]

        if isinstance(data, dict) and "messages" in data:
            return " ".join([m["content"] for m in data["messages"]])

        return str(data)

    except Exception as e:
        print(f"[ollama_chat] ERROR: {e}")
        return f"Error calling Ollama: {e}"
