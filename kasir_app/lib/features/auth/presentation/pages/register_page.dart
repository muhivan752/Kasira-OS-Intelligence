import 'dart:async';
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:dio/dio.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:go_router/go_router.dart';
import '../../../../core/config/app_config.dart';
import '../../../../core/services/session_cache.dart';
import '../../../../core/theme/kasira_ds.dart';
import '../../../../core/widgets/selaris_mark.dart';

enum RegStep { inputInfo, inputOtp, setPin }

class RegisterPage extends StatefulWidget {
  const RegisterPage({super.key});

  @override
  State<RegisterPage> createState() => _RegisterPageState();
}

class _RegisterPageState extends State<RegisterPage> {
  RegStep _step = RegStep.inputInfo;
  bool _isLoading = false;
  String? _error;
  Timer? _timer;
  int _countdown = 0;

  final _phoneCtrl = TextEditingController();
  final _nameCtrl = TextEditingController();
  final _businessCtrl = TextEditingController();
  final _otpCtrl = TextEditingController();
  final _pinCtrl = TextEditingController();
  final _pinConfirmCtrl = TextEditingController();
  String _businessType = 'cafe';
  String _referralCode = '';

  // ── Domain auto-detect (Batch #26) ─────────────────────────────────────
  // Debounced classify on business_name input. Suggestion card hanya muncul
  // kalau domain non-F&B + confidence >=0.5 (backend tentuin via
  // `suggest_ui_switch` flag). User accept → _userAcceptedDomain=true →
  // persist ke SessionCache SETELAH register success (bukan sebelum).
  Timer? _classifyDebounce;
  CancelToken? _classifyCancelToken;
  String? _detectedDomain;       // 'fnb' | 'retail' | 'service'
  String? _detectedDisplayName;  // e.g. "Salon/Barber", "Laundry"
  bool _showDomainSuggestion = false;
  bool? _userAcceptedDomain;     // null = belum interaksi, true/false = pilihan user

  final _cache = SessionCache.instance;
  Dio get _dio => Dio(BaseOptions(
    baseUrl: AppConfig.baseUrl,
    connectTimeout: const Duration(seconds: 15),
    receiveTimeout: const Duration(seconds: 15),
  ));

  @override
  void dispose() {
    _timer?.cancel();
    _classifyDebounce?.cancel();
    _classifyCancelToken?.cancel('dispose');
    _phoneCtrl.dispose();
    _nameCtrl.dispose();
    _businessCtrl.dispose();
    _otpCtrl.dispose();
    _pinCtrl.dispose();
    _pinConfirmCtrl.dispose();
    super.dispose();
  }

  // ── Domain auto-detect debounce handler ────────────────────────────────
  void _onBusinessNameChanged(String value) {
    // Reset suggestion saat user edit ulang (kemungkinan nama beda)
    if (_showDomainSuggestion && _userAcceptedDomain == null) {
      setState(() {
        _showDomainSuggestion = false;
        _detectedDomain = null;
        _detectedDisplayName = null;
      });
    }

    final text = value.trim();
    _classifyDebounce?.cancel();

    // Minimum 4 char — terlalu pendek bikin false positive
    if (text.length < 4) return;

    _classifyDebounce = Timer(const Duration(milliseconds: 500), () {
      _classifyDomain(text);
    });
  }

  Future<void> _classifyDomain(String businessName) async {
    // Cancel in-flight request kalau ada
    _classifyCancelToken?.cancel('new_request');
    _classifyCancelToken = CancelToken();

    try {
      final resp = await _dio.post(
        '/api/v1/ai/classify-domain',
        data: {
          'business_name': businessName,
          'business_type': _businessType,
        },
        cancelToken: _classifyCancelToken,
      );

      final data = resp.data is String
          ? json.decode(resp.data as String)['data'] as Map<String, dynamic>
          : (resp.data as Map<String, dynamic>)['data'] as Map<String, dynamic>;

      if (!mounted) return;

      final suggestUiSwitch = data['suggest_ui_switch'] as bool? ?? false;
      if (!suggestUiSwitch) return; // F&B = default, skip suggestion card

      setState(() {
        _detectedDomain = data['domain'] as String?;
        _detectedDisplayName = data['display_name'] as String?;
        _showDomainSuggestion = true;
        _userAcceptedDomain = null;
      });
    } on DioException catch (e) {
      // Silent fail — register flow tetap lanjut default F&B (fail-open per amendment E)
      if (e.type != DioExceptionType.cancel) {
        // log only, gak show error ke user
        // ignore: avoid_print
        print('Classify domain error (non-fatal): ${e.message}');
      }
    } catch (_) {
      // ignore parse error
    }
  }

