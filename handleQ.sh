# command_not_found_handle() {
#   # Check if the command starts with a "?"
#   if [[ "$1" == \?* ]]; then
#     # Print everything after the "?" character
#     echo "> : ${1:1}"
#     echo "$1" | nc -U /tmp/error_socket
#     return 0
#   fi
#   # Otherwise, do the normal behavior (or suppress error)
#   return 127
# }


# command_not_found_handle() {
#   if [[ "$1" == \?* ]]; then
#     echo "$1"
#     echo "$1" | nc -U /tmp/error_socket
#     return 0
#   fi
#   command_not_found_handle;
#   #echo "Command not found: $1"
# #   return 127
# }


# command_not_found_handle() {
#   if [[ "$*" == \?* ]]; then
#     echo "$*" | sed 's/^.//' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//'
#     echo "$*" | sed 's/^.//' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//' | nc -U /tmp/error_socket
#     return 0
#   fi

#   # Fall back to default Bash behavior
#   unset -f command_not_found_handle
#   "$1" "${@:2}"
#   return $?
# }



# trap 'handle_error $BASH_COMMAND' ERR

# handle_error() {
#   last_command="$1"
#   if [[ "$last_command" == \?* ]]; then
#     echo "------: ${last_command:1}"
#     return 0
#   else
#     # Let Bash handle the error normally
#     echo "******: $last_command"
#   fi
# }




# trap 'error_handler $LINENO' ERR

# error_handler() {
#     echo "n $*"
#     echo "e $?"
#     /home/ovi/env0/bin/python /home/ovi/software/BSagent/llmTerminal_3_h.py --error "$?" "$*"
# }

# error_handler() {
#     local exit_code=$?
#     echo "Error in command: \"$BASH_COMMAND\""
#     echo "Exit code: $exit_code"
#     echo "At line: $LINENO"
#     /home/ovi/env0/bin/python /home/ovi/software/BSagent/llmTerminal_3_h.py --error "$?" "$*"
# }







# Create temp file for error messages
ERROR_LOG=$(mktemp)
exec 3>&2  # Save original stderr
exec 2> >(tee "$ERROR_LOG" >&3)
trap 'error_handler $LINENO' ERR
# set -e

# Error handler function
error_handler() {
    /home/ovi/env0/bin/python /home/ovi/software/BSagent/llmTerminal_3_h.py --error "$err_msg" "$BASH_COMMAND" 
}

# Custom command-not-found handler
command_not_found_handle() {
    # Check if the command starts with a '?'
    if [[ "$1" == \?* ]]; then
        query=$(echo "$*" | sed 's/^.//' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
        /home/ovi/env0/bin/python /home/ovi/software/BSagent/llmTerminal_3_h.py "$query" 
        return 0
    fi

    # Fall back to default Bash behavior
    unset -f command_not_found_handle
    "$1" "${@:2}"
    return $?
}



# trap 'echo "$BASH_COMMAND" | nc -U /tmp/error_socket' ERR
