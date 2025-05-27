#!/usr/bin/env python3
import subprocess
import sys
import time
import os
from gemini_api import get_linux_command
from gemini_api import get_command_suggestions, LINUX_COMMANDS, LINUX_COMMANDS_NEED_FILE, get_api_key, save_api_key # Added imports
from prompt_toolkit.styles import Style
from rich.console import Console
from rich.prompt import Prompt
from rich.panel import Panel
from rich.text import Text
from rich.align import Align # Added import

# Define colors and styles to enhance the user interface
STYLE = Style.from_dict({
    # Autocomplete menu styles
    'completion-menu.completion': 'bg:#2c3e50 #ecf0f1',
    'completion-menu.completion.current': 'bg:#3498db #ffffff bold',
    'completion-menu.meta.completion': 'bg:#2c3e50 #95a5a6',
    'completion-menu.meta.completion.current': 'bg:#3498db #ffffff',
    # Scrollbar style
    'scrollbar.background': 'bg:#636e72',
    'scrollbar.button': 'bg:#2d3436',
    # Prompt style
    'prompt': 'bg:#2c3e50 #e74c3c bold',
    # Input text style
    'prompt.text': '#ecf0f1',
    # Cursor style
    'loading': '#e67e22 italic',
    # New style for dark yellow color
    'custom-prompt': 'ansiyellow bold',
})

console = Console()

def get_current_alias(rc_file):
    """Tries to find the current alias for this application in the rc_file."""
    if not os.path.exists(rc_file):
        return None

    try:
        # Determine the potential command paths
        source_script_path = os.path.abspath(__file__)
        source_command = f"python3 '{source_script_path}'"
        source_command_no_quotes = f"python3 {source_script_path}"

        binary_executable_path = None
        binary_command = None
        binary_command_no_quotes = None
        if getattr(sys, 'frozen', False):
            binary_executable_path = sys.executable
            binary_command = f"'{binary_executable_path}'"
            binary_command_no_quotes = binary_executable_path

        with open(rc_file, 'r') as f:
            for line in f:
                stripped_line = line.strip()
                if not stripped_line.startswith('alias '):
                    continue

                parts = stripped_line.split('=', 1)
                if len(parts) != 2:
                    continue

                alias_name_part = parts[0].replace('alias ', '', 1).strip()
                command_part = parts[1].strip().strip("'\"") # Remove potential outer quotes
                command_part_raw = parts[1].strip() # Keep original quotes for comparison

                # Check if command matches source script path (with or without quotes)
                if command_part_raw == source_command or command_part == source_command_no_quotes:
                    return alias_name_part

                # Check if command matches binary executable path (if frozen)
                if binary_command and (command_part_raw == binary_command or command_part == binary_command_no_quotes):
                    return alias_name_part

                # Heuristic check for old source path (less reliable, use script name)
                script_basename = os.path.basename(source_script_path)
                if script_basename in command_part and 'python3' in command_part:
                    # Check if it seems to point to *this* script's directory structure
                    # This is risky, might catch unrelated aliases
                    # Consider removing if it causes issues
                    if 'terminalAi/src' in command_part or 'src/main.py' in command_part:
                         return alias_name_part

                # Heuristic check for old binary path in /tmp (less reliable)
                if binary_executable_path and '/tmp/_MEI' in command_part and os.path.basename(binary_executable_path) in command_part:
                     return alias_name_part

    except Exception as e:
        console.print(f"[yellow]Warning: Could not read {rc_file} to find current alias: {e}[/yellow]")
        pass # Ignore errors reading rc file for this check

    return None # No matching alias found

