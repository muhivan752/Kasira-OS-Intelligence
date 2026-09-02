import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';

import '../config/app_config.dart';
import '../services/session_cache.dart';
import '../theme/kasira_ds.dart';
import '../utils/phone_normalize.dart';

/// Warna resmi WhatsApp — sengaja BUKAN token brand Selaris. Tombol WA di
/// [showTabReceiptSheet] juga pakai hijau ini, jadi kasir lihat warna yang sama
/// dari tombol yang dia pencet sampai dialog yang kebuka.
const _waGreen = Color(0xFF25D366);

/// Dialog input nomor WA + nama optional → kirim struk via WhatsApp.
///
/// Backend `POST /payments/send-receipt` upsert customer (tenant + phone),
/// auto-link order.customer_id kalau masih null (data capture untuk AI/KG/event store),
/// lalu kirim struk via Fonnte.
///
/// Caller pakai pattern:
/// ```dart
/// showDialog(
///   context: context,
///   builder: (_) => SendWaReceiptDialog(
///     orderId: orderId,
///     paymentId: paymentId,  // optional — subset receipt untuk pay-items/split
///   ),
/// );
/// ```
class SendWaReceiptDialog extends StatefulWidget {
  final String orderId;
  final String? paymentId;

  /// Optional default phone (misal: prefilled dari customer history).
  final String? defaultPhone;

  /// Optional default name.
  final String? defaultName;

  const SendWaReceiptDialog({
    super.key,
    required this.orderId,
    this.paymentId,
    this.defaultPhone,
    this.defaultName,
  });

  @override
  State<SendWaReceiptDialog> createState() => _SendWaReceiptDialogState();
}

