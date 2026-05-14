# Contributing to MEDIPREDICT

First off, thank you for considering contributing to MEDIPREDICT! It's people like you that make MEDIPREDICT such a great tool.

## 🎯 Code of Conduct

This project and everyone participating in it is governed by our [Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code.

## 📖 How Can I Contribute?

### 🐛 Reporting Bugs
Before creating bug reports, please check the existing issues to avoid duplicates.

**How to Submit a Good Bug Report:**
1. **Use a clear and descriptive title**
2. **Describe the exact steps to reproduce the problem**
3. **Provide specific examples** (code snippets, screenshots)
4. **Describe the expected behavior**
5. **Include environment details** (OS, Python version, Django version)
6. **Include error messages** (if any)

### 💡 Suggesting Enhancements
Enhancement suggestions are tracked as GitHub issues.

**How to Submit a Good Enhancement Suggestion:**
1. **Use a clear and descriptive title**
2. **Provide a step-by-step description** of the suggested enhancement
3. **Explain why this enhancement would be useful**
4. **List any similar features** in other projects
5. **Specify which version** you're using

### 🔧 Pull Requests
1. **Fork the repository**
2. **Create a new branch** (`git checkout -b feature/amazing-feature`)
3. **Make your changes**
4. **Run tests** to ensure quality
5. **Commit your changes** (`git commit -m 'Add some amazing feature'`)
6. **Push to the branch** (`git push origin feature/amazing-feature`)
7. **Open a Pull Request**

## 🏗️ Development Setup

### Prerequisites
- Python 3.11+
- PostgreSQL 14+
- Redis 7+
- Git

### Setup Steps
```bash
# 1. Fork and clone the repository
git clone https://github.com/YOUR_USERNAME/medipredict.git
cd medipredict

# 2. Set up virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# 4. Set up environment variables
cp .env.example .env
# Edit .env with your configuration

# 5. Set up database
python manage.py migrate
python manage.py createsuperuser

# 6. Train ML models
python train_real_models.py

# 7. Run the development server
python manage.py runserver