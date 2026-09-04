import 'package:cached_network_image/cached_network_image.dart';
import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';

import '../../../../core/config/app_config.dart';
import '../../../../core/services/session_cache.dart';
import '../../../../core/theme/kasira_ds.dart';

/// Pengaturan metode bayar dari HP (mig 103). Sumber kebenaran tetap server
/// (`PUT /outlets/{id}`), halaman ini dan Pengaturan web ngubah data yang
/// sama. Sesudah simpan, `SessionCache.applyPaymentConfig` dipanggil supaya
/// modal bayar langsung ikut tanpa harus buka ulang app.
///
/// Tunai nggak bisa dimatikan. QRIS punya dua saluran: kalau toko punya kunci
/// Xendit (diatur di web) QR-nya dinamis, kalau nggak pemilik unggah gambar
/// QRIS statis miliknya di sini dan kasir konfirmasi sendiri.
class PaymentMethodsSettingsPage extends StatefulWidget {
  const PaymentMethodsSettingsPage({super.key});

  @override
  State<PaymentMethodsSettingsPage> createState() => _PaymentMethodsSettingsPageState();
}

class _PaymentMethodsSettingsPageState extends State<PaymentMethodsSettingsPage> {
  SessionCache get _cache => SessionCache.instance;

  late List<String> _methods;
  late final TextEditingController _bankName;
  late final TextEditingController _bankNumber;
  late final TextEditingController _bankHolder;
  bool _saving = false;
  bool _uploading = false;
  String? _msg;
  bool _msgOk = true;

  Dio get _dio => Dio(BaseOptions(
        baseUrl: AppConfig.apiV1,
        connectTimeout: const Duration(seconds: 15),
        receiveTimeout: const Duration(seconds: 30),
      ));

  @override
  void initState() {
    super.initState();
    _methods = List.of(_cache.paymentMethods);
    _bankName = TextEditingController(text: _cache.bankName ?? '');
    _bankNumber = TextEditingController(text: _cache.bankAccountNumber ?? '');
    _bankHolder = TextEditingController(text: _cache.bankAccountName ?? '');
    // Ambil versi terbaru dari server: pemilik bisa saja baru mengubah di web.
    _cache.fetchAndCacheOutletInfo().then((_) {
      if (!mounted) return;
      setState(() {
        _methods = List.of(_cache.paymentMethods);
        if (_bankName.text.isEmpty) _bankName.text = _cache.bankName ?? '';
        if (_bankNumber.text.isEmpty) _bankNumber.text = _cache.bankAccountNumber ?? '';
        if (_bankHolder.text.isEmpty) _bankHolder.text = _cache.bankAccountName ?? '';
      });
    });
  }

  @override
  void dispose() {
    _bankName.dispose();
    _bankNumber.dispose();
    _bankHolder.dispose();
    super.dispose();
  }

