# ⚽ Workflow Sederhana: More Than a Hack 2027
### *Panduan Konseptual untuk Praktisi Data Tabular*

---

## 1. Peta Mental: "Ini Sebenarnya Masalah Tabular + Waktu"

Jika Anda terbiasa dengan klasifikasi tabular (Pandas, XGBoost, Random Forest), bayangkan proyek ini sebagai **satu tabel besar**:

* **Baris (Index)**: Nomor frame video dari `0` sampai `199.318` (total ~199 ribu baris, mewakili 90 menit pertandingan pada 25 frame per detik).
* **Target ($y$)**: Memprediksi 1 dari 3 kelas pada setiap baris:
  * `H` : Penguasaan bola oleh tim Home (Barcelona)
  * `A` : Penguasaan bola oleh tim Away (Athletic Club)
  * `D` : *Dead ball* (bola mati / permainan terhenti)
  * *(Opsional: `X` = abstain, di mana evaluator otomatis meneruskan tebakan terakhir Anda / forward-fill)*.

```
| frame | dist_home_to_ball | dist_away_to_ball | is_set_piece | team_centroid_x | ... | Target (y) |
|-------|-------------------|-------------------|--------------|-----------------|-----|------------|
| 0     | 1.2 meter         | 8.5 meter         | 0            | 45.2            | ... | H          |
| 1     | 1.1 meter         | 8.3 meter         | 0            | 45.8            | ... | H          |
```

---

## 2. Mengenal 2 Sumber Data Utama

Panitia menyediakan data mentah dalam format khusus, namun skrip *helper* bawaan sudah siap mengubahnya menjadi tabel:

1. **Tracking ATD (`load_atd.py`)**  
   * Berisi koordinat $(x, y)$ dan kecepatan seluruh 22 pemain serta bola di setiap frame.
   * **Tantangan utama**: Bola hilang (*missing/NaN*) di **~43% frame** (karena oklusi/tertutup pemain). Saat bola hilang, posisi kelompok pemain (*team shape/centroid*) menjadi petunjuk utama.
2. **Smart Tagging (`load_smart_tagging.py`)**  
   * Anotasi taktis per rentang waktu (misal: detik 30 s.d. 45 = *Build Up*, atau menit 10:15 s.d. 10:20 = *Corner Kick / Set Piece*).
   * Cukup ubah detik ke nomor frame ($\text{frame} = \text{detik} \times 25$) dan tempelkan ke baris tabel sebagai **fitur prior**.

---

## 3. Mengapa Berbeda dari Klasifikasi Tabular Biasa?

Ada 2 perbedaan fundamental yang wajib dipahami:

### A. Bahaya "Flickering" (Kedipan Cepat)
* Pada tabular biasa, baris 100 dan baris 101 independen.
* Di sepak bola, jika frame 100 ditebak `H`, frame 101 ditebak `A`, dan frame 102 ditebak `H`, model Anda menghasilkan **kedipan mustahil** (bola tidak mungkin berganti kepemilikan dalam 0,04 detik).

### B. Metrik Ranking Bukan Akurasi Frame, tapi `spellF1`
* Penyelenggara **tidak menilai** seberapa banyak frame yang Anda tebak benar.
* Penyelenggara menilai **keutuhan segmen serangan (*possession spell*)**: apakah Anda berhasil mendeteksi sebuah rangkaian penguasaan bola dari awal sampai akhir tanpa putus (*temporal IoU*).
* Model yang sering berkedip (*flickering*) bisa memiliki akurasi frame 60%, namun skor `spellF1`-nya akan **anjlok mendekati 0** karena menghasilkan puluhan serangan semu yang terlalu pendek.

---

## 4. Masalah Label Minim & Cara Melakukan Tuning

### Masalahnya:
* Ground Truth (kunci jawaban) yang diberikan **hanya 5 menit pertama** (7.500 frame, berisi **hanya 17 *possession***).
* Sisanya (85 menit) adalah *blind test* untuk penilaian kompetisi.
* **Akibatnya**: Kita **tidak bisa** melakukan K-Fold Cross Validation atau GridSearch biasa. Mencari angka hyperparameter demi skor 5 menit ini terbukti memicu **overfitting parah**.

### Solusi Praktisnya:

1. **Gunakan Bootstrap untuk Mengukur Kepastian Skor**:
   * Evaluator menyediakan fitur `--bootstrap 1000`. Fitur ini mengacak ulang 17 segmen ground truth 1.000 kali untuk menghasilkan rentang skor (misal: `[0.21 .. 0.43]`).
   * Gunakan ini untuk memastikan apakah perubahan model benar-benar meningkatkan performa atau hanya kebetulan/noise.
2. **Kunci Parameter Menggunakan Aturan Fisika & Domain Knowledge**:
   * **Lebar Jendela Smoothing**: Operan bola melayang di udara biasanya butuh 1–2 detik (25–50 frame). Gunakan jendela waktu di rentang fisik ini agar operan tidak dianggap putus.
   * **Filter Durasi Minimal**: Penguasaan bola nyata hampir tidak pernah di bawah 1 detik (< 25 frame). Segmen prediksi mikro di bawah durasi ini bisa langsung dihapus/disatukan.
3. **Weak Supervision (Membuat Label Sendiri untuk 90 Menit)**:
   * Gunakan Smart Tagging sepanjang 90 menit sebagai label latihan proksi:
     * Setiap ada rentang `SET PIECES` $\rightarrow$ label proksi untuk `D` (Dead ball).
     * Saat pemain menggiring bola sangat dekat selama beberapa detik $\rightarrow$ label proksi tim tersebut.

---

## 5. Ringkasan Alur Kerja Konseptual (End-to-End)

```
1. DATA PREPARATION
   Baca Tracking (koordinat pemain/bola) + Smart Tagging (fase taktis)
   Ubah semuanya menjadi DataFrame per frame (0 s.d. 199.318).
         │
         ▼
2. FEATURE ENGINEERING
   - Jarak pemain terdekat ke bola (saat bola ada).
   - Posisi rata-rata tim / centroid (saat bola hilang / NaN).
   - Penanda fase taktis & set piece dari Smart Tagging.
         │
         ▼
3. INITIAL PREDICTION (Per Frame)
   Bisa menggunakan Rule-Based (Heuristik pemain terdekat)
   atau Model Tabular (LightGBM/Random Forest dari label proksi).
         │
         ▼
4. TEMPORAL SMOOTHING & POST-PROCESSING (Kunci spellF1)
   - Rolling Majority Vote (window 35-50 frame / ~1.5 - 2 detik).
   - Pruning: hapus atau satukan segmen serangan yang < 1 detik.
   - Isi celah bola hilang sesaat dengan label 'X' (forward-fill).
         │
         ▼
5. SUBMISSION & EVALUASI
   - Simpan CSV 2 kolom: 'frame' dan 'label'.
   - Validasi format dengan validate_submission.py.
   - Cek skor 5 menit dengan run_evaluation.py --bootstrap 1000.
   - Cek kewajaran global: total serangan harus ~160-220 spells di 90 menit.
```
