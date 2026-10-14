import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';
import 'package:dio/dio.dart';
import 'package:drift/native.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:kasira_kasir/core/api/api_client.dart';
import 'package:kasira_kasir/core/database/app_database.dart';
import 'package:kasira_kasir/core/services/session_cache.dart';
import 'package:kasira_kasir/core/sync/sync_provider.dart';
import 'package:kasira_kasir/core/sync/sync_service.dart';
import 'package:kasira_kasir/core/theme/app_theme.dart';
import 'package:kasira_kasir/features/pos/providers/cart_provider.dart';
import 'package:kasira_kasir/features/dashboard/presentation/pages/staff_home_page.dart';
import 'package:kasira_kasir/features/dashboard/presentation/pages/managed_actions_page.dart';

class Adapter implements HttpClientAdapter {
  Adapter(this.respond);
  final FutureOr<ResponseBody> Function(RequestOptions) respond;
  final calls = <RequestOptions>[];
  @override
  Future<ResponseBody> fetch(RequestOptions options, Stream<Uint8List>? stream,
      Future<void>? cancel) async {
    calls.add(options);
    return await respond(options);
  }

  @override
  void close({bool force = false}) {}
}

ResponseBody jsonBody(dynamic value, [int status = 200]) =>
    ResponseBody.fromString(jsonEncode(value), status, headers: {
      Headers.contentTypeHeader: [Headers.jsonContentType]
    });
