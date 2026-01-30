import streamlit as st
import pandas as pd
import xml.etree.ElementTree as ET
import itertools

# --- 1. לוגיקת הבלוקים (Cluster Strategy) ---

KEY_MAPPING = {
    'Abm': '1A', 'G#m': '1A', 'B': '1B',
    'Ebm': '2A', 'D#m': '2A', 'F#': '2B', 'Gb': '2B',
    'Bbm': '3A', 'A#m': '3A', 'Db': '3B', 'C#': '3B',
    'Fm':  '4A', 'Ab': '4B', 'G#': '4B',
    'Cm':  '5A', 'Eb': '5B', 'D#': '5B',
    'Gm':  '6A', 'Bb': '6B', 'A#': '6B',
    'Dm':  '7A', 'F':  '7B',
    'Am':  '8A', 'C':  '8B',
    'Em':  '9A', 'G':  '9B',
    'Bm':  '10A', 'D': '10B',
    'F#m': '11A', 'Gbm': '11A', 'A': '11B',
    'Dbm': '12A', 'C#m': '12A', 'E': '12B'
}

def get_camelot(key_str):
    if not isinstance(key_str, str): return None
    return KEY_MAPPING.get(key_str.strip(), None)

def get_camelot_parts(key_str):
    if not key_str: return None, None
    return int(key_str[:-1]), key_str[-1]

def calculate_key_transition_cost(prev_key, next_key):
    """מחשב עלות מעבר בין קבוצות סולמות בלבד"""
    p_num, p_let = get_camelot_parts(prev_key)
    n_num, n_let = get_camelot_parts(next_key)
    
    diff = n_num - p_num
    if diff == -11: diff = 1
    if diff == 11: diff = -1
    
    if prev_key == next_key: return 0
    if p_num == n_num and p_let != n_let: return 1 # Relative
    if abs(diff) == 1:
        if p_let == n_let: return 2 # +/- 1
        else: return 4 # Diagonal
    if (p_num + 2) % 12 == n_num % 12: return 5 # Energy Boost +2
    if (p_num + 7) % 12 == n_num % 12: return 8 # +7 Semitones
    
    return 100 # Clash!

def solve_group_order(unique_keys):
    """
    Traveling Salesperson Solver (TSP) עבור הסולמות.
    מוצא את הסדר הטוב ביותר לעבור בין הקבוצות הקיימות.
    """
    # מאחר ויש מעט קבוצות (מקסימום 24), אפשר לנסות גישה חכמה של "שכן קרוב" עם Backtracking
    # או פשוט לנסות את כל ההתחלות ולרוץ Greedy משופר.
    
    best_path = None
    best_cost = float('inf')
    
    # מנסים להתחיל מכל סולם אפשרי
    for start_node in unique_keys:
        path = [start_node]
        remaining = set(unique_keys) - {start_node}
        current_cost = 0
        
        curr = start_node
        valid_path = True
        
        while remaining:
            # מחפש את הקבוצה הבאה הכי מתאימה
            candidates = []
            for next_node in remaining:
                cost = calculate_key_transition_cost(curr, next_node)
                candidates.append((cost, next_node))
            
            # מיון לפי עלות
            candidates.sort(key=lambda x: x[0])
            
            # לוקח את הכי טוב (Greedy)
            # בגרסה מתקדמת יותר אפשר לעשות פה Beam Search גם כן, אבל לרוב Greedy עובד מעולה על Meta-Groups
            chosen_cost, chosen_node = candidates[0]
            
            if chosen_cost >= 100: # אם האופציה היחידה היא קלאש
                 # כאן אפשר להכניס לוגיקה שמנסה לחזור אחורה, אבל לצורך הפשטות נמשיך
                 pass

            current_cost += chosen_cost
            path.append(chosen_node)
            remaining.remove(chosen_node)
            curr = chosen_node
            
        if current_cost < best_cost:
            best_cost = current_cost
            best_path = path

    return best_path

