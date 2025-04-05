_GLOBAL_STDERR_LOG=$(mktemp)
_SEARCH_WORD="?-"
lock=false

_bash_error_handler_detailed() {
  /home/ovi/env0/bin/python /home/ovi/software/BSagent/llm_bash_script_generator.py --error "$(cat $_GLOBAL_STDERR_LOG)" "$BASH_COMMAND"
  > "$_GLOBAL_STDERR_LOG"
  exec 2>&1           
  lock=false
}
trap '_bash_error_handler_detailed' ERR

function pre_command() {
  if [ "$lock" = false ]; then
    exec 2> >(tee "$_GLOBAL_STDERR_LOG" >&2)
    lock=true
  fi
}
trap 'pre_command' DEBUG

# Custom command-not-found handler
command_not_found_handle() {
    # Check if the command starts with _SEARCH_WORD
    cmd0=$*
    if [[ $cmd0 == $_SEARCH_WORD* ]]; then
        query="${cmd0//$_SEARCH_WORD/}"
        /home/ovi/env0/bin/python /home/ovi/software/BSagent/llm_bash_script_generator.py "$query" 
        exec 2>&1   
        return 0
    fi

    # Fall back to default Bash behavior
    unset -f command_not_found_handle
    "$1" "${@:2}"
    return $?
}




# function post_command() {
#   exec 2>&1 
# }

# # Trap the ERR signal to run the error_handler function
# trap 'post_command' RETURN