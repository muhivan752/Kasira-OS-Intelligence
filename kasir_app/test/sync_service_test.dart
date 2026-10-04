import 'dart:convert';
import 'dart:io';

import 'package:dio/dio.dart';
import 'package:drift/native.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:kasira_kasir/core/database/app_database.dart';
import 'package:kasira_kasir/core/services/session_cache.dart';
import 'package:kasira_kasir/core/sync/sync_service.dart';
import 'package:shared_preferences/shared_preferences.dart';

class SyncResponseAdapter implements HttpClientAdapter {
  final List<Map<String, dynamic>> responses;
  final List<Map<String, dynamic>> requests = [];
  int index = 0;
  SyncResponseAdapter(this.responses);

  @override
  Future<ResponseBody> fetch(RequestOptions options,
      Stream<List<int>>? requestStream, Future<void>? cancelFuture) async {
    requests.add(Map<String, dynamic>.from(options.data as Map));
    final response =
        responses[index < responses.length ? index++ : responses.length - 1];
    if (response.containsKey('http_status')) {
      return ResponseBody.fromString('{}', response['http_status'] as int);
    }
    return ResponseBody.fromString(jsonEncode(response), 200, headers: {
      Headers.contentTypeHeader: [Headers.jsonContentType]
    });
  }

  @override
  void close({bool force = false}) {}
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  test('full server pull applies even when a reservation deposit has no order',
      () async {
    SharedPreferences.setMockInitialValues({});
    final prefs = await SharedPreferences.getInstance();
    final db = AppDatabase.withExecutor(NativeDatabase.memory());
    final dio = Dio();
    addTearDown(db.close);
    addTearDown(dio.close);
    final fixturePath = Platform.environment['SELARIS_SYNC_FIXTURE'];
    final response = fixturePath == null
        ? {
            'last_sync_hlc': '1791111600000:0:server:outlet',
            'changes': {
              'payments': [
                {
                  'id': 'deposit',
                  'order_id': null,
                  'outlet_id': 'outlet',
                  'amount_due': '50000.00',
                  'amount_paid': '50000.00',
                  'payment_method': 'transfer',
                  'status': 'paid',
                  'reference_id': 'reservation:booking',
                },
                {
                  'id': 'sale-payment', 'order_id': 'sale-order',
                  'outlet_id': 'outlet', 'amount_due': '15000.00',
                  'amount_paid': '15000.00', 'payment_method': 'cash',
                  'status': 'paid', 'reference_id': 'receipt-001',
                }
              ],
            },
          }
        : jsonDecode(File(fixturePath).readAsStringSync())
            as Map<String, dynamic>;
    if (fixturePath != null) response['has_more'] = false;
    dio.httpClientAdapter = SyncResponseAdapter([response]);
    SessionCache.instance.outletId = 'outlet';
    final service = SyncService(db, dio, prefs);
    await service.sync();
    expect(service.status, SyncStatus.success);
    expect(
        (await db.select(db.payments).get()).every((p) => p.orderId.isNotEmpty),
        isTrue);
    if (fixturePath == null) {
      final payments = await db.select(db.payments).get();
      expect(payments, hasLength(1));
      expect(payments.single.referenceNumber, 'receipt-001');
    }
  });
  Map<String, dynamic> product(String id) => {
        'id': id,
        'brand_id': 'brand',
        'name': id,
        'base_price': '15000.00',
        'stock_qty': 8,
        'stock_enabled': true,
      };

  Future<(AppDatabase, SyncService, SharedPreferences, SyncResponseAdapter)>
      setup(List<Map<String, dynamic>> pages, {bool backfilled = true}) async {
    SharedPreferences.setMockInitialValues({
      'variants_backfilled_v1': true,
      'sync_pagination_backfilled_v1': backfilled,
      'last_sync_hlc': '1000:0:server:outlet',
    });
    final prefs = await SharedPreferences.getInstance();
    final db = AppDatabase.withExecutor(NativeDatabase.memory());
    final dio = Dio();
    final adapter = SyncResponseAdapter(pages);
    dio.httpClientAdapter = adapter;
    addTearDown(db.close);
    addTearDown(dio.close);
    SessionCache.instance.outletId = 'outlet';
    return (db, SyncService(db, dio, prefs), prefs, adapter);
  }

