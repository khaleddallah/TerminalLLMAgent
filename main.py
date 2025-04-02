import os
import sys
import subprocess
import tempfile
import time
import threading
import platform
import os
from dotenv import load_dotenv

load_dotenv()

# --- LLM Configuration ---
# Choose your LLM provider: 'ollama' or 'groq'
LLM_PROVIDER = "groq"  # or 'groq'

# Ollama settings
OLLAMA_MODEL = "codellama:7b"  # Or another model capable of code generation
OLLAMA_HOST = "http://localhost:11434" # Default Ollama host

# Groq settings (Requires GROQ_API_KEY environment variable)
GROQ_MODEL = "llama3-8b-8192" # Or other suitable model on Groq

# --- ANSI Color Codes ---
class Colors:
    RESET = "\033[0m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"

# --- Global variable for spinner ---
spinner_stop = False

def simple_spinner():
    """Displays a simple spinner animation in the console."""
    spinner_chars = "|/-\\"
    while not spinner_stop:
        for char in spinner_chars:
            if spinner_stop:
                break
            sys.stdout.write(f"\r{Colors.CYAN}Generating script... {char}{Colors.RESET}")
            sys.stdout.flush()
            time.sleep(0.1)
    # Clear the spinner line
    sys.stdout.write("\r" + " " * 30 + "\r")
    sys.stdout.flush()

def generate_script_with_ollama(prompt: str) -> str | None:
    """Generates a bash script using a local Ollama instance."""
    global spinner_stop
    try:
        import ollama
        print(f"{Colors.BLUE}Contacting Ollama (Model: {OLLAMA_MODEL})...{Colors.RESET}")

        spinner_thread = threading.Thread(target=simple_spinner)
        spinner_stop = False
        spinner_thread.start()

        try:
            # Construct a more specific prompt for the LLM
            full_prompt = f"""You are an AI assistant that translates user requests into executable bash scripts for a {platform.system()} system.
The user wants to achieve the following task: '{prompt}'

Generate *only* the bash script required to perform this task.
The script should start with `#!/bin/bash` (or equivalent like `#!/bin/sh` if more appropriate).
Do not include any explanations, comments outside the script, introductory text, or markdown formatting like ```bash ... ```.
The output should be *only* the raw script content, ready to be saved directly to a .sh file and executed.

Bash script:
"""
            response = ollama.generate(
                model=OLLAMA_MODEL,
                prompt=full_prompt,
                options={"temperature": 0.2} # Adjust temperature for more deterministic output
                # Consider adding stop sequences if the model adds extra text
                # options={"stop": ["```", "\n\nExplanation:", "User:"]}
            )
            script = response.get('response', '').strip()

            # Basic cleanup: remove potential markdown fences
            if script.startswith("```bash"):
                script = script[len("```bash"):].strip()
            if script.startswith("```sh"):
                script = script[len("```sh"):].strip()
            if script.endswith("```"):
                script = script[:-len("```")].strip()

            # Ensure it starts with a shebang
            if not script.startswith("#!"):
                 # Add a default shebang if missing - adjust if needed
                 script = "#!/bin/bash\n" + script

            return script if script else None

        finally:
            spinner_stop = True
            spinner_thread.join() # Wait for spinner thread to finish

    except ImportError:
        print(f"{Colors.RED}Error: 'ollama' library not found. Install it using: pip install ollama{Colors.RESET}")
        return None
    except Exception as e:
        spinner_stop = True # Ensure spinner stops on error
        if 'spinner_thread' in locals() and spinner_thread.is_alive():
              spinner_thread.join()
        print(f"{Colors.RED}\nError communicating with Ollama: {e}{Colors.RESET}")
        return None