def update_rc_file(rc_file, new_alias_name, new_alias_command):
    """Removes old aliases and adds the new one."""
    source_script_path = os.path.abspath(__file__)
    script_basename = os.path.basename(source_script_path)
    source_command_quoted = f"python3 '{source_script_path}'"
    source_command_unquoted = f"python3 {source_script_path}"

    binary_executable_path = None
    binary_command_quoted = None
    binary_command_unquoted = None
    executable_basename = None
    if getattr(sys, 'frozen', False):
        binary_executable_path = sys.executable
        executable_basename = os.path.basename(binary_executable_path)
        binary_command_quoted = f"'{binary_executable_path}'"
        binary_command_unquoted = binary_executable_path

    lines = []
    if os.path.exists(rc_file):
        try:
            with open(rc_file, 'r') as f:
                lines = f.readlines()
        except Exception as e:
            console.print(f"[red]Error reading {rc_file}: {e}[/red]")
            return False # Indicate failure

    filtered_lines = []
    alias_found_and_removed = False
    for line in lines:
        stripped_line = line.strip()
        keep_line = True

        if stripped_line.startswith('alias '):
            parts = stripped_line.split('=', 1)
            if len(parts) == 2:
                alias_def_name = parts[0].replace('alias ', '', 1).strip()
                command_part_raw = parts[1].strip()
                command_part_unquoted = command_part_raw.strip("'\"")

                # 1. Remove alias if it has the target name
                if alias_def_name == new_alias_name:
                    keep_line = False
                    alias_found_and_removed = True

                # 2. Remove alias if it points to the source script
                elif command_part_raw == source_command_quoted or command_part_unquoted == source_command_unquoted:
                    keep_line = False
                    alias_found_and_removed = True

                # 3. Remove alias if it points to the binary executable (if frozen)
                elif binary_command_quoted and (command_part_raw == binary_command_quoted or command_part_unquoted == binary_command_unquoted):
                    keep_line = False
                    alias_found_and_removed = True

                # 4. Heuristic: Remove alias pointing to old /tmp/_MEI binary path
                elif executable_basename and '/tmp/_MEI' in command_part_unquoted and executable_basename in command_part_unquoted:
                    keep_line = False
                    alias_found_and_removed = True
                
                # 5. Heuristic: Remove alias pointing to likely old source path (contains script name)
                # Be careful with this one - might remove unrelated aliases
                elif 'python3' in command_part_unquoted and script_basename in command_part_unquoted and ('terminalAi/src' in command_part_unquoted or 'src/main.py' in command_part_unquoted):
                    keep_line = False
                    alias_found_and_removed = True

        if keep_line:
            filtered_lines.append(line)

    # Ensure the last line has a newline if needed before appending
    if filtered_lines and not filtered_lines[-1].endswith('\n'):
        filtered_lines[-1] += '\n'

    # Add the new alias line
    new_alias_line = f"alias {new_alias_name}={new_alias_command}\n"
    filtered_lines.append(new_alias_line)

    # Write back the modified content
    try:
        with open(rc_file, 'w') as f:
            f.writelines(filtered_lines)
        return True # Indicate success
    except Exception as e:
        console.print(f"[red]Error writing to {rc_file}: {e}[/red]")
        return False # Indicate failure

