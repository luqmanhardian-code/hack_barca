# Rancangan Final: Ball Possession Detection — More Than A Hack 2027
### *Dokumen Teknis untuk Pembuatan Notebook*

> [!IMPORTANT]
> Dokumen ini adalah spesifikasi final. Model notebook-builder wajib mengikuti arsitektur, urutan, dan parameter yang dideskripsikan di sini.

---

## 0. Konteks Kritis (Wajib Dipahami)

| Fakta | Implikasi Desain |
|---|---|
| Metrik ranking: **spellF1**, bukan akurasi frame | Jangan optimize per-frame accuracy; optimize keutuhan segmen possession |
| Bola hilang **41% graded frames** | Semua fitur harus memiliki fallback saat `ball_x/y = NaN` |
| Ground truth publik hanya **5 menit / 17 possession** | Jangan hyperparameter tuning dari data ini; gunakan physics-informed defaults |
| Tidak ada ID pemain permanen (46 slot ≠ 22 orang) | Semua fitur berbasis **kolektif tim**, bukan individu |
| Label `X` → forward-fill oleh evaluator | Gunakan `X` saat occlusion di tengah possession; JANGAN di titik transisi |
| Ground truth diturunkan **mekanis dari corrected tracking** | Tidak ada smoothing ground truth → model harus belajar batas transisi tajam |
| Babak 2 mulai graded dari frame **110,808** tapi kickoff frame **113,742** | Frame 110,808–113,741 = 2,934 frame, semua `D`. Paksa hard rule. |

---

## 1. Pipeline Arsitektur End-to-End

```
┌─────────────────────────────────────────────────────────────────┐
│  TAHAP 0: DATA LOADING & ALIGNMENT                              │
│  ATD (tactical) + Smart Tagging → DataFrame 199,319 baris      │
└─────────────────────┬───────────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────────┐
│  TAHAP 1: FEATURE ENGINEERING (20 fitur)                        │
│  Spasial + Temporal + Smart Tagging + Derived                   │
└─────────────────────┬───────────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────────┐
│  TAHAP 2: WEAK LABEL GENERATION (90 menit penuh)                │
│  Rule-based dari Smart Tagging → pseudo-label H/A/D per frame   │
└─────────────────────┬───────────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────────┐
│  TAHAP 3: LGBM EMISSION MODEL                                   │
│  Train pada weak label → output P(H), P(A), P(D) per frame     │
└─────────────────────┬───────────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────────┐
│  TAHAP 4: PHYSICS-INFORMED HMM + VITERBI DECODING               │
│  Transition matrix manual → sequence decoding global optimal    │
└─────────────────────┬───────────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────────┐
│  TAHAP 5: HARD POST-PROCESSING RULES                            │
│  Dead ball lock + halftime enforcement + min-segment pruning    │
└─────────────────────┬───────────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────────┐
│  TAHAP 6: SUBMISSION & VALIDATION                               │
│  CSV 199,319 baris → validate_submission.py → spellF1 check    │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. Tahap 0: Data Loading & Alignment

### 2.1 ATD Loading
```python
# Gunakan kloppy untuk parsing EPTS
from kloppy import metrica
dataset = metrica.load_tracking_epts(meta_data=paths["atd_meta"], raw_data=paths["atd_raw"])
df = dataset.to_df()
# video_frame = frame_id - 1 (ATD 1-based → submission 0-based)
df["frame"] = df["frame_id"] - 1

