import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../../core/config/app_config.dart';
import '../../../../core/services/google_auth_service.dart';
import '../../../../core/theme/kasira_ds.dart';
import '../../../../core/widgets/sefrekuensi_otp_card.dart';
import 'login_page.dart';

class GoogleConnectPage extends ConsumerStatefulWidget {
  const GoogleConnectPage({super.key});

  @override
  ConsumerState<GoogleConnectPage> createState() => _GoogleConnectPageState();
}

class _GoogleConnectPageState extends ConsumerState<GoogleConnectPage> {
  final _phone = TextEditingController();
  final _otp = TextEditingController();
  final _dio = Dio(BaseOptions(
      baseUrl: AppConfig.apiV1,
      connectTimeout: const Duration(seconds: 15),
      receiveTimeout: const Duration(seconds: 15)));
  String? _token;
  String? _error;
  String _email = '';
  String _channel = 'sefrekuensi';
  String _verifiedPhone = '';
  bool _sent = false;
  bool _busy = false;
  bool _notFound = false;
  DateTime? _resendAt;

  String get _normalizedPhone {
    var digits = _phone.text.replaceAll(RegExp(r'\D'), '');
    if (digits.startsWith('0')) digits = '62${digits.substring(1)}';
    if (digits.startsWith('8')) digits = '62$digits';
    return digits;
  }

