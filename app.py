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
CAMELOT_ORDER = [
    "1A", "1B", "2A", "2B", "3A", "3B", "4A", "4B",
    "5A", "5B", "6A", "6B", "7A", "7B", "8A", "8B",
    "9A", "9B", "10A", "10B", "11A", "11B", "12A", "12B"
]

# Translator: Musical Key -> Camelot Key
KEY_MAPPING = {
    # Major (B -> 1B, F# -> 2B...)
    "B": "1B", "F#": "2B", "Gb": "2B", "Db": "3B", "C#": "3B",
    "Ab": "4B", "Eb": "5B", "Bb": "6B", "F": "7B", "C": "8B",
    "G": "9B", "D": "10B", "A": "11B", "E": "12B",
    
    # Minor (Abm -> 1A, Ebm -> 2A...)
    "Abm": "1A", "G#m": "1A", "Ebm": "2A", "D#m": "2A",
    "Bbm": "3A", "A#m": "3A", "Fm": "4A", "Cm": "5A",
    "Gm": "6A", "Dm": "7A", "Am": "8A", "Em": "9A",
    "Bm": "10A", "F#m": "11A", "Gbm": "11A", "C#m": "12A", "Dbm": "12A"
}

def standardize_key(key_val):
    """Converts various key formats (Am, 8A, 08A) to standard Camelot (8A)."""
    if not isinstance(key_val, str):
        return None
    
    k = key_val.strip()
    
    # 1. If already standard Camelot (e.g. "8A")
    if k in CAMELOT_ORDER:
        return k
        
    # 2. Try Dictionary Mapping (e.g. "Am" -> "8A")
    if k in KEY_MAPPING:
        return KEY_MAPPING[k]
        
    # 3. Handle Leading Zeros (e.g. "08A" -> "8A")
    if k.startswith("0") and k[1:] in CAMELOT_ORDER:
        return k[1:]
        
    return None

def get_camelot_distance(key1, key2):
    if not key1 or not key2: return 100
    
    idx1 = CAMELOT_ORDER.index(key1)
    idx2 = CAMELOT_ORDER.index(key2)
    
    num1, let1 = key1[:-1], key1[-1]
    num2, let2 = key2[:-1], key2[-1]
    
    if num1 == num2 and let1 != let2: return 1 # Major/Minor Mix
    
    diff = abs(idx1 - idx2)
    if diff > 12: diff = 24 - diff
    return diff

def parse_uploaded_file(uploaded_file):
    try:
        # Case 1: TXT / CSV
        if uploaded_file.name.endswith('.txt') or uploaded_file.name.endswith('.csv'):
            # Try parsing with tab delimiter first (Rekordbox TXT)
            try:
                df = pd.read_csv(uploaded_file, sep='\t', encoding='utf-16le')
                if 'Key' not in df.columns and len(df.columns) <= 1:
                    # If failed, try comma
                    uploaded_file.seek(0)
                    df = pd.read_csv(uploaded_file)
            except:
                uploaded_file.seek(0)
                df = pd.read_csv(uploaded_file)

            df.columns = [c.strip() for c in df.columns]
            return df
        
        # Case 2: XML
        elif uploaded_file.name.endswith('.xml'):
            tree = ET.parse(uploaded_file)
            root = tree.getroot()
            tracks = []
            collection = root.find('COLLECTION')
            if collection is None: return pd.DataFrame()
                
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
    # Cleanup columns
    df.columns = [c.strip() for c in df.columns]
    
    # 1. Standardize Keys (The Fix!)
    if 'Key' not in df.columns:
        st.error("Column 'Key' not found.")
        return df
        
    # Create a new column for processing, preserving original 'Key' for display if needed
    df['Camelot_Key'] = df['Key'].apply(standardize_key)
    
    # Filter valid
    valid_df = df[df['Camelot_Key'].notna()].copy()
    invalid_df = df[df['Camelot_Key'].isna()].copy()
    
    if valid_df.empty:
        st.warning("No valid keys found. Check if your file has Key/Tonality info.")
        return df

    # Group by Camelot Key
    groups = valid_df.groupby('Camelot_Key')
    unique_keys = valid_df['Camelot_Key'].unique().tolist()
    
    # Pathfinding
    sorted_keys = [unique_keys[0]]
    unique_keys.remove(unique_keys[0])
    
    while unique_keys:
        current_key = sorted_keys[-1]
        best_next_key = min(unique_keys, key=lambda k: get_camelot_distance(current_key, k))
        sorted_keys.append(best_next_key)
        unique_keys.remove(best_next_key)
        
    # Construct Final List
    final_playlist = []
    
    for key in sorted_keys:
        key_group = groups.get_group(key)
        
        # Convert BPM to numeric for sorting
        if 'BPM' in key_group.columns:
            key_group['BPM'] = pd.to_numeric(key_group['BPM'], errors='coerce')
            
        # Sort by BPM
        if energy_mode == "Ramp Up (Low -> High)":
            key_group = key_group.sort_values(by='BPM', ascending=True)
        elif energy_mode == "Ramp Down (High -> Low)":
            key_group = key_group.sort_values(by='BPM', ascending=False)
             
        final_playlist.append(key_group)
        
    if not invalid_df.empty:
        final_playlist.append(invalid_df)
        
    result = pd.concat(final_playlist)
    
    # Cleanup: remove the temporary column
    result = result.drop(columns=['Camelot_Key'])
    return result

# --- 4. Main UI ---
def main():
    st.title("Harmonic Flow Optimizer")
    
    st.markdown("""
    <div style='text-align: center; color: #888; margin-bottom: 20px;'>
    Instantly transform your raw playlist into a seamless harmonic journey.<br>
    Powered by the <b>Camelot Wheel</b> system for perfect key mixing.
    </div>
    """, unsafe_allow_html=True)
    
    with st.sidebar:
        st.header("⚙️ Settings")
        st.info("Supports **XML**, **TXT** and **CSV**.")
        
        energy_option = st.select_slider(
            "Energy Flow Strategy",
            options=["Ramp Down (High -> Low)", "Wave (Mixed)", "Ramp Up (Low -> High)"],
            value="Ramp Up (Low -> High)"
        )
    
    with st.container():
        uploaded_file = st.file_uploader("Upload Playlist", type=['xml', 'txt', 'csv'])
    
    if uploaded_file:
        df = parse_uploaded_file(uploaded_file)
        
        if not df.empty:
            st.success(f"Loaded {len(df)} tracks successfully!")
            
            with st.expander("📂 Preview Original Playlist"):
                st.dataframe(df.head(), use_container_width=True)
                
            if st.button("🚀 Optimize Magic"):
                with st.spinner("Translating keys & Calculating harmonic paths..."):
                    optimized_df = optimize_playlist(df, energy_mode=energy_option)
                    
                    st.divider()
                    st.markdown("<h3 style='text-align: center;'>✅ Optimized Result</h3>", unsafe_allow_html=True)
                    
                    # Metrics
                    col1, col2, col3 = st.columns(3)
                    col1.metric("Total Tracks", len(optimized_df))
                    
                    start_bpm = optimized_df.iloc[0]['BPM'] if 'BPM' in optimized_df.columns else "N/A"
                    col2.metric("Start BPM", f"{start_bpm}")
                    
                    start_key = optimized_df.iloc[0]['Key'] if 'Key' in optimized_df.columns else "N/A"
                    col3.metric("Start Key", f"{start_key}")
                    
                    # Result Table
                    display_cols = ['Artist', 'Track Title', 'Key', 'BPM']
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
