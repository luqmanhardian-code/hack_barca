# Ringkasan Praktis: 3 Starter Notebooks (More Than A Hack 2027)

Dokumen ini merangkum alur kerja teknis, temuan kunci, dan catatan kritis dari ketiga starter notebooks yang telah kita jalankan: dari eksplorasi data taktis, inspeksi tracking pemain dan bola, hingga pembuatan model baseline serta evaluasi metrik kompetisi.

---

## 1. Notebook 01: Smart Tagging (`01_smart_tagging.ipynb`)

Notebook ini mengeksplorasi data anotasi taktis otomatis (*Smart Tagging*) dari Metrica Sports untuk memahami struktur fase permainan dan bola mati (*set pieces*).

### Poin-Poin Kunci
* **Format & Pemuatan Data:** 
  * Menggunakan format standar industri analisis sepak bola (**SportsCode XML**).
  * Dibaca menggunakan library `kloppy.sportscode.load(...)` dan dikonversi ke `pandas.DataFrame`.
  * Menghasilkan **638 baris/interval** anotasi taktis.
* **Struktur Kolom & Data:**
  * Setiap baris mewakili rentang waktu: `timestamp` dan `end_timestamp` (dalam format pandas timedelta sejak awal video).
  * `code`: Nama fase permainan atau *set piece* dalam format huruf kapital (**UPPERCASE**), contohnya `PLAYERS IN THE BOX`, `BALL IN FINAL THIRD`, `SET PIECES`, `PROGRESSION`.
  * Tag pendukung: Menggunakan format **Title Case**, misalnya kolom `Type` pada `SET PIECES` berisi `Throw-in` (26), `Corner Kick` (12), `Goal Kick` (10), `Kick Off (Start)` (2), dll.
* **Konversi Waktu ke Frame Video:**
  * Video taktis berjalan pada **25 FPS**.
  * Konversi frame dihitung dengan rumus:
    $$\text{frame} = \text{round}(\text{seconds} \times 25)$$
  * Menghasilkan kolom `start_frame` dan `end_frame` yang sinkron dengan nomor frame video.

### Catatan Kritis & Jebakan Data
1. **Kolom `Team` Tidak Selalu Terisi:**
   * Terdapat 36 baris berlabel `N/A`, termasuk **seluruh lemparan ke dalam (*Throw-in*)**. Kita tidak bisa bergantung pada kolom ini untuk mengetahui tim pelempar bola.
2. **Interval adalah Jendela Waktu (*Window*), Bukan Titik Instan:**
   * Anotasi *set piece* mencakup rentang durasi beberapa detik di sekitar momen bola dimainkan kembali, bukan frame persis saat bola ditendang atau dilempar.

### Mengapa Sangat Bernilai (*Why It Is Worth Using Anyway*)
* **Prior Kuat Bebas Biaya (*Free Strong Prior*):** 
  * Setiap fase permainan memiliki label `Team`, memberikan sinyal awal tim mana yang mengontrol penguasaan bola (*possession*).
  * Setiap `SET PIECES` adalah *restart*, menandai batas berakhirnya fase bola mati (*dead-ball*).
* **Tantangan Batas (*Boundary Mismatch*):** 
  * Interval data ini adalah **fase taktis (*phase*)**, bukan **possession murni**. Satu fase (seperti *Build Up*) bisa mencakup sebagian *possession*, tepat satu *possession*, atau bahkan dua *possession* berbeda jika terjadi pergantian penguasaan bola (*turnover*) mendadak.

---

## 2. Notebook 02: Tracking ATD (`02_tracking_atd.ipynb`)

Notebook ini membedah **Automatic Tracking Data (ATD)** — data koordinat posisi $(x, y)$ dan kecepatan pemain serta bola per frame hasil deteksi *computer vision*.

### Poin-Poin Kunci
* **Format & Pemuatan Data:**
  * Menggunakan format standar **FIFA/EPTS** (metadata XML + berkas teks mentah koordinat).
  * Dibaca menggunakan `kloppy.metrica.load_tracking(...)`.
  * Pertandingan penuh terdiri dari **199.319 frame** kontigu.
* **Sinkronisasi Frame (*Alignment*):**
  * Tracking ATD menghitung frame mulai dari angka **1** (*1-based*), sedangkan submission lomba menghitung frame video mulai dari angka **0** (*0-based*).
  * Penyelarasannya cukup dengan pengurangan sederhana:
    $$\text{video\_frame} = \text{frame\_id} - 1$$
  * Verifikasi streaming via `load_atd.check_alignment()` mengonfirmasi data sinkron 100% tanpa frame yang melompat.
* **Dimensi Lapangan & Visualisasi:**
  * Lapangan dinormalisasi ke meter nyata ($105 \times 68\text{ meter}$).
  * Skrip `utils.plot_frame` dan `utils.animate_frames` memungkinkan kita memeriksa formasi kedua tim dan bola secara 2D pada frame tertentu (misal kickoff babak 1 pada frame 11185).

### Realitas Kritis Tracking Data
1. **Tidak Ada Identitas Pemain Tetap (*No Player Identities*):**
   * Terdapat **46 track slot** untuk 22 pemain lapangan.
   * Model deteksi visual sering berganti slot saat pemain saling menumpuk. Nomor punggung (*shirt number*) pada data hanyalah nomor slot, bukan nomor punggung pemain asli. Meski demikian, pembagian tim (*Barcelona* vs *Athletic Club*) tetap konsisten.
