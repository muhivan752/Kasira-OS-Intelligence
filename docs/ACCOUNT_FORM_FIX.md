# Form username dan tampilkan password

6 Oktober 2026. Ivan tidak dapat memigrasikan akun karena memakai `Kasira Coffee` sebagai username toko, lalu meminta password dapat dilihat. Username login memakai huruf/angka/tanda hubung/garis bawah tanpa spasi; nama usaha merupakan kolom terpisah. Form Akun saya sebelumnya hanya memeriksa panjang sehingga penolakan baru muncul dari API dan terlihat seperti masalah password.

Web **live** dari source `a2d88497b5115f3f8b83bdccc20604e568536d0b`:

- Form migrasi menyebut contoh `kasira_coffee`, menjelaskan nama usaha tetap sama, dan memvalidasi format sebelum submit. Pattern lama pada form auth juga diperbaiki karena tidak valid di browser yang memakai regex `v` untuk HTML pattern.
- Error validasi API pada web menyebut Username toko/Username akun dan menghapus awalan teknis `Value error,`.
- Komponen PasswordInput memberi label eksplisit serta tombol Tampilkan/Sembunyikan per kolom di login, daftar, aktivasi, pemulihan dan Akun saya (saat ini/baru/ulang). Awalnya tersembunyi; nilai bertahan, tombol tidak submit, keyboard Space tersedia. Warna/radius/font mengikuti form Selaris, ENERGY1/RHYTHM1/MOTION1, tanpa aset baru.
- Minimum username3/password8 tetap; APK1.6.34+201. QA hanya fixture lokal, tanpa mengganti credential merchant.

TypeScript dan production build PASS. Browser pada image produksi final PASS:32 auth appearance states (empat route/empat lebar/dua tema), tampilkan/sembunyikan+nilai+44px+keyboard+tanpa submit, registrasi/login/claim/change/activation/recovery, HRIS roles dan logout/retry. Case nyata `Kasira Coffee` ditolak lokal; bypass HTML untuk menguji server422 menghasilkan error Username toko; koreksi username diterima fixture. Helper/error migrasi pada320/768/1440, kedua tema,200% dan kontras teks AA PASS. Screenshot diperiksa langsung. [Delivery Gate](AI_ACCESS_GATE.md) diperiksa kembali beserta bukti follow-up.

Image `sha256:697b1f3c71e03b9b30df404c48f98775e4c84e9064322d9383bcafc317fc1ac1`: lima runtime source hashes cocok reviewed source. Source dipush dan remote SHA cocok sebelum frontend-only `compose up -d --no-deps`. Smoke HTTPS publik24 auth states, show/hide tanpa submit, username/keyboard/legacy/download tanpa pageerror PASS. Empat service healthy, schema115 dan seluruh312 backend hashes tetap cocok; DB/background healthy. Preview QA tugas dihentikan.

Rollback frontend tersedia: tag `selaris-frontend-before-username:20261006`, image `sha256:742368c98bb327cf842dcd84e8521337e75e28b9da0d08803a09d5a93d7b66e2`. Redeploy image itu frontend-only bila diperlukan.

Bukti `/tmp/selaris-username-*`: `typescript.log`, `build-final.log`, `accounts-browser.log`, `error-mobile.png`, `frontend-manifest.json`, `verify-frontend.log`, `previous-image.json`, `deploy-frontend.log`, `public-browser.log`, `live-state.json` dan `live-state.log`.