  String _domainEmoji(String? domain) {
    switch (domain) {
      case 'service':
        return '💈';
      case 'retail':
        return '🛒';
      default:
        return '☕';
    }
  }

  String _domainLabel(String? domain) {
    switch (domain) {
      case 'service':
        return 'Service';
      case 'retail':
        return 'Retail';
      default:
        return 'F&B';
    }
  }

  /// +62 tetap di UI; yang dikirim ke server '62…'. 0 di depan dibuang.
  String get _phoneNormalized {
    var d = _phoneCtrl.text.replaceAll(RegExp(r'\D'), '');
    if (d.startsWith('62')) d = d.substring(2);
    while (d.startsWith('0')) { d = d.substring(1); }
    return d.isEmpty ? '' : '62$d';
  }

  Future<void> _sendOtp() async {
    final phone = _phoneNormalized;
    final name = _nameCtrl.text.trim();
    final business = _businessCtrl.text.trim();

    if (phone.isEmpty || phone.length < 10 || !phone.startsWith('628')) {
      setState(() => _error = 'Format nomor HP: 628xxx (min 10 digit)');
      return;
    }
    if (name.isEmpty) {
      setState(() => _error = 'Nama pemilik harus diisi');
      return;
    }
    if (business.isEmpty) {
      setState(() => _error = 'Nama usaha harus diisi');
      return;
    }

    setState(() { _isLoading = true; _error = null; });

    try {
      await _dio.post('/api/v1/auth/otp/send', data: {
        'phone': phone,
        'purpose': 'register',
      });
      setState(() {
        _step = RegStep.inputOtp;
        _isLoading = false;
        _countdown = 300;
      });
      _startTimer();
    } on DioException catch (e) {
      setState(() {
        _isLoading = false;
        _error = e.response?.data?['detail']?.toString() ?? 'Gagal mengirim OTP';
      });
    }
  }

  void _startTimer() {
    _timer?.cancel();
    _timer = Timer.periodic(const Duration(seconds: 1), (t) {
      if (_countdown > 0) {
        setState(() => _countdown--);
      } else {
        _timer?.cancel();
      }
    });
  }

  Future<void> _register(String otp) async {
    if (otp.length != 6) return;
    setState(() { _isLoading = true; _error = null; });

    try {
      final resp = await _dio.post('/api/v1/auth/register', data: {
        'phone': _phoneNormalized,
        'owner_name': _nameCtrl.text.trim(),
        'business_name': _businessCtrl.text.trim(),
        'business_type': _businessType,
        'otp': otp,
        'pin': '000000', // Temporary, user sets real PIN next
        if (_referralCode.isNotEmpty) 'referral_code': _referralCode,
      });

      final data = resp.data is String
          ? json.decode(resp.data as String)['data'] as Map<String, dynamic>
          : (resp.data as Map<String, dynamic>)['data'] as Map<String, dynamic>;

      final token = data['access_token']?.toString() ?? '';
      await _cache.setAccessToken(token);
      await _cache.setPhone(_phoneNormalized);
      if (data['tenant_id'] != null) await _cache.setTenantId(data['tenant_id'].toString());
      if (data['outlet_id'] != null) await _cache.setOutletId(data['outlet_id'].toString());
      await _cache.setStockMode(data['stock_mode']?.toString() ?? 'simple');
      await _cache.setSubscriptionTier(data['subscription_tier']?.toString() ?? 'starter');

      // Persist domain pilihan user (Batch #26). Null kalau user tolak atau
      // suggestion tidak muncul (default F&B via BusinessLabels fallback).
      if (_userAcceptedDomain == true && _detectedDomain != null) {
        await _cache.setBusinessDomain(_detectedDomain);
      }

      _timer?.cancel();
      setState(() { _step = RegStep.setPin; _isLoading = false; });
    } on DioException catch (e) {
      setState(() {
        _isLoading = false;
        _error = e.response?.data?['detail']?.toString() ?? 'Registrasi gagal';
      });
    }
  }

