import 'dart:async';
import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:dio/dio.dart';
import 'package:go_router/go_router.dart';
import '../../../../core/config/app_config.dart';
import '../../../../core/theme/kasira_ds.dart';
import '../../../../core/widgets/selaris_mark.dart';
import '../../../../core/widgets/sefrekuensi_otp_card.dart';
import '../../../../core/services/location_service.dart';
import '../../../../core/services/session_cache.dart';
import '../../../../core/services/google_auth_service.dart';
import '../../../../core/sync/sync_provider.dart';

// --- STATE ---
enum AuthStep { inputPassword, inputPhone, inputOtp, setPin, pinLogin }

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
  // Kanal kode masuk yang DIPILIH user: 'whatsapp' | 'sefrekuensi'. Kirim
  // ulang pakai kanal yang sama, kode nggak loncat. Layar OTP baca ini buat
  // nyuruh periksa apa.
  final String channel;
  // Server bilang nomornya belum ada di Sefrekuensi: kartu ganti wujud
  // jadi ajakan pasang + tombol "kirim WA saja", bukan pesan error merah.
  final bool sefreNotFound;
  final bool sefreLoading;

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
    this.channel = 'sefrekuensi',
    this.sefreNotFound = false,
    this.sefreLoading = false,
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
    String? channel,
    bool? sefreNotFound,
    bool? sefreLoading,
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
      channel: channel ?? this.channel,
      sefreNotFound: sefreNotFound ?? this.sefreNotFound,
      sefreLoading: sefreLoading ?? this.sefreLoading,
    );
  }
}

// --- PROVIDER ---
final authProvider = StateNotifierProvider<AuthNotifier, AuthState>((ref) {
  return AuthNotifier(ref: ref);
});

class AuthNotifier extends StateNotifier<AuthState> {
  AuthNotifier({bool restoreSession = true, Ref? ref, Dio? client})
      : _sessionRef = ref,
        _client = client,
        super(AuthState()) {
    if (restoreSession) _checkInitialState();
  }

