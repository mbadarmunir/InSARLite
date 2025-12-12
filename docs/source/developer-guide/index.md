# Developer Guide

Welcome to the InSARLite Developer Guide! This comprehensive guide covers the architecture, design patterns, and development practices for InSARLite.

## Project Overview

InSARLite is a modern Python application built with:

- **GUI Framework**: Tkinter with custom enhancements
- **Plotting**: Matplotlib with interactive backends
- **Data Processing**: NumPy, SciPy, xarray ecosystem
- **Geospatial**: Rasterio, Shapely, Cartopy
- **SAR Processing**: GMTSAR integration
- **Authentication**: NASA EarthData integration

## Architecture Principles

### 🏗️ **Modular Design**
InSARLite follows a modular architecture where each component has clear responsibilities:

- **Separation of Concerns**: GUI, processing, and utilities are separated
- **Plugin Architecture**: Easy to extend with new processing modules
- **Configuration Management**: Centralized settings and preferences
- **Error Handling**: Comprehensive error management throughout

### 🔄 **Event-Driven Architecture** 
The application uses event-driven patterns for:

- **User Interactions**: Button clicks, map interactions, file selections
- **Progress Updates**: Real-time progress reporting during processing
- **State Management**: Dynamic UI updates based on application state
- **Background Processing**: Non-blocking operations with threading

### 📊 **Data Flow Management**
Efficient data handling through:

- **Lazy Loading**: Data loaded only when needed
- **Memory Management**: Efficient handling of large raster datasets
- **Caching**: Smart caching of expensive operations
- **Streaming**: Processing large files in chunks

## Code Organization

### Directory Structure

```
src/insarlite/
├── main.py                     # Main application entry point
├── config.json                 # Default configuration
├── gmtsar_gui/                 # GMTSAR workflow modules
│   ├── __init__.py
│   ├── data_dwn.py            # Data download functionality
│   ├── dem_dwn.py             # DEM management
│   ├── base2net.py            # Baseline network design
│   ├── align_genIFGs.py       # Interferogram generation
│   ├── unwrap.py              # Phase unwrapping
│   ├── sbas04.py              # Time series analysis
│   └── ...                    # Other processing modules
├── utils/                      # Utility modules
│   ├── __init__.py
│   ├── config_manager.py      # Configuration management
│   ├── earthdata_auth.py      # Authentication system
│   ├── matplotlib_baseline_plotter.py  # Interactive plotting
│   ├── utils.py               # General utilities
│   └── ...                    # Other utilities
└── __init__.py
```

### Module Responsibilities

#### **`main.py`** - Application Orchestrator
- Main GUI window and layout management
- Workflow coordination and state management
- User interaction handling
- Progress tracking and status updates

#### **`gmtsar_gui/`** - Processing Modules
Each module handles a specific part of the InSAR workflow:

- **Data Management**: Download, validation, organization
- **Preprocessing**: Orbit processing, alignment, coregistration
- **Interferometry**: Interferogram generation, coherence calculation
- **Post-processing**: Unwrapping, time series, atmospheric correction

#### **`utils/`** - Supporting Infrastructure
- **Authentication**: Secure credential management
- **Configuration**: Settings persistence and management
- **Plotting**: Interactive visualization components
- **File Operations**: Data I/O and file management

## Design Patterns

### 🎯 **Model-View-Controller (MVC)**

InSARLite implements a loose MVC pattern:

- **Model**: Data classes and processing logic
- **View**: Tkinter GUI components and visualization
- **Controller**: Event handlers and workflow coordination

### 🏭 **Factory Pattern**

Used for creating UI components and processing objects:

```python
class UIFactory:
    @staticmethod
    def create_button(parent, text, command, **kwargs):
        return tk.Button(parent, text=text, command=command, **kwargs)
    
    @staticmethod
    def create_entry_with_browse(parent, browse_command):
        frame = tk.Frame(parent)
        entry = tk.Entry(frame)
        button = tk.Button(frame, text="Browse", command=browse_command)
        return frame, entry, button
```

### 📋 **Observer Pattern**

For progress updates and status notifications:

```python
class ProgressObserver:
    def update_progress(self, percentage, message):
        # Update UI with progress information
        pass

class DataDownloader:
    def __init__(self):
        self.observers = []
    
    def add_observer(self, observer):
        self.observers.append(observer)
    
    def notify_progress(self, percentage, message):
        for observer in self.observers:
            observer.update_progress(percentage, message)
```

### 🔧 **Command Pattern**

For undo/redo functionality and operation management:

```python
class Command:
    def execute(self):
        raise NotImplementedError
    
    def undo(self):
        raise NotImplementedError

class DownloadCommand(Command):
    def __init__(self, urls, destination):
        self.urls = urls
        self.destination = destination
    
    def execute(self):
        # Perform download
        pass
    
    def undo(self):
        # Remove downloaded files
        pass
```

## Key Components

### 🖥️ **Main Application (`InSARLiteApp`)**

The central application class that:

- Manages the main window and layout
- Coordinates between different processing modules
- Handles user interactions and state transitions
- Provides progress feedback and error handling

**Key Methods**:
- `_create_widgets()`: Builds the main UI
- `_on_data_query_callback()`: Handles data search
- `on_next_step()`: Progresses through processing steps
- `_update_data_query_btn_state()`: Manages UI state

### 🛰️ **Data Management System**

Comprehensive data handling including:

- **EarthData Authentication**: Secure credential management
- **Sentinel-1 Downloads**: Bulk data acquisition with progress tracking
- **DEM Management**: Automatic elevation data processing
- **File Organization**: Structured project layout

### 📊 **Interactive Baseline Plotter**

Advanced matplotlib-based plotting system:

- **Real-time Interaction**: Click and drag baseline selection
- **Dynamic Updates**: Live baseline network visualization
- **Export Capabilities**: High-quality figure generation
- **Integration**: Seamless connection with processing workflow

### ⚙️ **Processing Pipeline**

Modular processing system with:

- **Sequential Steps**: Well-defined processing stages
- **Parameter Management**: Configurable processing options
- **Quality Control**: Validation at each step
- **Error Recovery**: Robust error handling and recovery

## Threading and Concurrency

### 🧵 **Threading Strategy**

InSARLite uses threading for:

- **Non-blocking UI**: Keep interface responsive during long operations
- **Parallel Downloads**: Multiple concurrent downloads
- **Background Processing**: CPU-intensive operations
- **Progress Updates**: Real-time status reporting

```python
import threading
from concurrent.futures import ThreadPoolExecutor

class BackgroundProcessor:
    def __init__(self, max_workers=4):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.pause_event = threading.Event()
    
    def submit_task(self, func, *args, **kwargs):
        future = self.executor.submit(func, *args, **kwargs)
        return future
    
    def pause_processing(self):
        self.pause_event.set()
    
    def resume_processing(self):
        self.pause_event.clear()
```

### 🔄 **Event Loop Integration**

Proper integration between background threads and Tkinter:

```python
def background_task():
    # Perform time-consuming operation
    result = process_data()
    
    # Update UI from main thread
    root.after(0, lambda: update_ui(result))

# Start background task
thread = threading.Thread(target=background_task)
thread.start()
```

## Error Handling Strategy

### 🚨 **Comprehensive Error Management**

InSARLite implements multi-level error handling:

1. **Input Validation**: Prevent errors before they occur
2. **Graceful Degradation**: Continue operation when possible
3. **User Feedback**: Clear error messages and recovery suggestions
4. **Logging**: Detailed error logging for debugging

```python
import logging
from tkinter import messagebox

logger = logging.getLogger(__name__)

def safe_operation(func):
    """Decorator for safe operation execution."""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {e}")
            messagebox.showerror("Error", f"Operation failed: {e}")
            return None
    return wrapper

@safe_operation
def risky_processing_step():
    # Processing code that might fail
    pass
```

### 📝 **Logging Configuration**

Structured logging throughout the application:

```python
import logging

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('insarlite.log'),
            logging.StreamHandler()
        ]
    )
```

## Performance Optimization

### 💾 **Memory Management**

Strategies for handling large datasets:

- **Chunked Processing**: Process data in manageable chunks
- **Lazy Loading**: Load data only when needed
- **Memory Profiling**: Monitor memory usage
- **Garbage Collection**: Explicit cleanup of large objects

```python
import gc
import psutil

def monitor_memory():
    process = psutil.Process()
    memory_mb = process.memory_info().rss / 1024 / 1024
    print(f"Memory usage: {memory_mb:.1f} MB")

def cleanup_memory():
    gc.collect()
    monitor_memory()
```

### ⚡ **Performance Optimization**

Techniques for improved performance:

- **Vectorized Operations**: Use NumPy for efficient array operations
- **Parallel Processing**: Utilize multiple CPU cores
- **Caching**: Cache expensive computations
- **Profiling**: Identify and optimize bottlenecks

```python
import numpy as np
from functools import lru_cache
from multiprocessing import Pool

@lru_cache(maxsize=128)
def expensive_calculation(param):
    # Cached expensive operation
    return result

def parallel_processing(data_list):
    with Pool() as pool:
        results = pool.map(process_item, data_list)
    return results
```