def terminal_mode_with_prompt(user_prompt=None, show_tip=False):
    # (Keep the existing terminal_mode_with_prompt function content as is)
    # ... (original function code) ...
    # Define privileged commands list at the top level
    privileged_commands = ['dmidecode', 'fdisk', 'mount', 'umount', 'apt', 'apt-get', 'dpkg', 'systemctl', 'service']

    def execute_command(cmd, is_privileged=False):
        """Helper function to execute commands with proper error handling"""
        if is_privileged and not cmd.startswith('sudo '):
            use_sudo = Prompt.ask("[bold yellow]This command might need sudo. Add sudo?[/bold yellow] (y/n)").strip().lower()
            if use_sudo == 'y':
                cmd = f"sudo {cmd}"
        
        try:
            # Use Popen for potentially interactive commands, but run for simple ones
            # For now, stick with run, assuming non-interactive commands from Gemini
            result = subprocess.run(cmd, shell=True, check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if result.stdout:
                console.print(result.stdout, end='')
            if result.stderr:
                console.print(f"[red]{result.stderr}[/red]", end='') # Print stderr in red
            return (True, None)  # Success with no error
        except subprocess.CalledProcessError as e:
            error_output = e.stderr if e.stderr else e.stdout
            if error_output:
                console.print(f"[red]{error_output}[/red]", end='') # Print stderr in red
            else: # If no stderr/stdout, print the exception message itself
                 console.print(f"[red]Error executing command: {e}[/red]")
                 
            # Improved sudo prompt logic
            if "permission denied" in str(e).lower() or (error_output and "permission denied" in error_output.lower()) and not cmd.startswith('sudo '):
                retry_sudo = Prompt.ask("[bold yellow]Permission denied. Retry with sudo?[/bold yellow] (y/n)").strip().lower()
                if retry_sudo == 'y':
                    return execute_command(f"sudo {cmd}", False) # Retry with sudo, is_privileged becomes False
            return (False, error_output or str(e))  # Return both status and error
        except FileNotFoundError:
             console.print(f"[red]Error: Command not found: {cmd.split()[0]}[/red]")
             return (False, f"Command not found: {cmd.split()[0]}")
        except Exception as general_exception:
             console.print(f"[red]An unexpected error occurred: {general_exception}[/red]")
             return (False, str(general_exception))

    # Rest of the function implementation
    try:
        api_key = get_api_key()
        if not api_key:
            # This part should ideally not be reached if main() handles it first
            console.print("[yellow]No Gemini API key found. Please run the app without arguments first to set it up.[/yellow]")
            return

        # Get initial user input
        if user_prompt is not None:
            user_input = user_prompt.strip()
        else:
            user_input = Prompt.ask("[bold cyan]Enter your command in English (or 'exit')[/bold cyan]").strip()
        
        if user_input.lower() == 'exit':
            console.print("[bold yellow]Goodbye![/bold yellow]")
            return

        while True:  # Main command execution loop
            console.print("[yellow]Getting suggestion from Gemini...[/yellow]")
            linux_cmd = get_linux_command(user_input)
            if not linux_cmd:
                 console.print("[red]Failed to get command suggestion. Please try again or rephrase.[/red]")
                 user_input = Prompt.ask("[bold cyan]Re-enter your command in English (or 'exit')[/bold cyan]").strip()
                 if user_input.lower() == 'exit':
                     console.print("[bold yellow]Goodbye![/bold yellow]")
                     return
                 continue # Go back to start of loop
                 
            show_box = True
            
            while True:  # Command execution inner loop
                if show_box:
                    console.print(Panel(f"[bold green]Suggested Linux command:[/bold green]\n[yellow]{linux_cmd}[/yellow]", expand=False))
                    show_box = False
                
                confirm = Prompt.ask("[bold blue](e)xecute  (m)odify  (r)eprompt  (s)uggestions  (c)ancel[/bold blue]").strip().lower()
                
                if confirm == 'm':
                    linux_cmd = Prompt.ask("[bold cyan]Enter modified command[/bold cyan]", default=linux_cmd).strip()
                    show_box = True  # Show box with modified command
                    continue

                elif confirm == 'e':
                    # Execute the command
                    is_privileged = any(cmd in linux_cmd for cmd in privileged_commands)
                    success, error = execute_command(linux_cmd, is_privileged)
                    # If successful, exit. If failed, stay in the inner loop to allow modification/retry.
                    if success:
                        # Decide whether to exit or ask for another command
                        # For now, let's exit after successful execution in direct mode
                        if user_prompt is not None: 
                             sys.exit(0)
                        else: # If in interactive mode, break inner loop to ask for new command
                             break 
                    # On failure, just continue the inner loop (stay with the same suggested command)
                    continue 

                elif confirm == 'r':
                    user_input = Prompt.ask("[bold cyan]Re-enter your command in English (or 'exit')[/bold cyan]").strip()
                    if user_input.lower() == 'exit':
                        console.print("[bold yellow]Goodbye![/bold yellow]")
                        return # Exit function completely
                    break  # Break inner loop to get new command suggestion based on new user_input

                elif confirm == 's':
                    console.print("[yellow]Getting alternative suggestions...[/yellow]")
                    suggestions = get_command_suggestions(user_input + " (give me more alternatives and options)")
                    if suggestions:
                        while True:  # Suggestions menu loop
                            suggestion_text = '\n'.join(f"[cyan]{i+1}.[/cyan] [yellow]{cmd}[/yellow] — {desc}" for i, (cmd, desc) in enumerate(suggestions))
                            console.print(Panel(f"[bold green]Alternative commands:[/bold green]\n{suggestion_text}\n\n[bold]Choose a number or Enter to go back[/bold]", expand=False))
                            choice = Prompt.ask("[bold blue]Choose number or Enter[/bold blue]").strip()

                            if not choice:  # User pressed Enter
                                show_box = True  # Show original command box again
                                break # Break suggestions loop, go back to inner command loop

                            if choice.isdigit() and 1 <= int(choice) <= len(suggestions):
                                selected_cmd = suggestions[int(choice)-1][0]
                                console.print(Panel(f"[bold green]Selected command:[/bold green]\n[yellow]{selected_cmd}[/yellow]", expand=False))
                                
                                # Inner loop for selected suggestion
                                while True:
                                    exec_choice = Prompt.ask("[bold blue](e)xecute  (m)odify  (b)ack to suggestions  (c)ancel[/bold blue]").strip().lower()
                                    
                                    if exec_choice == 'e':
                                        is_privileged = any(priv_cmd in selected_cmd for priv_cmd in privileged_commands)
                                        success, error = execute_command(selected_cmd, is_privileged)
                                        if success:
                                             if user_prompt is not None:
                                                 sys.exit(0)
                                             else:
                                                 # Break out of *both* inner loops to ask for a new command
                                                 # Need a flag or different approach
                                                 # For now, let's just break the suggestion execution loop
                                                 # and let the user decide again from the main prompt
                                                 # This requires breaking the outer suggestion loop too.
                                                 goto_main_prompt = True
                                                 break # break suggestion execution loop
                                        # On failure, stay in suggestion execution loop
                                        continue 
                                    
                                    elif exec_choice == 'm':
                                        modified_cmd = Prompt.ask("[bold cyan]Enter modified command[/bold cyan]", default=selected_cmd).strip()
                                        # Treat modified command as the new 'selected_cmd' for this loop
                                        selected_cmd = modified_cmd 
                                        console.print(Panel(f"[bold green]Modified command:[/bold green]\n[yellow]{selected_cmd}[/yellow]", expand=False))
                                        continue # Go back to execute/modify prompt for the modified command
                                    
                                    elif exec_choice == 'b':
                                        # Go back to suggestions list
                                        break # break suggestion execution loop
                                    
                                    else:  # cancel
                                        console.print("[yellow]Command cancelled.[/yellow]")
                                        sys.exit(0)
                                # End of suggestion execution loop
                                if exec_choice == 'b': # If user chose 'back'
                                     continue # Continue the suggestions list loop
                                if 'goto_main_prompt' in locals() and goto_main_prompt:
                                     break # Break suggestions list loop
                                     
                            else:
                                console.print("[red]Invalid choice. Please select a valid number or press Enter.[/red]")
                        # End of suggestions list loop
                        if 'goto_main_prompt' in locals() and goto_main_prompt:
                             break # Break inner command loop to ask for new command
                        # If we finished suggestions loop normally (user pressed Enter), show original box again
                        show_box = True 
                        continue # Continue inner command loop
                    else:
                        console.print("[yellow]No alternative suggestions found.[/yellow]")
                        show_box = True # Show original command box again
                        continue # Continue inner command loop

                else:  # cancel
                    console.print("[yellow]Command cancelled.[/yellow]")
                    sys.exit(0)
            # End of inner command loop (either executed successfully in interactive, or chose reprompt)
            # Ask for new command (only if not in direct mode)
            if user_prompt is None:
                 user_input = Prompt.ask("[bold cyan]Enter your command in English (or 'exit')[/bold cyan]").strip()
                 if user_input.lower() == 'exit':
                     console.print("[bold yellow]Goodbye![/bold yellow]")
                     return
            else:
                 # Should have exited already if successful in direct mode
                 # If direct mode failed, the loop should handle it?
                 # Let's assume direct mode exits on success or error handled inside.
                 break # Exit outer loop if started with user_prompt

        # Alias usage tip (moved outside the main loop, shown only if requested)
        if show_tip:
            shell = os.environ.get('SHELL', '')
            home = os.path.expanduser('~')
            if 'zsh' in shell:
                rc_file = os.path.join(home, '.zshrc')
            else:
                rc_file = os.path.join(home, '.bashrc')
            
            alias_name = get_current_alias(rc_file) or 't' # Get the actual current alias
            
            tip_text = f"[bold cyan]Tip:[/bold cyan] Next time, you can run:\n[bold yellow]$ [bold green]{alias_name}[/bold green] your prompt here[/bold yellow]"
            console.print(Panel(tip_text, expand=False))

    except KeyboardInterrupt:
        console.print("\n[bold yellow]Cancelled (Interrupted by user)[/bold yellow]")
        return
    except Exception as e:
        console.print(f"[bold red]An unexpected error occurred: {str(e)}[/bold red]")
        import traceback
        traceback.print_exc() # Print traceback for debugging
    return

def main():
    try:
        # If a prompt is passed as an argument, use it directly (Quick/Traditional mode)
        if len(sys.argv) > 1 and sys.argv[1] != '--menu':
            terminal_mode_with_prompt(' '.join(sys.argv[1:]), show_tip=False) # Don't show tip in direct mode
            return

        # Default mode: menu
        console.print(Panel("[bold cyan]Welcome to Commandify[/bold cyan]\n[green]Gemini Terminal AI[/green]", expand=False, border_style="cyan"))
        api_key = get_api_key()

        # --- Initial Setup: API Key and Alias --- 
        if not api_key:
            console.print("[yellow]No Gemini API key found.[/yellow]")
            while True:
                api_key = Prompt.ask("[bold green]Please enter your Gemini API key[/bold green]").strip()
                if api_key:
                    save_api_key(api_key)
                    console.print("[green]API key saved![/green]")
                    break
                else:
                    console.print("[red]API key cannot be empty.[/red]")
            
            # --- Alias Setup during Initial Run ---
            shell = os.environ.get('SHELL', '')
            home = os.path.expanduser('~')
            default_alias = 't'
            rc_file = os.path.join(home, '.zshrc') if 'zsh' in shell else os.path.join(home, '.bashrc')
            rc_filename = os.path.basename(rc_file)
            shell_name = os.path.basename(shell)

            # Determine executable path for alias command
            if getattr(sys, 'frozen', False):
                executable_path = sys.executable
                alias_command = f"'{executable_path}'" # Quote path for safety
            else:
                script_path = os.path.abspath(__file__)
                alias_command = f"python3 '{script_path}'" # Quote path for safety

            # Get current alias if exists
            current_alias_display = get_current_alias(rc_file) or default_alias # Show default if none found
            prompt_msg = f"[bold cyan]Enter alias name to use for launching the app (current: {current_alias_display}, default: t)[/bold cyan]"
            
            alias_name = Prompt.ask(prompt_msg).strip()
            if not alias_name:
                alias_name = default_alias

            # Update rc file (removes old, adds new)
            success = update_rc_file(rc_file, alias_name, alias_command)

            if success:
                console.print(Panel(f"[green]Successfully set alias '{alias_name}' in {rc_filename}[/green]\nTo activate it, execute the command: [bold yellow]exec {shell_name}[/bold yellow] or re-open your terminal.", expand=False))
            else:
                 console.print(f"[red]Failed to update {rc_filename}. Please check permissions or edit manually.[/red]")
                 console.print(f"You can manually add: alias {alias_name}={alias_command}")

            sys.exit(0) # Exit after initial setup

        # --- Main Menu Loop --- 
        while True:
            console.print("\n[bold magenta]Options:[/bold magenta] [1] Enter command  [2] Change API key  [3] Change alias and exit  [4] Help  [5] Exit")
            try:
                choice = Prompt.ask("[bold blue]Choose an option (1/2/3/4/5)[/bold blue]").strip()

                if choice == '1':
                    # Enter interactive command mode, show alias tip afterwards
                    terminal_mode_with_prompt(show_tip=True)
                    # After returning from terminal_mode_with_prompt, continue the menu loop
                    continue 

                elif choice == '2':
                    new_key = Prompt.ask("[bold green]Enter new Gemini API key[/bold green]").strip()
                    if new_key:
                        save_api_key(new_key)
                        console.print("[green]API key updated![/green]")
                    else:
                        console.print("[red]API key cannot be empty.[/red]")

                elif choice == '3' or choice.lower() == 'alias' or choice.lower() == 'change alias and exit':
                    # --- Change Alias Option --- 
                    shell = os.environ.get('SHELL', '')
                    home = os.path.expanduser('~')
                    default_alias = 't'
                    rc_file = os.path.join(home, '.zshrc') if 'zsh' in shell else os.path.join(home, '.bashrc')
                    rc_filename = os.path.basename(rc_file)
                    shell_name = os.path.basename(shell)

                    # Get current alias
                    current_alias = get_current_alias(rc_file) or default_alias
                    alias_name = Prompt.ask(f"[bold cyan]Enter alias name to use for launching the app (current: {current_alias}, default: t)[/bold cyan]").strip()
                    if not alias_name:
                        alias_name = default_alias

                    # Determine executable path for alias command
                    if getattr(sys, 'frozen', False):
                        executable_path = sys.executable
                        alias_command = f"'{executable_path}'" # Quote path for safety
                    else:
                        script_path = os.path.abspath(__file__)
                        alias_command = f"python3 '{script_path}'" # Quote path for safety

                    # Update rc file (removes old, adds new)
                    success = update_rc_file(rc_file, alias_name, alias_command)

                    if success:
                        console.print(Panel(f"[green]Successfully set alias '{alias_name}' in {rc_filename}[/green]\nTo activate it, execute the command: [bold yellow]exec {shell_name}[/bold yellow] or re-open your terminal.", expand=False))
                    else:
                         console.print(f"[red]Failed to update {rc_filename}. Please check permissions or edit manually.[/red]")
                         console.print(f"You can manually add: alias {alias_name}={alias_command}")

                    sys.exit(0) # Exit after changing alias

                elif choice == '4' or choice.lower() == 'help':
                    # --- Help Option --- 
                    help_panels = [
                        Panel(Align.left("""
[bold magenta]Getting Started:[/bold magenta]
1. First time setup:
   • Enter your Gemini API key when prompted.
   • Set up a command alias (default: 't') for easy access.

2. Main Menu Options:
   [cyan]1[/cyan] - Enter command: Get Linux command suggestions based on your English prompt.
   [cyan]2[/cyan] - Change API key: Update your saved Gemini API key.
   [cyan]3[/cyan] - Change alias: Modify the shell alias used to launch this app.
   [cyan]4[/cyan] - Help: Display this help message.
   [cyan]5[/cyan] - Exit: Close the application.
"""), title="[cyan]Basic Usage[/cyan]", expand=False, border_style="green"),
                        Panel(Align.left("""
[bold magenta]Entering Commands (Option 1):[/bold magenta]
1. Type your request in English (e.g., [green]"list files sorted by size"[/green]).
2. The suggested Linux command will be shown.
3. Choose an action:
   [cyan](e)[/cyan]xecute: Run the suggested command.
   [cyan](m)[/cyan]odify: Edit the command before running.
   [cyan](r)[/cyan]eprompt: Enter a new English request.
   [cyan](s)[/cyan]uggestions: Get alternative command suggestions.
   [cyan](c)[/cyan]ancel: Abort the current command.

[bold magenta]Quick Mode:[/bold magenta]
Run the app directly with your prompt:
[yellow]$ <your_alias> find all text files in my home directory[/yellow]
(Replace <your_alias> with the alias you set, e.g., 't')
"""), title="[cyan]Command Interaction[/cyan]", expand=False, border_style="yellow"),
                    ]
                    for panel in help_panels:
                        console.print(panel)

                elif choice == '5' or choice.lower() == 'exit':
                    console.print("[bold yellow]Goodbye![/bold yellow]")
                    sys.exit(0)
                else:
                    console.print("[red]Invalid choice. Please enter a number between 1 and 5.[/red]")

            except (EOFError, KeyboardInterrupt):
                console.print("\n[bold yellow]Goodbye! (Interrupted by user)[/bold yellow]")
                sys.exit(0)
            except Exception as e:
                 console.print(f"[bold red]An error occurred in the menu: {e}[/bold red]")
                 import traceback
                 traceback.print_exc()
                 # Decide whether to exit or continue loop after error
                 # For now, let's continue the loop
                 continue

    except Exception as e:
        console.print(f"[bold red]A critical error occurred: {e}[/bold red]")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