  final _storage = const FlutterSecureStorage();
  final Ref? _sessionRef;
  final Dio? _client;
  Dio get _dio =>
      _client ??
      Dio(BaseOptions(
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

  Future<void> acceptGoogleSession(Map<String, dynamic> data) async {
    final cache = SessionCache.instance;
    final phone = data['phone']?.toString() ?? '';
    String? userId = data['user_id']?.toString();
    if (userId == null) {
      final claims = jsonDecode(utf8.decode(base64Url.decode(base64Url
          .normalize((data['access_token'] as String).split('.')[1])))) as Map;
      userId = claims['sub']?.toString();
    }
    if (userId == null || userId.isEmpty)
      throw StateError('Identitas akun tidak tersedia');
    final nextMode =
        (data['access'] as Map?)?['enforcement_mode']?.toString() ?? 'legacy';
    if (cache.userId != userId ||
        cache.tenantId != data['tenant_id'] ||
        cache.accessMode != nextMode) {
      final sessionRef = _sessionRef;
      if (cache.accessToken != null && sessionRef != null) {
        try {
          final sync = sessionRef.read(syncServiceProvider);
          sync.cancelInFlight();
          sync.resetState();
          sessionRef.invalidate(syncServiceProvider);
        } catch (_) {
          if (kDebugMode)
            debugPrint('Auth: sync belum diinisialisasi saat pergantian akun.');
        }
      }
      await cache.clear();
      await _storage.delete(key: 'user_pin');
    }
    await cache.setAccessToken(data['access_token'] as String);
    await cache.setUserId(userId);
    cache.accessMode =
        (data['access'] as Map?)?['enforcement_mode']?.toString() ?? 'legacy';
    await _storage.write(key: 'access_mode', value: cache.accessMode);
    await cache.setPhone(phone);
    await cache.setTenantId(data['tenant_id'] as String);
    await cache.applyAccess(Map<String, dynamic>.from(
        (data['access'] as Map?) ?? {'enforcement_mode': 'legacy'}));
    await cache.setOutletId(data['outlet_id']?.toString() ?? '');
    await cache.setStockMode(data['stock_mode']?.toString() ?? 'simple');
    await cache.setSubscriptionTier(
        data['subscription_tier']?.toString() ?? 'starter');
    final pin = await _storage.read(key: 'user_pin');
    state = state.copyWith(
        phone: phone,
        isLoading: false,
        clearError: true,
        step: pin == null ? AuthStep.setPin : AuthStep.pinLogin,
        isSuccess: false,
        pinAttempts: 0,
        isLocked: false,
        firstPin: '');
  }

  /// Masuk dengan nomor HP/username + password, TANPA username toko (9 Okt 2026).
  /// Server mencari tokonya. Kalau nomor itu terdaftar di beberapa toko,
  /// kembalikan daftar tokonya; layar memanggil lagi dengan [tenantId].
  Future<List<Map<String, dynamic>>?> loginPassword(
      String username, String password, {String? tenantId}) async {
    state = state.copyWith(isLoading: true, clearError: true);
    try {
      final response = await _dio.post('/api/v1/auth/password/login', data: {
        'username': username.trim(),
        'password': password,
        if (tenantId != null) 'tenant_id': tenantId,
      });
      final data = Map<String, dynamic>.from(response.data['data'] as Map);
      if (data['choose_shop'] == true) {
        state = state.copyWith(isLoading: false);
        return (data['shops'] as List)
            .map((e) => Map<String, dynamic>.from(e as Map))
            .toList();
      }
      await acceptGoogleSession(data);
    } on DioException catch (error) {
      state = state.copyWith(
          isLoading: false,
          error: otpErrorMessage(error.response?.data?['detail'],
              'Belum dapat masuk. Periksa koneksi lalu coba lagi.'));
    } catch (_) {
      state = state.copyWith(
          isLoading: false, error: 'Akun belum dapat dibuka. Coba lagi.');
    }
    return null;
  }

  void usePasswordInstead() {
    state = state.copyWith(
        step: AuthStep.inputPassword,
        isLoading: false,
        isSuccess: false,
        clearError: true);
  }

  /// [channel] null = pakai kanal yang lagi dipilih di state (buat kirim
  /// ulang). Sefrekuensi loading-nya dipisah supaya tombol WhatsApp nggak
  /// ikut muter waktu yang ditekan kartu Sefrekuensi.
  Future<void> sendOtp({String? channel}) async {
    if (state.phone.isEmpty ||
        state.phone.length < 10 ||
        !state.phone.startsWith('628')) {
      state = state.copyWith(
          error: 'Format nomor HP tidak valid (harus 628xxx dan min 10 digit)');
      return;
    }
    final via = channel ?? state.channel;
    final lewatSefre = via == 'sefrekuensi';

    state = state.copyWith(
      isLoading: !lewatSefre,
      sefreLoading: lewatSefre,
      sefreNotFound: false,
      clearError: true,
    );

    try {
      final response = await _dio.post('/api/v1/auth/otp/send',
          data: {'phone': state.phone, 'channel': via});
      String got = 'whatsapp';
      try {
        final respData = response.data is String
            ? json.decode(response.data as String) as Map<String, dynamic>
            : response.data as Map<String, dynamic>;
        got = (respData['data'] as Map?)?['channel']?.toString() ?? 'whatsapp';
      } catch (_) {}

      state = state.copyWith(
        step: AuthStep.inputOtp,
        isLoading: false,
        sefreLoading: false,
        channel: got,
        countdown: 300,
        canResendOtp: false,
      );
      _startTimer();
    } on DioException catch (e) {
      dynamic detail;
      try {
        detail = e.response?.data['detail'];
      } catch (_) {}
      if (otpErrorCode(detail) == kSefrekuensiNotFoundCode) {
        state = state.copyWith(
            isLoading: false, sefreLoading: false, sefreNotFound: true);
        return;
      }
      final errMsg = otpErrorMessage(detail,
          '[${e.type.name}] ${e.message ?? e.error?.toString() ?? 'no message'}');
      state =
          state.copyWith(isLoading: false, sefreLoading: false, error: errMsg);
    } catch (e) {
      final msg = e.toString();
      state = state.copyWith(
          isLoading: false,
          sefreLoading: false,
          error: 'Exception: ${msg.length > 80 ? msg.substring(0, 80) : msg}');
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
      final response = await _dio.post('/api/v1/auth/otp/verify',
          data: {'phone': state.phone, 'otp': otp});

      final respData = response.data is String
          ? json.decode(response.data as String) as Map<String, dynamic>
          : response.data as Map<String, dynamic>;
      final data = respData['data'] as Map<String, dynamic>;
      final token = data['access_token']?.toString() ?? '';

      if (token.isEmpty) {
        state = state.copyWith(
            isLoading: false, error: 'Token tidak ditemukan dalam response');
        return;
      }

      await acceptGoogleSession(data);

      _timer?.cancel();

      final savedPin = await _storage.read(key: 'user_pin');
      if (savedPin != null && savedPin.isNotEmpty) {
        state = state.copyWith(isLoading: false, isSuccess: true);
      } else {
        state = state.copyWith(
            step: AuthStep.setPin, isLoading: false, firstPin: '');
      }
    } on DioException catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: otpErrorMessage(
            e.response?.data?['detail'], 'Kode OTP salah atau kedaluwarsa'),
      );
    } catch (e, stack) {
      // Jejaknya dibuang = bug abadi (CLAUDE.md gotcha #20). Dikurung kDebugMode
      // biar gak bocor ke logcat HP pemilik warung di build rilis.
      if (kDebugMode) {
        debugPrint('[AUTH] verifyOtp error: $e');
        debugPrint('[AUTH] stack: $stack');
      }
      state = state.copyWith(
          isLoading: false, error: 'Terjadi kesalahan sistem: $e');
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
        // PIN benar → init cache + langsung masuk (jangan block UI)
        await SessionCache.instance.init();
        final token = SessionCache.instance.accessToken;
        if (token != null) {
          try {
            final res = await Dio(BaseOptions(
              baseUrl: AppConfig.apiV1,
              connectTimeout: const Duration(seconds: 3),
              receiveTimeout: const Duration(seconds: 3),
            )).get('/auth/access',
                options: Options(headers: {'Authorization': 'Bearer $token'}));
            await SessionCache.instance.applyAccess(
                Map<String, dynamic>.from(res.data['data'] as Map));
          } on DioException catch (error) {
            if (error.response != null) {
              state = state.copyWith(
                  step: AuthStep.inputPassword,
                  isLoading: false,
                  error: otpErrorMessage(error.response?.data?['detail'],
                      'Masuk kembali untuk memperbarui akses akun.'));
              return;
            }
            if (!SessionCache.instance.offlinePosAllowed) {
              state = state.copyWith(
                  isLoading: false,
                  error:
                      'Akun staf perlu koneksi internet untuk memeriksa izin. Antrean transaksi tetap tersimpan.');
              return;
            }
          }
        } else {
          usePasswordInstead();
          return;
        }
        state =
            state.copyWith(isLoading: false, pinAttempts: 0, isSuccess: true);
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
        pinAttempts: 0);
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
  final _otpController = TextEditingController();
  final _usernameController = TextEditingController();
  final _passwordController = TextEditingController();
  bool _otpOpen = false;

  String _pinInput = '';
  bool _isConfirmingPin = false;
  bool _googleAvailable = false;
  bool _checkingGoogle = true;

  @override
  void initState() {
    super.initState();
    _loadGoogle();
  }

  Future<void> _loadGoogle() async {
    try {
      final response = await Dio(BaseOptions(
              baseUrl: AppConfig.apiV1,
              connectTimeout: const Duration(seconds: 10),
              receiveTimeout: const Duration(seconds: 10)))
          .get('/auth/providers');
      final enabled = response.data['data']['google']['enabled'] == true;
      final firebase = enabled && await GoogleAuthService.available();
      if (mounted) {
        setState(() => _googleAvailable = firebase);
      }
    } catch (_) {
    } finally {
      if (mounted) setState(() => _checkingGoogle = false);
    }
  }

  @override
  void dispose() {
    _phoneController.dispose();
    _otpController.dispose();
    _usernameController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  Future<void> _checkShiftAndNavigate(BuildContext context) async {
    try {
      // Init cache if not already (e.g. PIN login path)
      final cache = SessionCache.instance;
      if (!cache.isInitialized) await cache.init();
      final token = cache.accessToken;
      final tenantId = cache.tenantId;
      final outletId = cache.outletId;
      if (cache.accessMode == 'managed') {
        if (context.mounted)
          context.go(cache.allows('pos.sell') ||
                  cache.allows('stock.view') ||
                  cache.allows('sales.detail.view') || cache.allows('pos.shift.manage') || cache.allows('pos.cash.manage') || cache.allows('pos.refund') || cache.allows('pos.refund.approve') || cache.allows('pos.kitchen')
              ? '/dashboard'
              : '/team');
        return;
      }
      LocationService.sendLocationSilent();

      // debugPrint('[NAV] checkShift: token=${token != null ? "yes" : "null"} tenant=$tenantId outlet=$outletId');

      if (outletId == null || outletId.isEmpty) {
        // debugPrint('[NAV] No outlet_id — going to shift/open');
        if (context.mounted) context.go('/shift/open');
        return;
      }

      final dio = Dio(BaseOptions(
        baseUrl: AppConfig.apiV1,
        connectTimeout: const Duration(seconds: 10),
        receiveTimeout: const Duration(seconds: 10),
      ));

      // Identitas akun buat order offline (lihat SessionCache.ensureUserId).
      await cache.ensureUserId();

      final response = await dio.get(
        '/shifts/current',
        queryParameters: {'outlet_id': outletId},
        options: Options(headers: {
          if (token != null) 'Authorization': 'Bearer $token',
          if (tenantId != null) 'X-Tenant-ID': tenantId,
        }),
      );

      final data = response.data['data'];
      // debugPrint('[NAV] shift response: status=${data?['status']}');
      if (!context.mounted) return;
      // Shift otomatis (2 Sep 2026): nggak ada sesi terbuka BUKAN alasan
      // menghadang kasir di halaman "Buka shift". Sesi terbuka sendiri di
      // transaksi pertama; modal awal bisa diisi kapan saja dari Beranda.
      final mode = data?['shift_mode']?.toString();
      if (mode != null && mode.isNotEmpty) cache.shiftMode = mode;
      if (data != null && data['status'] == 'open') {
        cache.setShiftSessionId(data['id']);
        context.go('/dashboard');
      } else {
        cache.setShiftSessionId(null);
        // Profil Ketat: serah terima modal awal itu wajib, jadi di sini
        // memang diarahkan ke halaman buka kasir. Profil lain langsung Beranda.
        context.go(cache.shiftMode == 'ketat' ? '/shift/open' : '/dashboard');
      }
    } catch (e) {
      // Gagal cek shift (offline, timeout) juga bukan alasan menghadang.
      if (context.mounted) context.go('/dashboard');
    }
  }

  @override
  Widget build(BuildContext context) {
    final authState = ref.watch(authProvider);

    ref.listen<AuthState>(authProvider, (previous, next) {
      if (next.isSuccess && (previous?.isSuccess != true)) {
        // debugPrint('[AUTH] isSuccess → navigating...');
        _checkShiftAndNavigate(context);
      }
      if (next.step == AuthStep.setPin && previous?.step != AuthStep.setPin) {
        setState(() {
          _pinInput = '';
          _isConfirmingPin = false;
        });
      }
      if (next.error != null && next.error != previous?.error) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(next.error!),
            backgroundColor: KasiraDS.danger,
            behavior: SnackBarBehavior.floating,
          ),
        );
      }
    });

