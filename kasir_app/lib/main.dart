import 'dart:async';
import 'dart:ui' as ui;
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:intl/date_symbol_data_local.dart';
import 'core/config/app_config.dart';
import 'core/sync/sync_provider.dart';
import 'core/services/session_cache.dart';
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
import 'features/reservations/presentation/pages/reservation_list_page.dart';
import 'features/reservations/presentation/pages/table_grid_page.dart';
import 'features/tabs/presentation/pages/tab_detail_page.dart';
import 'features/tabs/presentation/pages/active_tabs_list_page.dart';
import 'features/auth/presentation/pages/register_page.dart';

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
      path: '/register',
      builder: (context, state) => const RegisterPage(),
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
      path: '/reservations',
      builder: (context, state) => const ReservationListPage(),
    ),
    GoRoute(
      path: '/reservations/tables',
      builder: (context, state) => const ReservationTableGridPage(),
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
          tax: (extra['tax'] as num?)?.toDouble(),
          serviceCharge: (extra['serviceCharge'] as num?)?.toDouble(),
          discount: (extra['discount'] as num?)?.toDouble(),
          taxInclusive: extra['taxInclusive'] as bool? ?? false,
          customerId: extra['customerId'] as String?,
          customerName: extra['customerName'] as String?,
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
          discount: (extra['discount'] as num?)?.toDouble(),
          taxInclusive: extra['taxInclusive'] as bool? ?? false,
          customerId: extra['customerId'] as String?,
          customerName: extra['customerName'] as String?,
        );
      },
    ),
    GoRoute(
      path: '/stock/alerts',
      builder: (context, state) => const LowStockAlertPage(),
    ),
    GoRoute(
      path: '/tabs',
      builder: (context, state) => const ActiveTabsListPage(),
    ),
    GoRoute(
      path: '/tabs/:tabId',
      builder: (context, state) {
        final tabId = state.pathParameters['tabId'] ?? '';
        return TabDetailPage(tabId: tabId);
      },
    ),
  ],
);

void main() async {
  // Global error boundary — catch uncaught errors sebelum bikin app crash.
  // Kasira dipake kasir di lapangan (Dita Coffee, dll), force-close =
  // potensi kehilangan transaksi. Log + tetep biarin app hidup.
  runZonedGuarded<Future<void>>(() async {
    WidgetsFlutterBinding.ensureInitialized();

    // Framework-level errors (build, layout, paint, widget lifecycle)
    FlutterError.onError = (FlutterErrorDetails details) {
      debugPrint('FlutterError: ${details.exception}');
      debugPrint('Stack: ${details.stack}');
      // Biar default presenter jalan (red screen di debug, silent di release)
      FlutterError.presentError(details);
    };

    // Async uncaught errors yang lolos dari zone (platform channel, dll)
    ui.PlatformDispatcher.instance.onError = (error, stack) {
      debugPrint('PlatformDispatcher uncaught: $error');
      debugPrint('Stack: $stack');
      return true; // mark as handled — jangan propagate ke OS
    };

    await initializeDateFormatting('id_ID', null);
    final prefs = await SharedPreferences.getInstance();
    await AppConfig.init(prefs);

    // Pre-warm session cache from SharedPreferences (fast) + SecureStorage (token only)
    await SessionCache.instance.initFromPrefsCache();

    runApp(
      ProviderScope(
        overrides: [
          sharedPreferencesProvider.overrideWithValue(prefs),
        ],
        child: const KasiraApp(),
      ),
    );
  }, (error, stack) {
    // Zone-level uncaught — async work yang gak di-await + gak di-try/catch
    debugPrint('Zone uncaught: $error');
    debugPrint('Stack: $stack');
  });
}

class KasiraApp extends StatelessWidget {
  const KasiraApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp.router(
      title: 'Kasira POS',
      theme: AppTheme.darkTheme,
      debugShowCheckedModeBanner: false,
      routerConfig: _router,
    );
  }
}
