#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e
# Treat unset variables as an error when substituting.
set -u
# Exit status of the last command that threw a non-zero exit code is returned.
set -o pipefail

# --- Colors ---
# Usage: echo -e "${COLOR_GREEN}This is green.${COLOR_RESET}"
COLOR_RESET='\033[0m'
COLOR_RED='\033[0;31m'
COLOR_GREEN='\033[0;32m'
COLOR_YELLOW='\033[0;33m'
COLOR_BLUE='\033[0;34m'
COLOR_MAGENTA='\033[0;35m'
COLOR_CYAN='\033[0;36m'
COLOR_BOLD_RED='\033[1;31m'
COLOR_BOLD_GREEN='\033[1;32m'
COLOR_BOLD_YELLOW='\033[1;33m'
COLOR_BOLD_BLUE='\033[1;34m'
COLOR_BOLD_MAGENTA='\033[1;35m'
COLOR_BOLD_CYAN='\033[1;36m'

# --- Display Header ---
echo -e "${COLOR_BOLD_CYAN}"
echo "========================================"
echo "     BASH SCRIPT LLM AGENT INSTALLER    "
echo "========================================"
echo -e "${COLOR_RESET}"
echo "" # Add a newline for spacing

# --- Configuration ---
VENV_NAME="venv" # Name of the virtual environment directory
REQUIREMENTS_FILE="requirements.txt" # Path to requirements relative to project root
LLM_BS_TRIGGER="bashscript_llm_agent_trigger.sh"
ENV_TEMPLATE_FILE=".env_template" # Name of the template environment file
ENV_FILE=".env"                   # Name of the actual environment file


# --- Get Project Directory ---
# Assumes the install.sh script is in the project's root directory
PROJECT_ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo -e "\n${COLOR_BLUE}Project root directory detected as: ${PROJECT_ROOT_DIR}${COLOR_RESET}"

# --- Check for Python 3 ---
if ! command -v python3 &> /dev/null; then
    echo -e "${COLOR_BOLD_RED}Error: python3 command could not be found. Please install Python 3.${COLOR_RESET}"
    exit 1
fi
echo -e "${COLOR_GREEN}Python 3 found.${COLOR_RESET}"

# --- Create Virtual Environment ---
VENV_PATH="${PROJECT_ROOT_DIR}/${VENV_NAME}"
if [ ! -d "$VENV_PATH" ]; then
    echo -e "\n${COLOR_BLUE}Creating Python virtual environment in '${VENV_PATH}'...${COLOR_RESET}"
    python3 -m venv "$VENV_PATH"
    echo -e "${COLOR_GREEN}Virtual environment created.${COLOR_RESET}"
else
    echo -e "${COLOR_YELLOW}Virtual environment '${VENV_PATH}' already exists. Skipping creation.${COLOR_RESET}"
fi

# --- Activate Virtual Environment (for this script's context) ---
# Note: This activation is temporary for the script's execution
echo -e "\n${COLOR_BLUE}Activating virtual environment for dependency installation...${COLOR_RESET}"
source "${VENV_PATH}/bin/activate"
echo -e "${COLOR_GREEN}Virtual environment activated.${COLOR_RESET}"

# --- Install Requirements ---
REQUIREMENTS_PATH="${PROJECT_ROOT_DIR}/${REQUIREMENTS_FILE}"
if [ -f "$REQUIREMENTS_PATH" ]; then
    echo -e "\n${COLOR_BLUE}Installing requirements from '${REQUIREMENTS_PATH}'...${COLOR_RESET}"
    # Suppress verbose output from pip, show errors
    pip install -r "$REQUIREMENTS_PATH" || {
        echo -e "${COLOR_BOLD_RED}Error installing requirements.${COLOR_RESET}";
        deactivate; # Ensure deactivation on error
        exit 1;
    }
    echo -e "${COLOR_GREEN}Requirements installed successfully.${COLOR_RESET}"
else
    echo -e "${COLOR_YELLOW}Warning: Requirements file '${REQUIREMENTS_PATH}' not found. Skipping dependency installation.${COLOR_RESET}"
    # Optionally exit if requirements are mandatory:
    # echo -e "${COLOR_BOLD_RED}Error: Requirements file '${REQUIREMENTS_PATH}' not found.${COLOR_RESET}"
    # deactivate
    # exit 1
fi

# --- Deactivate Virtual Environment (for this script's context) ---
# Although the script exiting does this implicitly, it's good practice
# to deactivate explicitly if more script logic followed.
deactivate
# echo "Virtual environment deactivated for script context."


# --- Add source command to .bashrc ---
BASHRC_FILE="${HOME}/.bashrc"
HANDLEQ_SCRIPT_PATH="${PROJECT_ROOT_DIR}/${LLM_BS_TRIGGER}"
SOURCE_COMMAND="source \"${HANDLEQ_SCRIPT_PATH}\"" # Quote path for safety

