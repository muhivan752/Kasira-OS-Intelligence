import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:uuid/uuid.dart';
import '../../../../core/config/app_config.dart';
import '../../../../core/theme/kasira_ds.dart';
import '../../../../core/widgets/sefrekuensi_otp_card.dart';
import 'login_page.dart';

class PasswordAccountPage extends ConsumerStatefulWidget {
  const PasswordAccountPage({super.key, this.register = false});
  final bool register;
  @override
  ConsumerState<PasswordAccountPage> createState() =>
      _PasswordAccountPageState();
}

class _PasswordAccountPageState extends ConsumerState<PasswordAccountPage> {
  final _form = GlobalKey<FormState>();
  final _fields = {
    for (final key in [
      'shop',
      'username',
      'owner',
      'business',
      'code',
      'password',
      'confirm'
    ])
      key: TextEditingController()
  };
  String _purpose = 'activation', _businessType = 'cafe';
  String? _error, _recovery, _requestId, _requestValue;
  bool _busy = false, _saved = false;
  @override
  void dispose() {
    for (final field in _fields.values) {
      field.dispose();
    }
    super.dispose();
  }

  Future<void> _submit() async {
    if (_busy || !_form.currentState!.validate()) return;
    final body = <String, dynamic>{
      'shop_username': _fields['shop']!.text.trim(),
      'username': widget.register ? 'owner' : _fields['username']!.text.trim(),
      'password': _fields['password']!.text
    };
    if (widget.register) {
      body.addAll({
        'owner_name': _fields['owner']!.text.trim(),
        'business_name': _fields['business']!.text.trim(),
        'business_type': _businessType
      });
    } else {
      body.addAll({'code': _fields['code']!.text.trim(), 'purpose': _purpose});
    }
    final value = body.toString();
    if (_requestValue != value) {
      _requestValue = value;
      _requestId = const Uuid().v4();
    }
    body['client_request_id'] = _requestId;
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final response = await Dio(BaseOptions(
              baseUrl: AppConfig.apiV1,
              connectTimeout: const Duration(seconds: 10),
              receiveTimeout: const Duration(seconds: 20)))
          .post(
              widget.register
                  ? '/auth/password/register'
                  : '/auth/password/challenge',
              data: body);
      final data = Map<String, dynamic>.from(response.data['data'] as Map);
      await ref.read(authProvider.notifier).acceptGoogleSession(data);
      if (!mounted) return;
      if (data['recovery_code'] != null) {
        setState(() => _recovery = data['recovery_code'].toString());
      } else {
        context.go('/login');
      }
    } on DioException catch (error) {
      if (mounted) {
        setState(() => _error = otpErrorMessage(error.response?.data?['detail'],
            'Hasil permintaan belum pasti. Coba lagi dengan data yang sama.'));
      }
    } catch (_) {
      if (mounted) {
        setState(() => _error = 'Akun belum dapat disimpan. Coba lagi.');
      }
    } finally {
      if (mounted) {
        setState(() => _busy = false);
      }
    }
  }

  Widget _field(String key, String label,
          {bool password = false, int minimum = 1}) =>
      Padding(
          padding: const EdgeInsets.only(bottom: 16),
          child: TextFormField(
              controller: _fields[key],
              enabled: !_busy,
              obscureText: password,
              autocorrect:
                  !password && !['shop', 'username', 'code'].contains(key),
              decoration: InputDecoration(labelText: label),
              textInputAction: TextInputAction.next,
              validator: (value) {
                if ((value ?? '').length < minimum)
                  return 'Isi sedikitnya $minimum karakter';
                if (key == 'confirm' && value != _fields['password']!.text)
                  return 'Konfirmasi password belum cocok';
                return null;
              }));

  @override
  Widget build(BuildContext context) => Scaffold(
      backgroundColor: KasiraDS.bgBase,
      appBar: AppBar(
          title: Text(
              widget.register ? 'Daftarkan usaha' : 'Aktivasi dan pemulihan'),
          leading: IconButton(
              tooltip: 'Kembali',
              icon: const Icon(Icons.arrow_back),
              onPressed: _busy || (_recovery != null && !_saved)
                  ? null
                  : () => context.go('/login'))),
      body: Center(
          child: SingleChildScrollView(
              padding: const EdgeInsets.all(24),
              child: ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 480),
                  child: Form(
                      key: _form,
                      child: Column(
                          crossAxisAlignment: CrossAxisAlignment.stretch,
                          children: [
                            if (_error != null)
                              Padding(
                                  padding: const EdgeInsets.only(bottom: 16),
                                  child: Text(_error!,
                                      style:
                                          TextStyle(color: KasiraDS.danger))),
                            if (_recovery != null) ...[
                              Text('Simpan kode pemulihan',
                                  style: KasiraDS.display(
                                      size: 24, color: KasiraDS.textStrong)),
                              const SizedBox(height: 12),
                              const Text(
                                  'Kode dipakai sekali saat Anda kehilangan password. Simpan di tempat pribadi.'),
                              const SizedBox(height: 16),
                              SelectableText(_recovery!),
                              CheckboxListTile(
                                  contentPadding: EdgeInsets.zero,
                                  title: const Text(
                                      'Saya sudah menyimpan kode ini'),
                                  value: _saved,
                                  onChanged: (value) =>
                                      setState(() => _saved = value ?? false)),
                              FilledButton(
                                  onPressed: _saved
                                      ? () => context.go('/login')
                                      : null,
                                  child: const Text('Lanjut ke akun')),
                            ] else ...[
                              const Text(
                                  'Gunakan akun yang sama di web dan aplikasi Selaris.'),
                              const SizedBox(height: 20),
                              _field('shop', 'Username toko', minimum: 3),
                              if (widget.register) ...[
                                _field('owner', 'Nama pemilik', minimum: 2),
                                _field('business', 'Nama usaha', minimum: 2),
                                DropdownButtonFormField<String>(
                                    isExpanded: true,
                                    initialValue: _businessType,
                                    decoration: const InputDecoration(
                                        labelText: 'Jenis usaha'),
                                    items: const [
                                      DropdownMenuItem(
                                          value: 'cafe', child: Text('Kafe')),
                                      DropdownMenuItem(
                                          value: 'warung',
                                          child: Text('Warung')),
                                      DropdownMenuItem(
                                          value: 'resto',
                                          child: Text('Restoran')),
                                      DropdownMenuItem(
                                          value: 'other',
                                          child: Text('Usaha lain'))
                                    ],
                                    onChanged: _busy
                                        ? null
                                        : (value) => setState(() =>
                                            _businessType = value ?? 'cafe')),
                                const SizedBox(height: 16),
                              ] else ...[
                                _field('username', 'Username akun', minimum: 3),
                                DropdownButtonFormField<String>(
                                    isExpanded: true,
                                    initialValue: _purpose,
                                    decoration: const InputDecoration(
                                        labelText: 'Jenis kode'),
                                    items: const [
                                      DropdownMenuItem(
                                          value: 'activation',
                                          child: Text('Aktivasi dari pemilik')),
                                      DropdownMenuItem(
                                          value: 'recovery',
                                          child: Text('Kode pemulihan pemilik'))
                                    ],
                                    onChanged: _busy
                                        ? null
                                        : (value) => setState(() =>
                                            _purpose = value ?? 'activation')),
                                const SizedBox(height: 16),
                                _field('code', 'Kode Anda', minimum: 32)
                              ],
                              _field('password', 'Password baru',
                                  password: true, minimum: 12),
                              _field('confirm', 'Ulangi password',
                                  password: true, minimum: 12),
                              FilledButton(
                                  onPressed: _busy ? null : _submit,
                                  child: Text(_busy
                                      ? 'Memproses…'
                                      : widget.register
                                          ? 'Buat usaha'
                                          : 'Simpan password')),
                            ],
                          ]))))));
}
