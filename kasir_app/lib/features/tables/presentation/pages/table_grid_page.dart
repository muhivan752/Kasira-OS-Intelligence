import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';
import 'package:dio/dio.dart';
import '../../../../core/config/app_config.dart';
import '../../../../core/services/session_cache.dart';
import '../../../../core/theme/kasira_ds.dart';
import '../../../reservations/presentation/pages/reservation_list_page.dart';
import '../../../pos/providers/cart_provider.dart';
import '../../../pos/providers/pos_mode_provider.dart';
import '../../../tabs/presentation/widgets/guest_count_sheet.dart';

enum TableStatus { available, occupied, reserved, dirty }

class TableModel {
  final String id;
  final String name;
  final int capacity;
  final TableStatus status;
  final String? currentOrderId;
  final String? occupiedSince;
  final int? eta; // minutes remaining (untuk kitchen display)

  const TableModel({
    required this.id,
    required this.name,
    required this.capacity,
    required this.status,
    this.currentOrderId,
    this.occupiedSince,
    this.eta,
  });
}


class TableGridPage extends ConsumerStatefulWidget {
  final void Function(TableModel table)? onTableSelected;

  const TableGridPage({super.key, this.onTableSelected});

  @override
  ConsumerState<TableGridPage> createState() => _TableGridPageState();
}

