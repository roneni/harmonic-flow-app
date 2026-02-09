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

# --- CUSTOM CSS (DARK MODE / PSYTRANCE) ---
st.markdown("""
    <style>
    /* Import Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&family=Roboto:wght@300;400&display=swap');

    /* General App Background */
    .stApp {
        background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%);
        color: #ffffff;
        font-family: 'Roboto', sans-serif;
    }

    /* Titles */
    h1 {
        font-family: 'Orbitron', sans-serif !important;
        background: -webkit-linear-gradient(45deg, #00d2ff, #3a7bd5);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        padding-bottom: 20px;
        text-shadow: 0px 0px 20px rgba(0, 210, 255, 0.3);
    }
    
    h2, h3 {
        font-family: 'Orbitron', sans-serif !important;
        color: #e0e0e0 !important;
    }

    /* Hide Streamlit Default Elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background-color: rgba(0, 0, 0, 0.2);
        border-right: 1px solid rgba(255, 255, 255, 0.1);
    }

    /* Buttons */
    div.stButton > button {
        width: 100%;
        background: linear-gradient(90deg, #00d2ff 0%, #3a7bd5 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 15px 30px;
        font-size: 18px;
        font-weight: bold;
        font-family: 'Orbitron', sans-serif;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        transition: all 0.3s ease;
        box-shadow: 0 0 15px rgba(0, 210, 255, 0.5);
    }
    
    div.stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 0 25px rgba(0, 210, 255, 0.8);
    }

    /* Metrics (Big Numbers) */
    div[data-testid="stMetricValue"] {
        color: #00d2ff !important;
        font-family: 'Orbitron', sans-serif;
        text-shadow: 0 0 10px rgba(0, 210, 255, 0.3);
    }

    /* Dataframe/Table Styling */
    div[data-testid="stDataFrame"] {
        background-color: rgba(255, 255, 255, 0.05);
        border-radius: 10px;
        padding: 10px;
    }

    /* File Uploader */
    .stFileUploader {
        border: 1px dashed #00d2ff;
        border-radius: 10px;
        padding: 20px;
        background: rgba(0, 210, 255, 0.05);
    }
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
    
    num1, let1 = key1[:-1], key
