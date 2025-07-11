import requests
import json
import colorama
import os
from pathlib import Path

class OllamaClient:
    def __init__(self, host="http://localhost", port=11434, model=None):
        self.base_url = f"{host}:{port}"
        self.model = model or self._get_model()

    def test_connection(self) -> bool:
        """Test if Ollama is running and accessible."""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except Exception:
            return False

    def _get_model(self) -> str:
        """Get model from config file or prompt user."""
        config_path = Path.home() / ".uxt" / "config.json"
        
        # Try to load from config
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    if 'model' in config and config['model']:
                        return config['model']
            except Exception:
                pass
        
        # Check if Ollama is running
        if not self.test_connection():
            print(f"{colorama.Fore.RED}Cannot connect to Ollama at {self.base_url}{colorama.Style.RESET_ALL}")
            print("Please ensure Ollama is running:")
            print("  1. Install Ollama: https://ollama.ai")
            print("  2. Start Ollama: ollama serve")
            print("  3. Pull a model: ollama pull llama3:8b")
            raise RuntimeError("Ollama not available")
        
        # Get available models from Ollama
        available_models = self._list_models()
        
        if not available_models:
            print(f"{colorama.Fore.RED}No models found in Ollama. Please install a model first.{colorama.Style.RESET_ALL}")
            print("Example: ollama pull llama3:8b")
            print("Or: ollama pull codellama")
            raise RuntimeError("No models available")
        
        # Show available models
        print(f"\n{colorama.Fore.YELLOW}Available models:{colorama.Style.RESET_ALL}")
        for i, model in enumerate(available_models, 1):
            print(f"  {i}. {model}")
        
        # Get user choice
        while True:
            choice = input(f"\n{colorama.Fore.YELLOW}Select model (1-{len(available_models)}) or enter model name:{colorama.Style.RESET_ALL} ").strip()
            
            # Check if it's a number
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(available_models):
                    selected_model = available_models[idx]
                    break
            except ValueError:
                pass
            
            # Check if it's a valid model name
            if choice in available_models:
                selected_model = choice
                break
            
            print(f"{colorama.Fore.RED}Invalid choice. Please try again.{colorama.Style.RESET_ALL}")
        
        # Save to config
        try:
            config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(config_path, 'w') as f:
                json.dump({'model': selected_model}, f, indent=2)
            print(f"{colorama.Fore.GREEN}Model '{selected_model}' saved to config.{colorama.Style.RESET_ALL}")
        except Exception as e:
            print(f"{colorama.Fore.YELLOW}Warning: Could not save config: {e}{colorama.Style.RESET_ALL}")
        
        return selected_model

    def _list_models(self) -> list:
        """Get list of available models from Ollama."""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=10)
            response.raise_for_status()
            data = response.json()
            return [model['name'] for model in data.get('models', [])]
        except Exception:
            return []

    def get_model_info(self) -> dict:
        """Get information about the current model."""
        try:
            response = requests.post(
                f"{self.base_url}/api/show",
                json={"name": self.model},
                timeout=10
            )
            if response.status_code == 200:
                return response.json()
        except Exception:
            pass
        return {}

    def chat(self, prompt: str) -> str:
        """Send a chat request to Ollama using the native API format."""
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False
        }
        headers = {"Content-Type": "application/json"}
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=60)
            response.raise_for_status()
            result = response.json()
            
            # Ollama's native response structure
            return result.get("response", "")
            
        except requests.exceptions.ConnectionError:
            return "[ERROR] Could not connect to Ollama. Please ensure Ollama is running."
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                return f"[ERROR] Model '{self.model}' not found. Please install it with: ollama pull {self.model}"
            elif e.response.status_code == 400:
                return f"[ERROR] Bad request. Check if model '{self.model}' is valid and properly loaded."
            return f"[ERROR] Ollama HTTP error ({e.response.status_code}): {e}"
        except Exception as e:
            return f"[ERROR] Ollama request failed: {e}"