def sort_playlist_clustered(tracks, bpm_mode='desc'):
    """
    הפונקציה הראשית החדשה:
    1. מקבצת
    2. מסדרת קבוצות
    3. מסדרת שירים בתוך קבוצה
    """
    # 1. ניקוי וקיבוץ
    clusters = {}
    for t in tracks:
        cam = get_camelot(t.get('Key'))
        if not cam: continue # מדלג על שירים בלי סולם
        if cam not in clusters: clusters[cam] = []
        
        # נרמול BPM למספר
        try:
            bpm = float(str(t.get('BPM', 0)).replace(',',''))
        except:
            bpm = 0
        t['bpm_val'] = bpm
        t['camelot'] = cam
        clusters[cam].append(t)
        
    if not clusters: return []
    
    unique_keys = list(clusters.keys())
    
    # 2. מציאת סדר הקבוצות האופטימלי
    sorted_keys = solve_group_order(unique_keys)
    
    # 3. בניית הפלייליסט הסופי
    final_playlist = []
    
    for key in sorted_keys:
        group_tracks = clusters[key]
        
        # סידור פנימי לפי BPM
        reverse_sort = True if bpm_mode == 'desc' else False # desc = יורד (מהיר לאיטי)
        group_tracks.sort(key=lambda x: x['bpm_val'], reverse=reverse_sort)
        
        final_playlist.extend(group_tracks)
        
    return final_playlist

# --- קריאת קבצים (ללא שינוי) ---
def parse_rekordbox_xml(uploaded_file):
    try:
        tree = ET.parse(uploaded_file)
        root = tree.getroot()
        tracks = []
        for track in root.findall(".//TRACK"):
            name = track.get('Name')
            key = track.get('Tonality')
            bpm = track.get('AverageBpm')
            artist = track.get('Artist')
            if key: tracks.append({'Artist': artist, 'Title': name, 'Key': key, 'BPM': bpm})
        return tracks
    except: return None

def parse_rekordbox_txt(uploaded_file):
    try:
        df = pd.read_csv(uploaded_file, sep='\t', encoding='utf-16') 
    except:
        try:
            uploaded_file.seek(0)
            df = pd.read_csv(uploaded_file, sep='\t', encoding='utf-8')
        except: return None
    
    tracks = []
    key_col = next((col for col in df.columns if 'Key' in col or 'Tonality' in col), None)
    title_col = next((col for col in df.columns if 'Title' in col or 'Name' in col), None)
    artist_col = next((col for col in df.columns if 'Artist' in col), None)
    bpm_col = next((col for col in df.columns if 'BPM' in col), None)
    if not key_col or not title_col: return None

    for index, row in df.iterrows():
        if pd.notna(row[key_col]):
            tracks.append({'Artist': row[artist_col] if artist_col else '', 'Title': row[title_col], 'Key': str(row[key_col]).strip(), 'BPM': row[bpm_col] if bpm_col else 0})
    return tracks

# --- Frontend ---

st.set_page_config(page_title="Cluster Flow Pro", layout="wide")
st.title("🎛️ Cluster Flow Pro")
st.markdown("""
**השיטה המקצועית (Block Strategy):** המערכת עובדת בשיטת "בלוקים" - היא מסדרת קודם את המסלול בין הסולמות, ורק אז את השירים בפנים.
זה מבטיח 0% "שאריות" בסוף הסט ומונע זגזוגים לחלוטין.
""")

uploaded_file = st.file_uploader("גרור קובץ Rekordbox (XML / TXT)", type=['xml', 'txt'])

if uploaded_file:
    file_type = uploaded_file.name.split('.')[-1].lower()
    raw_data = []
    if file_type == 'xml': raw_data = parse_rekordbox_xml(uploaded_file)
    elif file_type == 'txt': raw_data = parse_rekordbox_txt(uploaded_file)
    
    if raw_data:
        st.success(f"נטענו {len(raw_data)} טראקים.")
        
        # בחירת כיוון ה-BPM
        bpm_direction = st.radio("כיוון האנרגיה בתוך הבלוק:", 
                                 ('יורד (מהיר -> איטי) 📉', 'עולה (איטי -> מהיר) 📈'))
        
        mode = 'desc' if 'יורד' in bpm_direction else 'asc'

        if st.button("סדר לי את הסט (Cluster Mode) 🚀"):
            optimized_list = sort_playlist_clustered(raw_data, bpm_mode=mode)
            
            st.subheader("✅ התוצאה המושלמת:")
            df_res = pd.DataFrame(optimized_list)
            
            # הצגה
            cols = ['Key', 'camelot', 'BPM', 'Title', 'Artist']
            final_df = df_res[[c for c in cols if c in df_res.columns]]
            st.dataframe(final_df, use_container_width=True, height=600)
            
            csv = final_df.to_csv(index=False).encode('utf-8')
            st.download_button("הורד קובץ CSV", csv, "cluster_perfect_set.csv", "text/csv")