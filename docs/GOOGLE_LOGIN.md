# Login Google Selaris

Implementasi memakai Firebase Authentication. Backend menerima **Firebase ID token**, memeriksa tanda tangan Google, project, masa berlaku, provider `google.com`, dan email terverifikasi. Google OAuth client secret tidak dipasang di backend.

Google pertama kali → verifikasi nomor lewat Sefrekuensi → hubungkan toko lama atau isi nama usaha baru → PIN kasir. Login berikutnya memakai Google langsung. WhatsApp tersedia sebagai pilihan pengiriman kode. Data toko masih berada di Selaris; perubahan ini belum menggabungkan database dengan Sefrekuensi.

## 1. Pilih project Firebase

Buka [Firebase Console](https://console.firebase.google.com/). Untuk identitas Google yang sama dengan Sefrekuensi, pilih **project Firebase yang sudah dipakai Sefrekuensi**, lalu tambahkan aplikasi Selaris di project itu. Project ID harus sama di backend, aplikasi web, dan `google-services.json` Android.

Jika memakai project Selaris yang terpisah, login tetap berjalan, tetapi UID Firebase berbeda dari Sefrekuensi.

Jika project Android dipindah dari project push yang lama, samakan juga kredensial FCM backend dengan project baru lewat `scripts/pasang_fcm.sh <service-account.json>`. Ini menjaga notifikasi kasir memakai project yang sama dengan APK.

## 2. Aktifkan Google

Di **Authentication → Sign-in method → Add new provider → Google**, aktifkan provider, isi nama publik dan email dukungan, lalu simpan. Jika diminta mengatur Google Auth Platform/OAuth consent, gunakan nama dan domain produk yang benar, tambahkan email penguji selama statusnya Testing, lalu ikuti persyaratan konsol sebelum membuatnya tersedia untuk semua pengguna.

## 3. Daftarkan web

Di **Project settings → General → Your apps → Add app → Web**, daftarkan `Selaris Web`. Firebase Hosting tidak diperlukan. Salin konfigurasi `firebaseConfig` ke `.env` server:

```dotenv
GOOGLE_FIREBASE_PROJECT_ID=nilai_projectId
GOOGLE_FIREBASE_WEB_API_KEY=nilai_apiKey
GOOGLE_FIREBASE_AUTH_DOMAIN=nilai_authDomain
GOOGLE_FIREBASE_WEB_APP_ID=nilai_appId
```

Di **Authentication → Settings → Authorized domains**, tambahkan:

- `selaris.id`
- `kasira.online` jika alamat lama masih dipakai untuk login
- `localhost` untuk pengembangan lokal

Pakai `authDomain` bawaan konfigurasi Firebase, biasanya `<projectId>.firebaseapp.com`. Isi domain di daftar Authorized domains tanpa `https://` atau path. Konfigurasi web ini merupakan identitas aplikasi publik, bukan service-account private key.

Setelah `.env` diisi, muat ulang environment backend:

```bash
cd /var/www/kasira
sudo docker compose up -d --no-deps --force-recreate backend
curl -fsS https://selaris.id/api/v1/auth/providers
```

Hasil harus berisi `google.enabled: true` dan `google.web_config`. Refresh halaman login. Konfigurasi web dibaca saat runtime; tidak perlu build ulang frontend hanya untuk empat nilai ini.

## 4. Daftarkan Android kasir

Di **Project settings → Your apps → Add app → Android**, daftarkan package **`com.selaris.pos`**. Package APK lama `com.kasira.kasira_kasir` berbeda dari aplikasi rilis sekarang.

Tambahkan fingerprint **SHA-1 dan SHA-256** dari sertifikat upload/release. Jika aplikasi dipasang melalui Play Store, tambahkan juga fingerprint sertifikat **App signing** dari Play Console → App integrity. Sertifikat aplikasi yang benar-benar terpasang harus terdaftar.

Fingerprint upload keystore Selaris pada server ini (diverifikasi 4 Oktober 2026):

```text
SHA-1:   E2:D5:0A:1E:E0:9A:86:47:32:B9:E5:74:B3:39:5F:8C:39:25:6B:B8
SHA-256: 2F:49:02:80:8F:50:54:8B:A2:3C:94:C2:DB:12:2D:01:E9:05:4D:2E:D1:82:18:1D:1D:B5:22:0A:14:AB:24:8C
```

Untuk membaca fingerprint APK rilis:

```bash
apksigner verify --print-certs /path/selaris-pos.apk
```

Sesudah provider Google dan fingerprint terpasang, unduh **google-services.json yang baru**. Berkas ini perlu menyertakan OAuth web client (`client_type: 3`) agar Google Sign-In Android mendapatkan server client ID otomatis. Untuk notifikasi aplikasi dapur, tambahkan app **`com.selaris.dapur`** juga; onboarding Google pada perubahan ini ditujukan ke aplikasi kasir.

Pasang berkas lokal untuk build:

```bash
cp /path/google-services.json kasir_app/android/app/google-services.json
```

Folder `android/` dibuat ulang oleh CI. Perbarui secret build menggunakan skrip yang sudah tersedia:

```bash
bash scripts/pasang_google_services.sh /path/google-services.json
```

Kemudian jalankan workflow **Build & Release Selaris Flutter APK** dengan nomor versi baru dan pasang APK hasilnya. Menambahkan JSON ke server tidak mengubah APK yang sudah terpasang. Bila perlu server client ID eksplisit, build Flutter mendukung `--dart-define=GOOGLE_SERVER_CLIENT_ID=<OAuth-web-client-id>`; nilainya client ID Web, bukan client ID Android.

## 5. Tes setelah konfigurasi

1. Web: pilih Google dan batalkan pemilihan akun; layar harus tetap bisa dipakai.
2. Pilih Google yang belum terhubung, isi nomor toko demo lama, ambil kode Sefrekuensi, lalu verifikasi. Toko yang sama harus terbuka.
3. Logout, lalu masuk dengan Google yang sama. Tidak diminta OTP lagi.
4. Coba Google berbeda dengan nomor yang sudah terhubung. Sistem harus menolak penggantian identitas.
5. Nomor baru: verifikasi, isi usaha dan PIN, lalu ikuti onboarding menu. Toko hanya dibuat setelah formulir usaha dikirim.
6. APK baru: ulangi login Google dan buka kasir dengan PIN lokal. APK tanpa konfigurasi Firebase menampilkan pilihan Google yang belum tersedia dan tetap menyediakan OTP.

Saat ini tombol Google sengaja belum aktif jika konfigurasi belum dipasang. Verifikasi token, proof onboarding, dan penolakan token salah diuji otomatis; popup Google sungguhan perlu konfigurasi konsol di atas.

Rujukan: [Google login web](https://firebase.google.com/docs/auth/web/google-signin), [Google login Flutter](https://firebase.google.com/docs/auth/flutter/federated-auth), [fingerprint dan konfigurasi Android](https://firebase.google.com/docs/auth/android/google-signin).
