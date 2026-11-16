# Rekap Konseptual: More Than A Hack 2027 (Ball Possession)

Dokumen ini merangkum esensi kompetisi secara padat dan konseptual dari berkas **CHALLENGE**, **DATA**, dan **EVALUATION** sebagai panduan dasar pemodelan.

---

## 1. Problem Statement & Definisi Task (CHALLENGE)

* **Goal Utama**: Memprediksi tim mana yang memegang **ball possession** atau apakah statusnya **dead ball** pada setiap frame video match.
* **Definisi Controlled Possession**:
  * Possession menuntut **kontrol nyata** terhadap bola. Sentuhan sekilas, defleksi/pantulan umpan, tekel lepas, atau duel udara belum memindahkan possession.
  * **Prinsip Last Possessor**: Saat bola lepas (*loose ball*) atau sedang diperebutkan (*contested*), possession tetap dihitung milik tim terakhir yang memegang kontrol sampai tim lawan berhasil merebut dan menguasai bola secara meyakinkan.
* **Hanya 3 State (H / A / D)**:
  * Sistem hanya mengenal: **Home (`H`)**, **Away (`A`)**, atau **Dead Ball (`D`)**.
  * Tidak ada label perantara seperti "transisi", "contested", atau "unknown".
  * *Dead ball* adalah jeda (*stoppage*), bukan *possession*. Siapa yang akan mengambil bola mati tidak dihitung sebagai pemilik bola selama bola belum kembali *in play*.
* **Mekanisme Label Abstain (`X`)**:
  * Di luar waktu pertandingan (*pre-match*, *halftime*, *post-match*), label ini diabaikan dan tidak kena penalti.
  * Pada metrik ranking, evaluator otomatis melakukan **forward-fill** (meneruskan label tebakan terakhir Anda) untuk menutupi `X`.
  * *Implikasi*: Menulis `X` sangat aman saat bola hilang sesaat di tengah-tengah *possession* tim yang sama. Namun, fatal jika dilakukan di momen pergantian *possession* (*transition*) karena label lama akan bocor (*bleed*) ke wilayah tim lawan.
* **Karakter Ground Truth**:
  * Ground truth diturunkan **secara mekanis/algoritmik** dari *corrected tracking data* Metrica, bukan dari interpretasi mata manusia ataupun *event data* (seperti Opta/StatsBomb).

---

## 2. Karakteristik & Realitas Data (DATA)

* **Reference Timeline**:
  * Video **tactical** (sudut lebar dari atas) adalah **satu-satunya acuan timeline**. Seluruh indeks frame submission terikat ke video ini.
  * Video **broadcast** (siaran TV) hanya input opsional dengan timeline terpisah (*unsynchronized*) dan banyak *cuts/replays*.
* **Missing Ball (Tantangan Terbesar)**:
  * Deteksi otomatis sering kehilangan jejak bola (*NaN*) pada momen-momen krusial (kemelut di kotak penalti, duel udara, oklusi antarpemain).
  * Model tidak bisa hanya mengandalkan fitur posisi bola mentah, melainkan harus memanfaatkan struktur formasi dan pergerakan pemain di sekitarnya.
* **Player Tracking Tanpa ID Permanen**:
  * Tracking data (ATD) menyediakan koordinat per tim, tetapi **tanpa identitas pemain tetap** (terjadi fragmentasi dan *identity switches* saat pemain berdekatan).
  * Fitur harus dirancang berbasis **analisis spasial kolektif per tim** (posisi kelompok, *centroid*, dominasi ruang/pitch control), bukan *tracking* per individu pemain.
* **Smart Tagging sebagai Prior**:
  * Berisi anotasi taktis otomatis (fase *Build Up*, *Progression*, *Set Pieces*, dll.).
  * Sangat bermanfaat sebagai **prior**, terutama *set pieces* yang menandai berakhirnya *dead ball* dan mulainya *possession* baru. Namun, intervalnya adalah fase permainan, bukan ekuivalen 1-to-1 dengan *possession spell*.
* **Homography**:
  * Matriks 3x3 per frame untuk mapping koordinat pitch 2D yang ternormalisasi ke piksel video kamera, berguna untuk analisis proyeksi visual.

---

## 3. Filosofi Evaluasi & Metrik (EVALUATION)

* **Frame-Level Metrics Menipu**:
  * Evaluasi akurasi frame-by-frame bisa sangat menyesatkan: model yang ragu-ragu dan sering berkedip (*flickering*) bisa mendapatkan akurasi frame tinggi, namun menghasilkan puluhan *possession* mikro palsu yang merusak representasi taktikal.
* **Segment-Based Ranking Metric (`spellF1`)**:
  * Kompetisi ini diperingkat berdasarkan **`spellF1`**, yaitu kemampuan model merekonstruksi **possession spells secara utuh** (dari awal penguasaan bola sampai bola lepas/mati).
  * Setiap rangkaian *possession* hanya dihitung **satu kali** (seperti seorang analis menghitungnya), terlepas dari panjang-pendeknya durasi frame.
* **One-to-One Greedy Matching**:
  * Setiap *ground truth possession* hanya boleh dipasangkan dengan maksimal satu prediksi terbaik.
  * Model dicegah membuat tebakan segmen raksasa untuk mengklaim banyak serangan sekaligus, dan tebakan berulang pada satu serangan yang sama akan dipenalti sebagai *false positive* (*spurious*).
* **Multi-IoU Thresholds (0.3 s.d. 0.7)**:
  * Tingkat tumpang-tindih waktu (*temporal IoU*) antara prediksi dan kenyataan diuji pada 5 level ambang batas: dari kesesuaian kasar (0.3) hingga presisi *timing boundary* yang ketat (0.7), lalu dirata-ratakan.
* **Jebakan Public Ground Truth**:
  * Kunci jawaban publik yang tersedia hanya mencakup 5 menit awal pertandingan.
  * Sampel 5 menit ini hanya bertujuan untuk *sanity check* alur pipeline kode. Melakukan *hyperparameter tuning* (misalnya ukuran *smoothing window*) hanya demi skor di 5 menit ini terbukti menyesatkan dan rawan memicu **overfitting** terhadap pertandingan penuh.
