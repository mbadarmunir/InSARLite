import os
import shutil
import base64
import tkinter as tk
from tkinter import simpledialog
from datetime import datetime
from collections import defaultdict
from urllib.request import (
    build_opener, install_opener, Request, urlopen,
    HTTPCookieProcessor, HTTPHandler, HTTPSHandler
)
from urllib.error import HTTPError, URLError
from http.cookiejar import MozillaCookieJar
from shapely.wkt import loads as wkt_loads
from shapely.geometry import shape
import asf_search as asf
from asf_search.constants import INTERNAL
import threading
from concurrent.futures import ThreadPoolExecutor
import time
from ..utils.earthdata_auth import setup_asf_auth, ensure_earthdata_auth, get_earthdata_session

def search_sentinel1_acquisitions(aoi_wkt, start_date, end_date, orbit_dir):
    """
    Search Sentinel-1 SLC acquisitions for a given AOI, date range, and orbit direction
    using unified EarthData authentication.

    Args:
        aoi_wkt (str): AOI in WKT format.
        start_date (str): Start date in 'YYYY-MM-DD' format.
        end_date (str): End date in 'YYYY-MM-DD' format.
        orbit_dir (str): 'ASCENDING' or 'DESCENDING'.

    Returns:
        dict: Dictionary with (path, frame) as keys and lists of (date, url, size) as values.
    """
    # Ensure EarthData authentication for ASF search
    if not ensure_earthdata_auth():
        raise Exception("Could not authenticate with EarthData for Sentinel-1 search")
    
    # Setup ASF authentication
    if not setup_asf_auth():
        print("⚠ Warning: Could not setup ASF authentication, continuing anyway...")

    try:
        query_end_date = end_date
        if end_date == 'today':
            query_end_date = datetime.today().strftime('%Y-%m-%d')
    except Exception:
        query_end_date = end_date  # Fallback if date parsing fails

    try:
        print(f"🔍 Searching Sentinel-1 data for {orbit_dir.upper()} orbit...")
        results = asf.geo_search(
            platform=asf.PLATFORM.SENTINEL1,
            processingLevel=asf.PRODUCT_TYPE.SLC,
            beamMode=asf.BEAMMODE.IW,
            intersectsWith=aoi_wkt,
            start=start_date,
            end=query_end_date,
            flightDirection=orbit_dir.upper(),
            maxResults=10000,
        )
        print(f"✓ Found {len(results)} Sentinel-1 acquisitions")
    except asf.ASFSearchError as e:
        print(f"❌ ASF Search Error: {e}")
        print("This may be due to authentication issues or network connectivity")
        return {}
    except Exception as e:
        print(f"❌ Unexpected search error: {e}")
        return {}
    frame_dict = defaultdict(list)
    geometry_dict = {}
    size_dict = defaultdict(int)

    for result in results:
        props = result.properties
        path = props.get("pathNumber")
        frame = props.get("frameNumber")
        size = props.get("bytes") or 0  # Ensure size is not None        
        acq_date = datetime.strptime(props["startTime"].split("T")[0], "%Y-%m-%d").date()
        url = props.get("url", getattr(result, "download_url", None))
        if path is not None and frame is not None:
            key = (path, frame)
            frame_dict[key].append((acq_date, url, size))  # Include size for each file
            if url:  # Only add size if URL is valid (i.e., acquisition is downloadable)
                size_dict[key] += size
            if key not in geometry_dict:
                geometry_dict[key] = result.geometry

    aoi_geom = wkt_loads(aoi_wkt)
    summary = []
    for (path, frame), date_url_size_list in frame_dict.items():
        unique_dates = set(date for date, _, _ in date_url_size_list)
        # Create list of (url, size) tuples for files with valid URLs
        files_info = [(url, size) for _, url, size in date_url_size_list if url]
        geom = shape(geometry_dict[(path, frame)])
        intersection = aoi_geom.intersection(geom)
        percent_coverage = (intersection.area / aoi_geom.area) * 100 if aoi_geom.area > 0 else 0
        summary.append({
            "path": path,
            "frame": frame,
            "num_acquisitions": len(unique_dates),
            "geometry": geometry_dict[(path, frame)],
            "percent_coverage": percent_coverage,
            "urls": [url for url, _ in files_info],  # Keep backward compatibility
            "files_info": files_info,  # New: list of (url, size) tuples
            "total_expected_size": size_dict[(path, frame)],
        })

    summary = sorted(
        summary,
        key=lambda x: (x["percent_coverage"], x["num_acquisitions"]),
        reverse=True
    )[:3]
        
    return summary

