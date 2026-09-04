import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:url_launcher/url_launcher.dart';

import '../config/app_config.dart';
import '../services/session_cache.dart';
import '../theme/kasira_ds.dart';
import 'sefrekuensi_otp_card.dart' show kSefrekuensiName, kSefrekuensiPlayUrl;

/// Banner ajakan pasang Sefrekuensi di titik sakit (langkah 3, 4 Sep 2026):
/// halaman Pesanan Online. Alasannya ditaruh di sini, bukan di Beranda: orang
/// yang buka halaman ini lagi mikirin "pesanan masuk kapan", dan itu persis
/// yang Sefrekuensi selesaikan (kabar masuk walau app ditutup).
///
/// Status nomor toko dicek ke server (`/outlets/{id}/sefrekuensi-status`,
/// cache 1 jam di prefs). Sudah punya = nggak dirender. Tombol tutup = diam
/// 7 hari, bukan selamanya: yang belum pasang hari ini mungkin pasang bulan
/// depan sesudah kelewat satu pesanan.
class SefrekuensiNudgeBanner extends StatefulWidget {
  const SefrekuensiNudgeBanner({super.key});

  @override
  State<SefrekuensiNudgeBanner> createState() => _SefrekuensiNudgeBannerState();
}

class _SefrekuensiNudgeBannerState extends State<SefrekuensiNudgeBanner> {
  static const _prefStatus = 'sefre_status_json';
  static const _prefStatusAt = 'sefre_status_at';
  static const _prefDismissUntil = 'sefre_nudge_dismiss_until';

  bool _show = false;
  String _playUrl = kSefrekuensiPlayUrl;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final prefs = await SharedPreferences.getInstance();
    final now = DateTime.now().millisecondsSinceEpoch;
    if ((prefs.getInt(_prefDismissUntil) ?? 0) > now) return;

    bool? connected;
    bool enabled = true;
    final at = prefs.getInt(_prefStatusAt) ?? 0;
    if (now - at < 3600 * 1000) {
      final s = prefs.getString(_prefStatus);
      if (s != null) {
        connected = s.contains('"connected":true');
        enabled = !s.contains('"enabled":false');
      }
    }
    if (connected == null) {
      final outletId = SessionCache.instance.outletId;
      if (outletId == null) return;
      try {
        final dio = Dio(BaseOptions(
          baseUrl: AppConfig.apiV1,
          headers: SessionCache.instance.authHeaders,
          connectTimeout: const Duration(seconds: 5),
          receiveTimeout: const Duration(seconds: 8),
        ));
        final r = await dio.get('/outlets/$outletId/sefrekuensi-status');
        final d = (r.data['data'] as Map?) ?? const {};
        connected = d['connected'] == true;
        enabled = d['enabled'] != false;
        if (d['play_url'] is String && (d['play_url'] as String).isNotEmpty) _playUrl = d['play_url'];
        prefs.setString(_prefStatus, '{"connected":$connected,"enabled":$enabled}');
        prefs.setInt(_prefStatusAt, now);
      } catch (_) {
        return; // offline atau server nggak siap: jangan nampilin apa apa
      }
    }
    if (!mounted) return;
    setState(() => _show = enabled && connected == false);
  }

  Future<void> _dismiss() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setInt(_prefDismissUntil, DateTime.now().add(const Duration(days: 7)).millisecondsSinceEpoch);
    if (mounted) setState(() => _show = false);
  }

  @override
  Widget build(BuildContext context) {
    if (!_show) return const SizedBox.shrink();
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 0, 16, 10),
      child: Container(
        padding: const EdgeInsets.fromLTRB(12, 12, 8, 12),
        decoration: BoxDecoration(
          color: KasiraDS.brandTint2,
          borderRadius: KasiraDS.brMd,
          border: Border.all(color: KasiraDS.brandSecondary.withOpacity(0.28)),
        ),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              width: 34,
              height: 34,
              decoration: BoxDecoration(color: KasiraDS.brandSecondary.withOpacity(0.16), shape: BoxShape.circle),
              child: const Icon(Icons.notifications_active_rounded, size: 18, color: KasiraDS.brandSecondary),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('Pesanan masuk saat app ditutup?',
                      style: KasiraDS.sans(size: 13.5, weight: FontWeight.w700, color: KasiraDS.textStrong)),
                  const SizedBox(height: 2),
                  Text('Pasang $kSefrekuensiName dengan nomor toko. Kabar pesanan online, reservasi, dan bukti bayar langsung jadi notifikasi di HP, tanpa bergantung WhatsApp.',
                      style: KasiraDS.sans(size: 12, color: KasiraDS.textMuted, height: 1.4)),
                  const SizedBox(height: 8),
                  FilledButton.icon(
                    onPressed: () => launchUrl(Uri.parse(_playUrl), mode: LaunchMode.externalApplication),
                    style: FilledButton.styleFrom(
                      backgroundColor: KasiraDS.brandSecondary,
                      foregroundColor: Colors.white,
                      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                      shape: RoundedRectangleBorder(borderRadius: KasiraDS.brPill),
                      visualDensity: VisualDensity.compact,
                    ),
                    icon: const Icon(Icons.download_rounded, size: 16),
                    label: Text('Pasang $kSefrekuensiName',
                        style: KasiraDS.sans(size: 12.5, weight: FontWeight.w700, color: Colors.white)),
                  ),
                ],
              ),
            ),
            IconButton(
              onPressed: _dismiss,
              tooltip: 'Nanti saja',
              icon: const Icon(Icons.close_rounded, size: 18, color: KasiraDS.textMuted),
              visualDensity: VisualDensity.compact,
            ),
          ],
        ),
      ),
    );
  }
}
