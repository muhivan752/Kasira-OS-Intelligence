import 'dart:async';
import 'package:dio/dio.dart';
import '../../../../core/services/push_service.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:url_launcher/url_launcher.dart';
import '../../../../core/api/api_client.dart';
import '../../../../core/config/app_config.dart';
import '../../../../core/services/session_cache.dart';
import '../../../../core/sync/sync_provider.dart';
import 'managed_actions_page.dart';
import '../../../orders/presentation/pages/order_list_page.dart';
import '../../../orders/providers/orders_provider.dart';
import '../../../pos/presentation/pages/pos_page.dart';
import '../../../pos/providers/pos_mode_provider.dart';
import '../../../products/providers/products_provider.dart';
import '../../../shift/presentation/pages/shift_page.dart';
import '../../../online_orders/presentation/pages/online_orders_page.dart';

class ManagedWorkspacePage extends ConsumerStatefulWidget {
  const ManagedWorkspacePage({super.key});
  @override
  ConsumerState<ManagedWorkspacePage> createState() =>
      _ManagedWorkspacePageState();
}

class _ManagedWorkspacePageState extends ConsumerState<ManagedWorkspacePage>
    with WidgetsBindingObserver {
  bool _loading = true;
  String? _error;
  String _selected = 'home';
  final _cache = SessionCache.instance;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _refresh();
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) _refresh();
    if (state == AppLifecycleState.paused ||
        state == AppLifecycleState.hidden) {
      setState(() => _loading = true);
    }
  }

  Future<void> _refresh() async {
    if (mounted)
      setState(() {
        _loading = true;
        _error = null;
      });
    try {
      final dio = ref.read(apiClientProvider);
      final token = _cache.accessToken;
      final response = await dio.get('/auth/access');
      if (!mounted || token != _cache.accessToken) return;
      await _cache
          .applyAccess(Map<String, dynamic>.from(response.data['data'] as Map));
      if (!mounted) return;
      if (!_cache.allowedOutlets.any((o) => o['id'] == _cache.outletId)) {
        await _cache.setOutletId(
            _cache.allowedOutlets.firstOrNull?['id']?.toString() ?? '');
        await _cache.setShiftSessionId(null);
      }
      if (_cache.allows('pos.sell')) {
        unawaited(PushService.instance.daftar());
        PushService.instance.bukaTertunda();
      }
      ref.invalidate(productsProvider);
      ref.invalidate(ordersProvider);
      if (!_cache.allows('pos.sell')) _selected = 'home';
      if (ref.read(posModeProvider) != PosMode.selection &&
          _cache.allows('pos.sell')) _selected = 'pos';
    } on DioException catch (error) {
      final detail = error.response?.data?['detail'];
      _error = detail is Map
          ? detail['message']?.toString()
          : 'Akses belum dapat dimuat. Periksa koneksi internet.';
    } catch (_) {
      _error = 'Akses belum dapat dimuat. Coba lagi.';
    }
    if (mounted) setState(() => _loading = false);
  }

  @override
  Widget build(BuildContext context) {
    final destinations = <String, String>{
      'home': 'Operasional',
      if (_cache.allows('pos.sell')) 'pos': 'Kasir',
      if (_cache.allows('pos.sell') || _cache.allows('sales.detail.view'))
        'orders': 'Riwayat'
    };
    if (!destinations.containsKey(_selected)) _selected = 'home';
    ref.listen(pendingNavigateToPosProvider, (_, next) {
      if (next && _cache.allows('pos.sell')) {
        ref.read(pendingNavigateToPosProvider.notifier).state = false;
        setState(() => _selected = 'pos');
      }
    });
    final current = destinations.keys.toList().indexOf(_selected);
    return Scaffold(
      appBar: AppBar(title: const Text('Operasional toko'), actions: [
        IconButton(
            tooltip: 'Muat ulang akses',
            onPressed: _loading ? null : _refresh,
            icon: const Icon(Icons.refresh)),
        TextButton(
            onPressed: () => context.go('/team'), child: const Text('Akun'))
      ]),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
              ? Center(
                  child: Padding(
                      padding: const EdgeInsets.all(24),
                      child: Column(mainAxisSize: MainAxisSize.min, children: [
                        Text(_error!),
                        TextButton(
                            onPressed: _refresh, child: const Text('Coba lagi'))
                      ])))
              : _selected == 'pos'
                  ? const PosPage()
                  : _selected == 'orders'
                      ? const OrderListPage()
                      : ListView(padding: const EdgeInsets.all(24), children: [
                          Text(
                              'Akun staf perlu koneksi internet untuk bertransaksi. Antrean transaksi lama tetap disimpan jika izin berubah.',
                              style: Theme.of(context).textTheme.bodyLarge),
                          const SizedBox(height: 24),
                          DropdownButtonFormField<String>(
                              isExpanded: true,
                              initialValue: _cache.outletId?.isNotEmpty == true
                                  ? _cache.outletId
                                  : null,
                              decoration:
                                  const InputDecoration(labelText: 'Outlet'),
                              items: _cache.allowedOutlets
                                  .map((o) => DropdownMenuItem(
                                      value: o['id'] as String,
                                      child: Text(o['name'] as String)))
                                  .toList(),
                              onChanged: (id) async {
                                if (id == null) return;
                                ref.read(syncServiceProvider).cancelInFlight();
                                await _cache.setOutletId(id);
                                await _cache.setShiftSessionId(null);
                                ref.invalidate(productsProvider);
                                ref.invalidate(ordersProvider);
                                await _cache.fetchAndCacheOutletInfo();
                                if (mounted) setState(() {});
                              }),
                          const SizedBox(height: 24),
                          if (_cache.allows('pos.sell')) ...[
                            FilledButton(
                                onPressed: _cache.outletId?.isNotEmpty == true
                                    ? () => setState(() => _selected = 'pos')
                                    : null,
                                child: const Text('Buka kasir')),
                            OutlinedButton(
                                onPressed: () => Navigator.push(
                                    context,
                                    MaterialPageRoute(
                                        builder: (_) =>
                                            const OnlineOrdersPage())),
                                child: const Text('Pesanan online')),
                          ],
                          if (_cache.allows('stock.view'))
                            OutlinedButton(
                                onPressed: () => launchUrl(
                                    Uri.parse(
                                        '${AppConfig.baseUrl}/dashboard/operasional'),
                                    mode: LaunchMode.externalApplication),
                                child: Text(_cache.allows('stock.receive') || _cache.allows('stock.adjust') ? 'Kelola stok di web' : 'Lihat stok di web')),
                          if (_cache.allows('pos.shift.manage'))
                            OutlinedButton(
                                onPressed: () => Navigator.push(
                                    context,
                                    MaterialPageRoute(
                                        builder: (_) => const ShiftPage())),
                                child: const Text('Sesi kas')),
                          for (final entry in <ManagedAction, String>{
                            if (_cache.allows('pos.cash.manage'))
                              ManagedAction.cash: 'Catatan kas',
                            if (_cache.allows('pos.refund') ||
                                _cache.allows('pos.refund.approve'))
                              ManagedAction.refunds: 'Pengajuan refund',
                            if (_cache.allows('pos.kitchen'))
                              ManagedAction.kitchen: 'Pesanan dapur',
                          }.entries)
                            OutlinedButton(
                                onPressed: () => Navigator.push(
                                    context,
                                    MaterialPageRoute(
                                        builder: (_) => ManagedActionsPage(
                                            action: entry.key))),
                                child: Text(entry.value)),
                          if (['pos.sell', 'stock.view', 'sales.detail.view'].any(_cache.allows)) OutlinedButton(
                              onPressed: () async {
                                try {
                                  final service = ref.read(syncServiceProvider);
                                  await service.sync();
                                  if (service.status != SyncStatus.success)
                                    throw StateError('Data belum diperbarui');
                                  if (mounted)
                                    ScaffoldMessenger.of(context).showSnackBar(
                                        const SnackBar(
                                            content: Text(
                                                'Data diperbarui. Antrean transaksi lama tetap tersimpan untuk pemilik.')));
                                } catch (_) {
                                  if (mounted)
                                    ScaffoldMessenger.of(context).showSnackBar(
                                        const SnackBar(
                                            content: Text(
                                                'Data belum diperbarui. Antrean transaksi tetap tersimpan.')));
                                }
                              },
                              child: const Text('Perbarui data POS')),
                        ]),
      bottomNavigationBar: destinations.length < 2
          ? null
          : NavigationBar(
              selectedIndex: current,
              onDestinationSelected: _loading || _error != null
                  ? null
                  : (index) => setState(
                      () => _selected = destinations.keys.elementAt(index)),
              destinations: destinations.entries
                  .map((entry) => NavigationDestination(
                      icon: Icon(entry.key == 'pos'
                          ? Icons.shopping_bag_outlined
                          : entry.key == 'orders'
                              ? Icons.receipt_long_outlined
                              : Icons.store_outlined),
                      label: entry.value))
                  .toList()),
    );
  }
}
