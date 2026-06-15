import 'dart:async';
import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';
import '../../../../core/config/app_config.dart';
import '../../../../core/services/session_cache.dart';
import '../../../../core/theme/app_colors.dart';
import '../../providers/tab_provider.dart';

/// Modal yang nungguin webhook Xendit settle QRIS payment.
///
/// Behavior:
/// - Display QR string + countdown 5 menit (atau pakai qris_expired_at kalau ada)
/// - Poll GET /payments/{id}/status setiap 3 detik
/// - On status='paid' → atomic claim-print → invoke onPaid → close
/// - On status='failed'/'expired' → tampilkan error + close
/// - Timer expire → close + return null (kasir bisa retry pay-split)
/// - Cancel button → close + return null
///
/// onPaid: dipanggil setelah backend confirm paid + claim print sukses. Caller
/// harus refresh tab + trigger autoprint via callback yg di-pass.
class QrisWaitingModal extends ConsumerStatefulWidget {
  final String tabId;
  final PendingQrisModel pendingQris;

  /// Dipanggil kalau backend confirm payment.status='paid' DAN claim-print
  /// success (claimed=true). Caller responsible untuk autoprint + refresh tab.
  /// Kalau claimed=false (sudah ke-print path lain), onPaid TIDAK dipanggil.
  final Future<void> Function(String paymentId)? onPaidAndClaimedPrint;

  const QrisWaitingModal({
    super.key,
    required this.tabId,
    required this.pendingQris,
    this.onPaidAndClaimedPrint,
  });

  @override
  ConsumerState<QrisWaitingModal> createState() => _QrisWaitingModalState();
}

class _QrisWaitingModalState extends ConsumerState<QrisWaitingModal> {
  Timer? _pollTimer;
  Timer? _countdownTimer;
  int _secondsLeft = 300; // 5 min default
  String _status = 'pending';
  String? _error;
  bool _disposed = false;

  final _currency =
      NumberFormat.currency(locale: 'id_ID', symbol: 'Rp ', decimalDigits: 0);

  @override
  void initState() {
    super.initState();
    _status = widget.pendingQris.status;

    // Compute seconds_left from qris_expired_at if available
    final expiry = widget.pendingQris.qrisExpiredAt;
    if (expiry != null) {
      final diff = expiry.difference(DateTime.now()).inSeconds;
      if (diff > 0) _secondsLeft = diff;
    }

    if (widget.pendingQris.isReady) {
      _startCountdown();
      _startPolling();
    }
  }

  @override
  void dispose() {
    _disposed = true;
    _pollTimer?.cancel();
    _countdownTimer?.cancel();
    super.dispose();
  }

  void _startCountdown() {
    _countdownTimer = Timer.periodic(const Duration(seconds: 1), (t) {
      if (_disposed) return;
      if (_secondsLeft <= 0) {
        t.cancel();
        _onTimeout();
        return;
      }
      setState(() => _secondsLeft -= 1);
    });
  }

  void _startPolling() {
    _pollTimer = Timer.periodic(const Duration(seconds: 3), (_) async {
      if (_disposed) return;
      await _checkStatus();
    });
  }

  Future<void> _checkStatus() async {
    try {
      final cache = SessionCache.instance;
      final dio = Dio(BaseOptions(
        baseUrl: AppConfig.apiV1,
        connectTimeout: const Duration(seconds: 6),
        receiveTimeout: const Duration(seconds: 6),
      ));
      final res = await dio.get(
        '/payments/${widget.pendingQris.paymentId}/status',
        options: Options(headers: cache.authHeaders),
      );
      final data = res.data['data'] as Map<String, dynamic>?;
      if (data == null) return;
      final newStatus = data['status'] as String? ?? 'pending';
      if (_disposed) return;

      if (newStatus == 'paid') {
        _pollTimer?.cancel();
        _countdownTimer?.cancel();
        await _onPaid();
      } else if (newStatus == 'failed' || newStatus == 'expired' || newStatus == 'cancelled') {
        _pollTimer?.cancel();
        _countdownTimer?.cancel();
        if (mounted) {
          setState(() {
            _status = newStatus;
            _error = newStatus == 'expired'
                ? 'QRIS sudah kedaluwarsa — silakan generate ulang.'
                : 'Pembayaran gagal/dibatalkan — silakan coba lagi.';
          });
        }
      }
    } catch (_) {
      // Network glitch — retry next tick. Don't surface error.
    }
  }

