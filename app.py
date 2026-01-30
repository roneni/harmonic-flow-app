import streamlit as st
import pandas as pd
import numpy as np
import io
import xml.etree.ElementTree as ET

# --- 1. Page Configuration ---
st.set_page_config(
    page_title="Harmonic Flow Optimizer",
    page_icon="🎵",
    layout="wide"
)

# --- 2. Camelot Logic & Helpers ---
CAMELOT_ORDER = [
    "1A", "1B", "2A", "2B", "3A", "3B", "4A", "4B",
    "5A", "5B", "6A", "6B", "7A", "7B", "8A", "8B",
    "9A", "9B", "10A", "10B", "11A", "11B", "12A", "12B"
]

def get_camelot_distance(key1, key2):
    """Calculates the harmonic distance on the Camelot Wheel."""
    if not key1 or not key2 or key1 not in CAMELOT_ORDER or key2 not in CAMELOT_ORDER:
        return 100
    
    idx1 = CAMELOT_ORDER.index(key1)
    idx2 = CAMELOT_ORDER.index(key2)
    
    num1, let1 = key1[:-1], key1[-1]
    num2, let2 = key2[:-1], key2[-1]
    
    if num1 == num2 and let1 != let2:
        return 1
        
    diff = abs(idx1 - idx2)
    if diff > 12:
        diff = 24 - diff
    return diff

def parse_uploaded_file(uploaded_file):
    """Parses TXT, CSV, or XML from Rekordbox."""
    try:
        # Case 1: TXT / CSV (Tab Separated)
        if uploaded_file.name.endswith('.txt') or uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file, sep='\t', encoding='utf-16le')
            # Normalize columns just in case
            df.columns = [c.strip() for c in df.columns]
            return df
        
        # Case 2: XML (Rekordbox Standard Export)
        elif uploaded_file.name.endswith('.xml'):
            tree = ET.parse(uploaded_file)
            root = tree.getroot()
            
            # Rekordbox XML structure: COLLECTION -> TRACK
            tracks = []
            collection = root.find('COLLECTION')
            if collection is None:
                return pd.DataFrame() # Empty if invalid XML
                
            for track in collection.findall('TRACK'):
                # Extract attributes
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
    # Clean Data & Standardize Column Names
    # If XML was used, columns are already perfect. If TXT, they might need strip.
    df.columns = [c.strip() for c in df.columns]
    
    # Ensure BPM is numeric
    if 'BPM' in df.columns:
        df['BPM'] = pd.to_numeric(df['BPM'], errors='coerce')
    
    # Check for essential columns
    if 'Key' not in df.columns:
        st.error("Column 'Key' not found. Ensure your export includes Key/Tonality info.")
        return df

    # Filter valid keys
    valid_df = df[df['Key'].isin(CAMELOT_ORDER)].copy()
    invalid_df = df[~df['Key'].isin(CAMELOT_ORDER)].copy()
    
    # Group & Sort Keys
    if valid_df.empty:
        return df

    groups = valid_df.groupby('Key')
    unique_keys = valid_df['Key'].unique().tolist()
    
    # Pathfinding (Greedy / Nearest Neighbor)
    sorted_keys = [unique_keys[0]]
    unique_keys.remove(unique_keys[0])
    
    while unique_keys:
        current_key = sorted_keys[-1]
        best_next_key = min(unique_keys, key=lambda k: get_camelot_distance(current_key, k))
        sorted_keys.append(best_next_key)
        unique_keys.remove(best_next_key)
        
    # Build Final Playlist
    final_playlist = []
    
    for key in sorted_keys:
        key_group = groups.get_group(key)
        
        # Internal Sort by BPM
        if energy_mode == "Ramp Up (Low -> High)":
            key_group = key_group.sort_values(by='BPM', ascending=True)
        elif energy_mode == "Ramp Down (High -> Low)":
            key_group = key_group.sort_values(by='BPM', ascending=False)
        # Wave mode leaves as is (or could be random)
             
        final_playlist.append(key_group)
        
    if not invalid_df.empty:
        final_playlist.append(invalid_df)
        
    return pd.concat(final_playlist)

# --- 4. Main UI ---
def main():
    st.title("🎵 Harmonic Flow Optimizer")
    
    # Marketing & Time-Saving Text
    st.markdown("""
    **Save hours of prep time.** Instantly transform your raw playlist into a seamless harmonic journey. 
    This tool reorders your tracks to ensure perfect key compatibility and controlled energy flow—so you can focus on the mix, not the math.
    """)
    
    with st.sidebar:
        st.header("Settings")
        st.info("Supports **XML** and **TXT** exports directly from Rekordbox.")
        
        energy_option = st.select_slider(
            "Energy Flow Strategy",
            options=["Ramp Down (High -> Low)", "Wave (Mixed)", "Ramp Up (Low -> High)"],
            value="Ramp Up (Low -> High)"
        )
    
    uploaded_file = st.file_uploader("Upload Playlist (XML / TXT / CSV)", type=['xml', 'txt', 'csv'])
    
    if uploaded_file:
        df = parse_uploaded_file(uploaded_file)
        
        if not df.empty:
            st.success(f"Loaded {len(df)} tracks successfully!")
            
            with st.expander("Original Playlist Preview"):
                st.dataframe(df.head())
                
            if st.button("🚀 Optimize Magic"):
                with st.spinner("Analyzing harmony & BPM..."):
                    optimized_df = optimize_playlist(df, energy_mode=energy_option)
                    
                    st.divider()
                    st.subheader("✅ Optimized Result")
                    
                    col1, col2 = st.columns(2)
                    col1.metric("Tracks", len(optimized_df))
                    # Safe check for BPM display
                    start_bpm = optimized_df.iloc[0]['BPM'] if 'BPM' in optimized_df.columns and not optimized_df.empty else "N/A"
                    col1.metric("Start BPM", f"{start_bpm}")
                    
                    # Show result
                    display_cols = ['Artist', 'Track Title', 'Key', 'BPM']
                    # Only show columns that actually exist
                    display_cols = [c for c in display_cols if c in optimized_df.columns]
                    
                    st.dataframe(optimized_df[display_cols].reset_index(drop=True), use_container_width=True)
                    
                    # Download
                    csv = optimized_df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="📥 Download Sorted CSV",
                        data=csv,
                        file_name="harmonic_flow_sorted.csv",
                        mime="text/csv"
                    )

if __name__ == "__main__":
    main()
