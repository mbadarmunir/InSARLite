# ReadTheDocs Setup Guide for InSARLite

## Overview
InSARLite uses ReadTheDocs for hosting documentation, which automatically builds and publishes documentation from the GitHub repository.

## Setup Steps

### 1. ReadTheDocs Account Setup
1. Go to [ReadTheDocs.org](https://readthedocs.org/)
2. Sign up/login with your GitHub account
3. Import the InSARLite project from GitHub

### 2. Project Configuration
1. In ReadTheDocs dashboard, go to your project settings
2. Set the following configuration:
   - **Programming Language**: Python
   - **Repository URL**: `https://github.com/mbadarmunir/InSARLite`
   - **Default Branch**: `main`
   - **Documentation Type**: Sphinx Html
   - **Requirements File**: `docs/requirements.txt`
   - **Python Configuration File**: `.readthedocs.yaml`

### 3. Build Configuration
The project includes a `.readthedocs.yaml` file that configures:
- Python 3.12 environment
- Sphinx documentation builder
- PDF and ePub formats
- Automatic dependency installation

### 4. Custom Domain (Optional)
You can set up a custom domain like `docs.insarlite.org` by:
1. Adding a CNAME record in your DNS pointing to `insarlite.readthedocs.io`
2. Configuring the custom domain in ReadTheDocs project settings

### 5. PyPI Integration
The documentation URL is already configured in `pyproject.toml`:
```toml
[project.urls]
Documentation = "https://insarlite.readthedocs.io/"
```

This ensures that PyPI users can easily find the documentation.

## Automatic Updates
- Documentation rebuilds automatically on every push to `main` branch
- Pull requests trigger documentation previews
- Multiple format exports (HTML, PDF, ePub) are available

## Webhook Configuration
ReadTheDocs automatically sets up webhooks with GitHub when you import the project, enabling automatic builds on code changes.

## Local Testing
To test documentation builds locally:
```bash
cd docs
pip install -r requirements.txt
make html
```

The built documentation will be in `docs/build/html/index.html`.