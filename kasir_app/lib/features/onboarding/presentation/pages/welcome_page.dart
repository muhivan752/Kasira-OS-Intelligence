import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../../../../core/theme/kasira_ds.dart';
import '../../../../core/widgets/selaris_mark.dart';

class WelcomePage extends StatelessWidget {
  const WelcomePage({super.key});
  static const prefsKey = 'welcome_seen';

  Future<void> _continue(BuildContext context) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(prefsKey, true);
    if (context.mounted) context.go('/login');
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        backgroundColor: KasiraDS.bgBase,
        body: SafeArea(
            child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: Center(
              child: ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 480),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      Row(children: [
                        const SelarisMark(size: 28),
                        const SizedBox(width: 10),
                        Flexible(
                            child: FittedBox(
                                fit: BoxFit.scaleDown,
                                child: Text('Selaris',
                                    style: KasiraDS.display(
                                        size: 22, color: KasiraDS.textStrong))))
                      ]),
                      const SizedBox(height: 32),
                      ClipRRect(
                          borderRadius: KasiraDS.brLg,
                          child: Image.asset(
                              'assets/onboarding/slide_meja.webp',
                              height: 240,
                              fit: BoxFit.cover)),
                      const SizedBox(height: 32),
                      Text('Usaha Anda,\nlebih mudah dikelola.',
                          style: KasiraDS.display(
                              size: 28, color: KasiraDS.textStrong)),
                      const SizedBox(height: 12),
                      Text(
                          'Catat penjualan, atur menu, dan kirim struk dari satu tempat. Mulai dengan akun Google atau kode Sefrekuensi.',
                          style: KasiraDS.sans(
                              size: 15, color: KasiraDS.textBody, height: 1.5)),
                      const SizedBox(height: 32),
                      FilledButton(
                          onPressed: () => _continue(context),
                          child: const Text('Lanjut ke akun')),
                      const SizedBox(height: 12),
                      Text(
                          'Sudah punya toko? Masuk untuk melanjutkan usaha Anda.',
                          textAlign: TextAlign.center,
                          style: KasiraDS.sans(
                              size: 13, color: KasiraDS.textMuted)),
                    ],
                  ))),
        )),
      );
}
