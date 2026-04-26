import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../dashboard/providers/dashboard_provider.dart';
import '../../orders/providers/orders_provider.dart';
import '../../products/providers/products_provider.dart';
import '../../tabs/providers/tab_provider.dart';

/// P3 Quick Win #1: post-payment / post-sync provider refresh helper.
///
/// Pre-fix: 4 call sites (cart_panel.dart x2, pos_page.dart, payment_success_page.dart)
/// invalidate 3-4 providers SYNCHRONOUSLY → tiap widget yg `ref.watch` rebuild
/// blocking UI thread → 1-2 detik freeze setelah klik "Bayar".
///
/// Post-fix: defer ke microtask → navigation/snackbar paint dulu (instant <300ms),
/// providers refresh di background. User lihat success screen langsung, data refresh
/// pas dia balik ke dashboard (dgn loading indicator natural dari AsyncValue).
///
/// Single point of revert kalau cascade behavior perlu rollback.
void schedulePostPaymentRefresh(
  WidgetRef ref, {
  bool includeTabs = false,
}) {
  Future.microtask(() {
    ref.invalidate(dashboardProvider);
    ref.invalidate(ordersProvider);
    ref.invalidate(productsProvider);
    if (includeTabs) {
      ref.invalidate(activeTabsCountProvider);
    }
  });
}
