# Contributing to InSARLite

Thank you for your interest in contributing to InSARLite! This guide will help you get started with contributing to the project.

## Ways to Contribute

### 🐛 **Bug Reports**
Help us improve InSARLite by reporting bugs:
- Use GitHub Issues with the bug report template
- Include detailed steps to reproduce the issue
- Provide system information and error logs
- Test with the latest version before reporting

### 💡 **Feature Requests** 
Suggest new features or improvements:
- Use GitHub Issues with the feature request template
- Describe the use case and expected behavior
- Consider implementation complexity and scope
- Discuss with the community before large changes

### 📚 **Documentation**
Improve documentation:
- Fix typos and grammatical errors
- Add missing documentation
- Create tutorials and examples
- Translate documentation to other languages

### 💻 **Code Contributions**
Contribute code improvements:
- Bug fixes and stability improvements
- New features and functionality
- Performance optimizations
- Test coverage improvements

### 🧪 **Testing**
Help improve software quality:
- Write and improve unit tests
- Test new features and bug fixes
- Report edge cases and corner bugs
- Validate cross-platform compatibility

### 💬 **Community Support**
Help other users:
- Answer questions in GitHub Discussions
- Help troubleshoot issues
- Share usage examples and tips
- Mentor new contributors

## Getting Started

### Development Environment Setup

1. **Fork the Repository**
   ```bash
   # Fork on GitHub, then clone your fork
   git clone https://github.com/yourusername/InSARLite.git
   cd InSARLite
   ```

2. **Set Up Development Environment**
   ```bash
   # Create virtual environment
   python -m venv venv
   source venv/bin/activate  # Linux/macOS
   # or
   venv\Scripts\activate     # Windows
   
   # Install development dependencies
   pip install -e .[dev]
   ```

3. **Install Development Tools**
   ```bash
   # Install pre-commit hooks
   pre-commit install
   
   # Install testing tools
   pip install pytest pytest-cov black flake8 mypy
   ```

4. **Verify Installation**
   ```bash
   # Run tests to ensure everything works
   python -m pytest tests/
   
   # Start the application
   python -m insarlite.main
   ```

### Development Workflow

1. **Create Feature Branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make Changes**
   - Follow coding standards (see below)
   - Add tests for new functionality
   - Update documentation as needed

3. **Test Your Changes**
   ```bash
   # Run full test suite
   python -m pytest tests/ -v
   
   # Check code style
   black --check src/
   flake8 src/
   
   # Type checking
   mypy src/
   ```

4. **Commit Changes**
   ```bash
   git add .
   git commit -m "feat: add new feature description"
   ```

5. **Push and Create Pull Request**
   ```bash
   git push origin feature/your-feature-name
   ```
   Then create a Pull Request on GitHub.

## Coding Standards

### Python Style Guide

We follow PEP 8 with some specific guidelines:

**Code Formatting**:
```python
# Use Black for automatic formatting
black src/ tests/

# Line length: 88 characters (Black default)
# Use double quotes for strings
# 4 spaces for indentation
```

**Import Organization**:
```python
# Standard library imports
import os
import sys
from pathlib import Path

# Third-party imports
import numpy as np
import matplotlib.pyplot as plt
import tkinter as tk

# Local imports
from .utils import helper_function
from ..gmtsar_gui import processing_module
```

**Naming Conventions**:
```python
# Variables and functions: snake_case
variable_name = "value"
def function_name():
    pass

# Classes: PascalCase
class ClassName:
    pass

# Constants: UPPER_CASE
MAX_RETRIES = 3

# Private members: _leading_underscore
def _private_function():
    pass
```

### Documentation Standards

**Docstring Format** (Google Style):
```python
def process_data(input_path: Path, options: Dict[str, Any]) -> List[str]:
    """
    Process InSAR data from input directory.
    
    This function processes Sentinel-1 data according to the specified
    options and returns a list of output file paths.
    
    Args:
        input_path: Path to directory containing input data files.
        options: Dictionary containing processing options. Must include
            'output_dir' key and optionally 'parallel_workers'.
    
    Returns:
        List of paths to generated output files.
    
    Raises:
        ValueError: If input_path does not exist or is not a directory.
        ProcessingError: If processing fails due to data issues.
    
    Example:
        >>> from pathlib import Path
        >>> result = process_data(Path("data/"), {"output_dir": "results/"})
        >>> print(len(result))
        5
    """
    pass
```