# Konversi koordinat ke meter (pitch: 105.3 × 68.0 m)
PITCH_LENGTH, PITCH_WIDTH = 105.3, 68.0
df["ball_x_m"] = df["ball_x"] * PITCH_LENGTH
df["ball_y_m"] = df["ball_y"] * PITCH_WIDTH
# Kolom pemain: nama format "{slot}_x", "{slot}_y", "{slot}_s"
# Pisahkan slot home vs away menggunakan metadata XML
```

### 2.2 Smart Tagging Loading
```python
from kloppy import sportscode
events = sportscode.load(paths["smart_tagging"]).to_df()
# Konversi timestamp ke frame
events["start_frame"] = (events["timestamp"].dt.total_seconds() * 25).round().astype(int)
events["end_frame"] = (events["end_timestamp"].dt.total_seconds() * 25).round().astype(int)
```

### 2.3 Frame Ranges (Hard-coded, tidak perlu detect)
```python
PRE_MATCH   = (0, 11184)        # ungraded → X
HALF1       = (11185, 90651)    # graded
HALFTIME    = (90652, 110807)   # ungraded → X
HALF2_PRE   = (110808, 113741)  # graded tapi belum kickoff → semua D (hard rule)
HALF2       = (113742, 190197)  # graded
POST_MATCH  = (190198, 199318)  # ungraded → X
```

---

## 3. Tahap 1: Feature Engineering (20 Fitur)

> [!NOTE]
> Semua fitur harus menggunakan koordinat meter (bukan normalisasi 0-1). Semua fitur harus ada fallback untuk `ball_x/y = NaN`.

### 3.1 Kelompok A: Fitur Jarak ke Bola (tersedia saat bola ada)

| Nama Fitur | Formula | Fallback jika bola NaN |
|---|---|---|
| `dist_home_min` | jarak euclidean pemain home terdekat ke bola (m) | `NaN` → isi dengan `dist_home_centroid` |
| `dist_away_min` | jarak euclidean pemain away terdekat ke bola (m) | `NaN` → isi dengan `dist_away_centroid` |
| `dist_ratio` | `dist_home_min / (dist_away_min + 1e-5)` | `NaN` → 1.0 (neutral) |
| `n_home_near_ball` | jumlah pemain home dalam radius 3 meter dari bola | `NaN` → 0 |
| `n_away_near_ball` | jumlah pemain away dalam radius 3 meter dari bola | `NaN` → 0 |
| `ball_zone_density_ratio` | `n_home_near_ball / (n_away_near_ball + 1)` | `NaN` → 1.0 |

**Referensi:** Vidal-Codina et al. (2022) — Possession Zone (PZ): bola dalam radius ≤2m dari pemain = sinyal kuat possession.

### 3.2 Kelompok B: Fitur Posisi Bola

| Nama Fitur | Formula | Fallback jika bola NaN |
|---|---|---|
| `ball_x_m` | posisi x bola (meter, 0=garis kiri, 105=kanan) | `NaN` → forward-fill dalam window 10 frame |
| `ball_y_m` | posisi y bola (meter) | `NaN` → forward-fill dalam window 10 frame |
| `ball_in_home_half` | `ball_x_m < 52.5` → 1 (home half) | `NaN` → 0.5 |
| `dist_ball_to_sideline` | `min(ball_y_m, 68 - ball_y_m)` | `NaN` → 34.0 |
| `dist_ball_to_endline` | `min(ball_x_m, 105.3 - ball_x_m)` | `NaN` → 52.65 |
| `ball_speed` | dari kolom ATD langsung (m/s) | `NaN` → 0 |

**Referensi:** Vorobev et al. (2025) — bola dekat garis → state kandidat kuat "out of play" / Dead Ball.

### 3.3 Kelompok C: Fitur Formasi Tim (selalu tersedia)

| Nama Fitur | Formula | Catatan |
|---|---|---|
| `centroid_home_x` | rata-rata x semua slot home yang terlacak (m) | Selalu ada selama ada pemain |
| `centroid_away_x` | rata-rata x semua slot away yang terlacak (m) | Selalu ada |
| `centroid_diff_x` | `centroid_home_x - centroid_away_x` | Positif = home lebih maju |
| `spread_home` | std posisi x semua pemain home (m) | Tim menyerang → spread lebar |
| `spread_away` | std posisi x semua pemain away (m) | Tim bertahan → spread sempit |
| `dist_centroid_home_to_ball` | jarak centroid home ke bola (m) | Fallback `dist_home_min` saat bola ada |
| `dist_centroid_away_to_ball` | jarak centroid away ke bola (m) | Fallback `dist_away_min` saat bola ada |

**Referensi:** Renner et al. (2026) — centroid dan spread tim adalah sinyal kuat fase taktis dalam tracking tanpa ID pemain.

### 3.4 Kelompok D: Fitur Smart Tagging (selalu tersedia)

| Nama Fitur | Cara Hitung | Nilai |
|---|---|---|
| `is_set_piece` | frame dalam interval `code == "SET PIECES"` | 0/1 |
| `is_dead_ball_phase` | frame dalam interval code terkait dead ball (lihat tabel) | 0/1 |
| `smart_tag_team` | tim dari tag `Team` yang berlaku saat frame ini | 0=Home, 1=Away, -1=N/A |
| `frames_since_set_piece` | frame sejak interval SET PIECES terakhir berakhir | 0–∞ (clip ke 500) |

**Mapping `is_dead_ball_phase`** → aktifkan untuk code:
- `SET PIECES` (selalu dead ball)
- `GOALS` (gol → restart)
- Tambahkan threshold: frame dalam 25 frame **setelah** `end_frame` SET PIECES juga = 1

### 3.5 Kelompok E: Fitur Temporal (rolling/lag)

| Nama Fitur | Formula | Window |
|---|---|---|
| `frames_since_ball_seen` | frame sejak `ball_x` terakhir tidak NaN | — |
| `ball_visible` | `ball_x` tidak NaN → 1, else → 0 | — |
| `dist_ratio_roll25` | rolling mean `dist_ratio` window ±12 frame (backward) | 12 frame = 0.48 detik |

> [!TIP]
> Semua rolling features harus **backward-only** (tidak menggunakan frame masa depan). Gunakan `df["feat"].rolling(window=25, min_periods=1).mean()` bukan centered.

---

## 4. Tahap 2: Weak Label Generation

### Strategi: Rule-based Label 90 Menit Penuh

Tujuan: Memberi LightGBM data training ~199k baris, bukan hanya 7.5k (5 menit).

```
PRIORITAS LABEL (dari tertinggi ke terendah):
1. SET PIECES interval → D (dead ball)
2. HALF2_PRE frames (110808–113741) → D
3. PRE_MATCH, HALFTIME, POST_MATCH → X (tidak dilatih)
4. smart_tag_team = Home ("Barcelona") → H
5. smart_tag_team = Away ("Atletic Club") → A
6. smart_tag_team = N/A → gunakan nearest player heuristic
7. Frame tanpa coverage Smart Tagging → nearest player heuristic
```

**Nearest Player Heuristic** (fallback):
- Bola ada → tim pemain terdekat ke bola
- Bola tidak ada → tim yang centroid-nya lebih dekat ke posisi bola yang terakhir diketahui

> [!WARNING]
> Weak label BUKAN ground truth. Label ini memiliki noise signifikan (Smart Tagging bukan possesion label). LightGBM harus diperlakukan sebagai "emission probability estimator" yang menghasilkan *probability*, bukan label langsung.

---

## 5. Tahap 3: LightGBM Emission Model

### 5.1 Konfigurasi Training

```python
import lightgbm as lgb

