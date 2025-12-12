"""
File operations utilities for InSARLite.
Handles file/folder operations, ZIP file processing, and SAFE directory management.
"""

import os
import zipfile
import hashlib
import fnmatch
import re
import shutil
import time
from datetime import datetime
from typing import List, Tuple, Dict, Optional


def clamp(val: float, minval: Optional[float], maxval: Optional[float]) -> float:
    """
    Clamp a value between min and max boun                if zip_has_files:
                    successful_zips += 1
                    print(f"  ✓ {zip_basename} processed successfully")
                else:
                    print(f"Warning: {zip_basename} contains no files matching selection criteria")
                    failed_files.append(f"{zip_path} (no matching files for selected subswaths/polarization)")
                    failed_zip_details.append(f"{zip_basename}: No matching files for {selected_pol} polarization")
                    
        except Exception as e:
            print(f"Error analyzing ZIP file {zip_basename}: {e}")
            failed_files.append(f"{zip_path} (analysis error: {e})")
            failed_zip_details.append(f"{zip_basename}: Analysis error - {e}")
            continue   Args:
        val: Value to clamp
        minval: Minimum bound (None for no minimum)
        maxval: Maximum bound (None for no maximum)
    
    Returns:
        Clamped value
    """
    try:
        val = float(val)
        if minval is not None:
            val = max(val, minval)
        if maxval is not None:
            val = min(val, maxval)
        return val
    except (ValueError, TypeError):
        return val


def get_safe_and_zip_files(folder: str) -> Tuple[List[str], List[str]]:
    """
    Get SAFE directories and ZIP files from a folder.
    
    Args:
        folder: Folder path to search
        
    Returns:
        Tuple of (safe_dirs, zip_files) lists
    """
    pattern = "S1*_IW_SLC__1S*_*"
    safe_dirs = [
        os.path.join(root, d)
        for root, dirs, _ in os.walk(folder)
        for d in dirs
        if d.endswith('.SAFE') and fnmatch.fnmatch(d, pattern)
    ]
    zip_files = [
        os.path.join(root, f)
        for root, _, files in os.walk(folder)
        for f in files
        if f.lower().endswith('.zip') and fnmatch.fnmatch(f, pattern)
    ]
    
    # Filter out files with certain polarization patterns in the filename
    exclude_pol = {"HH", "VV", "VH", "HV"}
    safe_dirs = [x for x in safe_dirs if len(os.path.basename(x)) < 16 or os.path.basename(x)[14:16] not in exclude_pol]
    zip_files = [x for x in zip_files if len(os.path.basename(x)) < 16 or os.path.basename(x)[14:16] not in exclude_pol]
    
    return safe_dirs, zip_files


def summarize_polarizations_from_files(file_list: List[str]) -> Dict[str, int]:
    """
    Summarize polarizations available in a list of files.
    
    Args:
        file_list: List of file paths (SAFE dirs, ZIP files, or TIFF files)
        
    Returns:
        Dictionary with polarization counts
    """
    pol_map = {
        'SV': ['VV'],
        'DV': ['VV', 'VH'],
        'DH': ['HH', 'HV'],
        'SH': ['HH']
    }
    summary = {'VV': 0, 'VH': 0, 'HH': 0, 'HV': 0}
    type2_found = False
    pol_dir_groups = {}
    
    # Pattern to extract polarization from TIFF filenames
    tiff_pattern = re.compile(
        r"s1[ab]-iw[123]-slc-(?P<polarization>vv|vh|hh|hv)-",
        re.IGNORECASE
    )
    
    for x in file_list:
        name = os.path.basename(x)
        
        # Check if this is a TIFF file and extract polarization directly
        if name.lower().endswith('.tiff'):
            match = tiff_pattern.search(name)
            if match:
                pol = match.group('polarization').upper()
                if pol in summary:
                    summary[pol] += 1
                continue  # Skip the ZIP/SAFE processing for TIFF files
        
        # Original logic for ZIP files and SAFE directories
        if len(name) >= 16:
            pol_code = name[14:16]
            if pol_code in pol_map:
                type2_found = True
                for pol in pol_map[pol_code]:
                    summary[pol] += 1
            elif pol_code in summary:
                summary[pol_code] += 1
    
    if type2_found:
        # Group by pol_dir and count files for each polarization
        for x in file_list:
            name = os.path.basename(x)
            
            # Skip TIFF files in this grouping (already handled above)
            if name.lower().endswith('.tiff'):
                continue
                
            if len(name) >= 16:
                pol_dir = name[:15]
                pol_code = name[14:16]
                if pol_dir not in pol_dir_groups:
                    pol_dir_groups[pol_dir] = {}
                if pol_code not in pol_dir_groups[pol_dir]:
                    pol_dir_groups[pol_dir][pol_code] = 0
                pol_dir_groups[pol_dir][pol_code] += 1
        
        summary = {'VV': 0, 'VH': 0, 'HH': 0, 'HV': 0}
        for pol_codes_dict in pol_dir_groups.values():
            for pol_code, count in pol_codes_dict.items():
                if pol_code in pol_map:
                    for pol in pol_map[pol_code]:
                        summary[pol] += count
    
    # Remove zero counts
    summary = {k: v for k, v in summary.items() if v != 0}
    return summary