echo -e "\n${COLOR_BLUE}Checking ${BASHRC_FILE} for existing source command...${COLOR_RESET}"

# Check if the exact line already exists to prevent duplicates
if grep -qFx "$SOURCE_COMMAND" "$BASHRC_FILE"; then
    echo -e "${COLOR_YELLOW}Source command already exists in ${BASHRC_FILE}. Skipping.${COLOR_RESET}"
else
    echo -e "\n${COLOR_BLUE}Adding source command to ${BASHRC_FILE}...${COLOR_RESET}"
    # Add a comment for clarity before the command
    echo "" >> "$BASHRC_FILE" # Add a newline for separation
    echo "# Added by BSagent install script - $(date)" >> "$BASHRC_FILE"
    echo "$SOURCE_COMMAND" >> "$BASHRC_FILE"
    echo -e "${COLOR_GREEN}Source command added.${COLOR_RESET}"
fi


# --- Handle .env file ---
ENV_TEMPLATE_PATH="${PROJECT_ROOT_DIR}/${ENV_TEMPLATE_FILE}"
ENV_FILE_PATH="${PROJECT_ROOT_DIR}/${ENV_FILE}"

echo "" # Newline for separation
echo -e "${COLOR_MAGENTA}--- Configuring Environment File ---${COLOR_RESET}"

if [ -f "$ENV_FILE_PATH" ]; then
    echo -e "${COLOR_YELLOW}Environment file '${ENV_FILE_PATH}' already exists.${COLOR_RESET}"
    echo -e "${COLOR_YELLOW}Please review it manually to ensure it has the necessary API keys and configurations.${COLOR_RESET}"
elif [ -f "$ENV_TEMPLATE_PATH" ]; then
    echo -e "\n${COLOR_BLUE}Copying '${ENV_TEMPLATE_PATH}' to '${ENV_FILE_PATH}'...${COLOR_RESET}"
    if [ ! -f "$ENV_FILE_PATH" ]; then
        cp "$ENV_TEMPLATE_PATH" "$ENV_FILE_PATH"
    fi
    echo -e "${COLOR_GREEN}Successfully created '${ENV_FILE_PATH}'.${COLOR_RESET}"
    echo ""
    echo -e "${COLOR_BOLD_YELLOW}###################### IMPORTANT ######################${COLOR_RESET}"
    echo -e "${COLOR_BOLD_YELLOW}#                                                     #${COLOR_RESET}"
    echo -e "${COLOR_BOLD_YELLOW}#   You MUST edit the '${ENV_FILE}' file              #${COLOR_RESET}"
    echo -e "${COLOR_BOLD_YELLOW}#   and add your specific configurations              #${COLOR_RESET}"
    echo -e "${COLOR_BOLD_YELLOW}#   (e.g., API keys, model names, etc.).            #${COLOR_RESET}"
    echo -e "${COLOR_BOLD_YELLOW}#                                                     #${COLOR_RESET}"
    echo -e "${COLOR_BOLD_YELLOW}#######################################################${COLOR_RESET}"
    echo ""
else
    echo -e "${COLOR_BOLD_RED}Warning: Template file '${ENV_TEMPLATE_PATH}' not found.${COLOR_RESET}"
    echo -e "${COLOR_RED}         Cannot create '${ENV_FILE_PATH}'. You will need to create and configure${COLOR_RESET}"
    echo -e "${COLOR_RED}         this file manually with the required environment variables.${COLOR_RESET}"
fi


# --- Final Instructions ---
# Refresh .bashrc Note
# Sourcing .bashrc within the script only affects the script's subshell.
# It DOES NOT affect the parent shell (the terminal you ran the script from).
# The user MUST manually source it or open a new terminal.
echo ""
echo -e "${COLOR_GREEN}------------------------------------------------------------------${COLOR_RESET}"
echo -e "${COLOR_BOLD_GREEN} Installation Complete! ${COLOR_RESET}"
echo -e "${COLOR_GREEN}------------------------------------------------------------------${COLOR_RESET}"
echo ""
echo -e "${COLOR_BOLD_YELLOW} FINAL STEP:${COLOR_RESET}"
echo " To apply the changes and enable the agent trigger in your"
echo " current terminal session, please run the following command:"
echo ""
# Make the command stand out
echo -e "  ${COLOR_CYAN}source ~/.bashrc${COLOR_RESET}"
echo ""
echo -e " Alternatively, you can simply ${COLOR_BOLD_YELLOW}open a new terminal window${COLOR_RESET},"
echo " where the changes will be automatically loaded."
echo -e "${COLOR_GREEN}------------------------------------------------------------------${COLOR_RESET}"

exit 0