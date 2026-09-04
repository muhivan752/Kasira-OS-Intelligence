import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';

import '../config/app_config.dart';
import '../services/session_cache.dart';
import '../theme/kasira_ds.dart';

/// Panel untuk metode yang kasir konfirmasi sendiri (mig 103): QRIS statis
/// toko, transfer bank, kartu EDC. Dipakai modal bayar POS dan ketiga modal
/// bayar tab supaya teks dan tampilannya satu. Datanya dari SessionCache
/// (`payment_methods`, `qris_static_image_url`, `bank_*`), diisi dari
/// GET /outlets/{id} dan halaman Pengaturan app.
///
/// `method` = nilai API: 'qris' | 'transfer' | 'card'.
class ManualPaymentInfo extends StatelessWidget {
  final String method;
  final double amount;
  final bool compact;

  const ManualPaymentInfo({super.key, required this.method, required this.amount, this.compact = false});

  static final _rp = NumberFormat.currency(locale: 'id_ID', symbol: 'Rp ', decimalDigits: 0);

  static String _abs(String u) => u.startsWith('http') ? u : '${AppConfig.baseUrl}$u';

  @override
  Widget build(BuildContext context) {
    final c = SessionCache.instance;
    final children = <Widget>[];
    String hint;

    switch (method) {
      case 'qris':
        final url = c.qrisStaticImageUrl;
        final hasImg = url != null && url.isNotEmpty;
        final side = compact ? 170.0 : 220.0;
        children.add(ClipRRect(
          borderRadius: KasiraDS.brMd,
          child: Container(
            width: side,
            height: side,
            color: Colors.white,
            child: hasImg
                ? CachedNetworkImage(
                    imageUrl: _abs(url),
                    fit: BoxFit.contain,
                    placeholder: (_, __) => const Center(child: CircularProgressIndicator(strokeWidth: 2)),
                    errorWidget: (_, __, ___) => const Icon(LucideIcons.qrCode, size: 56, color: KasiraDS.textMuted),
                  )
                : const Icon(LucideIcons.qrCode, size: 56, color: KasiraDS.textMuted),
          ),
        ));
        hint = hasImg
            ? 'Pelanggan memindai QRIS toko. Setelah notifikasi uang masuk, tekan tombol konfirmasi.'
            : 'Tunjukkan QRIS toko ke pelanggan. Setelah notifikasi uang masuk, tekan tombol konfirmasi. Gambar QRIS bisa diunggah di Pengaturan, bagian Metode pembayaran.';
        break;
      case 'transfer':
        final hasBank = (c.bankAccountNumber ?? '').isNotEmpty;
        children.add(const Icon(LucideIcons.landmark, size: 30, color: KasiraDS.textMuted));
        if (hasBank) {
          children.add(const SizedBox(height: 10));
          children.add(Text(
            '${(c.bankName ?? '').trim().isEmpty ? 'Bank' : c.bankName} ${c.bankAccountNumber}',
            textAlign: TextAlign.center,
            style: KasiraDS.display(size: compact ? 18 : 21, color: KasiraDS.textStrong),
          ));
          if ((c.bankAccountName ?? '').isNotEmpty) {
            children.add(Text('a.n. ${c.bankAccountName}', style: KasiraDS.sans(size: 13, color: KasiraDS.textBody)));
          }
        }
        hint = hasBank
            ? 'Setelah transfer masuk, tekan tombol konfirmasi.'
            : 'Rekening toko belum diisi. Isi di Pengaturan, bagian Metode pembayaran.';
        break;
      default:
        children.add(const Icon(LucideIcons.creditCard, size: 30, color: KasiraDS.textMuted));
        hint = 'Gesek atau tap di mesin EDC, lalu tekan tombol konfirmasi.';
    }

    return Container(
      width: double.infinity,
      padding: EdgeInsets.all(compact ? 14 : 18),
      decoration: BoxDecoration(color: KasiraDS.surfaceSunken, borderRadius: KasiraDS.brLg),
      child: Column(
        children: [
          ...children,
          const SizedBox(height: 10),
          Text(_rp.format(amount), style: KasiraDS.display(size: compact ? 20 : 24, color: KasiraDS.textStrong)),
          const SizedBox(height: 6),
          Text(hint, textAlign: TextAlign.center, style: KasiraDS.sans(size: 13, color: KasiraDS.textMuted, height: 1.4)),
        ],
      ),
    );
  }
}
