import os
import subprocess
import sys
import datetime
import re
from dotenv import load_dotenv
import termios
import tty
import argparse

# --- Langchain Imports ---
from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from langchain_core.output_parsers import StrOutputParser

# --- ANSI Color Codes ---
COLOR_GRAY   = "\033[38;2;180;180;180m"  # Light gray
COLOR_RED    = "\033[38;2;255;160;160m"  # Light red
COLOR_YELLOW = "\033[38;2;255;255;180m"  # Light yellow
COLOR_GREEN  = "\033[38;2;160;255;160m"  # Light green (for success)
COLOR_RESET  = "\033[0m"

# --- Configuration ---
load_dotenv()
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq").lower()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL_NAME = os.getenv("GROQ_MODEL_NAME", "qwen-2.5-coder-32b")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL") # Optional for Ollama
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")

# --- Constants ---
SAVE_DIR = os.path.expanduser("~/.llmterminal")
LOG_FILE = os.path.join(SAVE_DIR, "command_log.txt")
os.makedirs(SAVE_DIR, exist_ok=True)

# --- LLM Setup ---
def get_llm():
    """Initializes and returns the LangChain LLM object based on .env config."""
    if LLM_PROVIDER == "groq":
        if not GROQ_API_KEY:
            print(f"{COLOR_RED}Error: GROQ_API_KEY not found in .env file.{COLOR_RESET}")
            sys.exit(1)
        try:
            from langchain_groq import ChatGroq
            llm = ChatGroq(
                temperature=0.1, # Lower temperature for more deterministic script generation
                groq_api_key=GROQ_API_KEY,
                model_name=GROQ_MODEL_NAME
            )
            print(f"{COLOR_YELLOW}Using Groq model: {GROQ_MODEL_NAME}{COLOR_RESET}")
            return llm
        except ImportError:
            print(f"{COLOR_RED}Error: langchain-groq not installed. Please run 'pip install langchain-groq'{COLOR_RESET}")
            sys.exit(1)
        except Exception as e:
            print(f"{COLOR_RED}Error initializing Groq Chat: {e}{COLOR_RESET}")
            sys.exit(1)

    elif LLM_PROVIDER == "ollama":
        try:
            from langchain_community.chat_models import ChatOllama
            ollama_kwargs = {"model": OLLAMA_MODEL, "temperature": 0.1}
            if OLLAMA_BASE_URL:
                ollama_kwargs["base_url"] = OLLAMA_BASE_URL
            llm = ChatOllama(**ollama_kwargs)
            print(f"{COLOR_YELLOW}Using Ollama model: {OLLAMA_MODEL}" +
                  (f" at {OLLAMA_BASE_URL}" if OLLAMA_BASE_URL else "") +
                  f"{COLOR_RESET}")
            # Perform a quick test call
            try:
                 llm.invoke("Respond with only 'OK'")
            except Exception as e:
                 print(f"{COLOR_RED}Error: Could not connect to Ollama or model '{OLLAMA_MODEL}' not available.")
                 print(f"Details: {e}{COLOR_RESET}")
                 print(f"{COLOR_YELLOW}Make sure Ollama is running and the model '{OLLAMA_MODEL}' is pulled (`ollama pull {OLLAMA_MODEL}`){COLOR_RESET}")
                 sys.exit(1)
            return llm
        except ImportError:
            print(f"{COLOR_RED}Error: langchain-community not installed. Please run 'pip install langchain-community'{COLOR_RESET}")
            sys.exit(1)
        except Exception as e:
            print(f"{COLOR_RED}Error initializing Ollama Chat: {e}{COLOR_RESET}")
            sys.exit(1)

    else:
        print(f"{COLOR_RED}Error: Invalid LLM_PROVIDER '{LLM_PROVIDER}' in .env. Use 'groq' or 'ollama'.{COLOR_RESET}")
        sys.exit(1)

