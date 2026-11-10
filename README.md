# Machado CVD Simulation

Aplikasi web dan pipeline penelitian untuk analisis warna citra buah menggunakan confusion line, simulasi Machado, dan CIEDE2000. Fokus aktif adalah eksperimen **tanpa segmentasi** pada `research/notebooks/tanpa_segmentasi/`. Dokumentasi diselaraskan pada 26 Oktober 2026 terhadap hasil tersimpan.

Folder eksperimen lain merupakan pembanding atau arsip dan tidak menjadi sumber angka utama.

## Tujuan dan ruang lingkup

Penelitian memilih kelompok citra berdasarkan hubungan pasangan warna terhadap confusion line, kemudian mengukur perubahan asli-versus-simulasi untuk protan dan deutan pada severity 0,25; 0,50; 0,75; dan 1,00. Machado tidak dilatih dengan dataset. K-means merangkum sampel RGB seluruh citra menjadi empat pusat warna, termasuk warna latar.

Severity adalah parameter model. Nilai di antara 0 dan 1 memodelkan anomalus trikromasi; 1 menjadi titik ujung dikromasi. Empat titik eksperimen tidak merepresentasikan kategori klinis atau persentase kehilangan kemampuan penglihatan. Keunggulan Machado yang relevan adalah cakupan kondisi bertingkat dalam satu model, bukan klaim menang uji akurasi antar-model.

## Pipeline dan sumber hasil

| Tahap | Tugas | Dokumen |
| --- | --- | --- |
| NB01 | Deduplikasi pHash intra-kelas, crop/resize 512 x 512, sampel seluruh citra, K-means, confusion line, Otsu, filter kelas/citra, undersampling dua tahap | [Analisis NB01](research/notebooks/tanpa_segmentasi/01/NB01_analisis_hasil.md) |
| NB02 | Empat severity untuk setiap keanggotaan citra-tipe pada manifest | [Analisis NB02](research/notebooks/tanpa_segmentasi/02/NB02_analisis_hasil.md) |
| NB03 | CIEDE2000 seluruh piksel, ringkasan individu/kelas/seleksi/kondisi, serta perbandingan sumber berpasangan | [Analisis NB03](research/notebooks/tanpa_segmentasi/03/NB03_analisis_hasil.md) |

Engine bersama berada di [research/core/machado.py](research/core/machado.py). NB00, rentang HSV, pemetaan manual Red-Orange/Green-Yellow, dan GrabCut tidak menjadi tahapan eksperimen aktif.

## Dataset dan kelompok seleksi

Sumber dataset mengikuti Fruitdataset pada naskah penelitian. Semua 19 kelas train selain `000neg` diperiksa. Kelas lolos jika mean dan median jarak antar-citra berada di bawah atau sama dengan ambang Otsu tipe; citra pada kelas lolos disaring kembali dengan median jaraknya. K-means empat pusat, median dua arah, dan aturan seleksi merupakan adaptasi operasional, bukan aturan klinis dari artikel confusion line.

Undersampling menyamakan jumlah per kelas di dalam tipe, lalu menyamakan total antar-tipe pada 456. Akibat tahap kedua, protan memiliki 46-54 citra per kelas pada sembilan kelas; deutan memiliki 57 pada delapan kelas. Kelompok boleh tumpang tindih dan komposisinya tetap berbeda.

## Hasil run yang tersedia

| Ukuran | Hasil run tersimpan |
| --- | ---: |
| Kelas train selain 000neg / citra awal | 19 / 4.870 |
| Duplikat intra-kelas tersaring | 178 |
| Citra setelah crop dan resize / analisis berhasil | 4.692 / 4.692 |
| Kelas terpilih protan / deutan | 9 / 8 |
| Hasil kuota per kelas protan / deutan | 612 / 456 |
| Jumlah akhir protan / deutan | 456 / 456 |
| Keanggotaan / sumber unik / irisan sumber | 912 / 782 / 130 |
| Simulasi / evaluasi | 3.648 / 3.648 |
| Mean Delta E00 seluruh evaluasi / SD | 9,0244 / 6,0331 |

Pada kelompok lengkap, mean deutan sedikit lebih tinggi pada 0,25; protan lebih tinggi pada 0,50-1,00. Pada 130 sumber yang sama, mean deutan lebih tinggi pada seluruh severity. Angka ini bersifat deskriptif dan tidak membuktikan perbedaan klinis, signifikansi statistik, atau ketepatan model.

Sumber angka: [ringkasan NB01](research/notebooks/tanpa_segmentasi/01/output/dataset_preparation_summary.json), [NB02](research/notebooks/tanpa_segmentasi/02/output/simulation_summary.json), dan [NB03](research/notebooks/tanpa_segmentasi/03/output/evaluation_summary.json).

## Tiga use case aplikasi

1. **Mensimulasikan warna citra dan mengevaluasi perubahan:** unggah JPEG, PNG, atau WebP, jalankan delapan kondisi, tampilkan citra masukan dan empat hasil pada tab terpilih, lalu tinjau metrik, heatmap, serta matriks.
2. **Mengunduh hasil:** simpan citra simulasi kondisi terpilih sebagai PNG.
3. **Memulai kembali:** tombol Reset membersihkan pilihan citra dan hasil setelah hasil tersedia.