def generate_script_with_groq(prompt: str) -> str | None:
    """Generates a bash script using the Groq API."""
    global spinner_stop
    try:
        from groq import Groq

        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            print(f"{Colors.RED}Error: GROQ_API_KEY environment variable not set.{Colors.RESET}")
            return None

        client = Groq(api_key=api_key)
        print(f"{Colors.BLUE}Contacting Groq (Model: {GROQ_MODEL})...{Colors.RESET}")

        spinner_thread = threading.Thread(target=simple_spinner)
        spinner_stop = False
        spinner_thread.start()

        try:
            # Construct a more specific prompt for the LLM
            full_prompt = f"""You are an AI assistant that translates user requests into executable bash scripts for a {platform.system()} system.
The user wants to achieve the following task: '{prompt}'

Generate *only* the bash script required to perform this task.
The script should start with `#!/bin/bash` (or equivalent like `#!/bin/sh` if more appropriate).
Do not include any explanations, comments outside the script, introductory text, or markdown formatting like ```bash ... ```.
The output should be *only* the raw script content, ready to be saved directly to a .sh file and executed.

Bash script:
"""
            chat_completion = client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": full_prompt.split("Bash script:")[0].strip() # System prompt part
                    },
                    {
                        "role": "user",
                        "content": prompt # User's core request
                    }
                ],
                model=GROQ_MODEL,
                temperature=0.2, # Lower temperature for more predictable script output
                # Consider adding stop sequences if needed
                # stop=["```", "\n\nExplanation:", "User:"]
            )
            script = chat_completion.choices[0].message.content.strip()

            # Basic cleanup: remove potential markdown fences
            if script.startswith("```bash"):
                script = script[len("```bash"):].strip()
            if script.startswith("```sh"):
                script = script[len("```sh"):].strip()
            if script.endswith("```"):
                script = script[:-len("```")].strip()

            # Ensure it starts with a shebang
            if not script.startswith("#!"):
                 script = "#!/bin/bash\n" + script # Add a default shebang if missing

            return script if script else None

        finally:
            spinner_stop = True
            spinner_thread.join()

    except ImportError:
        print(f"{Colors.RED}Error: 'groq' library not found. Install it using: pip install groq{Colors.RESET}")
        return None
    except Exception as e:
        spinner_stop = True # Ensure spinner stops on error
        if 'spinner_thread' in locals() and spinner_thread.is_alive():
              spinner_thread.join()
        print(f"{Colors.RED}\nError communicating with Groq: {e}{Colors.RESET}")
        return None


def execute_script(script_content: str):
    """Creates a temporary script file, sets permissions, executes it, and cleans up."""
    try:
        # Create a temporary file with .sh extension
        # 'delete=False' is important on Windows, less so on Linux/macOS
        # but safer to manage deletion manually after subprocess call
        # 'suffix' helps identify the file type
        # 'mode'='w+' allows writing and reading, 'encoding' avoids issues
        with tempfile.NamedTemporaryFile(mode='w+', suffix=".sh", delete=False, encoding='utf-8') as temp_script:
            script_path = temp_script.name
            temp_script.write(script_content)
            temp_script.flush() # Ensure content is written to disk
            # Close the file handle before changing permissions or executing
            # temp_script.close() # Not needed within 'with' block if flush is used? Test this.
                                # Closing inside 'with' might cause issues. Let's rely on flush.

        print(f"{Colors.MAGENTA}--- Temporary script saved to: {script_path} ---{Colors.RESET}")

        # --- Make the script executable ---
        try:
            # os.chmod is platform-dependent for exact modes, +x is common
            # Use standard library functions for cross-platform compatibility
            current_permissions = os.stat(script_path).st_mode
            os.chmod(script_path, current_permissions | 0o111) # Add execute permission for user, group, others
            print(f"{Colors.GREEN}--- Script permissions set to executable (chmod +x) ---{Colors.RESET}")
        except Exception as e:
            print(f"{Colors.RED}\nError setting script permissions: {e}{Colors.RESET}")
            os.unlink(script_path) # Clean up the temp file
            return

        # --- Execute the script ---
        print(f"{Colors.GREEN}--- Executing Script ---{Colors.RESET}")
        try:
            # Execute using subprocess.run for better control
            # 'capture_output=True' captures stdout and stderr
            # 'text=True' decodes output as text (UTF-8 by default)
            # 'shell=False' is generally safer, executing the script directly
            result = subprocess.run([script_path], capture_output=True, text=True, check=False) # check=False to handle non-zero exits manually

            print(f"\n{Colors.GREEN}--- Script Output (stdout) ---{Colors.RESET}")
            print(result.stdout if result.stdout else f"{Colors.YELLOW}<No standard output>{Colors.RESET}")
            print("------------------------------")

            if result.stderr:
                print(f"\n{Colors.RED}--- Script Error Output (stderr) ---{Colors.RESET}")
                print(result.stderr)
                print("---------------------------------")

            if result.returncode != 0:
                print(f"\n{Colors.RED}--- Script exited with non-zero status code: {result.returncode} ---{Colors.RESET}")
            else:
                print(f"\n{Colors.GREEN}--- Script execution finished successfully (exit code 0) ---{Colors.RESET}")

        except FileNotFoundError:
             print(f"{Colors.RED}\nError: Script file not found at {script_path}. This shouldn't happen.{Colors.RESET}")
        except Exception as e:
            print(f"{Colors.RED}\nError during script execution: {e}{Colors.RESET}")

    finally:
        # --- Clean up the temporary file ---
        if 'script_path' in locals() and os.path.exists(script_path):
            try:
                os.unlink(script_path)
                # print(f"--- Temporary script {script_path} deleted ---")
            except Exception as e:
                print(f"{Colors.YELLOW}\nWarning: Could not delete temporary script {script_path}: {e}{Colors.RESET}")