  Future<void> _run(Future<void> Function() action) async {
    if (_busy) return;
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await action();
    } on GoogleAuthFailure catch (error) {
      if (mounted) setState(() => _error = error.message);
    } on DioException catch (error) {
      final detail =
          error.response?.data is Map ? error.response?.data['detail'] : null;
      if (mounted)
        setState(() {
          _notFound = otpErrorCode(detail) == kSefrekuensiNotFoundCode;
          _error = _notFound
              ? null
              : otpErrorMessage(detail, 'Belum dapat terhubung. Coba lagi.');
        });
    } catch (_) {
      if (mounted)
        setState(() => _error =
            'Belum dapat masuk. Coba lagi atau gunakan kode Sefrekuensi.');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _google() async {
    final notifier = ref.read(authProvider.notifier);
    final token = await GoogleAuthService.idToken();
    if (token == null) return;
    final response = await _dio.post('/auth/google', data: {'id_token': token});
    final data = Map<String, dynamic>.from(response.data['data']);
    if (data['registered'] == true) {
      await notifier.acceptGoogleSession(data);
      if (mounted) context.go('/login');
    } else if (mounted) {
      setState(() {
        _token = token;
        _email = data['email'] ?? '';
      });
    }
  }

  Future<void> _send({String channel = 'sefrekuensi'}) async {
    final phone = _normalizedPhone;
    if (!RegExp(r'^628\d{7,12}$').hasMatch(phone)) {
      setState(() => _error = 'Masukkan nomor HP Indonesia yang aktif.');
      return;
    }
    if (_resendAt != null && DateTime.now().isBefore(_resendAt!)) {
      setState(() => _error = 'Tunggu satu menit sebelum mengirim ulang kode.');
      return;
    }
    await _dio.post('/auth/otp/send', data: {
      'phone': phone,
      'purpose': 'google',
      'id_token': _token,
      'channel': channel
    });
    if (mounted)
      setState(() {
        _verifiedPhone = phone;
        _channel = channel;
        _sent = true;
        _notFound = false;
        _resendAt = DateTime.now().add(const Duration(minutes: 1));
        _otp.clear();
      });
  }

  Future<void> _verify() async {
    if (_otp.text.length != 6) {
      setState(() => _error = 'Masukkan kode 6 angka.');
      return;
    }
    final notifier = ref.read(authProvider.notifier);
    final response = await _dio.post('/auth/google/phone', data: {
      'id_token': _token,
      'phone': _verifiedPhone,
      'otp': _otp.text,
    });
    final data = Map<String, dynamic>.from(response.data['data']);
    if (data['registered'] == true) {
      await notifier.acceptGoogleSession(data);
      if (mounted) context.go('/login');
    } else if (mounted) {
      context.go('/register', extra: {
        'phone': _verifiedPhone,
        'owner_name': data['name'],
        'google_proof': data['google_proof']
      });
    }
  }

  @override
  void dispose() {
    _phone.dispose();
    _otp.dispose();
    _dio.close();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        backgroundColor: KasiraDS.bgBase,
        appBar: AppBar(
            title: const Text('Akun Selaris'),
            leading: IconButton(
                tooltip: 'Kembali ke login',
                icon: const Icon(Icons.arrow_back),
                onPressed: _busy ? null : () => context.go('/login'))),
        body: SafeArea(
            child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: Center(
              child: ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 440),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      Text(
                          _token == null
                              ? 'Lanjut dengan Google'
                              : _sent
                                  ? 'Masukkan kode masuk'
                                  : 'Hubungkan nomor usaha',
                          style: KasiraDS.display(
                              size: 26, color: KasiraDS.textStrong)),
                      const SizedBox(height: 12),
                      Text(
                          _token == null
                              ? 'Pilih akun Google yang akan dipakai untuk mengelola usaha.'
                              : _sent
                                  ? 'Kode dikirim ke ${_channel == 'sefrekuensi' ? 'Sefrekuensi' : 'WhatsApp'} +$_verifiedPhone.'
                                  : '$_email\nVerifikasi nomor sekali untuk menghubungkan akun dan toko Anda.',
                          style: KasiraDS.sans(
                              size: 15, color: KasiraDS.textBody, height: 1.5)),
                      const SizedBox(height: 24),
                      if (_error != null) ...[
                        Semantics(
                            liveRegion: true,
                            child: Text(_error!,
                                style: KasiraDS.sans(
                                    size: 14, color: KasiraDS.danger))),
                        const SizedBox(height: 16),
                      ],
                      if (_token != null)
                        TextField(
                          controller: _sent ? _otp : _phone,
                          enabled: !_busy,
                          keyboardType: _sent
                              ? TextInputType.number
                              : TextInputType.phone,
                          autofillHints: _sent
                              ? const [AutofillHints.oneTimeCode]
                              : const [AutofillHints.telephoneNumberNational],
                          inputFormatters: [
                            FilteringTextInputFormatter.digitsOnly
                          ],
                          maxLength: _sent ? 6 : 15,
                          decoration: InputDecoration(
                              labelText: _sent ? 'Kode 6 angka' : 'Nomor HP',
                              hintText: _sent ? null : '081234567890'),
                        ),
                      const SizedBox(height: 16),
                      FilledButton(
                          onPressed: _busy
                              ? null
                              : () => _run(_token == null
                                  ? _google
                                  : _sent
                                      ? _verify
                                      : _send),
                          child: _busy
                              ? const SizedBox(
                                  width: 20,
                                  height: 20,
                                  child:
                                      CircularProgressIndicator(strokeWidth: 2))
                              : Text(_token == null
                                  ? 'Pilih akun Google'
                                  : _sent
                                      ? 'Verifikasi dan lanjut'
                                      : 'Kirim kode ke Sefrekuensi')),
                      if (_notFound)
                        SefrekuensiOtpCard(
                            loading: _busy,
                            notFound: true,
                            onPick: () => _run(_send),
                            onFallbackWhatsapp: () =>
                                _run(() => _send(channel: 'whatsapp'))),
                      if (_sent) ...[
                        TextButton(
                            onPressed: _busy
                                ? null
                                : () => _run(() => _send(channel: _channel)),
                            child: const Text('Kirim ulang kode')),
                        TextButton(
                            onPressed: _busy
                                ? null
                                : () => setState(() {
                                      _sent = false;
                                      _error = null;
                                    }),
                            child: const Text('Ubah nomor HP')),
                      ],
                    ],
                  ))),
        )),
      );
}
