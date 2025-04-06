import sys

# --- ANSI Color Codes ---
COLOR_GRAY = "\033[38;2;180;180;180m"
COLOR_RED = "\033[38;2;255;160;160m"
COLOR_YELLOW = "\033[38;2;255;255;180m"
COLOR_GREEN = "\033[38;2;160;255;160m"
COLOR_RESET = "\033[0m"

class LLMAgent:
    """Base class for LLM agents."""

    def __init__(self, temperature=0.1, system_prompt="", model_provider=None, model=None, api_key=None, base_url=None):
        self.temperature = temperature
        self.system_prompt = system_prompt
        self.model_provider = model_provider
        self.model = model
        self.api_key = api_key
        self.base_url = base_url
        self.llm = self._initialize_llm()

    def _initialize_llm(self):
        """Initializes the LangChain LLM object based on configuration."""
        if self.model_provider == "groq":
            if not self.api_key:
                print(f"{COLOR_RED}Error: GROQ_API_KEY not found in .env file.{COLOR_RESET}")
                sys.exit(1)
            try:
                from langchain_groq import ChatGroq
                return ChatGroq(temperature=self.temperature, groq_api_key=self.api_key, model_name=self.model)
            except ImportError:
                print(f"{COLOR_RED}Error: langchain-groq not installed. Please run 'pip install langchain-groq'{COLOR_RESET}")
                sys.exit(1)
            except Exception as e:
                print(f"{COLOR_RED}Error initializing Groq Chat: {e}{COLOR_RESET}")
                sys.exit(1)

        elif self.model_provider == "ollama":
            try:
                from langchain_community.chat_models import ChatOllama
                ollama_kwargs = {"model": self.model, "temperature": self.temperature}
                if self.base_url:
                    ollama_kwargs["base_url"] = self.base_url
                llm = ChatOllama(**ollama_kwargs)
                try:
                    llm.invoke("Respond with only 'OK'")
                except Exception as e:
                    print(f"{COLOR_RED}Error: Could not connect to Ollama or model '{self.model}' not available.")
                    print(f"Details: {e}{COLOR_RESET}")
                    print(f"{COLOR_YELLOW}Make sure Ollama is running and the model '{self.model}' is pulled (`ollama pull {self.model}`){COLOR_RESET}")
                    sys.exit(1)
                return llm
            except ImportError:
                print(f"{COLOR_RED}Error: langchain-community not installed. Please run 'pip install langchain-community'{COLOR_RESET}")
                sys.exit(1)
            except Exception as e:
                print(f"{COLOR_RED}Error initializing Ollama Chat: {e}{COLOR_RESET}")
                sys.exit(1)
        else:
            print(f"{COLOR_RED}Error: Invalid LLM_PROVIDER '{self.model_provider}' in .env. Use 'groq' or 'ollama'.{COLOR_RESET}")
            sys.exit(1)
