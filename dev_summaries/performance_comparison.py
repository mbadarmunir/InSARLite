"""
Performance comparison for file comparison methods.
"""

import os
import zipfile
import hashlib
import time
from typing import List, Tuple


def are_files_identical_size_only(zip_file_obj: zipfile.ZipFile, zip_member: str, local_file_path: str) -> bool:
    """
    Check if files are identical using SIZE COMPARISON ONLY.
    
    This is much faster but less reliable than checksum comparison.
    
    Args:
        zip_file_obj: ZipFile object
        zip_member: Path to member in ZIP
        local_file_path: Local file path to compare
        
    Returns:
        True if file sizes match, False otherwise
    """
    try:
        # First check if local file exists
        if not os.path.exists(local_file_path):
            return False
        
        # Get ZIP file info
        zip_info = zip_file_obj.getinfo(zip_member)
        zip_size = zip_info.file_size
        
        # Get local file size
        local_size = os.path.getsize(local_file_path)
        
        # Return True if sizes match
        return zip_size == local_size
        
    except Exception as e:
        print(f"Error comparing file sizes {zip_member} and {local_file_path}: {e}")
        # If we can't compare, assume they're different and extract
        return False


def are_files_identical_hybrid(zip_file_obj: zipfile.ZipFile, zip_member: str, local_file_path: str, 
                              quick_mode: bool = False) -> bool:
    """
    Hybrid approach - size + timestamp + optional checksum.
    
    Args:
        zip_file_obj: ZipFile object
        zip_member: Path to member in ZIP
        local_file_path: Local file path to compare
        quick_mode: If True, only compare size and timestamp
        
    Returns:
        True if files are considered identical, False otherwise
    """
    try:
        # First check if local file exists
        if not os.path.exists(local_file_path):
            return False
        
        # Get ZIP file info
        zip_info = zip_file_obj.getinfo(zip_member)
        zip_size = zip_info.file_size
        
        # Get local file info
        local_size = os.path.getsize(local_file_path)
        local_mtime = os.path.getmtime(local_file_path)
        
        # If sizes don't match, files are different
        if zip_size != local_size:
            return False
        
        # If sizes are 0, consider them identical (empty files)
        if zip_size == 0:
            return True
        
        # Get ZIP file timestamp (if available)
        try:
            zip_timestamp = time.mktime(zip_info.date_time + (0, 0, -1))
            # If local file is newer than ZIP file, assume it's the same extracted file
            if local_mtime >= zip_timestamp:
                if quick_mode:
                    return True  # Trust size + timestamp in quick mode
        except (AttributeError, ValueError):
            zip_timestamp = None
        
        if quick_mode:
            return True  # In quick mode, size match is sufficient
        
        # For more thorough checking, use content comparison for small files
        if zip_size < 1024 * 1024:  # < 1MB
            # Read ZIP file content
            with zip_file_obj.open(zip_member) as zip_src:
                zip_content = zip_src.read()
            
            # Read local file content
            with open(local_file_path, 'rb') as local_file:
                local_content = local_file.read()
            
            return zip_content == local_content
        
        # For larger files in non-quick mode, still use checksum
        # (You could skip this for even faster operation)
        zip_hash = hashlib.md5()
        with zip_file_obj.open(zip_member) as zip_src:
            while True:
                chunk = zip_src.read(8192)
                if not chunk:
                    break
                zip_hash.update(chunk)
        zip_checksum = zip_hash.hexdigest()
        
        local_hash = hashlib.md5()
        with open(local_file_path, 'rb') as local_file:
            while True:
                chunk = local_file.read(8192)
                if not chunk:
                    break
                local_hash.update(chunk)
        local_checksum = local_hash.hexdigest()
        
        return zip_checksum == local_checksum
        
    except Exception as e:
        print(f"Error comparing files {zip_member} and {local_file_path}: {e}")
        return False


def benchmark_file_comparison_methods(zip_file_path: str, sample_size: int = 10):
    """
    Benchmark different file comparison methods.
    
    Args:
        zip_file_path: Path to a ZIP file for testing
        sample_size: Number of files to test with
    """
    if not os.path.exists(zip_file_path) or not zipfile.is_zipfile(zip_file_path):
        print(f"Invalid ZIP file: {zip_file_path}")
        return
    
    print("File Comparison Method Performance Benchmark")
    print("=" * 50)
    
    with zipfile.ZipFile(zip_file_path, 'r') as zf:
        # Get sample files from ZIP
        all_files = [f for f in zf.namelist() if not f.endswith('/')]
        test_files = all_files[:min(sample_size, len(all_files))]
        
        if not test_files:
            print("No files found in ZIP for testing")
            return
        
        print(f"Testing with {len(test_files)} files from {zip_file_path}")
        print()
        
        # Test each method
        methods = [
            ("Size Only", are_files_identical_size_only),
            ("Hybrid Quick (size + timestamp)", lambda zf, mem, path: are_files_identical_hybrid(zf, mem, path, True)),
            ("Hybrid Full (size + content/checksum)", lambda zf, mem, path: are_files_identical_hybrid(zf, mem, path, False)),
        ]
        
        for method_name, method_func in methods:
            start_time = time.time()
            results = []
            
            for test_file in test_files:
                fake_local_path = f"/tmp/fake_{os.path.basename(test_file)}"
                # Create a fake local file for testing
                try:
                    os.makedirs(os.path.dirname(fake_local_path), exist_ok=True)
                    with zf.open(test_file) as src, open(fake_local_path, 'wb') as dst:
                        dst.write(src.read())
                    
                    # Now test the comparison
                    result = method_func(zf, test_file, fake_local_path)
                    results.append(result)
                    
                    # Clean up
                    if os.path.exists(fake_local_path):
                        os.remove(fake_local_path)
                        
                except Exception as e:
                    print(f"Error testing {test_file}: {e}")
                    continue
            
            end_time = time.time()
            avg_time_per_file = (end_time - start_time) / len(test_files) if test_files else 0
            
            print(f"{method_name}:")
            print(f"  Total time: {end_time - start_time:.3f}s")
            print(f"  Avg per file: {avg_time_per_file * 1000:.1f}ms")
            print(f"  Results: {sum(results)}/{len(results)} files matched")
            print()