**Type Hints**:
```python
from typing import List, Dict, Optional, Union, Tuple
from pathlib import Path

def analyze_baselines(
    acquisitions: List[Dict[str, str]], 
    max_temporal: int = 48,
    max_perpendicular: Optional[float] = None
) -> Tuple[List[Tuple[str, str]], Dict[str, float]]:
    """Analyze baseline network and return optimal pairs."""
    pass
```

### GUI Development Guidelines

**Tkinter Best Practices**:
```python
class MyDialog(tk.Toplevel):
    """Example dialog following InSARLite patterns."""
    
    def __init__(self, parent: tk.Widget, title: str):
        super().__init__(parent)
        self.title(title)
        self.transient(parent)
        self.grab_set()
        
        self._create_widgets()
        self._bind_events()
        
        # Center on parent
        self.geometry("+%d+%d" % (
            parent.winfo_rootx() + 50,
            parent.winfo_rooty() + 50
        ))
    
    def _create_widgets(self):
        """Create and layout widgets."""
        # Implementation here
        pass
    
    def _bind_events(self):
        """Bind event handlers."""
        # Implementation here
        pass
```

**Threading for GUI**:
```python
import threading
from concurrent.futures import ThreadPoolExecutor

class ProcessingDialog(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.executor = ThreadPoolExecutor(max_workers=1)
    
    def start_processing(self):
        """Start processing in background thread."""
        future = self.executor.submit(self._process_data)
        self._check_processing_complete(future)
    
    def _process_data(self):
        """Background processing function."""
        # Long-running operation
        return result
    
    def _check_processing_complete(self, future):
        """Check if background processing is complete."""
        if future.done():
            try:
                result = future.result()
                self._on_processing_complete(result)
            except Exception as e:
                self._on_processing_error(e)
        else:
            # Check again in 100ms
            self.after(100, lambda: self._check_processing_complete(future))
```

## Testing Guidelines

### Test Organization

```
tests/
├── unit/                   # Unit tests
│   ├── test_utils.py
│   ├── test_config.py
│   └── test_processing.py
├── integration/            # Integration tests
│   ├── test_download.py
│   └── test_workflow.py
├── gui/                    # GUI tests
│   ├── test_main_window.py
│   └── test_dialogs.py
└── fixtures/               # Test data and fixtures
    ├── sample_data/
    └── mock_responses/
```

### Writing Tests

**Unit Test Example**:
```python
import unittest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from insarlite.utils.config_manager import ConfigManager

class TestConfigManager(unittest.TestCase):
    """Test cases for ConfigManager class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config_manager = ConfigManager()
        self.test_config = {
            "data_folder": "/path/to/data",
            "output_folder": "/path/to/output"
        }
    
    def test_load_default_config(self):
        """Test loading default configuration."""
        config = self.config_manager.load_default_config()
        self.assertIsInstance(config, dict)
        self.assertIn("data_folder", config)
    
    @patch('pathlib.Path.exists')
    @patch('json.load')
    def test_load_config_file_exists(self, mock_json_load, mock_exists):
        """Test loading configuration from existing file."""
        mock_exists.return_value = True
        mock_json_load.return_value = self.test_config
        
        with patch('builtins.open', mock_open()):
            config = self.config_manager.load_config()
        
        self.assertEqual(config, self.test_config)
        mock_json_load.assert_called_once()
    
    def test_validate_config_valid(self):
        """Test validation of valid configuration."""
        is_valid = self.config_manager.validate_config(self.test_config)
        self.assertTrue(is_valid)
    
    def test_validate_config_missing_key(self):
        """Test validation fails for missing required key."""
        invalid_config = {"data_folder": "/path/to/data"}
        is_valid = self.config_manager.validate_config(invalid_config)
        self.assertFalse(is_valid)
```

**Integration Test Example**:
```python
import unittest
import tempfile
import shutil
from pathlib import Path

from insarlite.gmtsar_gui.data_dwn import DataDownloader

class TestDataDownloadIntegration(unittest.TestCase):
    """Integration tests for data download functionality."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.downloader = DataDownloader()
    
    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir)
    
    @unittest.skipIf(not has_internet(), "Requires internet connection")
    def test_search_and_download_integration(self):
        """Test complete search and download workflow."""
        # Search for data
        results = self.downloader.search_acquisitions(
            start_date="2023-01-01",
            end_date="2023-01-07",
            aoi_wkt="POLYGON((-118.5 34.0, -118.2 34.0, -118.2 34.2, -118.5 34.2, -118.5 34.0))"
        )
        
        self.assertGreater(len(results), 0)
        
        # Download first result (if available)
        if results:
            download_success = self.downloader.download_acquisition(
                results[0], self.temp_dir
            )
            self.assertTrue(download_success)
```