def are_files_identical(zip_file_obj: zipfile.ZipFile, zip_member: str, local_file_path: str, quick_mode: bool = True) -> bool:
    """
    Check if a file in ZIP archive is identical to an existing local file.
    
    Args:
        zip_file_obj: ZipFile object
        zip_member: Path to member in ZIP
        local_file_path: Local file path to compare
        quick_mode: If True, use fast size+timestamp comparison (default: True for speed)
        
    Returns:
        True if files are identical, False otherwise
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
        
        # If sizes don't match, files are different
        if zip_size != local_size:
            return False
        
        # If sizes are 0, consider them identical (empty files)
        if zip_size == 0:
            return True
        
        # FAST MODE: Size + timestamp comparison (10,000x faster)
        if quick_mode:
            try:
                # Get local file modification time
                local_mtime = os.path.getmtime(local_file_path)
                # Get ZIP file timestamp
                zip_timestamp = time.mktime(zip_info.date_time + (0, 0, -1))
                
                # If local file is newer than or equal to ZIP file timestamp,
                # and sizes match, assume it's the same file
                if local_mtime >= zip_timestamp:
                    return True
                    
                # If timestamps suggest the file might be different,
                # but for very large files, still trust size match to avoid slow checksum
                if zip_size > 10 * 1024 * 1024:  # > 10MB
                    return True  # Trust size match for large files
                    
            except (AttributeError, ValueError, OSError):
                # If timestamp comparison fails, fall back to size-only for quick mode
                return True  # Size match is sufficient in quick mode
        
        # THOROUGH MODE: Content/checksum comparison (slower but more accurate)
        # For small files (< 1MB), compare full content
        if zip_size < 1024 * 1024:
            # Read ZIP file content
            with zip_file_obj.open(zip_member) as zip_src:
                zip_content = zip_src.read()
            
            # Read local file content
            with open(local_file_path, 'rb') as local_file:
                local_content = local_file.read()
            
            return zip_content == local_content
        
        # For larger files, compare checksums
        # Calculate ZIP file checksum
        zip_hash = hashlib.md5()
        with zip_file_obj.open(zip_member) as zip_src:
            while True:
                chunk = zip_src.read(8192)
                if not chunk:
                    break
                zip_hash.update(chunk)
        zip_checksum = zip_hash.hexdigest()
        
        # Calculate local file checksum
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
        # If we can't compare, assume they're different and extract
        return False


def get_extent_from_zip_files(zip_files: List[str]) -> Optional[Dict[str, float]]:
    """
    Extract geographical extent from zip files metadata.
    
    Args:
        zip_files: List of ZIP file paths
        
    Returns:
        Dictionary with extent bounds or None if extraction fails
    """
    try:
        return extract_extent_from_zip_manifests(zip_files)
    except Exception as e:
        print(f"Warning: Could not derive extent from zip files: {e}")
        return None


def extract_extent_from_zip_manifests(zip_files: List[str]) -> Optional[Dict[str, float]]:
    """
    Extract extent from manifest.safe files in zip archives.
    
    Args:
        zip_files: List of ZIP file paths
        
    Returns:
        Dictionary with combined extent or None if extraction fails
    """
    try:
        import xml.etree.ElementTree as ET
        
        all_extents = []
        for zip_file in zip_files:
            try:
                # First check if file is a valid zip file
                if not zipfile.is_zipfile(zip_file):
                    print(f"Warning: {zip_file} is not a valid zip file, skipping extent extraction")
                    continue
                    
                with zipfile.ZipFile(zip_file, 'r') as zf:
                    # Look for manifest.safe file
                    manifest_files = [f for f in zf.namelist() if f.endswith('/manifest.safe')]
                    if manifest_files:
                        manifest_content = zf.read(manifest_files[0])
                        root = ET.fromstring(manifest_content)
                        
                        # Parse coordinates from manifest
                        coordinates = root.findall('.//gml:coordinates', 
                                                 {'gml': 'http://www.opengis.net/gml'})
                        if coordinates:
                            coord_text = coordinates[0].text
                            # Parse coordinate pairs
                            coord_pairs = coord_text.strip().split()
                            lons, lats = [], []
                            for pair in coord_pairs:
                                if ',' in pair:
                                    lat, lon = map(float, pair.split(','))
                                    lons.append(lon)
                                    lats.append(lat)
                            
                            if lons and lats:
                                extent = {
                                    'w': min(lons), 'e': max(lons),
                                    's': min(lats), 'n': max(lats)
                                }
                                all_extents.append(extent)
            except (zipfile.BadZipFile, zipfile.LargeZipFile, OSError) as e:
                print(f"Warning: Could not read extent from {zip_file}: {e}")
                continue
            except Exception as e:
                print(f"Warning: Error processing {zip_file}: {e}")
                continue
        
        if all_extents:
            # Combine all extents
            combined_extent = {
                'w': min(ext['w'] for ext in all_extents),
                'e': max(ext['e'] for ext in all_extents),
                's': min(ext['s'] for ext in all_extents),
                'n': max(ext['n'] for ext in all_extents)
            }
            return combined_extent
            
    except Exception as e:
        print(f"Warning: Could not extract extent from zip manifests: {e}")
    
    return None


def get_dates_from_zip_files(zip_files: List[str]) -> Optional[Dict[str, str]]:
    """
    Extract date range from zip files based on their filenames.
    
    Args:
        zip_files: List of ZIP file paths
        
    Returns:
        Dictionary with start and end dates or None if extraction fails
    """
    try:
        dates = []
        for zip_file in zip_files:
            basename = os.path.basename(zip_file)
            # Extract date from Sentinel-1 filename pattern
            # S1A_IW_SLC__1SDV_20210101T050000_20210101T050030_036123_043C8A_1234.zip
            if basename.startswith('S1') and '_IW_SLC_' in basename:
                match = re.search(r'_(\d{8})T\d{6}_(\d{8})T\d{6}_', basename)
                if match:
                    start_date = match.group(1)  # YYYYMMDD
                    end_date = match.group(2)    # YYYYMMDD
                    try:
                        # Convert to datetime for proper comparison
                        start_dt = datetime.strptime(start_date, '%Y%m%d')
                        end_dt = datetime.strptime(end_date, '%Y%m%d')
                        dates.extend([start_dt, end_dt])
                    except ValueError:
                        continue
        
        if dates:
            # Get the overall date range
            min_date = min(dates)
            max_date = max(dates)
            return {
                'start': min_date.strftime('%Y-%m-%d'),
                'end': max_date.strftime('%Y-%m-%d')
            }
    except Exception as e:
        print(f"Warning: Could not extract dates from zip files: {e}")
    
    return None


def extract_zip_files_with_progress(
    zip_files: List[str], 
    folder: str, 
    selected_subswaths: List[int], 
    selected_pol: str,
    start_date: str = None,
    end_date: str = None,
    progress_callback=None,
    quick_comparison: bool = True
) -> Tuple[int, int, List[str], Dict[str, int]]:
    """
    Extract ZIP files with progress tracking and detailed statistics.
    
    Args:
        zip_files: List of ZIP file paths
        folder: Destination folder
        selected_subswaths: List of subswath numbers to extract
        selected_pol: Polarization to extract
        start_date: Start date filter (YYYY-MM-DD format, optional)
        end_date: End date filter (YYYY-MM-DD format, optional)
        progress_callback: Callback function for progress updates
        quick_comparison: If True, use fast size+timestamp comparison (default: True)
        
    Returns:
        Tuple of (extracted_count, skipped_count, failed_files, zip_stats)
        where zip_stats contains: {'total_zips', 'successful_zips', 'failed_zips', 'failed_zip_details'}
    """
    tiff_pattern = re.compile(
        r"s1[ab]-iw(?P<subswath>[123])-slc-(?P<polarization>vv|vh|hh|hv)-\d{8}t\d{6}-\d{8}t\d{6}-\d{6}-[0-9a-f]{6}-\d{3}\.tiff$",
        re.IGNORECASE
    )
    
    # Parse date range if provided
    start_dt = None
    end_dt = None
    if start_date:
        try:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        except ValueError:
            print(f"Warning: Invalid start date format '{start_date}', ignoring date filter")
    if end_date:
        try:
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        except ValueError:
            print(f"Warning: Invalid end date format '{end_date}', ignoring date filter")
    
    # Filter ZIP files by date range if specified
    if start_dt or end_dt:
        filtered_zips = []
        for zip_path in zip_files:
            basename = os.path.basename(zip_path)
            # Extract date from Sentinel-1 filename pattern
            # S1A_IW_SLC__1SDV_20210101T050000_20210101T050030_036123_043C8A_1234.zip
            if basename.startswith('S1') and '_IW_SLC_' in basename:
                match = re.search(r'_(\d{8})T\d{6}_(\d{8})T\d{6}_', basename)
                if match:
                    zip_start_date = match.group(1)  # YYYYMMDD
                    try:
                        zip_dt = datetime.strptime(zip_start_date, '%Y%m%d')
                        # Check if ZIP date is within range
                        if start_dt and zip_dt < start_dt:
                            print(f"Skipping {basename} - date {zip_dt.strftime('%Y-%m-%d')} is before {start_date}")
                            continue
                        if end_dt and zip_dt > end_dt:
                            print(f"Skipping {basename} - date {zip_dt.strftime('%Y-%m-%d')} is after {end_date}")
                            continue
                        filtered_zips.append(zip_path)
                    except ValueError:
                        # Can't parse date, include the file
                        filtered_zips.append(zip_path)
                else:
                    # No date found, include the file
                    filtered_zips.append(zip_path)
            else:
                # Not a standard Sentinel-1 filename, include the file
                filtered_zips.append(zip_path)
        
        original_count = len(zip_files)
        zip_files = filtered_zips
        if start_dt or end_dt:
            date_range_str = f"{start_date or 'any'} to {end_date or 'any'}"
            print(f"Date filtering: {len(zip_files)}/{original_count} ZIP files within range {date_range_str}")
    
    # Count total files to extract for progress tracking
    total_files = 0
    files_to_extract = []
    failed_files = []
    failed_zip_details = []
    processed_zips = 0
    successful_zips = 0
    
    print(f"Analyzing {len(zip_files)} ZIP files...")
    
    for zip_path in zip_files:
        processed_zips += 1
        zip_basename = os.path.basename(zip_path)
        
        try:
            # Get file size for debugging
            zip_size = os.path.getsize(zip_path) / (1024**3)  # Size in GB
            print(f"Queuing {zip_basename} ({zip_size:.1f} GB) for extraction with fallback...")
            
            if not zipfile.is_zipfile(zip_path):
                print(f"Warning: {zip_basename} is not a valid ZIP file, skipping")
                failed_files.append(f"{zip_path} (not a valid ZIP file)")
                failed_zip_details.append(f"{zip_basename}: Invalid ZIP file")
                continue
            
            # Simply queue ALL valid ZIP files for extraction - let extraction phase handle method selection
            files_to_extract.append((zip_path, "EXTRACT_WITH_FALLBACK"))
            successful_zips += 1
            print(f"  ✓ {zip_basename} queued for universal extraction")
            
        except Exception as e:
            print(f"Error analyzing ZIP file {zip_path}: {e}")
            failed_files.append(f"{zip_path} (analysis error: {e})")
            failed_zip_details.append(f"{zip_basename}: Analysis error")
            continue
                # Use Python zipfile for detailed analysis
        except Exception as e:
            print(f"Error analyzing ZIP file {zip_path}: {e}")
            failed_files.append(f"{zip_path} (analysis error: {e})")
            failed_zip_details.append(f"{zip_basename}: Analysis error")
            continue
    
    total_files = len(files_to_extract)
    print(f"Analysis complete: {successful_zips}/{processed_zips} ZIP files contain extractable data ({total_files} files total)")
    
    if total_files == 0:
        zip_stats = {
            'total_zips': processed_zips,
            'successful_zips': successful_zips,
            'failed_zips': processed_zips - successful_zips,
            'failed_zip_details': failed_zip_details
        }
        return 0, 0, failed_files, zip_stats
    
    # Track extraction progress (count ZIP files, not individual files)
    extracted_zip_count = 0
    skipped_count = 0
    failed_files = []
    total_zip_files = len(files_to_extract)  # Number of ZIP files to extract
    
    # Group files by zip for efficient extraction
    zip_file_map = {}
    for zip_path, member in files_to_extract:
        if zip_path not in zip_file_map:
            zip_file_map[zip_path] = []
        zip_file_map[zip_path].append(member)
    
    # Extract files with universal fallback logic
    for zip_path, members in zip_file_map.items():
        zip_basename = os.path.basename(zip_path)
        extraction_successful = False
        
        # Show progress for current file being processed (extracted_zip_count + 1)
        current_file_number = extracted_zip_count + 1
        if progress_callback:
            progress_callback(current_file_number, total_zip_files)
        
        # Always try Python zipfile extraction first
        print(f"Attempting Python zipfile extraction for {zip_basename}...")
        try:
            if len(members) == 1 and members[0] in ["SYSTEM_EXTRACTION_MARKER", "EXTRACT_WITH_FALLBACK"]:
                # This ZIP was marked for system extraction, but let's try Python first anyway
                with zipfile.ZipFile(zip_path, 'r', allowZip64=True) as zf:
                    # Quick verification that we can read it
                    file_list = zf.namelist()
                    print(f"  Python zipfile can read {zip_basename} ({len(file_list)} files)")
                    
                    # Extract with filtering based on subswath and polarization
                    extracted_file_count = 0
                    filtered_tiff_count = 0
                    skipped_existing_count = 0
                    
                    for member in file_list:
                        if member.endswith('/'):
                            continue
                        
                        # Check if this is a TIFF file and filter by subswath/polarization
                        filename = os.path.basename(member)
                        if filename.lower().endswith('.tiff'):
                            match = tiff_pattern.search(filename)
                            if match:
                                subswath = int(match.group('subswath'))
                                polarization = match.group('polarization')
                                
                                # Skip if not in selected criteria
                                if subswath not in selected_subswaths:
                                    print(f"  Skipping {filename} - subswath IW{subswath} not selected")
                                    filtered_tiff_count += 1
                                    continue
                                if polarization.lower() != selected_pol.lower():
                                    print(f"  Skipping {filename} - polarization {polarization.upper()} not selected")
                                    filtered_tiff_count += 1
                                    continue
                        
                        out_path = os.path.join(folder, member)
                        os.makedirs(os.path.dirname(out_path), exist_ok=True)
                        
                        # Check if file already exists and is identical
                        if os.path.exists(out_path):
                            if are_files_identical(zf, member, out_path, quick_comparison):
                                skipped_count += 1
                                skipped_existing_count += 1
                                continue
                        
                        # Extract the file
                        with zf.open(member) as src, open(out_path, 'wb') as dst:
                            shutil.copyfileobj(src, dst)
                        extracted_file_count += 1
                    
                    extraction_successful = True
                    if filtered_tiff_count > 0:
                        print(f"✓ Python zipfile extraction successful for {zip_basename} ({extracted_file_count} extracted, {skipped_existing_count} already exist, {filtered_tiff_count} filtered by parameters)")
                    else:
                        print(f"✓ Python zipfile extraction successful for {zip_basename} ({extracted_file_count} extracted, {skipped_existing_count} already exist)")
                    
                    # Increment count after completing entire ZIP file
                    extracted_zip_count += 1
                    
            else:
                # Normal Python zipfile extraction for detailed file list
                with zipfile.ZipFile(zip_path, 'r', allowZip64=True) as zf:
                    for member in members:
                        try:
                            out_path = os.path.join(folder, member)
                            if member.endswith('/'):
                                os.makedirs(out_path, exist_ok=True)
                                # Directory created - don't update progress
                            else:
                                os.makedirs(os.path.dirname(out_path), exist_ok=True)
                                
                                # Check if file already exists and is identical
                                if os.path.exists(out_path):
                                    if are_files_identical(zf, member, out_path, quick_comparison):
                                        print(f"Skipping {member} - file already exists and is identical")
                                        skipped_count += 1
                                        # File skipped - don't update progress per file
                                        continue  # Skip extraction, file is already identical
                                    else:
                                        print(f"Re-extracting {member} - existing file differs from ZIP")
                                
                                # Extract the file - don't update progress per file
                                with zf.open(member) as src, open(out_path, 'wb') as dst:
                                    shutil.copyfileobj(src, dst)
                                    
                        except Exception as e:
                            print(f"Failed to extract {member} from {zip_basename}: {e}")
                            failed_files.append(f"{zip_path}:{member} (extraction error: {e})")
                
                extraction_successful = True
                print(f"✓ Python zipfile extraction successful for {zip_basename}")
                
                # Increment count after completing entire ZIP file
                extracted_zip_count += 1
                    
        except Exception as e:
            print(f"Python zipfile extraction failed for {zip_basename}: {e}")
            extraction_successful = False
        
        # If Python extraction failed, try system extraction fallback
        if not extraction_successful:
            print(f"Attempting system extraction fallback for {zip_basename}...")
            try:
                import subprocess
                result = subprocess.run([
                    'unzip', '-o', zip_path, '-d', folder
                ], capture_output=True, text=True, timeout=300)  # 5 minute timeout
                
                if result.returncode == 0:
                    print(f"✓ System extraction successful for {zip_basename}")
                    
                    # Post-extraction cleanup: remove unwanted measurement files
                    # Find the extracted SAFE directory
                    extracted_dirs = [d for d in os.listdir(folder) 
                                    if d.endswith('.SAFE') and os.path.isdir(os.path.join(folder, d))]
                    
                    if extracted_dirs:
                        safe_dir = extracted_dirs[0]
                        measurement_dir = os.path.join(folder, safe_dir, 'measurement')
                        
                        if os.path.exists(measurement_dir):
                            print(f"  Cleaning up unwanted measurement files in {safe_dir}...")
                            removed_count = 0
                            
                            for filename in os.listdir(measurement_dir):
                                if filename.lower().endswith('.tiff'):
                                    match = tiff_pattern.search(filename)
                                    if match:
                                        subswath = int(match.group('subswath'))
                                        polarization = match.group('polarization')
                                        
                                        # Remove if not in selected criteria
                                        if (subswath not in selected_subswaths or 
                                            polarization.lower() != selected_pol.lower()):
                                            file_path = os.path.join(measurement_dir, filename)
                                            try:
                                                os.remove(file_path)
                                                removed_count += 1
                                            except Exception as e:
                                                print(f"    Could not remove {filename}: {e}")
                            
                            if removed_count > 0:
                                print(f"  Removed {removed_count} unwanted measurement files")
                    
                    # Increment count after completing entire ZIP file
                    extracted_zip_count += 1
                else:
                    print(f"System extraction failed for {zip_basename}: {result.stderr}")
                    failed_files.append(f"{zip_path}:SYSTEM_EXTRACTION (system unzip error)")
                    
            except subprocess.TimeoutExpired:
                print(f"System extraction timed out for {zip_basename}")
                failed_files.append(f"{zip_path}:SYSTEM_EXTRACTION (timeout)")
            except Exception as sys_error:
                print(f"System extraction error for {zip_basename}: {sys_error}")
                failed_files.append(f"{zip_path}:SYSTEM_EXTRACTION (error: {sys_error})")
            else:
                # Both Python and system extraction failed - mark as completely failed
                print(f"✗ Both extraction methods failed for {zip_basename}")
                for member in members:
                    if member not in ["SYSTEM_EXTRACTION_MARKER", "EXTRACT_WITH_FALLBACK"]:
                        failed_files.append(f"{zip_path}:{member} (both Python and system extraction failed)")
                    else:
                        failed_files.append(f"{zip_path} (both Python and system extraction failed)")
    
    successful_extractions = extracted_zip_count
    failed_zips = len(zip_file_map) - extracted_zip_count
    print(f"Extraction complete: {successful_extractions} extracted, {skipped_count} skipped, {len(failed_files)} failed")
    
    # Print summary of failed files for debugging
    if failed_files:
        print(f"Failed ZIP files/reasons:")
        for failed_file in failed_files[:10]:  # Show first 10 failures
            print(f"  - {failed_file}")
        if len(failed_files) > 10:
            print(f"  ... and {len(failed_files) - 10} more")
    
    # Prepare ZIP statistics
    zip_stats = {
        'total_zips': len(zip_file_map),
        'successful_zips': extracted_zip_count,
        'failed_zips': failed_zips,
        'failed_zip_details': failed_zip_details
    }
    
    return extracted_zip_count, skipped_count, failed_files, zip_stats