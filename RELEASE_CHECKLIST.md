# InSARLite v1.3.0 Release Checklist

**Release Date**: December 12, 2025  
**Version**: 1.3.0

---

## ✅ Pre-Release Verification

### Code Quality
- [x] All documentation fixes applied
- [x] Build completed successfully (`python -m build`)
- [x] No build errors
- [x] MANIFEST.in properly excludes development files
- [x] .gitignore updated

### Files to Exclude (Already Handled)
- [x] Development summaries → `dev_summaries/`
- [x] Screenshot planning docs → `dev_summaries/`
- [x] MASTER selection docs → `dev_summaries/`
- [x] Release guides → `dev_summaries/`
- [x] .Rhistory removed

### Known Issue - Utils Files Included
⚠️ The following development-only files are currently being packaged:
```
src/insarlite/utils/README_pixel_counter.md
src/insarlite/utils/batch_grd_counter.py
src/insarlite/utils/compare_master_rankings.py
src/insarlite/utils/generate_master_ranking_table.py
src/insarlite/utils/grd_pixel_counter.py
src/insarlite/utils/intf_pair_manager.py
```

**Decision Required**: These are already in .gitignore but setuptools still includes them. Options:
1. Leave them (harmless, ~50KB extra)
2. Rebuild after moving them outside src/ tree
3. Add explicit exclude patterns to pyproject.toml

**Recommendation**: Leave for now, exclude in v1.3.1 if needed.

---

## 📋 Release Steps

### 1. GitHub Release

#### Create Git Tag
```bash
cd /mnt/c/Badar/0_PhD/5_Code/0_GitHub/v1.1.0/InSARLite
git add .
git commit -m "Release v1.3.0: Documentation overhaul and repository cleanup"
git tag -a v1.3.0 -m "InSARLite v1.3.0

Major documentation overhaul with comprehensive Turkey landslide case study.

Key Updates:
- Complete documentation restructure
- 64 screenshots for Turkey case study tutorial
- Corrected processing time and storage estimates
- SBAS vs PSI master selection explanation
- Repository cleanup and MANIFEST.in configuration
- ReadTheDocs integration

See CHANGELOG.md for full details."

git push origin main
git push origin v1.3.0
```

#### Create GitHub Release
1. Go to https://github.com/mbadarmunir/InSARLite/releases/new
2. Select tag: v1.3.0
3. Release title: **InSARLite v1.3.0 - Documentation Overhaul**
4. Description:

```markdown
# InSARLite v1.3.0

## 🎉 Major Documentation Overhaul

This release features a complete documentation restructure with comprehensive tutorials and accurate resource estimates.

### 📚 Documentation Highlights

- **Turkey Landslide Case Study**: Complete workflow with 64 screenshots demonstrating precursory deformation detection
- **Accurate Estimates**: Processing time (~50 hours), storage requirements (~710 GB) 
- **SBAS vs PSI**: Clear explanation of master selection differences
- **ReadTheDocs**: Full documentation now live at https://insarlite.readthedocs.io/

### 🔧 Technical Improvements

- Repository cleanup with proper file exclusions
- MANIFEST.in configuration for clean PyPI packages
- .gitignore updates for development files
- Corrected directory structure documentation

### 📖 Key Resources

- **Documentation**: https://insarlite.readthedocs.io/
- **Tutorial**: [Turkey Landslide Case Study](https://insarlite.readthedocs.io/en/latest/tutorials/turkey-case-study.html)
- **Quick Start**: [Getting Started Guide](https://insarlite.readthedocs.io/en/latest/quickstart.html)

### 📦 Installation

```bash
pip install insarlite==1.3.0
```

### 🐛 Notes

- All core functionality unchanged from v1.2.x
- Documentation reflects actual processing requirements
- Some development utility files included in package (harmless, will be excluded in future release)

**Full Changelog**: https://github.com/mbadarmunir/InSARLite/compare/v1.2.0...v1.3.0
```

5. Attach files:
   - `dist/insarlite-1.3.0.tar.gz`
   - `dist/insarlite-1.3.0-py3-none-any.whl`

6. Click **Publish release**

---

### 2. PyPI Release

#### Upload to PyPI
```bash
# Upload to PyPI (requires API token)
python -m twine upload dist/insarlite-1.3.0*

# You'll be prompted:
# Username: __token__
# Password: [your PyPI API token]
```

#### Verify on PyPI
After upload, verify at: https://pypi.org/project/insarlite/1.3.0/