## Testing Framework

### 🧪 **Testing Strategy**

InSARLite uses a comprehensive testing approach:

- **Unit Tests**: Test individual functions and classes
- **Integration Tests**: Test component interactions
- **GUI Tests**: Test user interface components
- **End-to-End Tests**: Test complete workflows

```python
import unittest
from unittest.mock import Mock, patch

class TestDataDownloader(unittest.TestCase):
    def setUp(self):
        self.downloader = DataDownloader()
    
    def test_download_success(self):
        # Test successful download
        pass
    
    def test_download_failure(self):
        # Test error handling
        pass
    
    @patch('requests.get')
    def test_download_with_mock(self, mock_get):
        # Test with mocked network calls
        pass
```

### 🎯 **Continuous Integration**

Automated testing with GitHub Actions:

```yaml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.9
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run tests
        run: python -m pytest tests/
```

## Development Workflow

### 🔄 **Git Workflow**

Standard Git practices for InSARLite development:

1. **Feature Branches**: Create feature branches for new development
2. **Pull Requests**: Use PRs for code review
3. **Code Review**: Peer review before merging
4. **Release Tags**: Tag releases with version numbers

### 📦 **Package Management**

Modern Python packaging with:

- **pyproject.toml**: Modern package configuration
- **setup.cfg**: Additional package metadata
- **requirements.txt**: Development dependencies
- **version management**: Semantic versioning

## Extending InSARLite

### 🔌 **Adding New Processing Modules**

To add a new processing step:

1. **Create Module**: Add new file in `gmtsar_gui/`
2. **Implement Interface**: Follow existing module patterns
3. **Update Main App**: Add integration points
4. **Add Tests**: Include comprehensive testing
5. **Update Documentation**: Document new functionality

### 🎨 **Customizing the UI**

For UI modifications:

1. **Follow Patterns**: Use existing UI factory methods
2. **Maintain Consistency**: Follow established visual patterns
3. **Add Configuration**: Make customizations configurable
4. **Test Thoroughly**: Test across different screen sizes

### 📊 **Adding Visualization Features**

For new plotting capabilities:

1. **Extend Plotter**: Build on matplotlib foundation
2. **Interactive Features**: Add click/drag functionality
3. **Export Options**: Include various output formats
4. **Integration**: Connect with processing pipeline

## Best Practices

### 🎯 **Code Quality**

- **PEP 8 Compliance**: Follow Python style guidelines
- **Type Hints**: Use type annotations for clarity
- **Docstrings**: Document all public functions and classes
- **Code Reviews**: Peer review all changes

### 🔒 **Security**

- **Credential Management**: Secure storage of API keys
- **Input Validation**: Validate all user inputs
- **Safe Operations**: Use safe file operations
- **Dependency Management**: Keep dependencies updated

### 📚 **Documentation**

- **Code Comments**: Explain complex logic
- **API Documentation**: Auto-generated from docstrings
- **User Guides**: Comprehensive user documentation
- **Examples**: Provide working code examples

## Release Process

### 🚀 **Version Management**

InSARLite follows semantic versioning:

- **Major.Minor.Patch** (e.g., 1.0.0)
- **Major**: Breaking changes
- **Minor**: New features (backward compatible)
- **Patch**: Bug fixes

### 📦 **Release Steps**

1. **Update Version**: Bump version numbers
2. **Update Changelog**: Document changes
3. **Run Tests**: Ensure all tests pass
4. **Build Package**: Create distribution packages
5. **Tag Release**: Create Git tag
6. **Publish**: Upload to PyPI

## Community and Support

### 💬 **Communication Channels**

- **GitHub Issues**: Bug reports and feature requests
- **GitHub Discussions**: Community discussions
- **Documentation**: Comprehensive guides and references
- **Code Reviews**: Collaborative development

### 🤝 **Contributing**

We welcome contributions! See the [Contributing Guide](../contributing.md) for details on development setup, code standards, testing requirements, and documentation guidelines.

### 📋 **Issue Management**

- **Bug Reports**: Use issue templates
- **Feature Requests**: Describe use cases clearly
- **Support Questions**: Use GitHub Discussions
- **Security Issues**: Follow responsible disclosure

## Next Steps

Ready to contribute to InSARLite? Check out:

- [Contributing Guidelines](../contributing.md) - See how to contribute
- [GitHub Repository](https://github.com/mbadarmunir/InSARLite) - View source code
- [Issues](https://github.com/mbadarmunir/InSARLite/issues) - Report bugs or request features