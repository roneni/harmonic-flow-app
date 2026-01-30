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

# This block injects custom CSS to make the app look better
st.markdown("""
    <style>
    /* Center the Main Title */
    h1 {
        text-align: center;
        background: -webkit-linear-gradient(45deg, #FF4B4B, #FF9068);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        padding-bottom: 20px;
    }
    
    /* Style the Optimize Button */
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
    
    /* Info Box Styling */
    .stAlert {
        border-radius: 10px;
    }
    </style>
""", unsafe_allow_html=True)

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
        # Case 1: TXT / CSV
        if uploaded_file.name.endswith('.txt') or uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file, sep='\t', encoding='utf-16le')
            df.columns = [c.strip() for c in df.columns]
            return df
        
        # Case 2: XML
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
    df.columns = [c.strip() for c in df.columns]
    
    if 'BPM' in df.columns:
        df['BPM'] = pd.to_numeric(df['BPM'], errors='coerce')
    
    if 'Key' not in df.columns:
        st.error("Column 'Key' not found. Ensure your export includes Key/Tonality info.")
        return df

    valid_df = df[df['Key'].isin(CAMELOT_ORDER)].copy()
    invalid_df = df[~df['Key'].isin(CAMELOT_ORDER)].copy()
    
    if valid_df.empty:
        return df

    groups = valid_df.groupby('Key')
    unique_keys = valid_df['Key'].unique().tolist()
    
    sorted_keys = [unique_keys[0]]
    unique_keys.remove(unique_keys[0])
    
    while unique_keys:
        current_key = sorted_keys[-1]
        best_next_key = min(unique_keys, key=lambda k: get_camelot_distance(current_key, k))
        sorted_keys.append(best_next_key)
        unique_keys.remove(best_next_key)
        
    final_playlist = []
    
    for key in sorted_keys:
        key_group = groups.get_group(key)
        if energy_mode == "Ramp Up (Low -> High)":
            key_group = key_group.sort_values(by='BPM', ascending=True)
        elif energy_mode == "Ramp Down (High -> Low)":
            key_group = key_group.sort_values(by='BPM', ascending=False)
             
        final_playlist.append(key_group)
        
    if not invalid_df.empty:
        final_playlist.append(invalid_df)
        
    return pd.concat(final_playlist)

# --- 4. Main UI ---
def main():
    st.title("Harmonic Flow Optimizer")
    
    # Updated Description with Camelot Credit
    st.markdown("""
    <div style='text-align: center; color: #888; margin-bottom: 20px;'>
    Instantly transform your raw playlist into a seamless harmonic journey.<br>
    Powered by the <b>Camelot Wheel</b> system for perfect key mixing.
    </div>
    """, unsafe_allow_html=True)
    
    # Layout: Sidebar + Main Area
    with st.sidebar:
        st.header("⚙️ Settings")
        st.info("Supports **XML** and **TXT** exports directly from Rekordbox.")
        
        energy_option = st.select_slider(
            "Energy Flow Strategy",
            options=["Ramp Down (High -> Low)", "Wave (Mixed)", "Ramp Up (Low -> High)"],
            value="Ramp Up (Low -> High)"
        )
    
    # File Uploader Container
    with st.container():
        uploaded_file = st.file_uploader("Upload Playlist (XML / TXT / CSV)", type=['xml', 'txt', 'csv'])
    
    if uploaded_file:
        df = parse_uploaded_file(uploaded_file)
        
        if not df.empty:
            st.success(f"Loaded {len(df)} tracks successfully!")
            
            with st.expander("📂 Preview Original Playlist"):
                st.dataframe(df.head(), use_container_width=True)
                
            # The Magic Button (Styled via CSS above)
            if st.button("🚀 Optimize Magic"):
                with st.spinner("Analyzing harmonic paths..."):
                    optimized_df = optimize_playlist(df, energy_mode=energy_option)
                    
                    st.divider()
                    st.markdown("<h3 style='text-align: center;'>✅ Optimized Result</h3>", unsafe_allow_html=True)
                    
                    # Metrics
                    col1, col2, col3 = st.columns(3)
                    col1.metric("Total Tracks", len(optimized_df))
                    
                    start_bpm = optimized_df.iloc[0]['BPM'] if 'BPM' in optimized_df.columns and not optimized_df.empty else "N/A"
                    col2.metric("Start BPM", f"{start_bpm}")
                    
                    start_key = optimized_df.iloc[0]['Key'] if 'Key' in optimized_df.columns and not optimized_df.empty else "N/A"
                    col3.metric("Start Key", f"{start_key}")
                    
                    # Result Table
                    display_cols = ['Artist', 'Track Title', 'Key', 'BPM']
                    display_cols = [c for c in display_cols if c in optimized_df.columns]
                    
                    st.dataframe(optimized_df[display_cols].reset_index(drop=True), use_container_width=True)
                    
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
