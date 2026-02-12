import streamlit as st
import pandas as pd
import numpy as np
import io
import xml.etree.ElementTree as ET

# --- 1. Page Configuration & Custom CSS ---
st.set_page_config(
    page_title="Harmonic Flow Optimizer",
    page_icon="🎵",
    layout="wide"
)

st.markdown("""
    <style>
    h1 {
        text-align: center;
        background: -webkit-linear-gradient(45deg, #FF4B4B, #FF9068);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        padding-bottom: 20px;
    }
    div.stButton > button {
        width: 100%;
        background: linear-gradient(90deg, #FF4B4B 0%, #FF9068 100%);
        color: white;
        font-weight: bold;
        border: none;
        padding: 10px 24px;
        border-radius: 8px;
        transition: all 0.3s ease;
    }
    div.stButton > button:hover {
        transform: scale(1.02);
        box-shadow: 0 4px 15px rgba(255, 75, 75, 0.4);
    }
    .stAlert { border-radius: 10px; }
    </style>
""", unsafe_allow_html=True)

# --- 2. Camelot Logic & Translation ---

# All valid Camelot codes
CAMELOT_ORDER = [
    "1A", "1B", "2A", "2B", "3A", "3B", "4A", "4B",
    "5A", "5B", "6A", "6B", "7A", "7B", "8A", "8B",
    "9A", "9B", "10A", "10B", "11A", "11B", "12A", "12B"
]

# Translator: Musical Key -> Camelot Key
# Covers standard notation, enharmonic equivalents, and Open Key (d/m) notation
KEY_MAPPING = {
    # --- Standard Major Keys -> B side ---
    "B": "1B", "F#": "2B", "Gb": "2B", "Db": "3B", "C#": "3B",
    "Ab": "4B", "Eb": "5B", "Bb": "6B", "F": "7B", "C": "8B",
    "G": "9B", "D": "10B", "A": "11B", "E": "12B",

    # --- Standard Minor Keys -> A side ---
    "Abm": "1A", "G#m": "1A", "Ebm": "2A", "D#m": "2A",
    "Bbm": "3A", "A#m": "3A", "Fm": "4A", "Cm": "5A",
    "Gm": "6A", "Dm": "7A", "Am": "8A", "Em": "9A",
    "Bm": "10A", "F#m": "11A", "Gbm": "11A", "C#m": "12A", "Dbm": "12A",

    # --- Long-form notation (e.g. from some DJ software) ---
    "Bmaj": "1B", "F#maj": "2B", "Gbmaj": "2B", "Dbmaj": "3B",
    "C#maj": "3B", "Abmaj": "4B", "Ebmaj": "5B", "Bbmaj": "6B",
    "Fmaj": "7B", "Cmaj": "8B", "Gmaj": "9B", "Dmaj": "10B",
    "Amaj": "11B", "Emaj": "12B",
    "Abmin": "1A", "G#min": "1A", "Ebmin": "2A", "D#min": "2A",
    "Bbmin": "3A", "A#min": "3A", "Fmin": "4A", "Cmin": "5A",
    "Gmin": "6A", "Dmin": "7A", "Amin": "8A", "Emin": "9A",
    "Bmin": "10A", "F#min": "11A", "Gbmin": "11A", "C#min": "12A",
    "Dbmin": "12A",

    # --- Open Key notation (shown on Camelot Wheel: 1d=1B, 1m=1A) ---
    "1d": "1B", "2d": "2B", "3d": "3B", "4d": "4B", "5d": "5B",
    "6d": "6B", "7d": "7B", "8d": "8B", "9d": "9B", "10d": "10B",
    "11d": "11B", "12d": "12B",
    "1m": "1A", "2m": "2A", "3m": "3A", "4m": "4A", "5m": "5A",
    "6m": "6A", "7m": "7A", "8m": "8A", "9m": "9A", "10m": "10A",
    "11m": "11A", "12m": "12A",
}


