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

# --- 2. Camelot Logic & Translation ---
CAMELOT_ORDER = [
    "1A", "1B", "2A", "2B", "3A", "3B", "4A", "4B",
    "5A", "5B", "6A", "6B", "7A", "7B", "8A", "8B",
    "9A", "9B", "10A", "10B", "11A", "11B", "12A", "12B"
]

# Translator: Musical Key -> Camelot Key
KEY_MAPPING = {
    # Major
    "B": "1B", "F#": "2B", "Gb": "2B", "Db": "3B", "C#": "3B",
    "Ab": "4B", "Eb": "5B", "Bb": "6B", "F": "7B", "C": "8B",
    "G": "9B", "D": "10B", "A": "11B", "E": "12B",
    
    # Minor
    "Abm": "1A", "G#m": "1A", "Ebm": "2A", "D#m": "2A",
    "Bbm": "3A", "A#m": "3A", "Fm": "4A", "Cm": "5A",
    "Gm": "6A", "Dm": "7A", "Am": "8A", "Em": "9A",
    "Bm": "10A", "F#m": "11A", "Gbm": "11A", "C#m": "12A", "Dbm": "12A"
}

def standardize_key(key_val):
    if not isinstance(key_val, str):
        return None
    k = key_val.strip()
    if k in CAMELOT_ORDER:
        return k
    if k in KEY_MAPPING:
        return KEY_MAPPING[k]
    if k.startswith("0") and k[1:] in CAMELOT_ORDER:
        return k[1:]
    return None

def get_camelot_distance(key1, key2):
    if not key1 or not key2: return 100
    idx1 = CAMELOT_ORDER.index(key1)
    idx2 = CAMELOT_ORDER.index(key2)
    num1, let1 = key1[:-1], key1[-1]
    num2, let2 = key2[:-1], key2[-1]
    if num1 == num2 and let1 != let2: return 1
    diff = abs(idx1 - idx2)
    if diff > 12: diff = 24 - diff
    return diff

def parse_uploaded_file(uploaded_file):
    try:
        if uploaded_file.name.endswith('.txt') or uploaded_file.name.endswith('.csv'):
            try:
                df = pd.read_csv(uploaded_file, sep='\t', encoding='utf-16le')
                if 'Key' not in df.columns and len(df.columns) <= 1:
                    uploaded_file.seek(0)
                    df = pd.read_csv(uploaded_file)
            except:
                uploaded_file.seek(0)
                df = pd.read_csv(uploaded_file)
            df.columns = [c.strip() for c in df.columns]
            return df
        
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
    df.columns = [c.strip() for c in df.columns]
    if 'Key' not in df.columns:
        st.error("Column 'Key' not found.")
        return df
        
    df['Camelot_Key'] = df['Key'].apply(standardize_key)
    valid_df = df[df['Camelot_Key'].notna()].copy()
    invalid_df = df[df['Camelot_Key'].isna()].copy()
    
    if valid_df.empty:
        st.warning("No valid keys found.")
        return df

    groups = valid_df.groupby('Camelot_Key')
    unique_keys = valid_df['Camelot_Key'].unique().tolist()
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
        if 'BPM' in key_group.columns:
            key_group['BPM'] = pd.to_numeric(key_group['BPM'], errors='coerce')
        
        if energy_mode == "Ramp Up (Low -> High)":
            key_group = key_group.sort_values(by='BPM', ascending=True)
        elif energy_mode == "Ramp Down (High -> Low)":
            key_group = key_group.sort_values(by='BPM', ascending=False)
        final_playlist.append(key_group)
        
    if not invalid_df.empty:
        final_playlist.append(invalid_df)
    
    result = pd.concat(final_playlist)
    result = result.drop(columns=['Camelot_Key'])
    return result

# --- 4. Main UI ---
def main():
    st.title("Harmonic Flow Optimizer")
    
    st.markdown("""
    **Sequence your set like a pro.**
    Powered by Camelot Wheel logic.
    """)
    
    with st.sidebar:
        st.header("Settings")
        st.info("Supported: XML, TXT, CSV")
        energy_option = st.select_slider(
            "Energy Flow",
            options=["Ramp Down (High -> Low)", "Wave (Mixed)", "Ramp Up (Low -> High)"],
            value="Ramp Up (Low -> High)"
        )
    
    uploaded_file = st.file_uploader("Upload Playlist", type=['xml', 'txt', 'csv'])
    
    if uploaded_file:
        df = parse_uploaded_file(uploaded_file)
        if not df.empty:
            st.success(f"Loaded {len(df)} tracks")
            if st.button("Optimize Magic"):
                optimized_df = optimize_playlist(df, energy_mode=energy_option)
                st.write("### Optimized Result")
                st.dataframe(optimized_df)
                csv = optimized_df.to_csv(index=False).encode('utf-8')
                st.download_button("Download CSV", csv, "sorted.csv", "text/csv")

if __name__ == "__main__":
    main()
