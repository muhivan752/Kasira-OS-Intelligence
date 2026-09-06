import 'package:flutter/material.dart';

/// Membatasi lebar isi halaman di layar lebar.
///
/// Halaman daftar dan formulir di app ini semuanya dirancang di layar HP,
/// lalu dipakai apa adanya di tablet. Di tablet tidur 1280px hasilnya satu
/// baris teks membentang dari ujung ke ujung: mata harus jalan jauh untuk
/// membaca satu baris, dan kolom kiri (label) jadi jauh sekali dari kolom
/// kanan (nilai). Bukan rusak, tapi kelihatan seperti halaman HP yang
/// ditarik paksa, dan itu yang pertama dilihat calon pembeli.
///
/// Yang dibatasi HANYA isinya. Header, AppBar, dan bar bawah tetap selebar
/// layar: kalau ikut dipersempit, warnanya berhenti di tengah dan halaman
/// malah kelihatan seperti kartu mengambang.
///
/// 720px kira-kira selebar tablet berdiri, ukuran yang memang sudah dipakai
/// dan sudah enak dibaca.
class LebarKonten extends StatelessWidget {
  const LebarKonten({super.key, required this.child, this.maks = 720});

  final Widget child;
  final double maks;

  @override
  Widget build(BuildContext context) {
    // Di layar sempit ConstrainedBox tidak melakukan apa-apa (lebar layar
    // sudah di bawah batas), jadi tidak perlu dicabang. Center yang menaruh
    // isinya di tengah begitu ruangnya lebih lebar dari batas.
    return Center(
      child: ConstrainedBox(
        constraints: BoxConstraints(maxWidth: maks),
        child: child,
      ),
    );
  }
}