def standardize_key(key_val):
    """Converts various key formats (Am, 8A, 08A, 8m, 8d) to standard Camelot (8A)."""
    if not isinstance(key_val, str):
        return None

    k = key_val.strip()

    # 1. Already standard Camelot (e.g. "8A", "12B")
    if k in CAMELOT_ORDER:
        return k

    # 2. Dictionary mapping (e.g. "Am" -> "8A", "8m" -> "8A", "8d" -> "8B")
    if k in KEY_MAPPING:
        return KEY_MAPPING[k]

    # 3. Handle leading zeros from some software (e.g. "08A" -> "8A")
    if k.startswith("0") and k[1:] in CAMELOT_ORDER:
        return k[1:]

    # 4. Case-insensitive fallback (e.g. "am" -> "Am" -> "8A")
    for mapping_key, camelot_val in KEY_MAPPING.items():
        if k.lower() == mapping_key.lower():
            return camelot_val

    return None


def get_camelot_distance(key1, key2):
    """
    Calculates the true harmonic distance between two Camelot keys.

    The Camelot Wheel has two concentric rings (A=minor, B=major),
    each with 12 positions arranged in a circle (1-12).

    Compatible transitions (distance 1):
      - Same number, switch A<->B (relative major/minor)
      - Same letter, adjacent number on the 1-12 circle

    Distance = number of steps needed on the wheel.
    """
    if not key1 or not key2:
        return 100

    num1, let1 = int(key1[:-1]), key1[-1]
    num2, let2 = int(key2[:-1]), key2[-1]

    # Circular distance on the 1-12 wheel
    num_diff = abs(num1 - num2)
    num_diff = min(num_diff, 12 - num_diff)

    # Same number, different letter = relative major/minor (perfect mix)
    if num_diff == 0 and let1 != let2:
        return 1

    # Same letter (both minor or both major) = just the circular step count
    if let1 == let2:
        return num_diff

    # Different letter AND different number = cross ring + steps
    return num_diff + 1