final cache = SessionCache.instance;
Map<String, dynamic> manifest([List<String> grants = const ['stock.view']]) => {
      'user_id': 'staff',
      'tenant_id': 'tenant',
      'enforcement_mode': 'managed',
      'permissions': grants,
      'access_version': 'policy-2',
      'outlets': [
        {'id': 'outlet', 'name': 'QA outlet', 'brand_id': 'brand'}
      ],
    };

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  setUp(() async {
    SharedPreferences.setMockInitialValues({
      'last_sync_hlc': '1000:0:server:outlet',
      'pending_sync_idempotency_key': 'owner-pending'
    });
    FlutterSecureStorage.setMockInitialValues({});
    await cache.clear();
    await cache.setUserId('staff');
    await cache.setTenantId('tenant');
    await cache.setAccessToken('staff-token');
    await cache.setOutletId('outlet');
    await cache.applyAccess(manifest());
  });

  test(
      'managed policy survives cold cache initialization and refuses offline writes',
      () async {
    cache.accessMode = 'legacy';
    cache.permissions = {'pos.sell'};
    await cache.initFromPrefsCache();
    expect(cache.accessMode, 'managed');
    expect(cache.allows('stock.view'), isTrue);
    expect(cache.allows('pos.sell'), isFalse);
    expect(cache.offlinePosAllowed, isFalse);
    await cache.clear();
    FlutterSecureStorage.setMockInitialValues({
      'access_mode': 'managed',
      'access_manifest': 'corrupt',
      'access_token': 'staff-token',
      'user_id': 'staff'
    });
    await cache.initFromPrefsCache();
    expect(cache.allows('stock.view'), isFalse);
    expect(cache.offlinePosAllowed, isFalse);
  });

  Future<AppDatabase> seeded() async {
    final db = AppDatabase.withExecutor(NativeDatabase.memory());
    addTearDown(db.close);
    await db.customStatement(
        "INSERT INTO products (id, brand_id, name, base_price, buy_price, is_synced) VALUES ('product', 'brand', 'Pending product', 15000, 7000, 0), ('private', 'brand', 'Private cached product', 15000, 7000, 1)");
    await db.customStatement(
        "INSERT INTO orders (id, outlet_id, order_number, display_number, user_id, is_synced) VALUES ('order', 'outlet', 'Pending order', 1, 'owner', 0), ('parent', 'outlet', 'Pending child parent', 2, 'owner', 1), ('private-order', 'outlet', 'Private cached order', 3, 'owner', 1)");
    await db.customStatement(
        "INSERT INTO order_items (id, order_id, product_id, quantity, unit_price, total_price, is_synced) VALUES ('item', 'order', 'product', 1, 15000, 15000, 0), ('parent-item', 'parent', 'product', 1, 15000, 15000, 0)");
    await db.customStatement(
        "INSERT INTO payments (id, order_id, outlet_id, amount_due, amount_paid, payment_method, is_synced) VALUES ('payment', 'order', 'outlet', 15000, 15000, 'cash', 0)");
    await db.customStatement(
        "INSERT INTO shifts (id, outlet_id, user_id, start_time, is_synced) VALUES ('shift', 'outlet', 'owner', 1000, 0)");
    await db.customStatement(
        "INSERT INTO cash_activities (id, shift_id, activity_type, amount, description, is_synced) VALUES ('cash', 'shift', 'expense', 2000, 'Pending expense', 0)");
    return db;
  }

  test(
      'read-only pull keeps all queues, pending retry key and dependencies even for identical server IDs',
      () async {
    final db = await seeded(), prefs = await SharedPreferences.getInstance();
    final adapter = Adapter((request) => request.path == '/auth/access'
        ? jsonBody({'data': manifest()})
        : jsonBody({
            'last_sync_hlc': '2000:0:server:outlet',
            'changes': {
              'products': [
                {
                  'id': 'product',
                  'brand_id': 'brand',
                  'name': 'Server overwrite',
                  'base_price': 1
                }
              ],
              'orders': [
                {
                  'id': 'order',
                  'outlet_id': 'outlet',
                  'order_number': 'Server overwrite',
                  'display_number': 1
                },
                {
                  'id': 'parent',
                  'outlet_id': 'outlet',
                  'order_number': 'Server overwrite',
                  'display_number': 2
                }
              ],
            },
          }));
    final dio = Dio()..httpClientAdapter = adapter;
    addTearDown(dio.close);
    final service = SyncService(db, dio, prefs);
    await service.sync();
    expect(service.status, SyncStatus.success);
    final post = adapter.calls.last.data as Map;
    // Tanpa pos.sell staf tidak mengirim apa pun; antrean pemilik utuh.
    expect((post['changes'] as Map).values.every((v) => (v as List).isEmpty),
        isTrue);
    // Kunci idempoten staf terpisah: kunci pemilik yang tertunda tidak dipakai.
    expect(post['idempotency_key'], isNot('owner-pending'));
    expect(prefs.getString('pending_sync_idempotency_key'), 'owner-pending');
    expect(prefs.getString('last_sync_hlc'), '1000:0:server:outlet');
    expect((await db.select(db.products).get()).single.name, 'Pending product');
    expect(prefs.getBool('sync_pagination_backfilled_v1'), isFalse);
    expect(prefs.getBool('recipe_hpp_backfilled_v1'), isFalse);
    final orders = await db.select(db.orders).get();
    expect(orders.map((r) => r.orderNumber),
        containsAll(['Pending order', 'Pending child parent']));
    expect(orders, hasLength(2));
    for (final table in [
      'products',
      'order_items',
      'payments',
      'shifts',
      'cash_activities'
    ]) {
      expect(
          (await db
              .customSelect('SELECT id FROM "$table" WHERE is_synced = 0')
              .get()),
          isNotEmpty);
    }
    cache.accessMode = 'legacy';
    final legacyAdapter = Adapter((request) => jsonBody({'last_sync_hlc': '3000:0:server:outlet', 'changes': {}}));
    dio.httpClientAdapter = legacyAdapter;
    await service.sync();
    expect(legacyAdapter.calls.single.data['last_sync_hlc'], isNull);
    expect(legacyAdapter.calls.single.data['idempotency_key'], 'owner-pending');
    expect(legacyAdapter.calls.single.data['changes']['payments'], hasLength(1));
    expect(prefs.getString('pos_cache_access_scope'), 'legacy:tenant:staff:outlet');
    await cache.applyAccess(manifest());
    final returned = Adapter((request) => request.path == '/auth/access' ? jsonBody({'data': manifest()}) : jsonBody({'last_sync_hlc': '4000:0:server:outlet', 'changes': {}}));
    dio.httpClientAdapter = returned;
    await service.sync();
    expect(returned.calls.last.data['last_sync_hlc'], isNull);
    expect(await db.select(db.orders).get(), isEmpty);
    expect(prefs.getString('pos_cache_access_scope'), 'tenant:staff:outlet:policy-2');
  });

  test('revoked access preserves queues and prevents the sync POST', () async {
    final db = await seeded(), prefs = await SharedPreferences.getInstance();
    final adapter = Adapter((_) => jsonBody({
          'data': manifest(['hris.self'])
        }));
    final dio = Dio()..httpClientAdapter = adapter;
    addTearDown(dio.close);
    final service = SyncService(db, dio, prefs);
    await expectLater(service.sync(), throwsStateError);
    expect(adapter.calls, hasLength(1));
    expect((await db.getUnsyncedOrders('outlet')), hasLength(1));
    expect(prefs.getString('pending_sync_idempotency_key'), 'owner-pending');
    expect(prefs.getString('last_sync_hlc'), '1000:0:server:outlet');
  });

  test('account switch during pull cannot apply old rows or advance cursor',
      () async {
    final db = await seeded(), prefs = await SharedPreferences.getInstance();
    final arrived = Completer<void>(), release = Completer<ResponseBody>();
    final adapter = Adapter((request) {
      if (request.path == '/auth/access') return jsonBody({'data': manifest()});
      arrived.complete();
      return release.future;
    });
    final dio = Dio()..httpClientAdapter = adapter;
    addTearDown(dio.close);
    final service = SyncService(db, dio, prefs);
    final running = service.sync();
    await arrived.future;
    await cache.setUserId('other-staff');
    release.complete(jsonBody({
      'last_sync_hlc': '2000:0:server:outlet',
      'changes': {
        'products': [
          {
            'id': 'leak',
            'brand_id': 'other',
            'name': 'Old private response',
            'base_price': 1
          }
        ]
      }
    }));
    await expectLater(running, throwsStateError);
    expect((await db.select(db.products).get()).any((r) => r.id == 'leak'),
        isFalse);
    expect(prefs.getString('managed_sync_hlc:tenant:staff:outlet'), isNull);
  });

  testWidgets(
      'staff home fits 320px at 160% and omits transaction controls',
      (tester) async {
    tester.view.physicalSize = const Size(320, 760);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    final adapter = Adapter((request) => request.path == '/sync/'
            ? jsonBody({'last_sync_hlc': '2000:0:server:outlet', 'changes': {}})
            : jsonBody({'data': manifest()})),
        dio = Dio();
    dio.httpClientAdapter = adapter;
    addTearDown(dio.close);
    final db = AppDatabase.withExecutor(NativeDatabase.memory());
    addTearDown(db.close);
    final prefs = await SharedPreferences.getInstance();
    await tester.pumpWidget(ProviderScope(
        overrides: [
          apiClientProvider.overrideWithValue(dio),
          databaseProvider.overrideWithValue(db),
          sharedPreferencesProvider.overrideWithValue(prefs),
        ],
        child: MaterialApp(
            theme: AppTheme.auroraTheme,
            builder: (context, child) => MediaQuery(
                data: MediaQuery.of(context)
                    .copyWith(textScaler: const TextScaler.linear(1.6)),
                child: child!),
            home: StaffHomePage(onRefreshAccess: () async {
              await dio.get('/auth/access');
            }))));
    await tester.pumpAndSettle();
    expect(find.text('Pesanan online'), findsNothing);
    expect(find.text('Sesi kas'), findsNothing);
    expect(find.text('Keuangan'), findsNothing);
    expect(find.text('Lihat stok di web'), findsOneWidget);
    expect(find.text('Akun ini tidak untuk berjualan.'), findsOneWidget);
    await tester.tap(find.text('Perbarui izin dan data'));
    await tester.pumpAndSettle();
    // Tombol perbarui = muat ulang izin + satu putaran sync.
    expect(adapter.calls.map((r) => r.path), containsAll(['/auth/access', '/sync/']));
    expect(find.text('Izin dan data kasir sudah diperbarui.'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets(
      'cash-only account can record a cash activity without shift or sales permission',
      (tester) async {
    await cache.applyAccess(manifest(['pos.cash.manage']));
    final adapter = Adapter((request) {
      if (request.path == '/shifts/current')
        return jsonBody({
          'data': {'id': 'shift'}
        });
      return jsonBody({
        'data': request.method == 'GET' ? {'activities': []} : {'id': 'cash'}
      });
    });
    final dio = Dio()..httpClientAdapter = adapter;
    addTearDown(dio.close);
    await tester.pumpWidget(ProviderScope(
        overrides: [apiClientProvider.overrideWithValue(dio)],
        child: MaterialApp(
            theme: AppTheme.auroraTheme,
            home: const ManagedActionsPage(action: ManagedAction.cash))));
    await tester.pumpAndSettle();
    await tester.enterText(
        find.widgetWithText(TextField, 'Jumlah (Rp)'), '2000');
    await tester.enterText(
        find.widgetWithText(TextField, 'Keperluan'), 'Air minum');
    await tester.tap(find.text('Catat kas'));
    await tester.pumpAndSettle();
    expect(adapter.calls.where((r) => r.method == 'POST').single.data['amount'],
        2000);
    expect(adapter.calls.any((r) => r.path.contains('uncounted')), isFalse);
    expect(tester.takeException(), isNull);
  });
  test('managed cashier sells offline only within the 12-hour window', () async {
    final db = await seeded(), cart = CartNotifier(db);
    addTearDown(cart.dispose);
    expect(await cart.submitOrder(), isNull);
    expect(cart.state.error, contains('Izin'));
    // Izin jualan baru diterima: offline boleh (keputusan Ivan 14/10/2026).
    await cache.applyAccess(manifest(['pos.sell']));
    expect(cache.offlinePosAllowed, isTrue);
    expect(await cart.savePaymentOffline(orderId: 'order', paymentMethod: 'cash', amountDue: 15000, amountPaid: 15000), isTrue);
    expect((await db.getUnsyncedPayments('outlet')), hasLength(2));
    // Lewat 12 jam tanpa online: berhenti, antrean tetap.
    cache.accessReceivedAt = DateTime.now().subtract(const Duration(hours: 12, minutes: 1));
    expect(cache.offlinePosAllowed, isFalse);
    expect(await cart.savePaymentOffline(orderId: 'order', paymentMethod: 'cash', amountDue: 15000, amountPaid: 15000), isFalse);
    expect(cart.state.error, sefStafOfflineHabis);
    // Jam HP dimundurkan sesudah akses diterima = jendela dianggap habis.
    cache.accessReceivedAt = DateTime.now().add(const Duration(hours: 1));
    expect(cache.offlinePosAllowed, isFalse);
    expect((await db.getUnsyncedPayments('outlet')), hasLength(2));
  });

  test('12-hour window survives a cold start and follows the server value', () async {
    await cache.applyAccess({...manifest(['pos.sell']), 'offline_grace_hours': 2});
    final received = cache.accessReceivedAt!;
    cache.accessReceivedAt = null;
    cache.offlineGraceHours = 12;
    await cache.initFromPrefsCache();
    expect(cache.accessReceivedAt!.difference(received).inSeconds.abs(), lessThan(1));
    expect(cache.offlineGraceHours, 2);
    cache.accessReceivedAt = DateTime.now().subtract(const Duration(hours: 3));
    expect(cache.offlinePosAllowed, isFalse);
  });

  test('staff sync pushes only its own sales and leaves the rest queued', () async {
    final db = await seeded(), prefs = await SharedPreferences.getInstance();
    await db.customStatement(
        "INSERT INTO orders (id, outlet_id, order_number, display_number, user_id, is_synced) VALUES ('mine', 'outlet', 'OFFLINE-1', 9, 'staff', 0), ('mine-old', 'outlet', 'Synced own', 10, 'staff', 1)");
    await db.customStatement(
        "INSERT INTO order_items (id, order_id, product_id, quantity, unit_price, total_price, is_synced) VALUES ('mine-item', 'mine', 'product', 1, 15000, 15000, 0)");
    await db.customStatement(
        "INSERT INTO payments (id, order_id, outlet_id, amount_due, amount_paid, payment_method, is_synced) VALUES ('mine-pay', 'mine', 'outlet', 15000, 15000, 'cash', 0), ('old-pay', 'mine-old', 'outlet', 5000, 5000, 'cash', 0)");
    final adapter = Adapter((request) => request.path == '/auth/access'
        ? jsonBody({'data': manifest(['pos.sell'])})
        : jsonBody({'last_sync_hlc': '2000:0:server:outlet', 'changes': {}}));
    final dio = Dio()..httpClientAdapter = adapter;
    addTearDown(dio.close);
    final service = SyncService(db, dio, prefs);
    await service.sync();
    expect(service.status, SyncStatus.success);
    final changes = (adapter.calls.last.data as Map)['changes'] as Map;
    List ids(String table) => (changes[table] as List).map((r) => r['id']).toList();
    expect(ids('orders'), ['mine']);
    expect(ids('order_items'), ['mine-item']);
    expect(ids('payments'), unorderedEquals(['mine-pay', 'old-pay']));
    for (final table in ['products', 'shifts', 'cash_activities']) {
      expect(changes[table], isEmpty);
    }
    expect(adapter.calls.last.data['idempotency_key'], isNotNull);
    // Terkirim = tandai; milik pemilik tetap mengantre.
    expect((await db.getUnsyncedOrders('outlet')).map((o) => o.id), ['order']);
    expect((await db.getUnsyncedPayments('outlet')).map((p) => p.id), ['payment']);
    expect(await db.getUnsyncedShifts('outlet'), hasLength(1));
    expect(prefs.getString('pending_sync_idempotency_key'), 'owner-pending');
  });

  for (final approve in [false, true]) {
    testWidgets('refund supervisor can cancel confirmation and ${approve ? 'approve' : 'reject'} with current row version', (tester) async {
      await cache.applyAccess(manifest(['pos.refund.approve']));
      var pending = true;
      final adapter = Adapter((request) {
        if (request.method == 'POST') { pending = false; return jsonBody({'data': {'id': 'refund'}}); }
        return jsonBody({'data': pending ? [{'id': 'refund', 'amount': '1000', 'reason': 'QA partial refund', 'status': 'pending', 'row_version': 7}] : []});
      });
      final dio = Dio()..httpClientAdapter = adapter; addTearDown(dio.close);
      await tester.pumpWidget(ProviderScope(overrides: [apiClientProvider.overrideWithValue(dio)], child: MaterialApp(theme: AppTheme.auroraTheme, home: const ManagedActionsPage(action: ManagedAction.refunds))));
      await tester.pumpAndSettle();
      final button = find.text(approve ? 'Setujui' : 'Tolak');
      await tester.tap(button); await tester.pumpAndSettle();
      await tester.tap(find.text('Kembali')); await tester.pumpAndSettle();
      expect(adapter.calls.where((r) => r.method == 'POST'), isEmpty);
      await tester.tap(button); await tester.pumpAndSettle();
      await tester.tap(find.text('Konfirmasi')); await tester.pumpAndSettle();
      final write = adapter.calls.where((r) => r.method == 'POST').single;
      expect(write.path, '/payments/refunds/refund/${approve ? 'approve' : 'reject'}');
      expect(write.data['row_version'], 7); expect(tester.takeException(), isNull);
    });
  }

  testWidgets('kitchen staff can progress a ticket through all three states at 320px', (tester) async {
    tester.view.physicalSize = const Size(320, 760); tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize); addTearDown(tester.view.resetDevicePixelRatio);
    await cache.applyAccess(manifest(['pos.kitchen']));
    var status = 'queued';
    final adapter = Adapter((request) {
      if (request.method == 'POST') status = request.data['status'];
      return jsonBody({'data': request.method == 'POST' ? {'id': 'ticket'} : {'active': [{'id': 'ticket', 'display_number': 1, 'kitchen_status': status, 'items': [{'quantity': 2, 'product_name': 'QA coffee', 'notes': 'No sugar'}]}]}});
    });
    final dio = Dio()..httpClientAdapter = adapter; addTearDown(dio.close);
    await tester.pumpWidget(ProviderScope(overrides: [apiClientProvider.overrideWithValue(dio)], child: MaterialApp(theme: AppTheme.auroraTheme, home: const ManagedActionsPage(action: ManagedAction.kitchen))));
    await tester.pumpAndSettle();
    for (final label in ['Kerjakan', 'Siap', 'Selesai']) { await tester.tap(find.text(label)); await tester.pumpAndSettle(); }
    expect(adapter.calls.where((r) => r.method == 'POST').map((r) => r.data['status']), ['preparing', 'ready', 'done']);
    expect(tester.takeException(), isNull);
  });

}
