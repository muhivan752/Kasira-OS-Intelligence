import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'package:crypto/crypto.dart';
import 'package:dio/dio.dart';
import 'package:drift/drift.dart' as drift;
import 'package:shared_preferences/shared_preferences.dart';
import 'package:uuid/uuid.dart';
import '../database/app_database.dart';
import '../utils/hlc.dart';
import '../utils/pn_counter.dart';
import '../services/session_cache.dart';
import 'package:flutter/foundation.dart';

/// Status terakhir dari SyncService.sync(). UI bisa watch ini untuk kasih
/// badge/icon tanpa perlu manage loading state manual.
enum SyncStatus {
  idle,
  syncing,
  success,
  /// Expected offline scenarios: SocketException, TimeoutException, DioException
  /// connectionError/timeout. Di-log silent (debugPrint) — gak lempar exception
  /// biar caller fire-and-forget gak keganggu.
  networkError,
  /// HTTP error dari server (4xx/5xx). Di-rethrow biar caller bisa show UI.
  serverError,
  /// Bug di Flutter (parsing error, null deref, dll). Di-rethrow biar bug gak
  /// ketimbun silent.
  clientError,
}

class SyncService {
  final AppDatabase db;
  final Dio dio;
  final SharedPreferences prefs;

  static const String _lastSyncKey = 'last_sync_hlc';
  // Raw device installation ID — UUID random di-generate sekali saat first
  // launch, survive logout (identity device fisik). Key legacy-compat pake
  // nama lama `device_node_id` biar user existing gak reset.
  static const String _deviceIdKey = 'device_node_id';

  // Persistent idempotency_key (Batch #23 bulletproof): disimpan di prefs
  // sampai server balas 200 OK. Kalau network drop mid-push, next sync()
  // reuse key yang sama → backend dedup via (tenant_id, key) composite PK =
  // zero duplicate stock deduct walaupun ruko Medan sinyal naik-turun.
  static const String _pendingIdempotencyKey = 'pending_sync_idempotency_key';

  // UUID v4 generator untuk idempotency_key sync batch (Batch #23).
  static const _uuid = Uuid();

  /// Set to true after sync if stock_mode changed on server
  bool _stockModeChanged = false;
  String _newStockMode = '';

  bool get stockModeChanged => _stockModeChanged;
  String get newStockMode => _newStockMode;
  void clearStockModeChanged() { _stockModeChanged = false; _newStockMode = ''; }

  /// Current sync status — reset to terminal state (never stuck di syncing).
  SyncStatus _status = SyncStatus.idle;
  String? _lastError;
  SyncStatus get status => _status;
  String? get lastError => _lastError;
  bool get isSyncing => _status == SyncStatus.syncing;

  SyncService(this.db, this.dio, this.prefs);

  /// Persistent device installation ID — dibuat sekali saat first launch,
  /// survive logout. Bukan identitas user, tapi identitas fisik device.
  String get deviceId {
    String? id = prefs.getString(_deviceIdKey);
    if (id == null) {
      id = 'device_${DateTime.now().millisecondsSinceEpoch}';
      prefs.setString(_deviceIdKey, id);
    }
    return id;
  }

  /// CRDT node ID — Batch #17 Rule #9: unik per pasangan (device, user).
  ///
  /// WHY: Sebelumnya nodeId cuma `device_{ts}` — kalau User A dan User B
  /// login di device yang sama, mereka share nodeId → tabrakan PNCounter
  /// dan HLC di merge server (inkrement A dan B jatuh di slot yang sama).
  ///
  /// Sekarang: `sha256(deviceId|userId)` dipotong 16 hex char, prefix `u`.
  /// Deterministic — user yang sama di device yang sama → nodeId tetap
  /// (penting biar inkrement lama ke-merge dengan inkrement baru).
  ///
  /// Pre-login fallback: return raw deviceId. Sync gak jalan tanpa userId
  /// anyway (di sync() kita bail out kalau `outletId` null).
  String get nodeId {
    final device = deviceId;
    final userId = SessionCache.instance.userId;
    if (userId == null || userId.isEmpty) {
      return device;
    }
    final digest = sha256.convert(utf8.encode('$device|$userId')).toString();
    return 'u${digest.substring(0, 16)}';
  }

