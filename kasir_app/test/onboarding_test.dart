import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:kasira_kasir/core/theme/app_theme.dart';
import 'package:kasira_kasir/features/onboarding/presentation/pages/welcome_page.dart';
import 'package:kasira_kasir/features/onboarding/presentation/pages/ready_page.dart';

void main() {
  for (final width in [320.0, 768.0]) {
    testWidgets('Welcome works at width $width with enlarged text',
        (tester) async {
      SharedPreferences.setMockInitialValues({});
      tester.view.physicalSize = Size(width, 700);
      tester.view.devicePixelRatio = 1;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
      final router = GoRouter(initialLocation: '/welcome', routes: [
        GoRoute(path: '/welcome', builder: (_, __) => const WelcomePage()),
        GoRoute(
            path: '/login',
            builder: (_, __) => const Scaffold(body: Text('Akun login'))),
      ]);
      addTearDown(router.dispose);
      await tester.pumpWidget(MaterialApp.router(
          theme: AppTheme.auroraTheme,
          routerConfig: router,
          builder: (context, child) => MediaQuery(
              data: MediaQuery.of(context)
                  .copyWith(textScaler: const TextScaler.linear(1.6)),
              child: child!)));
      await tester.pumpAndSettle();
      expect(tester.takeException(), isNull);
      final button = find.text('Lanjut ke akun');
      await tester.ensureVisible(button);
      await tester.tap(button);
      await tester.pumpAndSettle();
      expect(find.text('Akun login'), findsOneWidget);
      expect(
          (await SharedPreferences.getInstance()).getBool(WelcomePage.prefsKey),
          isTrue);
      expect(tester.takeException(), isNull);
    });
  }

  testWidgets('Ready page scrolls and its primary action opens dashboard',
      (tester) async {
    SharedPreferences.setMockInitialValues({});
    tester.view.physicalSize = const Size(320, 600);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    final router = GoRouter(initialLocation: '/ready', routes: [
      GoRoute(path: '/ready', builder: (_, __) => const ReadyPage()),
      GoRoute(
          path: '/dashboard',
          builder: (_, __) => const Scaffold(body: Text('Dashboard usaha'))),
    ]);
    addTearDown(router.dispose);
    await tester.pumpWidget(MaterialApp.router(
        theme: AppTheme.auroraTheme,
        routerConfig: router,
        builder: (context, child) => MediaQuery(
            data: MediaQuery.of(context)
                .copyWith(textScaler: const TextScaler.linear(1.6)),
            child: child!)));
    await tester.pumpAndSettle();
    expect(tester.takeException(), isNull);
    await tester.ensureVisible(find.text('Buka Beranda'));
    await tester.tap(find.text('Buka Beranda'));
    await tester.pumpAndSettle();
    expect(find.text('Dashboard usaha'), findsOneWidget);
    expect((await SharedPreferences.getInstance()).getBool(ReadyPage.prefsKey),
        isTrue);
    expect(tester.takeException(), isNull);
  });
}
