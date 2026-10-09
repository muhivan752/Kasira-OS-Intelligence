import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../../core/auth/logout_service.dart';
import '../../../../core/config/app_config.dart';
import '../../../../core/services/session_cache.dart';
import '../../../../core/widgets/lebar_konten.dart';

/// Hapus akun (syarat Play Store). Dipakai app Kasir dan Dapur.
///
/// Aturan pemilik vs karyawan dan masa tenggang 30 hari diputuskan backend
/// (`backend/services/account_deletion.py`); layar ini cuma menampilkan
/// status dari `GET /account-deletion`. Warna dari Theme supaya cocok di
/// app Kasir (terang) dan Dapur (gelap).
class AccountDeletionPage extends ConsumerStatefulWidget {
  const AccountDeletionPage({super.key, this.client});
  final Dio? client;

  @override
  ConsumerState<AccountDeletionPage> createState() => _AccountDeletionPageState();
}

class _AccountDeletionPageState extends ConsumerState<AccountDeletionPage> {
  late final Dio _dio = widget.client ??
      Dio(BaseOptions(
          baseUrl: AppConfig.apiV1,
          connectTimeout: const Duration(seconds: 10),
          receiveTimeout: const Duration(seconds: 20)));
  final _word = TextEditingController();
  Map<String, dynamic>? _status;
  String? _error;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _word.dispose();
    super.dispose();
  }

  Options get _auth => Options(headers: SessionCache.instance.authHeaders);

  String _message(Object error) {
    if (error is DioException) {
      final detail = error.response?.data is Map ? error.response?.data['detail'] : null;
      if (detail is String) return detail;
      if (error.response == null) return 'Tidak ada koneksi. Periksa internet lalu coba lagi.';
    }
    return 'Permintaan gagal. Coba lagi.';
  }

  Future<void> _load() async {
    setState(() => _error = null);
    try {
      final res = await _dio.get('/account-deletion', options: _auth);
      if (mounted) setState(() => _status = Map<String, dynamic>.from(res.data['data']));
    } catch (e) {
      if (mounted) setState(() => _error = _message(e));
    }
  }

  Future<void> _request() async {
    if (_busy) return;
    setState(() { _busy = true; _error = null; });
    try {
      final res = await _dio.post('/account-deletion',
          data: {'confirm': _word.text.trim()}, options: _auth);
      final data = Map<String, dynamic>.from(res.data['data']);
      if (data['deleted'] == true) {
        // Server sudah mencabut semua sesi; logout lokal membersihkan sisanya.
        try { await performLogout(ref); } catch (_) {}
        if (mounted) context.go('/login');
        return;
      }
      _word.clear();
      await _load();
    } catch (e) {
      if (mounted) setState(() => _error = _message(e));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _cancel() async {
    if (_busy) return;
    setState(() { _busy = true; _error = null; });
    try {
      await _dio.delete('/account-deletion', options: _auth);
      await _load();
    } catch (e) {
      if (mounted) setState(() => _error = _message(e));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  String _date(String iso) {
    const bulan = ['Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni', 'Juli',
      'Agustus', 'September', 'Oktober', 'November', 'Desember'];
    final d = DateTime.parse(iso).toLocal();
    return '${d.day} ${bulan[d.month - 1]} ${d.year}';
  }

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final status = _status;
    final business = status?['scope'] == 'business';
    final word = (status?['confirm_word'] ?? 'HAPUS') as String;
    return Scaffold(
      appBar: AppBar(title: const Text('Hapus akun')),
      body: LebarKonten(
        child: status == null
            ? Center(
                child: _error == null
                    ? const CircularProgressIndicator()
                    : Padding(
                        padding: const EdgeInsets.all(24),
                        child: Column(mainAxisSize: MainAxisSize.min, children: [
                          Text(_error!, textAlign: TextAlign.center),
                          const SizedBox(height: 16),
                          OutlinedButton(onPressed: _load, child: const Text('Coba lagi')),
                        ])))
            : ListView(padding: const EdgeInsets.all(24), children: [
                if (status['scheduled_at'] != null) ...[
                  Text(
                      'Usaha ${status['business_name']} dijadwalkan dihapus pada '
                      '${_date(status['scheduled_at'])}. Sampai tanggal itu Selaris '
                      'tetap berjalan normal.',
                      style: Theme.of(context).textTheme.bodyLarge),
                  const SizedBox(height: 24),
                  if (status['can_cancel'] == true)
                    SizedBox(
                      height: 48,
                      child: OutlinedButton(
                          onPressed: _busy ? null : _cancel,
                          child: const Text('Batalkan penghapusan')),
                    ),
                ] else ...[
                  Text(
                      business
                          ? 'Menghapus akun pemilik akan menghapus seluruh data usaha '
                              '${status['business_name']}: outlet, menu, stok, transaksi, '
                              'pelanggan, karyawan, dan akun kasir. Penghapusan dijalankan '
                              '${status['grace_days']} hari setelah permintaan dan dapat '
                              'dibatalkan selama masa itu.'
                          : 'Akun login Anda akan dihapus sekarang dan Anda keluar dari '
                              'semua perangkat. Transaksi yang pernah Anda catat tetap '
                              'tersimpan di usaha tempat Anda bekerja.',
                      style: Theme.of(context).textTheme.bodyLarge),
                  const SizedBox(height: 24),
                  TextField(
                    controller: _word,
                    textCapitalization: TextCapitalization.characters,
                    autocorrect: false,
                    decoration: InputDecoration(
                        labelText: 'Ketik $word untuk mengonfirmasi',
                        border: const OutlineInputBorder()),
                    onChanged: (_) => setState(() {}),
                  ),
                  const SizedBox(height: 16),
                  SizedBox(
                    height: 48,
                    child: FilledButton(
                      style: FilledButton.styleFrom(
                          backgroundColor: scheme.error, foregroundColor: scheme.onError),
                      onPressed: _busy || _word.text.trim().toUpperCase() != word ? null : _request,
                      child: Text(business ? 'Jadwalkan penghapusan' : 'Hapus akun saya'),
                    ),
                  ),
                ],
                if (_error != null) ...[
                  const SizedBox(height: 16),
                  Text(_error!, style: TextStyle(color: scheme.error)),
                ],
              ]),
      ),
    );
  }
}
