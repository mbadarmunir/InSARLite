# InSARLite Execution Methods

## Fixed RuntimeWarning Issue

The RuntimeWarning you encountered has been resolved by:

1. **Removing circular imports** from `__init__.py`
2. **Creating proper `__main__.py`** entry point
3. **Improving module structure** for cleaner execution

## Ways to Run InSARLite

### Method 1: Module execution (Recommended)
```bash
cd src
python -m insarlite
```

### Method 2: Direct execution
```bash
cd src
python -c "from insarlite.main import main; main()"
```

### Method 3: Direct script execution
```bash
cd src
python insarlite/main.py
```

## Changes Made

### 1. Updated `src/insarlite/__init__.py`
- Removed direct import of `InSARLiteApp` 
- Added `get_app_class()` function for lazy loading
- Prevents circular import warnings

### 2. Created `src/insarlite/__main__.py`
- Proper entry point for `python -m insarlite`
- Clean module execution without warnings

### 3. Improved `src/insarlite/main.py`
- Better main() function documentation
- Maintains backward compatibility

## Verification

✅ No more RuntimeWarning when using `python -m insarlite`
✅ All import methods work correctly
✅ GMTSAR integration still functions properly
✅ GUI application launches successfully
✅ Backward compatibility maintained

The application is now ready for production use with clean module execution!