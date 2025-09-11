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

def search_sentinel1_acquisitions(aoi_wkt, start_date, end_date, orbit_dir):
    """
    Search Sentinel-1 SLC acquisitions for a given AOI, date range, and orbit direction.

    Args:
        aoi_wkt (str): AOI in WKT format.
        start_date (str): Start date in 'YYYY-MM-DD' format.
        end_date (str): End date in 'YYYY-MM-DD' format.
        orbit_dir (str): 'ASCENDING' or 'DESCENDING'.

    Returns:
        list of dict: Each dict contains 'path', 'frame', 'num_acquisitions', 'geometry', 'percent_coverage', 'urls'
    """
    INTERNAL.CMR_TIMEOUT = 120

    try:
        results = asf.geo_search(
            platform=asf.PLATFORM.SENTINEL1,
            processingLevel=asf.PRODUCT_TYPE.SLC,
            beamMode=asf.BEAMMODE.IW,
            intersectsWith=aoi_wkt,
            start=start_date,
            end=end_date,
            flightDirection=orbit_dir.upper(),
            maxResults=10000,
        )
    except asf.ASFSearchError as e:
        print(f"ASF Search Error: {e}")
        return []
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
            frame_dict[key].append((acq_date, url))
            if url:  # Only add size if URL is valid (i.e., acquisition is downloadable)
                size_dict[key] += size
            if key not in geometry_dict:
                geometry_dict[key] = result.geometry

    aoi_geom = wkt_loads(aoi_wkt)
    summary = []
    for (path, frame), date_url_list in frame_dict.items():
        unique_dates = set(date for date, _ in date_url_list)
        urls = [url for _, url in date_url_list if url]
        geom = shape(geometry_dict[(path, frame)])
        intersection = aoi_geom.intersection(geom)
        percent_coverage = (intersection.area / aoi_geom.area) * 100 if aoi_geom.area > 0 else 0
        summary.append({
            "path": path,
            "frame": frame,
            "num_acquisitions": len(unique_dates),
            "geometry": geometry_dict[(path, frame)],
            "percent_coverage": percent_coverage,
            "urls": urls,
            "total_expected_size": size_dict[(path, frame)],
        })

    summary = sorted(
        summary,
        key=lambda x: (x["percent_coverage"], x["num_acquisitions"]),
        reverse=True
    )[:3]
        
    return summary

