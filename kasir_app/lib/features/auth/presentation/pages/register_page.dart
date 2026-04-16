import 'dart:async';
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:dio/dio.dart';
import 'package:go_router/go_router.dart';
import '../../../../core/config/app_config.dart';
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

  final _storage = const FlutterSecureStorage();
  Dio get _dio => Dio(BaseOptions(
    baseUrl: AppConfig.baseUrl,
    connectTimeout: const Duration(seconds: 15),
    receiveTimeout: const Duration(seconds: 15),
  ));

  @override
  void dispose() {
    _timer?.cancel();
    _phoneCtrl.dispose();
    _nameCtrl.dispose();
    _businessCtrl.dispose();
    _otpCtrl.dispose();
    _pinCtrl.dispose();
    _pinConfirmCtrl.dispose();
    super.dispose();
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
      await _storage.write(key: 'access_token', value: token);
      await _storage.write(key: 'phone', value: _phoneCtrl.text.trim());
      if (data['tenant_id'] != null) await _storage.write(key: 'tenant_id', value: data['tenant_id'].toString());
      if (data['outlet_id'] != null) await _storage.write(key: 'outlet_id', value: data['outlet_id'].toString());
      await _storage.write(key: 'stock_mode', value: data['stock_mode']?.toString() ?? 'simple');
      await _storage.write(key: 'subscription_tier', value: data['subscription_tier']?.toString() ?? 'starter');

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
      await _storage.write(key: 'user_pin', value: pin);

      // Set PIN on server too
      final token = await _storage.read(key: 'access_token');
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
                _buildField('Nama Usaha', _businessCtrl, hint: 'Warung Kopi Ivan'),
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
  }) {
    return TextField(
      controller: ctrl,
      obscureText: obscure,
      keyboardType: keyboardType,
      maxLength: maxLength,
      style: const TextStyle(color: Colors.white),
      inputFormatters: keyboardType == TextInputType.number ? [FilteringTextInputFormatter.digitsOnly] : null,
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
}
