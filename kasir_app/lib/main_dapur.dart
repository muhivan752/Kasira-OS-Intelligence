import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'core/config/app_config.dart';
import 'core/theme/app_theme.dart';
import 'features/dapur/presentation/pages/dapur_splash_page.dart';
import 'features/dapur/presentation/pages/dapur_login_page.dart';
import 'features/dapur/presentation/pages/dapur_dashboard_page.dart';
import 'features/dapur/presentation/pages/dapur_completed_page.dart';
import 'features/dapur/presentation/pages/dapur_statistik_page.dart';
import 'features/dapur/presentation/pages/dapur_settings_page.dart';
import 'features/onboarding/presentation/pages/server_setup_page.dart';
import 'core/sync/sync_provider.dart';

final _dapurRouter = GoRouter(
  initialLocation: '/dapur',
  routes: [
    GoRoute(
      path: '/dapur',
      builder: (context, state) => const DapurSplashPage(),
    ),
    GoRoute(
      path: '/dapur/login',
      builder: (context, state) => const DapurLoginPage(),
    ),
    GoRoute(
      path: '/dapur/dashboard',
      builder: (context, state) => const DapurDashboardPage(),
    ),
    GoRoute(
      path: '/dapur/completed',
      builder: (context, state) => const DapurCompletedPage(),
    ),
    GoRoute(
      path: '/dapur/statistik',
      builder: (context, state) => const DapurStatistikPage(),
    ),
    GoRoute(
      path: '/dapur/settings',
      builder: (context, state) => const DapurSettingsPage(),
    ),
    // Reuse main app's server setup page
    GoRoute(
      path: '/setup',
      builder: (context, state) => const ServerSetupPage(),
    ),
  ],
);

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  final prefs = await SharedPreferences.getInstance();
  await AppConfig.init(prefs);

  runApp(
    ProviderScope(
      overrides: [
        sharedPreferencesProvider.overrideWithValue(prefs),
      ],
      child: const KasiraDapurApp(),
    ),
  );
}

class KasiraDapurApp extends StatelessWidget {
  const KasiraDapurApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp.router(
      title: 'Kasira Dapur',
      theme: AppTheme.lightTheme.copyWith(
        // Override scaffold background to dark for kitchen mode
        scaffoldBackgroundColor: const Color(0xFF0F0F1A),
        appBarTheme: AppTheme.lightTheme.appBarTheme.copyWith(
          backgroundColor: const Color(0xFF1A1A2E),
          foregroundColor: Colors.white,
        ),
      ),
      debugShowCheckedModeBanner: false,
      routerConfig: _dapurRouter,
    );
  }
}
