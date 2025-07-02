import requests
import json
import colorama

class OllamaClient:
    def __init__(self, host="http://localhost", port=11434, model=input(f"[ What {colorama.Fore.YELLOW}model{colorama.Style.RESET_ALL} to use for your {colorama.Fore.YELLOW}agent{colorama.Style.RESET_ALL}? Make sure you have it downloaded via {colorama.Fore.YELLOW}Ollama{colorama.Style.RESET_ALL} already. ] > ")):
        self.url = f"{host}:{port}/v1/chat/completions"
        self.model = model

    def chat(self, prompt: str) -> str:
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False
        }
        headers = {"Content-Type": "application/json"}
        try:
            response = requests.post(self.url, json=payload, headers=headers, timeout=60)
            response.raise_for_status()
            result = response.json()
            # Ollama's response structure: choices[0].message.content
            return result["choices"][0]["message"]["content"]
        except Exception as e:
            return f"[ERROR] Ollama request failed: {e}"
