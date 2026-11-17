# 📋 Pembagian Track Pengerjaan: More Than a Hack 2027

Dokumen ini merangkum pembagian kerja modular yang dapat dikerjakan secara paralel oleh tim. Setiap track beroperasi secara independen dan bermuara pada array/kolom indeks frame `0` sampai `199.318` (total 199.319 frame).

---

## Track 1: Spatial & Tracking Feature Engineering
*Fokus pada ekstraksi data spasial pergerakan pemain dan bola dari Automatic Tracking Data (ATD).*

### Tanggung Jawab:
1. **Ekstraksi Data ATD**: Membaca koordinat posisi dan kecepatan pemain serta bola menggunakan `load_atd.py`.
2. **Kalkulasi Jarak Kedekatan**: Menghitung jarak pemain terdekat ke bola untuk Tim Home (`min_dist_home`) dan Tim Away (`min_dist_away`) pada frame di mana bola terdeteksi.
3. **Penanganan Oklusi Bola (~43% frame hilang)**:
   - Menghitung posisi rata-rata tim (*team centroid* $x, y$) dan sebaran pemain untuk menentukan tim mana yang mengontrol ruang saat bola tidak terdeteksi.
4. **Proyeksi Lapangan (*Opsional/Lanjutan*)**: Memanfaatkan matriks proyeksi `load_homography.py` untuk mengonversi piksel ke jarak metrik lapangan nyata (meter).

### Deliverable / Output:
* Array / Kolom Series per frame (panjang 199.319 baris):
  * `home_possession_confidence`: float [0.0 - 1.0]
  * `away_possession_confidence`: float [0.0 - 1.0]

---

## Track 2: Dead Ball (`D`) & Set Piece Detection Engine
*Fokus pada identifikasi situasi bola mati dan penghentian permainan memanfaatkan anotasi taktis dan perilaku spasial.*

### Tanggung Jawab:
1. **Parsing Smart Tagging**: Mengambil anotasi fase permainan dan kejadian bola mati dari `load_smart_tagging.py` (misal: `SET PIECES`, `THROW-IN`, `CORNER KICK`, `GOAL KICK`, `FREE KICK`, `PENALTY`).
2. **Sinkronisasi Temporal**: Mengonversi stempel waktu detik ke indeks frame (`frame = int(second * 25)`).
3. **Heuristik Spasial Pendukung**:
   - Mendeteksi penurunan drastis pada kecepatan rata-rata seluruh pemain (*stagnant team velocity*).
   - Mendeteksi posisi bola di luar garis batas lapangan atau keberadaan pemain di luar lapangan (*throw-in*).

### Deliverable / Output:
* Array / Boolean Mask per frame (panjang 199.319 baris):
  * `is_dead_ball`: boolean [True/False] atau skor probabilitas `dead_ball_prob` [0.0 - 1.0].

---

## Track 3: Temporal Smoothing & Spell Post-Processing Engine
*Fokus pada optimalisasi metrik ranking utama (`spellF1`) melalui pembersihan fluktuasi cepat (flickering) dan pemodelan kontinuitas penguasaan bola.*

### Tanggung Jawab:
1. **Filtering Prediksi Semu (Pruning)**:
   - Menghapus atau menggabungkan segmen penguasaan mikro yang berdurasi terlalu pendek (< 1 detik atau < 25 frame) ke segmen dominan di sekitarnya.
2. **Centred Majority Voting / Rolling Filter**:
   - Menguji dan menetapkan jendela penghalusan temporal yang sesuai dengan dinamika fisik sepak bola (25–50 frame / 1–2 detik).
3. **Pemanfaatan Strategis Label Abstain (`X`)**:
   - Menerapkan label `X` pada celah oklusi sementara di tengah rangkaian kepemilikan tim yang sama agar tidak memecah keutuhan *possession spell*.
4. **Regulasi Transisi**:
   - Mencegah perpindahan instan antar-tim dalam 1 frame tanpa melalui fase perebutan atau bola mati.

### Deliverable / Output:
* Modul/fungsi Python mandiri:
  ```python
  def optimize_spells(raw_labels: np.ndarray) -> np.ndarray:
      """Menerima array label mentah per frame (panjang 199.319),

      mengembalikan array label teroptimasi bebas flickering.
      """
  ```

---

## Track 4: Decision Fusion, Evaluasi & Pipeline Submission
*Fokus pada penggabungan seluruh sinyal fitur, pengujian performa lokal, dan pembuatan berkas akhir submission.*

### Tanggung Jawab:
1. **Harness Evaluasi Lokal**:
   - Menjalankan evaluasi pada 5 menit ground truth publik menggunakan `evaluation/run_evaluation.py` dengan parameter `--bootstrap 1000` untuk mengukur interval keyakinan skor.
2. **Global Sanity-Checking**:
   - Memverifikasi total segmen penguasaan bola (*possession spells*) sepanjang 90 menit agar berada di rentang normal pertandingan sepak bola (~160–220 *spells*).
3. **Penggabungan Logika (Decision Fusion)**:
   - Menggabungkan sinyal dari Track 1 dan Track 2 (misal: aturan hierarkis di mana status Dead Ball memiliki prioritas utama, diikuti evaluasi tingkat keyakinan Home vs Away).
4. **Validasi & Ekspor Berkas**:
   - Menghasilkan file submission berformat CSV 2 kolom (`frame`, `label`).
   - Memastikan integritas file dengan menjalankan `evaluation/validate_submission.py`.

### Deliverable / Output:
* Notebook orkestrasi integrasi akhir (`final_submission_pipeline.ipynb`).
* Berkas submission valid: `submission.csv` (199.319 baris).

---

## 📋 Kesepakatan Kontrak Antarmuka (Interface Contract)

Untuk memastikan integrasi antar-track berjalan tanpa hambatan:
1. **Indeks Frame Baku**: Seluruh array atau Series DataFrame wajib memiliki panjang tepat **199.319 baris**, merepresentasikan frame 0 hingga frame 199.318.
2. **Label Baku**: Karakter keluaran resmi hanya terdiri dari `'H'`, `'A'`, `'D'`, atau `'X'`.
3. **Penyimpanan Antara (Intermediate Storage)**: Sinyal fitur per frame antar-track disarankan disimpan dalam format `.parquet` atau `.npz` untuk mempercepat pemuatan data tanpa membebani memori (RAM).
