import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:dio/dio.dart';
import 'package:go_router/go_router.dart';
import '../../../../core/config/app_config.dart';
import '../../../../core/theme/app_colors.dart';

// --- STATE ---
enum AuthStep { inputPhone, inputOtp, setPin, pinLogin }

class AuthState {
  final AuthStep step;
  final bool isLoading;
  final String? error;
  final String phone;
  final String otp;
  final String firstPin;
  final int pinAttempts;
  final bool isLocked;
  final int countdown;
  final bool canResendOtp;
  final bool isSuccess;

  AuthState({
    this.step = AuthStep.pinLogin,
    this.isLoading = true,
    this.error,
    this.phone = '',
    this.otp = '',
    this.firstPin = '',
    this.pinAttempts = 0,
    this.isLocked = false,
    this.countdown = 300,
    this.canResendOtp = false,
    this.isSuccess = false,
  });

  AuthState copyWith({
    AuthStep? step,
    bool? isLoading,
    String? error,
    bool clearError = false,
    String? phone,
    String? otp,
    String? firstPin,
    int? pinAttempts,
    bool? isLocked,
    int? countdown,
    bool? canResendOtp,
    bool? isSuccess,
  }) {
    return AuthState(
      step: step ?? this.step,
      isLoading: isLoading ?? this.isLoading,
      error: clearError ? null : (error ?? this.error),
      phone: phone ?? this.phone,
      otp: otp ?? this.otp,
      firstPin: firstPin ?? this.firstPin,
      pinAttempts: pinAttempts ?? this.pinAttempts,
      isLocked: isLocked ?? this.isLocked,
      countdown: countdown ?? this.countdown,
      canResendOtp: canResendOtp ?? this.canResendOtp,
      isSuccess: isSuccess ?? this.isSuccess,
    );
  }
}

// --- PROVIDER ---
final authProvider = StateNotifierProvider<AuthNotifier, AuthState>((ref) {
  return AuthNotifier();
});

class AuthNotifier extends StateNotifier<AuthState> {
  AuthNotifier() : super(AuthState()) {
    _checkInitialState();
  }

  final _storage = const FlutterSecureStorage();
  Dio get _dio => Dio(BaseOptions(
    baseUrl: AppConfig.baseUrl,
    connectTimeout: const Duration(seconds: 10),
    receiveTimeout: const Duration(seconds: 10),
  ));
  Timer? _timer;

  Future<void> _checkInitialState() async {
    try {
      final savedPin = await _storage.read(key: 'user_pin');
      if (savedPin != null && savedPin.isNotEmpty) {
        state = state.copyWith(step: AuthStep.pinLogin, isLoading: false);
      } else {
        state = state.copyWith(step: AuthStep.inputPhone, isLoading: false);
      }
    } catch (e) {
      state = state.copyWith(step: AuthStep.inputPhone, isLoading: false);
    }
  }

  void setPhone(String phone) {
    state = state.copyWith(phone: phone, clearError: true);
  }