    if (authState.isSuccess) {
      return Scaffold(
        backgroundColor: KasiraDS.brandPrimary,
        body: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Icon(Icons.check_circle_outline,
                  color: Colors.white, size: 64),
              const SizedBox(height: 16),
              const Text('Login berhasil!',
                  style: TextStyle(
                      color: Colors.white,
                      fontSize: 20,
                      fontWeight: FontWeight.bold)),
              const SizedBox(height: 8),
              const Text('Menyiapkan...',
                  style: TextStyle(color: Colors.white70, fontSize: 14)),
              const SizedBox(height: 24),
              const CircularProgressIndicator(color: Colors.white),
            ],
          ),
        ),
      );
    }

    if (authState.isLoading &&
        authState.step == AuthStep.pinLogin &&
        _pinInput.isEmpty) {
      return const Scaffold(
        backgroundColor: KasiraDS.brandPrimary,
        body: Center(child: CircularProgressIndicator(color: Colors.white)),
      );
    }

    return Scaffold(
      backgroundColor: KasiraDS.bgBase,
      body: SafeArea(
          child: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 24),
          child: Container(
            constraints: const BoxConstraints(maxWidth: 440),
            width: double.infinity,
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(
              color: KasiraDS.surfaceCard,
              borderRadius: BorderRadius.circular(24),
            ),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                _buildHeader(),
                const SizedBox(height: 32),
                _buildContent(authState),
                if (authState.step == AuthStep.inputPassword ||
                    authState.step == AuthStep.inputPhone ||
                    authState.step == AuthStep.pinLogin) ...[
                  const SizedBox(height: 24),
                  Wrap(
                    alignment: WrapAlignment.center,
                    crossAxisAlignment: WrapCrossAlignment.center,
                    children: [
                      Text('Belum punya akun? ',
                          style: TextStyle(
                              color: KasiraDS.textMuted, fontSize: 13)),
                      TextButton(
                        onPressed: () => context.go('/register'),
                        child: const Text('Daftar Gratis',
                            style: TextStyle(
                                color: KasiraDS.brandPrimary,
                                fontSize: 13,
                                fontWeight: FontWeight.w600)),
                      ),
                    ],
                  ),
                ],
              ],
            ),
          ),
        ),
      )),
    );
  }

  Widget _buildHeader() {
    return Row(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        const SelarisMark(size: 36),
        const SizedBox(width: 10),
        Flexible(
            child: FittedBox(
                fit: BoxFit.scaleDown,
                child: Text('Selaris',
                    style: KasiraDS.display(
                        size: 26, color: KasiraDS.textStrong)))),
      ],
    );
  }

  Widget _buildContent(AuthState state) {
    switch (state.step) {
      case AuthStep.inputPassword:
        return _buildPassword(state);
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

  Widget _buildPassword(AuthState state) {
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Text('Masuk ke toko Anda',
          style: KasiraDS.display(size: 22, color: KasiraDS.textStrong)),
      const SizedBox(height: 16),
      _passwordForm(state),
      TextButton(
          onPressed: state.isLoading
              ? null
              : () => ref.read(authProvider.notifier).useOtpInstead(),
          child: const Text('Masuk dengan Google atau kode Sefrekuensi')),
    ]);
  }

  // Nomor HP/username + password, satu-satunya isian karyawan. Username toko
  // dan centang "saya karyawan" dihapus 9 Okt 2026: server yang mencari tokonya.
  Widget _passwordForm(AuthState state) {
    return AutofillGroup(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      TextField(
          controller: _usernameController,
          enabled: !state.isLoading,
          autocorrect: false,
          textCapitalization: TextCapitalization.none,
          autofillHints: const [AutofillHints.username],
          decoration:
              const InputDecoration(labelText: 'Nomor HP atau username'),
          textInputAction: TextInputAction.next),
      const SizedBox(height: 8),
      TextField(
          controller: _passwordController,
          enabled: !state.isLoading,
          obscureText: true,
          autofillHints: const [AutofillHints.password],
          decoration: const InputDecoration(labelText: 'Password'),
          onSubmitted: (_) => _passwordLogin()),
      const SizedBox(height: 16),
      SizedBox(
          width: double.infinity,
          child: FilledButton(
              onPressed: state.isLoading ? null : _passwordLogin,
              child: Text(state.isLoading ? 'Memproses…' : 'Masuk'))),
      const SizedBox(height: 8),
      Text('Lupa password? Minta pemilik toko membuat yang baru.',
          style: KasiraDS.sans(size: 12.5, color: KasiraDS.textMuted)),
    ]));
  }

  Future<void> _passwordLogin({String? tenantId}) async {
    if (_usernameController.text.trim().isEmpty ||
        _passwordController.text.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(
          content: Text('Isi nomor HP atau username, dan password.')));
      return;
    }
    final shops = await ref.read(authProvider.notifier).loginPassword(
        _usernameController.text, _passwordController.text,
        tenantId: tenantId);
    if (shops == null || !mounted) return;
    final picked = await showModalBottomSheet<String>(
        context: context,
        showDragHandle: true,
        builder: (sheet) => SafeArea(
                child: Column(mainAxisSize: MainAxisSize.min, children: [
              Padding(
                  padding: const EdgeInsets.fromLTRB(20, 0, 20, 8),
                  child: Text('Pilih toko',
                      style: KasiraDS.display(
                          size: 20, color: KasiraDS.textStrong))),
              for (final shop in shops)
                ListTile(
                    leading: const Icon(Icons.storefront_outlined),
                    title: Text('${shop['name']}'),
                    subtitle: shop['owner'] == true
                        ? const Text('Pemilik')
                        : null,
                    onTap: () =>
                        Navigator.pop(sheet, '${shop['tenant_id']}')),
              const SizedBox(height: 8),
            ])));
    if (picked != null && mounted) await _passwordLogin(tenantId: picked);
  }

  // Layar pertama (9 Okt 2026): tiga cara masuk terlihat sekaligus. Google dan
  // kode Sefrekuensi untuk pemilik, nomor HP/username + password untuk karyawan.
  Widget _buildInputPhone(AuthState state) {
    if (_otpOpen) return _buildOtpPhone(state);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text('Masuk ke toko Anda',
            style: KasiraDS.display(size: 22, color: KasiraDS.textStrong)),
        const SizedBox(height: 20),
        SizedBox(
            width: double.infinity,
            child: OutlinedButton.icon(
              onPressed: _googleAvailable ? () => context.go('/google') : null,
              icon: const Icon(Icons.account_circle_outlined),
              label: const Text('Lanjut dengan Google'),
            )),
        if (_checkingGoogle) ...[
          const SizedBox(height: 8),
          Text('Menyiapkan pilihan login…',
              style: KasiraDS.sans(size: 13, color: KasiraDS.textMuted)),
        ] else if (!_googleAvailable) ...[
          const SizedBox(height: 8),
          Text('Google belum tersedia. Gunakan kode Sefrekuensi.',
              style: KasiraDS.sans(size: 13, color: KasiraDS.textMuted)),
        ],
        const SizedBox(height: 10),
        SizedBox(
            width: double.infinity,
            child: OutlinedButton.icon(
              onPressed: state.isLoading
                  ? null
                  : () => setState(() => _otpOpen = true),
              icon: const Icon(Icons.sms_outlined),
              label: Text('Kode dari $kSefrekuensiName'),
            )),
        const SizedBox(height: 20),
        Row(children: [
          const Expanded(child: Divider()),
          Padding(
              padding: const EdgeInsets.symmetric(horizontal: 10),
              child: Text('atau nomor HP dan password',
                  style: KasiraDS.sans(size: 12, color: KasiraDS.textMuted))),
          const Expanded(child: Divider()),
        ]),
        const SizedBox(height: 12),
        _passwordForm(state),
      ],
    );
  }

  Widget _buildOtpPhone(AuthState state) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        TextButton.icon(
            onPressed: state.isLoading || state.sefreLoading
                ? null
                : () => setState(() => _otpOpen = false),
            icon: const Icon(Icons.arrow_back, size: 18),
            label: const Text('Kembali')),
        const SizedBox(height: 8),
        Text('Nomor HP Anda',
            style: KasiraDS.display(size: 22, color: KasiraDS.textStrong)),
        const SizedBox(height: 6),
        Text('Kode masuk dikirim ke $kSefrekuensiName, atau WhatsApp sebagai cadangan.',
            style: KasiraDS.sans(size: 13.5, color: KasiraDS.textMuted)),
        const SizedBox(height: 20),
        Text('NOMOR HP', style: KasiraDS.eyebrow()),
        const SizedBox(height: 6),
        // Prefix +62 tetap, user ketik tanpa 0. Yang dikirim ke server tetap
        // "628…" (provider nerima format lama). Nol di depan dibuang otomatis.
        TextField(
          controller: _phoneController,
          keyboardType: TextInputType.phone,
          inputFormatters: [FilteringTextInputFormatter.digitsOnly],
          style: KasiraDS.sans(
              size: 17, weight: FontWeight.w600, color: KasiraDS.textStrong),
          decoration: InputDecoration(
            hintText: '812 3456 7890',
            prefixIcon: Padding(
              padding: const EdgeInsets.only(left: 14, right: 8),
              child: Text('🇮🇩 +62',
                  style: KasiraDS.sans(
                      size: 15,
                      weight: FontWeight.w600,
                      color: KasiraDS.textMuted)),
            ),
            prefixIconConstraints:
                const BoxConstraints(minWidth: 0, minHeight: 0),
            filled: true,
            fillColor: KasiraDS.surfaceCard,
            border: OutlineInputBorder(
                borderRadius: KasiraDS.brMd,
                borderSide: const BorderSide(color: KasiraDS.controlBorder)),
            enabledBorder: OutlineInputBorder(
                borderRadius: KasiraDS.brMd,
                borderSide: const BorderSide(color: KasiraDS.controlBorder)),
            focusedBorder: OutlineInputBorder(
                borderRadius: KasiraDS.brMd,
                borderSide:
                    const BorderSide(color: KasiraDS.brandPrimary, width: 1.5)),
          ),
          onChanged: (val) {
            var d = val;
            if (d.startsWith('62')) d = d.substring(2);
            while (d.startsWith('0')) {
              d = d.substring(1);
            }
            ref.read(authProvider.notifier).setPhone(d.isEmpty ? '' : '62$d');
          },
        ),
        const SizedBox(height: 10),
        Container(
          padding: const EdgeInsets.all(10),
          decoration: BoxDecoration(
              color: KasiraDS.surfaceSunken, borderRadius: KasiraDS.brSm),
          child: Text(
              'Nomor ini juga jadi nomor WA pemilik buat struk & laporan pagi.',
              style: KasiraDS.sans(size: 11.5, color: KasiraDS.textBody)),
        ),
        const SizedBox(height: 20),
        SizedBox(
          width: double.infinity,
          child: FilledButton(
            onPressed: (state.isLoading || state.sefreLoading)
                ? null
                : () => ref
                    .read(authProvider.notifier)
                    .sendOtp(channel: 'sefrekuensi'),
            style: FilledButton.styleFrom(
              backgroundColor: KasiraDS.brandFill,
              foregroundColor: KasiraDS.onBrandFill,
              shape: RoundedRectangleBorder(borderRadius: KasiraDS.brMd),
            ),
            child: (state.isLoading || state.sefreLoading)
                ? const SizedBox(
                    width: 22,
                    height: 22,
                    child: CircularProgressIndicator(
                        color: KasiraDS.onBrandFill, strokeWidth: 2))
                : Text('Kirim kode ke Sefrekuensi',
                    style: KasiraDS.sans(
                        size: 15.5,
                        weight: FontWeight.w700,
                        color: KasiraDS.onBrandFill)),
          ),
        ),
        const SizedBox(height: 12),
        if (state.sefreNotFound)
          SefrekuensiOtpCard(
            loading: state.isLoading || state.sefreLoading,
            notFound: state.sefreNotFound,
            onPick: () =>
                ref.read(authProvider.notifier).sendOtp(channel: 'sefrekuensi'),
            onFallbackWhatsapp: () =>
                ref.read(authProvider.notifier).sendOtp(channel: 'whatsapp'),
          ),
        if (!state.sefreNotFound)
          TextButton(
            onPressed: (state.isLoading || state.sefreLoading)
                ? null
                : () => ref
                    .read(authProvider.notifier)
                    .sendOtp(channel: 'whatsapp'),
            child: const Text('Gunakan WhatsApp'),
          ),
      ],
    );
  }

  Widget _buildInputOtp(AuthState state) {
    final lewatSefre = state.channel == 'sefrekuensi';
    final minutes = (state.countdown / 60).floor();
    final seconds = state.countdown % 60;
    final timeString =
        '${minutes.toString().padLeft(2, '0')}:${seconds.toString().padLeft(2, '0')}';

    return Column(
      children: [
        Text(
            lewatSefre
                ? 'Periksa $kSefrekuensiName Anda'
                : 'Periksa WhatsApp Anda',
            style: KasiraDS.display(size: 22, color: KasiraDS.textStrong)),
        const SizedBox(height: 6),
        Text(
          lewatSefre
              ? 'Kode 6 angka dikirim sebagai pesan dari Yasmin ke +${state.phone}'
              : 'Kode 6 angka dikirim ke WhatsApp +${state.phone}',
          style: KasiraDS.sans(size: 13.5, color: KasiraDS.textMuted),
          textAlign: TextAlign.center,
        ),
        const SizedBox(height: 24),
        TextField(
          controller: _otpController,
          enabled: !state.isLoading,
          keyboardType: TextInputType.number,
          autofillHints: const [AutofillHints.oneTimeCode],
          inputFormatters: [FilteringTextInputFormatter.digitsOnly],
          textAlign: TextAlign.center,
          maxLength: 6,
          style: KasiraDS.mono(size: 24, weight: FontWeight.w700),
          decoration:
              const InputDecoration(labelText: 'Kode 6 angka', counterText: ''),
          onChanged: (_) => setState(() {}),
        ),
        const SizedBox(height: 16),
        SizedBox(
            width: double.infinity,
            child: FilledButton(
              onPressed: state.isLoading || _otpController.text.length != 6
                  ? null
                  : () => ref
                      .read(authProvider.notifier)
                      .verifyOtp(_otpController.text),
              child: const Text('Verifikasi kode'),
            )),
        const SizedBox(height: 24),
        if (state.isLoading)
          const CircularProgressIndicator()
        else
          Column(
            children: [
              Text(timeString,
                  style: const TextStyle(
                      fontWeight: FontWeight.bold, fontSize: 18)),
              const SizedBox(height: 8),
              TextButton(
                onPressed: state.canResendOtp
                    ? () {
                        _otpController.clear();
                        ref.read(authProvider.notifier).sendOtp();
                      }
                    : null,
                child: Text(
                  lewatSefre
                      ? 'Belum dapat? Kirim ulang ke $kSefrekuensiName'
                      : 'Belum dapat? Kirim ulang',
                  style: TextStyle(
                      color: state.canResendOtp
                          ? KasiraDS.brandPrimary
                          : Colors.grey),
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
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
          decoration: BoxDecoration(
            color: KasiraDS.brandPrimary.withOpacity(0.1),
            borderRadius: BorderRadius.circular(8),
          ),
          child: const Text(
            'Akun terverifikasi',
            style: TextStyle(
                color: KasiraDS.brandPrimary,
                fontWeight: FontWeight.w600,
                fontSize: 13),
          ),
        ),
        const SizedBox(height: 16),
        Text(
          _isConfirmingPin ? 'Konfirmasi PIN' : 'Buat PIN Baru',
          style: Theme.of(context)
              .textTheme
              .titleLarge
              ?.copyWith(fontWeight: FontWeight.bold),
        ),
        const SizedBox(height: 8),
        Text(
          _isConfirmingPin
              ? 'Masukkan ulang PIN 6 digit Anda'
              : 'PIN digunakan untuk login cepat berikutnya',
          style: const TextStyle(color: KasiraDS.textMuted),
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
                  ref
                      .read(authProvider.notifier)
                      .confirmPin(_pinInput)
                      .then((_) {
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
          style: Theme.of(context)
              .textTheme
              .titleLarge
              ?.copyWith(fontWeight: FontWeight.bold),
        ),
        const SizedBox(height: 8),
        Text(
          state.isLocked ? 'Akun terkunci' : 'Masukkan PIN 6 digit Anda',
          style: TextStyle(
              color: state.isLocked ? KasiraDS.danger : KasiraDS.textMuted),
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
                ref
                    .read(authProvider.notifier)
                    .loginWithPin(_pinInput)
                    .then((_) {
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
              style: TextStyle(color: KasiraDS.brandPrimary),
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
            color:
                index < length ? KasiraDS.brandPrimary : KasiraDS.borderSubtle,
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
        for (var i = 1; i <= 9; i++)
          _buildKeypadButton(i.toString(), onKeyPress),
        const SizedBox(),
        _buildKeypadButton('0', onKeyPress),
        _buildKeypadButton('del', onKeyPress, icon: Icons.backspace_outlined),
      ],
    );
  }

  Widget _buildKeypadButton(String value, Function(String) onKeyPress,
      {IconData? icon}) {
    return InkWell(
      onTap: () => onKeyPress(value),
      borderRadius: BorderRadius.circular(12),
      child: Container(
        decoration: BoxDecoration(
          color: KasiraDS.surfaceSunken,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: KasiraDS.borderSubtle),
        ),
        child: Center(
          child: icon != null
              ? Icon(icon, color: KasiraDS.textStrong)
              : Text(
                  value,
                  style: const TextStyle(
                      fontSize: 24, fontWeight: FontWeight.bold),
                ),
        ),
      ),
    );
  }
}
