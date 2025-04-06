

_GLOBAL_STDERR_LOG=$(mktemp)
_SEARCH_WORD="?-"
lock=false


_bash_error_handler_detailed() {
  /home/ovi/env0/bin/python /home/ovi/software/BSagent/llm_bash_script_generator.py --error "$(cat $_GLOBAL_STDERR_LOG)" "$BASH_COMMAND"
  exec 2>&1
  lock=false
}
trap '_bash_error_handler_detailed' ERR


# Custom command-not-found handler (override of a built in function)
command_not_found_handle() {
    # Check if the command starts with _SEARCH_WORD
    cmd0=$*
    if [[ $cmd0 == $_SEARCH_WORD* ]]; then
        cmd0="${cmd0//$_SEARCH_WORD/}"
        /home/ovi/env0/bin/python /home/ovi/software/BSagent/llm_bash_script_generator.py "$cmd0"
        exec 2>&1
        return 0
    fi

    # Fall back to default Bash behavior
    unset -f command_not_found_handle
    "$1" "${@:2}"
    return $?
}


function inturrupt0() {
    exec 2>&1
}
trap 'inturrupt0' SIGINT


# IMPORTANT : it is important for this to be as the last
#             because it cause problems in read errors if then
#             the pre_command trap start before
function pre_command() {
  if [ "$lock" = false ]; then
    exec 2> >(tee "$_GLOBAL_STDERR_LOG" >&2)
    > "$_GLOBAL_STDERR_LOG"
    lock=true
  fi
}
trap 'pre_command' DEBUG