# --- Main Agent Logic ---
if __name__ == "__main__":
    print(f"{Colors.BOLD}{Colors.BLUE}Bash Script Executer Agent{Colors.RESET}")
    print("=" * 30)
    print(f"{Colors.GREEN}Using LLM Provider: {LLM_PROVIDER.upper()}{Colors.RESET}")
    if LLM_PROVIDER == "groq" and not os.environ.get("GROQ_API_KEY"):
        print(f"{Colors.YELLOW}Warning: GROQ_API_KEY environment variable not set. Groq will fail.{Colors.RESET}")
    elif LLM_PROVIDER == "ollama":
        print(f"{Colors.GREEN}(Ensure Ollama is running and model '{OLLAMA_MODEL}' is available){Colors.RESET}")


    while True:
        try:
            user_request = input(f"{Colors.CYAN}\nEnter your task (or 'quit' to exit): {Colors.RESET}")
            if user_request.lower() == 'quit':
                break
            if not user_request:
                continue

            # --- Generate Script ---
            generated_script = None
            if LLM_PROVIDER == "ollama":
                generated_script = generate_script_with_ollama(user_request)
            elif LLM_PROVIDER == "groq":
                generated_script = generate_script_with_groq(user_request)
            else:
                print(f"{Colors.RED}Error: Unknown LLM_PROVIDER '{LLM_PROVIDER}'. Choose 'ollama' or 'groq'.{Colors.RESET}")
                continue # Go to next loop iteration

            if not generated_script:
                print(f"{Colors.RED}Failed to generate script.{Colors.RESET}")
                continue

            # --- Display Script and Ask for Permission ---
            print(f"\n{Colors.BLUE}--- Generated Bash Script ---{Colors.RESET}")
            print("-" * 30)
            print(generated_script)
            print("-" * 30)

            print(f"\n{Colors.YELLOW}*** WARNING: Review the script carefully before execution! ***{Colors.RESET}")
            print(f"{Colors.YELLOW}*** Running unknown scripts can be dangerous.           ***{Colors.RESET}")

            while True:
                permission = input(f"{Colors.CYAN}Do you want to execute this script? (y/n): {Colors.RESET}").lower().strip()
                if permission in ['y', 'yes']:
                    execute_script(generated_script)
                    break
                elif permission in ['n', 'no']:
                    print(f"{Colors.GREEN}Execution cancelled by user.{Colors.RESET}")
                    break
                else:
                    print(f"{Colors.RED}Invalid input. Please enter 'y' or 'n'.{Colors.RESET}")

        except KeyboardInterrupt:
            print(f"\n{Colors.YELLOW}Exiting agent.{Colors.RESET}")
            break
        except Exception as e:
            print(f"{Colors.RED}\nAn unexpected error occurred: {e}{Colors.RESET}")
            # Optionally add more detailed error logging here

    print(f"{Colors.BLUE}Agent finished.{Colors.RESET}")
