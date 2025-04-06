import os
import subprocess
import datetime
import re
import argparse
from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from langchain_core.output_parsers import StrOutputParser
from llm_agent import LLMAgent

# --- ANSI Color Codes ---
COLOR_GRAY = "\033[38;2;180;180;180m"
COLOR_RED = "\033[38;2;255;160;160m"
COLOR_YELLOW = "\033[38;2;255;255;180m"
COLOR_GREEN = "\033[38;2;160;255;160m"
COLOR_RESET = "\033[0m"

# --- Configuration ---
load_dotenv()
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq").lower()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL_NAME = os.getenv("GROQ_MODEL_NAME", "qwen-2.5-coder-32b")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")

# --- Constants ---
SAVE_DIR = os.path.expanduser("~/.llmterminal")
LOG_FILE = os.path.join(SAVE_DIR, "command_log.txt")
os.makedirs(SAVE_DIR, exist_ok=True)



class BashScriptAgent(LLMAgent):
    """Agent for generating and executing bash scripts."""

    def __init__(self, temperature=0.1, model_provider=LLM_PROVIDER, model=None, api_key=None, base_url=None):
        system_prompt = """You are an expert bash script generator.
Create a bash script based on the user's request or failed command.
The output MUST follow this exact format:
# title: [a_20_character_max_title_without_spaces]
# description: [A short description, maximum 50 words, explaining what the script does.]
bashscript:
[The bash script content starts here. Ensure it's runnable.]

Constraints:
- The title must be 20 characters max and contain no spaces (use underscores).
- The description must be 50 words max.
- The line "bashscript:" MUST be present exactly as shown, followed by a newline.
- The script content should directly follow the "bashscript:" line.
- If the user provided a failed command and error, try to fix it or achieve the user's likely intent.
- If the user started the command with '?', treat it as a request for a script.
- Only output the requested format, nothing else. No introductory text or closing remarks.
"""
        super().__init__(temperature, system_prompt, model_provider, model, api_key, base_url)

    def parse_output(self, output: str):
        """Parses LLM output to extract title, description, and script."""
        title_match = re.search(r"^# title:\s*(.*)", output, re.MULTILINE)
        desc_match = re.search(r"^# description:\s*(.*)", output, re.MULTILINE | re.DOTALL)
        script_match = re.search(r"^bashscript:\s*\n?(.*)", output, re.MULTILINE | re.DOTALL)

        title = title_match.group(1).strip().replace(" ", "_")[:20] if title_match else "untitled_script"
        description = desc_match.group(1).strip() if desc_match else "No description provided."
        script_lines = []

        if desc_match and "bashscript:" in description:
            description = description.split("bashscript:", 1)[0].strip()
        description = " ".join(description.split()[:50])

        if script_match:
            script_content = script_match.group(1).strip()
            script_content = re.sub(r"^```bash\n?", "", script_content, flags=re.MULTILINE)
            script_content = re.sub(r"\n?```$", "", script_content, flags=re.MULTILINE)
            script_lines = script_content.strip().splitlines()
        else:
            lines = output.splitlines()
            start_index = next((i + 1 for i, line in enumerate(lines) if line.strip().lower() == "bashscript:" or line.strip().startswith("#!")), -1)
            if start_index != -1:
                script_lines = [line for line in lines[start_index:] if line.strip()]

        full_script = "\n".join(script_lines) if script_lines else None
        if full_script and not full_script.strip().startswith("#!"):
            full_script = "#!/bin/bash\n" + full_script

        return title, description, full_script

    def generate_script(self, user_prompt: str, error_output: str | None = None):
        """Generates bash script using the LLM."""
        human_prompt_text = (
            f"The user ran a command that failed:\nCommand: {user_prompt}\nError Output:\n{error_output}\n\nGenerate a bash script that likely achieves the user's intended goal or fixes the command."
            if error_output
            else f"The user asked for help with the following request: '{user_prompt[1:].strip()}'\n\nGenerate a bash script to fulfill this request."
            if user_prompt.startswith("?")
            else f"Generate a bash script based on this user input: {user_prompt}"
        )

        prompt = ChatPromptTemplate.from_messages([
            SystemMessagePromptTemplate.from_template(self.system_prompt),
            HumanMessagePromptTemplate.from_template(human_prompt_text)
        ])
        parser = StrOutputParser()
        chain = prompt | self.llm | parser

        print(f"{COLOR_YELLOW}Generating script suggestion...{COLOR_RESET}")
        try:
            response = chain.invoke({})
            return self.parse_output(response)
        except Exception as e:
            print(f"{COLOR_RED}Error during LLM interaction: {e}{COLOR_RESET}")
            return None, None, None

    def get_confirmation(self):
        """Gets user confirmation."""
        print(f"{COLOR_RED}Confirm script execution? [y/N]: {COLOR_RESET}", end="")
        try:
            user_input = input().lower().strip()
            return user_input == 'y'
        except (EOFError, KeyboardInterrupt):
            return False

    def save_and_log(self, title: str, description: str, script_content: str, user_prompt: str):
        """Saves script and logs the command."""
        now = datetime.datetime.now()
        filename = f"{title}_{now.strftime('%Y%m%d_%H%M%S')}.sh"
        filepath = os.path.join(SAVE_DIR, filename)

        script_header = f"""#!/bin/bash
# title: {title}
# description: {description}
# generated_at: {now.isoformat()}
# user_prompt: {user_prompt}
# ---- Start of Generated Script ----
"""
        full_script_content = script_header + "\n" + script_content.replace('#!/bin/bash\n', '', 1)

        try:
            with open(filepath, "w") as f:
                f.write(full_script_content)
            os.chmod(filepath, 0o755)
            with open(LOG_FILE, "a") as log:
                log.write(f"--- {now.isoformat()} ---\nUser Prompt: {user_prompt}\nGenerated Script: {filename}\nDescription: {description}\n\n")
            return filepath
        except Exception as e:
            print(f"{COLOR_RED}Error saving or logging script: {e}{COLOR_RESET}")
            return None

    def execute_script(self, script_path: str):
        """Executes a script and displays its stdout in real-time."""
        try:
            process = subprocess.Popen(
                [script_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True,
            )

            while True:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                if output:
                    print(output.strip(), flush=True)

            stderr_output, _ = process.communicate()
            if stderr_output:
                print("Standard Error:")
                print(stderr_output, flush=True)

            return_code = process.poll()
            if return_code != 0:
                print(f"Script exited with return code: {return_code}")
                return return_code #Return the error code for the caller to handle.
            return 0 # return 0 for success.

        except FileNotFoundError:
            print("Script not found.")
            return 1 #Return 1 for file not found error.

        except Exception as generic_error:
            print(f"An unexpected error occurred: {generic_error}")
            return 2 #Return 2 for generic errors.


    def suggest_and_execute(self, query: str, error: str | None = None):
        """Generates, confirms, saves, and executes a script."""
        print(f"{query=}")
        print(f"{error=}")
        title, description, script_content = self.generate_script(query, error)

        if title and description and script_content:
            print(f"\n--- LLM Suggestion ---")
            print(f"{COLOR_YELLOW}# title: {title}{COLOR_RESET}")
            print(f"{COLOR_YELLOW}# description: {description}{COLOR_RESET}")
            print(f"{COLOR_YELLOW}# query: {query}{COLOR_RESET}")
            print(f"{COLOR_YELLOW}# error: {error}{COLOR_RESET}")
            print(f"{COLOR_YELLOW}--- Script Start ---{COLOR_RESET}")
            for line in script_content.splitlines():
                print(f"{COLOR_GRAY}{line}{COLOR_RESET}")
            print(f"{COLOR_GRAY}--- Script End ---{COLOR_RESET}\n")

            if self.get_confirmation():
                filepath = self.save_and_log(title, description, script_content, query)
                if filepath:
                    self.execute_script(filepath)
            else:
                print(f"{COLOR_YELLOW}Execution cancelled by user.{COLOR_RESET}")
        else:
            print(f"{COLOR_RED}Could not generate a valid script suggestion.{COLOR_RESET}")


def main():
    """Main function to parse command line arguments and execute the agent."""
    parser = argparse.ArgumentParser(description="Generate and execute bash scripts based on a query and error.")
    parser.add_argument("query", type=str, help="The query to generate the script from.")
    parser.add_argument("--error", type=str, default=None, help="The error message to include in the script generation.")
    args = parser.parse_args()

    agent = BashScriptAgent(model=GROQ_MODEL_NAME if LLM_PROVIDER == "groq" else OLLAMA_MODEL, api_key=GROQ_API_KEY, base_url=OLLAMA_BASE_URL)
    agent.suggest_and_execute(args.query, args.error)


if __name__ == "__main__":
    main()
