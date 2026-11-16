# Rekap Data & Kegunaan Pemodelan (More Than A Hack 2027)

Dokumen ini memetakan seluruh berkas awal dari panitia, status kelayakan pemakaiannya (*usability*), fungsi teknis, serta detail pemanfaatannya dalam pipeline pemodelan *ball possession*.

---

## Ringkasan Eksekutif

* **Fokus Pemodelan (Data yang Wajib Digunakan)**:
  1. `BAR-ATH_tactical_atd.txt` & `BAR-ATH_tactical_atd.xml`: Sumber data *tracking* posisi bola dan pergerakan pemain di lapangan (tulang punggung fitur spasio-temporal).
  2. `BAR-ATH_tactical_smart_tagging.xml`: Sinyal fase taktis untuk mendeteksi *Dead Ball* (`D`), *restarts*, dan tim penguasa bola.
  3. `BAR-ATH_possession_gt_public.csv` & `.json`: Validasi format dan *sanity check* alur kalkulasi metrik lokal.
* **Data Opsional**:
  1. `BAR-ATH_tactical_homography.csv` dan `BAR-ATH_tactical.mp4`: Hanya diperlukan jika membangun pipeline *computer vision* berbasis piksel video atau melakukan *visual debugging* kualitatif.
* **Data yang Dieliminasi (Tidak Digunakan)**:
  * Seluruh bundel **Broadcast** (`.mp4`, `_atd.txt`, `_atd.xml`, `_homography.csv`) **wajib diabaikan** karena *timeline*-nya tidak tersinkronisasi (*unsynchronized*), memiliki jumlah frame berbeda (~164k vs 199k), dan mengandung banyak potongan (*cuts/replays*). Memasukkan data broadcast berisiko mendiskualifikasi berkas submisi.

---

## Rekapitulasi Akhir Berkas Data

Urutan status: **Digunakan** $\rightarrow$ **Opsional** $\rightarrow$ **Tidak Digunakan**.

| Nama File | Kategori Sumber | Status Penggunaan | Peran / Alasan Teknis |
|---|---|---|---|
| `BAR-ATH_tactical_atd.txt` | Tactical | **DIGUNAKAN** | **Fitur Inti**: Tracking posisi bola dan 46 slot pemain (0–1). Sumber utama ekstraksi fitur jarak, kecepatan, centroid, dan formasi. |
| `BAR-ATH_tactical_atd.xml` | Tactical | **DIGUNAKAN** | **Parser & Metadata**: Definisi dimensi lapangan (105×68 m), frame rate (25 fps), dan pemisahan slot tim (Home/Away). |
| `BAR-ATH_tactical_smart_tagging.xml` | Tactical | **DIGUNAKAN** | **Prior & Rule-based**: Penanda fase permainan, deteksi batas *dead ball* (`D`), set pieces, dan tim yang menyerang. |
| `BAR-ATH_possession_gt_public.csv` | Evaluation | **DIGUNAKAN** | **Validasi Pipeline**: Uji coba pipeline lokal dan verifikasi format submisi pada 5 menit pertama pertandingan. |
| `BAR-ATH_possession_gt_public_meta.json` | Evaluation | **DIGUNAKAN** | **Validasi Pipeline**: Verifikasi rentang frame aktif babak 1 dan 2 untuk evaluator lokal. |
| `BAR-ATH_tactical_homography.csv` | Tactical | **OPSIONAL** | **Proyeksi Piksel**: Matriks 3×3 pemetaan koordinat pitch (0–1) ke piksel video. Tidak esensial untuk model tabular/spasial. |
| `BAR-ATH_tactical.mp4` | Tactical | **OPSIONAL** | **Inspeksi Visual**: Acuan visual timeline (199.319 frame) untuk evaluasi kualitatif dan *sanity check* manual manusia. |
| `BAR-ATH_broadcast_atd.txt` | Broadcast | **TIDAK DIGUNAKAN** | *Unsynchronized*: Timeline berbeda, panjang baris berbeda (164.488 baris). Menggunakannya akan membuat submisi ditolak evaluator. |
| `BAR-ATH_broadcast_atd.xml` | Broadcast | **TIDAK DIGUNAKAN** | Metadata tracking siaran TV yang tidak selaras dengan submission grid (199.319 frame). |
| `BAR-ATH_broadcast_homography.csv` | Broadcast | **TIDAK DIGUNAKAN** | Kualitas rendah: 34,2% frame invalid akibat replay/close-up, serta tidak sinkron ke frame acuan. |
| `BAR-ATH_broadcast.mp4` | Broadcast | **TIDAK DIGUNAKAN** | Video siaran TV dengan banyak pemotongan kamera (*cuts*), sudut zoom, dan jeda iklan. |

