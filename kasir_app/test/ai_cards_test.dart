import 'dart:convert';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:kasira_kasir/core/api/api_client.dart';
import 'package:kasira_kasir/core/services/session_cache.dart';
import 'package:kasira_kasir/features/ai/presentation/widgets/ai_cards.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// Kartu Selaris AI di app (1.6.37): muat di layar kecil dan Simpan memanggil
/// endpoint yang sama dengan dashboard, dengan path persis (tanpa redirect).
class _Adapter implements HttpClientAdapter {
  final calls = <RequestOptions>[];
  @override
  Future<ResponseBody> fetch(RequestOptions options, Stream<Uint8List>? stream, Future<void>? cancel) async {
    calls.add(options);
    return ResponseBody.fromString(jsonEncode({'success': true, 'data': {}}), 200,
        headers: {Headers.contentTypeHeader: [Headers.jsonContentType]});
  }

  @override
  void close({bool force = false}) {}
}

final _cards = <Map<String, dynamic>>[
  {
    'type': 'recipe_draft', 'session_id': 's1', 'revision': 2, 'fingerprint': 'fp', 'ready': true, 'replaces_recipe': false,
    'product': 'Es Kopi Gula Aren Spesial Ukuran Besar', 'new_product': false, 'total_cost': 2040, 'base_price': 22000, 'margin': 90.7,
    'lines': [
      {'bahan': 'Gula aren cair premium', 'takaran': '20', 'satuan': 'gram', 'biaya': 600, 'perkiraan': false},
      {'bahan': 'Susu UHT full cream', 'takaran': '80', 'satuan': 'ml', 'biaya': 1440, 'perkiraan': true},
    ],
    'missing': [],
  },
  {
    'type': 'ingredient_price', 'ingredient_id': 'ing-1', 'row_version': 3, 'bahan': 'Gula Aren', 'base_unit': 'gram',
    'harga_lama': 30000, 'jumlah_lama': 1000, 'harga_baru': 38000, 'jumlah_baru': 1000, 'biaya_lama': 30, 'biaya_baru': 38,
    'produk': [{'produk': 'Es Kopi Gula Aren', 'modal_lama': 2040, 'modal_baru': 2200, 'margin_baru': 90.0, 'harga_jual': 22000}],
  },
  {
    'type': 'stock_in', 'outlet_id': 'out-1', 'pemasok': 'Toko Makmur Jaya Sentosa', 'nota': true, 'total': 70000, 'produk': [], 'masalah': [],
    'lines': [
      {'ingredient_id': 'ing-1', 'bahan': 'Gula Aren', 'jumlah': 2, 'satuan': 'kg', 'jumlah_dasar': 2000, 'base_unit': 'gram',
        'stok_lama': 500, 'stok_baru': 2500, 'harga_total': 70000, 'biaya_lama': 30, 'biaya_baru': 34},
      {'ingredient_id': 'ing-2', 'bahan': 'Susu UHT', 'jumlah': 5, 'satuan': 'liter', 'jumlah_dasar': 5000, 'base_unit': 'ml',
        'stok_lama': 0, 'stok_baru': 5000, 'harga_total': null, 'biaya_lama': 18, 'biaya_baru': null},
    ],
  },
  {
    'type': 'sell_price', 'masalah': [],
    'lines': [
      {'product_id': 'p-1', 'row_version': 5, 'menu': 'Es Kopi Gula Aren', 'cara': 'naik 7% dari Rp 18.000, dibulatkan ke Rp500',
        'harga_lama': 20000, 'harga_baru': 22000, 'modal': 2040, 'margin_lama': 89.8, 'margin_baru': 90.7, 'di_bawah_modal': false,
        'lonjakan': false, 'varian': [{'nama': 'Large', 'lama': 23000, 'baru': 25000}]},
    ],
  },
];

Future<_Adapter> _pump(WidgetTester tester, List<Map<String, dynamic>> cards) async {
  tester.view.physicalSize = const Size(320, 2400);
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);
  final adapter = _Adapter();
  final dio = Dio(BaseOptions(baseUrl: 'http://qa/api/v1'))..httpClientAdapter = adapter;
  await tester.pumpWidget(ProviderScope(
    overrides: [apiClientProvider.overrideWithValue(dio)],
    child: MaterialApp(
      builder: (context, child) => MediaQuery(
          data: MediaQuery.of(context).copyWith(textScaler: const TextScaler.linear(1.6)), child: child!),
      home: Scaffold(body: ListView(padding: const EdgeInsets.all(12), children: [for (final c in cards) AiCard(card: c)])),
    ),
  ));
  await tester.pumpAndSettle();
  return adapter;
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  setUp(() async {
    SharedPreferences.setMockInitialValues({});
    FlutterSecureStorage.setMockInitialValues({});
    await SessionCache.instance.clear();
    await SessionCache.instance.setOutletId('out-1');
  });

  for (final card in _cards) {
    testWidgets('kartu ${card['type']} muat di 320px dengan teks 160%', (tester) async {
      await _pump(tester, [card]);
      expect(tester.takeException(), isNull);
    });
  }

  testWidgets('Simpan harga bahan = PUT /ingredients/{id} tanpa garis miring', (tester) async {
    final adapter = await _pump(tester, [_cards[1]]);
    await tester.tap(find.text('Simpan harga'));
    await tester.pumpAndSettle();
    final call = adapter.calls.single;
    expect(call.method, 'PUT');
    expect(call.path, '/ingredients/ing-1');
    expect(call.data, {'buy_price': 38000, 'buy_qty': 1000, 'row_version': 3});
    expect(find.text('Harga Gula Aren tersimpan.'), findsOneWidget);
  });

  testWidgets('Simpan nota = POST /purchases/ + restock baris tanpa harga', (tester) async {
    final adapter = await _pump(tester, [_cards[2]]);
    await tester.tap(find.text('Simpan nota'));
    await tester.pumpAndSettle();
    expect(adapter.calls.map((c) => '${c.method} ${c.path}').toList(),
        ['POST /purchases/', 'POST /ingredients/ing-2/restock']);
    final nota = adapter.calls.first.data as Map;
    expect(nota['client_request_id'], isA<String>());
    expect(nota['paid_amount'], isNull);
    expect((nota['items'] as List).single, {
      'ingredient_id': 'ing-1', 'quantity': 2, 'unit': 'kg', 'unit_price': 35000.0, 'total_price': 70000,
    });
    expect((adapter.calls.last.data as Map)['quantity'], 5000);
  });

  testWidgets('Simpan harga jual memakai angka yang diedit', (tester) async {
    final adapter = await _pump(tester, [_cards[3]]);
    await tester.enterText(find.byType(TextField), '21500');
    await tester.pumpAndSettle();
    await tester.tap(find.text('Simpan harga jual'));
    await tester.pumpAndSettle();
    expect(adapter.calls.single.path, '/products/p-1');
    expect(adapter.calls.single.data, {'base_price': 21500, 'row_version': 5});
  });

  testWidgets('Simpan resep = approve sesi HPP dengan outlet aktif', (tester) async {
    final adapter = await _pump(tester, [_cards[0]]);
    await tester.tap(find.text('Simpan resep'));
    await tester.pumpAndSettle();
    expect(adapter.calls.single.path, '/ai/hpp-setup/sessions/s1/approve');
    expect(adapter.calls.single.data, {'outlet_id': 'out-1', 'revision': 2, 'fingerprint': 'fp', 'replace_recipe': false});
  });
}