  Future<bool> _save(Map<String, dynamic> patch, {String ok = 'Tersimpan.'}) async {
    final outletId = _cache.outletId;
    if (outletId == null) return false;
    setState(() {
      _saving = true;
      _msg = null;
    });
    try {
      final res = await _dio.put('/outlets/$outletId', data: patch, options: Options(headers: _cache.authHeaders));
      final data = res.data['data'] as Map<String, dynamic>?;
      if (data != null) await _cache.applyPaymentConfig(data);
      if (mounted) {
        setState(() {
          _methods = List.of(_cache.paymentMethods);
          _msg = ok;
          _msgOk = true;
        });
      }
      return true;
    } on DioException catch (e) {
      final detail = e.response?.data?['detail'];
      if (mounted) {
        setState(() {
          _msg = detail is Map ? (detail['message']?.toString() ?? 'Gagal menyimpan') : (detail?.toString() ?? 'Gagal menyimpan. Periksa koneksi.');
          _msgOk = false;
        });
      }
      return false;
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  Future<void> _toggle(String method, bool on) async {
    final prev = List.of(_methods);
    final next = <String>{..._methods};
    if (on) {
      next.add(method);
    } else {
      next.remove(method);
    }
    next.add('cash');
    const order = ['cash', 'qris', 'transfer', 'card'];
    setState(() => _methods = order.where(next.contains).toList());
    final ok = await _save({'payment_methods': _methods});
    if (!ok && mounted) setState(() => _methods = prev);
  }

  Future<void> _pickQris() async {
    final picker = ImagePicker();
    final file = await picker.pickImage(source: ImageSource.gallery, maxWidth: 1200, imageQuality: 90);
    if (file == null) return;
    setState(() {
      _uploading = true;
      _msg = null;
    });
    try {
      final form = FormData.fromMap({
        'file': await MultipartFile.fromFile(file.path, filename: file.name),
      });
      final res = await _dio.post('/media/upload', data: form, options: Options(headers: _cache.authHeaders));
      final rel = res.data?['url']?.toString();
      if (rel == null || rel.isEmpty) throw Exception('URL kosong');
      final url = rel.startsWith('http') ? rel : '${AppConfig.baseUrl}$rel';
      await _save({'qris_static_image_url': url}, ok: 'Gambar QRIS tersimpan. Kasir menampilkannya saat pelanggan memilih QRIS.');
    } catch (_) {
      if (mounted) {
        setState(() {
          _msg = 'Unggah gagal. Coba gambar lain atau periksa koneksi.';
          _msgOk = false;
        });
      }
    } finally {
      if (mounted) setState(() => _uploading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final qrisOn = _methods.contains('qris');
    final transferOn = _methods.contains('transfer');
    final qrisUrl = _cache.qrisStaticImageUrl;
    return Scaffold(
      backgroundColor: KasiraDS.bgBase,
      appBar: AppBar(
        backgroundColor: KasiraDS.surfaceCard,
        foregroundColor: KasiraDS.textStrong,
        elevation: 0,
        title: Text('Metode pembayaran', style: KasiraDS.display(size: 18, color: KasiraDS.textStrong)),
      ),
      body: ListView(
        padding: const EdgeInsets.all(KasiraDS.space4),
        children: [
          Text(
            'Kasir hanya melihat metode yang dinyalakan di sini. Tunai selalu aktif.',
            style: KasiraDS.sans(size: 13.5, color: KasiraDS.textMuted, height: 1.5),
          ),
          if (_msg != null) ...[
            const SizedBox(height: KasiraDS.space3),
            Text(_msg!, style: KasiraDS.sans(size: 13, weight: FontWeight.w600, color: _msgOk ? KasiraDS.success : KasiraDS.danger)),
          ],
          const SizedBox(height: KasiraDS.space4),
          _methodTile(
            icon: LucideIcons.banknote,
            title: 'Tunai',
            subtitle: 'Selalu aktif. Kembalian dihitung otomatis.',
            value: true,
            onChanged: null,
          ),
          _methodTile(
            icon: LucideIcons.qrCode,
            title: 'QRIS',
            subtitle: 'GoPay, OVO, DANA, ShopeePay, dan semua m-banking.',
            value: qrisOn,
            onChanged: _saving ? null : (v) => _toggle('qris', v),
          ),
          if (qrisOn) _qrisCard(qrisUrl),
          _methodTile(
            icon: LucideIcons.landmark,
            title: 'Transfer bank',
            subtitle: 'Pesanan besar, katering, atau bayar di muka.',
            value: transferOn,
            onChanged: _saving ? null : (v) => _toggle('transfer', v),
          ),
          if (transferOn) _bankCard(),
          _methodTile(
            icon: LucideIcons.creditCard,
            title: 'Kartu EDC',
            subtitle: 'Debit atau kredit lewat mesin EDC bank Anda.',
            value: _methods.contains('card'),
            onChanged: _saving ? null : (v) => _toggle('card', v),
          ),
        ],
      ),
    );
  }

  Widget _methodTile({
    required IconData icon,
    required String title,
    required String subtitle,
    required bool value,
    required ValueChanged<bool>? onChanged,
  }) {
    return Container(
      margin: const EdgeInsets.only(bottom: KasiraDS.space2),
      padding: const EdgeInsets.symmetric(horizontal: KasiraDS.space3, vertical: KasiraDS.space2),
      decoration: BoxDecoration(
        color: KasiraDS.surfaceCard,
        borderRadius: KasiraDS.brMd,
        border: Border.all(color: KasiraDS.borderSubtle),
      ),
      child: Row(
        children: [
          Container(
            width: 38,
            height: 38,
            alignment: Alignment.center,
            decoration: BoxDecoration(color: KasiraDS.surfaceSunken, borderRadius: KasiraDS.brSm),
            child: Icon(icon, size: 19, color: KasiraDS.textMuted),
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
          Switch(value: value, onChanged: onChanged, activeColor: KasiraDS.brandPrimary),
        ],
      ),
    );
  }

  Widget _subCard({required List<Widget> children}) {
    return Container(
      margin: const EdgeInsets.only(bottom: KasiraDS.space3, left: KasiraDS.space3),
      padding: const EdgeInsets.all(KasiraDS.space3),
      decoration: BoxDecoration(
        color: KasiraDS.surfaceSunken,
        borderRadius: KasiraDS.brMd,
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: children),
    );
  }

  Widget _qrisCard(String? url) {
    if (!_cache.qrisIsManual) {
      return _subCard(children: [
        Text('QRIS dinamis lewat Xendit', style: KasiraDS.sans(size: 13.5, weight: FontWeight.w700, color: KasiraDS.textStrong)),
        const SizedBox(height: 4),
        Text(
          'Tiap transaksi membuat kode QR dengan nominalnya sendiri dan lunas terkonfirmasi otomatis. Kunci Xendit diatur dari Dashboard web.',
          style: KasiraDS.sans(size: 12.5, color: KasiraDS.textMuted, height: 1.45),
        ),
      ]);
    }
    final hasImg = url != null && url.isNotEmpty;
    return _subCard(children: [
      Text('Gambar QRIS toko', style: KasiraDS.sans(size: 13.5, weight: FontWeight.w700, color: KasiraDS.textStrong)),
      const SizedBox(height: 4),
      Text(
        'Unduh QRIS dari aplikasi bank, GoPay, atau DANA merchant Anda, lalu unggah di sini. Kasir menampilkannya ke pelanggan dan menekan Konfirmasi setelah notifikasi uang masuk.',
        style: KasiraDS.sans(size: 12.5, color: KasiraDS.textMuted, height: 1.45),
      ),
      const SizedBox(height: KasiraDS.space3),
      Row(
        children: [
          ClipRRect(
            borderRadius: KasiraDS.brSm,
            child: Container(
              width: 96,
              height: 96,
              color: Colors.white,
              child: hasImg
                  ? CachedNetworkImage(
                      imageUrl: url,
                      fit: BoxFit.contain,
                      errorWidget: (_, __, ___) => const Icon(LucideIcons.imageOff, color: KasiraDS.textMuted),
                    )
                  : const Icon(LucideIcons.qrCode, size: 34, color: KasiraDS.textMuted),
            ),
          ),
          const SizedBox(width: KasiraDS.space3),
          Expanded(
            child: FilledButton.icon(
              onPressed: _uploading || _saving ? null : _pickQris,
              style: FilledButton.styleFrom(
                backgroundColor: KasiraDS.brandPrimary,
                shape: RoundedRectangleBorder(borderRadius: KasiraDS.brPill),
              ),
              icon: _uploading
                  ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                  : const Icon(LucideIcons.upload, size: 16),
              label: Text(hasImg ? 'Ganti gambar' : 'Unggah dari galeri',
                  style: KasiraDS.sans(size: 13.5, weight: FontWeight.w700, color: KasiraDS.textOnBrand)),
            ),
          ),
        ],
      ),
    ]);
  }

  Widget _bankCard() {
    InputDecoration deco(String hint) => InputDecoration(
          hintText: hint,
          isDense: true,
          filled: true,
          fillColor: KasiraDS.surfaceCard,
          contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
          border: OutlineInputBorder(borderRadius: KasiraDS.brSm, borderSide: const BorderSide(color: KasiraDS.borderSubtle)),
          enabledBorder: OutlineInputBorder(borderRadius: KasiraDS.brSm, borderSide: const BorderSide(color: KasiraDS.borderSubtle)),
        );
    return _subCard(children: [
      Text('Rekening tujuan transfer', style: KasiraDS.sans(size: 13.5, weight: FontWeight.w700, color: KasiraDS.textStrong)),
      const SizedBox(height: 4),
      Text('Ditampilkan kasir ke pelanggan saat memilih transfer.', style: KasiraDS.sans(size: 12.5, color: KasiraDS.textMuted)),
      const SizedBox(height: KasiraDS.space3),
      TextField(controller: _bankName, decoration: deco('Nama bank (BCA, BRI, Mandiri)'), style: KasiraDS.sans(size: 14, color: KasiraDS.textStrong)),
      const SizedBox(height: KasiraDS.space2),
      TextField(controller: _bankNumber, keyboardType: TextInputType.number, decoration: deco('Nomor rekening'), style: KasiraDS.sans(size: 14, color: KasiraDS.textStrong)),
      const SizedBox(height: KasiraDS.space2),
      TextField(controller: _bankHolder, decoration: deco('Atas nama'), style: KasiraDS.sans(size: 14, color: KasiraDS.textStrong)),
      const SizedBox(height: KasiraDS.space3),
      SizedBox(
        width: double.infinity,
        child: FilledButton(
          onPressed: _saving
              ? null
              : () => _save({
                    'bank_name': _bankName.text.trim(),
                    'bank_account_number': _bankNumber.text.trim(),
                    'bank_account_name': _bankHolder.text.trim(),
                  }, ok: 'Rekening tersimpan.'),
          style: FilledButton.styleFrom(
            backgroundColor: KasiraDS.brandPrimary,
            shape: RoundedRectangleBorder(borderRadius: KasiraDS.brPill),
          ),
          child: Text('Simpan rekening', style: KasiraDS.sans(size: 14, weight: FontWeight.w700, color: KasiraDS.textOnBrand)),
        ),
      ),
    ]);
  }
}