---

## Detail Isi dan Kegunaan Berkas Data Awal

Berikut adalah ulasan mendalam mengenai struktur, isi, dan peran teknis dari masing-masing berkas berdasarkan grup yang disediakan oleh panitia.

### 1. Tactical Bundle (`data/tactical/`)
> **Pondasi Timeline Utama**: Video *tactical* adalah **satu-satunya acuan timeline resmi (*reference timeline*)**. Baris ke-$i$ pada file submisi wajib berkorespondensi 1-ke-1 dengan frame ke-$i$ dari video ini (total 199.319 baris).

#### 1.1 `BAR-ATH_tactical_atd.txt`
* **Status**: `[DIGUNAKAN - FITUR UTAMA / INTI]`
* **Isi**:
  * Data *tracking* mentah keluaran *computer vision* Metrica (format FIFA/EPTS) sebanyak 199.319 baris (25 fps $\approx$ 133 menit).
  * Kolom mencakup `frame_id`, koordinat bola (`ball_x`, `ball_y`), serta koordinat $x, y$ dan kecepatan $s$ (*speed* dalam m/s) untuk hingga 46 *track slots* pemain dalam skala normalisasi `[0, 1]`.
* **Kegunaan untuk Pengerjaan**:
  * **Sumber fitur spasial & temporal utama**: Ekstraksi fitur jarak pemain terdekat ke bola, kecepatan bola, pergerakan akselerasi, *centroid* tim (Home vs Away), kerapatan formasi, serta *pitch control*.
  * **Tantangan**: Bola hilang (*NaN*) pada **43,1% frame** dan tidak ada ID pemain permanen. Analisis harus didesain berbasis kolektif per tim, bukan riwayat pemain individu.

#### 1.2 `BAR-ATH_tactical_atd.xml`
* **Status**: `[DIGUNAKAN - KONFIGURASI & PARSER]`
* **Isi**:
  * Berkas metadata EPTS yang mendefinisikan dimensi lapangan (105 × 68 meter), *frame rate* (25 fps), pemetaan *track slot* ke kubu tim (`Barcelona` / `Athletic Club`), dan penomoran slot.
* **Kegunaan untuk Pengerjaan**:
  * Berpasangan wajib dengan `BAR-ATH_tactical_atd.txt`. Diperlukan oleh parser (seperti library `kloppy.metrica`) untuk memisahkan slot mana yang milik Home (`H`) dan Away (`A`), serta mengonversi koordinat normalisasi `[0, 1]` ke satuan meter riil.

#### 1.3 `BAR-ATH_tactical_smart_tagging.xml`
* **Status**: `[DIGUNAKAN - FITUR PRIOR / RULE-BASED HEURISTIC]`
* **Isi**:
  * 638 anotasi taktis otomatis berbasis interval waktu (SportsCode format) yang memuat kode fase permainan (`SET PIECES`, `BUILD UP`, `PROGRESSION`, `DEFENDING`, `BALL IN THE BOX`, dll.) beserta tag penjelas (`Team`, `Type`, `Side`, `Half`).
  * Waktu `<start>` dan `<end>` dalam detik presisi dari awal video (`video_frame = round(seconds * 25)`).
* **Kegunaan untuk Pengerjaan**:
  * **Prior probabilitas transisi**: Menandai momen krusial *Dead Ball* (`D`) dan mulainya *possession* baru, terutama dari event `SET PIECES` (*Corner*, *Goal Kick*, *Throw-in*, *Free Kick*).
  * **Catatan**: Data ini hasil inferensi otomatis (bukan *ground truth* manual) dan 36 instance (termasuk semua lemparan ke dalam) memiliki tim `N/A`. Digunakan sebagai sinyal pelengkap/prior, bukan label mutlak.

#### 1.4 `BAR-ATH_tactical_homography.csv`
* **Status**: `[OPSIONAL - TIDAK DIGUNAKAN UNTUK TABULAR ML]`
* **Isi**:
  * 199.319 baris matriks homografi 3×3 (`h00` s.d. `h22`), nilai `reprojection_error`, dan indikator status `valid` (100% valid untuk kamera *tactical*).