  Future<void> sendOtp() async {
    if (state.phone.isEmpty || state.phone.length < 10 || !state.phone.startsWith('628')) {
      state = state.copyWith(error: 'Format nomor HP tidak valid (harus 628xxx dan min 10 digit)');
      return;
    }
    
    state = state.copyWith(isLoading: true, clearError: true);
    
    try {
      await _dio.post('/api/v1/auth/otp/send', data: {'phone': state.phone});
      
      state = state.copyWith(
        step: AuthStep.inputOtp, 
        isLoading: false,
        countdown: 300,
        canResendOtp: false,
      );
      _startTimer();
    } on DioException catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: e.response?.data['detail'] ?? 'Gagal mengirim OTP. Pastikan nomor terdaftar.',
      );
    } catch (e) {
      state = state.copyWith(isLoading: false, error: 'Terjadi kesalahan sistem');
    }
  }

  void _startTimer() {
    _timer?.cancel();
    _timer = Timer.periodic(const Duration(seconds: 1), (timer) {
      if (state.countdown > 0) {
        final newCountdown = state.countdown - 1;
        state = state.copyWith(
          countdown: newCountdown,
          canResendOtp: newCountdown <= 240, // 300 - 60 = 240
        );
      } else {
        _timer?.cancel();
        state = state.copyWith(error: 'OTP telah kedaluwarsa');
      }
    });
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  Future<void> verifyOtp(String otp) async {
    if (otp.length != 6) return;
    
    state = state.copyWith(isLoading: true, otp: otp, clearError: true);
    
    try {
      final response = await _dio.post('/api/v1/auth/otp/verify', data: {
        'phone': state.phone, 
        'otp': otp
      });
      
      final data = response.data['data'];
      final token = data['access_token'] as String;
      final tenantId = data['tenant_id'] as String?;
      final outletId = data['outlet_id'] as String?;

      await _storage.write(key: 'access_token', value: token);
      if (tenantId != null) await _storage.write(key: 'tenant_id', value: tenantId);
      if (outletId != null) await _storage.write(key: 'outlet_id', value: outletId);

      _timer?.cancel();

      final savedPin = await _storage.read(key: 'user_pin');
      if (savedPin != null && savedPin.isNotEmpty) {
        state = state.copyWith(isLoading: false, isSuccess: true);
      } else {
        state = state.copyWith(step: AuthStep.setPin, isLoading: false, firstPin: '');
      }
    } on DioException catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: e.response?.data['detail'] ?? 'Kode OTP salah atau kedaluwarsa',
      );
    } catch (e) {
      state = state.copyWith(isLoading: false, error: 'Terjadi kesalahan sistem');
    }
  }

  void setFirstPin(String pin) {
    state = state.copyWith(firstPin: pin, clearError: true);
  }

  Future<void> confirmPin(String pin) async {
    if (pin != state.firstPin) {
      state = state.copyWith(error: 'PIN tidak cocok');
      return;
    }
    
    state = state.copyWith(isLoading: true, clearError: true);
    try {
      await _storage.write(key: 'user_pin', value: pin);
      state = state.copyWith(isLoading: false, isSuccess: true);
    } catch (e) {
      state = state.copyWith(isLoading: false, error: 'Gagal menyimpan PIN');
    }
  }

  Future<void> loginWithPin(String pin) async {
    if (state.isLocked) {
      state = state.copyWith(error: 'Akun terkunci. Silakan gunakan OTP.');
      return;
    }

    state = state.copyWith(isLoading: true, clearError: true);
    
    try {
      final savedPin = await _storage.read(key: 'user_pin');
      
      if (savedPin == pin) {
        state = state.copyWith(isLoading: false, pinAttempts: 0, isSuccess: true);
      } else {
        final attempts = state.pinAttempts + 1;
        if (attempts >= 3) {
          state = state.copyWith(
            isLoading: false, 
            pinAttempts: attempts, 
            isLocked: true,
            error: 'PIN salah 3 kali. Akun terkunci, gunakan OTP.',
          );
        } else {
          state = state.copyWith(
            isLoading: false, 
            pinAttempts: attempts,
            error: 'PIN salah. Sisa percobaan: ${3 - attempts}',
          );
        }
      }
    } catch (e) {
      state = state.copyWith(isLoading: false, error: 'Terjadi kesalahan');
    }
  }

  void useOtpInstead() {
    state = state.copyWith(
      step: AuthStep.inputPhone, 
      clearError: true, 
      isLocked: false, 
      pinAttempts: 0
    );
  }
}

// --- UI ---
class LoginPage extends ConsumerStatefulWidget {
  const LoginPage({super.key});

  @override
  ConsumerState<LoginPage> createState() => _LoginPageState();
}

class _LoginPageState extends ConsumerState<LoginPage> {
  final _phoneController = TextEditingController();
  final _otpControllers = List.generate(6, (_) => TextEditingController());
  final _otpFocusNodes = List.generate(6, (_) => FocusNode());
  
  String _pinInput = '';
  bool _isConfirmingPin = false;

