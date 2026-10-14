import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';
import 'package:url_launcher/url_launcher.dart';
import '../../../../core/config/app_config.dart';
import '../../../../core/services/session_cache.dart';
import '../../../../core/sync/sync_provider.dart';
import '../../../../core/theme/kasira_ds.dart';
import '../../../online_orders/presentation/pages/online_orders_page.dart';
import '../../../orders/providers/orders_provider.dart';
import '../../../products/providers/products_provider.dart';
import '../../../shift/presentation/pages/shift_page.dart';
import 'managed_actions_page.dart';

/// Tab Beranda untuk akun staf (mode "managed").
///
/// Dulu staf punya layar terpisah (`ManagedWorkspacePage`): AppBar sendiri di
/// atas layar kasir (kepala dobel), tombol polos tanpa jarak, tanpa tampilan
/// tablet, dan wajib online. 14/10/2026 Ivan: staf memakai kerangka kasir yang
/// sama dengan pemilik (DashboardPage, tab disaring izin), dan tab Beranda
/// pemilik yang berisi omzet diganti layar ini: siapa saya, boleh offline
/// sampai kapan, outlet, lalu pintu ke kerjaan sesuai izin jabatan.
class StaffHomePage extends ConsumerStatefulWidget {
  const StaffHomePage({super.key, required this.onRefreshAccess});

  /// Muat ulang manifest akses (DashboardPage yang memegang caranya).
  final Future<void> Function() onRefreshAccess;

  @override
  ConsumerState<StaffHomePage> createState() => _StaffHomePageState();
}

class _StaffHomePageState extends ConsumerState<StaffHomePage> {
  final _cache = SessionCache.instance;
  bool _busy = false;

  Future<void> _refresh() async {
    setState(() => _busy = true);
    try {
      await widget.onRefreshAccess();
      final service = ref.read(syncServiceProvider);
      await service.sync();
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Text(service.status == SyncStatus.success
              ? 'Izin dan data kasir sudah diperbarui.'
              : 'Belum tersambung. Transaksi yang sudah tercatat tetap aman di HP ini.')));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  String _offlineLine() {
    if (!_cache.allows('pos.sell')) return 'Akun ini tidak untuk berjualan.';
    final left = _cache.offlineGraceLeft ?? Duration.zero;
    if (left == Duration.zero) return sefStafOfflineHabis;
    final h = left.inHours;
    final m = left.inMinutes % 60;
    final sisa = h > 0 ? '$h jam ${m > 0 ? '$m menit' : ''}'.trim() : '$m menit';
    return 'Kasir tetap jalan tanpa internet sampai $sisa lagi. Sambung ke internet sebentar untuk memperpanjang.';
  }