  /// Reset in-memory state flags — dipanggil saat logout biar sync cycle
  /// lama (kalau ada) gak leak status stale ke session user baru.
  /// NOTE: Tidak nyentuh SQLite — data offline (orders, payments) tetap
  /// tersimpan untuk re-login atau user kedua di device yang sama.
  void resetState() {
    _status = SyncStatus.idle;
    _lastError = null;
    _stockModeChanged = false;
    _newStockMode = '';
  }

  // Batch #18 Rule #4b: CancelToken untuk cancel in-flight POST saat logout.
  // Dio CancelToken one-shot — setelah cancel() dipanggil, token gak bisa
  // dipake ulang. Makanya kita re-init di [cancelInFlight] biar sync cycle
  // berikutnya start fresh.
  CancelToken _syncCancelToken = CancelToken();

  /// Batalin request POST /sync yang sedang in-flight (kalau ada). Dipanggil
  /// dari `performLogout()` biar gak ada request "gentayangan" yang complete
  /// dengan header auth lama setelah user logout.
  ///
  /// Setelah cancel, token di-reset ke instance baru biar sync berikut
  /// (e.g. dari user baru yang login) punya CancelToken segar.
  void cancelInFlight() {
    if (!_syncCancelToken.isCancelled) {
      _syncCancelToken.cancel('logout');
    }
    _syncCancelToken = CancelToken();
  }