def download_sentinel1_acquisitions(urls, outputdir, total_expected_size,
                                    progress_callback=None,
                                    pause_event=None):
    """
    Download all Sentinel-1 acquisitions from the provided list of URLs using Earthdata authentication.

    Args:
        urls (list): List of download URLs.
        outputdir (str): Directory to save downloaded files.
    """
    cookie_jar_path = os.path.join(os.path.expanduser('~'), ".bulk_download_cookiejar.txt")
    cookie_jar = MozillaCookieJar()

    def check_cookie():
        if not cookie_jar:
            return False
        file_check = 'https://urs.earthdata.nasa.gov/profile'
        opener = build_opener(
            HTTPCookieProcessor(cookie_jar),
            HTTPHandler(),
            HTTPSHandler()
        )
        install_opener(opener)
        request = Request(file_check)
        request.get_method = lambda: 'HEAD'
        try:
            response = urlopen(request, timeout=30)
            if response.getcode() in (200, 307):
                cookie_jar.save(cookie_jar_path)
                return True
        except Exception:
            return False
        return False

    def get_cookie():
        if os.path.isfile(cookie_jar_path):
            cookie_jar.load(cookie_jar_path)
            if check_cookie():
                print(" > Reusing previous cookie jar.")
                return
            else:
                print(" > Could not validate old cookie jar")
        print("No existing URS cookie found, please enter Earthdata username & password:")
        while not check_cookie():
            class LoginDialog(simpledialog.Dialog):
                def body(self, master):
                    tk.Label(master, text="Username:").grid(row=0, sticky="e")
                    tk.Label(master, text="Password:").grid(row=1, sticky="e")
                    self.username_entry = tk.Entry(master)
                    self.password_entry = tk.Entry(master, show="*")
                    self.username_entry.grid(row=0, column=1)
                    self.password_entry.grid(row=1, column=1)
                    return self.username_entry

                def apply(self):
                    self.result = (
                        self.username_entry.get(),
                        self.password_entry.get()
                    )

            root = tk.Tk()
            root.withdraw()
            dialog = LoginDialog(root, title="Earthdata Login")
            if dialog.result:
                username, password = dialog.result
            else:
                raise Exception("Login cancelled by user.")
            auth_cookie_url = (
                "https://urs.earthdata.nasa.gov/oauth/authorize"
                "?client_id=BO_n7nTIlMljdvU6kRRB3g"
                "&redirect_uri=https://auth.asf.alaska.edu/login"
                "&response_type=code&state="
            )
            user_pass = base64.b64encode(f"{username}:{password}".encode("utf-8")).decode("utf-8")
            opener = build_opener(HTTPCookieProcessor(cookie_jar), HTTPHandler(), HTTPSHandler())
            request = Request(auth_cookie_url, headers={"Authorization": f"Basic {user_pass}"})
            try:
                opener.open(request)
            except Exception:
                pass

    # ...existing code...
    def download_file(url, idx):
        filename = os.path.basename(url).split('?')[0]
        outpath = os.path.join(outputdir, filename)
        if os.path.isfile(outpath):
            print(f" > File {outpath} exists, skipping.")
            return
        try:
            request = Request(url)
            response = urlopen(request, timeout=60)
            with open(outpath, "wb") as f:
                bytes_downloaded = 0
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    f.write(chunk)
                    bytes_downloaded += len(chunk)
                    with lock:
                        download_sizes[idx - 1] = bytes_downloaded
                    # Call progress_callback if provided
                    if progress_callback:
                        progress_callback(idx, total, bytes_downloaded)
            print(f" > Downloaded {outpath}")
        except HTTPError as e:
            print(f"HTTP Error: {e.code}, {url}")
        except URLError as e:
            print(f"URL Error: {e.reason}, {url}")
        except Exception as e:
            print(f"Error: {e}, {url}")
    # ...existing code...

    os.makedirs(outputdir, exist_ok=True)
    get_cookie()
    total = len(urls)

    def threaded_download(url, idx):
        download_file(url, idx, pause_event=pause_event)

    start_time = time.time()
    download_sizes = [0] * total
    lock = threading.Lock()

    def download_file(url, idx, pause_event=None):
        filename = os.path.basename(url).split('?')[0]
        outpath = os.path.join(outputdir, filename)
        if os.path.isfile(outpath):
            print(f" > File {outpath} exists, skipping.")
            return
        try:
            request = Request(url)
            response = urlopen(request, timeout=60)
            with open(outpath, "wb") as f:
                bytes_downloaded = 0
                start_time = time.time()
                while True:
                    # Respect pause
                    if pause_event and pause_event.is_set():
                        time.sleep(0.2)
                        continue

                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    f.write(chunk)
                    bytes_downloaded += len(chunk)
                    with lock:
                        download_sizes[idx - 1] = bytes_downloaded

                    # Build stats dict
                    elapsed = time.time() - start_time
                    total_downloaded = sum(download_sizes)
                    mean_speed = total_downloaded / elapsed if elapsed > 0 else 0
                    percent_complete = (
                        total_downloaded / total_expected_size * 100
                        if total_expected_size > 0 else 0
                    )
                    eta = (
                        (total_expected_size - total_downloaded) / mean_speed
                        if mean_speed > 0 else float("inf")
                    )

                    stats = {
                        "elapsed": elapsed,
                        "total_downloaded": total_downloaded,
                        "mean_speed": mean_speed,
                        "percent_complete": percent_complete,
                        "eta_seconds": eta,
                        "current_speed": bytes_downloaded / elapsed if elapsed > 0 else 0,
                    }

                    if progress_callback:
                        progress_callback(stats)
            print(f" > Downloaded {outpath}")
        except Exception as e:
            print(f"Error: {e}, {url}")



    def get_download_stats():
        elapsed = time.time() - start_time
        with lock:
            total_downloaded = sum(download_sizes)

        mean_speed = total_downloaded / elapsed if elapsed > 0 else 0
        percent_complete = (total_downloaded / total_expected_size * 100) if total_expected_size > 0 else 0
        eta = (total_expected_size - total_downloaded) / mean_speed if mean_speed > 0 else float('inf')

        stats = {
            "elapsed": elapsed,
            "total_downloaded": total_downloaded,
            "mean_speed": mean_speed,
            "percent_complete": percent_complete,
            "eta_seconds": eta,
        }
        return stats

    speed_window = []

    # Use ThreadPoolExecutor to run downloads in parallel threads
    def stats_printer():        
        stats = get_download_stats()
        now = time.time()
        with lock:
            speed_window.append((now, sum(download_sizes)))
            # Keep only last 5 seconds
            speed_window[:] = [(t, b) for t, b in speed_window if now - t <= 5]
        
        if len(speed_window) >= 2:
            t0, b0 = speed_window[0]
            t1, b1 = speed_window[-1]
            current_speed = (b1 - b0) / (t1 - t0) if (t1 - t0) > 0 else 0
            stats["current_speed"] = current_speed
        else:
            stats["current_speed"] = stats["mean_speed"]  # fallback

        if progress_callback:
            progress_callback(stats)
        time.sleep(1)

    # Final update
    stats = get_download_stats()
    if progress_callback:
        progress_callback(stats)

    
    printer_thread = threading.Thread(target=stats_printer)
    printer_thread.start()

    with ThreadPoolExecutor(max_workers=min(8, total)) as executor:
        futures = []
        for idx, url in enumerate(urls, 1):
            futures.append(executor.submit(threaded_download, url, idx))
        for future in futures:
            future.result()
    
    printer_thread.join()
    # After downloads, return final stats
    stats = get_download_stats()
    return stats
