import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import '../../../../core/config/app_config.dart';
import '../../../../core/theme/app_colors.dart';

/// Splash screen for Dapur (Kitchen) app.
/// Checks server config → if not set, redirect to /dapur/setup.
/// Otherwise checks token → if logged in, go to /dapur/dashboard, else /dapur/login.
class DapurSplashPage extends StatefulWidget {
  const DapurSplashPage({super.key});

  @override
  State<DapurSplashPage> createState() => _DapurSplashPageState();
}

class _DapurSplashPageState extends State<DapurSplashPage>
    with SingleTickerProviderStateMixin {
  late AnimationController _animController;
  late Animation<double> _fadeAnim;
  final _storage = const FlutterSecureStorage();

  @override
  void initState() {
    super.initState();
    _animController = AnimationController(
        vsync: this, duration: const Duration(milliseconds: 600));
    _fadeAnim = CurvedAnimation(parent: _animController, curve: Curves.easeIn);
    _animController.forward();
    _init();
  }

  @override
  void dispose() {
    _animController.dispose();
    super.dispose();
  }

  Future<void> _init() async {
    await Future.delayed(const Duration(milliseconds: 1200));
    if (!mounted) return;

    if (!AppConfig.isConfigured) {
      context.go('/setup'); // reuse main app setup page
      return;
    }

    final token = await _storage.read(key: 'access_token');
    if (!mounted) return;

    if (token != null) {
      context.go('/dapur/dashboard');
    } else {
      context.go('/dapur/login');
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF1A1A2E),
      body: FadeTransition(
        opacity: _fadeAnim,
        child: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Container(
                width: 100,
                height: 100,
                decoration: BoxDecoration(
                  color: AppColors.warning.withOpacity(0.15),
                  borderRadius: BorderRadius.circular(28),
                ),
                child: const Icon(
                  Icons.kitchen_rounded,
                  color: AppColors.warning,
                  size: 56,
                ),
              ),
              const SizedBox(height: 24),
              const Text(
                'DAPUR',
                style: TextStyle(
                  color: Colors.white,
                  fontSize: 40,
                  fontWeight: FontWeight.w800,
                  letterSpacing: 4,
                ),
              ),
              const SizedBox(height: 8),
              Text(
                'Kasira Kitchen Display',
                style: TextStyle(
                  color: Colors.white.withOpacity(0.5),
                  fontSize: 14,
                ),
              ),
              const SizedBox(height: 64),
              SizedBox(
                width: 24,
                height: 24,
                child: CircularProgressIndicator(
                  color: AppColors.warning.withOpacity(0.7),
                  strokeWidth: 2,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