  Future<void> sync() async {
    // Concurrent sync guard — kalau udah ada yang jalan, skip (bukan error)
    if (_status == SyncStatus.syncing) {
      debugPrint('sync() skipped: already in progress');
      return;
    }
    _status = SyncStatus.syncing;
    _lastError = null;

    try {
      // Rule #50: scope unsynced reads ke outletId aktif — jangan push data
      // outlet lain saat user switch. Kalau outletId null = session belum
      // lengkap, bail out biar sync berikutnya re-run dengan context bener.
      final currentOutletId = SessionCache.instance.outletId;
      if (currentOutletId == null || currentOutletId.isEmpty) {
        _status = SyncStatus.idle;
        return;
      }

      // Batch #18 Rule #4: scope unsynced products by current tenant's brand
      // biar gak leak produk dari session tenant lama (kalau pernah login
      // beda tenant di device sama). Null = first-install, no filter.
      final currentBrandId = await db.getCurrentBrandId();

      // 1. Gather unsynced local changes — parallel
      final futures = await Future.wait([
        db.getUnsyncedProducts(brandId: currentBrandId),
        db.getUnsyncedOrders(currentOutletId),
        db.getUnsyncedOrderItems(currentOutletId),
        db.getUnsyncedPayments(currentOutletId),
        db.getUnsyncedShifts(currentOutletId),
        db.getUnsyncedCashActivities(currentOutletId),
      ]);
      final unsyncedProducts = futures[0] as List<ProductLocal>;
      final unsyncedOrders = futures[1] as List<OrderLocal>;
      final unsyncedOrderItems = futures[2] as List<OrderItemLocal>;
      final unsyncedPayments = futures[3] as List<PaymentLocal>;
      final unsyncedShifts = futures[4] as List<ShiftLocal>;
      final unsyncedCashActivities = futures[5] as List<CashActivityLocal>;

      final changes = {
        'categories': [], // We don't create categories from POS
        'products': unsyncedProducts.map(_productToJson).toList(),
        'orders': unsyncedOrders.map(_orderToJson).toList(),
        'order_items': unsyncedOrderItems.map(_orderItemToJson).toList(),
        'payments': unsyncedPayments.map(_paymentToJson).toList(),
        'outlet_stock': [], // Handled via products/orders usually
        'shifts': unsyncedShifts.map(_shiftToJson).toList(),
        'cash_activities': unsyncedCashActivities.map(_cashActivityToJson).toList(),
      };

      final lastSyncHlc = prefs.getString(_lastSyncKey);

      // Multi-outlet tenant WAJIB kirim outlet_id — backend reject (400) kalau
      // tenant punya >1 outlet dan outlet_id kosong. Single-outlet backward
      // compat masih jalan karena backend auto-pick satu-satunya outlet.
      //
      // idempotency_key (Batch #23 bulletproof): cek prefs dulu — kalau ada
      // key pending dari attempt sebelumnya yang gagal/timeout, REUSE key itu
      // supaya backend bisa dedup. Kalau kosong, generate v4 baru + save ke
      // prefs. Key di-remove dari prefs cuma setelah server balas 200 OK
      // (end of success block) — guarantee retry-safe walau mid-flight drop.
      String? pendingKey = prefs.getString(_pendingIdempotencyKey);
      if (pendingKey == null || pendingKey.isEmpty) {
        pendingKey = _uuid.v4();
        await prefs.setString(_pendingIdempotencyKey, pendingKey);
      }

      final payload = {
        'node_id': nodeId,
        'outlet_id': currentOutletId,
        'last_sync_hlc': lastSyncHlc,
        'idempotency_key': pendingKey,
        'changes': changes,
      };

      // 2. Send to server — pass cancel token biar logout bisa batalin
      //    in-flight request (Batch #18 Rule #4b).
      final response = await dio.post(
        '/sync/',
        data: payload,
        cancelToken: _syncCancelToken,
      );

      if (response.statusCode == 200) {
        final data = response.data;
        final serverHlc = data['last_sync_hlc'];
        final serverChanges = data['changes'];

        // 3. Apply server changes to local DB
        await _applyServerChanges(serverChanges);

        // 3b. Persist stock_mode + subscription_tier via SessionCache
        final cache = SessionCache.instance;
        final stockMode = data['stock_mode']?.toString();
        final subscriptionTier = data['subscription_tier']?.toString();
        if (stockMode != null) {
          await cache.setStockMode(stockMode);
          if (cache.stockModeChanged) {
            _stockModeChanged = true;
            _newStockMode = stockMode;
          }
        }
        if (subscriptionTier != null) {
          await cache.setSubscriptionTier(subscriptionTier);
        }

        // 4. Mark local changes as synced
        await _markAsSynced(
          products: unsyncedProducts,
          orders: unsyncedOrders,
          orderItems: unsyncedOrderItems,
          payments: unsyncedPayments,
          shifts: unsyncedShifts,
          cashActivities: unsyncedCashActivities,
        );

        // 5. Update last sync HLC — merge server HLC dengan local via
        // HLC.receive() daripada naïve string-write (Batch #23 fix). Ini
        // guarantee monotonic increase + handle clock drift device↔server.
        // Sebelumnya naïve write bisa regress HLC kalau device clock mundur
        // → offline order HLC < previous → gagal menang di CRDT merge.
        if (serverHlc is String && serverHlc.isNotEmpty) {
          HLC localHlc;
          try {
            localHlc = (lastSyncHlc != null && lastSyncHlc.isNotEmpty)
                ? HLC.parse(lastSyncHlc)
                : HLC.now(nodeId);
          } catch (_) {
            // Prefs corrupt (malformed HLC dari version lama atau manual edit)
            // — fallback ke fresh HLC, gak crash.
            localHlc = HLC.now(nodeId);
          }
          try {
            final merged = HLC.fromServer(localHlc, serverHlc);
            await prefs.setString(_lastSyncKey, merged.toString());
          } on FormatException catch (e) {
            // Server HLC malformed — skip save, sync berikutnya retry.
            // Prefs gak ter-corrupt.
            debugPrint('sync() server HLC malformed, skip save: $e');
          }
        }

        // 6. Hapus pending idempotency_key — sync selesai end-to-end, next
        // sync() generate fresh. Timing: SETELAH HLC update + markAsSynced
        // biar kalau ada failure mid-way, key stays persist → retry reuses →
        // backend dedup. Placed paling akhir sebelum _status=success.
        await prefs.remove(_pendingIdempotencyKey);

        _status = SyncStatus.success;
        // debugPrint('Sync completed successfully. New HLC: $serverHlc');
      } else {
        _status = SyncStatus.serverError;
        _lastError = 'Server status: ${response.statusCode}';
        debugPrint('sync() server status: ${response.statusCode}');
      }
    } on SocketException catch (e) {
      // Offline / DNS fail / connection refused — silent, data stays
      // isSynced=false biar retry otomatis saat online lagi.
      _status = SyncStatus.networkError;
      _lastError = 'Tidak ada koneksi internet';
      debugPrint('sync() SocketException: $e');
    } on TimeoutException catch (e) {
      // Jaringan lambat / hang — silent, retry next cycle.
      _status = SyncStatus.networkError;
      _lastError = 'Jaringan timeout';
      debugPrint('sync() TimeoutException: $e');
    } on DioException catch (e) {
      // Cancel = request dibatalin via CancelToken (Batch #18 Rule #4b —
      // biasanya dari performLogout). Silent, treat as idle exit — jangan
      // rethrow biar logout flow gak ganggu UI dengan error dialog.
      if (e.type == DioExceptionType.cancel) {
        _status = SyncStatus.idle;
        _lastError = null;
        debugPrint('sync() cancelled (logout or manual)');
        return;
      }
      final isNetworkFailure = e.type == DioExceptionType.connectionError ||
          e.type == DioExceptionType.connectionTimeout ||
          e.type == DioExceptionType.receiveTimeout ||
          e.type == DioExceptionType.sendTimeout ||
          e.error is SocketException;
      if (isNetworkFailure) {
        _status = SyncStatus.networkError;
        _lastError = 'Jaringan putus di tengah sync';
        debugPrint('sync() Dio network: ${e.type} ${e.message}');
        // silent — expected offline scenario
      } else {
        _status = SyncStatus.serverError;
        _lastError = 'Server error: ${e.response?.statusCode ?? "unknown"}';
        debugPrint('sync() Dio server: ${e.response?.statusCode} ${e.message}');
        rethrow; // server errors bubble up — caller boleh tampilin UI
      }
    } catch (e, st) {
      _status = SyncStatus.clientError;
      _lastError = 'Error internal: $e';
      debugPrint('sync() unknown: $e\n$st');
      rethrow; // bug Flutter — jangan ditelan silent
    } finally {
      // Guard: kalau status masih "syncing" di sini berarti ada code path
      // yang lupa set terminal state → paksa ke idle biar UI gak nyangkut.
      if (_status == SyncStatus.syncing) {
        _status = SyncStatus.idle;
      }
    }
  }