class _TableGridPageState extends ConsumerState<TableGridPage> {
  TableStatus? _filterStatus;
  List<TableModel> _tables = [];
  // Map table_id → tab.status untuk render sub-badge di occupied cards.
  // Active states only (open/asking_bill/splitting). Empty kalau gak ada
  // active tab di table tsb. Refreshed bareng dgn _load.
  Map<String, String> _tabStatusByTable = {};
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    // Optimistic: spinner full-screen HANYA saat load pertama (belum ada data).
    // Refresh berikutnya jalan diam-diam, grid lama tetap tampil.
    if (_tables.isEmpty) setState(() => _isLoading = true);
    try {
      final cache = SessionCache.instance;

      final dio = Dio(BaseOptions(baseUrl: AppConfig.apiV1, connectTimeout: const Duration(seconds: 15), receiveTimeout: const Duration(seconds: 15)));

      // Paralel: fetch tables + active tabs sekaligus untuk minimize roundtrip.
      // /tabs/ tanpa status filter return semua — client-side filter ke active.
      final results = await Future.wait([
        dio.get(
          '/tables/',
          queryParameters: {'outlet_id': cache.outletId},
          options: Options(headers: cache.authHeaders),
        ),
        dio.get(
          '/tabs/',
          queryParameters: {'outlet_id': cache.outletId},
          options: Options(headers: cache.authHeaders),
        ).catchError((_) {
          // Tabs fetch gagal? Fallback empty — table grid tetap render
          // tanpa sub-badge, no crash.
          return Response(
            requestOptions: RequestOptions(path: '/tabs/'),
            data: {'data': []},
            statusCode: 200,
          );
        }),
      ]);

      final tablesRes = results[0];
      final tabsRes = results[1];

      final list = (tablesRes.data['data'] as List? ?? []).map((t) {
        final statusStr = t['status'] as String? ?? 'available';
        final status = TableStatus.values.firstWhere(
          (s) => s.name == statusStr,
          orElse: () => TableStatus.available,
        );
        return TableModel(
          id: t['id'] as String,
          name: t['name'] as String,
          capacity: (t['capacity'] as num?)?.toInt() ?? 2,
          status: status,
        );
      }).toList();

      // Build map table_id → tab.status untuk active tabs only
      final tabStatusMap = <String, String>{};
      const activeStates = {'open', 'asking_bill', 'splitting'};
      for (final t in (tabsRes.data['data'] as List? ?? [])) {
        final tabStatus = t['status'] as String? ?? '';
        final tableId = t['table_id'] as String?;
        if (tableId != null && activeStates.contains(tabStatus)) {
          // Kalau ada multi tab per table (edge case), pick yang most recent
          // (backend sort created_at desc) — first hit wins.
          tabStatusMap.putIfAbsent(tableId, () => tabStatus);
        }
      }

      if (mounted) setState(() {
        _tables = list;
        _tabStatusByTable = tabStatusMap;
        _isLoading = false;
      });
    } catch (_) {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  List<TableModel> get _filteredTables {
    if (_filterStatus == null) return _tables;
    return _tables.where((t) => t.status == _filterStatus).toList();
  }

  @override
  Widget build(BuildContext context) {
    final available = _tables.where((t) => t.status == TableStatus.available).length;
    final occupied = _tables.where((t) => t.status == TableStatus.occupied).length;
    final reserved = _tables.where((t) => t.status == TableStatus.reserved).length;
    final dirty = _tables.where((t) => t.status == TableStatus.dirty).length;

    return Scaffold(
      backgroundColor: KasiraDS.bgBase,
      body: Column(
        children: [
          // Header
          Container(
            padding: const EdgeInsets.fromLTRB(20, 14, 20, 14),
            color: KasiraDS.surfaceCard,
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                Text('Meja', style: KasiraDS.display(size: 22, color: KasiraDS.textStrong)),
                const Spacer(),
                Text(
                  '$occupied terisi · $available kosong',
                  style: KasiraDS.sans(size: 12.5, weight: FontWeight.w600, color: KasiraDS.textMuted),
                ),
                // Reservasi (di desain = sub-tab Meja). Cuma saat standalone,
                // bukan pas dipakai di flow POS dine-in (onTableSelected != null).
                if (widget.onTableSelected == null) ...[
                  const SizedBox(width: 10),
                  InkWell(
                    onTap: () => Navigator.push(context,
                        MaterialPageRoute(builder: (_) => const ReservationListPage())),
                    borderRadius: KasiraDS.brPill,
                    child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 7),
                      decoration: BoxDecoration(
                        color: KasiraDS.brandTint2,
                        borderRadius: KasiraDS.brPill,
                      ),
                      child: Row(mainAxisSize: MainAxisSize.min, children: [
                        const Icon(LucideIcons.calendarCheck, size: 14, color: KasiraDS.brandSecondary),
                        const SizedBox(width: 5),
                        Text('Reservasi',
                            style: KasiraDS.sans(size: 12, weight: FontWeight.w700, color: KasiraDS.brandSecondary)),
                      ]),
                    ),
                  ),
                ],
              ],
            ),
          ),

          // (Desain Meja: langsung ke grid — tanpa filter chips / stat badges.)
          const SizedBox(height: 6),

          // Table grid
          Expanded(
            child: (_isLoading && _tables.isEmpty)
                ? const Center(child: CircularProgressIndicator())
                : _tables.isEmpty
                    ? const Center(child: Text('Belum ada meja. Tambah di Owner Dashboard.', style: TextStyle(color: KasiraDS.textMuted)))
                    : Padding(
                        padding: const EdgeInsets.fromLTRB(24, 8, 24, 24),
                        child: GridView.builder(
                          gridDelegate: const SliverGridDelegateWithMaxCrossAxisExtent(
                            maxCrossAxisExtent: 200,
                            childAspectRatio: 1.0,
                            crossAxisSpacing: 16,
                            mainAxisSpacing: 16,
                          ),
                          itemCount: _filteredTables.length,
                          itemBuilder: (context, index) {
                            return _buildTableCard(_filteredTables[index]);
                          },
                        ),
                      ),
          ),
        ],
      ),
    );
  }

  Widget _buildFilterChip(TableStatus? status, String label, Color color) {
    final isSelected = _filterStatus == status;
    return GestureDetector(
      onTap: () => setState(() => _filterStatus = status),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
        decoration: BoxDecoration(
          color: isSelected ? color.withOpacity(0.15) : Colors.transparent,
          borderRadius: BorderRadius.circular(20),
          border: Border.all(color: isSelected ? color : KasiraDS.borderSubtle),
        ),
        child: Text(
          label,
          style: TextStyle(
            color: isSelected ? color : KasiraDS.textMuted,
            fontSize: 13,
            fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
          ),
        ),
      ),
    );
  }

  Widget _buildStatBadge(String label, int count, Color color) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(width: 8, height: 8, decoration: BoxDecoration(color: color, shape: BoxShape.circle)),
          const SizedBox(width: 6),
          Text('$count $label', style: TextStyle(color: color, fontWeight: FontWeight.w600, fontSize: 13)),
        ],
      ),
    );
  }

  /// Sub-badge config untuk occupied table — show tab.status spesifik
  /// supaya owner langsung tau "split bill in progress" / "minta bill"
  /// tanpa harus tap dulu.
  ({Color color, String label, IconData icon})? _tabSubBadge(String? tabStatus) {
    switch (tabStatus) {
      case 'splitting':
        return (color: KasiraDS.info, label: 'Split Bill', icon: LucideIcons.split);
      case 'asking_bill':
        return (color: KasiraDS.warning, label: 'Minta Bill', icon: LucideIcons.receipt);
      default:
        return null;
    }
  }

  Widget _buildTableCard(TableModel table) {
    final config = _statusConfig(table.status);
    final isSelectable = table.status == TableStatus.available;
    final subBadge = table.status == TableStatus.occupied
        ? _tabSubBadge(_tabStatusByTable[table.id])
        : null;

    final isOccupied = table.status == TableStatus.occupied;
    return GestureDetector(
      onTap: () {
        if (widget.onTableSelected != null) {
          widget.onTableSelected!(table);
        } else if (table.status == TableStatus.occupied) {
          _openTabForTable(table);
        } else if (isSelectable) {
          _startDineInFromMeja(table);
        }
      },
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        decoration: BoxDecoration(
          color: isOccupied ? config.bgColor : KasiraDS.surfaceCard,
          borderRadius: KasiraDS.brLg,
          border: Border.all(
            color: isOccupied ? config.borderColor.withOpacity(0.5) : KasiraDS.borderSubtle,
          ),
          boxShadow: KasiraDS.shadowSm,
        ),
        padding: const EdgeInsets.all(15),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // name + status dot
            Row(
              children: [
                Expanded(
                  child: Text(
                    table.name,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: KasiraDS.display(size: 16, color: KasiraDS.textStrong),
                  ),
                ),
                Container(width: 7, height: 7,
                    decoration: BoxDecoration(color: config.iconColor, shape: BoxShape.circle)),
                const SizedBox(width: 5),
                Text(config.statusLabel,
                    style: KasiraDS.sans(size: 10.5, weight: FontWeight.w700, color: config.iconColor)),
              ],
            ),
            const SizedBox(height: 9),
            // seats
            Row(
              children: [
                const Icon(LucideIcons.users, size: 13, color: KasiraDS.textMuted),
                const SizedBox(width: 5),
                Text('${table.capacity} kursi',
                    style: KasiraDS.sans(size: 12, weight: FontWeight.w600, color: KasiraDS.textMuted)),
                if (isOccupied && table.eta != null) ...[
                  const Spacer(),
                  _buildEtaBadge(table.eta!),
                ],
              ],
            ),
            const Spacer(),
            // bottom affordance
            if (isOccupied)
              Row(
                children: [
                  if (subBadge != null) ...[
                    Icon(subBadge.icon, size: 12, color: subBadge.color),
                    const SizedBox(width: 4),
                    Flexible(
                      child: Text(subBadge.label,
                          overflow: TextOverflow.ellipsis,
                          style: KasiraDS.sans(size: 11, weight: FontWeight.w700, color: subBadge.color)),
                    ),
                  ] else if (table.occupiedSince != null)
                    Text('Buka ${table.occupiedSince}',
                        style: KasiraDS.sans(size: 11.5, weight: FontWeight.w600, color: KasiraDS.textMuted))
                  else
                    Text('Lihat pesanan',
                        style: KasiraDS.sans(size: 11.5, weight: FontWeight.w700, color: config.iconColor)),
                ],
              )
            else if (table.status == TableStatus.available)
              Text('+ Buka meja',
                  style: KasiraDS.sans(size: 12, weight: FontWeight.w700, color: KasiraDS.brandPrimary))
            else if (table.status == TableStatus.reserved)
              Text('Reservasi',
                  style: KasiraDS.sans(size: 11.5, weight: FontWeight.w700, color: KasiraDS.warning))
            else
              Text('Perlu dibersihkan',
                  style: KasiraDS.sans(size: 11.5, weight: FontWeight.w600, color: KasiraDS.textMuted)),
          ],
        ),
      ),
    );
  }

  Widget _buildEtaBadge(int etaMinutes) {
    final isUrgent = etaMinutes <= 5;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
      decoration: BoxDecoration(
        color: isUrgent ? KasiraDS.danger : KasiraDS.warning,
        borderRadius: BorderRadius.circular(6),
      ),
      child: Text(
        etaMinutes == 0 ? 'SIAP' : '${etaMinutes}m',
        style: const TextStyle(color: Colors.white, fontSize: 11, fontWeight: FontWeight.bold),
      ),
    );
  }

  _TableStatusConfig _statusConfig(TableStatus status) {
    switch (status) {
      case TableStatus.available:
        return _TableStatusConfig(
          bgColor: KasiraDS.success.withOpacity(0.10),
          borderColor: KasiraDS.success,
          icon: LucideIcons.checkCircle2,
          iconColor: KasiraDS.success,
          textColor: KasiraDS.success,
          badgeColor: KasiraDS.success.withOpacity(0.18),
          statusLabel: 'Tersedia',
        );
      case TableStatus.occupied:
        return _TableStatusConfig(
          bgColor: KasiraDS.danger.withOpacity(0.10),
          borderColor: KasiraDS.danger,
          icon: LucideIcons.users,
          iconColor: KasiraDS.danger,
          textColor: KasiraDS.danger,
          badgeColor: KasiraDS.danger.withOpacity(0.18),
          statusLabel: 'Terisi',
        );
      case TableStatus.reserved:
        return _TableStatusConfig(
          bgColor: KasiraDS.warning.withOpacity(0.10),
          borderColor: KasiraDS.warning,
          icon: LucideIcons.calendarCheck2,
          iconColor: KasiraDS.warning,
          textColor: KasiraDS.warning,
          badgeColor: KasiraDS.warning.withOpacity(0.18),
          statusLabel: 'Reservasi',
        );
      case TableStatus.dirty:
        return _TableStatusConfig(
          bgColor: KasiraDS.surfaceSunken,
          borderColor: KasiraDS.borderSubtle,
          icon: LucideIcons.alertTriangle,
          iconColor: KasiraDS.textMuted,
          textColor: KasiraDS.textMuted,
          badgeColor: KasiraDS.surfaceCard,
          statusLabel: 'Perlu Dibersihkan',
        );
    }
  }

  Future<void> _openTabForTable(TableModel table) async {
    final cache = SessionCache.instance;
    final loadingDialog = showDialog(
      context: context,
      barrierDismissible: false,
      builder: (_) => const Center(child: CircularProgressIndicator()),
    );
    try {
      final dio = Dio(BaseOptions(
        baseUrl: AppConfig.apiV1,
        connectTimeout: const Duration(seconds: 10),
        receiveTimeout: const Duration(seconds: 10),
      ));
      // Pakai /tabs/by-table/{table_id} yang filter SEMUA active state
      // (open, asking_bill, splitting) di backend. Sebelumnya pake
      // /tabs/?status=open yang miss split-bill in-progress → user
      // confused karena meja occupied tapi snackbar bilang "tidak ada tab".
      final res = await dio.get(
        '/tabs/by-table/${table.id}',
        queryParameters: {'outlet_id': cache.outletId},
        options: Options(headers: cache.authHeaders),
      );
      if (mounted) Navigator.of(context, rootNavigator: true).pop();
      final tabData = res.data['data'];
      if (tabData == null) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text('Tidak ada tab aktif di ${table.name}'),
              backgroundColor: KasiraDS.warning,
            ),
          );
        }
        return;
      }
      final tabId = tabData['id'] as String;
      if (mounted) context.push('/tabs/$tabId');
    } catch (e) {
      if (mounted) Navigator.of(context, rootNavigator: true).pop();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Gagal memuat tab: $e'), backgroundColor: KasiraDS.danger),
        );
      }
    }
    // Ignore linter for unused loadingDialog future
    loadingDialog.ignore();
  }

  /// Tab Meja standalone: tap meja kosong → tanya jumlah tamu → dine-in + lompat
  /// ke Kasir. (Desain: Meja → tap meja → order.)
  ///
  /// Jumlah tamu WAJIB ditanya di sini. Dulu cabang ini manggil setTable() tanpa
  /// guestCount sementara cabang POS nanya, jadi tab yang dibuka lewat tab Meja
  /// selalu kecatat 1 orang dan split "bagi rata" jadi gak kepake.
  Future<void> _startDineInFromMeja(TableModel table) async {
    final guestCount = await showGuestCountSheet(context, tableName: table.name);
    if (guestCount == null || !mounted) return; // user batal

    final cart = ref.read(cartProvider.notifier);
    cart.setTable(table.id, name: table.name, guestCount: guestCount);
    cart.setOrderType('Dine In');
    ref.read(posModeProvider.notifier).state = PosMode.dineInOrdering;
    // Shell (dashboard) consume flag ini → pindah ke tab Kasir.
    ref.read(pendingNavigateToPosProvider.notifier).state = true;
  }

  void _showTableDetail(TableModel table) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
        title: Text(table.name),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Kapasitas: ${table.capacity} kursi'),
            const SizedBox(height: 8),
            Text('Status: ${_statusConfig(table.status).statusLabel}'),
            if (table.currentOrderId != null) ...[
              const SizedBox(height: 8),
              Text('Order: ${table.currentOrderId}'),
            ],
          ],
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context), child: const Text('Tutup')),
          if (table.status == TableStatus.available)
            ElevatedButton(
              onPressed: () {
                Navigator.pop(context);
                widget.onTableSelected?.call(table);
              },
              child: const Text('Pilih Meja'),
            ),
        ],
      ),
    );
  }
}

class _TableStatusConfig {
  final Color bgColor;
  final Color borderColor;
  final IconData icon;
  final Color iconColor;
  final Color textColor;
  final Color badgeColor;
  final String statusLabel;

  _TableStatusConfig({
    required this.bgColor,
    required this.borderColor,
    required this.icon,
    required this.iconColor,
    required this.textColor,
    required this.badgeColor,
    required this.statusLabel,
  });
}
