# Contributing to CCXT Multi-Exchange Copy Trading System

Thank you for your interest in contributing to the CCXT Multi-Exchange Copy Trading System! 🎉

We welcome contributions from everyone. This document provides guidelines and information for contributors.

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [How to Contribute](#how-to-contribute)
- [Development Guidelines](#development-guidelines)
- [Testing](#testing)
- [Submitting Changes](#submitting-changes)

## 🤝 Code of Conduct

This project adheres to a code of conduct to ensure a welcoming environment for all contributors. By participating, you agree to:

- Be respectful and inclusive
- Focus on constructive feedback
- Accept responsibility for mistakes
- Show empathy towards other contributors
- Help create a positive community

## 🚀 Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/your-username/ccxt-multi-exchange-copy-trader.git
   cd ccxt-multi-exchange-copy-trader
   ```
3. **Create a branch** for your changes:
   ```bash
   git checkout -b feature/your-feature-name
   ```

## 🛠️ Development Setup

### Prerequisites

- Python 3.8+
- pip
- virtualenv (recommended)

### Installation

1. **Create a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   ```

3. **Install pre-commit hooks:**
   ```bash
   pre-commit install
   ```

### Project Structure

```
ccxt-multi-exchange-copy-trader/
├── exchange/              # Main package
│   ├── core/             # Core functionality
│   ├── adapters/         # Exchange adapters
│   ├── interfaces/       # Abstract interfaces
│   ├── models/           # Data models
│   ├── services/         # Business logic
│   └── utils/            # Utilities
├── config/               # Configuration files
├── examples/             # Usage examples
├── tests/                # Test suite
└── docs/                 # Documentation
```

## 🤝 How to Contribute

### Types of Contributions

- 🐛 **Bug fixes** - Fix existing issues
- 🚀 **Features** - Add new functionality
- 📚 **Documentation** - Improve docs or examples
- 🧪 **Tests** - Add or improve tests
- 🔧 **Maintenance** - Code refactoring, dependency updates

### Finding Issues

- Check the [Issues](https://github.com/yigoza/ccxt-multi-exchange-copy-trader/issues) page
- Look for issues labeled `good first issue` or `help wanted`
- Comment on issues you'd like to work on

### Development Workflow

1. **Choose an issue** or create a new one
2. **Create a branch** from `main`:
   ```bash
   git checkout -b feature/issue-number-description
   ```
3. **Make your changes**
4. **Write tests** for new functionality
5. **Run the test suite**:
   ```bash
   pytest
   ```
6. **Check code quality**:
   ```bash
   flake8 exchange/
   black exchange/
   mypy exchange/
   ```
7. **Commit your changes**:
   ```bash
   git add .
   git commit -m "feat: add your feature description"
   ```
8. **Push to your fork**:
   ```bash
   git push origin feature/issue-number-description
   ```
9. **Create a Pull Request**

## 📏 Development Guidelines

### Code Style

- Follow [PEP 8](https://pep8.org/) style guidelines
- Use [Black](https://black.readthedocs.io/) for code formatting
- Use [isort](https://isort.readthedocs.io/) for import sorting
- Add type hints for all function parameters and return values

### Commit Messages

Use conventional commit format:

```
type(scope): description

[optional body]

[optional footer]
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `style`: Code style changes
- `refactor`: Code refactoring
- `test`: Test additions
- `chore`: Maintenance

Examples:
```
feat: add Binance futures support
fix: resolve memory leak in replication service
docs: update API documentation
```

### Naming Conventions

- **Classes**: PascalCase
- **Functions/Methods**: snake_case
- **Constants**: UPPER_CASE
- **Modules**: snake_case
- **Packages**: snake_case

### Documentation

- Add docstrings to all public functions, classes, and methods
- Use Google-style docstrings
- Keep comments up-to-date with code changes
- Update README and docs for significant changes

## 🧪 Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=exchange --cov-report=html

# Run specific test file
pytest tests/test_replication.py

# Run tests in verbose mode
pytest -v
```

### Writing Tests

- Write tests for all new functionality
- Use descriptive test names
- Test both success and failure scenarios
- Mock external dependencies (API calls, network requests)
- Aim for >80% code coverage

### Test Structure

```
tests/
├── __init__.py
├── conftest.py          # Pytest fixtures and configuration
├── test_exchange_manager.py
├── test_replication_service.py
├── test_adapters/
│   └── test_binance_adapter.py
└── fixtures/            # Test data and mocks
```

## 📝 Submitting Changes

### Pull Request Process

1. **Ensure your PR meets these requirements:**
   - ✅ Tests pass
   - ✅ Code style checks pass
   - ✅ Type checking passes
   - ✅ Documentation updated
   - ✅ No breaking changes without discussion

2. **PR Title Format:**
   ```
   feat: add multi-exchange support (#123)
   fix: resolve connection timeout issue (#456)
   ```

3. **PR Description:**
   - Describe what changes were made
   - Reference related issues
   - Include screenshots for UI changes
   - List any breaking changes

4. **Review Process:**
   - Maintainers will review your PR
   - Address any feedback or requested changes
   - Once approved, your PR will be merged

### Checklist for PR Submission

- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] Code style checks pass
- [ ] Type checking passes
- [ ] No linting errors
- [ ] Commit messages follow conventional format
- [ ] PR description is clear and comprehensive

## 🎯 Areas for Contribution

### High Priority
- [ ] Add support for Bybit exchange
- [ ] Implement position synchronization
- [ ] Add comprehensive error handling
- [ ] Create web dashboard

### Medium Priority
- [ ] Add KuCoin adapter
- [ ] Implement backtesting framework
- [ ] Add notification system (Telegram, Email)
- [ ] Performance optimizations

### Low Priority
- [ ] Add OKX adapter
- [ ] Implement paper trading mode
- [ ] Add advanced risk management
- [ ] Create mobile app

## 📞 Getting Help

- **Issues**: [GitHub Issues](https://github.com/yigoza/ccxt-multi-exchange-copy-trader/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yigoza/ccxt-multi-exchange-copy-trader/discussions)
- **Documentation**: [Project Wiki](https://github.com/yigoza/ccxt-multi-exchange-copy-trader/wiki)

## 🙏 Recognition

Contributors will be recognized:
- In the CHANGELOG.md file
- In GitHub release notes
- In the project's contributor list

Thank you for contributing to the CCXT Multi-Exchange Copy Trading System! 🚀