  Future<void> _onPaid() async {
    // Atomic claim-print: backend cek receipt_printed_at IS NULL → set timestamp
    // → return claimed=true. Race-safe: kalau webhook + poll trigger autoprint
    // overlap, only one path proceeds.
    bool claimedPrint = false;
    try {
      final cache = SessionCache.instance;
      final dio = Dio(BaseOptions(
        baseUrl: AppConfig.apiV1,
        connectTimeout: const Duration(seconds: 6),
        receiveTimeout: const Duration(seconds: 6),
      ));
      final res = await dio.post(
        '/payments/${widget.pendingQris.paymentId}/claim-print',
        options: Options(headers: cache.authHeaders),
      );
      final data = res.data['data'] as Map<String, dynamic>?;
      claimedPrint = (data?['claimed'] as bool?) ?? false;
    } catch (_) {
      // Treat as not-claimed → skip autoprint to be safe (no double-print).
      claimedPrint = false;
    }

    if (mounted) setState(() => _status = 'paid');
    if (claimedPrint && widget.onPaidAndClaimedPrint != null) {
      try {
        await widget.onPaidAndClaimedPrint!(widget.pendingQris.paymentId);
      } catch (_) {
        // Print issue gak boleh block flow.
      }
    }
    if (mounted) Navigator.pop(context, true); // signal: paid
  }

  void _onTimeout() {
    if (!mounted) return;
    setState(() {
      _status = 'expired';
      _error = 'QRIS sudah kedaluwarsa — silakan generate ulang.';
    });
  }

  String _formatCountdown(int seconds) {
    final m = (seconds ~/ 60).toString().padLeft(2, '0');
    final s = (seconds % 60).toString().padLeft(2, '0');
    return '$m:$s';
  }

