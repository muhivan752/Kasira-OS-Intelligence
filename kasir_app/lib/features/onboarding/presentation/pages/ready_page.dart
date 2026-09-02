import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../../../core/services/session_cache.dart';
import '../../../../core/theme/kasira_ds.dart';
import '../../../settings/presentation/pages/printer_settings_page.dart';

/// Layar 7 onboarding: "Siap jualan". Muncul sekali sesudah daftar + PIN,
/// menggantikan dashboard kosong di menit pertama. Tiga langkah, semuanya
/// bisa dilewati — yang penting orangnya tahu harus ke mana.
///
/// Mode latihan (transaksi nggak masuk laporan) SENGAJA belum dibangun —
/// keputusan 2 Sep: nanti. Langkah 3 cukup "buka shift".
class ReadyPage extends StatelessWidget {
  const ReadyPage({super.key});

  static const prefsKey = 'onboarding_ready_done';

  Future<void> _done(BuildContext context, String route) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(prefsKey, true);
    if (context.mounted) context.go(route);
  }

  @override
  Widget build(BuildContext context) {
    final cache = SessionCache.instance;
    final bizName = cache.outletName ?? 'Usahamu';
    final phone = cache.phone ?? '';

    return Scaffold(
      backgroundColor: KasiraDS.bgBase,
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(KasiraDS.space5),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const SizedBox(height: KasiraDS.space3),
              Text('$bizName siap jualan 🎉', style: KasiraDS.display(size: 26, color: KasiraDS.textStrong)),
              const SizedBox(height: KasiraDS.space2),
              Text(
                'Tiga langkah supaya transaksi pertama lancar. Bisa dilewati, pengaturannya tetap tersedia nanti.',
                style: KasiraDS.sans(size: 14, color: KasiraDS.textMuted, height: 1.5),
              ),
              const SizedBox(height: KasiraDS.space5),
              _Step(done: true, index: 0, title: 'Akun & PIN', subtitle: phone.isNotEmpty ? '+$phone' : 'Sudah dibuat'),
              const SizedBox(height: KasiraDS.space2),
              _Step(index: 1, title: 'Tambah 3 menu terlaris', subtitle: 'Cukup nama dan harga. Resep bisa menyusul.', onTap: () => _done(context, '/dashboard')),
              const SizedBox(height: KasiraDS.space2),
              _Step(
                index: 2,
                title: 'Hubungkan printer Bluetooth',
                subtitle: 'Opsional, struk bisa lewat WhatsApp dulu.',
                onTap: () async {
                  await Navigator.of(context).push(MaterialPageRoute(builder: (_) => const PrinterSettingsPage()));
                },
              ),
              const SizedBox(height: KasiraDS.space2),
              _Step(index: 3, title: 'Buka shift & mulai kasir', subtitle: 'Isi modal awal laci, kasir langsung siap dipakai.', onTap: () => _done(context, '/shift/open')),
              const Spacer(),
              SizedBox(
                height: 54,
                child: FilledButton(
                  onPressed: () => _done(context, '/dashboard'),
                  style: FilledButton.styleFrom(
                    backgroundColor: KasiraDS.brandPrimary,
                    shape: RoundedRectangleBorder(borderRadius: KasiraDS.brPill),
                  ),
                  child: Text('Mulai: tambah menu', style: KasiraDS.sans(size: 16, weight: FontWeight.w700, color: KasiraDS.textOnBrand)),
                ),
              ),
              const SizedBox(height: KasiraDS.space2),
              TextButton(
                onPressed: () => _done(context, '/shift/open'),
                child: Text('Lewati, langsung ke kasir', style: KasiraDS.sans(size: 14, weight: FontWeight.w600, color: KasiraDS.textMuted)),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _Step extends StatelessWidget {
  final bool done;
  final int index;
  final String title;
  final String subtitle;
  final VoidCallback? onTap;

  const _Step({this.done = false, required this.index, required this.title, required this.subtitle, this.onTap});

  @override
  Widget build(BuildContext context) {
    final tint = done ? KasiraDS.success : KasiraDS.brandPrimary;
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        borderRadius: KasiraDS.brMd,
        child: Container(
          padding: const EdgeInsets.all(KasiraDS.space3),
          decoration: BoxDecoration(
            color: KasiraDS.surfaceCard,
            borderRadius: KasiraDS.brMd,
            border: Border.all(color: KasiraDS.borderSubtle),
          ),
          child: Row(
            children: [
              Container(
                width: 34,
                height: 34,
                alignment: Alignment.center,
                decoration: BoxDecoration(color: tint.withOpacity(0.12), borderRadius: KasiraDS.brSm),
                child: done
                    ? Icon(LucideIcons.check, size: 18, color: tint)
                    : Text('$index', style: KasiraDS.sans(size: 14, weight: FontWeight.w800, color: tint)),
              ),
              const SizedBox(width: KasiraDS.space3),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(title, style: KasiraDS.sans(size: 14.5, weight: FontWeight.w700, color: KasiraDS.textStrong)),
                    Text(subtitle, style: KasiraDS.sans(size: 12, color: KasiraDS.textMuted)),
                  ],
                ),
              ),
              if (!done) const Icon(LucideIcons.chevronRight, size: 18, color: KasiraDS.textMuted),
            ],
          ),
        ),
      ),
    );
  }
}
