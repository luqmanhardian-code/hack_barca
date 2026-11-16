# Indeks & Panduan Referensi: More than a Hack 2027 (Ball Possession)

Folder ini berisi kumpulan literatur akademik, dokumentasi resmi penyelenggara (Metrica Sports & FC Barcelona), dan repositori kode rujukan yang secara langsung relevan untuk menyelesaikan tantangan **More than a Hack 2027 — Phase 1: Ball Possession**.

---

## Daftar Berkas Referensi

| No | Berkas / Direktori | Judul & Penulis | Topik Utama |
|---|---|---|---|
| 01 | [`01_VidalCodina_Automatic_Event_Detection_Tracking_Data.pdf`](01_VidalCodina_Automatic_Event_Detection_Tracking_Data.pdf) | *Automatic Event Detection in Football Using Tracking Data* (Vidal-Codina et al., MIT Sports Lab & FIFA, 2022) | Deteksi penguasaan bola frame-by-frame, *possession zone* (PZ), *duel zone* (DZ), dan aturan bola mati (*set piece triggers*). |
| 02 | [`02_Kim_PathCRF_Ball_Free_Soccer_Possession_Path.pdf`](02_Kim_PathCRF_Ball_Free_Soccer_Possession_Path.pdf) | *PathCRF: Ball-Free Soccer Event Detection via Possession Path Inference from Player Trajectories* (Kim et al., KAIST & Fitogether, KDD 2026) | Estimasi *possession path* tanpa bola menggunakan Masked CRF & Viterbi Decoding untuk mencegah *flickering* dan *teleportation*. |
| 03 | [`03_Renner_Match_Phases_Football_GNN_Tracking.pdf`](03_Renner_Match_Phases_Football_GNN_Tracking.pdf) | *Automated Detection of Match Phases in Football from Spatio-Temporal Tracking Data Using Graph Neural Networks* (Renner et al., KIT & DFB, 2026) | Pemodelan graf berbasis Delaunay Triangulation + SEAConv + LSTM untuk klasifikasi fase taktis (*Smart Tagging* & *In/Out of Possession*). |
| 04 | [`04_Link_Individual_Ball_Possession_Soccer.pdf`](04_Link_Individual_Ball_Possession_Soccer.pdf) | *Individual Ball Possession in Soccer* (Link & Hoernig, TU Munich, PLOS ONE 2017) | Definisi matematis & batas fisik *Individual Ball Possession* (IBP), *Individual Ball Action* (IBA), dan *Individual Ball Control* (IBC). |
| 05 | [`05_MendesNeves_KNN_Pitch_Ownership_Soccer.pdf`](05_MendesNeves_KNN_Pitch_Ownership_Soccer.pdf) | *A Neighbor-based Approach to Pitch Ownership Models in Soccer* (Mendes-Neves et al., Univ. of Porto, 2025) | Model *pitch control* cepat & ringan berbasis K-Nearest Neighbors (KNN) dengan pembobotan jarak & *spatial smoothing*. |
| 06 | [`06_Vorobev_RealTime_Soccer_Ball_Localization_Trajectory.pdf`](06_Vorobev_RealTime_Soccer_Ball_Localization_Trajectory.pdf) | *Real-time Localization of a Soccer Ball from a Single Camera* (Vorobev et al., Yandex, 2025) | Model *Markov state* 4-mode ($J$ = Jumping, $P$ = Possession, $W$ = Waiting/Occlusion, $O$ = Out-of-Pitch) untuk mengatasi bola hilang (41% missing). |
| 07 | [`07_Yamamoto_Theory_Data_Analysis_Ball_Possession_Time_Football.pdf`](07_Yamamoto_Theory_Data_Analysis_Ball_Possession_Time_Football.pdf) | *Theory and Data Analysis of Player and Team Ball Possession Time in Football* (Yamamoto et al., Phys. Rev. E, 2024) | Distribusi statistik durasi *possession spell* (distribusi Gamma & *mixture geometric*), berguna sebagai prior durasi possession. |
| 08 | [`08_Metrica_Sports_Events_Definitions.pdf`](08_Metrica_Sports_Events_Definitions.pdf) | *Metrica Sports Event Definitions* (Dokumentasi Resmi Metrica Sports) | Definisi resmi penyelenggara lomba mengenai aturan *possession*, *deflection*, *duel*, *out of play*, dan klasifikasi kejadian pertandingan. |
| 09 | [`LaurieOnTracking/`](LaurieOnTracking/) | Repositori Modul & Tutorial Resmi Metrica Sports (Dr. Laurie Shaw) | Implementasi Python siap pakai untuk *Pitch Control* Spearman, perhitungan kecepatan pemain (*Savitzky-Golay*), dan visualisasi tracking. |
