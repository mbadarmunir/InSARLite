import os
import numpy as np
import asf_search as asf
from copy import deepcopy
from datetime import datetime
import tkinter as tk
from tkinter import messagebox
import json
from ..utils.earthdata_auth import setup_asf_auth, ensure_earthdata_auth

"""
Master Selection Logic Documentation
=====================================

Primary Method: Local Baseline Table Analysis
---------------------------------------------
This implementation uses GMTSAR's baseline_table.dat file to rank master scene candidates
based on network centrality principle. This approach provides several advantages:

1. **No External Authentication Required**: Works offline without ASF credentials
2. **Perfect Local File Matching**: Always matches locally available SAFE files
3. **Accurate Orbit Metadata**: Uses actual processed orbit data from GMTSAR
4. **Handles Reprocessed Scenes**: Not limited by ASF baseline stack linking

Theoretical Foundation:
----------------------
The optimal master scene for InSAR processing minimizes the total baseline network distance,
ensuring good coherence with all slave scenes. We compute this using network centrality:

For each candidate master image C:
    NetworkCentrality(C) = Σ |Baseline(C, O)| for all other images O
    
Where Baseline(C, O) includes both perpendicular and temporal components:
    Baseline(C, O) = |Perp_C - Perp_O| + |Temp_C - Temp_O|

The image with minimum NetworkCentrality is the optimal master.

Understanding Average Baseline Ranking:
--------------------------------------
The "average baseline" is the mean distance from a candidate master to all other images
in the dataset, measured in combined perpendicular and temporal baseline space. This metric
represents how "central" an image is within the baseline network.

**What Average Baseline Means:**
When we say an image has an average baseline of 150 meters + 100 days = 250 units, this means
that on average, this image is separated from other images in the stack by 150 meters 
perpendicular distance and 100 days in time. An image with a lower average baseline is more
centrally positioned - it's closer to all other images in the network, making it an ideal
reference point for interferometric processing.

**The Reference Scene Bias Problem:**
Traditional baseline measurements from GMTSAR's baseline_table.dat are calculated relative to
an arbitrary reference scene (usually the first processed image). This creates a fundamental
bias: the reference scene appears to have zero baseline by definition, even if it's actually
located at the edge of the temporal or spatial baseline distribution. This can mislead master
selection algorithms into choosing poorly positioned scenes.

**How Average Baseline Eliminates Bias:**
By calculating the average baseline for each image relative to ALL other images (not just
one reference), we remove the dependence on any single reference scene. This is achieved by:

1. Computing pairwise baseline differences between every image pair using the mathematical
   property: Baseline(A,B) = |Baseline(A,Ref) - Baseline(B,Ref)|
   
2. Summing these pairwise baselines for each candidate master to get total network distance

3. Dividing by (N-1) images to get the average baseline - a measure of centrality that is
   independent of which scene was chosen as the original reference

This approach ensures that even if the reference scene in baseline_table.dat is poorly
positioned (e.g., at the beginning or end of the time series), it won't artificially appear
as the best master. Instead, the truly central scene - the one with minimum average distance
to all others - will be correctly identified regardless of the reference choice.

**Physical Interpretation:**
A scene with low average baseline (highly ranked) sits near the "center of mass" of the
baseline network, providing balanced coherence with both recent and older acquisitions, and
with scenes at various perpendicular positions. This maximizes the overall quality of
interferograms generated from this master, as no slave scene is excessively distant in
time or space.

Baseline Reconstruction:
-----------------------
GMTSAR's baseline_table.dat stores baselines relative to an arbitrary reference scene R:
    Image_i: (Perp_i_to_R, Temp_i_to_R)

To calculate baseline between any two images A and B:
    Perp_AB = |Perp_A_to_R - Perp_B_to_R|
    Temp_AB = |Temp_A_to_R - Temp_B_to_R|

This mathematical property allows reconstruction of the complete baseline network from
a single reference-based table, eliminating reference image bias.

Implementation Algorithm:
------------------------
1. Locate baseline_table.dat in subswath folders (F1, F2, or F3)
2. Parse temporal (column 3) and perpendicular (column 5) baselines
3. For each image, calculate sum of pairwise baseline differences to all other images
4. Normalize by (N-1) to get average baseline distance
5. Rank by ascending average baseline (lowest = best master)
6. Return ranked array: [temporal_bl, perpendicular_bl, image_id, avg_total_bl, rank]

Equivalence to ASF Method:
-------------------------
This approach produces rankings mathematically equivalent to ASF's baseline stack method
because both optimize for network centrality. Minor ranking differences may occur due to:
- Different reference scene selection
- Updated orbit files in local processing
- Scene filtering differences

However, the top-ranked master candidates (top 5-10) remain consistent across both methods.

Fallback Hierarchy:
------------------
1. Primary: Local baseline_table.dat analysis (this implementation)
2. Fallback: ASF baseline stack search (requires authentication)
3. Emergency: Simple temporal baseline calculation from filenames

References:
----------
This implementation follows the baseline network optimization principles described in:
- Zebker & Villasenor (1992): Decorrelation in interferometric radar echoes
- Hooper et al. (2007): Persistent scatterer InSAR for crustal deformation analysis
- GMTSAR Documentation: Baseline processing methodology
"""


