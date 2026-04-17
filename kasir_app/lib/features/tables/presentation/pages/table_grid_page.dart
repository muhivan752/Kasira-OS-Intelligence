import 'package:flutter/material.dart';
import 'package:lucide_icons/lucide_icons.dart';
import 'package:dio/dio.dart';
import '../../../../core/config/app_config.dart';
import '../../../../core/services/session_cache.dart';
import '../../../../core/theme/app_colors.dart';

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


class TableGridPage extends StatefulWidget {
  final void Function(TableModel table)? onTableSelected;

  const TableGridPage({super.key, this.onTableSelected});

  @override
  State<TableGridPage> createState() => _TableGridPageState();
}

class _TableGridPageState extends State<TableGridPage> {
  TableStatus? _filterStatus;
  List<TableModel> _tables = [];
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _isLoading = true);
    try {
      final cache = SessionCache.instance;

      final dio = Dio(BaseOptions(baseUrl: AppConfig.apiV1, connectTimeout: const Duration(seconds: 15), receiveTimeout: const Duration(seconds: 15)));
      final res = await dio.get(
        '/tables/',
        queryParameters: {'outlet_id': cache.outletId},
        options: Options(headers: cache.authHeaders),
      );

      final list = (res.data['data'] as List? ?? []).map((t) {
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

      if (mounted) setState(() { _tables = list; _isLoading = false; });
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
      backgroundColor: AppColors.background,
      body: Column(
        children: [
          // Header
          Container(
            padding: const EdgeInsets.fromLTRB(24, 16, 24, 16),
            color: AppColors.surface,
            child: Row(
              children: [
                const Icon(LucideIcons.layoutGrid, color: AppColors.primary),
                const SizedBox(width: 12),
                Text('Denah Meja', style: Theme.of(context).textTheme.titleLarge),
                const Spacer(),
                Text(
                  '$available tersedia • $occupied terisi',
                  style: const TextStyle(color: AppColors.textSecondary, fontSize: 14),
                ),
              ],
            ),
          ),

          // Status filter chips
          Container(
            height: 60,
            color: AppColors.surface,
            child: ListView(
              scrollDirection: Axis.horizontal,
              padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
              children: [
                _buildFilterChip(null, 'Semua', AppColors.primary),
                const SizedBox(width: 8),
                _buildFilterChip(TableStatus.available, 'Tersedia ($available)', AppColors.success),
                const SizedBox(width: 8),
                _buildFilterChip(TableStatus.occupied, 'Terisi ($occupied)', AppColors.error),
                const SizedBox(width: 8),
                _buildFilterChip(TableStatus.reserved, 'Reservasi ($reserved)', AppColors.warning),
                const SizedBox(width: 8),
                _buildFilterChip(TableStatus.dirty, 'Perlu Dibersihkan ($dirty)', AppColors.textSecondary),
              ],
            ),
          ),

          const SizedBox(height: 1),

          // Summary stats
          Padding(
            padding: const EdgeInsets.fromLTRB(24, 16, 24, 8),
            child: Row(
              children: [
                _buildStatBadge('Tersedia', available, AppColors.success),
                const SizedBox(width: 12),
                _buildStatBadge('Terisi', occupied, AppColors.error),
                const SizedBox(width: 12),
                _buildStatBadge('Reservasi', reserved, AppColors.warning),
                const SizedBox(width: 12),
                _buildStatBadge('Kotor', dirty, AppColors.textSecondary),
              ],
            ),
          ),

          // Table grid
          Expanded(
            child: _isLoading
                ? const Center(child: CircularProgressIndicator())
                : _tables.isEmpty
                    ? const Center(child: Text('Belum ada meja. Tambah di Owner Dashboard.', style: TextStyle(color: AppColors.textSecondary)))
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
          border: Border.all(color: isSelected ? color : AppColors.border),
        ),
        child: Text(
          label,
          style: TextStyle(
            color: isSelected ? color : AppColors.textSecondary,
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

  Widget _buildTableCard(TableModel table) {
    final config = _statusConfig(table.status);
    final isSelectable = table.status == TableStatus.available;

    return GestureDetector(
      onTap: () {
        if (widget.onTableSelected != null) {
          widget.onTableSelected!(table);
        } else if (table.status == TableStatus.occupied) {
          _showTableDetail(table);
        } else if (isSelectable) {
          _showTableDetail(table);
        }
      },
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        decoration: BoxDecoration(
          color: config.bgColor,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: config.borderColor, width: 2),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(0.04),
              blurRadius: 8,
              offset: const Offset(0, 2),
            ),
          ],
        ),
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(config.icon, color: config.iconColor, size: 20),
                const Spacer(),
                if (table.status == TableStatus.occupied && table.eta != null)
                  _buildEtaBadge(table.eta!),
              ],
            ),
            const Spacer(),
            Text(
              table.name,
              style: TextStyle(
                fontWeight: FontWeight.bold,
                fontSize: 16,
                color: config.textColor,
              ),
            ),
            const SizedBox(height: 4),
            Row(
              children: [
                Icon(LucideIcons.users, size: 12, color: config.textColor.withOpacity(0.6)),
                const SizedBox(width: 4),
                Text(
                  '${table.capacity} kursi',
                  style: TextStyle(color: config.textColor.withOpacity(0.6), fontSize: 12),
                ),
              ],
            ),
            if (table.status == TableStatus.occupied && table.occupiedSince != null) ...[
              const SizedBox(height: 4),
              Row(
                children: [
                  Icon(LucideIcons.clock, size: 12, color: config.textColor.withOpacity(0.6)),
                  const SizedBox(width: 4),
                  Text(
                    'Sejak ${table.occupiedSince}',
                    style: TextStyle(color: config.textColor.withOpacity(0.6), fontSize: 11),
                  ),
                ],
              ),
            ],
            const SizedBox(height: 8),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
              decoration: BoxDecoration(
                color: config.badgeColor,
                borderRadius: BorderRadius.circular(6),
              ),
              child: Text(
                config.statusLabel,
                style: TextStyle(
                  color: config.iconColor,
                  fontSize: 11,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ),
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
        color: isUrgent ? AppColors.error : AppColors.warning,
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
          bgColor: AppColors.success.withOpacity(0.10),
          borderColor: AppColors.success,
          icon: LucideIcons.checkCircle2,
          iconColor: AppColors.success,
          textColor: AppColors.success,
          badgeColor: AppColors.success.withOpacity(0.18),
          statusLabel: 'Tersedia',
        );
      case TableStatus.occupied:
        return _TableStatusConfig(
          bgColor: AppColors.error.withOpacity(0.10),
          borderColor: AppColors.error,
          icon: LucideIcons.users,
          iconColor: AppColors.error,
          textColor: AppColors.error,
          badgeColor: AppColors.error.withOpacity(0.18),
          statusLabel: 'Terisi',
        );
      case TableStatus.reserved:
        return _TableStatusConfig(
          bgColor: AppColors.warning.withOpacity(0.10),
          borderColor: AppColors.warning,
          icon: LucideIcons.calendarCheck2,
          iconColor: AppColors.warning,
          textColor: AppColors.warning,
          badgeColor: AppColors.warning.withOpacity(0.18),
          statusLabel: 'Reservasi',
        );
      case TableStatus.dirty:
        return _TableStatusConfig(
          bgColor: AppColors.surfaceVariant,
          borderColor: AppColors.border,
          icon: LucideIcons.alertTriangle,
          iconColor: AppColors.textSecondary,
          textColor: AppColors.textSecondary,
          badgeColor: AppColors.surfaceElevated,
          statusLabel: 'Perlu Dibersihkan',
        );
    }
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