### Test Data and Fixtures

**Creating Test Fixtures**:
```python
import pytest
from pathlib import Path

@pytest.fixture
def sample_safe_directory():
    """Create a mock Sentinel-1 SAFE directory structure."""
    temp_dir = Path(tempfile.mkdtemp())
    safe_dir = temp_dir / "S1A_IW_SLC__1SDV_20230101T120000_20230101T120027_046123_058456_1234.SAFE"
    safe_dir.mkdir()
    
    # Create mock files
    (safe_dir / "manifest.safe").write_text("mock manifest")
    (safe_dir / "annotation").mkdir()
    (safe_dir / "measurement").mkdir()
    
    yield safe_dir
    
    # Cleanup
    shutil.rmtree(temp_dir)

def test_safe_directory_parsing(sample_safe_directory):
    """Test parsing of SAFE directory structure."""
    from insarlite.utils.utils import parse_safe_directory
    
    metadata = parse_safe_directory(sample_safe_directory)
    assert metadata is not None
    assert "acquisition_date" in metadata
```

## Pull Request Process

### Before Submitting

1. **Run Full Test Suite**
   ```bash
   python -m pytest tests/ -v --cov=src/insarlite
   ```

2. **Check Code Quality**
   ```bash
   # Format code
   black src/ tests/
   
   # Check style
   flake8 src/ tests/
   
   # Type checking
   mypy src/
   ```

3. **Update Documentation**
   - Add docstrings for new functions/classes
   - Update user documentation if needed
   - Add examples for new features

4. **Add Tests**
   - Unit tests for new functions
   - Integration tests for new workflows
   - GUI tests for interface changes

### Pull Request Template

When creating a pull request, please include:

```markdown
## Description
Brief description of changes and motivation.

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Documentation update
- [ ] Performance improvement
- [ ] Code refactoring

## Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing completed
- [ ] New tests added

## Documentation
- [ ] Docstrings updated
- [ ] User documentation updated
- [ ] API documentation updated

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Comments added for complex logic
- [ ] No new warnings introduced
```

### Review Process

1. **Automated Checks**: CI/CD pipeline runs automatically
2. **Code Review**: Maintainers review code quality and design
3. **Testing**: Verify functionality and test coverage
4. **Documentation**: Check documentation completeness
5. **Approval**: At least one maintainer approval required

## Community Guidelines

### Code of Conduct

We are committed to providing a welcoming and inclusive environment:

- **Be Respectful**: Treat all community members with respect
- **Be Inclusive**: Welcome contributors from all backgrounds
- **Be Constructive**: Provide helpful and constructive feedback
- **Be Patient**: Help newcomers learn and contribute

### Communication

- **GitHub Issues**: For bug reports and feature requests
- **GitHub Discussions**: For questions and general discussion
- **Pull Request Comments**: For code-specific discussions
- **Email**: For private matters or security issues

### Recognition

We recognize contributors through:

- **Contributors List**: Listed in repository and documentation
- **Release Notes**: Acknowledgment in release announcements
- **Community Highlights**: Featured contributions in updates

## Getting Help

### For Contributors

- **Documentation**: This contributing guide and developer docs
- **Examples**: Look at existing code for patterns and conventions
- **Ask Questions**: Use GitHub Discussions for help
- **Mentorship**: Request guidance from experienced contributors

### For Maintainers

- **Review Guidelines**: Standards for code review
- **Release Process**: Steps for creating releases
- **Issue Triage**: Guidelines for managing issues
- **Community Management**: Practices for community interaction

## Resources

### Development Tools

- **IDEs**: VS Code, PyCharm, or your preferred editor
- **Version Control**: Git with GitHub
- **Testing**: pytest for test execution
- **Documentation**: Sphinx for documentation generation
- **CI/CD**: GitHub Actions for automated testing

### Learning Resources

- **Python**: [Official Python Tutorial](https://docs.python.org/3/tutorial/)
- **Tkinter**: [Tkinter Documentation](https://docs.python.org/3/library/tkinter.html)
- **Testing**: [pytest Documentation](https://docs.pytest.org/)
- **InSAR**: Background on InSAR processing concepts

Thank you for contributing to InSARLite! Your contributions help make InSAR processing more accessible to everyone. 🚀