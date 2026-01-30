import streamlit as st
import pandas as pd
import numpy as np
import io

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
        return 100  # Penalty for missing keys
    
    idx1 = CAMELOT_ORDER.index(key1)
    idx2 = CAMELOT_ORDER.index(key2)
    
    # Check for direct modulation (same number, different letter)
    num1, let1 = key1[:-1], key1[-1]
    num2, let2 = key2[:-1], key2[-1]
    
    if num1 == num2 and let1 != let2:
        return 1  # Perfect mix (Major <-> Minor)
        
    # Calculate distance on the circle
    diff = abs(idx1 - idx2)
    # Adjust for wrap-around (e.g., 12A -> 1A)
    if diff > 12:
        diff = 24 - diff
        
    # Favor closer keys (simple linear distance for clustering)
    return diff

def parse_rekordbox_xml(uploaded_file):
    """Simple parser for Rekordbox XML exports."""
    try:
        # This is a simplified XML parser. For robust usage, ElementTree is better,
        # but for this snippet we'll assume a standard structure or TXT export.
        # If the user uploads a TXT/CSV (which is easier from Rekordbox):
        if uploaded_file.name.endswith('.txt') or uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file, sep='\t', encoding='utf-16le') # Rekordbox standard
            return df
        
        # Fallback for XML (Mock logic for this snippet - assuming CSV/TXT preference)
        # In a real deployed app, we would use xml.etree.ElementTree here.
        st.error("Please export your playlist as TXT from Rekordbox (Right click -> Export a playlist to a file -> .txt). XML parsing is heavy for this lightweight version.")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Error reading file: {e}")
        return pd.DataFrame()

# --- 3. The Algorithm (Cluster + Sort) ---
def optimize_playlist(df, energy_mode="Ramp Up (Low -> High)"):
    """
    1. Groups tracks by Camelot Key.
    2. Sorts the Key Groups to form a harmonic path.
    3. Sorts tracks inside each group by BPM based on energy_mode.
    """
    
    # Clean Data
    required_cols = ['Artist', 'Track Title', 'BPM', 'Key']
    # Check if columns exist (Rekordbox sometimes names them differently)
    # We'll do a loose match or assume standard TXT export headers
    
    # Normalize column names
    df.columns = [c.strip() for c in df.columns]
    
    # Basic filtering
    if 'Key' not in df.columns:
        st.error("Column 'Key' not found. Please ensure your export includes Key information.")
        return df
        
    # Filter valid keys
    valid_df = df[df['Key'].isin(CAMELOT_ORDER)].copy()
    invalid_df = df[~df['Key'].isin(CAMELOT_ORDER)].copy()
    
    # 1. Group by Key
    groups = valid_df.groupby('Key')
    unique_keys = valid_df['Key'].unique().tolist()
    
    # 2. Sort Keys (Simple Traveling Salesman - Nearest Neighbor)
    # Start with the most common key or simply the first one
    if not unique_keys:
        return df
        
    sorted_keys = [unique_keys[0]]
    unique_keys.remove(unique_keys[0])
    
    while unique_keys:
        current_key = sorted_keys[-1]
        # Find closest next key
        best_next_key = min(unique_keys, key=lambda k: get_camelot_distance(current_key, k))
        sorted_keys.append(best_next_key)
        unique_keys.remove(best_next_key)
        
    # 3. Build Final List
    final_playlist = []
    
    for key in sorted_keys:
        key_group = groups.get_group(key)
        
        # Sort internal group by BPM
        if energy_mode == "Ramp Up (Low -> High)":
            key_group = key_group.sort_values(by='BPM', ascending=True)
        elif energy_mode == "Ramp Down (High -> Low)":
            key_group = key_group.sort_values(by='BPM', ascending=False)
        elif energy_mode == "Wave (Mixed)":
             # Alternating sort could go here, simply keeping original for now or random
             pass 
             
        final_playlist.append(key_group)
        
    # Add tracks with no key at the end
    if not invalid_df.empty:
        final_playlist.append(invalid_df)
        
    return pd.concat(final_playlist)

# --- 4. Main UI ---
def main():
    st.title("🎵 Harmonic Flow Optimizer")
    st.markdown("""
    **Transform your Rekordbox playlist into a harmonic journey.** This tool reorders your tracks to ensure compatible key mixing and a controlled energy flow.
    """)
    
    with st.sidebar:
        st.header("Settings")
        st.info("Export your playlist from Rekordbox as a **TXT file** for best results.")
        
        # The Slider Fix: Using a Select Slider for clear options
        energy_option = st.select_slider(
            "Energy Flow Strategy",
            options=["Ramp Down (High -> Low)", "Wave (Mixed)", "Ramp Up (Low -> High)"],
            value="Ramp Up (Low -> High)"
        )
    
    uploaded_file = st.file_uploader("Upload Playlist (TXT / CSV)", type=['txt', 'csv'])
    
    if uploaded_file:
        df = parse_rekordbox_xml(uploaded_file)
        
        if not df.empty:
            st.success(f"Loaded {len(df)} tracks successfully!")
            
            # Show preview
            with st.expander("Original Playlist Preview"):
                st.dataframe(df.head())
                
            if st.button("🚀 Optimize Magic"):
                with st.spinner("Calculating harmonic paths..."):
                    optimized_df = optimize_playlist(df, energy_mode=energy_option)
                    
                    st.divider()
                    st.subheader("✅ Optimized Result")
                    
                    # Display metrics
                    col1, col2 = st.columns(2)
                    col1.metric("Tracks", len(optimized_df))
                    col1.metric("Start BPM", f"{optimized_df.iloc[0]['BPM']}" if 'BPM' in optimized_df else "N/A")
                    
                    # Show result
                    st.dataframe(optimized_df[['Artist', 'Track Title', 'Key', 'BPM']].reset_index(drop=True), use_container_width=True)
                    
                    # Download Button
                    csv = optimized_df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="📥 Download Sorted CSV",
                        data=csv,
                        file_name="harmonic_flow_sorted.csv",
                        mime="text/csv"
                    )

if __name__ == "__main__":
    main()
