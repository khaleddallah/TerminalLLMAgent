

_GLOBAL_STDERR_LOG=$(mktemp)
_SEARCH_WORD="?-"
lock=false

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
VENV_PYTHON=$SCRIPT_DIR/venv/bin/python
LLM_TERMINAL_AGENT=$SCRIPT_DIR/src/bashscript_llm_agent.py

_bash_error_handler_detailed() {
  error0=$(cat $_GLOBAL_STDERR_LOG)
  exec 2>&1
  $VENV_PYTHON $LLM_TERMINAL_AGENT --error "$error0" "$BASH_COMMAND"
  lock=false
}
trap '_bash_error_handler_detailed' ERR


# Custom command-not-found handler (override of a built in function)
command_not_found_handle() {
    # Check if the command starts with _SEARCH_WORD
    cmd0=$*
    if [[ $cmd0 == $_SEARCH_WORD* ]]; then
        cmd0="${cmd0//$_SEARCH_WORD/}"
        exec 2>&1
        $VENV_PYTHON $LLM_TERMINAL_AGENT "$cmd0"
        return 0
    fi

    # Fall back to default Bash behavior
    unset -f command_not_found_handle
    "$1" "${@:2}"
    return $?
}


function post_command() {
    exec 2>&1
    lock=false
}
PROMPT_COMMAND="${PROMPT_COMMAND:+$PROMPT_COMMAND; }post_command"


# IMPORTANT : it is important for this to be as the last
#             because it cause problems in read errors if then
#             the pre_command trap start before
function pre_command() {
  if [ "$lock" = false ]; then
    exec 2> >(tee "$_GLOBAL_STDERR_LOG" >&2)
    lock=true
  fi
}
trap 'pre_command' DEBUG
