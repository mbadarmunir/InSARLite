# InSARLite v1.3.1 Release Notes

**Release Date**: January 12, 2026  
**Type**: Patch Release  
**Previous Version**: v1.3.0

---

## 🎯 Overview

InSARLite v1.3.1 is a focused patch release addressing critical bugs in interferogram generation, configuration management, and project structure validation. This release improves workflow reliability and prevents potential data corruption scenarios.

---

## 🐛 Bug Fixes

### Output Folder Validation
**Issue**: Users could accidentally set output folder inside data folder (or vice versa), leading to potential data corruption or circular dependencies during processing.

**Fix**: Added comprehensive path validation in two places:
- `show_confirm_btn_if_ready()`: Validates when user types/selects folders, prevents Confirm Configuration button from appearing if conflict detected
- `_on_confirm_configuration()`: Double-checks before creating project structure as safety measure

**Validation Logic**:
- Uses `os.path.relpath()` to check if one path is within another at any depth
- Blocks if output folder is same as data folder
- Blocks if output folder is nested anywhere within data folder
- Allows data folder to be inside output folder (valid use case)
- Handles Windows cross-drive scenarios gracefully
- Shows clear error message indicating which folder is problematic

**User Impact**: Prevents accidental data loss or corruption from misconfigured folder paths.

---

### Baseline Constraints Not Saved to Configuration
**Issue**: Changes to perpendicular and temporal baseline constraints weren't persisted to `.config.json`, causing `intf.in` files to not regenerate when constraints changed, even though the network visualization updated correctly.

**Fix**: Enhanced configuration management in `base2net.py`:
- Added `perpendicular_baseline_constraint` and `temporal_baseline_constraint` to config save logic in `_save_config()`
- Modified `_on_export_edges()` to check baseline constraints alongside master/alignment/ESD settings before skipping regeneration
- Now properly detects when user changes baseline thresholds and regenerates interferogram pairs accordingly

**Technical Details**:
```python
# Previously only checked: mst, align_mode, esd_mode
# Now also checks: perpendicular_baseline_constraint, temporal_baseline_constraint

if (self.mst == prev_mst and 
    self.align_mode_var.get() == prev_align and 
    self.esd_mode_var.get() == prev_esd and
    current_perp == prev_perp and       # NEW
    current_temp == prev_temp):         # NEW
    # Skip regeneration
```

**User Impact**: Baseline constraint changes now properly trigger interferogram pair regeneration.

---

### Subswath-Specific Interferogram Generation
**Issue**: When generating interferometric pairs for multiple subswaths (F1, F2, F3), all `intf.in` files contained identical F1 references instead of properly substituting F2 and F3.

**Root Cause**: String replacement logic `line.replace(f'F{key[-1]}', f'F{other_key[-1]}')` was too broad, matching unintended substrings (e.g., "F11" → "F21" instead of just updating F1→F2 in proper context).

**Fix**: Implemented targeted replacement in two locations:

**1. pair_generation.py** (lines 149-160):
```python
# Generate for primary subswath, copy to others with proper replacement
for other_key in ["pF1", "pF2", "pF3"]:
    if other_key != primary_key:
        shutil.copy(ind, other_ind)
        with open(other_ind, 'r') as f:
            lines = f.readlines()
        with open(other_ind, 'w') as f:
            for line in lines:
                # Replace _ALL_F1 with _ALL_F2, etc. (more specific pattern)
                modified_line = line.replace(f'_ALL_F{primary_key[-1]}', 
                                            f'_ALL_F{other_key[-1]}')
                f.write(modified_line)
```

**2. base2net.py** (lines 1527-1542):
```python
# Copy and modify intf.in with correct subswath references
target_subswath = os.path.basename(dir_path)[-1]
shutil.copy2(intf_path, subswath_intf)

with open(subswath_intf, 'r') as f:
    lines = f.readlines()
with open(subswath_intf, 'w') as f:
    for line in lines:
        # Replace _ALL_F1 with _ALL_F2, etc.
        modified_line = line.replace(f'_ALL_F{primary_subswath}', 
                                     f'_ALL_F{target_subswath}')
        f.write(modified_line)
```

**User Impact**: Each subswath now correctly references its own files (F1→F1, F2→F2, F3→F3) in interferometric pair lists.

---

### Alignment Workflow Improvements
**Issue**: Complex partial alignment logic could cause unexpected behavior and was difficult to maintain.

**Fix**: Simplified alignment workflow in `alignment.py`:
- Commented out partial alignment function (`_perform_partial_alignment`)
- Now always offers full alignment with optional backup when:
  - Alignment method changes (ESD ↔ no_ESD)
  - Partial alignment detected
- Enhanced backup popup with reason parameter (`method_change` vs `partial_alignment`)
- Restored method change detection logic (`check_alignment_method_change`)

**Backup Workflow**:
```python
def _backup_alignment_files_with_permission(praw, key, reason="partial_alignment"):
    """
    Offers user choice to backup existing alignment files before re-alignment.
    - Never deletes original files
    - Creates timestamped backup directory if user accepts
    - Clear messaging about what will happen to existing files
    """
```

**User Impact**: More predictable alignment behavior with clear user prompts and data protection.

---

## 📋 Files Modified

### Core Processing Files
- **src/insarlite/main.py**: Added output folder validation in `show_confirm_btn_if_ready()` and `_on_confirm_configuration()`
- **src/insarlite/gmtsar_gui/base2net.py**: Enhanced config save/check to include baseline constraints
- **src/insarlite/gmtsar_gui/pair_generation.py**: Fixed subswath-specific string replacement in `gen_pairs()`
- **src/insarlite/gmtsar_gui/alignment.py**: Simplified alignment workflow, commented out partial alignment

### Version Updates
- **pyproject.toml**: Version 1.3.0 → 1.3.1
- **src/insarlite/__init__.py**: `__version__ = "1.3.1"`
- **README.md**: Updated version badge and release announcement

---

## 🔄 Migration Guide

### From v1.3.0 to v1.3.1

**No breaking changes** - this is a drop-in replacement.

**Installation**:
```bash
pip install --upgrade insarlite
```

**Existing Projects**: 
- Projects created with v1.3.0 are fully compatible
- Configuration files (`.config.json`) will automatically be enhanced with baseline constraints on next export
- No manual migration required

**Recommendations**:
- If you experienced issues with baseline constraint changes not taking effect, regenerate your interferometric pairs after upgrading
- Review output folder paths to ensure they're not within data folders

---

## 📝 Known Issues

None identified in this release.

---

## 🙏 Acknowledgments

- **Bug Reports**: Thanks to users who identified the subswath generation and baseline constraint persistence issues
- **GMTSAR Team**: For the robust InSAR processing engine that powers InSARLite

---

## 📧 Support

- **Documentation**: [insarlite.readthedocs.io](https://insarlite.readthedocs.io/)
- **Issues**: [GitHub Issues](https://github.com/mbadarmunir/InSARLite/issues)
- **Email**: mbadarmunir@gmail.com

---

## 🔗 Links

- **PyPI**: https://pypi.org/project/insarlite/
- **GitHub**: https://github.com/mbadarmunir/InSARLite
- **Documentation**: https://insarlite.readthedocs.io/

---

**Full Changelog**: [v1.3.0...v1.3.1](https://github.com/mbadarmunir/InSARLite/compare/v1.3.0...v1.3.1)
