import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:lucide_icons/lucide_icons.dart';

import '../config/app_config.dart';
import '../services/session_cache.dart';
import '../theme/app_colors.dart';

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

  /// Normalize ke format internasional 62xxx (Fonnte requirement).
  /// 0812... → 62812..., 8121... → 62812..., 62812... → 62812... (no change).
  String _normalize(String input) {
    var p = input.trim().replaceAll(RegExp(r'[\s\-\+]'), '');
    if (p.startsWith('0')) {
      p = '62${p.substring(1)}';
    } else if (p.startsWith('8')) {
      p = '62$p';
    }
    return p;
  }

  bool _isValid(String phone) {
    final p = _normalize(phone);
    return p.startsWith('62') && p.length >= 10 && p.length <= 15 && RegExp(r'^\d+$').hasMatch(p);
  }

  Future<void> _submit() async {
    final phoneRaw = _phoneController.text.trim();
    if (!_isValid(phoneRaw)) {
      setState(() => _error = 'Nomor WA tidak valid (contoh: 081234567890)');
      return;
    }
    setState(() {
      _isSending = true;
      _error = null;
    });

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
          'phone': _normalize(phoneRaw),
          if (widget.paymentId != null) 'payment_id': widget.paymentId,
          if (_nameController.text.trim().isNotEmpty) 'customer_name': _nameController.text.trim(),
        },
      );

      final data = response.data['data'] as Map<String, dynamic>?;
      final sent = data?['sent'] == true;
      final maskedPhone = data?['phone'] as String? ?? '****';

      if (!mounted) return;
      Navigator.of(context).pop();
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            sent
                ? '✅ Struk terkirim ke $maskedPhone'
                : '⚠️ Struk gagal terkirim — cek koneksi WA',
          ),
          backgroundColor: sent ? AppColors.success : AppColors.warning,
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
    return AlertDialog(
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      title: Row(
        children: const [
          Icon(LucideIcons.send, color: AppColors.primary, size: 22),
          SizedBox(width: 10),
          Expanded(child: Text('Kirim Struk via WhatsApp', style: TextStyle(fontSize: 16))),
        ],
      ),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Customer terima struk + tersimpan di database (untuk loyalty & insight).',
            style: TextStyle(fontSize: 12, color: AppColors.textSecondary),
          ),
          const SizedBox(height: 14),
          TextField(
            controller: _phoneController,
            enabled: !_isSending,
            keyboardType: TextInputType.phone,
            inputFormatters: [
              FilteringTextInputFormatter.allow(RegExp(r'[0-9+\-\s]')),
              LengthLimitingTextInputFormatter(16),
            ],
            decoration: const InputDecoration(
              labelText: 'Nomor WhatsApp *',
              hintText: '081234567890',
              prefixIcon: Icon(LucideIcons.phone, size: 18),
              border: OutlineInputBorder(),
              isDense: true,
            ),
            autofocus: true,
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _nameController,
            enabled: !_isSending,
            decoration: const InputDecoration(
              labelText: 'Nama Customer (opsional)',
              hintText: 'Misal: Pak Adit',
              prefixIcon: Icon(LucideIcons.user, size: 18),
              border: OutlineInputBorder(),
              isDense: true,
            ),
          ),
          if (_error != null) ...[
            const SizedBox(height: 10),
            Container(
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(
                color: AppColors.error.withOpacity(0.1),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Row(
                children: [
                  const Icon(LucideIcons.alertCircle, color: AppColors.error, size: 16),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(_error!, style: const TextStyle(color: AppColors.error, fontSize: 12)),
                  ),
                ],
              ),
            ),
          ],
        ],
      ),
      actions: [
        TextButton(
          onPressed: _isSending ? null : () => Navigator.of(context).pop(),
          child: const Text('Batal', style: TextStyle(color: AppColors.textSecondary)),
        ),
        ElevatedButton.icon(
          onPressed: _isSending ? null : _submit,
          icon: _isSending
              ? const SizedBox(
                  width: 14,
                  height: 14,
                  child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                )
              : const Icon(LucideIcons.send, size: 16),
          label: Text(_isSending ? 'Mengirim…' : 'Kirim'),
          style: ElevatedButton.styleFrom(
            backgroundColor: AppColors.primary,
            foregroundColor: Colors.white,
          ),
        ),
      ],
    );
  }
}