# Input: 20 fitur dari Tahap 1
# Output: P(H), P(A), P(D) per frame — probabilitas 3 kelas

params = {
    "objective": "multiclass",
    "num_class": 3,
    "metric": "multi_logloss",
    "n_estimators": 500,
    "learning_rate": 0.05,
    "max_depth": 6,
    "num_leaves": 31,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "min_child_samples": 50,   # cegah overfit pada weak label
    "random_state": 42,
    "verbose": -1,
}
# Label encoding: H=0, A=1, D=2
```

### 5.2 Training Scheme

```
Data Training:
- Semua frame yang mendapat weak label (H atau A atau D) = graded frames + Smart Tagging coverage
- EXCLUDE: frame X (PRE_MATCH, HALFTIME, POST_MATCH)

Validation (hanya sanity check, bukan untuk tuning):
- 5 menit public GT (frame 11185–18684)
- Hanya cek log_loss, JANGAN adjust hyperparameter dari sini
```

### 5.3 Feature Importance Check
Setelah training, plot `lgb.plot_importance()`. Jika `dist_ratio`, `dist_home_min`, `is_set_piece` tidak masuk top-5 → ada bug di feature engineering.

---

## 6. Tahap 4: Physics-Informed HMM + Viterbi Decoding

### 6.1 Mengapa HMM, Bukan Hanya Rolling Vote?

| Aspek | Rolling Majority Vote | HMM + Viterbi |
|---|---|---|
| Optimal dalam? | Lokal (per jendela) | **Global** (seluruh sequence) |
| Bisa leverage emission probability? | Tidak (hanya label) | **Ya** (pakai P(H/A/D) dari LightGBM) |
| Handle transisi asimetris? | Tidak | **Ya** (D→H lebih sering dari H→A langsung) |
| Viterbi smooth otomatis? | Perlu pruning manual | **Ya, inherent** |

### 6.2 Transition Matrix (Physics-Informed, TIDAK dilearn dari data)

Alasan tidak di-learn: 5 menit / 17 possession → sample terlalu sedikit.
Parameter diset berdasarkan domain knowledge sepak bola + distribusi Yamamoto et al. (2024).

```python
import numpy as np

# State: 0=H, 1=A, 2=D
# Interpretasi: dalam 1 frame (1/25 detik), seberapa besar kemungkinan transisi?

