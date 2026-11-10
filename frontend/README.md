# Machado CVD Lab Frontend

Antarmuka React untuk demonstrasi simulasi Machado dan evaluasi perubahan warna. Penjelasan penelitian tersedia pada [README utama](../README.md) dan kebutuhan lengkap pada [PRD](../PRD_Simulasi_CVD_Machado.md).

## Menjalankan

Dari folder frontend:

```powershell
npm ci
npm run dev
```

Backend perlu berjalan terpisah. URL bawaan adalah http://localhost:8000. Tetapkan VITE_API_URL pada .env.local jika alamat backend berbeda dan sesuaikan CORS_ORIGINS pada backend.

Dependensi utama: React 19, Vite 8, Tailwind CSS 4, dan TanStack Query 5. Versi paket yang dipasang mengikuti package-lock.json.

## Alur dan tiga use case

1. Pengguna memilih atau menyeret JPEG, PNG, atau WebP berukuran paling besar 10 MiB, berlabel 10 MB pada antarmuka. Nama berkas tampil setelah lolos pemeriksaan MIME dan ukuran.
2. Tombol Jalankan simulasi mengirim satu field image melalui POST /api/simulation/analyze. Tipe, severity, model, dan domain tidak dikirim sebagai parameter pilihan.
3. Backend menghasilkan protan dan deutan masing-masing pada severity 0,25; 0,50; 0,75; dan 1,00, beserta evaluasi Delta E00.
4. Frontend menampilkan citra masukan dan empat hasil pada tab tipe terpilih. Setiap kartu memuat rata-rata Delta E00, perubahan RGB, dan proporsi piksel berubah.
5. Memilih tab atau kartu memperbarui kondisi terpilih, heatmap, matriks, dan target unduhan menggunakan respons yang sudah diterima.
6. Pengguna dapat mengunduh citra simulasi terpilih sebagai PNG atau menekan Reset untuk memulai kembali.

Langkah unggah sampai peninjauan hasil merupakan satu use case: mensimulasikan warna citra dan mengevaluasi perubahan. Unduh dan memulai kembali merupakan dua use case opsional setelah hasil tersedia.

Reset menghapus state file, data dan status mutation, serta mereset komponen unggahan. Tombol ini nonaktif sebelum ada hasil dan selama pemrosesan. Reset dan unduhan tidak memanggil endpoint backend.

## Heatmap dan metrik

Heatmap kondisi terpilih memakai Viridis: ungu untuk nilai kecil dan kuning untuk nilai besar. Semua delapan kondisi dalam satu respons memakai skala 0 hingga maksimum Delta E00 seluruh hasil tersebut. Bila maksimum nol, heatmap memakai warna minimum. Skala dapat berbeda antara dua unggahan.

| Nilai | Penyajian |
|---|---|
| metrics.meanDeltaE00 | Rata-rata perbedaan warna, empat desimal |
| metrics.meanAbsRgbChange | Rata-rata selisih absolut kanal dibagi 255, ditampilkan sebagai persen |
| metrics.changedPixelRatio | Proporsi piksel dengan setidaknya satu kanal 8 bit berubah, ditampilkan sebagai persen |
| matrix | Matriks kondisi terpilih, tampilan empat desimal |
| deltaE00Heatmap | Data URL PNG untuk peta perbedaan warna kondisi terpilih |

Clipping tersedia dalam payload API melalui clipLowRatio, clipHighRatio, dan clipAnyRatio, tetapi belum ditampilkan pada UI aktif. Tombol unduh heatmap dan mode presentasi sedang dinonaktifkan; unduhan yang aktif menyimpan citra simulasi dengan nama simulasi_<tipe>_<severity-persen>.png.

Label 25%, 50%, 75%, dan 100% menunjukkan parameter model, bukan persentase kehilangan penglihatan. Besarnya Delta E00 bukan skor akurasi simulasi.

## Pembagian tanggung jawab

| Lokasi | Tanggung jawab |
|---|---|
| src/routes/SimulationLab.jsx | State unggahan, pemrosesan, error, hasil, dan Reset |
| src/features/simulation/components/ImageUploader.jsx | Pemilihan berkas, seret dan lepas, pemeriksaan MIME dan ukuran |
| src/features/simulation/hooks/useAnalyzeSimulation.js | Mutation permintaan simulasi |
| src/shared/lib/apiClient.js | URL dasar API |
| src/features/simulation/components/SimulationResults.jsx | Tab tipe, empat kartu, heatmap, matriks, dan unduhan |

Perhitungan Machado dan CIEDE2000 dilakukan backend. Frontend tidak menjalankan deduplikasi, K-means, confusion line, filter kelas, atau undersampling dataset. Komponen SimulationResults di frontend berbeda dari dataclass SimulationResult di backend yang menampung satu hasil per kondisi.

## Penanganan input dan kegagalan

Backend memeriksa berkas kosong, ukuran maksimum, keberhasilan decode, serta resolusi maksimum 16 megapiksel. Batas jumlah piksel diperiksa backend dan bukan oleh komponen unggahan. Input tidak valid atau kegagalan decode dikembalikan dengan HTTP 422; endpoint juga menerapkan rate limit 10 request per menit. Antarmuka menampilkan status pemrosesan dan pesan kegagalan dari permintaan.

## Pemeriksaan

```powershell
npm run lint
npm run build
npm audit
```

Untuk pemeriksaan manual, gunakan citra valid dan input yang tidak memenuhi ketentuan. Periksa delapan hasil, pergantian tipe dan severity tanpa request tambahan, kesesuaian heatmap serta matriks, unduhan PNG, dan Reset setelah hasil tersedia. Kinerja citra beresolusi tinggi belum memiliki batas waktu penerimaan yang terukur.

## Hubungan dengan fokus penelitian

Eksperimen aktif berada di [tanpa_segmentasi](../research/notebooks/tanpa_segmentasi/). Seleksi confusion line dilakukan pada dataset batch sebelum simulasi; aplikasi menerima satu citra dan tetap menghasilkan delapan kondisi. Keanggotaan kelompok batch tidak menjadi syarat unggahan web. Semua piksel termasuk latar ikut disimulasikan dan dievaluasi.

Hasil batch tersimpan mencakup 456 citra per tipe dan 3.648 simulasi dari 782 sumber unik. Hasil satu unggahan tidak ditambahkan ke statistik penelitian secara otomatis. Rujuk [konteks penelitian](../KONTEKS_PENELITIAN.md) untuk aturan seleksi dan batas interpretasi.