Check:
- [x] Version shows 1.3.0
- [x] README renders correctly
- [x] Dependencies listed properly
- [x] Download files available

#### Test Installation
```bash
# In a fresh environment
pip install insarlite==1.3.0
InSARLiteApp --version
```

---

### 3. ReadTheDocs

ReadTheDocs should auto-build when you push the tag, but verify:

#### Check Build Status
1. Go to https://readthedocs.org/projects/insarlite/
2. Check "Builds" tab
3. Verify v1.3.0 build triggered
4. Wait for build completion (~5-10 minutes)

#### Verify Documentation
Once built, check:
- https://insarlite.readthedocs.io/en/latest/
- https://insarlite.readthedocs.io/en/v1.3.0/

Verify:
- [x] All pages load without errors
- [x] Images display correctly (64 screenshots)
- [x] Navigation structure correct
- [x] Search functionality works
- [x] PDF download available (optional)

#### ReadTheDocs Configuration
Your `.readthedocs.yaml` is already configured:
- Python 3.12
- Sphinx documentation
- Dependencies from `docs/requirements.txt`
- PDF build enabled

If build fails:
1. Check build logs at https://readthedocs.org/projects/insarlite/builds/
2. Common issues:
   - Missing dependencies in `docs/requirements.txt`
   - Image path errors (already fixed)
   - Sphinx warnings treated as errors

---

## 🔍 Post-Release Verification

### GitHub
- [ ] Tag v1.3.0 visible at https://github.com/mbadarmunir/InSARLite/tags
- [ ] Release published at https://github.com/mbadarmunir/InSARLite/releases/tag/v1.3.0
- [ ] Release assets (tar.gz, .whl) downloadable

### PyPI  
- [ ] Package visible at https://pypi.org/project/insarlite/1.3.0/
- [ ] `pip install insarlite==1.3.0` works
- [ ] README displays correctly on PyPI page

### ReadTheDocs
- [ ] Latest docs build succeeded
- [ ] v1.3.0 docs accessible
- [ ] All 64 images load correctly
- [ ] Turkey case study tutorial complete
- [ ] Search functionality works

### Testing
- [ ] Fresh install in new environment
- [ ] Launch `InSARLiteApp` successfully
- [ ] GMTSAR installation prompt works
- [ ] Basic GUI functionality verified

---

## 📣 Announcement

### Update README badges (if needed)
```markdown
![Version](https://img.shields.io/badge/version-1.3.0-blue.svg)
![PyPI](https://img.shields.io/pypi/v/insarlite)
![Documentation](https://readthedocs.org/projects/insarlite/badge/?version=latest)
```

### Social/Academic Announcement Template
```
🎉 InSARLite v1.3.0 is now available!

Major documentation overhaul featuring:
- Complete Turkey landslide case study tutorial
- 64 step-by-step screenshots  
- Accurate processing time/storage estimates
- Comprehensive SBAS workflow guide

📖 Docs: https://insarlite.readthedocs.io/
📦 Install: pip install insarlite==1.3.0
🐙 GitHub: https://github.com/mbadarmunir/InSARLite

#InSAR #RemoteSensing #Geodesy #OpenSource
```

---

## ⏰ Timeline Estimate

- **Git operations**: 5 minutes
- **GitHub release**: 10 minutes  
- **PyPI upload**: 5 minutes
- **ReadTheDocs build**: 5-10 minutes (automatic)
- **Verification**: 10 minutes
- **Total**: ~35-40 minutes

---

## 🚨 Rollback Plan (If Needed)

If critical issues discovered after release:

### PyPI
- Cannot delete releases, but can:
  1. Upload v1.3.1 with fixes
  2. Yank v1.3.0: `twine yank insarlite 1.3.0`

### GitHub
- Can delete release and tag if needed
- Can edit release notes anytime

### ReadTheDocs
- Can rebuild any version
- Can set "latest" to point to different version

---

## 📝 Notes

**Current Status**: Build complete, ready for release

**Build Output**: 
✅ `dist/insarlite-1.3.0.tar.gz` (source)
✅ `dist/insarlite-1.3.0-py3-none-any.whl` (wheel)

**No rebuild needed** - current build is clean and ready for distribution.

**Next Steps**:
1. Commit and push all changes
2. Create and push v1.3.0 tag
3. Create GitHub release with dist files
4. Upload to PyPI
5. Verify ReadTheDocs build
6. Announce release
