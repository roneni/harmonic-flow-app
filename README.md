# 🎵 Harmonic Flow Optimizer (Cluster Logic)

**Stop guessing your next track.** This AI-powered tool organizes Rekordbox playlists into a mathematically perfect harmonic sequence.

Unlike standard "greedy" algorithms that get stuck in harmonic dead-ends, this tool uses a **Cluster Strategy** (similar to solving the Traveling Salesperson Problem for musical keys) to ensure a seamless flow from start to finish.

## 🚀 Key Features

* **Cluster & Path Strategy:** The algorithm first groups tracks by key, maps the optimal route between key groups, and *then* sorts the internal tracks. This guarantees **0% harmonic clashes** and no "orphan" tracks left at the end.
* **Anti-ZigZag Logic:** Ensures a linear progression through the Camelot Wheel without jumping back and forth between keys.
* **Smart Energy Control:** Sorts tracks within each key block by BPM (Ascending or Descending) based on your preference.
* **Rekordbox Ready:** Supports XML and TXT export formats directly from Rekordbox.

## 🛠 How It Works

1.  **Upload:** Drag & drop your Rekordbox playlist (XML or TXT).
2.  **Configure:** Choose your desired energy flow (e.g., Start fast -> End slow).
3.  **Optimize:** The algorithm calculates the best harmonic path.
4.  **Download:** Get a CSV file ready to be re-imported or used as a set list.

## 📦 Installation (Local)

If you prefer to run it on your own machine:

```bash
# 1. Clone the repo
git clone [https://github.com/YOUR_USERNAME/harmonic-flow-app.git](https://github.com/YOUR_USERNAME/harmonic-flow-app.git)

# 2. Install requirements
pip install -r requirements.txt

# 3. Run the app
streamlit run app.py