  Future<void> _setPin() async {
    final pin = _pinCtrl.text;
    final confirm = _pinConfirmCtrl.text;
    if (pin.length != 6) {
      setState(() => _error = 'PIN harus 6 digit');
      return;
    }
    if (pin != confirm) {
      setState(() => _error = 'PIN tidak cocok');
      return;
    }

    setState(() { _isLoading = true; _error = null; });
    try {
      // PIN stored via SecureStorage through cache write
      const FlutterSecureStorage().write(key: 'user_pin', value: pin);

      // Set PIN on server too
      final token = _cache.accessToken;
      if (token != null) {
        try {
          await _dio.post('/api/v1/auth/pin/set',
            data: {'pin': pin},
            options: Options(headers: {'Authorization': 'Bearer $token'}),
          );
        } catch (_) {} // Non-blocking
      }

      if (!mounted) return;
      context.go('/ready');
    } catch (e) {
      setState(() { _isLoading = false; _error = 'Gagal menyimpan PIN'; });
    }
  }

  @override
  Widget build(BuildContext context) {
    final stepNo = _step == RegStep.inputInfo ? 1 : _step == RegStep.inputOtp ? 2 : 3;
    return Scaffold(
      backgroundColor: KasiraDS.bgBase,
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.fromLTRB(20, 8, 20, 24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  IconButton(
                    icon: const Icon(Icons.arrow_back, color: KasiraDS.textStrong),
                    onPressed: () {
                      if (_step == RegStep.inputOtp) {
                        setState(() { _step = RegStep.inputInfo; _error = null; });
                      } else {
                        context.go('/welcome');
                      }
                    },
                  ),
                  const Spacer(),
                  const SelarisMark(size: 24),
                  const SizedBox(width: 6),
                  Text('Selaris', style: KasiraDS.display(size: 18, color: KasiraDS.textStrong)),
                ],
              ),
              const SizedBox(height: 8),
              Text('Langkah $stepNo dari 3', style: KasiraDS.eyebrow(color: KasiraDS.brandPrimary)),
              const SizedBox(height: 6),
              Text(
                _step == RegStep.inputInfo ? 'Ceritain usahamu'
                    : _step == RegStep.inputOtp ? 'Periksa WhatsApp Anda'
                    : 'Buat PIN kasir',
                style: KasiraDS.display(size: 26, color: KasiraDS.textStrong),
              ),
              const SizedBox(height: 6),
              Text(
                _step == RegStep.inputInfo ? 'Nama & jenis usaha nentuin menu awal dan mode stok. Bisa diubah nanti.'
                    : _step == RegStep.inputOtp ? 'Kode 6 angka dikirim ke +$_phoneNormalized'
                    : '6 angka. Dipakai buat masuk cepat tiap hari tanpa nunggu OTP.',
                style: KasiraDS.sans(size: 13.5, color: KasiraDS.textMuted, height: 1.45),
              ),
              const SizedBox(height: 24),

              if (_error != null)
                Container(
                  padding: const EdgeInsets.all(12),
                  margin: const EdgeInsets.only(bottom: 16),
                  decoration: BoxDecoration(
                    color: KasiraDS.danger.withOpacity(0.08),
                    borderRadius: KasiraDS.brSm,
                    border: Border.all(color: KasiraDS.danger.withOpacity(0.3)),
                  ),
                  child: Text(_error!, style: KasiraDS.sans(size: 13, color: KasiraDS.danger)),
                ),

              if (_step == RegStep.inputInfo) ...[
                _label('Nomor WhatsApp'),
                TextField(
                  controller: _phoneCtrl,
                  keyboardType: TextInputType.phone,
                  inputFormatters: [FilteringTextInputFormatter.digitsOnly],
                  style: KasiraDS.sans(size: 16, weight: FontWeight.w600, color: KasiraDS.textStrong),
                  decoration: _deco(hint: '812 3456 7890').copyWith(
                    prefixIcon: Padding(
                      padding: const EdgeInsets.only(left: 14, right: 8),
                      child: Text('🇮🇩 +62', style: KasiraDS.sans(size: 15, weight: FontWeight.w600, color: KasiraDS.textMuted)),
                    ),
                    prefixIconConstraints: const BoxConstraints(minWidth: 0, minHeight: 0),
                  ),
                ),
                const SizedBox(height: 14),
                _label('Nama pemilik'),
                _buildField('', _nameCtrl, hint: 'Ivan'),
                const SizedBox(height: 14),
                _label('Nama usaha'),
                _buildField('', _businessCtrl, hint: 'Kopi Senja', onChanged: _onBusinessNameChanged),
                if (_showDomainSuggestion && _detectedDomain != null)
                  _buildDomainSuggestionCard(),
                const SizedBox(height: 14),
                _label('Jenis usaha'),
                GridView.count(
                  crossAxisCount: 2,
                  shrinkWrap: true,
                  physics: const NeverScrollableScrollPhysics(),
                  mainAxisSpacing: 8,
                  crossAxisSpacing: 8,
                  childAspectRatio: 3.1,
                  children: const [
                    ('cafe', '☕', 'Coffee shop'),
                    ('warung', '🍛', 'Warung makan'),
                    ('resto', '🍽️', 'Resto bermeja'),
                    ('other', '🛍️', 'Toko lainnya'),
                  ].map((t) {
                    final selected = _businessType == t.$1;
                    return InkWell(
                      onTap: () => setState(() => _businessType = t.$1),
                      borderRadius: KasiraDS.brMd,
                      child: Container(
                        padding: const EdgeInsets.symmetric(horizontal: 12),
                        decoration: BoxDecoration(
                          color: selected ? KasiraDS.brandTint : KasiraDS.surfaceCard,
                          borderRadius: KasiraDS.brMd,
                          border: Border.all(color: selected ? KasiraDS.brandPrimary : KasiraDS.borderSubtle, width: selected ? 1.5 : 1),
                        ),
                        child: Row(
                          children: [
                            Text(t.$2, style: const TextStyle(fontSize: 18)),
                            const SizedBox(width: 8),
                            Expanded(child: Text(t.$3, maxLines: 1, overflow: TextOverflow.ellipsis,
                                style: KasiraDS.sans(size: 13.5, weight: FontWeight.w700, color: selected ? KasiraDS.brandPrimary : KasiraDS.textStrong))),
                          ],
                        ),
                      ),
                    );
                  }).toList(),
                ),
                const SizedBox(height: 14),
                _label('Kode referral (opsional)'),
                TextField(
                  onChanged: (v) => _referralCode = v,
                  style: KasiraDS.sans(size: 15, color: KasiraDS.textStrong),
                  decoration: _deco(hint: 'Dari teman yang sudah memakai Selaris'),
                ),
                const SizedBox(height: 24),
                _primary(_isLoading ? null : _sendOtp, 'Lanjut → kirim kode WhatsApp'),
                const SizedBox(height: 10),
                Center(child: Text('Dengan melanjutkan, Anda menyetujui Ketentuan & Privasi Selaris.',
                    textAlign: TextAlign.center, style: KasiraDS.sans(size: 11, color: KasiraDS.textMuted))),
              ],

              if (_step == RegStep.inputOtp) ...[
                TextField(
                  controller: _otpCtrl,
                  keyboardType: TextInputType.number,
                  maxLength: 6,
                  autofocus: true,
                  textAlign: TextAlign.center,
                  style: KasiraDS.mono(size: 28, weight: FontWeight.w700, color: KasiraDS.textStrong, letterSpacing: 12),
                  inputFormatters: [FilteringTextInputFormatter.digitsOnly],
                  decoration: _deco(hint: '••••••').copyWith(counterText: ''),
                  onChanged: (v) { if (v.length == 6) _register(v); },
                ),
                const SizedBox(height: 12),
                Center(child: Text('Kode otomatis terbaca kalau WA di HP ini',
                    style: KasiraDS.sans(size: 12, color: KasiraDS.textMuted))),
                const SizedBox(height: 16),
                if (_countdown > 0)
                  Center(child: Text('Belum dapat? Kirim ulang · ${_countdown ~/ 60}:${(_countdown % 60).toString().padLeft(2, '0')}',
                      style: KasiraDS.sans(size: 13, color: KasiraDS.textMuted))),
                if (_isLoading)
                  const Padding(
                    padding: EdgeInsets.only(top: 16),
                    child: Center(child: CircularProgressIndicator(color: KasiraDS.brandPrimary)),
                  ),
              ],

              if (_step == RegStep.setPin) ...[
                _label('PIN baru (6 angka)'),
                _buildField('', _pinCtrl, obscure: true, keyboardType: TextInputType.number, maxLength: 6, hint: '••••••'),
                const SizedBox(height: 14),
                _label('Ulangi PIN'),
                _buildField('', _pinConfirmCtrl, obscure: true, keyboardType: TextInputType.number, maxLength: 6, hint: '••••••'),
                const SizedBox(height: 24),
                _primary(_isLoading ? null : _setPin, 'Mulai pakai Selaris'),
                const SizedBox(height: 10),
                Center(child: Text('Lupa PIN? Masuk kembali dengan OTP WhatsApp.',
                    style: KasiraDS.sans(size: 11.5, color: KasiraDS.textMuted))),
              ],
            ],
          ),
        ),
      ),
    );
  }

  Widget _label(String t) => Padding(
        padding: const EdgeInsets.only(bottom: 6),
        child: Text(t.toUpperCase(), style: KasiraDS.eyebrow()),
      );

  InputDecoration _deco({String? hint}) => InputDecoration(
        hintText: hint,
        hintStyle: KasiraDS.sans(size: 15, color: KasiraDS.textMuted),
        filled: true,
        fillColor: KasiraDS.surfaceCard,
        contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
        border: OutlineInputBorder(borderRadius: KasiraDS.brMd, borderSide: const BorderSide(color: KasiraDS.borderDefault)),
        enabledBorder: OutlineInputBorder(borderRadius: KasiraDS.brMd, borderSide: const BorderSide(color: KasiraDS.borderDefault)),
        focusedBorder: OutlineInputBorder(borderRadius: KasiraDS.brMd, borderSide: const BorderSide(color: KasiraDS.brandPrimary, width: 1.5)),
      );

  Widget _primary(VoidCallback? onPressed, String label) => SizedBox(
        width: double.infinity,
        height: 54,
        child: FilledButton(
          onPressed: onPressed,
          style: FilledButton.styleFrom(
            backgroundColor: KasiraDS.brandPrimary,
            shape: RoundedRectangleBorder(borderRadius: KasiraDS.brPill),
          ),
          child: _isLoading
              ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
              : Text(label, style: KasiraDS.sans(size: 15.5, weight: FontWeight.w700, color: KasiraDS.textOnBrand)),
        ),
      );

  Widget _buildField(String label, TextEditingController ctrl, {
    String? hint, bool obscure = false, TextInputType? keyboardType, int? maxLength,
    ValueChanged<String>? onChanged,
  }) {
    return TextField(
      controller: ctrl,
      obscureText: obscure,
      keyboardType: keyboardType,
      maxLength: maxLength,
      style: KasiraDS.sans(size: 15, weight: FontWeight.w600, color: KasiraDS.textStrong),
      inputFormatters: keyboardType == TextInputType.number ? [FilteringTextInputFormatter.digitsOnly] : null,
      onChanged: onChanged,
      decoration: _deco(hint: hint).copyWith(counterText: '', labelText: label.isEmpty ? null : label),
    );
  }

  Widget _buildDomainSuggestionCard() {
    final displayName = _detectedDisplayName ?? 'bisnis Anda';
    final domainLabel = _domainLabel(_detectedDomain);
    final emoji = _domainEmoji(_detectedDomain);

    return Container(
      margin: const EdgeInsets.only(top: 10, bottom: 4),
      padding: const EdgeInsets.fromLTRB(14, 12, 14, 10),
      decoration: BoxDecoration(
        color: KasiraDS.brandPrimary.withOpacity(0.09),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: KasiraDS.brandPrimary.withOpacity(0.4), width: 1),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Text(emoji, style: const TextStyle(fontSize: 18)),
              const SizedBox(width: 8),
              Expanded(
                child: Text.rich(
                  TextSpan(
                    style: const TextStyle(color: Colors.white, fontSize: 13, height: 1.35),
                    children: [
                      const TextSpan(text: 'Kami deteksi bisnisnya '),
                      TextSpan(
                        text: displayName,
                        style: const TextStyle(fontWeight: FontWeight.bold),
                      ),
                      const TextSpan(text: ', pakai istilah '),
                      TextSpan(
                        text: domainLabel,
                        style: const TextStyle(fontWeight: FontWeight.bold),
                      ),
                      const TextSpan(text: '?'),
                    ],
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Row(
            children: [
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: () => setState(() {
                    _userAcceptedDomain = true;
                    _showDomainSuggestion = false;
                  }),
                  style: OutlinedButton.styleFrom(
                    side: BorderSide(color: KasiraDS.brandPrimary.withOpacity(0.6)),
                    foregroundColor: KasiraDS.brandPrimary,
                    padding: const EdgeInsets.symmetric(vertical: 6),
                  ),
                  icon: const Icon(Icons.check, size: 16),
                  label: const Text('Iya, pakai', style: TextStyle(fontSize: 12)),
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: TextButton(
                  onPressed: () => setState(() {
                    _userAcceptedDomain = false;
                    _showDomainSuggestion = false;
                    _detectedDomain = null;
                  }),
                  style: TextButton.styleFrom(
                    foregroundColor: Colors.grey[400],
                    padding: const EdgeInsets.symmetric(vertical: 6),
                  ),
                  child: const Text('Bukan', style: TextStyle(fontSize: 12)),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