def parse_llm_output(output: str) -> tuple[str | None, str | None, str | None]:
    """Parses the LLM output to extract title, description, and script."""
    title = None
    description = None
    script_lines = []
    in_script_block = False

    # Try regex first for cleaner extraction
    title_match = re.search(r"^# title:\s*(.*)", output, re.MULTILINE)
    desc_match = re.search(r"^# description:\s*(.*)", output, re.MULTILINE | re.DOTALL) # DOTALL for multiline desc
    script_match = re.search(r"^bashscript:\s*\n?(.*)", output, re.MULTILINE | re.DOTALL)

    if title_match:
        title = title_match.group(1).strip().replace(" ", "_")[:20] # Max 20 chars, no spaces

    # Be more flexible with description extraction if regex fails
    if desc_match:
         # Limit description parsing if it captured too much (e.g., the script itself)
        potential_desc = desc_match.group(1).strip()
        if "bashscript:" in potential_desc:
             description = potential_desc.split("bashscript:", 1)[0].strip()
        else:
             description = potential_desc
        # Limit description length
        description = " ".join(description.split()[:50]) # Max 50 words
    else:
         # Fallback: try to grab lines between title and script if they exist
         lines = output.splitlines()
         desc_lines = []
         in_desc_section = False
         for line in lines:
            if line.startswith("# title:"):
                in_desc_section = True
                continue
            if line.startswith("bashscript:") or line.startswith("#!"):
                in_desc_section = False
                break
            if in_desc_section and line.startswith("# description:"):
                 desc_lines.append(line.split(":",1)[1].strip())
            elif in_desc_section and line.startswith("#"): # Allow multi-line description comments
                 desc_lines.append(line[1:].strip()) # remove leading #
         if desc_lines:
             description = " ".join(" ".join(desc_lines).split()[:50])


    # Be more flexible with script extraction
    if script_match:
        script_content = script_match.group(1).strip()
        # Remove potential backticks ```bash ... ```
        script_content = re.sub(r"^```bash\n?", "", script_content, flags=re.MULTILINE)
        script_content = re.sub(r"\n?```$", "", script_content, flags=re.MULTILINE)
        script_lines = script_content.strip().splitlines()
    else:
        # Fallback: Find lines after "bashscript:" or starting with #!/bin/bash
        lines = output.splitlines()
        start_index = -1
        for i, line in enumerate(lines):
             if line.strip().lower() == "bashscript:":
                 start_index = i + 1
                 break
             if line.strip().startswith("#!/"): # Common script start
                 # Check if previous lines were metadata
                 if i > 0 and (lines[i-1].startswith("# title:") or lines[i-1].startswith("# description:")):
                     start_index = i
                     break
                 elif i == 0 : # Script starts directly with shebang
                      start_index = i
                      break

        if start_index != -1:
            script_lines = [line for line in lines[start_index:] if line.strip()] # Get non-empty lines

    # Basic validation
    if not title: title = "untitled_script"
    if not description: description = "No description provided."
    if not script_lines: return title, description, None # Return None if no script found

    # Ensure script starts with shebang if not present
    full_script = "\n".join(script_lines)
    if not full_script.strip().startswith("#!"):
        full_script = "#!/bin/bash\n" + full_script

    return title, description, full_script


def generate_bash_script(llm, user_prompt: str, error_output: str | None = None):
    """Generates the bash script using the LLM."""
    system_prompt_text = """You are an expert bash script generator.
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
    if error_output:
        human_prompt_text = f"The user ran a command that failed:\nCommand: {user_prompt}\nError Output:\n{error_output}\n\nGenerate a bash script that likely achieves the user's intended goal or fixes the command."
    elif user_prompt.startswith("?"):
         human_prompt_text = f"The user asked for help with the following request: '{user_prompt[1:].strip()}'\n\nGenerate a bash script to fulfill this request."
    else:
         # Should not happen based on trigger logic, but handle defensively
         human_prompt_text = f"Generate a bash script based on this user input: {user_prompt}"

    prompt = ChatPromptTemplate.from_messages([
        SystemMessagePromptTemplate.from_template(system_prompt_text),
        HumanMessagePromptTemplate.from_template(human_prompt_text)
    ])
    parser = StrOutputParser()
    chain = prompt | llm | parser

    print(f"{COLOR_YELLOW}Generating script suggestion...{COLOR_RESET}")
    try:
        response = chain.invoke({})
        # print(f"\nDEBUG LLM Raw Output:\n---\n{response}\n---\n") # Uncomment for debugging
        title, description, script_content = parse_llm_output(response)

        if script_content:
             return title, description, script_content
        else:
             print(f"{COLOR_RED}Error: Failed to parse LLM output or script content missing.{COLOR_RESET}")
             print(f"{COLOR_GRAY}LLM Response:\n{response}{COLOR_RESET}") # Show raw response on failure
             return None, None, None

    except Exception as e:
        print(f"{COLOR_RED}Error during LLM interaction: {e}{COLOR_RESET}")
        return None, None, None


def get_confirmation():
    """Gets user confirmation, looking for Shift+Enter (simulated)."""
    print(f"{COLOR_RED}Should I execute? [Enter or y/yes + Enter to confirm, anything else to cancel]{COLOR_RESET}")
    # Simple input handling - requires Enter. Robust Shift+Enter requires more complex tty handling.
    # This part is tricky cross-platform without libraries like prompt_toolkit or curses.
    # We simulate by just checking for 'y' or empty input after Enter.
    try:
        user_input = input().lower().strip()
        if user_input == '' or user_input == 'y' or user_input == 'yes':
            return True
        return False
    except EOFError: # Handle Ctrl+D
        return False
    except KeyboardInterrupt: # Handle Ctrl+C
        print("\nCancelled.")
        return False


def save_and_log_script(title: str, description: str, script_content: str, user_prompt: str):
    """Saves the script and logs the command."""
    now = datetime.datetime.now()
    timestamp = now.strftime("%Y%m%d_%H%M%S")
    filename = f"{title}_{timestamp}.sh"
    filepath = os.path.join(SAVE_DIR, filename)

    # Prepare script content with metadata comments
    script_header = f"""#!/bin/bash