class _SendWaReceiptDialogState extends State<SendWaReceiptDialog> {
  final _phoneController = TextEditingController();
  final _nameController = TextEditingController();
  bool _isSending = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    if (widget.defaultPhone != null) _phoneController.text = widget.defaultPhone!;
    if (widget.defaultName != null) _nameController.text = widget.defaultName!;
  }

  @override
  void dispose() {
    _phoneController.dispose();
    _nameController.dispose();
    super.dispose();
  }

  /// Normalisasi lewat [normalizeIndoPhone] — helper yang SAMA dipakai
  /// `add_customer_modal`. Wajib satu sumber: `/payments/send-receipt` nge-upsert
  /// customer by (tenant, phone), jadi kalau dua jalur ini beda format, satu
  /// orang bisa jadi dua baris customer.
  bool _isValid(String? normalized) =>
      normalized != null &&
      normalized.startsWith('62') &&
      normalized.length >= 10 &&
      normalized.length <= 15;

  Future<void> _submit() async {
    final phone = normalizeIndoPhone(_phoneController.text);
    if (!_isValid(phone)) {
      setState(() => _error = 'Nomor WA tidak valid (contoh: 081234567890)');
      return;
    }
    setState(() {
      _isSending = true;
      _error = null;
    });

    // Di-capture SEBELUM pop. Sesudah `Navigator.pop`, element dialog-nya mati
    // dan `ScaffoldMessenger.of(context)` bisa throw "deactivated widget's
    // ancestor" — snackbar-nya senyap gak muncul. Lihat CLAUDE.md gotcha #22.
    final navigator = Navigator.of(context);
    final messenger = ScaffoldMessenger.of(context);

    final cache = SessionCache.instance;
    final dio = Dio(BaseOptions(
      baseUrl: AppConfig.apiV1,
      connectTimeout: const Duration(seconds: 10),
      receiveTimeout: const Duration(seconds: 15),
    ));

    try {
      final response = await dio.post(
        '/payments/send-receipt',
        options: Options(headers: cache.authHeaders),
        data: {
          'order_id': widget.orderId,
          'phone': phone,
          if (widget.paymentId != null) 'payment_id': widget.paymentId,
          if (_nameController.text.trim().isNotEmpty) 'customer_name': _nameController.text.trim(),
        },
      );

      final data = response.data['data'] as Map<String, dynamic>?;
      final sent = data?['sent'] == true;
      final maskedPhone = data?['phone'] as String? ?? '****';

      if (!mounted) return;
      navigator.pop();
      messenger.showSnackBar(
        SnackBar(
          content: Text(
            sent
                ? 'Struk terkirim ke $maskedPhone'
                : 'Struk gagal terkirim, cek koneksi WA',
          ),
          backgroundColor: sent ? KasiraDS.success : KasiraDS.warning,
          behavior: SnackBarBehavior.floating,
          duration: const Duration(seconds: 3),
        ),
      );
    } on DioException catch (e) {
      final msg = e.response?.data?['detail']?.toString() ??
          e.message ??
          'Gagal kirim struk';
      if (mounted) {
        setState(() {
          _isSending = false;
          _error = msg;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _isSending = false;
          _error = 'Error: $e';
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Dialog(
      backgroundColor: KasiraDS.surfaceCard,
      insetPadding: const EdgeInsets.symmetric(horizontal: 20, vertical: 24),
      shape: RoundedRectangleBorder(borderRadius: KasiraDS.brXl),
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 460),
        // Field pertama autofocus → keyboard naik. Tanpa scroll, dialog-nya
        // overflow di HP pendek.
        child: SingleChildScrollView(
          padding: const EdgeInsets.fromLTRB(20, 20, 20, 18),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _header(),
              const SizedBox(height: 16),
              Text(
                'Customer terima struk, dan nomornya kesimpan buat loyalty & insight.',
                style: KasiraDS.sans(size: 12.5, color: KasiraDS.textMuted, height: 1.35),
              ),
              const SizedBox(height: 18),
              _field(
                label: 'Nomor WhatsApp *',
                icon: LucideIcons.phone,
                hint: '081234567890',
                controller: _phoneController,
                keyboardType: TextInputType.phone,
                autofocus: true,
                textInputAction: TextInputAction.next,
                inputFormatters: [
                  FilteringTextInputFormatter.allow(RegExp(r'[0-9+\-\s]')),
                  LengthLimitingTextInputFormatter(16),
                ],
              ),
              const SizedBox(height: 12),
              _field(
                label: 'Nama Customer (opsional)',
                icon: LucideIcons.user,
                hint: 'Misal: Pak Adit',
                controller: _nameController,
                textInputAction: TextInputAction.done,
                onSubmitted: (_) => _isSending ? null : _submit(),
              ),
              if (_error != null) ...[
                const SizedBox(height: 12),
                _errorBox(_error!),
              ],
              const SizedBox(height: 20),
              _actions(),
            ],
          ),
        ),
      ),
    );
  }

  Widget _header() {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Container(
          width: 42,
          height: 42,
          decoration: BoxDecoration(
            color: _waGreen.withOpacity(0.12),
            borderRadius: KasiraDS.brMd,
          ),
          child: const Icon(LucideIcons.messageCircle, color: _waGreen, size: 21),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const SizedBox(height: 2),
              Text('Kirim Struk',
                  style: KasiraDS.display(size: 19, color: KasiraDS.textStrong)),
              const SizedBox(height: 3),
              Text('via WhatsApp',
                  style: KasiraDS.eyebrow(color: KasiraDS.textMuted)),
            ],
          ),
        ),
        IconButton(
          onPressed: _isSending ? null : () => Navigator.of(context).pop(),
          icon: const Icon(LucideIcons.x, size: 20),
          color: KasiraDS.textMuted,
          visualDensity: VisualDensity.compact,
          tooltip: 'Tutup',
        ),
      ],
    );
  }

  Widget _field({
    required String label,
    required IconData icon,
    required String hint,
    required TextEditingController controller,
    TextInputType keyboardType = TextInputType.text,
    List<TextInputFormatter>? inputFormatters,
    bool autofocus = false,
    TextInputAction? textInputAction,
    ValueChanged<String>? onSubmitted,
  }) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label,
            style: KasiraDS.sans(
                size: 12, weight: FontWeight.w700, color: KasiraDS.textMuted)),
        const SizedBox(height: 6),
        Container(
          decoration: BoxDecoration(
            color: KasiraDS.surfaceSunken,
            borderRadius: KasiraDS.brMd,
            border: Border.all(color: KasiraDS.borderSubtle, width: 1.5),
          ),
          child: TextField(
            controller: controller,
            enabled: !_isSending,
            keyboardType: keyboardType,
            inputFormatters: inputFormatters,
            autofocus: autofocus,
            textInputAction: textInputAction,
            onSubmitted: onSubmitted,
            style: KasiraDS.sans(size: 15, color: KasiraDS.textStrong),
            decoration: InputDecoration(
              hintText: hint,
              hintStyle: KasiraDS.sans(size: 14.5, color: KasiraDS.textMuted),
              prefixIcon: Icon(icon, size: 18, color: KasiraDS.textMuted),
              border: InputBorder.none,
              enabledBorder: InputBorder.none,
              focusedBorder: InputBorder.none,
              disabledBorder: InputBorder.none,
              isDense: true,
              contentPadding: const EdgeInsets.symmetric(vertical: 14),
            ),
          ),
        ),
      ],
    );
  }

  Widget _errorBox(String msg) {
    return Container(
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: KasiraDS.danger.withOpacity(0.10),
        borderRadius: KasiraDS.brSm,
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Icon(LucideIcons.alertCircle, color: KasiraDS.danger, size: 16),
          const SizedBox(width: 8),
          Expanded(
            child: Text(msg,
                style: KasiraDS.sans(size: 12.5, color: KasiraDS.danger, height: 1.3)),
          ),
        ],
      ),
    );
  }

  Widget _actions() {
    return Row(
      children: [
        TextButton(
          onPressed: _isSending ? null : () => Navigator.of(context).pop(),
          style: TextButton.styleFrom(
            foregroundColor: KasiraDS.textMuted,
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
          ),
          child: Text('Batal',
              style: KasiraDS.sans(size: 14.5, weight: FontWeight.w600)),
        ),
        const SizedBox(width: 8),
        Expanded(
          child: SizedBox(
            height: 50,
            child: FilledButton.icon(
              onPressed: _isSending ? null : _submit,
              style: FilledButton.styleFrom(
                backgroundColor: _waGreen,
                disabledBackgroundColor: _waGreen.withOpacity(0.45),
                foregroundColor: Colors.white,
                disabledForegroundColor: Colors.white,
                shape: RoundedRectangleBorder(borderRadius: KasiraDS.brMd),
              ),
              icon: _isSending
                  ? const SizedBox(
                      width: 16,
                      height: 16,
                      child: CircularProgressIndicator(
                          strokeWidth: 2, color: Colors.white),
                    )
                  : const Icon(LucideIcons.send, size: 17),
              label: Text(_isSending ? 'Mengirim...' : 'Kirim Struk',
                  style: KasiraDS.sans(
                      size: 15, weight: FontWeight.w700, color: Colors.white)),
            ),
          ),
        ),
      ],
    );
  }
}
