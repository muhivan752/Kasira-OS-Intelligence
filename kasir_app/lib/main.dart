import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'core/config/app_config.dart';
import 'core/sync/sync_provider.dart';
import 'core/theme/app_theme.dart';
import 'features/auth/presentation/pages/login_page.dart';
import 'features/dashboard/presentation/pages/dashboard_page.dart';
import 'features/onboarding/presentation/pages/server_setup_page.dart';
import 'features/inventory/presentation/pages/low_stock_alert_page.dart';
import 'features/pos/presentation/pages/payment_success_page.dart';
import 'features/pos/presentation/pages/receipt_preview_page.dart';
import 'features/shift/presentation/pages/shift_open_page.dart';
import 'features/splash/presentation/pages/splash_page.dart';
import 'features/tables/presentation/pages/table_grid_page.dart';

final _router = GoRouter(
  initialLocation: '/',
  routes: [
    GoRoute(
      path: '/',
      builder: (context, state) => const SplashPage(),
    ),
    GoRoute(
      path: '/setup',
      builder: (context, state) => const ServerSetupPage(),
    ),
    GoRoute(
      path: '/login',
      builder: (context, state) => const LoginPage(),
    ),
    GoRoute(
      path: '/shift/open',
      builder: (context, state) => const ShiftOpenPage(),
    ),
    GoRoute(
      path: '/dashboard',
      builder: (context, state) => const DashboardPage(),
    ),
    GoRoute(
      path: '/tables',
      builder: (context, state) => const TableGridPage(),
    ),
    GoRoute(
      path: '/payment/success',
      builder: (context, state) {
        final extra = state.extra as Map<String, dynamic>? ?? {};
        return PaymentSuccessPage(
          totalAmount: (extra['totalAmount'] as num?)?.toDouble() ?? 0,
          amountPaid: (extra['amountPaid'] as num?)?.toDouble() ?? 0,
          paymentMethod: extra['paymentMethod'] as String? ?? 'Cash',
          orderId: extra['orderId'] as String? ?? '',
          displayNumber: extra['displayNumber'] as String? ?? '-',
          items: (extra['items'] as List<ReceiptItem>?) ?? [],
        );
      },
    ),
    GoRoute(
      path: '/receipt',
      builder: (context, state) {
        final extra = state.extra as Map<String, dynamic>? ?? {};
        return ReceiptPreviewPage(
          orderId: extra['orderId'] as String? ?? '',
          displayNumber: extra['displayNumber'] as String? ?? '-',
          totalAmount: (extra['totalAmount'] as num?)?.toDouble() ?? 0,
          amountPaid: (extra['amountPaid'] as num?)?.toDouble() ?? 0,
          changeAmount: (extra['changeAmount'] as num?)?.toDouble() ?? 0,
          paymentMethod: extra['paymentMethod'] as String? ?? 'Cash',
          items: (extra['items'] as List<ReceiptItem>?) ?? [],
          outletName: extra['outletName'] as String? ?? 'Kasira Outlet',
          outletAddress: extra['outletAddress'] as String? ?? '',
          tax: (extra['tax'] as num?)?.toDouble(),
          serviceCharge: (extra['serviceCharge'] as num?)?.toDouble(),
        );
      },
    ),
    GoRoute(
      path: '/stock/alerts',
      builder: (context, state) => const LowStockAlertPage(),
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
      child: const KasiraApp(),
    ),
  );
}

class KasiraApp extends StatelessWidget {
  const KasiraApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp.router(
      title: 'Kasira POS',
      theme: AppTheme.lightTheme,
      debugShowCheckedModeBanner: false,
      routerConfig: _router,
    );
  }
}
