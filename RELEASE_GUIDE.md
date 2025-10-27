# InSARLite v1.0.0 Release Guide

## ✅ **Release Readiness Checklist**

### **Package Configuration**
- ✅ **pyproject.toml**: Modern PEP 621 format, clean license specification
- ✅ **Version**: Set to 1.0.0 in both pyproject.toml and __init__.py
- ✅ **Dependencies**: All required packages specified with version constraints
- ✅ **Entry Points**: `InSARLiteApp` command configured correctly
- ✅ **Build System**: setuptools with proper package discovery
- ✅ **Package Structure**: Clean src-layout with proper module organization

### **Documentation**
- ✅ **README.md**: Comprehensive with badges, installation, usage
- ✅ **ReadTheDocs Config**: `.readthedocs.yaml` properly configured
- ✅ **Sphinx Documentation**: Complete conf.py with all extensions
- ✅ **Documentation Requirements**: `docs/requirements.txt` ready
- ✅ **License**: MIT license included

### **GitHub Integration**
- ✅ **GitHub Actions**: Automated PyPI publishing workflow configured
- ✅ **Trusted Publishing**: Using OIDC for secure PyPI deployment
- ✅ **Multi-Python Testing**: Tests for Python 3.8-3.12

### **Code Quality**
- ✅ **GMTSAR Integration**: Fully functional with gfortran-9 support
- ✅ **Module Execution**: Fixed RuntimeWarning for `python -m insarlite`
- ✅ **Import Structure**: Clean module imports without circular dependencies
- ✅ **Package Build**: Builds successfully with no critical warnings

---

## 🚀 **Publishing Steps**

### **Step 1: ReadTheDocs Setup**