  @override
  Widget build(BuildContext context) {
    final qris = widget.pendingQris;
    final isReady = qris.isReady && _status == 'pending';

    return Padding(
      padding: EdgeInsets.only(
        left: 20,
        right: 20,
        top: 20,
        bottom: MediaQuery.of(context).viewInsets.bottom + 20,
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          Row(
            children: [
              const Icon(LucideIcons.qrCode, color: AppColors.primary),
              const SizedBox(width: 12),
              Text('Tunggu Pembayaran QRIS',
                  style: Theme.of(context).textTheme.titleLarge),
              const Spacer(),
              if (_status == 'pending')
                IconButton(
                  onPressed: () => Navigator.pop(context, false),
                  icon: const Icon(LucideIcons.x),
                  tooltip: 'Batal nunggu',
                )
              else
                IconButton(
                  onPressed: () => Navigator.pop(context, _status == 'paid'),
                  icon: const Icon(LucideIcons.check),
                  tooltip: 'Tutup',
                ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            'Tagihan: ${_currency.format(qris.amountDue)}',
            style: const TextStyle(
                fontWeight: FontWeight.bold, fontSize: 18, color: AppColors.primary),
          ),
          const SizedBox(height: 20),

          if (qris.isManualCheck) ...[
            _buildManualCheckCard(),
          ] else if (qris.isFailed) ...[
            _buildFailedCard('Gagal generate QR — coba lagi atau periksa konfigurasi Xendit.'),
          ] else if (_status == 'paid') ...[
            _buildPaidCard(),
          ] else if (_error != null) ...[
            _buildFailedCard(_error!),
          ] else if (isReady) ...[
            // QR string display — caller can scan via Xendit-compatible app
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: AppColors.border),
              ),
              child: Column(
                children: [
                  // QR code as encoded text — Flutter doesn't ship qr_flutter by
                  // default; show string + ask kasir to render via dashboard if
                  // needed. Future: add qr_flutter package.
                  SelectableText(
                    qris.qrisUrl ?? '',
                    style: const TextStyle(
                      fontFamily: 'monospace',
                      fontSize: 11,
                    ),
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'String QR di atas — render via app Xendit/QRIS-compatible',
                    style: TextStyle(
                      color: AppColors.textTertiary,
                      fontSize: 11,
                      fontStyle: FontStyle.italic,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 20),
            // Countdown
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
              decoration: BoxDecoration(
                color: AppColors.warning.withOpacity(0.1),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  const Icon(LucideIcons.clock, size: 16, color: AppColors.warning),
                  const SizedBox(width: 8),
                  Text(
                    'Sisa waktu: ${_formatCountdown(_secondsLeft)}',
                    style: const TextStyle(fontWeight: FontWeight.w600, color: AppColors.warning),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 12),
            const Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                SizedBox(
                  width: 14,
                  height: 14,
                  child: CircularProgressIndicator(strokeWidth: 2),
                ),
                SizedBox(width: 10),
                Text('Cek status pembayaran tiap 3 detik...',
                    style: TextStyle(fontSize: 12)),
              ],
            ),
          ],

          const SizedBox(height: 20),
          if (_status == 'pending') ...[
            SizedBox(
              width: double.infinity,
              child: OutlinedButton.icon(
                onPressed: () => Navigator.pop(context, false),
                icon: const Icon(LucideIcons.x, size: 16),
                label: const Text('Batalkan & Tunggu Manual'),
              ),
            ),
            const SizedBox(height: 4),
            Text(
              'Webhook Xendit tetap update tab kalau customer akhirnya bayar — kamu bisa cek tab list nanti.',
              style: TextStyle(fontSize: 11, color: AppColors.textTertiary),
              textAlign: TextAlign.center,
            ),
          ] else ...[
            SizedBox(
              width: double.infinity,
              child: FilledButton.icon(
                onPressed: () => Navigator.pop(context, _status == 'paid'),
                icon: const Icon(LucideIcons.check, size: 16),
                label: const Text('Tutup'),
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildManualCheckCard() {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.warning.withOpacity(0.1),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.warning),
      ),
      child: Column(
        children: [
          const Icon(LucideIcons.alertTriangle, size: 32, color: AppColors.warning),
          const SizedBox(height: 8),
          const Text(
            'Verifikasi Manual',
            style: TextStyle(fontWeight: FontWeight.bold, color: AppColors.warning),
          ),
          const SizedBox(height: 4),
          Text(
            'Xendit lambat respon. Admin akan cek dashboard Xendit untuk verify pembayaran.',
            style: TextStyle(fontSize: 12, color: AppColors.textSecondary),
            textAlign: TextAlign.center,
          ),
        ],
      ),
    );
  }

  Widget _buildFailedCard(String msg) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.error.withOpacity(0.1),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.error),
      ),
      child: Column(
        children: [
          const Icon(LucideIcons.xCircle, size: 32, color: AppColors.error),
          const SizedBox(height: 8),
          Text(
            msg,
            style: const TextStyle(fontWeight: FontWeight.w600, color: AppColors.error),
            textAlign: TextAlign.center,
          ),
        ],
      ),
    );
  }

  Widget _buildPaidCard() {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.success.withOpacity(0.1),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.success),
      ),
      child: const Column(
        children: [
          Icon(LucideIcons.checkCircle, size: 32, color: AppColors.success),
          SizedBox(height: 8),
          Text(
            'Pembayaran Sukses!',
            style: TextStyle(fontWeight: FontWeight.bold, color: AppColors.success),
          ),
        ],
      ),
    );
  }
}