Antarmuka menampilkan rata-rata Delta E00 empat desimal, perubahan RGB, dan proporsi piksel berubah pada setiap kartu severity. Heatmap mengikuti kondisi terpilih dan menggunakan Viridis dengan skala bersama untuk delapan hasil dalam satu request. Pemilihan tab dan severity, unduhan, serta Reset tidak mengirim permintaan simulasi baru.

Clipping tetap dihitung backend dan tersedia dalam respons API, tetapi tidak ditampilkan oleh komponen hasil saat ini. Tombol mode presentasi dan unduhan heatmap sedang dinonaktifkan dalam kode antarmuka.

## Menjalankan aplikasi

Backend menggunakan Python, FastAPI, OpenCV, NumPy, dan scikit-image. Frontend menggunakan React 19, Vite 8, Tailwind CSS 4, dan TanStack Query 5; dependensi aktual tercatat dalam requirements dan package-lock.

Dari root proyek, jalankan backend:

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

Pada terminal lain, jalankan frontend:

```powershell
cd frontend
npm ci
npm run dev
```

Frontend memakai http://localhost:8000 secara bawaan. Untuk alamat lain, tetapkan VITE_API_URL dalam frontend/.env.local. Backend membaca CORS_ORIGINS dari lingkungan atau backend/.env, dengan nilai bawaan http://localhost:5173. Daftar origin dipisahkan koma.

## API

| Metode | Endpoint | Fungsi |
|---|---|---|
| GET | /api/health | Status layanan |
| GET | /api/simulation/method | Metadata engine, tipe, severity, dan tahap transformasi |
| POST | /api/simulation/analyze | Simulasi dan evaluasi satu citra |

POST menerima multipart/form-data dengan satu field image. Tidak ada field ID model atau pemilihan domain. Frontend membatasi MIME JPEG, PNG, atau WebP dan ukuran 10 MiB, yang ditulis 10 MB pada UI. Backend memeriksa berkas kosong, ukuran, keberhasilan decode, dan maksimum 16.000.000 piksel. Rate limit endpoint adalah 10 request per menit.

Respons berisi original, width, height, method, heatmapScale, serta delapan results. Setiap hasil memuat cvdType, severity, image, deltaE00Heatmap, metrics, dan matrix. Citra dikirim sebagai data URL PNG. Backend mempertahankan dimensi citra unggahan yang diterima; crop 512 x 512 merupakan tahap dataset batch, bukan tahap request aplikasi.

## Interpretasi evaluasi

- Delta E00 mengukur perbedaan warna pada posisi piksel yang sama dalam CIELAB. Rata-rata mencakup seluruh citra, termasuk latar.
- Perubahan RGB adalah rata-rata selisih absolut seluruh kanal, dibagi 255. Antarmuka menyajikannya sebagai persen.
- Piksel berubah adalah proporsi piksel dengan sedikitnya satu kanal 8 bit berbeda.
- Clipping adalah proporsi piksel yang memiliki kanal di luar rentang RGB linear sebelum pembatasan. Proporsi gabungan bukan penjumlahan proporsi bawah dan atas.

NB03 menggunakan heatmap YlGn dengan skala bersama antarcontoh panel, sedangkan web menggunakan Viridis dengan skala bersama delapan hasil unggahan. Kedua visual tidak dapat dibandingkan hanya dari warna tanpa membaca skalanya. Pemeriksaan formula CIEDE2000 dengan data acuan, jika dijalankan, harus dilaporkan terpisah dari evaluasi citra; hasil eksperimen aktif tidak dianggap otomatis membuktikan kelulusan pengujian versi lama.

## Reproduksi dan pemeriksaan

Jalankan NB01, NB02, dan NB03 dari folder `research/notebooks/tanpa_segmentasi/` secara berurutan. Gunakan lingkungan dengan dependensi notebook yang tersedia. Catat versi paket dan parameter aktual saat menjalankan ulang.

Periksa lokasi input/output sebelum menjalankan ulang. NB01 yang tersimpan masih mengatur `OUTPUT_DIR` ke `research/notebooks/01/output/tanpa_segmentasi`, sedangkan NB02 dan NB03 menggunakan `research/notebooks/tanpa_segmentasi/...`. Selaraskan konfigurasi lokasi terlebih dahulu dan pastikan manifest serta hash berasal dari run yang sama; keberadaan laporan tersimpan tidak berarti rantai eksekusi ulang sudah siap tanpa penyesuaian.

Pemeriksaan kode ketika ada perubahan aplikasi:

```powershell
backend\venv\Scripts\python.exe -m pytest backend/tests -q
cd frontend
npm run lint
npm run build
npm audit
```

Perintah tersebut adalah prosedur pemeriksaan, bukan pernyataan bahwa seluruh pemeriksaan telah lulus pada setiap pembaruan dokumentasi. Aplikasi tidak melakukan koreksi warna atau diagnosis, dan penelitian tidak melibatkan validasi persepsi manusia.

## Kebijakan berkas hasil

Dataset mentah/processed dan folder citra `confusion_line_filtered/`, `simulated_images/`, serta output gambar legacy diabaikan Git. Notebook, laporan Markdown, CSV, JSON, dan grafik ringkasan tidak diabaikan secara menyeluruh agar hasil dapat ditinjau. Notebook dapat memuat gambar tertanam, sehingga ukurannya tetap perlu diperiksa sebelum commit. Aturan `/scripts/` yang sudah ada tetap berlaku untuk catatan lokal. Perubahan `.gitignore` tidak menghapus berkas yang telah dilacak.