1. **Go to [ReadTheDocs.org](https://readthedocs.org/)**
2. **Sign in with your GitHub account**
3. **Import your project:**
   - Click "Import a Project"
   - Select "InSARLite" from your GitHub repositories
   - Repository URL: `https://github.com/mbadarmunir/InSARLite`

4. **Configure Project Settings:**
   - **Name**: `insarlite`
   - **Language**: `English`
   - **Programming Language**: `Python`
   - **Repository URL**: `https://github.com/mbadarmunir/InSARLite`
   - **Default Branch**: `main`

5. **Build Settings:**
   - ReadTheDocs will automatically detect your `.readthedocs.yaml`
   - The build should use Python 3.12 and install docs requirements
   - Your documentation will be available at: `https://insarlite.readthedocs.io/`

6. **Webhook Setup:**
   - ReadTheDocs should automatically create a webhook
   - If not, add manually: Settings → Webhooks → Add webhook
   - Payload URL: `https://readthedocs.org/api/v2/webhook/insarlite/{your-id}/`

### **Step 2: GitHub Repository Preparation**

1. **Create PyPI Environment in GitHub:**
   ```bash
   # Go to your GitHub repository
   # Settings → Environments → New environment
   # Name: "pypi"
   # Add protection rules as needed
   ```

2. **Set up Trusted Publishing (Recommended):**
   - Go to [PyPI Trusted Publishing](https://pypi.org/manage/account/publishing/)
   - Add a new publisher:
     - **Owner**: `mbadarmunir`
     - **Repository**: `InSARLite`
     - **Workflow**: `python-publish.yml`
     - **Environment**: `pypi`

3. **Commit and Push All Changes:**
   ```bash
   git add .
   git commit -m "Release v1.0.0: Production-ready InSARLite"
   git push origin main
   ```

### **Step 3: Create GitHub Release**

1. **Go to GitHub Releases:**
   - Navigate to: `https://github.com/mbadarmunir/InSARLite/releases`
   - Click "Create a new release"

2. **Release Configuration:**
   - **Tag version**: `v1.0.0`
   - **Release title**: `InSARLite v1.0.0 - Production Release`
   - **Description**:
   ```markdown
   # InSARLite v1.0.0 - Production Release 🚀

   ## 🌟 Major Features
   - Complete GMTSAR-based InSAR processing workflow
   - Automated Sentinel-1 data download and management
   - Interactive baseline network design
   - Advanced time series analysis (SBAS)
   - Professional visualization tools

   ## 🔧 Technical Improvements
   - Enhanced GMTSAR installer with gfortran-9 support
   - Fixed module execution warnings
   - Comprehensive documentation
   - Multi-platform compatibility

   ## 📦 Installation
   ```bash
   pip install insarlite
   InSARLiteApp
   ```

   ## 📖 Documentation
   Full documentation available at: https://insarlite.readthedocs.io/

   ## 🙏 Acknowledgments
   Special thanks to the GMTSAR team and the open-source community.
   ```

3. **Publish Release:**
   - ✅ Check "Set as the latest release"
   - Click "Publish release"

### **Step 4: Monitor Automated Publishing**

1. **GitHub Actions:**
   - Go to Actions tab in your repository
   - Monitor the "Build and Publish to PyPI" workflow
   - Should automatically trigger on release publication

2. **PyPI Publishing:**
   - The workflow will automatically:
     - Run tests on multiple Python versions
     - Build source and wheel distributions
     - Upload to PyPI using trusted publishing

3. **Verify Publication:**
   - Check [PyPI InSARLite page](https://pypi.org/project/insarlite/)
   - Verify version 1.0.0 is published
   - Test installation: `pip install insarlite==1.0.0`

---

## 🔧 **Manual PyPI Publishing (Backup Method)**

If automated publishing fails, use manual approach:

```bash
# Install publishing tools
pip install twine

# Build packages
python -m build --sdist --wheel

# Check packages
python -m twine check dist/*

# Upload to PyPI (you'll need API token)
python -m twine upload dist/*
```

### **PyPI API Token Setup:**
1. Go to [PyPI Account Settings](https://pypi.org/manage/account/token/)
2. Create new API token for InSARLite project
3. Use as password with username `__token__`

---

## 📊 **Post-Release Verification**

### **Test Installation:**
```bash
# Create fresh environment
python -m venv test_env
source test_env/bin/activate  # Linux/Mac
# test_env\Scripts\activate  # Windows

# Install from PyPI
pip install insarlite

# Test execution
InSARLiteApp
python -m insarlite
```

### **Documentation Check:**
- Verify ReadTheDocs builds successfully
- Check all pages render correctly
- Ensure API documentation is generated

### **GitHub Integration:**
- Verify release is marked as "Latest"
- Check download statistics
- Monitor for issues or bug reports

---

## 🎯 **Success Criteria**

- ✅ **PyPI**: Package installable via `pip install insarlite`
- ✅ **ReadTheDocs**: Documentation live at `insarlite.readthedocs.io`
- ✅ **GitHub**: Release tagged and published
- ✅ **Functionality**: Application launches and GMTSAR integration works
- ✅ **Command Line**: Both `InSARLiteApp` and `python -m insarlite` work

---

## 🚨 **Troubleshooting**

### **PyPI Upload Issues:**
- Ensure PyPI trusted publishing is configured correctly
- Check GitHub Actions logs for detailed error messages
- Verify package name isn't already taken

### **ReadTheDocs Build Failures:**
- Check build logs in ReadTheDocs admin panel
- Ensure all documentation dependencies are in `docs/requirements.txt`
- Verify `.readthedocs.yaml` configuration

### **Import/Module Issues:**
- Test in clean environment to catch missing dependencies
- Check entry points configuration in pyproject.toml
- Verify all required files are included in package

---

## 📈 **Next Steps After Release**

1. **Announce Release:**
   - Update project README badges
   - Share on relevant forums/communities
   - Create social media announcements

2. **Monitor Usage:**
   - Track PyPI download statistics
   - Monitor GitHub issues and discussions
   - Collect user feedback

3. **Plan Updates:**
   - Set up issue templates
   - Plan minor releases for bug fixes
   - Consider feature requests for future versions

**InSARLite v1.0.0 is ready for production release!** 🎉