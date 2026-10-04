import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:kasira_kasir/core/theme/app_theme.dart';
import 'package:kasira_kasir/features/auth/presentation/pages/login_page.dart';
import 'package:kasira_kasir/features/auth/presentation/pages/register_page.dart';

class TestAuthNotifier extends AuthNotifier {
  TestAuthNotifier(AuthState snapshot) : super(restoreSession: false) {
    state = snapshot;
  }
  String? sentChannel;
  String? enteredOtp;

  @override
  Future<void> sendOtp({String? channel}) async {
    sentChannel = channel;
    state = state.copyWith(
        step: AuthStep.inputOtp, channel: channel, isLoading: false);
  }

  @override
  Future<void> verifyOtp(String otp) async {
    enteredOtp = otp;
  }
}

void main() {
  testWidgets('Google onboarding phone stays fixed and fits enlarged text',
      (tester) async {
    tester.view.physicalSize = const Size(320, 760);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    await tester.pumpWidget(MaterialApp(
        theme: AppTheme.auroraTheme,
        home: const RegisterPage(
            phone: '628111111111',
            ownerName: 'Owner',
            googleProof: 'pending-proof'),
        builder: (context, child) => MediaQuery(
            data: MediaQuery.of(context)
                .copyWith(textScaler: const TextScaler.linear(1.6)),
            child: child!)));
    await tester.pumpAndSettle();
    final phone = tester.widget<TextField>(find.byType(TextField).first);
    expect(phone.readOnly, isTrue);
    expect(phone.controller!.text, '8111111111');
    await tester.ensureVisible(find.text('Buat usaha'));
    await tester.tap(find.text('Buat usaha'));
    await tester.pumpAndSettle();
    expect(find.text('Nama usaha harus diisi'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });
  for (final step in AuthStep.values) {
    testWidgets('Login $step fits 320px with enlarged text', (tester) async {
      tester.view.physicalSize = const Size(320, 760);
      tester.view.devicePixelRatio = 1;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
      final notifier = TestAuthNotifier(AuthState(
          step: step,
          isLoading: false,
          phone: '628111111111',
          channel: 'sefrekuensi'));
      await tester.pumpWidget(ProviderScope(
          overrides: [authProvider.overrideWith((ref) => notifier)],
          child: MaterialApp(
              theme: AppTheme.auroraTheme,
              home: const LoginPage(),
              builder: (context, child) => MediaQuery(
                  data: MediaQuery.of(context)
                      .copyWith(textScaler: const TextScaler.linear(1.6)),
                  child: child!))));
      await tester.pumpAndSettle();
      expect(tester.takeException(), isNull);
      if (step == AuthStep.inputPhone) {
        await tester.enterText(find.byType(TextField).first, '08111111111');
        await tester.ensureVisible(find.text('Kirim kode ke Sefrekuensi'));
        await tester.tap(find.text('Kirim kode ke Sefrekuensi'));
        await tester.pumpAndSettle();
        expect(notifier.sentChannel, 'sefrekuensi');
        expect(notifier.state.phone, '628111111111');
      }
      if (step == AuthStep.inputOtp) {
        await tester.enterText(find.byType(TextField), '123456');
        await tester.pump();
        expect(notifier.enteredOtp, isNull);
        await tester.ensureVisible(find.text('Verifikasi kode'));
        await tester.tap(find.text('Verifikasi kode'));
        await tester.pumpAndSettle();
        expect(notifier.enteredOtp, '123456');
      }
      expect(tester.takeException(), isNull);
    });
  }
}