2. **Posisi Bola Hilang Sekitar 43% Waktu (*Missing Ball*):**
   * Bola adalah sinyal paling krusial sekaligus paling tidak lengkap.
   * Sepanjang pertandingan penuh, bola hanya terlacak pada **56,9% frame** (artinya ~43,1% frame berada dalam kondisi *missing* / `NaN`). Kita tidak boleh merancang model yang berasumsi bola selalu ada.
   * Saat bola hilang, **pergerakan dan bentuk formasi tim (*team shape*)** menjadi petunjuk utama untuk menentukan siapa yang menguasai permainan.

---

## 3. Notebook 03: First Submission & Scoring (`03_first_submission.ipynb`)

Notebook ini menghubungkan seluruh komponen: membangun model baseline, membuat berkas submission, memvalidasi formatnya, dan menguji skornya terhadap data publik *Ground Truth* (GT).

### Poin-Poin Kunci
* **Algoritma Baseline (*Nearest Player Heuristic*):**
  * Pada setiap frame di mana bola terdeteksi, model mencari pemain terdekat dengan bola:
    * Jika pemain terdekat tim Home $\rightarrow$ `H` (Barcelona).
    * Jika pemain terdekat tim Away $\rightarrow$ `A` (Athletic Club).
    * Jika bola hilang atau tidak ada pemain $\rightarrow$ `D` (*Dead ball / Nobody*).
* **Format Submission Resmi:**
  * Berkas CSV dua kolom: `frame` (0 s.d. 199.318) dan `label` (`H`, `A`, `D`, atau `X`).
  * Wajib lolos pemeriksaan skrip `validate_submission.py`.

### Masalah Flickering & Anomali Metrik
Saat baseline mentah dievaluasi terhadap 5 menit data publik GT (berisi 17 *possession* riil berdurasi rata-rata 14,2 detik):
* Hasil baseline mentah:
  * `macroF1` = **0.5972** (tampak cukup baik).
  * `spellF1` = **0.0378** (sangat rendah).
* **Penyebab:** Terjadi **flickering** (label berganti-ganti tim setiap beberapa frame). Model mentah menghasilkan **131 possession semu** dengan durasi rata-rata hanya **2,0 detik**. Karena metrik peringkat kompetisi (**`spellF1`**) menilai keutuhan interval serangan secara utuh (*IoU matching*), model tanpa penghalusan (*smoothing*) mendapat skor mendekati nol.

### Solusi Smoothing (Majority Vote Window)
Dengan menerapkan *rolling majority voting* selebar jendela ($\pm\text{window}$ frame):

| Window | macroF1 | spellF1 | Jumlah Possession | Rerata Durasi |
| :---: | :---: | :---: | :---: | :---: |
| **0 (raw)** | 0.5972 | **0.0378** | 131 | 2.0 detik |
| **12** | 0.6070 | **0.1012** | 66 | 4.1 detik |
| **25** | 0.6200 | **0.2868** | 36 | 7.6 detik |
| **50** | 0.6207 | **0.3256** | 26 | 10.8 detik |
| **125** | 0.5812 | **0.4242** | 16 | 18.5 detik |
| **200** | 0.5151 | **0.1926** | 10 | 30.0 detik |

* **Temuan:** Nilai `macroF1` per frame relatif datar, namun `spellF1` melonjak lebih dari 10 kali lipat begitu *flickering* diredam dan durasi segmen mendekati kondisi sepak bola nyata.

### Peringatan Kritis: Jebakan Overfitting pada Public GT
* Pada sampel publik 5 menit (hanya 17 *possession*), window $\pm 125$ terlihat paling optimal.
* Namun pada evaluasi satu pertandingan penuh, window $\pm 50$ terbukti mengalahkan $\pm 125$.
* **Prinsip Penting:** Sampel 5 menit publik terlalu kecil untuk memilih hyperparameter final (satu kesalahan segmen menggeser skor $\pm 6$ poin). Gunakan data publik hanya untuk memastikan pipeline berjalan benar (*sanity check*), dan gunakan teknik statistik seperti bootstrap (`--bootstrap 1000`) saat membandingkan varian model.

---

## 4. Arah Eksperimen & Perbaikan Kita Berikutnya

Model baseline ini sangat sederhana dan menyisakan banyak ruang improvisasi terarah:
1. **Pemodelan Dead-Ball yang Realistis:**
   * Jangan hanya menganggap bola hilang sebagai `D`. Manfaatkan fitur fisik (pergerakan pemain yang melambat, bola statis) serta penanda waktu `SET PIECES` dari Smart Tagging.
2. **Pemodelan Berbasis Interval / State-Machine:**
   * Alih-alih memprediksi setiap frame secara independen lalu melakukan smoothing, gunakan model sekuensial (seperti HMM, CRF, atau segment classifier) yang mengenali batas awal dan akhir sebuah rangkaian *possession*.
3. **Pemanfaatan Smart Tagging sebagai Feature/Prior:**
   * Integrasikan 638 interval fase taktis sebagai prior probabilitas tim yang memegang kendali bola.
4. **Analisis Kesalahan Berbasis Transisi:**
   * Manfaatkan berkas laporan evaluasi `evaluation/reports/<nama>_transitions.csv` untuk melihat daftar transisi kepemilikan bola yang terlewat (*missed*) atau salah ditebak (*spurious*), lalu bandingkan langsung dengan frame videonya.

