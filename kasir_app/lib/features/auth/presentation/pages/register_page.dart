import 'dart:async';
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:dio/dio.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:go_router/go_router.dart';
import '../../../../core/config/app_config.dart';
import '../../../../core/services/session_cache.dart';
import '../../../../core/theme/app_colors.dart';

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

  Future<void> _sendOtp() async {
    final phone = _phoneCtrl.text.trim();
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
        'phone': _phoneCtrl.text.trim(),
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
      await _cache.setPhone(_phoneCtrl.text.trim());
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
      context.go('/dashboard');
    } catch (e) {
      setState(() { _isLoading = false; _error = 'Gagal menyimpan PIN'; });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0B0E14),
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        leading: IconButton(
          icon: const Icon(Icons.arrow_back, color: Colors.white),
          onPressed: () {
            if (_step == RegStep.inputOtp) {
              setState(() { _step = RegStep.inputInfo; _error = null; });
            } else {
              context.go('/login');
            }
          },
        ),
      ),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                _step == RegStep.inputInfo ? 'Daftar Kasira'
                    : _step == RegStep.inputOtp ? 'Verifikasi OTP'
                    : 'Buat PIN',
                style: const TextStyle(fontSize: 28, fontWeight: FontWeight.bold, color: Colors.white),
              ),
              const SizedBox(height: 8),
              Text(
                _step == RegStep.inputInfo ? 'Mulai kelola usahamu dengan Kasira POS'
                    : _step == RegStep.inputOtp ? 'Masukkan kode OTP yang dikirim ke WhatsApp'
                    : 'Buat PIN 6 digit untuk login cepat',
                style: TextStyle(color: Colors.grey[400], fontSize: 14),
              ),
              const SizedBox(height: 32),

              if (_error != null)
                Container(
                  padding: const EdgeInsets.all(12),
                  margin: const EdgeInsets.only(bottom: 16),
                  decoration: BoxDecoration(
                    color: Colors.red.withValues(alpha: 0.1),
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: Colors.red.withValues(alpha: 0.3)),
                  ),
                  child: Text(_error!, style: const TextStyle(color: Colors.red, fontSize: 13)),
                ),

              if (_step == RegStep.inputInfo) ...[
                _buildField('Nomor WhatsApp', _phoneCtrl, hint: '628123456789', keyboardType: TextInputType.phone),
                const SizedBox(height: 16),
                _buildField('Nama Pemilik', _nameCtrl, hint: 'Ivan'),
                const SizedBox(height: 16),
                _buildField(
                  'Nama Usaha',
                  _businessCtrl,
                  hint: 'Warung Kopi Ivan',
                  onChanged: _onBusinessNameChanged,
                ),
                // Suggestion card — muncul saat classify detect Non-F&B
                if (_showDomainSuggestion && _detectedDomain != null)
                  _buildDomainSuggestionCard(),
                const SizedBox(height: 16),
                // Business type
                Text('Jenis Usaha', style: TextStyle(color: Colors.grey[300], fontSize: 13, fontWeight: FontWeight.w500)),
                const SizedBox(height: 8),
                Wrap(
                  spacing: 8,
                  children: ['cafe', 'warung', 'resto', 'other'].map((t) {
                    final label = {'cafe': 'Cafe', 'warung': 'Warung', 'resto': 'Resto', 'other': 'Lainnya'}[t]!;
                    final selected = _businessType == t;
                    return ChoiceChip(
                      label: Text(label),
                      selected: selected,
                      onSelected: (_) => setState(() => _businessType = t),
                      selectedColor: AppColors.primary,
                      labelStyle: TextStyle(color: selected ? Colors.white : Colors.grey[300]),
                      backgroundColor: const Color(0xFF1A1F2B),
                    );
                  }).toList(),
                ),
                const SizedBox(height: 16),
                // Referral (optional)
                TextField(
                  onChanged: (v) => _referralCode = v,
                  style: const TextStyle(color: Colors.white),
                  decoration: InputDecoration(
                    labelText: 'Kode Referral (opsional)',
                    labelStyle: TextStyle(color: Colors.grey[500]),
                    filled: true,
                    fillColor: const Color(0xFF141820),
                    border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none),
                  ),
                ),
                const SizedBox(height: 24),
                SizedBox(
                  width: double.infinity,
                  height: 52,
                  child: ElevatedButton(
                    onPressed: _isLoading ? null : _sendOtp,
                    style: ElevatedButton.styleFrom(
                      backgroundColor: AppColors.primary,
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                    ),
                    child: _isLoading
                        ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                        : const Text('Kirim OTP', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600, color: Colors.white)),
                  ),
                ),
              ],

              if (_step == RegStep.inputOtp) ...[
                TextField(
                  controller: _otpCtrl,
                  keyboardType: TextInputType.number,
                  maxLength: 6,
                  textAlign: TextAlign.center,
                  style: const TextStyle(color: Colors.white, fontSize: 28, letterSpacing: 12),
                  inputFormatters: [FilteringTextInputFormatter.digitsOnly],
                  decoration: InputDecoration(
                    counterText: '',
                    filled: true,
                    fillColor: const Color(0xFF141820),
                    border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none),
                  ),
                  onChanged: (v) { if (v.length == 6) _register(v); },
                ),
                const SizedBox(height: 16),
                if (_countdown > 0)
                  Text('OTP berlaku ${_countdown ~/ 60}:${(_countdown % 60).toString().padLeft(2, '0')}',
                      style: TextStyle(color: Colors.grey[500])),
                if (_isLoading)
                  const Padding(
                    padding: EdgeInsets.only(top: 16),
                    child: Center(child: CircularProgressIndicator(color: AppColors.primary)),
                  ),
              ],

              if (_step == RegStep.setPin) ...[
                _buildField('PIN Baru (6 digit)', _pinCtrl, obscure: true, keyboardType: TextInputType.number, maxLength: 6),
                const SizedBox(height: 16),
                _buildField('Konfirmasi PIN', _pinConfirmCtrl, obscure: true, keyboardType: TextInputType.number, maxLength: 6),
                const SizedBox(height: 24),
                SizedBox(
                  width: double.infinity,
                  height: 52,
                  child: ElevatedButton(
                    onPressed: _isLoading ? null : _setPin,
                    style: ElevatedButton.styleFrom(
                      backgroundColor: AppColors.primary,
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                    ),
                    child: _isLoading
                        ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                        : const Text('Mulai Pakai Kasira', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600, color: Colors.white)),
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildField(String label, TextEditingController ctrl, {
    String? hint, bool obscure = false, TextInputType? keyboardType, int? maxLength,
    ValueChanged<String>? onChanged,
  }) {
    return TextField(
      controller: ctrl,
      obscureText: obscure,
      keyboardType: keyboardType,
      maxLength: maxLength,
      style: const TextStyle(color: Colors.white),
      inputFormatters: keyboardType == TextInputType.number ? [FilteringTextInputFormatter.digitsOnly] : null,
      onChanged: onChanged,
      decoration: InputDecoration(
        labelText: label,
        hintText: hint,
        labelStyle: TextStyle(color: Colors.grey[400]),
        hintStyle: TextStyle(color: Colors.grey[600]),
        counterText: '',
        filled: true,
        fillColor: const Color(0xFF141820),
        border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none),
      ),
    );
  }

  Widget _buildDomainSuggestionCard() {
    final displayName = _detectedDisplayName ?? 'bisnis kamu';
    final domainLabel = _domainLabel(_detectedDomain);
    final emoji = _domainEmoji(_detectedDomain);

    return Container(
      margin: const EdgeInsets.only(top: 10, bottom: 4),
      padding: const EdgeInsets.fromLTRB(14, 12, 14, 10),
      decoration: BoxDecoration(
        color: AppColors.primary.withOpacity(0.09),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.primary.withOpacity(0.4), width: 1),
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
                      const TextSpan(text: ' — pakai istilah '),
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
                    side: BorderSide(color: AppColors.primary.withOpacity(0.6)),
                    foregroundColor: AppColors.primary,
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