def download_sentinel1_acquisitions(files_info, outputdir, total_expected_size,
                                    progress_callback=None,
                                    pause_event=None):
    """
    Download all Sentinel-1 acquisitions using unified EarthData authentication.

    Args:
        files_info (list): List of (url, expected_size) tuples.
        outputdir (str): Directory to save downloaded files.
        total_expected_size (int): Total expected download size in bytes.
        progress_callback (callable): Callback function for progress updates.
        pause_event (threading.Event): Event to pause downloads.
    """
    # Ensure EarthData authentication and get cached session
    if not ensure_earthdata_auth():
        raise Exception("Could not authenticate with EarthData for downloads")
    
    # Get the authenticated session once and reuse it for all downloads
    shared_session = get_earthdata_session()
    print("✓ Using unified EarthData authentication for downloads")
    
    os.makedirs(outputdir, exist_ok=True)
    total = len(files_info)

    # Shared data structures
    start_time = time.time()
    paused_time = [0]  # Track total paused time (list for closure)
    last_pause_start = [None]  # Track when current pause started (list for closure)
    download_sizes = [0] * total
    session_downloaded = [0] * total  # Track only bytes downloaded THIS session
    lock = threading.Lock()
    speed_window = []
    stats_running = True

    # Initialize download_sizes with any existing files, but don't count them for speed
    # Note: This is a rough estimate - actual verification happens in download_file()
    for idx, (url, expected_size) in enumerate(files_info):
        filename = os.path.basename(url).split('?')[0]
        outpath = os.path.join(outputdir, filename)
        if os.path.isfile(outpath):
            try:
                download_sizes[idx] = os.path.getsize(outpath)
                # session_downloaded[idx] remains 0 for existing files
            except OSError:
                download_sizes[idx] = 0

    def download_file(url, idx, expected_size):
        """Download a single file using shared authenticated session and update its progress."""
        filename = os.path.basename(url).split('?')[0]
        outpath = os.path.join(outputdir, filename)
        
        # Use the shared session instead of creating a new one each time
        session = shared_session
        
        # Check if file exists and get its current size
        existing_size = 0
        if os.path.isfile(outpath):
            try:
                existing_size = os.path.getsize(outpath)
            except OSError:
                existing_size = 0
        
        # Check if file is complete
        if existing_size > 0:
            if expected_size and existing_size == expected_size:
                # File is complete, add to progress but NOT to session download count
                with lock:
                    download_sizes[idx - 1] = existing_size
                    # session_downloaded[idx - 1] remains 0 - no new download
                print(f" > File {filename} already complete ({existing_size} bytes), skipping.")
                return
            elif not expected_size and existing_size > 1024*1024:  # File > 1MB and no expected size
                # Assume large files are likely complete if we don't know the expected size
                # This is a fallback for cases where expected_size is None/0
                print(f" > File {filename} exists ({existing_size} bytes), assuming complete (no expected size), skipping.")
                with lock:
                    download_sizes[idx - 1] = existing_size
                return
        
        # Handle partial file - try to resume if supported
        resume_pos = 0
        mode = "wb"  # Default: overwrite
        
        if existing_size > 0:
            if expected_size and existing_size < expected_size:
                # Try to resume - check if server supports it
                try:
                    # Test resume with authenticated session
                    test_response = session.get(url, headers={'Range': 'bytes=0-1'}, timeout=10)
                    if test_response.status_code == 206:  # Partial Content
                        resume_pos = existing_size
                        print(f" > Resuming {filename} from {existing_size} bytes...")
                    else:
                        print(f" > Server doesn't support resume for {filename}, restarting...")
                        os.remove(outpath)
                        existing_size = 0
                    test_response.close()
                except Exception:
                    print(f" > Resume test failed for {filename}, restarting...")
                    try:
                        os.remove(outpath)
                    except OSError:
                        pass
                    existing_size = 0
            elif expected_size and existing_size >= expected_size:
                # File is larger than expected (corrupted?), restart
                print(f" > File {filename} is larger than expected, restarting download...")
                try:
                    os.remove(outpath)
                except OSError:
                    pass
                existing_size = 0
            elif not expected_size and existing_size < 1024*1024:  # Small partial file, no expected size
                # For files smaller than 1MB with unknown expected size, try to resume
                print(f" > Attempting to resume {filename} from {existing_size} bytes (unknown expected size)...")
                try:
                    test_response = session.get(url, headers={'Range': 'bytes=0-1'}, timeout=10)
                    if test_response.status_code == 206:
                        resume_pos = existing_size
                    else:
                        print(f" > Server doesn't support resume for {filename}, restarting...")
                        os.remove(outpath)
                        existing_size = 0
                    test_response.close()
                except Exception:
                    print(f" > Resume test failed for {filename}, restarting...")
                    try:
                        os.remove(outpath)
                    except OSError:
                        pass
                    existing_size = 0
        
        # Initialize progress with existing bytes
        with lock:
            download_sizes[idx - 1] = existing_size
            session_downloaded[idx - 1] = 0  # No session download yet
        
        try:
            # Download using authenticated session
            headers = {}
            if resume_pos > 0:
                headers['Range'] = f'bytes={resume_pos}-'
            
            response = session.get(url, headers=headers, timeout=60, stream=True)
            response.raise_for_status()
            
            # Verify resume response
            if resume_pos > 0 and response.status_code != 206:
                print(f" > Resume failed for {filename}, restarting...")
                response.close()
                os.remove(outpath)
                existing_size = 0
                resume_pos = 0
                with lock:
                    download_sizes[idx - 1] = 0
                # Retry without resume
                response = session.get(url, timeout=60, stream=True)
                response.raise_for_status()
            
            mode = "ab" if resume_pos > 0 else "wb"
            with open(outpath, mode) as f:
                bytes_downloaded = existing_size  # Start with existing bytes
                session_start_bytes = existing_size  # Track where this session started
                for chunk in response.iter_content(chunk_size=1024*1024):
                    # Respect pause
                    if pause_event and pause_event.is_set():
                        time.sleep(0.2)
                        continue
                    
                    if chunk:
                        f.write(chunk)
                        bytes_downloaded += len(chunk)
                        
                        # Update global progress tracking
                        with lock:
                            download_sizes[idx - 1] = bytes_downloaded
                            # Track only bytes downloaded in this session (excluding pre-existing)
                            session_downloaded[idx - 1] = bytes_downloaded - session_start_bytes

            # Verify final file size if we know what to expect
            if expected_size and bytes_downloaded != expected_size:
                print(f" > Warning: {filename} size mismatch. Expected: {expected_size}, Got: {bytes_downloaded}")
            else:
                print(f" > Downloaded {outpath} ({bytes_downloaded} bytes)")
                
        except Exception as e:
            # Check if this might be an authentication error
            if "401" in str(e) or "403" in str(e) or "Unauthorized" in str(e):
                print(f"🔄 Authentication error for {filename}, refreshing session...")
                try:
                    # Get a fresh session and retry once
                    session = get_earthdata_session()
                    response = session.get(url, headers=headers, timeout=60, stream=True)
                    response.raise_for_status()
                    
                    mode = "ab" if resume_pos > 0 else "wb"
                    with open(outpath, mode) as f:
                        bytes_downloaded = existing_size
                        session_start_bytes = existing_size
                        for chunk in response.iter_content(chunk_size=1024*1024):
                            if pause_event and pause_event.is_set():
                                time.sleep(0.2)
                                continue
                            
                            if chunk:
                                f.write(chunk)
                                bytes_downloaded += len(chunk)
                                
                                with lock:
                                    download_sizes[idx - 1] = bytes_downloaded
                                    session_downloaded[idx - 1] = bytes_downloaded - session_start_bytes
                    
                    print(f" > Downloaded {outpath} ({bytes_downloaded} bytes) [after retry]")
                    return
                    
                except Exception as retry_error:
                    print(f"🔄 Retry also failed for {filename}: {retry_error}")
            
            print(f"Error downloading {filename}: {e}")
            # If download failed and we were resuming, try to restart
            if resume_pos > 0 and os.path.isfile(outpath):
                print(f" > Resume failed, will retry {filename} from beginning on next attempt")

    def stats_updater():
        """Continuously update and report download statistics."""
        while stats_running:
            current_time = time.time()
            
            if pause_event and pause_event.is_set():
                # Track pause start time if not already tracking
                if not last_pause_start:
                    last_pause_start[0] = current_time
                time.sleep(0.5)
                continue
            else:
                # If we were paused and now resumed, add to total pause time
                if last_pause_start[0] is not None:
                    paused_time[0] += current_time - last_pause_start[0]
                    last_pause_start[0] = None
                
            # Calculate elapsed time excluding pauses
            elapsed = current_time - start_time - paused_time[0]
            with lock:
                total_downloaded = sum(download_sizes)
                session_bytes_downloaded = sum(session_downloaded)  # Only bytes downloaded THIS session
                # Update speed window for current speed calculation using session bytes only
                now = time.time()
                speed_window.append((now, session_bytes_downloaded))
                # Keep only last 5 seconds for more stable current speed
                speed_window[:] = [(t, b) for t, b in speed_window if now - t <= 5]

            # Calculate average speed using only session downloads (excluding pre-existing files)
            mean_speed = session_bytes_downloaded / elapsed if elapsed > 0 else 0
            
            # Calculate current speed from sliding window with smoothing
            if len(speed_window) >= 2:
                t0, b0 = speed_window[0]
                t1, b1 = speed_window[-1]
                current_speed = (b1 - b0) / (t1 - t0) if (t1 - t0) > 0 else 0
                
                # Apply smoothing for more stable display
                if hasattr(stats_updater, 'last_current_speed'):
                    current_speed = 0.7 * stats_updater.last_current_speed + 0.3 * current_speed
                stats_updater.last_current_speed = current_speed
            else:
                current_speed = mean_speed
                if not hasattr(stats_updater, 'last_current_speed'):
                    stats_updater.last_current_speed = current_speed

            # Calculate other statistics
            percent_complete = (total_downloaded / total_expected_size * 100) if total_expected_size > 0 else 0
            # Calculate ETA based on remaining bytes that still need to be downloaded
            remaining_bytes = total_expected_size - total_downloaded
            eta = remaining_bytes / current_speed if current_speed > 0 and remaining_bytes > 0 else 0

            stats = {
                "elapsed": elapsed,
                "total_downloaded": total_downloaded,
                "session_downloaded": session_bytes_downloaded,  # Add this for debugging
                "total_expected_size": total_expected_size,
                "mean_speed": mean_speed,
                "current_speed": current_speed,
                "percent_complete": percent_complete,
                "eta_seconds": eta,
            }

            if progress_callback:
                progress_callback(stats)
            
            time.sleep(1.0)  # Update once per second for stable progress

    # Start statistics updater thread
    stats_thread = threading.Thread(target=stats_updater, daemon=True)
    stats_thread.start()

    # Use ThreadPoolExecutor to run downloads in parallel
    with ThreadPoolExecutor(max_workers=min(8, total)) as executor:
        futures = []
        for idx, (url, expected_size) in enumerate(files_info, 1):
            futures.append(executor.submit(download_file, url, idx, expected_size))
        
        # Wait for all downloads to complete
        for future in futures:
            future.result()

    # Stop stats updater and provide final update
    stats_running = False
    stats_thread.join(timeout=1)
    
    # Final statistics
    elapsed = time.time() - start_time
    with lock:
        total_downloaded = sum(download_sizes)
        session_bytes_downloaded = sum(session_downloaded)
    
    final_stats = {
        "elapsed": elapsed,
        "total_downloaded": total_downloaded,
        "session_downloaded": session_bytes_downloaded,
        "total_expected_size": total_expected_size,
        "mean_speed": session_bytes_downloaded / elapsed if elapsed > 0 else 0,  # Use session bytes for speed
        "current_speed": 0,  # Download complete
        "percent_complete": 100.0,
        "eta_seconds": 0,
    }
    
    if progress_callback:
        progress_callback(final_stats)
    
    return final_stats
