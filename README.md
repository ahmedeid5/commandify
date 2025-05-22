# Commandify - Your AI-Powered Terminal Assistant

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Gemini AI](https://img.shields.io/badge/Gemini-AI-orange.svg)](https://deepmind.google/technologies/gemini/)
[![Rich UI](https://img.shields.io/badge/Rich-UI-purple.svg)](https://rich.readthedocs.io/)
[![Release](https://img.shields.io/github/v/release/ahmedeid5/commandify)](https://github.com/ahmedeid5/commandify/releases/latest)

Commandify is an intelligent terminal assistant that translates English descriptions into Linux commands using Google's Gemini AI. It helps both beginners and experienced users interact with the Linux terminal more naturally.

## Features

- 🤖 **AI-Powered Command Translation**: Simply describe what you want to do in English
- 🔄 **Multiple Suggestions**: Get alternative commands for the same task
- 🛡️ **Smart Sudo Detection**: Automatically detects when commands need elevated privileges
- ⚠️ **Error Handling**: Helpful options when commands fail
- 💡 **Interactive Interface**: User-friendly terminal UI with color coding
- ⚡ **Quick Access**: Custom alias for faster access

## Installation

### Option 1: Using Pre-built Binary (Linux)
1. Download the latest release from [GitHub Releases](https://github.com/ahmedeid5/commandify/releases/latest)
2. Extract the archive:
```bash
tar -xzf commandify-linux-x64.tar.gz
```
3. Make it executable and move to your bin directory:
```bash
chmod +x commandify
sudo mv commandify /usr/local/bin/
```
4. Get your Gemini API key from [Google AI Studio](https://makersuite.google.com/app/apikey)
   - The app will prompt you to enter it on first run
   - Your key will be saved securely for future use
5. Run the program:
```bash
commandify
```

### Option 2: From Source
1. Clone the repository:
```bash
git clone https://github.com/ahmedeid5/commandify.git
cd commandify
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up your Gemini API key:
- Get your API key from [Google AI Studio](https://makersuite.google.com/app/apikey)
- The app will prompt you to enter it on first run

## Usage

### Basic Usage
Run the program:
```bash
python3 src/main.py
```

Or use the configured alias (default: 't'):
```bash
t show running processes
t check disk space
```

### Menu Options
1. **Enter command**: Input your command in English
2. **Change API key**: Update your Gemini API key
3. **Change alias**: Modify the quick access command
4. **Help**: Show detailed usage instructions
5. **Exit**: Close the application

### Example Commands
- "show all running processes"
- "create a new directory called projects"
- "check system memory usage"
- "find all pdf files in downloads folder"
- "show network connections"

## Smart Features

### Sudo Detection
- Automatically detects commands that might need sudo
- Prompts for confirmation before adding sudo
- Helps prevent permission-related errors

### Error Handling
When a command fails, you can:
- Retry with sudo if it's a permission issue
- Modify the command directly
- Get more command suggestions
- Cancel and start over

### Command Suggestions
- Get multiple alternative commands
- View detailed descriptions for each suggestion
- Modify suggestions before execution
- Chain multiple commands together

## Contributing

Contributions are welcome! Please feel free to submit pull requests.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## Requirements

- Python 3.8 or higher
- Required Python packages (installed via requirements.txt):
  - requests
  - prompt_toolkit
  - rich
  - google-ai-generativelanguage
  - google-auth

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Built with Google's Gemini AI
- Uses the Rich library for terminal styling
- Inspired by the need to make terminal commands more accessible