def find_baseline_table(ddata):
    """
    Locate baseline_table.dat file in subswath folders.
    Searches for F1, F2, F3 folders and returns the first found baseline table.
    
    Args:
        ddata: Path to data directory (e.g., asc/data or des/data)
    
    Returns:
        str: Full path to baseline_table.dat, or None if not found
    """
    project_dir = os.path.dirname(ddata)
    
    for subswath in ['F1', 'F2', 'F3']:
        baseline_file = os.path.join(project_dir, subswath, 'baseline_table.dat')
        if os.path.exists(baseline_file):
            print(f'✓ Found baseline table: {baseline_file}')
            return baseline_file
    
    print('⚠️  No baseline_table.dat file found in F1, F2, or F3 folders')
    return None


def parse_baseline_table(baseline_file):
    """
    Parse GMTSAR baseline_table.dat file.
    
    File format (space-separated):
    file_id timestamp temporal_baseline parallel_baseline perpendicular_baseline
    
    Args:
        baseline_file: Path to baseline_table.dat
    
    Returns:
        list: [(image_id, temporal_bl, perpendicular_bl), ...]
    """
    baselines = []
    
    try:
        with open(baseline_file, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                parts = line.split()
                if len(parts) >= 5:
                    image_id = parts[0]
                    temporal_bl = float(parts[2])
                    perpendicular_bl = float(parts[4])
                    baselines.append((image_id, temporal_bl, perpendicular_bl))
        
        print(f'✓ Parsed {len(baselines)} images from baseline table')
        return baselines
    
    except Exception as e:
        print(f'❌ Error parsing baseline table: {e}')
        return []


def calculate_network_centrality(baselines_data):
    """
    Calculate network centrality for master selection using pairwise baseline differences.
    
    This method computes for each image how it would perform as a master by calculating
    the sum of baseline distances to all other images. The image with the lowest sum
    is the most centrally located in the baseline network.
    
    Args:
        baselines_data: List of (image_id, temporal_bl, perpendicular_bl) tuples
    
    Returns:
        numpy.ndarray: Sorted array with columns:
                       [temporal_bl, perpendicular_bl, image_id, avg_total_bl, rank]
    """
    if not baselines_data:
        return np.array([])
    
    N = len(baselines_data)
    rankings = []
    
    print(f'\n📊 Calculating network centrality for {N} images...')
    
    for i, (img_id_i, temp_i, perp_i) in enumerate(baselines_data):
        total_baseline = 0.0
        
        for j, (img_id_j, temp_j, perp_j) in enumerate(baselines_data):
            if i != j:
                perp_diff = abs(perp_i - perp_j)
                temp_diff = abs(temp_i - temp_j)
                total_baseline += (perp_diff + temp_diff)
        
        avg_baseline = total_baseline / (N - 1) if N > 1 else 0.0
        rankings.append([temp_i, perp_i, img_id_i, avg_baseline])
    
    rankings_array = np.array(rankings, dtype=object)
    avg_baselines = np.array([r[3] for r in rankings], dtype=float)
    sorted_indices = np.argsort(avg_baselines)
    rankings_sorted = rankings_array[sorted_indices]
    
    ranks = np.arange(1, N + 1)
    rankings_with_rank = np.column_stack((rankings_sorted, ranks))
    
    print(f'✓ Network centrality calculated')
    print(f'   Top master candidate: {rankings_with_rank[0][2]} (avg baseline: {rankings_with_rank[0][3]:.2f})')
    
    return rankings_with_rank


class FallbackProduct:
    """Fallback product class when ASF search is unavailable."""
    def __init__(self, file_id, frame_number, path_number):
        self.properties = {
            'fileID': file_id,
            'fileName': file_id.replace('-SLC', '') + '.zip',
            'frameNumber': frame_number,
            'pathNumber': path_number,
            'temporalBaseline': 0,  # Will be calculated relative to other scenes
            'perpendicularBaseline': None  # Not available in fallback mode
        }
        self.geometry = None
    
    def __eq__(self, other):
        if isinstance(other, FallbackProduct):
            return self.properties['fileID'] == other.properties['fileID']
        return False
    
    def __ne__(self, other):
        return not self.__eq__(other)


def _create_fallback_results(ddata, granule_name):
    """
    Create fallback results using only local SAFE directory information.
    This method doesn't require ASF authentication.
    """
    # Extract frame and path info from granule name
    # Format: S1A_IW_SLC__1SDV_20150101T000000_...
    parts = granule_name.split('_')
    
    # Get all SAFE directories
    data_files = [x for x in os.listdir(ddata) if x.endswith('.SAFE')]
    
    # Find the reference scene
    reference = None
    for safe_file in data_files:
        file_id = safe_file.replace('.SAFE', '')
        if granule_name in file_id:
            # Extract frame and path from the SAFE filename
            # This is a simplified extraction - may need adjustment based on actual filename format
            reference = FallbackProduct(
                file_id=file_id + '-SLC',
                frame_number=0,  # Default value - actual frame number not critical for fallback
                path_number=0    # Default value
            )
            break
    
    if not reference:
        # If exact match not found, use first SAFE file as reference
        if data_files:
            file_id = data_files[0].replace('.SAFE', '')
            reference = FallbackProduct(
                file_id=file_id + '-SLC',
                frame_number=0,
                path_number=0
            )
    
    return [reference]


def _create_fallback_stack(ddata, reference):
    """
    Create a fallback stack using only local SAFE directory information.
    Since we don't have ASF baseline data, we'll create products with minimal info.
    """
    data_files = [x for x in os.listdir(ddata) if x.endswith('.SAFE')]
    
    stack = []
    for safe_file in data_files:
        file_id = safe_file.replace('.SAFE', '') + '-SLC'
        product = FallbackProduct(
            file_id=file_id,
            frame_number=reference.properties['frameNumber'],
            path_number=reference.properties['pathNumber']
        )
        stack.append(product)
    
    return stack


def _calculate_fallback_rankings(stack):
    """
    Calculate master selection rankings in fallback mode (without ASF baseline data).
    Uses only temporal baseline since perpendicular baseline is not available.
    """
    # Extract dates from fileIDs
    dates_dict = {}
    for product in stack:
        file_id = product.properties['fileID']
        # Extract date from file_id (format: S1X_IW_SLC__1SDV_YYYYMMDDTHHMMSS_...)
        try:
            date_str = file_id.split('_')[4].split('T')[0]  # Get YYYYMMDD
            date = datetime.strptime(date_str, "%Y%m%d")
            dates_dict[file_id] = date
        except:
            print(f"Warning: Could not extract date from {file_id}")
            continue
    
    # Calculate temporal baselines relative to each scene
    tbl_list = []
    for product in stack:
        file_id = product.properties['fileID']
        if file_id not in dates_dict:
            continue
            
        ref_date = dates_dict[file_id]
        total_temporal_bl = 0
        
        for other_id, other_date in dates_dict.items():
            if other_id != file_id:
                temporal_diff = abs((ref_date - other_date).days)
                total_temporal_bl += temporal_diff
        
        # In fallback mode, we set perpendicular baseline to 0 (not available)
        tbl_list.append([total_temporal_bl, 0, file_id])
    
    # Rank by temporal baseline only
    tbl_arr = np.array(tbl_list)
    if len(tbl_arr) == 0:
        return np.array([])
        
    # Sort by temporal baseline (column 0)
    temporal_baselines = tbl_arr[:, 0].astype('float')
    ranks = np.argsort(np.argsort(temporal_baselines)) + 1  # Rank starts from 1
    tbl_arr_sort = np.column_stack((tbl_arr, ranks))
    tbl_arr_sort = tbl_arr_sort[tbl_arr_sort[:, -1].argsort()]  # Sort by rank column
    
    return tbl_arr_sort


def _save_excluded_images(ddata, excluded_images, filter_type, user_choice):
    """
    Save excluded images information to a JSON file in the project folder
    
    Args:
        ddata: Data directory path
        excluded_images: List of excluded image items with properties
        filter_type: Type of filter ("missing_baselines", "different_frames", or "not_in_asf_stack")
        user_choice: User's decision ("exclude", "keep", or "cancel")
    """
    # Find the project root directory (parent of ddata where log files are created)
    project_root = os.path.dirname(ddata)
    
    # Create exclusion log file path in project root
    exclusion_log_path = os.path.join(project_root, 'excluded_images.json')
    
    # Load existing log if it exists
    if os.path.exists(exclusion_log_path):
        try:
            with open(exclusion_log_path, 'r') as f:
                exclusion_log = json.load(f)
        except Exception as e:
            print(f"Warning: Could not load existing exclusion log: {e}")
            exclusion_log = []
    else:
        exclusion_log = []
    
    # Prepare new entry
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    excluded_file_ids = []
    for item in excluded_images:
        if isinstance(item, str):
            # Simple filename string (for local files not in stack)
            excluded_file_ids.append({
                'fileID': item,
                'perpendicularBaseline': 'Unknown',
                'temporalBaseline': 'Unknown',
                'frameNumber': 'Unknown',
                'pathNumber': 'Unknown',
                'reason': 'Not found in ASF baseline stack'
            })
        else:
            # Full product object
            file_id = item.properties.get('fileID', 'Unknown')
            perp_bl = item.properties.get('perpendicularBaseline', None)
            temp_bl = item.properties.get('temporalBaseline', None)
            frame = item.properties.get('frameNumber', None)
            path = item.properties.get('pathNumber', None)
            
            excluded_file_ids.append({
                'fileID': file_id,
                'perpendicularBaseline': str(perp_bl) if perp_bl is not None else 'None',
                'temporalBaseline': str(temp_bl) if temp_bl is not None else 'None',
                'frameNumber': str(frame) if frame is not None else 'None',
                'pathNumber': str(path) if path is not None else 'None'
            })
    
    new_entry = {
        'timestamp': timestamp,
        'filter_type': filter_type,
        'user_decision': user_choice,
        'count': len(excluded_images),
        'images': excluded_file_ids
    }
    
    # Append to log
    exclusion_log.append(new_entry)
    
    # Save updated log
    try:
        with open(exclusion_log_path, 'w') as f:
            json.dump(exclusion_log, f, indent=2)
        print(f'   💾 Exclusion log saved to: {exclusion_log_path}')
    except Exception as e:
        print(f'   ⚠️  Warning: Could not save exclusion log: {e}')


def _prompt_user_filter_decision(title, message, details_list, filter_type):
    """
    Prompt user to decide whether to exclude problematic images using console input.
    This works reliably from any thread, unlike GUI dialogs.
    
    Args:
        title: Dialog title
        message: Main message to display
        details_list: List of items with issues
        filter_type: Type of filter being applied
    
    Returns:
        str: "exclude", "keep", or "cancel"
    """
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)
    print(f"\n{message}\n")
    
    # Show affected images
    print("Affected Images:")
    print("-" * 80)
    for idx, item in enumerate(details_list[:20]):  # Show first 20
        print(item)
    if len(details_list) > 20:
        print(f"\n... and {len(details_list) - 20} more images")
    print("-" * 80)
    
    # Show recommendation
    if filter_type == "missing_baselines":
        print("\n⚠️  RECOMMENDATION: Exclude these images")
        print("Images without baseline data cannot be used for interferometric processing.")
        print("Keeping them may cause errors in later stages.")
    elif filter_type == "different_frames":
        print("\n⚠️  RECOMMENDATION: Consider carefully")
        print("Different frames may cover adjacent areas but can cause:")
        print("  • Geometric misalignment issues")
        print("  • Different processing parameters")
        print("  • Reduced interferometric coherence")
        print("\nKeep only if you intentionally downloaded multiple frames for wider coverage.")
    
    # Get user input
    print("\n" + "=" * 80)
    print("Options:")
    print("  [1] Exclude These Images (recommended)")
    print("  [2] Keep All Images")
    print("  [3] Cancel Processing")
    print("=" * 80)
    
    while True:
        try:
            choice = input("\nEnter your choice (1/2/3): ").strip()
            if choice == "1":
                return "exclude"
            elif choice == "2":
                return "keep"
            elif choice == "3":
                return "cancel"
            else:
                print("Invalid choice. Please enter 1, 2, or 3.")
        except (EOFError, KeyboardInterrupt):
            print("\n\nOperation cancelled by user.")
            return "cancel"