  Future<void> _applyServerChanges(Map<String, dynamic> changes) async {
    await db.transaction(() async {
      // Apply Products — CRDT merge: gabungkan counter lokal & server
      if (changes['products'] != null) {
        for (var p in changes['products']) {
          final serverPos = p['crdt_positive'] ?? '{}';
          final serverNeg = p['crdt_negative'] ?? '{}';

          // Cek apakah produk sudah ada di lokal
          final existing = await (db.select(db.products)
                ..where((t) => t.id.equals(p['id'])))
              .getSingleOrNull();

          String mergedPos = serverPos;
          String mergedNeg = serverNeg;
          double mergedStock = (p['stock_qty'] as num?)?.toDouble() ?? 0.0;

          if (existing != null && existing.stockEnabled) {
            // Merge CRDT: ambil max dari setiap node
            final localPosMap = PNCounter.fromJson(existing.crdtPositive);
            final localNegMap = PNCounter.fromJson(existing.crdtNegative);
            final serverPosMap = PNCounter.fromJson(serverPos);
            final serverNegMap = PNCounter.fromJson(serverNeg);

            final mPos = PNCounter.merge(localPosMap, serverPosMap);
            final mNeg = PNCounter.merge(localNegMap, serverNegMap);

            mergedPos = PNCounter.toJson(mPos);
            mergedNeg = PNCounter.toJson(mNeg);
            mergedStock = PNCounter.getValue(mPos, mNeg);
          }

          await db.into(db.products).insertOnConflictUpdate(
            ProductLocal(
              id: p['id'],
              brandId: p['brand_id'],
              categoryId: p['category_id'],
              name: p['name'],
              description: p['description'],
              basePrice: (p['base_price'] as num).toDouble(),
              sku: p['sku'],
              barcode: p['barcode'],
              imageUrl: p['image_url'],
              stockEnabled: p['stock_enabled'] ?? false,
              crdtPositive: mergedPos,
              crdtNegative: mergedNeg,
              stockQty: mergedStock,
              isActive: p['is_active'] ?? true,
              rowVersion: p['row_version'] ?? 0,
              isDeleted: p['is_deleted'] ?? false,
              lastModifiedHlc: p['hlc'],
              isSynced: true,
            ),
          );
        }
      }

      // Apply Orders
      if (changes['orders'] != null) {
        for (var o in changes['orders']) {
          await db.into(db.orders).insertOnConflictUpdate(
            OrderLocal(
              id: o['id'],
              outletId: o['outlet_id'],
              shiftSessionId: o['shift_session_id'],
              customerId: o['customer_id'],
              tableId: o['table_id'],
              userId: o['user_id'],
              orderNumber: o['order_number'],
              displayNumber: o['display_number'],
              status: o['status'],
              orderType: o['order_type'],
              subtotal: (o['subtotal'] as num).toDouble(),
              serviceChargeAmount: (o['service_charge_amount'] as num).toDouble(),
              taxAmount: (o['tax_amount'] as num).toDouble(),
              discountAmount: (o['discount_amount'] as num).toDouble(),
              totalAmount: (o['total_amount'] as num).toDouble(),
              notes: o['notes'],
              createdAt: o['created_at'] != null ? DateTime.parse(o['created_at']) : null,
              updatedAt: o['updated_at'] != null ? DateTime.parse(o['updated_at']) : null,
              rowVersion: o['row_version'] ?? 0,
              isDeleted: o['is_deleted'] ?? false,
              lastModifiedHlc: o['hlc'],
              isSynced: true,
            ),
          );
        }
      }
      
      // Apply Order Items
      if (changes['order_items'] != null) {
        for (var oi in changes['order_items']) {
          await db.into(db.orderItems).insertOnConflictUpdate(
            OrderItemLocal(
              id: oi['id'],
              orderId: oi['order_id'],
              productId: oi['product_id'],
              productVariantId: oi['product_variant_id'],
              quantity: oi['quantity'],
              unitPrice: (oi['unit_price'] as num).toDouble(),
              discountAmount: (oi['discount_amount'] as num).toDouble(),
              totalPrice: (oi['total_price'] as num).toDouble(),
              modifiers: oi['modifiers']?.toString(),
              notes: oi['notes'],
              rowVersion: oi['row_version'] ?? 0,
              isDeleted: oi['is_deleted'] ?? false,
              lastModifiedHlc: oi['hlc'],
              isSynced: true,
            ),
          );
        }
      }

      // Apply Payments
      if (changes['payments'] != null) {
        for (var p in changes['payments']) {
          await db.into(db.payments).insertOnConflictUpdate(
            PaymentLocal(
              id: p['id'],
              orderId: p['order_id'],
              outletId: p['outlet_id'],
              shiftSessionId: p['shift_session_id'],
              amountDue: (p['amount_due'] as num).toDouble(),
              amountPaid: (p['amount_paid'] as num).toDouble(),
              paymentMethod: p['payment_method'],
              status: p['status'],
              referenceNumber: p['reference_number'],
              paidAt: p['paid_at'] != null ? DateTime.parse(p['paid_at']) : null,
              rowVersion: p['row_version'] ?? 0,
              isDeleted: p['is_deleted'] ?? false,
              lastModifiedHlc: p['hlc'],
              isSynced: true,
            ),
          );
        }
      }

      // Apply Shifts
      if (changes['shifts'] != null) {
        for (var s in changes['shifts']) {
          await db.into(db.shifts).insertOnConflictUpdate(
            ShiftLocal(
              id: s['id'],
              outletId: s['outlet_id'],
              userId: s['user_id'],
              status: s['status'],
              startTime: DateTime.parse(s['start_time']),
              endTime: s['end_time'] != null ? DateTime.parse(s['end_time']) : null,
              startingCash: (s['starting_cash'] as num).toDouble(),
              endingCash: (s['ending_cash'] as num?)?.toDouble(),
              expectedEndingCash: (s['expected_ending_cash'] as num?)?.toDouble(),
              notes: s['notes'],
              rowVersion: s['row_version'] ?? 0,
              isDeleted: s['is_deleted'] ?? false,
              lastModifiedHlc: s['hlc'],
              isSynced: true,
            ),
          );
        }
      }
      
      // Apply Cash Activities
      if (changes['cash_activities'] != null) {
        for (var ca in changes['cash_activities']) {
          await db.into(db.cashActivities).insertOnConflictUpdate(
            CashActivityLocal(
              id: ca['id'],
              shiftId: ca['shift_id'],
              activityType: ca['activity_type'],
              amount: (ca['amount'] as num).toDouble(),
              description: ca['description'],
              rowVersion: ca['row_version'] ?? 0,
              isDeleted: ca['is_deleted'] ?? false,
              lastModifiedHlc: ca['hlc'],
              isSynced: true,
            ),
          );
        }
      }

      // Apply Ingredients (read-only from server)
      if (changes['ingredients'] != null) {
        for (var ing in changes['ingredients']) {
          await db.into(db.ingredients).insertOnConflictUpdate(
            IngredientLocal(
              id: ing['id'],
              brandId: ing['brand_id'],
              name: ing['name'],
              trackingMode: ing['tracking_mode'] ?? 'simple',
              baseUnit: ing['base_unit'] ?? 'pcs',
              unitType: ing['unit_type'] ?? 'COUNT',
              buyPrice: _toDouble(ing['buy_price']),
              buyQty: _toDouble(ing['buy_qty'], fallback: 1.0),
              costPerBaseUnit: _toDouble(ing['cost_per_base_unit']),
              ingredientType: ing['ingredient_type'] ?? 'recipe',
              rowVersion: ing['row_version'] ?? 0,
              isDeleted: ing['is_deleted'] ?? false,
              lastModifiedHlc: ing['hlc'],
              isSynced: true,
            ),
          );
        }
      }

      // Apply Recipes (read-only from server)
      if (changes['recipes'] != null) {
        for (var r in changes['recipes']) {
          await db.into(db.recipes).insertOnConflictUpdate(
            RecipeLocal(
              id: r['id'],
              productId: r['product_id'],
              version: r['version'] ?? 1,
              isActive: r['is_active'] ?? true,
              notes: r['notes'],
              rowVersion: 0,
              isDeleted: r['is_deleted'] ?? false,
              lastModifiedHlc: r['hlc'],
              isSynced: true,
            ),
          );
        }
      }

      // Apply Recipe Ingredients (read-only from server)
      if (changes['recipe_ingredients'] != null) {
        for (var ri in changes['recipe_ingredients']) {
          await db.into(db.recipeIngredients).insertOnConflictUpdate(
            RecipeIngredientLocal(
              id: ri['id'],
              recipeId: ri['recipe_id'],
              ingredientId: ri['ingredient_id'],
              quantity: _toDouble(ri['quantity']),
              quantityUnit: ri['quantity_unit'],
              notes: ri['notes'],
              isOptional: ri['is_optional'] ?? false,
              rowVersion: 0,
              isDeleted: ri['is_deleted'] ?? false,
              lastModifiedHlc: ri['hlc'],
              isSynced: true,
            ),
          );
        }
      }

      // Apply Outlet Stock (ingredient stock per outlet, read-only from server)
      if (changes['outlet_stock'] != null) {
        for (var os in changes['outlet_stock']) {
          await db.into(db.outletStocks).insertOnConflictUpdate(
            OutletStockLocal(
              id: os['id'],
              outletId: os['outlet_id'],
              ingredientId: os['ingredient_id'],
              computedStock: _toDouble(os['computed_stock']),
              minStockBase: _toDouble(os['min_stock_base']),
              rowVersion: os['row_version'] ?? 0,
              isDeleted: os['is_deleted'] ?? false,
              lastModifiedHlc: os['hlc'],
              isSynced: true,
            ),
          );
        }
      }
    });
  }

