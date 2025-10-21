# Lumecode

AI-powered developer CLI tool for intelligent code assistance.

[![PyPI version](https://badge.fury.io/py/lumecode.svg)](https://badge.fury.io/py/lumecode)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

## Overview

Lumecode is a free, open-source CLI tool that provides AI-powered code assistance directly in your terminal. It supports documentation generation, test creation, code review, refactoring, and natural language queries.

## Features

- Documentation generation and management
- Automated test creation
- AI-powered code reviews
- Code refactoring suggestions
- Natural language Q&A
- Multiple AI model support (Groq, OpenRouter)
- Batch file processing
- Response caching for faster operations

## Installation

**From PyPI:**

```bash
pip install lumecode
```

**From source:**

```bash
git clone https://github.com/anonymus-netizien/lumecode.git
cd lumecode
pip install -e .
```

## Configuration

Set up your API key for AI providers:

```bash
# For Groq (recommended, free)
export GROQ_API_KEY="your-api-key"

# For OpenRouter (optional)
export OPENROUTER_API_KEY="your-api-key"
```

## Quick Start

```bash
# Get help
lumecode --help

# Generate documentation
lumecode docs generate src/main.py

# Generate tests
lumecode test generate src/calculator.py

# Review code
lumecode review file src/api.py

# Ask questions about your code
lumecode ask query "How does authentication work?"

# Generate commit messages
lumecode commit generate

# Refactor code
lumecode refactor suggest src/legacy.py
```

## Available Commands

- `docs` - Generate and manage documentation
- `test` - Generate and improve tests
- `review` - Get AI-powered code reviews
- `ask` - Ask questions about your codebase
- `commit` - Generate smart commit messages
- `explain` - Explain code and concepts
- `refactor` - Get refactoring suggestions
- `cache` - Manage response cache

## Requirements

- Python 3.10 or higher
- API key from Groq or OpenRouter

## License

MIT License. See LICENSE file for details.

## Contributing

Contributions are welcome! Feel free to submit issues and pull requests.
