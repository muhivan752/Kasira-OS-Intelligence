import 'dart:convert';
import 'dart:typed_data';
import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:kasira_kasir/core/services/session_cache.dart';
import 'package:kasira_kasir/core/theme/app_theme.dart';
import 'package:kasira_kasir/features/auth/presentation/pages/login_page.dart';
import 'package:kasira_kasir/features/auth/presentation/pages/password_account_page.dart';
import 'package:kasira_kasir/features/auth/presentation/pages/team_account_page.dart';

class Adapter implements HttpClientAdapter {
  Adapter(this.respond);
  final Map<String, dynamic> Function(RequestOptions) respond;
  final calls = <RequestOptions>[];
  @override
  Future<ResponseBody> fetch(RequestOptions options, Stream<Uint8List>? stream,
      Future<void>? cancel) async {
    calls.add(options);
    return ResponseBody.fromString(
        jsonEncode({'success': true, 'data': respond(options)}), 200,
        headers: {
          Headers.contentTypeHeader: [Headers.jsonContentType]
        });
  }

  @override
  void close({bool force = false}) {}
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  setUp(() async {
    SharedPreferences.setMockInitialValues({});
    FlutterSecureStorage.setMockInitialValues({});
    await SessionCache.instance.clear();
  });

  test('password login switches by UUID even when both accounts have no phone',
      () async {
    final cache = SessionCache.instance;
    await cache.setUserId('old-user');
    await cache.setTenantId('old-tenant');
    await cache.setAccessToken('old-token');
    await const FlutterSecureStorage().write(key: 'user_pin', value: '123456');
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(
        'hris-punch:old-tenant:old-user', 'preserved-request');
    final adapter = Adapter((request) => {
          'user_id': 'new-user',
          'tenant_id': 'new-tenant',
          'outlet_id': 'new-outlet',
          'access_token': 'new-token',
          'phone': null,
          'access': {'enforcement_mode': 'managed'}
        });
    final client = Dio()..httpClientAdapter = adapter;
    final notifier = AuthNotifier(restoreSession: false, client: client);
    await notifier.loginPassword('staff', 'qa private password');
    expect(adapter.calls.single.data.containsKey('shop_username'), isFalse);
    expect(adapter.calls.single.data['username'], 'staff');
    expect(cache.userId, 'new-user');
    expect(cache.tenantId, 'new-tenant');
    expect(cache.shiftSessionId, isNull);
    expect(cache.accessMode, 'managed');
    expect(await const FlutterSecureStorage().read(key: 'user_pin'), isNull);
    expect(
        prefs.getString('hris-punch:old-tenant:old-user'), 'preserved-request');
    expect(notifier.state.step, AuthStep.setPin);
    notifier.dispose();
  });

  for (final register in [true, false]) {
    testWidgets('password account form register=$register fits 320px at 160%',
        (tester) async {
      tester.view.physicalSize = const Size(320, 760);
      tester.view.devicePixelRatio = 1;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
      await tester.pumpWidget(ProviderScope(
          child: MaterialApp(
              theme: AppTheme.auroraTheme,
              home: PasswordAccountPage(register: register),
              builder: (context, child) => MediaQuery(
                  data: MediaQuery.of(context)
                      .copyWith(textScaler: const TextScaler.linear(1.6)),
                  child: child!))));
      await tester.pumpAndSettle();
      final button = find.text(register ? 'Buat usaha' : 'Simpan password');
      await tester.ensureVisible(button);
      await tester.tap(button);
      await tester.pumpAndSettle();
      expect(find.textContaining('Isi sedikitnya'), findsWidgets);
      expect(tester.takeException(), isNull);
    });
  }

  testWidgets(
      'uncertain attendance retries the same request after the page reopens',
      (tester) async {
    final cache = SessionCache.instance;
    await cache.setUserId('qa-user');
    await cache.setTenantId('qa-tenant');
    await cache.setAccessToken('qa-token');
    var fail = true;
    final adapter = Adapter((request) {
      if (request.path == '/hris/setup')
        return {
          'self_employee': {'name': 'QA staff', 'outlet_id': 'qa-outlet'},
          'open_attendance': null
        };
      if (fail) {
        fail = false;
        throw DioException(
            requestOptions: request, type: DioExceptionType.receiveTimeout);
      }
      return {'id': 'qa-attendance', 'row_version': 1};
    });
    final client = Dio()..httpClientAdapter = adapter;
    Widget page() => ProviderScope(
        child: MaterialApp(
            theme: AppTheme.auroraTheme,
            home: TeamAccountPage(client: client)));
    await tester.pumpWidget(page());
    await tester.pumpAndSettle();
    await tester.tap(find.text('Catat masuk'));
    await tester.pumpAndSettle();
    final pending = (await SharedPreferences.getInstance())
        .getString('hris-punch:qa-tenant:qa-user');
    expect(pending, isNotNull);
    await tester.pumpWidget(const SizedBox());
    await tester.pumpAndSettle();
    await tester.pumpWidget(page());
    await tester.pumpAndSettle();
    await tester.tap(find.text('Periksa pencatatan'));
    await tester.pumpAndSettle();
    final writes = adapter.calls.where((r) => r.path == '/hris/punch').toList();
    expect(writes.length, 2);
    expect(writes.first.data['client_request_id'],
        writes.last.data['client_request_id']);
    expect(
        (await SharedPreferences.getInstance())
            .getString('hris-punch:qa-tenant:qa-user'),
        isNull);
    expect(tester.takeException(), isNull);
  });
}