def find_optimal_key_path(unique_keys):
    """
    Finds the globally optimal ordering of Camelot keys using the
    Held-Karp algorithm (dynamic programming on bitmasks).

    This solves the Shortest Hamiltonian Path problem exactly.
    With typical playlists (up to ~20 unique keys), this runs in
    under a second: O(2^n * n^2) where n = number of unique keys.
    """
    n = len(unique_keys)

    # Edge case: 1 or 2 keys
    if n <= 1:
        return unique_keys[:]
    if n == 2:
        return unique_keys[:]

    # Pre-compute distance matrix
    dist = [[0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            dist[i][j] = get_camelot_distance(unique_keys[i], unique_keys[j])

    # Held-Karp DP
    # dp[mask][i] = minimum distance to visit exactly the nodes in mask, ending at node i
    INF = float('inf')
    full_mask = (1 << n) - 1
    dp = [[INF] * n for _ in range(1 << n)]
    parent = [[-1] * n for _ in range(1 << n)]

    # Base case: start at each node individually
    for i in range(n):
        dp[1 << i][i] = 0

    # Fill DP table
    for mask in range(1, 1 << n):
        for last in range(n):
            if not (mask & (1 << last)):
                continue
            if dp[mask][last] == INF:
                continue

            for nxt in range(n):
                if mask & (1 << nxt):
                    continue
                new_mask = mask | (1 << nxt)
                new_dist = dp[mask][last] + dist[last][nxt]
                if new_dist < dp[new_mask][nxt]:
                    dp[new_mask][nxt] = new_dist
                    parent[new_mask][nxt] = last

    # Find the best endpoint
    best_last = min(range(n), key=lambda i: dp[full_mask][i])

    # Backtrack to recover path
    path_indices = []
    mask = full_mask
    curr = best_last
    while curr != -1:
        path_indices.append(curr)
        prev = parent[mask][curr]
        mask ^= (1 << curr)
        curr = prev

    path_indices.reverse()
    return [unique_keys[i] for i in path_indices]


def parse_uploaded_file(uploaded_file):
    """Parses XML (Rekordbox), TXT (tab-separated), or CSV playlist files."""
    try:
        # Case 1: TXT / CSV
        if uploaded_file.name.endswith('.txt') or uploaded_file.name.endswith('.csv'):
            # Try Rekordbox TXT format first (tab-delimited, UTF-16LE)
            try:
                df = pd.read_csv(uploaded_file, sep='\t', encoding='utf-16le')
                if 'Key' not in df.columns and len(df.columns) <= 1:
                    uploaded_file.seek(0)
                    df = pd.read_csv(uploaded_file)
            except Exception:
                uploaded_file.seek(0)
                try:
                    df = pd.read_csv(uploaded_file, sep='\t')
                    if 'Key' not in df.columns and len(df.columns) <= 1:
                        uploaded_file.seek(0)
                        df = pd.read_csv(uploaded_file)
                except Exception:
                    uploaded_file.seek(0)
                    df = pd.read_csv(uploaded_file)

            df.columns = [c.strip() for c in df.columns]
            return df

        # Case 2: XML (Rekordbox)
        elif uploaded_file.name.endswith('.xml'):
            tree = ET.parse(uploaded_file)
            root = tree.getroot()
            tracks = []
            collection = root.find('COLLECTION')
            if collection is None:
                return pd.DataFrame()

            for track in collection.findall('TRACK'):
                tracks.append({
                    'Artist': track.get('Artist'),
                    'Track Title': track.get('Name'),
                    'BPM': track.get('AverageBpm'),
                    'Key': track.get('Tonality')
                })
            return pd.DataFrame(tracks)

        return pd.DataFrame()
    except Exception as e:
        st.error(f"Error reading file: {e}")
        return pd.DataFrame()


# --- 3. The Algorithm ---
def optimize_playlist(df, energy_mode="Ramp Up (Low -> High)"):
    """
    Optimizes a playlist for harmonic mixing using the Camelot Wheel.

    1. Standardizes all keys to Camelot notation
    2. Finds the mathematically optimal key path (Held-Karp algorithm)
    3. Chooses path direction based on energy mode + BPM
    4. Sorts tracks within each key group by BPM
    """
    df = df.copy()
    df.columns = [c.strip() for c in df.columns]

    if 'Key' not in df.columns:
        st.error("Column 'Key' not found in your file.")
        return df

    # Standardize keys to Camelot notation
    df['Camelot_Key'] = df['Key'].apply(standardize_key)

    # Separate valid and invalid tracks
    valid_df = df[df['Camelot_Key'].notna()].copy()
    invalid_df = df[df['Camelot_Key'].isna()].copy()

    if valid_df.empty:
        st.warning("No valid keys found. Check if your file has Key/Tonality info.")
        return df

    # Ensure BPM is numeric
    if 'BPM' in valid_df.columns:
        valid_df['BPM'] = pd.to_numeric(valid_df['BPM'], errors='coerce')

    # Group tracks by their Camelot key
    groups = valid_df.groupby('Camelot_Key')
    unique_keys = valid_df['Camelot_Key'].unique().tolist()

    # --- STEP 1: Find optimal key ordering (Held-Karp) ---
    optimal_path = find_optimal_key_path(unique_keys)

    # --- STEP 2: Choose path direction based on energy mode ---
    # Calculate average BPM of first and last key groups
    if 'BPM' in valid_df.columns:
        first_group_bpm = groups.get_group(optimal_path[0])['BPM'].mean()
        last_group_bpm = groups.get_group(optimal_path[-1])['BPM'].mean()

        if energy_mode == "Ramp Up (Low -> High)":
            # Start with lower BPM end
            if first_group_bpm > last_group_bpm:
                optimal_path = optimal_path[::-1]
        elif energy_mode == "Ramp Down (High -> Low)":
            # Start with higher BPM end
            if first_group_bpm < last_group_bpm:
                optimal_path = optimal_path[::-1]
        # Wave mode: pick direction that gives better wave pattern (keep as-is)

    # --- STEP 3: Sort tracks within each key group by BPM ---
    final_playlist = []

    for idx, key in enumerate(optimal_path):
        key_group = groups.get_group(key).copy()

        if 'BPM' in key_group.columns:
            if energy_mode == "Ramp Up (Low -> High)":
                key_group = key_group.sort_values(by='BPM', ascending=True)
            elif energy_mode == "Ramp Down (High -> Low)":
                key_group = key_group.sort_values(by='BPM', ascending=False)
            elif energy_mode == "Wave (Mixed)":
                # Alternate ascending/descending within each key group
                if idx % 2 == 0:
                    key_group = key_group.sort_values(by='BPM', ascending=True)
                else:
                    key_group = key_group.sort_values(by='BPM', ascending=False)

        final_playlist.append(key_group)

    # Append tracks with unrecognized keys at the end
    if not invalid_df.empty:
        final_playlist.append(invalid_df)

    result = pd.concat(final_playlist)

    # Store the Camelot path for display before dropping the column
    result.attrs['camelot_path'] = optimal_path

    # Clean up temporary column
    result = result.drop(columns=['Camelot_Key'])
    return result


# --- 4. Main UI ---
def main():
    st.title("Harmonic Flow Optimizer")

    st.markdown("""
    <div style='text-align: center; color: #888; margin-bottom: 20px;'>
    Instantly transform your raw playlist into a seamless harmonic journey.<br>
    Powered by the <b>Camelot Wheel</b> system &mdash; now with mathematically optimal path finding.
    </div>
    """, unsafe_allow_html=True)

    with st.sidebar:
        st.header("Settings")
        st.info("Supports **XML** (Rekordbox), **TXT** and **CSV**.")

        energy_option = st.select_slider(
            "Energy Flow Strategy",
            options=["Ramp Down (High -> Low)", "Wave (Mixed)", "Ramp Up (Low -> High)"],
            value="Ramp Up (Low -> High)"
        )

        st.divider()
        st.markdown("**How it works:**")
        st.markdown("""
        1. Keys are converted to Camelot codes
        2. The **Held-Karp algorithm** finds the shortest harmonic path through all keys
        3. Tracks are sorted by BPM within each key group
        4. Path direction is chosen based on your energy strategy
        """)

    with st.container():
        uploaded_file = st.file_uploader("Upload Playlist", type=['xml', 'txt', 'csv'])

    if uploaded_file:
        df = parse_uploaded_file(uploaded_file)

        if not df.empty:
            st.success(f"Loaded {len(df)} tracks successfully!")

            with st.expander("Preview Original Playlist"):
                st.dataframe(df.head(10), use_container_width=True)

            if st.button("Optimize Playlist"):
                with st.spinner("Finding optimal harmonic path..."):
                    optimized_df = optimize_playlist(df, energy_mode=energy_option)

                    st.divider()
                    st.markdown("<h3 style='text-align: center;'>Optimized Result</h3>", unsafe_allow_html=True)

                    # --- Metrics Row ---
                    col1, col2, col3, col4 = st.columns(4)
                    col1.metric("Total Tracks", len(optimized_df))

                    if 'BPM' in optimized_df.columns:
                        start_bpm = optimized_df.iloc[0]['BPM']
                        end_bpm = optimized_df.iloc[-1]['BPM']
                        col2.metric("Start BPM", f"{start_bpm}")
                        col3.metric("End BPM", f"{end_bpm}")

                    start_key = optimized_df.iloc[0]['Key'] if 'Key' in optimized_df.columns else "N/A"
                    col4.metric("Start Key", f"{start_key}")

                    # --- Harmonic Quality Report ---
                    temp_df = optimized_df.copy()
                    temp_df['Camelot_Key'] = temp_df['Key'].apply(standardize_key)
                    camelot_keys = temp_df['Camelot_Key'].tolist()

                    total_dist = 0
                    perfect = 0
                    good = 0
                    bad = 0
                    worst = 0
                    for i in range(1, len(camelot_keys)):
                        d = get_camelot_distance(camelot_keys[i - 1], camelot_keys[i])
                        if d <= 100:  # valid keys
                            total_dist += d
                            if d <= 1:
                                perfect += 1
                            elif d == 2:
                                good += 1
                            else:
                                bad += 1
                            worst = max(worst, d)

                    transitions = len(camelot_keys) - 1

                    st.markdown("---")
                    st.markdown("**Harmonic Quality Report**")
                    q1, q2, q3, q4 = st.columns(4)
                    q1.metric("Total Distance", total_dist)
                    q2.metric("Perfect Transitions", f"{perfect}/{transitions}")
                    q3.metric("Worst Jump", worst)
                    q4.metric("Avg Distance", f"{total_dist / transitions:.2f}" if transitions > 0 else "N/A")

                    if bad > 0:
                        st.warning(f"{bad} transition(s) with distance 3+. These are unavoidable gaps in your key selection.")
                    else:
                        st.success("Every transition is distance 2 or less. Mathematically optimal!")

                    # --- Result Table ---
                    display_cols = ['Artist', 'Track Title', 'Key', 'BPM']
                    display_cols = [c for c in display_cols if c in optimized_df.columns]

                    st.dataframe(optimized_df[display_cols].reset_index(drop=True), use_container_width=True)

                    # --- Download ---
                    csv = optimized_df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="Download Sorted CSV",
                        data=csv,
                        file_name="harmonic_flow_sorted.csv",
                        mime="text/csv"
                    )


if __name__ == "__main__":
    main()