  @override
  void dispose() {
    _phoneController.dispose();
    for (var c in _otpControllers) { c.dispose(); }
    for (var f in _otpFocusNodes) { f.dispose(); }
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final authState = ref.watch(authProvider);

    ref.listen<AuthState>(authProvider, (previous, next) {
      if (next.isSuccess && (previous?.isSuccess != true)) {
        context.go('/dashboard');
      }
      if (next.error != null && next.error != previous?.error) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(next.error!),
            backgroundColor: Colors.red,
            behavior: SnackBarBehavior.floating,
          ),
        );
      }
    });

    if (authState.isLoading && authState.step == AuthStep.pinLogin && _pinInput.isEmpty) {
      return const Scaffold(
        backgroundColor: AppColors.primary,
        body: Center(child: CircularProgressIndicator(color: Colors.white)),
      );
    }

    return Scaffold(
      backgroundColor: AppColors.primary,
      body: Center(
        child: SingleChildScrollView(
          child: Container(
            width: 400,
            padding: const EdgeInsets.all(40),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(24),
              boxShadow: [
                BoxShadow(
                  color: Colors.black.withOpacity(0.1),
                  blurRadius: 30,
                  offset: const Offset(0, 10),
                ),
              ],
            ),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                _buildHeader(),
                const SizedBox(height: 32),
                _buildContent(authState),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildHeader() {
    return Row(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        Container(
          padding: const EdgeInsets.all(8),
          decoration: BoxDecoration(
            color: AppColors.primary.withOpacity(0.1),
            borderRadius: BorderRadius.circular(12),
          ),
          child: const Icon(
            Icons.point_of_sale_rounded, 
            color: AppColors.primary, 
            size: 32
          ),
        ),
        const SizedBox(width: 16),
        Text(
          'KASIRA',
          style: Theme.of(context).textTheme.displaySmall?.copyWith(
                color: AppColors.primary,
                fontWeight: FontWeight.w800,
                letterSpacing: -1,
              ),
        ),
      ],
    );
  }

  Widget _buildContent(AuthState state) {
    switch (state.step) {
      case AuthStep.inputPhone:
        return _buildInputPhone(state);
      case AuthStep.inputOtp:
        return _buildInputOtp(state);
      case AuthStep.setPin:
        return _buildSetPin(state);
      case AuthStep.pinLogin:
        return _buildPinLogin(state);
    }
  }

  Widget _buildInputPhone(AuthState state) {
    return Column(
      children: [
        Text(
          'Masukkan Nomor HP',
          style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.bold),
        ),
        const SizedBox(height: 8),
        const Text(
          'Format: 628xxx',
          style: TextStyle(color: AppColors.textSecondary),
        ),
        const SizedBox(height: 24),
        TextField(
          controller: _phoneController,
          keyboardType: TextInputType.phone,
          inputFormatters: [FilteringTextInputFormatter.digitsOnly],
          decoration: InputDecoration(
            hintText: '628...',
            prefixIcon: const Icon(Icons.phone),
            border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
          ),
          onChanged: (val) => ref.read(authProvider.notifier).setPhone(val),
        ),
        const SizedBox(height: 24),
        SizedBox(
          width: double.infinity,
          height: 50,
          child: ElevatedButton(
            onPressed: state.isLoading ? null : () {
              ref.read(authProvider.notifier).sendOtp();
            },
            child: state.isLoading 
                ? const SizedBox(width: 24, height: 24, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
                : const Text('Kirim OTP'),
          ),
        ),
      ],
    );
  }

  Widget _buildInputOtp(AuthState state) {
    final minutes = (state.countdown / 60).floor();
    final seconds = state.countdown % 60;
    final timeString = '${minutes.toString().padLeft(2, '0')}:${seconds.toString().padLeft(2, '0')}';

    return Column(
      children: [
        Text(
          'Verifikasi OTP',
          style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.bold),
        ),
        const SizedBox(height: 8),
        Text(
          'Kode dikirim ke ${state.phone}',
          style: const TextStyle(color: AppColors.textSecondary),
          textAlign: TextAlign.center,
        ),
        const SizedBox(height: 24),
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceEvenly,
          children: List.generate(6, (index) {
            return SizedBox(
              width: 45,
              child: TextField(
                controller: _otpControllers[index],
                focusNode: _otpFocusNodes[index],
                keyboardType: TextInputType.number,
                textAlign: TextAlign.center,
                maxLength: 1,
                style: const TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
                decoration: InputDecoration(
                  counterText: '',
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                ),
                onChanged: (value) {
                  if (value.isNotEmpty && index < 5) {
                    _otpFocusNodes[index + 1].requestFocus();
                  } else if (value.isEmpty && index > 0) {
                    _otpFocusNodes[index - 1].requestFocus();
                  }
                  
                  final otp = _otpControllers.map((c) => c.text).join();
                  if (otp.length == 6) {
                    ref.read(authProvider.notifier).verifyOtp(otp);
                  }
                },
              ),
            );
          }),
        ),
        const SizedBox(height: 24),
        if (state.isLoading)
          const CircularProgressIndicator()
        else
          Column(
            children: [
              Text(timeString, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 18)),
              const SizedBox(height: 8),
              TextButton(
                onPressed: state.canResendOtp ? () {
                  for (var c in _otpControllers) { c.clear(); }
                  _otpFocusNodes[0].requestFocus();
                  ref.read(authProvider.notifier).sendOtp();
                } : null,
                child: Text(
                  'Kirim Ulang OTP',
                  style: TextStyle(color: state.canResendOtp ? AppColors.primary : Colors.grey),
                ),
              ),
            ],
          ),
      ],
    );
  }

  Widget _buildSetPin(AuthState state) {
    return Column(
      children: [
        Text(
          _isConfirmingPin ? 'Konfirmasi PIN' : 'Buat PIN Baru',
          style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.bold),
        ),
        const SizedBox(height: 8),
        Text(
          _isConfirmingPin ? 'Masukkan ulang PIN 6 digit Anda' : 'Masukkan PIN 6 digit untuk login selanjutnya',
          style: const TextStyle(color: AppColors.textSecondary),
          textAlign: TextAlign.center,
        ),
        const SizedBox(height: 24),
        _buildPinDots(_pinInput.length),
        const SizedBox(height: 32),
        _buildCustomKeypad((val) {
          setState(() {
            if (val == 'del') {
              if (_pinInput.isNotEmpty) {
                _pinInput = _pinInput.substring(0, _pinInput.length - 1);
              }
            } else if (_pinInput.length < 6) {
              _pinInput += val;
              if (_pinInput.length == 6) {
                if (!_isConfirmingPin) {
                  ref.read(authProvider.notifier).setFirstPin(_pinInput);
                  _isConfirmingPin = true;
                  _pinInput = '';
                } else {
                  ref.read(authProvider.notifier).confirmPin(_pinInput).then((_) {
                    final currentState = ref.read(authProvider);
                    if (currentState.error != null) {
                      setState(() {
                        _pinInput = '';
                        _isConfirmingPin = false;
                      });
                    }
                  });
                }
              }
            }
          });
        }),
        if (state.isLoading) ...[
          const SizedBox(height: 16),
          const CircularProgressIndicator(),
        ]
      ],
    );
  }

  Widget _buildPinLogin(AuthState state) {
    return Column(
      children: [
        Text(
          'Masukkan PIN',
          style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.bold),
        ),
        const SizedBox(height: 8),
        Text(
          state.isLocked ? 'Akun terkunci' : 'Masukkan PIN 6 digit Anda',
          style: TextStyle(color: state.isLocked ? Colors.red : AppColors.textSecondary),
        ),
        const SizedBox(height: 24),
        _buildPinDots(_pinInput.length),
        const SizedBox(height: 32),
        _buildCustomKeypad((val) {
          if (state.isLocked || state.isLoading) return;
          
          setState(() {
            if (val == 'del') {
              if (_pinInput.isNotEmpty) {
                _pinInput = _pinInput.substring(0, _pinInput.length - 1);
              }
            } else if (_pinInput.length < 6) {
              _pinInput += val;
              if (_pinInput.length == 6) {
                ref.read(authProvider.notifier).loginWithPin(_pinInput).then((_) {
                  final currentState = ref.read(authProvider);
                  if (!currentState.isSuccess) {
                    setState(() {
                      _pinInput = '';
                    });
                  }
                });
              }
            }
          });
        }),
        const SizedBox(height: 24),
        if (state.isLoading)
          const CircularProgressIndicator()
        else
          TextButton(
            onPressed: () {
              ref.read(authProvider.notifier).useOtpInstead();
            },
            child: const Text(
              'Lupa PIN? Gunakan OTP',
              style: TextStyle(color: AppColors.primary),
            ),
          ),
      ],
    );
  }

  Widget _buildPinDots(int length) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.center,
      children: List.generate(6, (index) {
        return Container(
          margin: const EdgeInsets.symmetric(horizontal: 8),
          width: 16,
          height: 16,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            color: index < length ? AppColors.primary : Colors.grey.shade300,
          ),
        );
      }),
    );
  }

  Widget _buildCustomKeypad(Function(String) onKeyPress) {
    return GridView.count(
      shrinkWrap: true,
      crossAxisCount: 3,
      childAspectRatio: 1.5,
      mainAxisSpacing: 8,
      crossAxisSpacing: 8,
      physics: const NeverScrollableScrollPhysics(),
      children: [
        for (var i = 1; i <= 9; i++) _buildKeypadButton(i.toString(), onKeyPress),
        const SizedBox(),
        _buildKeypadButton('0', onKeyPress),
        _buildKeypadButton('del', onKeyPress, icon: Icons.backspace_outlined),
      ],
    );
  }

  Widget _buildKeypadButton(String value, Function(String) onKeyPress, {IconData? icon}) {
    return InkWell(
      onTap: () => onKeyPress(value),
      borderRadius: BorderRadius.circular(12),
      child: Container(
        decoration: BoxDecoration(
          color: Colors.grey.shade50,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: Colors.grey.shade200),
        ),
        child: Center(
          child: icon != null
              ? Icon(icon, color: AppColors.textPrimary)
              : Text(
                  value,
                  style: const TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
                ),
        ),
      ),
    );
  }
}
