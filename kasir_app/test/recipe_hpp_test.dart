import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:dio/dio.dart';
import 'package:drift/native.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:kasira_kasir/core/database/app_database.dart';
import 'package:kasira_kasir/core/services/session_cache.dart';
import 'package:kasira_kasir/core/sync/sync_provider.dart';
import 'package:kasira_kasir/core/theme/app_theme.dart';
import 'package:kasira_kasir/features/products/providers/recipe_provider.dart';
import 'package:kasira_kasir/features/products/presentation/widgets/product_detail_sheet.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'sync_service_test.dart' show SyncResponseAdapter;

Map<String, dynamic> snapshot() =>
    jsonDecode(File('test/fixtures/recipe_hpp.json').readAsStringSync());
Map<String, dynamic> page(Map<String, dynamic> changes) => {
      'last_sync_hlc': '2000:0:server:outlet',
      'has_more': false,
      'changes': changes,
    };
Map<String, dynamic> fullChanges() => {
      'products': [
        {
          'id': 'product',
          'brand_id': 'brand',
          'name': 'Menu',
          'base_price': '5000',
          'stock_enabled': true,
          'stock_qty': 8
        }
      ],
      'recipes': [
        {'id': 'recipe', 'product_id': 'product', 'is_estimated': true}
      ],
      'ingredients': [
        {
          'id': 'rice',
          'brand_id': 'brand',
          'name': 'Beras',
          'base_unit': 'gram',
          'cost_per_base_unit': '17',
          'needs_review': true
        }
      ],
      'recipe_ingredients': [
        {
          'id': 'ri',
          'recipe_id': 'recipe',
          'ingredient_id': 'rice',
          'quantity': 0.1,
          'quantity_unit': 'kg'
        }
      ],
      'outlet_stock': [
        {
          'id': 'stock',
          'outlet_id': 'outlet',
          'ingredient_id': 'rice',
          'computed_stock': 250
        }
      ],
      'recipe_hpp': [snapshot()],
    };

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  Future<
      (
        AppDatabase,
        SyncService,
        SharedPreferences,
        SyncResponseAdapter,
        ProviderContainer
      )> setup(List<Map<String, dynamic>> pages) async {
    SharedPreferences.setMockInitialValues({
      'variants_backfilled_v1': true,
      'sync_pagination_backfilled_v1': true,
      'last_sync_hlc': '1000:0:server:outlet',
    });
    final prefs = await SharedPreferences.getInstance();
    final db = AppDatabase.withExecutor(NativeDatabase.memory());
    final dio = Dio();
    final adapter = SyncResponseAdapter(pages);
    dio.httpClientAdapter = adapter;
    final container =
        ProviderContainer(overrides: [databaseProvider.overrideWithValue(db)]);
    addTearDown(container.dispose);
    addTearDown(db.close);
    addTearDown(dio.close);
    SessionCache.instance.outletId = 'outlet';
    return (db, SyncService(db, dio, prefs), prefs, adapter, container);
  }

  Future<RecipeDetail?> nextDetail(
      ProviderContainer container,
      Future<void> Function() action,
      bool Function(RecipeDetail?) predicate) async {
    final result = Completer<RecipeDetail?>();
    final subscription =
        container.listen(recipeDetailProvider('product'), (_, value) {
      if (value.hasValue &&
          predicate(value.valueOrNull) &&
          !result.isCompleted) {
        result.complete(value.valueOrNull);
      }
    });
    try {
      await action();
      return await result.future.timeout(const Duration(seconds: 5));
    } finally {
      subscription.close();
    }
  }

  test(
      'empty cached result updates on full sync, server costs and provenance persist',
      () async {
    final (db, service, prefs, adapter, container) =
        await setup([page(fullChanges())]);
    final keepAlive =
        container.listen(recipeDetailProvider('product'), (_, __) {});
    addTearDown(keepAlive.close);
    expect(
        await container.read(recipeDetailProvider('product').future), isNull);
    final detail =
        await nextDetail(container, service.sync, (r) => r?.totalHpp == 1700);
    expect(detail!.ingredients[0].quantity, 0.1);
    expect(detail.ingredients[0].lineCost, 1700);
    expect(detail.ingredients[1].isOptional, isTrue);
    expect(detail.ingredients[1].lineCost, 0);
    expect(detail.ingredients[1].needsReview, isTrue);
    expect(detail.isEstimated, isTrue);
    expect(detail.marginAmount, 3300);
    expect((await db.select(db.ingredients).get()).single.needsReview, isTrue);
    expect((await db.select(db.recipes).get()).single.isEstimated, isTrue);
    expect((await db.select(db.recipeIngredients).get()).single.quantity, 0.1);
    expect((await db.select(db.outletStocks).get()).single.computedStock, 250);
    expect(adapter.requests.single['last_sync_hlc'], isNull);
    expect(prefs.getBool('recipe_hpp_backfilled_v1'), isTrue);
  });

  test('ingredient-only delta updates an open provider without invalidation',
      () async {
    final updated = snapshot()
      ..['total_cost'] = '1900.00'
      ..['is_estimated'] = false;
    final (db, service, _, adapter, container) = await setup([
      page(fullChanges()),
      page({
        'recipe_hpp': [updated],
        'ingredients': [
          {
            'id': 'rice',
            'brand_id': 'brand',
            'name': 'Beras',
            'cost_per_base_unit': '19'
          }
        ]
      })
    ]);
    final keepAlive =
        container.listen(recipeDetailProvider('product'), (_, __) {});
    addTearDown(keepAlive.close);
    await nextDetail(container, service.sync, (r) => r?.totalHpp == 1700);
    await nextDetail(container, service.sync, (r) => r?.totalHpp == 1900);
    expect(adapter.requests[1]['last_sync_hlc'], '2000:0:server:outlet');
    expect((await db.select(db.recipeIngredients).get()).single.quantity, 0.1);
  });

  test(
      'paginated snapshot can arrive before recipe; failure retries full backfill',
      () async {
    final first = page({
      'recipe_hpp': [snapshot()]
    })
      ..addAll({
        'has_more': true,
        'next_cursor_hlc': '1500:0:server:outlet',
        'next_cursor_last_id': 'id',
      });
    final (_, service, prefs, adapter, container) = await setup([
      first,
      {'http_status': 503}
    ]);
    await expectLater(service.sync(), throwsA(isA<DioException>()));
    expect(prefs.getBool('recipe_hpp_backfilled_v1'), isNull);
    expect(prefs.getString('last_sync_hlc'), '1000:0:server:outlet');
    adapter.responses[1] = page(fullChanges()
      ..remove('recipe_hpp')
      ..['recipe_hpp'] = []);
    final detail =
        await nextDetail(container, service.sync, (r) => r?.totalHpp == 1700);
    expect(detail!.isEstimated, isTrue);
    expect(adapter.requests[2]['last_sync_hlc'], isNull);
    expect(prefs.getBool('recipe_hpp_backfilled_v1'), isTrue);
  });

  test(
      'missing server protocol never fabricates HPP or marks backfill complete',
      () async {
    final (_, service, prefs, _, container) =
        await setup([page(fullChanges()..remove('recipe_hpp'))]);
    await service.sync();
    final detail = await container.read(recipeDetailProvider('product').future);
    expect(detail!.needsSync, isTrue);
    expect(detail.totalHpp, isNull);
    expect(detail.marginAmount, isNull);
    expect(prefs.getBool('recipe_hpp_backfilled_v1'), isNull);
  });

  test('replacement and soft delete update the watched active recipe',
      () async {
    final replacement = snapshot()
      ..['recipe_id'] = 'new'
      ..['total_cost'] = '2100';
    final (_, service, _, __, container) = await setup([
      page(fullChanges()),
      page({
        'recipes': [
          {'id': 'recipe', 'product_id': 'product', 'is_active': false},
          {'id': 'new', 'product_id': 'product', 'version': 2},
        ],
        'recipe_hpp': [replacement]
      }),
      page({
        'recipes': [
          {
            'id': 'new',
            'product_id': 'product',
            'version': 2,
            'is_deleted': true
          }
        ],
        'recipe_hpp': []
      }),
    ]);
    final keepAlive =
        container.listen(recipeDetailProvider('product'), (_, __) {});
    addTearDown(keepAlive.close);
    await nextDetail(container, service.sync, (r) => r?.totalHpp == 1700);
    await nextDetail(container, service.sync, (r) => r?.totalHpp == 2100);
    await nextDetail(container, service.sync, (r) => r == null);
  });

  test(
      'v7 upgrade preserves pending transactions and adds only HPP cache fields',
      () async {
    final dir = await Directory.systemTemp.createTemp('selaris-hpp-migration-');
    addTearDown(() => dir.delete(recursive: true));
    final file = File('${dir.path}/cache.sqlite');
    final old = AppDatabase.withExecutor(NativeDatabase(file));
    await old.customStatement(
        "INSERT INTO orders (id, outlet_id, user_id, order_number, display_number, status, order_type, subtotal, tax_amount, service_charge_amount, discount_amount, total_amount, row_version, is_deleted, is_synced) VALUES ('offline-order','outlet','user','OFFLINE-1',1,'pending','takeaway',100,0,0,0,100,0,0,0)");
    await old
        .customStatement('ALTER TABLE ingredients DROP COLUMN needs_review');
    await old.customStatement('ALTER TABLE recipes DROP COLUMN is_estimated');
    await old.customStatement('DROP TABLE recipe_hpp_snapshots');
    await old.customStatement('PRAGMA user_version = 7');
    await old.close();
    final upgraded = AppDatabase.withExecutor(NativeDatabase(file));
    addTearDown(upgraded.close);
    final orders = await upgraded.select(upgraded.orders).get();
    expect(orders.single.id, 'offline-order');
    expect(orders.single.isSynced, isFalse);
    expect(await upgraded.select(upgraded.recipeHppSnapshots).get(), isEmpty);
    expect(upgraded.schemaVersion, 8);
  });

  test('actual read-only server snapshots apply to native recipe details',
      () async {
    final response = jsonDecode(
        File(Platform.environment['HPP_LIVE_SYNC_FIXTURE']!)
            .readAsStringSync()) as Map<String, dynamic>;
    final (_, service, __, ___, container) = await setup([response]);
    await service.sync();
    expect(service.status, SyncStatus.success);
    final changes = response['changes'] as Map<String, dynamic>;
    final visibleProducts = (changes['products'] as List)
        .where((p) => p['is_deleted'] != true)
        .map((p) => p['id'])
        .toSet();
    final active = (changes['recipes'] as List)
        .where((r) =>
            r['is_active'] == true &&
            r['is_deleted'] != true &&
            visibleProducts.contains(r['product_id']))
        .map((r) => r['id'])
        .toSet();
    var checked = 0;
    for (final snapshot in changes['recipe_hpp']) {
      if (!active.contains(snapshot['recipe_id'])) continue;
      final detail = await container
          .read(recipeDetailProvider(snapshot['product_id']).future);
      expect(detail, isNotNull);
      expect(
          detail!.totalHpp,
          snapshot['total_cost'] == null
              ? null
              : double.parse(snapshot['total_cost']));
      expect(detail.isEstimated, snapshot['is_estimated']);
      expect(detail.needsReview, snapshot['needs_review']);
      checked++;
    }
    expect(checked, greaterThan(0));
  }, skip: Platform.environment['HPP_LIVE_SYNC_FIXTURE'] == null);

  final detail = RecipeDetail(
      recipeName: 'Resep',
      totalHpp: 1700,
      sellingPrice: 5000,
      marginAmount: 3300,
      marginPercent: 66,
      isEstimated: true,
      ingredients: const [
        RecipeIngredientDetail(
            name: 'Beras dengan nama bahan panjang',
            quantity: 0.025,
            unit: 'kg',
            costPerUnit: 17,
            lineCost: 1700),
        RecipeIngredientDetail(
            name: 'Tambahan',
            quantity: 1,
            unit: 'pcs',
            costPerUnit: 500,
            lineCost: 0,
            isOptional: true,
            needsReview: true)
      ]);

  for (final width in [320.0, 375.0, 600.0, 768.0, 1024.0]) {
    for (final dark in [false, true]) {
      testWidgets('HPP sheet at $width dark=$dark with 200% text and close',
          (tester) async {
        tester.view.physicalSize = Size(width, 600);
        tester.view.devicePixelRatio = 1;
        addTearDown(tester.view.resetPhysicalSize);
        addTearDown(tester.view.resetDevicePixelRatio);
        await tester.pumpWidget(ProviderScope(
            overrides: [
              recipeDetailProvider('product')
                  .overrideWith((_) => Stream.value(detail)),
            ],
            child: MaterialApp(
              theme: dark ? AppTheme.darkTheme : AppTheme.auroraTheme,
              builder: (context, child) => MediaQuery(
                  data: MediaQuery.of(context)
                      .copyWith(textScaler: const TextScaler.linear(2)),
                  child: child!),
              home: Scaffold(
                  body: Builder(
                      builder: (context) => TextButton(
                          onPressed: () => ProductDetailSheet.show(context,
                              productId: 'product',
                              productName: 'Menu dengan nama panjang sekali',
                              sellingPrice: 5000),
                          child: const Text('Buka rincian')))),
            )));
        await tester.tap(find.text('Buka rincian'));
        await tester.pumpAndSettle();
        expect(tester.takeException(), isNull);
        final theme = dark ? AppTheme.darkTheme : AppTheme.auroraTheme;
        final material = tester.widget<Material>(find
            .ancestor(
                of: find.byType(ProductDetailSheet),
                matching: find.byType(Material))
            .first);
        final background = material.color ?? theme.colorScheme.surface;
        for (final ink in [
          theme.colorScheme.onSurface,
          theme.colorScheme.onSurfaceVariant,
          dark ? const Color(0xFFE5A08C) : const Color(0xFF914C38)
        ]) {
          final a = ink.computeLuminance(), b = background.computeLuminance();
          final contrast =
              a > b ? (a + 0.05) / (b + 0.05) : (b + 0.05) / (a + 0.05);
          expect(contrast, greaterThanOrEqualTo(4.5));
        }
        expect(find.text('HPP bahan per porsi (estimasi)'), findsOneWidget);
        await tester.ensureVisible(find.text('Opsional, tidak masuk HPP'));
        expect(find.text('0,025 kg'), findsOneWidget);
        expect(find.text('Harga perkiraan'), findsOneWidget);
        expect(tester.takeException(), isNull);
        await tester.ensureVisible(find.byTooltip('Tutup rincian HPP'));
        expect(tester.getSize(find.byTooltip('Tutup rincian HPP')).width,
            greaterThanOrEqualTo(44));
        await tester.tap(find.byTooltip('Tutup rincian HPP'));
        await tester.pumpAndSettle();
        expect(find.text('Buka rincian'), findsOneWidget);
      });
    }
  }

  testWidgets('error retries, empty state and Escape closes the sheet',
      (tester) async {
    var attempts = 0;
    await tester.pumpWidget(ProviderScope(
        overrides: [
          recipeDetailProvider('product').overrideWith((_) {
            attempts++;
            return attempts == 1
                ? Stream.error(StateError('fixture'))
                : Stream.value(null);
          }),
        ],
        child: MaterialApp(
          theme: AppTheme.auroraTheme,
          home: Scaffold(
              body: Builder(
                  builder: (context) => TextButton(
                      onPressed: () => ProductDetailSheet.show(context,
                          productId: 'product',
                          productName: 'Menu',
                          sellingPrice: 5000),
                      child: const Text('Buka rincian')))),
        )));
    await tester.tap(find.text('Buka rincian'));
    await tester.pumpAndSettle();
    expect(find.text('Rincian HPP belum bisa dimuat.'), findsOneWidget);
    await tester.tap(find.text('Muat ulang rincian'));
    await tester.pumpAndSettle();
    expect(attempts, 2);
    expect(
        find.text(
            'Belum ada resep. Tambah resep di dashboard, lalu sinkronkan data.'),
        findsOneWidget);
    await tester.sendKeyEvent(LogicalKeyboardKey.escape);
    await tester.pumpAndSettle();
    expect(find.text('Buka rincian'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });
}