  @override
  Widget build(BuildContext context) {
    final actions = <({IconData icon, String label, VoidCallback onTap})>[
      if (_cache.allows('pos.sell'))
        (
          icon: LucideIcons.bellRing,
          label: 'Pesanan online',
          onTap: () => Navigator.push(context,
              MaterialPageRoute(builder: (_) => const OnlineOrdersPage())),
        ),
      if (_cache.allows('pos.shift.manage'))
        (
          icon: LucideIcons.wallet,
          label: 'Sesi kas',
          onTap: () => Navigator.push(
              context, MaterialPageRoute(builder: (_) => const ShiftPage())),
        ),
      if (_cache.allows('pos.cash.manage'))
        (icon: LucideIcons.notebookPen, label: 'Catatan kas', onTap: () => _open(ManagedAction.cash)),
      if (_cache.allows('pos.refund') || _cache.allows('pos.refund.approve'))
        (icon: LucideIcons.undo2, label: 'Pengajuan refund', onTap: () => _open(ManagedAction.refunds)),
      if (_cache.allows('pos.kitchen'))
        (icon: LucideIcons.chefHat, label: 'Pesanan dapur', onTap: () => _open(ManagedAction.kitchen)),
      if (_cache.allows('stock.view'))
        (
          icon: LucideIcons.package,
          label: _cache.allows('stock.receive') || _cache.allows('stock.adjust')
              ? 'Kelola stok di web'
              : 'Lihat stok di web',
          onTap: () => launchUrl(
              Uri.parse('${AppConfig.baseUrl}/dashboard/operasional'),
              mode: LaunchMode.externalApplication),
        ),
      (icon: LucideIcons.userRound, label: 'Akun dan kehadiran', onTap: () => context.go('/team')),
    ];
    final outlets = _cache.allowedOutlets;
    final outletId = outlets.any((o) => o['id'] == _cache.outletId) ? _cache.outletId : null;

    return Scaffold(
      backgroundColor: KasiraDS.bgBase,
      body: SafeArea(
        child: Align(
          alignment: Alignment.topCenter,
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 640),
            child: RefreshIndicator(
              onRefresh: _refresh,
              child: ListView(
                padding: const EdgeInsets.fromLTRB(KasiraDS.space5, KasiraDS.space6, KasiraDS.space5, KasiraDS.space8),
                children: [
                  Text(_cache.outletName ?? 'Toko', style: KasiraDS.sans(size: 26, weight: FontWeight.w800, color: KasiraDS.textStrong)),
                  if (_cache.roleName != null) ...[
                    const SizedBox(height: KasiraDS.space1),
                    Text('Jabatan: ${_cache.roleName}', style: KasiraDS.sans(size: 15, color: KasiraDS.textMuted)),
                  ],
                  const SizedBox(height: KasiraDS.space5),
                  _Card(
                    child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                      Icon(_cache.offlinePosAllowed ? LucideIcons.wifiOff : LucideIcons.wifi,
                          size: 20, color: KasiraDS.brandPrimary),
                      const SizedBox(width: KasiraDS.space3),
                      Expanded(child: Text(_offlineLine(), style: KasiraDS.sans(size: 14, color: KasiraDS.textBody, height: 1.4))),
                    ]),
                  ),
                  if (outlets.length > 1) ...[
                    const SizedBox(height: KasiraDS.space4),
                    DropdownButtonFormField<String>(
                      isExpanded: true,
                      initialValue: outletId,
                      decoration: const InputDecoration(labelText: 'Outlet'),
                      items: [
                        for (final o in outlets)
                          DropdownMenuItem(value: o['id'] as String, child: Text(o['name'] as String)),
                      ],
                      onChanged: (id) async {
                        if (id == null || id == _cache.outletId) return;
                        ref.read(syncServiceProvider).cancelInFlight();
                        await _cache.setOutletId(id);
                        await _cache.setShiftSessionId(null);
                        ref.invalidate(productsProvider);
                        ref.invalidate(ordersProvider);
                        await _cache.fetchAndCacheOutletInfo();
                        if (mounted) setState(() {});
                      },
                    ),
                  ],
                  const SizedBox(height: KasiraDS.space5),
                  for (final a in actions) ...[
                    _ActionTile(icon: a.icon, label: a.label, onTap: a.onTap),
                    const SizedBox(height: KasiraDS.space3),
                  ],
                  const SizedBox(height: KasiraDS.space2),
                  OutlinedButton.icon(
                    onPressed: _busy ? null : _refresh,
                    icon: _busy
                        ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2))
                        : const Icon(LucideIcons.refreshCw, size: 18),
                    label: const Text('Perbarui izin dan data'),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }

  void _open(ManagedAction action) => Navigator.push(
      context, MaterialPageRoute(builder: (_) => ManagedActionsPage(action: action)));
}

class _Card extends StatelessWidget {
  const _Card({required this.child});
  final Widget child;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.all(KasiraDS.space4),
        decoration: BoxDecoration(
          color: KasiraDS.surfaceCard,
          borderRadius: BorderRadius.circular(KasiraDS.radiusLg),
          border: Border.all(color: KasiraDS.borderSubtle),
        ),
        child: child,
      );
}

class _ActionTile extends StatelessWidget {
  const _ActionTile({required this.icon, required this.label, required this.onTap});
  final IconData icon;
  final String label;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => Material(
        color: KasiraDS.surfaceCard,
        borderRadius: BorderRadius.circular(KasiraDS.radiusMd),
        child: InkWell(
          borderRadius: BorderRadius.circular(KasiraDS.radiusMd),
          onTap: onTap,
          child: Container(
            constraints: const BoxConstraints(minHeight: 56),
            padding: const EdgeInsets.symmetric(horizontal: KasiraDS.space4),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(KasiraDS.radiusMd),
              border: Border.all(color: KasiraDS.borderSubtle),
            ),
            child: Row(children: [
              Icon(icon, size: 20, color: KasiraDS.brandPrimary),
              const SizedBox(width: KasiraDS.space3),
              Expanded(child: Text(label, style: KasiraDS.sans(size: 15, weight: FontWeight.w700, color: KasiraDS.textStrong))),
              const Icon(LucideIcons.chevronRight, size: 18, color: KasiraDS.textMuted),
            ]),
          ),
        ),
      );
}
