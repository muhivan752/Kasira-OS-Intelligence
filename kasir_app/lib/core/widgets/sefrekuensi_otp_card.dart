import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../theme/kasira_ds.dart';

/// Iklan halus Sefrekuensi di layar masuk & daftar (keputusan Ivan 4 Sep).
///
/// Dua wujud, satu widget:
/// - Biasa: tawaran "kirim kode lewat Sefrekuensi". Yang punya dapat kode
///   tanpa WhatsApp, yang belum cuma lihat mereknya. WhatsApp tetap tombol
///   utama di LUAR kartu ini supaya orang baru nggak kepaksa pasang app
///   kedua di tengah daftar.
/// - [notFound]: server bilang nomornya belum ada di Sefrekuensi. Jangan
///   buntu: tawarkan Pasang (Play Store) atau kirim lewat WhatsApp saja.
///
/// Kode nggak pernah loncat kanal: yang dipilih di sini, itu yang dikirim.
const kSefrekuensiName = 'Sefrekuensi';
const kSefrekuensiPlayUrl = 'https://play.google.com/store/apps/details?id=com.sefrekuensi.app';

/// Kode dari server buat "nomor belum ada di Sefrekuensi" (HTTP 404 dengan
/// detail berbentuk map). Dipakai login + daftar buat nyalain wujud kedua.
const kSefrekuensiNotFoundCode = 'SEFREKUENSI_NOT_FOUND';

class SefrekuensiOtpCard extends StatelessWidget {
  final bool loading;
  final bool notFound;
  final VoidCallback onPick;
  final VoidCallback onFallbackWhatsapp;

  const SefrekuensiOtpCard({
    super.key,
    required this.loading,
    required this.notFound,
    required this.onPick,
    required this.onFallbackWhatsapp,
  });

  Future<void> _bukaPlayStore() async {
    final uri = Uri.parse(kSefrekuensiPlayUrl);
    await launchUrl(uri, mode: LaunchMode.externalApplication);
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: KasiraDS.brandTint2,
        borderRadius: KasiraDS.brMd,
        border: Border.all(color: KasiraDS.brandSecondary.withOpacity(0.28)),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 36,
            height: 36,
            decoration: BoxDecoration(
              color: KasiraDS.brandSecondary.withOpacity(0.16),
              shape: BoxShape.circle,
            ),
            child: const Icon(Icons.smartphone_rounded, size: 18, color: KasiraDS.brandSecondary),
          ),
          const SizedBox(width: 12),
          Expanded(child: notFound ? _buildNotFound() : _buildOffer()),
        ],
      ),
    );
  }

  ButtonStyle _isiUngu() => FilledButton.styleFrom(
        backgroundColor: KasiraDS.brandSecondary,
        foregroundColor: Colors.white,
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
        shape: RoundedRectangleBorder(borderRadius: KasiraDS.brPill),
        visualDensity: VisualDensity.compact,
      );

  Widget _buildOffer() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text('Untuk pengalaman yang lebih baik',
            style: KasiraDS.sans(size: 13.5, weight: FontWeight.w700, color: KasiraDS.textStrong)),
        const SizedBox(height: 3),
        Text('Punya $kSefrekuensiName? Kode masuk datang sebagai pesan di sana, tanpa lewat WhatsApp.',
            style: KasiraDS.sans(size: 12, color: KasiraDS.textMuted, height: 1.4)),
        const SizedBox(height: 10),
        Wrap(
          crossAxisAlignment: WrapCrossAlignment.center,
          spacing: 12,
          runSpacing: 8,
          children: [
            FilledButton.icon(
              onPressed: loading ? null : onPick,
              style: _isiUngu(),
              icon: loading
                  ? const SizedBox(width: 14, height: 14, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                  : const Icon(Icons.smartphone_rounded, size: 16),
              label: Text('Kirim kode ke $kSefrekuensiName',
                  style: KasiraDS.sans(size: 12.5, weight: FontWeight.w700, color: Colors.white)),
            ),
            GestureDetector(
              onTap: _bukaPlayStore,
              child: Text('Belum punya? Pasang di Play Store',
                  style: KasiraDS.sans(size: 11.5, color: KasiraDS.textMuted).copyWith(decoration: TextDecoration.underline)),
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildNotFound() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text('Nomor ini belum ada di $kSefrekuensiName',
            style: KasiraDS.sans(size: 13.5, weight: FontWeight.w700, color: KasiraDS.textStrong)),
        const SizedBox(height: 3),
        Text('Pasang $kSefrekuensiName dengan nomor yang sama, lalu coba lagi. Atau kirim kodenya lewat WhatsApp saja.',
            style: KasiraDS.sans(size: 12, color: KasiraDS.textMuted, height: 1.4)),
        const SizedBox(height: 10),
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: [
            FilledButton.icon(
              onPressed: _bukaPlayStore,
              style: _isiUngu(),
              icon: const Icon(Icons.download_rounded, size: 16),
              label: Text('Pasang $kSefrekuensiName',
                  style: KasiraDS.sans(size: 12.5, weight: FontWeight.w700, color: Colors.white)),
            ),
            OutlinedButton.icon(
              onPressed: loading ? null : onFallbackWhatsapp,
              style: OutlinedButton.styleFrom(
                foregroundColor: KasiraDS.textBody,
                side: const BorderSide(color: KasiraDS.borderDefault),
                backgroundColor: KasiraDS.surfaceCard,
                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                shape: RoundedRectangleBorder(borderRadius: KasiraDS.brPill),
                visualDensity: VisualDensity.compact,
              ),
              icon: const Icon(Icons.chat_bubble_outline_rounded, size: 16),
              label: Text('Kirim lewat WhatsApp saja',
                  style: KasiraDS.sans(size: 12.5, weight: FontWeight.w700, color: KasiraDS.textBody)),
            ),
          ],
        ),
      ],
    );
  }
}

/// Baca kode kesalahan dari `detail` respons server. `detail` bisa string
/// (pesan biasa) atau map `{code, message}`; dua duanya dipakai backend.
String? otpErrorCode(dynamic detail) {
  if (detail is Map) return detail['code']?.toString();
  return null;
}

String otpErrorMessage(dynamic detail, String fallback) {
  if (detail is Map) return detail['message']?.toString() ?? fallback;
  if (detail is String && detail.isNotEmpty) return detail;
  return fallback;
}
