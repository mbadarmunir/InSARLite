"""
InSARLite - A comprehensive GUI application for GMTSAR-based InSAR processing.

InSARLite provides an intuitive interface for processing Sentinel-1 SAR data
to generate interferograms and perform time series analysis using the GMTSAR workflow.

Author: Muhammad Badar Munir
Email: mbadarmunir@gmail.com
License: MIT
"""

__version__ = "1.3.2"
__author__ = "Muhammad Badar Munir"
__email__ = "mbadarmunir@gmail.com"
__license__ = "MIT"
__description__ = "A comprehensive GUI application for GMTSAR-based InSAR processing"
__url__ = "https://github.com/mbadarmunir/InSARLite"

# Make version available at package level
# Avoid importing main directly to prevent circular import warnings
__all__ = ["__version__"]

def get_app_class():
    """Lazy import of InSARLiteApp to avoid circular imports."""
    from .main import InSARLiteApp
    return InSARLiteApp