  Future<void> _markAsSynced({
    required List<ProductLocal> products,
    required List<OrderLocal> orders,
    required List<OrderItemLocal> orderItems,
    required List<PaymentLocal> payments,
    required List<ShiftLocal> shifts,
    required List<CashActivityLocal> cashActivities,
  }) async {
    // Batch #18 Rule #3: Atomic UPDATE kolom `isSynced` saja — jangan
    // `batch.replace(table, snapshot)` yang overwrite seluruh row. Kalau
    // pake replace, mutation lokal yang terjadi saat sync window berjalan
    // (misal: PNCounter decrement stok dari sale baru, status update dari
    // _applyServerChanges di dalam sync yang sama) bakal di-CLOBBER kembali
    // ke snapshot pre-sync → data loss.
    //
    // `batch.update(table, Companion(isSynced: Value(true)), where: id=...)`
    // cuma nyentuh 1 kolom, preserve kolom lain apa adanya saat query dibuat.
    await db.batch((batch) {
      for (var p in products) {
        batch.update(
          db.products,
          const ProductsCompanion(isSynced: drift.Value(true)),
          where: (t) => t.id.equals(p.id),
        );
      }
      for (var o in orders) {
        batch.update(
          db.orders,
          const OrdersCompanion(isSynced: drift.Value(true)),
          where: (t) => t.id.equals(o.id),
        );
      }
      for (var oi in orderItems) {
        batch.update(
          db.orderItems,
          const OrderItemsCompanion(isSynced: drift.Value(true)),
          where: (t) => t.id.equals(oi.id),
        );
      }
      for (var p in payments) {
        batch.update(
          db.payments,
          const PaymentsCompanion(isSynced: drift.Value(true)),
          where: (t) => t.id.equals(p.id),
        );
      }
      for (var s in shifts) {
        batch.update(
          db.shifts,
          const ShiftsCompanion(isSynced: drift.Value(true)),
          where: (t) => t.id.equals(s.id),
        );
      }
      for (var ca in cashActivities) {
        batch.update(
          db.cashActivities,
          const CashActivitiesCompanion(isSynced: drift.Value(true)),
          where: (t) => t.id.equals(ca.id),
        );
      }
    });
  }

