#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e
# Treat unset variables as an error when substituting.
set -u
# Exit status of the last command that threw a non-zero exit code is returned.
set -o pipefail

# --- Configuration ---
VENV_NAME="venv" # Name of the virtual environment directory
REQUIREMENTS_FILE="requirements.txt" # Path to requirements relative to project root
LLM_BS_TRIGGER="bashscript_llm_agent_trigger.sh"


# --- Get Project Directory ---
# Assumes the install.sh script is in the project's root directory
PROJECT_ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "Project root directory detected as: ${PROJECT_ROOT_DIR}"

# --- Check for Python 3 ---
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 command could not be found. Please install Python 3."
    exit 1
fi
echo "Python 3 found."

# --- Create Virtual Environment ---
VENV_PATH="${PROJECT_ROOT_DIR}/${VENV_NAME}"
if [ ! -d "$VENV_PATH" ]; then
    echo "Creating Python virtual environment in '${VENV_PATH}'..."
    python3 -m venv "$VENV_PATH"
    echo "Virtual environment created."
else
    echo "Virtual environment '${VENV_PATH}' already exists. Skipping creation."
fi

# --- Activate Virtual Environment (for this script's context) ---
# Note: This activation is temporary for the script's execution
echo "Activating virtual environment for dependency installation..."
source "${VENV_PATH}/bin/activate"
echo "Virtual environment activated."

# --- Install Requirements ---
REQUIREMENTS_PATH="${PROJECT_ROOT_DIR}/${REQUIREMENTS_FILE}"
if [ -f "$REQUIREMENTS_PATH" ]; then
    echo "Installing requirements from '${REQUIREMENTS_PATH}'..."
    pip install -r "$REQUIREMENTS_PATH"
    echo "Requirements installed successfully."
else
    echo "Warning: Requirements file '${REQUIREMENTS_PATH}' not found. Skipping dependency installation."
    # Optionally exit if requirements are mandatory:
    # echo "Error: Requirements file '${REQUIREMENTS_PATH}' not found."
    # exit 1
fi

# --- Deactivate Virtual Environment (for this script's context) ---
# Although the script exiting does this implicitly, it's good practice
# to deactivate explicitly if more script logic followed.
# deactivate
# echo "Virtual environment deactivated for script context."


# --- Add source command to .bashrc ---
BASHRC_FILE="${HOME}/.bashrc"
HANDLEQ_SCRIPT_PATH="${PROJECT_ROOT_DIR}/${LLM_BS_TRIGGER}"
SOURCE_COMMAND="source \"${HANDLEQ_SCRIPT_PATH}\"" # Quote path for safety

echo "Checking ${BASHRC_FILE} for existing source command..."

# Check if the exact line already exists to prevent duplicates
if grep -qF "$SOURCE_COMMAND" "$BASHRC_FILE"; then
    echo "Source command already exists in ${BASHRC_FILE}. Skipping."
else
    echo "Adding source command to ${BASHRC_FILE}..."
    # Add a comment for clarity before the command
    echo "" >> "$BASHRC_FILE" # Add a newline for separation
    echo "# Added by BSagent install script - $(date)" >> "$BASHRC_FILE"
    echo "$SOURCE_COMMAND" >> "$BASHRC_FILE"
    echo "Source command added."
fi

# --- Refresh .bashrc ---
# Note: Sourcing .bashrc within the script only affects the script's subshell.
# It DOES NOT affect the parent shell (the terminal you ran the script from).
# The user MUST manually source it or open a new terminal.
echo ""
echo "------------------------------------------------------------------"
echo "Installation Complete!"
echo ""
echo "IMPORTANT:"
echo "To make the changes effective in your current terminal session,"
echo "please run the following command:"
echo ""
echo "  source ~/.bashrc"
echo ""
echo "Alternatively, you can simply open a new terminal window."
echo "------------------------------------------------------------------"

exit 0