* **Kegunaan untuk Pengerjaan**:
  * Menghubungkan titik 2D lapangan ke koordinat piksel frame kamera (atau sebaliknya).
  * **Catatan**: Jika pemodelan berfokus pada data tabular/spatiotemporal (*tracking* ATD + *Smart Tagging*), transformasi piksel kamera tidak diperlukan. Hanya berguna jika melatih arsitektur *Computer Vision* langsung dari piksel video atau melakukan proyeksi bounding box visual.

#### 1.5 `BAR-ATH_tactical.mp4` (Video Mentah)
* **Status**: `[OPSIONAL - HANYA DEBUGGING VISUAL KUALITATIF]`
* **Isi**:
  * Rekaman video sudut lebar (*tactical wide-angle*) 1920×1080 @ 25 fps, 199.319 frame penuh tanpa potongan (*cuts*).
* **Kegunaan untuk Pengerjaan**:
  * Sebagai bahan inspeksi kualitatif manusia untuk memverifikasi kesalahan boundary prediksi segmen possession pada edge cases.
  * Tidak dimasukkan langsung ke pipeline training model karena beban komputasi/I/O yang berlebihan dibandingkan data ATD yang sudah mengekstrak koordinatnya.

---

### 2. Broadcast Bundle (`data/broadcast/`)
> **Karakteristik**: Sudut pandang siaran TV komersial. Memiliki *timeline* sendiri yang tidak tersinkronisasi dengan *tactical*, dan sarat dengan *cuts*, *zooms*, tayangan ulang (*replays*), dan sorotan penonton.

#### 2.1 `BAR-ATH_broadcast_atd.txt` & `BAR-ATH_broadcast_atd.xml`
* **Status**: `[TIDAK DIGUNAKAN]`
* **Isi & Alasan**:
  * Tracking ATD siaran TV dengan panjang hanya 164.488 baris (bukan 199.319 baris).
  * Tidak disediakan mapping table antara frame broadcast dengan frame tactical. Menggunakan urutan frame ini akan menyebabkan kegagalan validasi baris submisi.

#### 2.2 `BAR-ATH_broadcast_homography.csv`
* **Status**: `[TIDAK DIGUNAKAN]`
* **Isi & Alasan**:
  * Matriks homografi broadcast sebanyak 164.488 baris, di mana **34,2% baris berstatus invalid (`valid = 0`)** karena kamera sering menyorot close-up pemain atau kerumunan tanpa menampilkan garis lapangan yang cukup.

#### 2.3 `BAR-ATH_broadcast.mp4`
* **Status**: `[TIDAK DIGUNAKAN]`
* **Isi & Alasan**:
  * Video siaran TV dengan banyak pemotongan adegan; tidak relevan untuk pipeline ekstraksi fitur otomatis submisi.

---

### 3. Evaluation & Ground Truth Bundle (`evaluation/gt/`)

#### 3.1 `BAR-ATH_possession_gt_public.csv`
* **Status**: `[DIGUNAKAN - HANYA UNTUK SANITY CHECK & VALIDASI PIPELINE]`
* **Isi**:
  * Format template submisi resmi (199.319 baris), tetapi **hanya berisi label nyata pada 5 menit pertama pertandingan** (frame 11.185 s.d. 18.684: 3.454 `H`, 2.577 `A`, 1.469 `D`). Seluruh frame di luar 5 menit tersebut diisi nilai `X`.
* **Kegunaan untuk Pengerjaan**:
  * Menguji apakah fungsi evaluasi lokal (`evaluation/run_evaluation.py`) berjalan dengan benar dan memverifikasi format file prediksi sebelum *submit*.
  * **Peringatan Keras**: **Jangan melakukan tuning model/hyperparameter berbasis data ini**, karena durasi 5 menit (17 *possession spells*) terlalu sempit dan sangat rawan *overfitting*.

#### 3.2 `BAR-ATH_possession_gt_public_meta.json`
* **Status**: `[DIGUNAKAN - VERIFIKASI EVALUATOR]`
* **Isi**: Metadata acuan evaluasi (daftar rentang frame aktif babak 1 dan 2, batas 5 menit publik, dan statistik agregat).