  Map<String, dynamic> _productToJson(ProductLocal p) => {
    'id': p.id,
    'brand_id': p.brandId,
    'category_id': p.categoryId,
    'name': p.name,
    'description': p.description,
    'base_price': p.basePrice,
    'sku': p.sku,
    'barcode': p.barcode,
    'image_url': p.imageUrl,
    'stock_enabled': p.stockEnabled,
    'stock_qty': p.stockQty,
    // Pure CRDT: kirim kedua G-Counter agar backend bisa merge dengan benar
    'crdt_positive': p.crdtPositive,
    'crdt_negative': p.crdtNegative,
    'is_active': p.isActive,
    'row_version': p.rowVersion,
    'is_deleted': p.isDeleted,
    'hlc': p.lastModifiedHlc,
  };

  Map<String, dynamic> _orderToJson(OrderLocal o) => {
    'id': o.id,
    'outlet_id': o.outletId,
    'shift_session_id': o.shiftSessionId,
    'customer_id': o.customerId,
    'table_id': o.tableId,
    'user_id': o.userId,
    'order_number': o.orderNumber,
    'display_number': o.displayNumber,
    'status': o.status,
    'order_type': o.orderType,
    'subtotal': o.subtotal,
    'service_charge_amount': o.serviceChargeAmount,
    'tax_amount': o.taxAmount,
    'discount_amount': o.discountAmount,
    'total_amount': o.totalAmount,
    'notes': o.notes,
    'created_at': o.createdAt?.toIso8601String(),
    'updated_at': o.updatedAt?.toIso8601String(),
    'row_version': o.rowVersion,
    'is_deleted': o.isDeleted,
    'hlc': o.lastModifiedHlc,
  };