# title: {title}
# description: {description}
# generated_at: {now.isoformat()}
# user_prompt: {user_prompt}
# ---- Start of Generated Script ----
"""
    full_script_content = script_header + "\n" + script_content.replace('#!/bin/bash\n', '', 1) # Avoid duplicate shebang

    try:
        with open(filepath, "w") as f:
            f.write(full_script_content)
        # print(f"{COLOR_YELLOW}Script saved to: {filepath}{COLOR_RESET}")

        # Make executable
        os.chmod(filepath, 0o755) # rwxr-xr-x

        # Log the command
        with open(LOG_FILE, "a") as log:
            log.write(f"--- {now.isoformat()} ---\n")
            log.write(f"User Prompt: {user_prompt}\n")
            log.write(f"Generated Script: {filename}\n")
            log.write(f"Description: {description}\n\n")

        return filepath
    except Exception as e:
        print(f"{COLOR_RED}Error saving or logging script: {e}{COLOR_RESET}")
        return None

def execute_script(script_path: str):
    """Executes the generated script."""
    # print(f"{COLOR_YELLOW}Executing script: {script_path}{COLOR_RESET}")
    try:
        # Use subprocess.run to execute, capturing output
        # result = subprocess.run([script_path], capture_output=True, text=True, check=False) # Don't check=True here, let user see errors
        exit_code = os.system(script_path)
        # if result.stdout:
        #     print(f"{COLOR_GREEN}--- Script Output ---{COLOR_RESET}\n{result.stdout.strip()}")
        # if result.stderr:
        #      print(f"{COLOR_RED}--- Script Error Output ---{COLOR_RESET}\n{result.stderr.strip()}")

        # if result.returncode == 0:
        #     print(f"{COLOR_GREEN}Script executed successfully.{COLOR_RESET}")
        # else:
        #     print(f"{COLOR_RED}Script finished with exit code: {result.returncode}{COLOR_RESET}")


        if exit_code == 0:
            print(f"{COLOR_GREEN}Script executed successfully.{COLOR_RESET}")
        else:
            print(f"{COLOR_RED}Script finished with exit code: {exit_code}{COLOR_RESET}")

    except Exception as e:
        print(f"{COLOR_RED}Error executing script: {e}{COLOR_RESET}")


# --- Main Loop ---
def main():
    llm = get_llm()
    if not llm:
        sys.exit(1)

    print(f"\n{COLOR_GREEN}LLM Terminal Assistant Initialized.{COLOR_RESET}")
    print(f"Provider: {LLM_PROVIDER.upper()}")
    print(f"Enter bash commands, prefix with '?' to ask for a script, or type 'exit'/'quit'.")

    while True:
        try:
            # Basic prompt, you might want something more sophisticated
            command = input(f"{COLOR_GREEN}>>> {COLOR_RESET}")
        except EOFError:
            print("\nExiting.")
            break
        except KeyboardInterrupt:
            print("\nType 'exit' or 'quit' to exit.")
            continue

        command_strip = command.strip()
        if not command_strip:
            continue
        if command_strip.lower() in ["exit", "quit"]:
            print("Exiting.")
            break

        trigger_llm = False
        error_output = None
        return_code = 0

        if command_strip.startswith("?"):
            trigger_llm = True
            print(f"{COLOR_YELLOW}Request received: '{command_strip[1:].strip()}'{COLOR_RESET}")
        else:
            # Execute the command directly
            try:
                print(f"{COLOR_GRAY}Running: {command_strip}{COLOR_RESET}")
                result = subprocess.run(
                    command_strip,
                    shell=True,         # Be cautious with shell=True
                    capture_output=True,
                    text=True,
                    check=False         # Don't raise exception on non-zero exit
                )
                return_code = result.returncode
                error_output = result.stderr.strip()

                # Print output/error from direct execution
                if result.stdout.strip():
                    print(f"{COLOR_GRAY}Output:{COLOR_RESET}\n{result.stdout.strip()}")
                if error_output:
                     print(f"{COLOR_RED}Error Output:{COLOR_RESET}\n{error_output}")


                if return_code != 0:
                    trigger_llm = True
                    print(f"{COLOR_RED}Command failed with exit code {return_code}. Attempting to generate suggestion...{COLOR_RESET}")
                else:
                    print(f"{COLOR_GREEN}Command executed successfully.{COLOR_RESET}") # State 1

            except Exception as e:
                print(f"{COLOR_RED}Failed to execute command locally: {e}{COLOR_RESET}")
                trigger_llm = True # Trigger LLM if execution itself fails
                error_output = str(e)


        # State 2: Trigger LLM
        if trigger_llm:
            title, description, script_content = generate_bash_script(llm, command_strip, error_output)

            if title and description and script_content:
                print(f"\n--- LLM Suggestion ---")
                print(f"{COLOR_GRAY}# title: {title}{COLOR_RESET}")
                print(f"{COLOR_GRAY}# description: {description}{COLOR_RESET}")
                print(f"{COLOR_GRAY}--- Script Start ---{COLOR_RESET}")
                # Print script line by line in gray
                for line in script_content.splitlines():
                    print(f"{COLOR_GRAY}{line}{COLOR_RESET}")
                print(f"{COLOR_GRAY}--- Script End ---{COLOR_RESET}\n")


                if get_confirmation():
                    filepath = save_and_log_script(title, description, script_content, command_strip)
                    if filepath:
                        execute_script(filepath)
                else:
                    print(f"{COLOR_YELLOW}Execution cancelled by user.{COLOR_RESET}")
            else:
                print(f"{COLOR_RED}Could not generate a valid script suggestion.{COLOR_RESET}")


def tryToSuggestAndExec(query, error):
    llm = get_llm()
    if not llm:
        sys.exit(1)

    title, description, script_content = generate_bash_script(llm, query, error)

    if title and description and script_content:
        print(f"\n--- LLM Suggestion ---")
        print(f"{COLOR_YELLOW}# title: {title}{COLOR_RESET}")
        print(f"{COLOR_YELLOW}# description: {description}{COLOR_RESET}")
        print(f"{COLOR_YELLOW}# query: {query}{COLOR_RESET}")
        print(f"{COLOR_YELLOW}# error: {error}{COLOR_RESET}")
        print(f"{COLOR_YELLOW}--- Script Start ---{COLOR_RESET}")
        # Print script line by line in gray
        for line in script_content.splitlines():
            print(f"{COLOR_GRAY}{line}{COLOR_RESET}")
        print(f"{COLOR_GRAY}--- Script End ---{COLOR_RESET}\n")


        if get_confirmation():
            filepath = save_and_log_script(title, description, script_content, query)
            if filepath:
                execute_script(filepath)
        else:
            print(f"{COLOR_YELLOW}Execution cancelled by user.{COLOR_RESET}")
    else:
        print(f"{COLOR_RED}Could not generate a valid script suggestion.{COLOR_RESET}")

# if __name__ == "__main__":
    # main()
    
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate and execute bash scripts based on a query and error.")
    parser.add_argument("query", type=str, help="The query to generate the script from.")
    parser.add_argument("--error", type=str, default=None, help="The error message to include in the script generation.")

    args = parser.parse_args()

    tryToSuggestAndExec(args.query, args.error)