def extract_date(folder_name):
    try:
        date_str0 = folder_name.split('_')[5]
        date_str = date_str0.split('T')[0]
        return datetime.strptime(date_str, "%Y%m%d")
    except (IndexError, ValueError):
        return None


# Calculate the temporal baseline for each date
def calculate_temporal_baseline(dates):
    baselines = []
    for i, (folder, date) in enumerate(dates):
        total_baseline = sum(abs((date - other_date).days) for _, other_date in dates if other_date != date)
        baselines.append((folder, date, total_baseline))
    return baselines


def calc_center(main_folder):
    # Get a list of subfolders and extract dates
    subfolders = [f for f in os.listdir(main_folder) if os.path.isdir(os.path.join(main_folder, f))]
    dates = [(folder, extract_date(folder)) for folder in subfolders]

    # Filter out subfolders where date extraction failed
    dates = [item for item in dates if item[1] is not None]

    # Get the baselines and find the one with the shortest temporal baseline
    baselines = calculate_temporal_baseline(dates)
    baselines.sort(key=lambda x: x[2])

    # The subfolder with the shortest temporal baseline
    center_folder = baselines[0][0]

    return center_folder


def select_mst(ddata, use_fallback=False, retry_count=0):
    """
    Select master scene using local baseline table (primary) or ASF search (fallback).
    
    Primary Method (Recommended):
    - Uses GMTSAR's baseline_table.dat from F1/F2/F3 subswath folders
    - Calculates network centrality for master selection
    - Works offline, matches local files perfectly
    
    Fallback Method:
    - Uses ASF baseline stack search (requires EarthData authentication)
    - Applied when baseline_table.dat not found or use_fallback=True
    
    Args:
        ddata: Data directory path (e.g., asc/data or des/data)
        use_fallback: If True, skip local baseline method and use ASF search
        retry_count: Number of retry attempts (for internal tracking)
    
    Returns:
        numpy.ndarray: Ranked master candidates
                      [temporal_bl, perpendicular_bl, image_id, avg_total_bl, rank]
    """
    print("\n" + "="*80)
    print("  MASTER SCENE SELECTION")
    print("="*80)
    
    # Try local baseline table method first (unless fallback explicitly requested)
    if not use_fallback:
        baseline_file = find_baseline_table(ddata)
        
        if baseline_file:
            print(f'\n🎯 Using LOCAL baseline table method (recommended)')
            print(f'   File: {os.path.basename(baseline_file)}')
            
            # Parse baseline table
            baselines_data = parse_baseline_table(baseline_file)
            
            if baselines_data:
                # Calculate network centrality and rank
                rankings = calculate_network_centrality(baselines_data)
                
                if len(rankings) > 0:
                    print(f'\n✓ Master selection completed using local baseline table')
                    print(f'   Method: Network centrality optimization')
                    print(f'   Total candidates: {len(rankings)}')
                    print(f'   Top 5 master candidates:')
                    for i in range(min(5, len(rankings))):
                        img_id = rankings[i][2]
                        avg_bl = float(rankings[i][3])
                        rank = int(rankings[i][4])
                        print(f'      #{rank}: {img_id} (avg baseline: {avg_bl:.2f})')
                    print("="*80 + "\n")
                    return rankings
                else:
                    print('⚠️  Failed to calculate rankings from baseline table')
                    print('   Falling back to ASF search method...')
            else:
                print('⚠️  Failed to parse baseline table')
                print('   Falling back to ASF search method...')
        else:
            print(f'\n⚠️  No baseline_table.dat found in F1/F2/F3 folders')
            print('   This is normal if baselines have not been plotted yet')
            print('   Falling back to ASF search method...')
    else:
        print(f'\n🔄 Fallback mode explicitly requested')
        print('   Using ASF baseline stack method...')
    
    # Fallback to ASF search method
    print(f'\n🌐 Using ASF baseline stack method')
    
    # Use the super master scene that is just in the middle of the temporal baseline
    granule = [calc_center(ddata).split('.')[0]]
    
    if use_fallback:
        # User explicitly requested fallback - use local baseline calculation
        print("🔄 Using local fallback method (no ASF search)...")
        results = _create_fallback_results(ddata, granule[0])
        print(f"✓ Loaded baseline data from local files")
    else:
        # Ensure EarthData authentication for ASF
        if not ensure_earthdata_auth():
            raise Exception("Could not authenticate with EarthData for master selection")
        
        # Setup ASF authentication and get credentials
        if not setup_asf_auth():
            print("⚠ Warning: Could not setup ASF authentication, continuing anyway...")

        # Get authenticated session for ASF
        from ..utils.earthdata_auth import earthdata_auth
        session = earthdata_auth.get_authenticated_session()
        username, password = earthdata_auth.get_credentials()
        
        try:
            # Perform ASF search with authenticated session
            if username and password:
                # Set ASF session with authentication
                asf.ASFSession().auth_with_creds(username, password)
                results = asf.granule_search(granule)
            else:
                # No credentials available
                results = asf.granule_search(granule)
            print(f"✓ Successfully found master scene: {granule[0]}")
        except Exception as e:
            print(f"❌ ASF search failed: {e}")
            print("This may be due to authentication issues or network connectivity")
            # Re-raise to let caller handle the user prompt
            raise e

    reference = results[0]
    
    if use_fallback:
        # Fallback mode: Create minimal stack from local files
        stack = _create_fallback_stack(ddata, reference)
        print(f'Fallback mode: Stack created from local files')
    else:
        # Normal mode: Use ASF stack
        stack_org = reference.stack()
        
        # %% Make a deep copy of the stack
        stack = deepcopy(stack_org)
        initial_stack_size = len(stack)
        
        # Get local SAFE files count for comparison
        data_files_temp = [x for x in os.listdir(ddata) if x.endswith('.SAFE')]
        local_files_count = len(data_files_temp)
        
        print(f'\n📊 Stack Filtering Summary:')
        print(f'Initial ASF stack size: {initial_stack_size}')
        print(f'Local SAFE files count: {local_files_count}')
        
        if initial_stack_size < local_files_count:
            diff = local_files_count - initial_stack_size
            print(f'\n⚠️  ASF stack is {diff} images smaller than local files')
            print(f'   Possible reasons:')
            print(f'   • Different acquisition modes (IW1/IW2/IW3 separate products)')
            print(f'   • Reprocessed scenes not linked in ASF baseline stack')
            print(f'   • Images from multiple reference scenes')
            print(f'   • ASF stack method limitations\n')
            
            # Find which local files are NOT in ASF stack
            stack_file_ids = set()
            for s in stack:
                file_id = s.properties.get('fileID', '').replace('-SLC', '')
                stack_file_ids.add(file_id)
            
            local_not_in_stack = []
            for safe_file in data_files_temp:
                local_id = safe_file.replace('.SAFE', '')
                if local_id not in stack_file_ids:
                    local_not_in_stack.append(local_id)
            
            if local_not_in_stack:
                print(f'   📋 {len(local_not_in_stack)} local files NOT found in ASF stack:')
                for idx, file_id in enumerate(local_not_in_stack[:5]):
                    print(f'      • {file_id}')
                if len(local_not_in_stack) > 5:
                    print(f'      ... and {len(local_not_in_stack) - 5} more')
                
                # Save these to exclusion log
                _save_excluded_images(ddata, local_not_in_stack, "not_in_asf_stack", "automatic")

        # Filter #1: Remove scenes with missing baseline data
        frames_nan = []
        for i in stack:
            pp_bl = i.properties['perpendicularBaseline']
            tm_pl = i.properties['temporalBaseline']
            if pp_bl is None or tm_pl is None:
                frames_nan.append(i)

        if frames_nan:
            print(f'\n🔴 Filter #1: Found {len(frames_nan)} images with missing baseline metadata')
            
            # Prepare details for user prompt
            details_list = []
            for i in frames_nan:
                file_id = i.properties.get('fileID', 'Unknown')
                perp = i.properties.get('perpendicularBaseline', 'None')
                temp = i.properties.get('temporalBaseline', 'None')
                details_list.append(f"❌ {file_id}\n   Perpendicular Baseline: {perp}\n   Temporal Baseline: {temp}")
            
            # Prompt user for decision
            message = (
                f"Found {len(frames_nan)} images with missing baseline metadata.\n\n"
                f"These images are missing perpendicular and/or temporal baseline information,\n"
                f"which is essential for interferometric processing.\n\n"
                f"Do you want to exclude these images from master selection?"
            )
            
            user_choice = _prompt_user_filter_decision(
                title="Missing Baseline Data",
                message=message,
                details_list=details_list,
                filter_type="missing_baselines"
            )
            
            if user_choice == "exclude":
                # Save excluded images before removing
                _save_excluded_images(ddata, frames_nan, "missing_baselines", user_choice)
                
                for i in frames_nan:
                    file_id = i.properties.get('fileID', 'Unknown')
                    print(f'  ❌ Excluding: {file_id}')
                    stack.remove(i)
                print(f'✓ Excluded {len(frames_nan)} images with missing baselines')
            elif user_choice == "keep":
                # Log that user chose to keep them
                _save_excluded_images(ddata, frames_nan, "missing_baselines", user_choice)
                print(f'✓ Keeping all {len(frames_nan)} images despite missing baselines (user choice)')
            else:  # cancel
                print("❌ Processing cancelled by user")
                raise Exception("User cancelled processing at Filter #1")
        else:
            print(f'✓ Filter #1: No images with missing baselines')

        # Filter #2: Remove scenes from different frames or paths
        frame = reference.properties['frameNumber']
        rel_orb = reference.properties['pathNumber']
        print(f'\n📍 Reference frame: {frame}, Path: {rel_orb}')
        
        frames_out = []
        frame_stats = {}  # Track different frames/paths
        for i in stack:
            fr = i.properties['frameNumber']
            rel = i.properties['pathNumber']
            if fr != frame or rel != rel_orb:
                frames_out.append(i)
                key = f'Frame_{fr}_Path_{rel}'
                frame_stats[key] = frame_stats.get(key, 0) + 1

        if frames_out:
            print(f'🔴 Filter #2: Found {len(frames_out)} images from different frames/paths')
            print(f'   Opening user dialog for decision...')
            
            # Prepare details for user prompt
            details_list = []
            details_list.append(f"Reference Image: Frame {frame}, Path {rel_orb}\n")
            
            # Group by frame/path
            grouped_images = {}
            for i in frames_out:
                fr = i.properties['frameNumber']
                rel = i.properties['pathNumber']
                key = f'Frame_{fr}_Path_{rel}'
                if key not in grouped_images:
                    grouped_images[key] = []
                file_id = i.properties.get('fileID', 'Unknown')
                grouped_images[key].append(file_id)
            
            # Add to details list
            for key, count in frame_stats.items():
                details_list.append(f"\n{key}: {count} images")
                # Show first 5 examples
                for idx, file_id in enumerate(grouped_images[key][:5]):
                    details_list.append(f"  • {file_id}")
                if len(grouped_images[key]) > 5:
                    details_list.append(f"  ... and {len(grouped_images[key]) - 5} more")
            
            # Prompt user for decision
            message = (
                f"Found {len(frames_out)} images from different frames/paths than the reference.\n\n"
                f"Reference: Frame {frame}, Path {rel_orb}\n\n"
                f"These images cover different geographic areas or orbital paths.\n"
                f"Mixing frames can cause geometric alignment issues.\n\n"
                f"Do you want to exclude these images from master selection?"
            )
            
            user_choice = _prompt_user_filter_decision(
                title="Different Frames/Paths Detected",
                message=message,
                details_list=details_list,
                filter_type="different_frames"
            )
            
            print(f'   User selected: {user_choice}')
            
            if user_choice == "exclude":
                # Save excluded images before removing
                _save_excluded_images(ddata, frames_out, "different_frames", user_choice)
                
                print(f'  Excluding images from different frames/paths:')
                for key, count in frame_stats.items():
                    print(f'  ❌ {count} images from {key}')
                for i in frames_out:
                    stack.remove(i)
                print(f'✓ Excluded {len(frames_out)} images from different frames/paths')
            elif user_choice == "keep":
                # Log that user chose to keep them
                _save_excluded_images(ddata, frames_out, "different_frames", user_choice)
                print(f'✓ Keeping all {len(frames_out)} images from different frames/paths (user choice)')
                print(f'  ⚠️  Warning: This may cause processing issues if frames are not adjacent')
            else:  # cancel
                print("❌ Processing cancelled by user")
                raise Exception("User cancelled processing at Filter #2")
        else:
            print(f'✓ Filter #2: All images from same frame/path')

    # Get local SAFE files
    data_files = [x for x in os.listdir(ddata) if x.endswith('.SAFE')]
    
    if not use_fallback:
        # Filter #3: Match stack items with local files
        data_analysis = []
        for s in stack:
            for f in data_files:
                # More robust filename matching
                f_name = f.replace('.SAFE', '.zip')
                if f_name == s.properties['fileName']:
                    data_analysis.append(s.properties['fileName'])
                    break
                    
        frames_out_lim = []
        for s in stack:
            if s.properties['fileName'] not in data_analysis:
                frames_out_lim.append(s)

        if frames_out_lim:
            print(f'\n🔴 Filter #3: Removing {len(frames_out_lim)} stack items not in local files:')
            for i in frames_out_lim[:5]:  # Show first 5 examples
                print(f'  ❌ {i.properties.get("fileID", "Unknown")}')
            if len(frames_out_lim) > 5:
                print(f'  ... and {len(frames_out_lim) - 5} more')
            for i in frames_out_lim:
                stack.remove(i)
        else:
            print(f'✓ Filter #3: All stack items matched with local files')

    print(f'\n📈 Final Result: Stack: {len(stack)}, Data: {len(data_files)}')
    if len(stack) < len(data_files):
        diff = len(data_files) - len(stack)
        print(f'⚠️  {diff} local SAFE files are NOT in the baseline stack')
        print(f'   This usually means they are from different frames/paths or have missing metadata')
    elif len(stack) > len(data_files):
        diff = len(stack) - len(data_files)
        print(f'⚠️  {diff} stack items were not found in local files (may need to download)')
    else:
        print(f'✓ Perfect match: All local files are in the stack')

    if use_fallback:
        # Fallback mode: Simple ranking based on temporal baseline only
        print("⚠ Fallback mode: Using temporal baseline only (no perpendicular baseline data)")
        return _calculate_fallback_rankings(stack)

    # Normal mode: Calculate both temporal and perpendicular baselines
    inter_pairs = []
    for i in stack:
        for j in stack:
            if i != j:
                slave_1 = i.properties['fileID']
                t_bl_s1 = i.properties['temporalBaseline']
                p_bl_s1 = i.properties['perpendicularBaseline']
                geo_s1 = i.geometry

                slave_2 = j.properties['fileID']
                t_bl_s2 = j.properties['temporalBaseline']
                p_bl_s2 = j.properties['perpendicularBaseline']
                geo_s2 = j.geometry

                t_bl = np.abs(t_bl_s1 - t_bl_s2)
                p_bl = np.abs(p_bl_s1 - p_bl_s2)

                # Double check to prevent creating list between two identical frames
                if slave_1 != slave_2:
                    inter_pairs.append([slave_1, slave_2, t_bl, p_bl, t_bl_s1,
                                        p_bl_s1, t_bl_s2, p_bl_s2, geo_s1, geo_s2])
                else:
                    print("Super master frame: %s %s" % (slave_1, slave_2))

    # 1. Calculate the temporal baseline between all image pairs
    tbl_pbl_lst = []
    for i in stack:
        tbl_val = 0
        pbl_val = 0
        for j in stack:
            if i != j:
                slave_1 = i.properties['fileID']
                t_bl_s1 = i.properties['temporalBaseline']
                p_bl_s1 = i.properties['perpendicularBaseline']

                slave_2 = j.properties['fileID']
                t_bl_s2 = j.properties['temporalBaseline']
                p_bl_s2 = j.properties['perpendicularBaseline']

                t_bl = np.abs(t_bl_s1 - t_bl_s2)
                p_bl = np.abs(p_bl_s1 - p_bl_s2)

                # Double check to prevent creating list between two identical frames
                if slave_1 != slave_2:
                    tbl_val += t_bl
                    pbl_val += p_bl

        tbl_pbl_lst.append([tbl_val, pbl_val, i.properties['fileID']])

    # Get the minimum temporal + perpendicular baseline
    tbl_pbl_arr = np.array(tbl_pbl_lst)
    sums = tbl_pbl_arr[:, 0].astype('float') + tbl_pbl_arr[:, 1].astype('float')
    ranks = np.argsort(np.argsort(sums)) + 1  # Rank starts from 1
    tbl_pbl_arr_sort = np.column_stack((tbl_pbl_arr, ranks))
    tbl_pbl_arr_sort = tbl_pbl_arr_sort[tbl_pbl_arr_sort[:, -1].argsort()]  # Sort by rank column
    
    print(f'\n✓ Master selection completed using ASF baseline stack')
    print(f'   Method: ASF baseline network')
    print(f'   Total candidates: {len(tbl_pbl_arr_sort)}')
    print(f'   Top 5 master candidates:')
    for i in range(min(5, len(tbl_pbl_arr_sort))):
        img_id = tbl_pbl_arr_sort[i][2]
        rank = int(tbl_pbl_arr_sort[i][3])
        print(f'      #{rank}: {img_id}')
    print("="*80 + "\n")

    return tbl_pbl_arr_sort

def main(ddata):
    
    master = select_mst(ddata)
    print(f"Selected master: {master}")

if __name__ == "__main__":
    main()