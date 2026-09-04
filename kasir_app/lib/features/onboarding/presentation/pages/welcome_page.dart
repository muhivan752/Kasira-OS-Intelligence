import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../../../core/theme/kasira_ds.dart';
import '../../../../core/widgets/selaris_mark.dart';

/// Layar 2 onboarding: "Selamat datang". Tiga slide geser tentang apa yang
/// Selaris kerjain sendiri, dua tombol jelas: Daftar / Masuk. Tampil sekali
/// per instalasi (`welcome_seen`), sesudah itu splash langsung ke login.
class WelcomePage extends StatefulWidget {
  const WelcomePage({super.key});

  static const prefsKey = 'welcome_seen';

  @override
  State<WelcomePage> createState() => _WelcomePageState();
}

class _WelcomePageState extends State<WelcomePage> {
  final _controller = PageController();
  int _index = 0;

  // Foto dari Unsplash (lisensi bebas komersial, tanpa atribusi wajib):
  // slide_nota = Pasar Gading Surakarta (Prabu Panji), slide_meja = tiga
  // minuman satu meja (Nathan Dumlao), slide_pelanggan = dua pelanggan di
  // kafe, satu pegang HP (tommao wang). Sudah di-crop 4:3, WebP ~1080px.
  static const _slides = [
    (
      image: 'assets/onboarding/slide_nota.webp',
      icon: LucideIcons.camera,
      title: 'Foto nota belanja,\nharga modal terisi sendiri',
      body: 'Stok bahan bertambah, harga modal dihitung ulang, dan utang supplier tercatat. Anda cukup memfoto notanya.',
    ),
    (
      image: 'assets/onboarding/slide_meja.webp',
      icon: LucideIcons.receipt,
      title: 'Satu meja,\ntiap orang bayar sendiri',
      body: 'Ada yang membayar dengan QRIS, ada yang tunai, ada yang menyusul. Struknya terbit per orang.',
    ),
    (
      image: 'assets/onboarding/slide_pelanggan.webp',
      icon: LucideIcons.messageCircle,
      title: 'Struk ke WhatsApp,\ndata pelanggan terbentuk sendiri',
      body: 'Nomor pelanggan tercatat dari struk. Siapa yang setia dan siapa yang mulai jarang datang jadi terlihat.',
    ),
  ];

  Future<void> _markSeen() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(WelcomePage.prefsKey, true);
  }

  void _go(String route) async {
    await _markSeen();
    if (mounted) context.go(route);
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: KasiraDS.bgBase,
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(KasiraDS.space5, KasiraDS.space4, KasiraDS.space5, KasiraDS.space5),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Row(
                children: [
                  const SelarisMark(size: 28),
                  const SizedBox(width: KasiraDS.space2),
                  Text('Selaris', style: KasiraDS.display(size: 20, color: KasiraDS.textStrong)),
                  const Spacer(),
                  TextButton(
                    onPressed: () => _go('/login'),
                    child: Text('Masuk', style: KasiraDS.sans(size: 14, weight: FontWeight.w700, color: KasiraDS.textMuted)),
                  ),
                ],
              ),
              const SizedBox(height: KasiraDS.space4),
              Expanded(
                child: PageView.builder(
                  controller: _controller,
                  itemCount: _slides.length,
                  onPageChanged: (i) => setState(() => _index = i),
                  itemBuilder: (_, i) {
                    final s = _slides[i];
                    return Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Expanded(
                          child: ClipRRect(
                            borderRadius: KasiraDS.brLg,
                            child: Stack(
                              fit: StackFit.expand,
                              children: [
                                // Gradien tetap jadi latar: kalau aset gagal
                                // dimuat, kartunya nggak pernah kosong.
                                const DecoratedBox(
                                  decoration: BoxDecoration(gradient: KasiraDS.gradientFrekuensiSoft),
                                ),
                                Image.asset(
                                  s.image,
                                  fit: BoxFit.cover,
                                  errorBuilder: (_, __, ___) => const SizedBox.shrink(),
                                ),
                                // Vignette bawah supaya lencana ikon kebaca di
                                // atas foto terang.
                                const DecoratedBox(
                                  decoration: BoxDecoration(
                                    gradient: LinearGradient(
                                      begin: Alignment.topCenter,
                                      end: Alignment.bottomCenter,
                                      stops: [0.55, 1.0],
                                      colors: [Colors.transparent, Color(0x99000000)],
                                    ),
                                  ),
                                ),
                                Positioned(
                                  left: KasiraDS.space3,
                                  bottom: KasiraDS.space3,
                                  child: Container(
                                    width: 44,
                                    height: 44,
                                    decoration: BoxDecoration(
                                      color: Colors.white.withOpacity(0.92),
                                      borderRadius: BorderRadius.circular(14),
                                    ),
                                    child: Icon(s.icon, size: 22, color: KasiraDS.brandPrimary),
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ),
                        const SizedBox(height: KasiraDS.space5),
                        Text(s.title, style: KasiraDS.display(size: 26, color: KasiraDS.textStrong)),
                        const SizedBox(height: KasiraDS.space2),
                        Text(s.body, style: KasiraDS.sans(size: 15, color: KasiraDS.textBody, height: 1.5)),
                      ],
                    );
                  },
                ),
              ),
              const SizedBox(height: KasiraDS.space4),
              Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: List.generate(_slides.length, (i) {
                  final on = i == _index;
                  return AnimatedContainer(
                    duration: KasiraDS.durBase,
                    margin: const EdgeInsets.symmetric(horizontal: 4),
                    width: on ? 22 : 8,
                    height: 8,
                    decoration: BoxDecoration(
                      color: on ? KasiraDS.brandPrimary : KasiraDS.borderDefault,
                      borderRadius: KasiraDS.brPill,
                    ),
                  );
                }),
              ),
              const SizedBox(height: KasiraDS.space5),
              SizedBox(
                height: 54,
                child: FilledButton(
                  onPressed: () => _go('/register'),
                  style: FilledButton.styleFrom(
                    backgroundColor: KasiraDS.brandPrimary,
                    shape: RoundedRectangleBorder(borderRadius: KasiraDS.brPill),
                  ),
                  child: Text('Daftar gratis 30 hari',
                      style: KasiraDS.sans(size: 16, weight: FontWeight.w700, color: KasiraDS.textOnBrand)),
                ),
              ),
              const SizedBox(height: KasiraDS.space2),
              SizedBox(
                height: 50,
                child: OutlinedButton(
                  onPressed: () => _go('/login'),
                  style: OutlinedButton.styleFrom(
                    side: const BorderSide(color: KasiraDS.borderDefault),
                    shape: RoundedRectangleBorder(borderRadius: KasiraDS.brPill),
                  ),
                  child: Text('Sudah punya akun · Masuk',
                      style: KasiraDS.sans(size: 15, weight: FontWeight.w700, color: KasiraDS.textStrong)),
                ),
              ),
              const SizedBox(height: KasiraDS.space2),
              Text('Tanpa kartu kredit · Server di Indonesia',
                  textAlign: TextAlign.center,
                  style: KasiraDS.sans(size: 11.5, color: KasiraDS.textMuted)),
            ],
          ),
        ),
      ),
    );
  }
}
