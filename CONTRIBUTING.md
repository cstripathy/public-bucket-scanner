# Contributing to Bucket Scanner

Thank you for your interest in contributing to Bucket Scanner! This document provides guidelines and instructions for contributing to the project.

## 🚀 Getting Started

### Prerequisites

- Docker & Docker Compose v2.x+
- Python 3.11+ (for local development)
- Git

### Development Setup

1. **Fork and Clone**
   ```bash
   git clone https://github.com/yourusername/bucket-scanner.git
   cd bucket-scanner
   ```

2. **Environment Configuration**
   ```bash
   cp .env.example .env
   # Edit .env with your local configuration
   ```

3. **Start Development Environment**
   ```bash
   docker compose up -d --build
   ```

4. **Verify Installation**
   ```bash
   curl http://localhost:8000/health
   ```

## 📝 Development Guidelines

### Code Style

- **Python**: Follow PEP 8 guidelines
- **Type Hints**: Use type annotations for all functions
- **Docstrings**: Use Google-style docstrings
- **Async**: Prefer async/await for I/O operations
- **Logging**: Use structlog for structured logging

### Project Structure

```
src/
├── scanner/       # Cloud provider scanners
├── workers/       # Background workers
├── enumeration/   # Bucket name generation
├── queue/         # Redis queue system
├── api/           # FastAPI REST API
├── database/      # SQLAlchemy models
└── utils/         # Shared utilities
```

### Adding a New Cloud Provider

1. Create scanner class in `src/scanner/`
2. Inherit from `BaseScanner`
3. Implement required methods:
   - `check_bucket_exists()`
   - `check_public_access()`
   - `list_bucket_contents()`
   - `get_bucket_permissions()`
4. Add tests
5. Update documentation

### Testing

```bash
# Unit tests (local imports)
python3 test_poc.py

# Integration tests (requires running containers)
./test_workflow.sh

# Enumeration tests
./test_enumeration.sh
```

### Adding Wordlists

1. Create wordlist file in `wordlists/`
2. One pattern per line
3. Comments start with `#`
4. Use descriptive filename (e.g., `finance-sector.txt`)
5. Update documentation

## 🔧 Making Changes

### Branch Naming

- `feature/` - New features
- `fix/` - Bug fixes
- `docs/` - Documentation updates
- `refactor/` - Code refactoring
- `test/` - Test additions/updates

### Commit Messages

Follow conventional commits:

```
feat: add support for Oracle Cloud bucket scanning
fix: resolve rate limit issue in AWS scanner
docs: update enumeration API examples
test: add integration tests for GCP scanner
refactor: optimize queue consumer performance
```

### Pull Request Process

1. **Create Feature Branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make Changes**
   - Write code
   - Add tests
   - Update documentation

3. **Test Locally**
   ```bash
   docker compose up -d --build
   ./test_workflow.sh
   ```

4. **Commit Changes**
   ```bash
   git add .
   git commit -m "feat: your descriptive message"
   ```

5. **Push and Create PR**
   ```bash
   git push origin feature/your-feature-name
   ```

6. **PR Requirements**
   - Clear description of changes
   - Tests passing
   - Documentation updated
   - No merge conflicts

## 🐛 Reporting Bugs

### Before Reporting

1. Check existing issues
2. Verify it's reproducible
3. Test with latest version

### Bug Report Template

```markdown
**Description**: Clear description of the bug

**Steps to Reproduce**:
1. Start services with `docker compose up`
2. Execute command: `curl ...`
3. Observe error

**Expected Behavior**: What should happen

**Actual Behavior**: What actually happens

**Environment**:
- OS: Ubuntu 22.04
- Docker version: 24.0.x
- Python version: 3.11.x

**Logs**: Paste relevant logs
```

## 💡 Feature Requests

We welcome feature requests! Please provide:

1. **Use Case**: Why is this feature needed?
2. **Proposed Solution**: How should it work?
3. **Alternatives**: Other approaches considered?
4. **Additional Context**: Screenshots, examples, etc.

## 📚 Documentation

- Update README.md for user-facing changes
- Update docs/ for technical documentation
- Add API examples for new endpoints
- Update QUICKSTART.md if setup process changes

## 🔒 Security

- **Never commit credentials** (use .env.example)
- Report security vulnerabilities privately
- Follow OWASP guidelines for web security
- Use parameterized queries for database operations

## ✅ Code Review Checklist

Before submitting a PR, ensure:

- [ ] Code follows project style guidelines
- [ ] All tests pass locally
- [ ] New features have tests
- [ ] Documentation is updated
- [ ] Commit messages are clear
- [ ] No commented-out code
- [ ] No hardcoded credentials
- [ ] Error handling is proper
- [ ] Logging is appropriate
- [ ] Performance is considered

## 🎯 Priority Areas

Current priority areas for contribution:

1. **Additional Cloud Providers**: Oracle, Alibaba Cloud, IBM Cloud
2. **Advanced Enumeration**: Machine learning-based name generation
3. **Notification Channels**: Email, Discord, PagerDuty
4. **UI Dashboard**: Web-based monitoring interface
5. **Performance**: Optimization for large-scale scanning
6. **Testing**: Increase test coverage

## 📞 Getting Help

- **Documentation**: Check docs/ folder
- **Issues**: Search existing GitHub issues
- **Discussions**: Use GitHub Discussions for questions

## 📜 License

By contributing, you agree that your contributions will be licensed under the MIT License.

## 🙏 Thank You

Thank you for contributing to making cloud storage more secure!
