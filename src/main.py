#!/usr/bin/env python3
import subprocess
import sys
import time
import os
from gemini_api import get_linux_command
from gemini_api import get_command_suggestions, LINUX_COMMANDS, LINUX_COMMANDS_NEED_FILE
from prompt_toolkit.styles import Style
from rich.console import Console
from rich.prompt import Prompt
from rich.panel import Panel
from rich.text import Text

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

def terminal_mode_with_prompt(user_prompt=None, show_tip=False):
    from gemini_api import get_api_key, save_api_key
    console = Console()
    try:
        api_key = get_api_key()
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
            # After saving the key, ask for alias setup
            shell = os.environ.get('SHELL', '')
            home = os.path.expanduser('~')
            script_path = os.path.abspath(__file__)
            main_path = os.path.dirname(script_path)
            default_alias = 't'

            # Determine rc_file before reading alias
            if 'zsh' in shell:
                rc_file = os.path.join(home, '.zshrc')
            else:
                rc_file = os.path.join(home, '.bashrc')

            # Get current alias if exists
            current_alias = ''
            if os.path.exists(rc_file):
                with open(rc_file, 'r') as f:
                    for line in f:
                        if line.strip().startswith('alias') and '/home/eid/Downloads/terminalAi/src/main.py' in line:
                            try:
                                current_alias = line.strip().split('=')[0].split()[1]
                            except Exception:
                                current_alias = ''
                            break

            prompt_msg = f"[bold cyan]Enter alias name to use for launching the app (default: t, current: {current_alias or 'None'})[/bold cyan]"
            alias_name = Prompt.ask(prompt_msg).strip()
            if not alias_name:
                alias_name = default_alias
            alias_line = f"alias {alias_name}='python3 {main_path}/main.py'"
            
            # Delete any existing aliases pointing to main.py
            if os.path.exists(rc_file):
                with open(rc_file, 'r') as f:
                    lines = f.readlines()
                with open(rc_file, 'w') as f:
                    for line in lines:
                        if not (line.strip().startswith('alias') and '/home/eid/Downloads/terminalAi/src/main.py' in line):
                            f.write(line)
            
            # Add new alias
            with open(rc_file, 'a') as f:
                f.write(f"\n{alias_line}\n")
            console.print(Panel(f"[green]Successfully added alias to ~/.bashrc[/green]\nTo activate it, execute the command: [bold yellow]exec bash[/bold yellow] or re-open your terminal.", expand=False))
            sys.exit(0)

        if user_prompt is not None:
            user_input = user_prompt.strip()
        else:
            user_input = Prompt.ask("[bold cyan]Enter your command in English[/bold cyan]").strip()
        # Update all option prompts to use the new format
        if user_input.lower() == 'exit':
            console.print("[bold yellow]Goodbye![/bold yellow]")
            return
        linux_cmd = get_linux_command(user_input)
        console.print(Panel(f"[bold green]Suggested Linux command:[/bold green]\n[yellow]{linux_cmd}[/yellow]", expand=False))
        confirm = Prompt.ask("[bold blue](e)xecute  (m)odify  (r)eprompt  (s)uggestions  (c)ancel[/bold blue]").strip().lower()
        while True:
            if confirm == 'm':
                linux_cmd = Prompt.ask("[bold cyan]Enter modified command[/bold cyan]", default=linux_cmd).strip()
                console.print(Panel(f"[bold green]Modified command:[/bold green]\n[yellow]{linux_cmd}[/yellow]", expand=False))
                confirm = Prompt.ask("[bold blue](e)xecute  (m)odify  (r)eprompt  (s)uggestions  (c)ancel[/bold blue]").strip().lower()
                continue
            if confirm == 'e':
                # Check if command might need sudo
                privileged_commands = ['dmidecode', 'fdisk', 'mount', 'umount', 'apt', 'apt-get', 'dpkg', 'systemctl', 'service']
                if any(cmd in linux_cmd for cmd in privileged_commands) and not linux_cmd.startswith('sudo'):
                    use_sudo = Prompt.ask("[bold yellow]This command might need sudo. Add sudo?[/bold yellow] (y/n)").strip().lower()
                    if use_sudo == 'y':
                        linux_cmd = f"sudo {linux_cmd}"
                
                while True:
                    try:
                        result = subprocess.run(linux_cmd, shell=True, check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                        if result.stdout:
                            console.print(result.stdout, end="")
                        if result.stderr:
                            console.print(result.stderr, end="")
                        break
                    except subprocess.CalledProcessError as e:
                        console.print(Panel(f"[red]Error executing command:[/red]\n{e.stderr}", expand=False))
                        if "permission denied" in e.stderr.lower() and not linux_cmd.startswith('sudo'):
                            retry_sudo = Prompt.ask("[bold yellow]Permission denied. Add sudo?[/bold yellow] (y/n)").strip().lower()
                            if retry_sudo == 'y':
                                linux_cmd = f"sudo {linux_cmd}"
                                continue
                        
                        # Return to main options after error
                        console.print("[yellow]Command failed. What would you like to do?[/yellow]")
                        error_choice = Prompt.ask("[bold blue](m)odify  (r)eprompt  (s)uggestions  (c)ancel[/bold blue]").strip().lower()
                        if error_choice == 'm':
                            linux_cmd = Prompt.ask("[bold cyan]Enter modified command[/bold cyan]", default=linux_cmd).strip()
                            continue
                        elif error_choice == 'r':
                            user_input = Prompt.ask("[bold cyan]Re-enter your command in English[/bold cyan]").strip()
                            if user_input.lower() == 'exit':
                                console.print("[bold yellow]Goodbye![/bold yellow]")
                                return
                            linux_cmd = get_linux_command(user_input)
                            console.print(Panel(f"[bold green]Suggested Linux command:[/bold green]\n[yellow]{linux_cmd}[/yellow]", expand=False))
                            confirm = Prompt.ask("[bold blue](e) Execute, (m) Modify, (r) Reprompt, (s) More-suggestions, (c) Cancel[/bold blue]").strip().lower()
                            continue  # Show options again for the new command
                        elif error_choice == 's':
                            # Show more options
                            break
                        else:  # cancel
                            console.print("[yellow]Command cancelled.[/yellow]")
                            return
                break
            elif confirm == 'r':
                user_input = Prompt.ask("[bold cyan]Re-enter your command in English[/bold cyan]").strip()
                if user_input.lower() == 'exit':
                    console.print("[bold yellow]Goodbye![/bold yellow]")
                    return
                linux_cmd = get_linux_command(user_input)
                console.print(Panel(f"[bold green]Suggested Linux command:[/bold green]\n[yellow]{linux_cmd}[/yellow]", expand=False))
                confirm = Prompt.ask("[bold blue](e) Execute, (r) Reprompt, (s) More-suggestions, (c) Cancel[/bold blue]").strip().lower()
            elif confirm == 's':
                try:
                    suggestions = get_command_suggestions(user_input + " (give me more alternatives and options)")
                    if suggestions:
                        suggestion_text = '\n'.join(f"[cyan]{i+1}.[/cyan] [yellow]{cmd}[/yellow] — {desc}" for i, (cmd, desc) in enumerate(suggestions))
                        console.print(Panel(f"[bold green]More-suggestions for Linux commands:[/bold green]\n{suggestion_text}\n\n[bold]Choose a number or Enter to go back[/bold]", expand=False))
                        choice = Prompt.ask("[bold blue]Choose number or Enter[/bold blue]").strip()
                        if choice.isdigit() and 1 <= int(choice) <= len(suggestions):
                            chosen_cmd = suggestions[int(choice)-1][0]
                            while True:
                                console.print(f"[bold green]Command to execute:[/bold green] [yellow]{chosen_cmd}[/yellow]")
                                exec_choice = Prompt.ask("[bold blue](e)xecute  (m)odify  (s)uggestions  (c)ancel[/bold blue]").strip().lower()
                                
                                if exec_choice == 'm':
                                    chosen_cmd = Prompt.ask("[bold cyan]Enter modified command[/bold cyan]", default=chosen_cmd).strip()
                                    continue
                                elif exec_choice == 's':
                                    # Show more command suggestions for the current command
                                    try:
                                        suggestions = get_command_suggestions(chosen_cmd + " (give me more alternatives and similar commands)")
                                        if suggestions:
                                            suggestion_text = '\n'.join(f"[cyan]{i+1}.[/cyan] [yellow]{cmd}[/yellow] — {desc}" for i, (cmd, desc) in enumerate(suggestions))
                                            console.print(Panel(f"[bold green]More-suggestions for Linux commands:[/bold green]\n{suggestion_text}\n\n[bold]Choose a number or Enter to go back[/bold]", expand=False))
                                            choice = Prompt.ask("[bold blue]Choose number or Enter[/bold blue]").strip()
                                            if choice.isdigit() and 1 <= int(choice) <= len(suggestions):
                                                chosen_cmd = suggestions[int(choice)-1][0]
                                                continue
                                        else:
                                            console.print("[yellow]No additional suggestions found.[/yellow]")
                                    except Exception as e:
                                        console.print(f"[red]Error fetching suggestions: {e}[/red]")
                                    continue  # Return to main command menu
                                elif exec_choice == 'c':
                                    console.print("[yellow]Command cancelled.[/yellow]")
                                    return
                                elif exec_choice == 'e':
                                    try:
                                        # Check if command might need sudo
                                        if any(word in chosen_cmd for word in ['dmidecode', 'fdisk', 'mount', 'umount', 'apt', 'systemctl']):
                                            use_sudo = Prompt.ask("[bold yellow]Add sudo?[/bold yellow] (y/n)").strip().lower() == 'y'
                                            if use_sudo:
                                                chosen_cmd = f"sudo {chosen_cmd}"
                                                
                                        result = subprocess.run(chosen_cmd, shell=True, check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                                        if result.stdout:
                                            console.print(result.stdout, end="")
                                        if result.stderr:
                                            console.print(result.stderr, end="")
                                        return
                                    except subprocess.CalledProcessError as e:
                                        console.print(Panel(f"[red]Error executing command:[/red]\n{e.stderr}", expand=False))
                                        if "permission denied" in e.stderr.lower() and not chosen_cmd.startswith('sudo'):
                                            retry_sudo = Prompt.ask("[bold yellow]Permission denied. Add sudo?[/bold yellow] (y/n)").strip().lower()
                                            if retry_sudo == 'y':
                                                chosen_cmd = f"sudo {chosen_cmd}"
                                                continue
                                        
                                        # Return to command options after error
                                        console.print("[yellow]Command failed. What would you like to do?[/yellow]")
                                        exec_choice = Prompt.ask("[bold blue](m)odify  (r)eprompt  (s)uggestions  (c)ancel[/bold blue]").strip().lower()
                                        if exec_choice == 'm':
                                            chosen_cmd = Prompt.ask("[bold cyan]Enter modified command[/bold cyan]", default=chosen_cmd).strip()
                                            continue
                                        elif exec_choice == 'r':
                                            user_input = Prompt.ask("[bold cyan]Re-enter your command in English[/bold cyan]").strip()
                                            if user_input.lower() == 'exit':
                                                console.print("[bold yellow]Goodbye![/bold yellow]")
                                                return
                                            chosen_cmd = get_linux_command(user_input)
                                            console.print(Panel(f"[bold green]Suggested Linux command:[/bold green]\n[yellow]{chosen_cmd}[/yellow]", expand=False))
                                            continue  # Show options again for the new command
                                        elif exec_choice == 's':
                                            # Show more suggestions
                                            break
                                        else:  # cancel
                                            console.print("[yellow]Command cancelled.[/yellow]")
                                            return
                                else:
                                    console.print("[red]Invalid option. Try again.[/red]")
                        else:
                            confirm = Prompt.ask("[bold blue](e) Execute, (r) Reprompt, (s) More-suggestions, (c) Cancel[/bold blue]").strip().lower()
                            continue
                    else:
                        console.print("[yellow]No additional suggestions found.[/yellow]")
                except Exception as e:
                    console.print(f"[red]Error fetching suggestions: {e}[/red]")
                confirm = Prompt.ask("[bold blue](e) Execute, (r) Reprompt, (s) More-suggestions, (c) Cancel[/bold blue]").strip().lower()
            else:
                console.print("[yellow]Command cancelled.[/yellow]")
                break
        # After execution or cancellation, print alias usage tip only if show_tip=True
        if show_tip:
            shell = os.environ.get('SHELL', '')
            home = os.path.expanduser('~')
            if 'zsh' in shell:
                rc_file = os.path.join(home, '.zshrc')
            else:
                rc_file = os.path.join(home, '.bashrc')
            alias_name = 't'
            if os.path.exists(rc_file):
                with open(rc_file, 'r') as f:
                    for line in f:
                        if line.strip().startswith('alias') and 'python3' in line and 'main.py' in line:
                            parts = line.strip().split('=')[0].split()
                            if len(parts) > 1:
                                alias_name = parts[1]
            # Print the tip more clearly and on a separate line
            tip_text = f"[bold cyan]Tip:[/bold cyan] Next time, you can run:\n[bold yellow]$ [bold green]{alias_name}[/bold green] your prompt here[/bold yellow]"
            console.print(Panel(tip_text, expand=False))
        return
    except KeyboardInterrupt:
        console.print("\n[bold yellow]Cancelled (Interrupted by user)[/bold yellow]")
        return
    except Exception as e:
        console.print(f"[bold red]An error occurred: {str(e)}[/bold red]")
    return

def main():
    try:
        # Autocomplete mode is permanently removed
        # If a prompt is passed as an argument, use it directly (Quick/Traditional mode)
        if len(sys.argv) > 1 and sys.argv[1] != '--menu':
            terminal_mode_with_prompt(' '.join(sys.argv[1:]))
            return
        # Default mode: menu
        from gemini_api import get_api_key, save_api_key
        console = Console()
        console.print(Panel("[bold cyan]Welcome to Commandify[/bold cyan]\n[green]Gemini Terminal AI[/green]", expand=False, border_style="cyan"))
        api_key = get_api_key()
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
            # After saving the key, ask for alias setup
            shell = os.environ.get('SHELL', '')
            home = os.path.expanduser('~')
            script_path = os.path.abspath(__file__)
            main_path = os.path.dirname(script_path)
            default_alias = 't'

            # Determine rc_file before reading alias
            if 'zsh' in shell:
                rc_file = os.path.join(home, '.zshrc')
            else:
                rc_file = os.path.join(home, '.bashrc')

            # Get current alias if exists
            current_alias = ''
            if os.path.exists(rc_file):
                with open(rc_file, 'r') as f:
                    for line in f:
                        if line.strip().startswith('alias') and '/home/eid/Downloads/terminalAi/src/main.py' in line:
                            try:
                                current_alias = line.strip().split('=')[0].split()[1]
                            except Exception:
                                current_alias = ''
                            break

            prompt_msg = f"[bold cyan]Enter alias name to use for launching the app (default: t, current: {current_alias or 'None'})[/bold cyan]"
            alias_name = Prompt.ask(prompt_msg).strip()
            if not alias_name:
                alias_name = default_alias
            alias_line = f"alias {alias_name}='python3 {main_path}/main.py'"
            
            # Delete any existing aliases pointing to main.py
            if os.path.exists(rc_file):
                with open(rc_file, 'r') as f:
                    lines = f.readlines()
                with open(rc_file, 'w') as f:
                    for line in lines:
                        if not (line.strip().startswith('alias') and '/home/eid/Downloads/terminalAi/src/main.py' in line):
                            f.write(line)
            
            # Add new alias
            with open(rc_file, 'a') as f:
                f.write(f"\n{alias_line}\n")
            console.print(Panel(f"[green]Successfully added alias to ~/.bashrc[/green]\nTo activate it, execute the command: [bold yellow]exec bash[/bold yellow] or re-open your terminal.", expand=False))
            sys.exit(0)
        while True:
            console.print("\n[bold magenta]Options:[/bold magenta] [1] Enter command  [2] Change API key  [3] Change alias and exit  [4] Help  [5] Exit")
            try:
                choice = Prompt.ask("[bold blue]Choose an option (1/2/3/4/5)[/bold blue]").strip()
                if choice == '3' or choice.lower() == 'alias' or choice.lower() == 'change alias and exit':
                    # Get current alias
                    current_alias = get_current_alias()
                    alias_name = Prompt.ask(f"[bold cyan]Enter alias name to use for launching the app (current: {current_alias}, default: t)[/bold cyan]").strip()
                    if not alias_name:
                        alias_name = 't'  # default alias
                    
                    # Determine .bashrc file
                    shell = os.environ.get('SHELL', '')
                    home = os.path.expanduser('~')
                    if 'zsh' in shell:
                        rc_file = os.path.join(home, '.zshrc')
                    else:
                        rc_file = os.path.join(home, '.bashrc')
                        
                    # Create new alias line
                    main_path = os.path.dirname(os.path.abspath(__file__))
                    alias_line = f"alias {alias_name}='python3 {main_path}/main.py'"
                    
                    # Read existing content
                    if os.path.exists(rc_file):
                        with open(rc_file, 'r') as f:
                            lines = f.readlines()
                        
                        # Remove all old terminalAi aliases
                        filtered_lines = []
                        for line in lines:
                            if not (line.strip().startswith('alias') and 'terminalAi/src/main.py' in line):
                                filtered_lines.append(line)
                        
                        # Write back filtered content plus new alias
                        with open(rc_file, 'w') as f:
                            f.writelines(filtered_lines)
                            if filtered_lines and not filtered_lines[-1].strip():
                                f.write(alias_line + '\n')  # Already have trailing newline
                            else:
                                f.write('\n' + alias_line + '\n')  # Add with newlines
                    else:
                        # If rc file doesn't exist, create it with just our alias
                        with open(rc_file, 'w') as f:
                            f.write(alias_line + '\n')
                    console.print(Panel(f"[green]Successfully added alias to ~/.bashrc[/green]\nTo activate it, execute the command: [bold yellow]exec bash[/bold yellow] or re-open your terminal.", expand=False))
                    sys.exit(0)
                elif choice == '2':
                    new_key = Prompt.ask("[bold green]Enter new Gemini API key[/bold green]").strip()
                    if new_key:
                        save_api_key(new_key)
                        console.print("[green]API key updated![/green]")
                    else:
                        console.print("[red]API key cannot be empty.[/red]")
                elif choice == '1':
                    # Directly enter traditional mode (terminal_mode_with_prompt) with alias tip
                    terminal_mode_with_prompt(show_tip=True)
                    break
                elif choice == '4' or choice.lower() == 'help':
                    # Enhance user experience in help display
                    from rich.align import Align
                    help_panels = [
                        Panel(Align.left("""
[bold magenta]Getting Started:[/bold magenta]
1. First time setup:
   • Enter your Gemini API key
   • Set up a command alias (default: 't')

2. Main Menu Options:
   [cyan]1[/cyan] - Enter command
   [cyan]2[/cyan] - Change API key
   [cyan]3[/cyan] - Change alias
   [cyan]4[/cyan] - Help
   [cyan]5[/cyan] - Exit
"""), title="[cyan]Basic Usage[/cyan]", expand=False),
                        Panel(Align.left("""
[bold magenta]Entering Commands:[/bold magenta]
1. Type your command in English:
   Example: [green]"show running processes"[/green] or [green]"create a new directory called test"[/green]

2. The program will:
   • Show the suggested Linux command
   • Give you options:
     [cyan](e)[/cyan] - Execute command
     [cyan](r)[/cyan] - Reprompt with new request
     [cyan](s)[/cyan] - More-suggestions
     [cyan](c)[/cyan] - Cancel

3. If you choose More-suggestions:
   • Select a number to use that command
   • You can then:
     [cyan](e)[/cyan] - Execute command as is
     [cyan](m)[/cyan] - Modify command before executing
     [cyan](s)[/cyan] - More-suggestions
     [cyan](c)[/cyan] - Cancel
"""), title="[cyan]Command Usage[/cyan]", expand=False),
                        Panel(Align.left("""
[bold magenta]Smart Features:[/bold magenta]
• [yellow]Sudo Detection:[/yellow] Automatically detects commands that might need sudo
• [yellow]Error Handling:[/yellow] If a command fails, you can:
  • Retry with sudo if it's a permission issue
  • Modify the command directly
  • Get more command suggestions
  • Cancel and start over

• [yellow]Quick Access:[/yellow] Use the alias (default: 't') for faster access:
  [green]t list files[/green]
  [green]t check disk space[/green]
"""), title="[cyan]Advanced Features[/cyan]", expand=False),
                        Panel(Align.left("""
[bold magenta]Tips:[/bold magenta]
• Be descriptive in your requests
• You can type [yellow]exit[/yellow] at any time to quit
• Use the 'Show more' option to see alternative commands
• If a command fails, you'll always have the option to modify it
"""), title="[cyan]Tips & Tricks[/cyan]", expand=False)
                    ]
                    for p in help_panels:
                        console.print(p)
                elif choice == '5' or choice.lower() == 'exit':
                    console.print("[bold yellow]Goodbye![/bold yellow]")
                    break
                else:
                    console.print("[red]Invalid option. Please choose 1, 2, 3, 4, or 5.[/red]")
            except KeyboardInterrupt:
                console.print("\n[bold yellow]Goodbye! (Interrupted by user)[/bold yellow]")
                sys.exit(0)
    except KeyboardInterrupt:
        console.print("\n[bold yellow]Goodbye! (Interrupted by user)[/bold yellow]")
        sys.exit(0)
    return

def get_current_alias():
    """Find the current alias in .bashrc or .zshrc"""
    home = os.path.expanduser('~')
    shell = os.environ.get('SHELL', '')
    current_aliases = []
    
    # Determine shell rc file
    if 'zsh' in shell:
        rc_file = os.path.join(home, '.zshrc')
    else:
        rc_file = os.path.join(home, '.bashrc')
    
    if os.path.exists(rc_file):
        with open(rc_file, 'r') as f:
            for line in f:
                if line.strip().startswith('alias') and 'terminalAi/src/main.py' in line:
                    try:
                        alias = line.strip().split('=')[0].split()[1]
                        current_aliases.append(alias)
                    except:
                        pass
    
    # Return the most recent alias or 'None' if no aliases found
    return current_aliases[-1] if current_aliases else 'None'

if __name__ == "__main__":
    main()