# Possession sangat "sticky" → P(stay) tinggi
# H→A langsung sangat jarang (biasanya lewat D dulu)
# D→H/A relatif cepat setelah restart

TRANSITION_MATRIX = np.array([
    # ke H       ke A      ke D
    [0.9940,    0.0005,   0.0055],  # dari H
    [0.0005,    0.9940,   0.0055],  # dari A
    [0.0150,    0.0150,   0.9700],  # dari D
])
# Jumlah tiap baris = 1.0
# Interpretasi durasi rata-rata: H/A spell ~167 frame ~6.7 detik, D spell ~33 frame ~1.3 detik
# Referensi: Yamamoto et al. (2024) — distribusi Gamma possession spell

INITIAL_PROB = np.array([0.33, 0.33, 0.34])  # uniform (kickoff unknown)
# Override: frame pertama babak 1 (11185) = H atau A sesuai kickoff Smart Tagging
```

### 6.3 Viterbi Implementation

```python
def viterbi_decode(emission_probs, trans_matrix, init_prob):
    """
    emission_probs: array shape (N_frames, 3) — output softmax LightGBM
    trans_matrix: (3, 3) — log space untuk numerical stability
    init_prob: (3,) initial state distribution
    Returns: array (N_frames,) label index
    """
    import numpy as np
    n_frames, n_states = emission_probs.shape
    
    log_trans = np.log(trans_matrix + 1e-10)
    log_emit = np.log(emission_probs + 1e-10)
    log_init = np.log(init_prob + 1e-10)
    
    # DP tables
    viterbi = np.zeros((n_frames, n_states))
    backpointer = np.zeros((n_frames, n_states), dtype=int)
    
    # Initialization
    viterbi[0] = log_init + log_emit[0]
    
    # Recursion
    for t in range(1, n_frames):
        for s in range(n_states):
            scores = viterbi[t-1] + log_trans[:, s]
            backpointer[t, s] = np.argmax(scores)
            viterbi[t, s] = scores[backpointer[t, s]] + log_emit[t, s]
    
    # Backtrack
    states = np.zeros(n_frames, dtype=int)
    states[-1] = np.argmax(viterbi[-1])
    for t in range(n_frames - 2, -1, -1):
        states[t] = backpointer[t + 1, states[t + 1]]
    
    return states  # 0=H, 1=A, 2=D
```

> [!NOTE]
> Jalankan Viterbi **per babak** secara terpisah (babak 1: frame 11185–90651, babak 2: frame 113742–190197). Jangan jalankan melewati halftime.

### 6.4 Modifikasi untuk Bola NaN (inspirasi Vorobev et al., 2025)

Vorobev et al. mendefinisikan 4 state Markov termasuk `W` (Waiting/Occlusion). Adaptasi untuk kita:

Ketika `ball_visible = 0` (bola NaN):
- **Kurangi bobot emission** dari LightGBM (bola hilang → less informative)
- **Tingkatkan bobot transition** (lebih bergantung pada inersia state sebelumnya)

```python
# Di dalam loop Viterbi, modifikasi emission weight:
emission_weight = 0.7 if ball_visible[t] else 0.3
viterbi[t, s] = scores[backpointer[t, s]] + emission_weight * log_emit[t, s]
```

---

## 7. Tahap 5: Hard Post-Processing Rules

Urutan aplikasi (berurutan, bukan paralel):

### Rule 1: Halftime & Non-graded Frames → X
```python
labels[PRE_MATCH[0]:PRE_MATCH[1]+1] = "X"
labels[HALFTIME[0]:HALFTIME[1]+1] = "X"
labels[POST_MATCH[0]:POST_MATCH[1]+1] = "X"
```

### Rule 2: Pre-kickoff Babak 2 → D (Hard Override)
```python
# Frame 110808–113741: graded tapi semua D
labels[110808:113742] = "D"
```

### Rule 3: SET PIECES Interval → D (Hard Lock)
```python
for _, row in set_pieces_df.iterrows():
    # Tambah buffer: 5 frame sebelum start (bola mulai mati)
    start = max(0, row["start_frame"] - 5)
    end = min(199318, row["end_frame"])
    labels[start:end+1] = "D"