  Map<String, dynamic> _orderItemToJson(OrderItemLocal oi) => {
    'id': oi.id,
    'order_id': oi.orderId,
    'product_id': oi.productId,
    'product_variant_id': oi.productVariantId,
    'quantity': oi.quantity,
    'unit_price': oi.unitPrice,
    'discount_amount': oi.discountAmount,
    'total_price': oi.totalPrice,
    'modifiers': oi.modifiers,
    'notes': oi.notes,
    'row_version': oi.rowVersion,
    'is_deleted': oi.isDeleted,
    'hlc': oi.lastModifiedHlc,
  };

  Map<String, dynamic> _paymentToJson(PaymentLocal p) => {
    'id': p.id,
    'order_id': p.orderId,
    'outlet_id': p.outletId,
    'shift_session_id': p.shiftSessionId,
    'amount_due': p.amountDue,
    'amount_paid': p.amountPaid,
    'payment_method': p.paymentMethod,
    'status': p.status,
    'reference_number': p.referenceNumber,
    'paid_at': p.paidAt?.toIso8601String(),
    'row_version': p.rowVersion,
    'is_deleted': p.isDeleted,
    'hlc': p.lastModifiedHlc,
  };

  Map<String, dynamic> _shiftToJson(ShiftLocal s) => {
    'id': s.id,
    'outlet_id': s.outletId,
    'user_id': s.userId,
    'status': s.status,
    'start_time': s.startTime.toIso8601String(),
    'end_time': s.endTime?.toIso8601String(),
    'starting_cash': s.startingCash,
    'ending_cash': s.endingCash,
    'expected_ending_cash': s.expectedEndingCash,
    'notes': s.notes,
    'row_version': s.rowVersion,
    'is_deleted': s.isDeleted,
    'hlc': s.lastModifiedHlc,
  };

  static double _toDouble(dynamic v, {double fallback = 0.0}) {
    if (v == null) return fallback;
    if (v is num) return v.toDouble();
    return double.tryParse(v.toString()) ?? fallback;
  }

  Map<String, dynamic> _cashActivityToJson(CashActivityLocal ca) => {
    'id': ca.id,
    'shift_id': ca.shiftId,
    'activity_type': ca.activityType,
    'amount': ca.amount,
    'description': ca.description,
    'row_version': ca.rowVersion,
    'is_deleted': ca.isDeleted,
    'hlc': ca.lastModifiedHlc,
  };
}