  test('all pages apply before success and cursor keeps server time', () async {
    final (db, service, prefs, adapter) = await setup([
      {
        'last_sync_hlc': '2000:0:server:outlet',
        'has_more': true,
        'next_cursor_hlc': '1500:0:server:outlet',
        'next_cursor_last_id': 'p1',
        'changes': {
          'products': [product('p1')]
        }
      },
      {
        'last_sync_hlc': '3000:0:server:outlet',
        'has_more': false,
        'changes': {
          'products': [product('p2')]
        }
      },
    ]);
    await service.sync();
    expect(service.status, SyncStatus.success);
    expect((await db.select(db.products).get()).map((p) => p.id), ['p1', 'p2']);
    expect(prefs.getString('last_sync_hlc'), '2000:0:server:outlet');
    expect(adapter.requests[1]['cursor_hlc'], '1500:0:server:outlet');
    expect(adapter.requests[1]['cursor_last_id'], 'p1');
    expect(adapter.requests[1]['changes'], isEmpty);
    expect(adapter.requests[1].containsKey('idempotency_key'), isFalse);
    expect(prefs.getString('pending_sync_idempotency_key'), isNull);
  });

  test('failed continuation preserves checkpoint and pending retry key',
      () async {
    final (_, service, prefs, adapter) = await setup([
      {
        'last_sync_hlc': '2000:0:server:outlet',
        'has_more': true,
        'next_cursor_hlc': '1500:0:server:outlet',
        'next_cursor_last_id': 'p1',
        'changes': {
          'products': [product('p1')]
        }
      },
      {'http_status': 503},
    ]);
    await expectLater(service.sync(), throwsA(isA<DioException>()));
    expect(service.status, SyncStatus.serverError);
    expect(prefs.getString('last_sync_hlc'), '1000:0:server:outlet');
    final pending = prefs.getString('pending_sync_idempotency_key');
    expect(pending, adapter.requests.first['idempotency_key']);
    adapter.responses[1] = {
      'last_sync_hlc': '2000:0:server:outlet', 'has_more': false, 'changes': {}
    };
    await service.sync();
    expect(service.status, SyncStatus.success);
    expect(adapter.requests[2]['idempotency_key'], pending);
    expect(prefs.getString('pending_sync_idempotency_key'), isNull);
  });

  test('invalid pagination cannot report success or advance checkpoint',
      () async {
    final (_, service, prefs, _) = await setup([
      {
        'last_sync_hlc': '2000:0:server:outlet',
        'has_more': true,
        'changes': {}
      },
    ]);
    await expectLater(service.sync(), throwsStateError);
    expect(service.status, SyncStatus.clientError);
    expect(prefs.getString('last_sync_hlc'), '1000:0:server:outlet');
  });

  test('older installation gets a full backfill',
      () async {
    final (_, service, prefs, adapter) = await setup([
      {
        'last_sync_hlc': '2000:0:server:outlet',
        'has_more': false,
        'changes': {}
      },
    ], backfilled: false);
    await service.sync();
    expect(adapter.requests.first['last_sync_hlc'], isNull);
    expect(prefs.getBool('sync_pagination_backfilled_v1'), isTrue);
  });

  test('actual outlet pages apply completely to SQLite', () async {
    final path = Platform.environment['SELARIS_SYNC_PAGES'];
    if (path == null) throw StateError('Missing diagnostic fixture');
    final pages = (jsonDecode(File(path).readAsStringSync()) as List)
        .cast<Map<String, dynamic>>();
    final (db, service, _, adapter) = await setup(pages);
    await service.sync();
    expect(service.status, SyncStatus.success);
    expect(adapter.requests.length, pages.length);
    final expectedProducts = <String>{};
    final expectedItems = <String>{};
    for (final page in pages) {
      for (final row in page['changes']['products']) {
        expectedProducts.add(row['id'] as String);
      }
      for (final row in page['changes']['order_items']) {
        expectedItems.add(row['id'] as String);
      }
    }
    expect((await db.select(db.products).get()).map((p) => p.id).toSet(),
        expectedProducts);
    expect((await db.select(db.orderItems).get()).map((p) => p.id).toSet(),
        expectedItems);
  }, skip: Platform.environment['SELARIS_SYNC_PAGES'] == null);
}