```

### Rule 4: Minimum Segment Duration Pruning
```python
# Segmen possession < MIN_SPELL_FRAMES → merge ke segmen tetangga
MIN_SPELL_FRAMES = 15  # 0.6 detik — possession nyata hampir tidak pernah < ini
# Implementasi: scan segmen, cek durasi, merge yang terlalu pendek
```

**Referensi:** Link & Hoernig (2017) — Individual Ball Possession minimum duration ≈ 0.5–1 detik untuk kontrol nyata.

### Rule 5: Abstain (X) Strategy untuk Bola Hilang Panjang
```python
# Jika bola hilang >75 frame BERTURUT-TURUT (3 detik) di luar SET PIECES
# → kemungkinan bola keluar lapangan → pertimbangkan X (forward-fill aman)
# Hanya terapkan jika label sekitar konsisten (bukan di titik transisi)
```

---

## 8. Tahap 6: Submission & Validation

```python
import pandas as pd

# Format final
submission = pd.DataFrame({
    "frame": range(199319),
    "label": labels  # array string "H"/"A"/"D"/"X"
})

# Validasi
submission.to_csv("evaluation/results/our_submission.csv", index=False)
# Jalankan:
# python evaluation/validate_submission.py evaluation/results/our_submission.csv
# python evaluation/run_evaluation.py --bootstrap 1000
```

### Sanity Check Target
| Metrik | Target Minimal | Keterangan |
|---|---|---|
| Total possession spells | 150–250 | Di luar range → ada flickering atau over-smoothing |
| Rata-rata durasi spell | 10–20 detik | Di bawah 5 detik → smoothing kurang |
| spellF1 public (5 menit) | >0.35 | Baseline floor: 0.2433 |
| macroF1 public | >0.60 | Informatif, bukan target utama |

---

## 9. Referensi → Implementasi Mapping

| Referensi | Yang Diadopsi |
|---|---|
| **Vidal-Codina et al. (2022)** | Possession Zone radius 2–3m untuk fitur `n_home/away_near_ball` |
| **Kim et al. — PathCRF (2026)** | Inspirasi Viterbi global decoding; konsep "anti-flickering" via sequence model |
| **Vorobev et al. (2025)** | Modifikasi emission weight saat bola NaN (state W/Occlusion) |
| **Yamamoto et al. (2024)** | Kalibrasi transition matrix: durasi rata-rata possession spell → P(stay) = 0.994 |
| **Link & Hoernig (2017)** | Minimum possession duration = 0.5–1 detik → `MIN_SPELL_FRAMES = 15` |
| **Renner et al. (2026)** | Centroid & spread tim sebagai fitur kolektif tanpa ID pemain |
| **Metrica Docs (2027)** | Definisi resmi `D`: mechanical derivation dari corrected tracking |
| **LaurieOnTracking** | Template kalkulasi kecepatan (Savitzky-Golay) & pitch control (opsional) |

---

## 10. Urutan Notebook yang Harus Dibuat

> [!IMPORTANT]
> Buat **satu notebook tunggal** yang menjalankan seluruh pipeline dari data mentah hingga submission. Modular per section.

```
notebook: 04_possession_model.ipynb
│
├── Section 0: Setup & Import
├── Section 1: Data Loading (ATD + Smart Tagging)
├── Section 2: Feature Engineering (20 fitur)
├── Section 3: Weak Label Generation
├── Section 4: LightGBM Training
├── Section 5: HMM Viterbi Decoding
├── Section 6: Post-Processing Rules
├── Section 7: Submission & Evaluation
└── Section 8: Error Analysis (opsional)
```

### Dependencies
```
lightgbm>=4.0
kloppy>=4.0
numpy, pandas, scipy
scikit-learn (untuk label encoding)
matplotlib (untuk visualisasi feature importance)
```

---

## 11. Parameter Default (Physics-Informed, Jangan Diubah dari Public GT)

| Parameter | Nilai | Alasan |
|---|---|---|
| `MIN_SPELL_FRAMES` | 15 | 0.6 detik — minimum possession nyata |
| `BALL_PROXIMITY_RADIUS` | 3.0 m | PZ radius dari Vidal-Codina |
| `TRANSITION_H_STAY` | 0.9940 | ~167 frame rata-rata spell |
| `TRANSITION_D_STAY` | 0.9700 | ~33 frame rata-rata dead ball |
| `EMISSION_WEIGHT_NO_BALL` | 0.3 | Bola NaN → kurangi kepercayaan emission |
| `SET_PIECE_BUFFER_FRAMES` | 5 | Buffer pre-start set piece |
| `BALL_NAN_FORWARD_FILL` | 10 frame | Fill posisi bola untuk fitur spatial |
| `FPS` | 25 | Frame rate video tactical |
| `PITCH_LENGTH` | 105.3 m | games.py verified |
| `PITCH_WIDTH` | 68.0 m | games.py verified |
