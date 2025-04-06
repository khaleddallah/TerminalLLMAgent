# Bash Script LLM Agent
[[logo.png]]    
The Bash Script LLM Agent is a command-line tool designed to help you to: 
* **Generate Bash Scripts:** Given a natural language prompt, it can generate the corresponding bash script.
* **Suggest Error Solutions:** When you encounter an error in your terminal, it can analyze the error message and provide relevant solutions.


### Motive 
Skip the browser. Get bash help directly in your terminal. No more copying and pasting.


### Installation    
1.  Clone this repository.
2.  Navigate to the repository directory.
3.  Run the installation script:

    ```bash
    ./install.sh
    ```

### Usage
* **Error Handling:** When a command results in an error, the agent will automatically analyze the error message and suggest potential solutions.
* **Direct Prompting:** To directly ask the agent for a bash command or script, start your query with `?-`.

    Example:

    ```bash
    ?- list all files in the current directory with size greater than 1MB
    ```
