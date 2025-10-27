# PyPI Publishing Setup Guide for InSARLite

## Overview
This guide explains how to set up automated PyPI publishing for InSARLite using GitHub Actions and trusted publishing.

## Prerequisites

### 1. PyPI Account Setup
1. Create an account at [PyPI.org](https://pypi.org/)
2. Enable 2FA for your account (required for trusted publishing)
3. Reserve the project name by manually uploading the first version (optional but recommended)

### 2. GitHub Repository Setup
1. Ensure your repository is public or you have GitHub Pro
2. Set up the following repository secrets and environments

## Trusted Publishing Setup (Recommended)

### 1. Configure PyPI Trusted Publisher
1. Go to [PyPI.org](https://pypi.org/) and log in
2. Navigate to "Your Account" → "Publishing" → "Add a new pending publisher"
3. Fill in the details:
   - **PyPI Project Name**: `insarlite`
   - **Owner**: `mbadarmunir` 
   - **Repository name**: `InSARLite`
   - **Workflow filename**: `python-publish.yml`
   - **Environment name**: `pypi`

### 2. GitHub Environment Setup
1. Go to your GitHub repository
2. Navigate to Settings → Environments
3. Create a new environment named `pypi`
4. Add the following protection rules:
   - **Required reviewers**: Add yourself as a reviewer
   - **Deployment branches**: Only protected branches
   - **Wait timer**: 0 minutes (optional)

## Alternative: Manual Token Setup

If you prefer using API tokens instead of trusted publishing:

### 1. Generate PyPI API Token
1. Go to PyPI.org → Account settings → API tokens
2. Create a new token with scope limited to `insarlite` project
3. Copy the token (starts with `pypi-`)

### 2. Add GitHub Secret
1. Go to GitHub repository → Settings → Secrets and variables → Actions
2. Create a new repository secret:
   - **Name**: `PYPI_API_TOKEN`
   - **Value**: Your PyPI token

### 3. Update Workflow
If using tokens, modify the publish step in `.github/workflows/python-publish.yml`:
```yaml
- name: Publish release distributions to PyPI
  uses: pypa/gh-action-pypi-publish@release/v1
  with:
    password: ${{ secrets.PYPI_API_TOKEN }}
```

## Release Process

### 1. Version Management
Update version in these files before creating a release:
- `pyproject.toml` → `version = "x.y.z"`
- `docs/source/conf.py` → `release = 'x.y.z'` and `version = 'x.y.z'`
- `src/insarlite/__init__.py` → `__version__ = "x.y.z"`

### 2. Create GitHub Release
1. Go to GitHub repository → Releases
2. Click "Create a new release"
3. Create a new tag: `v1.0.0` (or appropriate version)
4. Fill in release title and description
5. Click "Publish release"

### 3. Automated Publishing
The GitHub Action will automatically:
1. Run tests across Python 3.8-3.12
2. Build distribution packages (wheel and sdist)
3. Validate the packages
4. Publish to PyPI (if all tests pass)

## Manual Publishing (Fallback)

If automated publishing fails, you can publish manually:

```bash
# Install build tools
pip install build twine

# Build packages
python -m build

# Check packages
twine check dist/*

# Upload to PyPI
twine upload dist/*
```

## Verification

After publishing, verify the package:

1. Check PyPI page: https://pypi.org/project/insarlite/
2. Test installation: `pip install insarlite`
3. Verify documentation link works
4. Check that all metadata is correct

## Troubleshooting

### Common Issues

1. **"Project name already exists"**: The name is taken, choose a different name
2. **"Invalid credentials"**: Check your API token or trusted publishing setup
3. **"File already exists"**: You're trying to upload the same version twice
4. **"Environment protection rules"**: Ensure you have reviewer approval if required

### Debug Steps

1. Check GitHub Actions logs for detailed error messages
2. Validate your `pyproject.toml` syntax
3. Test builds locally before pushing
4. Ensure all required files are included in the package

## Security Best Practices

1. Use trusted publishing instead of long-lived tokens when possible
2. Enable 2FA on both GitHub and PyPI accounts
3. Use environment protection rules for production releases
4. Regularly rotate API tokens if using them
5. Monitor package downloads and verify authenticity