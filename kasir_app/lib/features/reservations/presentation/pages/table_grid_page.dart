import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:lucide_icons/lucide_icons.dart';
import '../../../../core/theme/app_colors.dart';
import '../../providers/table_provider.dart';
import '../../providers/reservation_provider.dart';

class ReservationTableGridPage extends ConsumerStatefulWidget {
  const ReservationTableGridPage({super.key});

  @override
  ConsumerState<ReservationTableGridPage> createState() => _ReservationTableGridPageState();
}

class _ReservationTableGridPageState extends ConsumerState<ReservationTableGridPage> {
  @override
  void initState() {
    super.initState();
    Future.microtask(() {
      ref.read(tableListProvider.notifier).fetchTables();
      ref.read(reservationProvider.notifier).fetchReservations();
    });
  }

  @override
  Widget build(BuildContext context) {
    final tableState = ref.watch(tableListProvider);
    final reservState = ref.watch(reservationProvider);

    // Build a map of table_id -> reservations for today
    final tableReservations = <String, List<ReservationModel>>{};
    for (final r in reservState.reservations) {
      if (r.tableId != null && ['pending', 'confirmed', 'seated'].contains(r.status)) {
        tableReservations.putIfAbsent(r.tableId!, () => []).add(r);
      }
    }

    // Group tables by floor section
    final sections = <String, List<TableInfo>>{};
    for (final t in tableState.tables.where((t) => t.isActive)) {
      final section = t.floorSection.isNotEmpty ? t.floorSection : 'Umum';
      sections.putIfAbsent(section, () => []).add(t);
    }

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
                Text('Denah Meja & Reservasi', style: Theme.of(context).textTheme.titleLarge),
                const Spacer(),
                IconButton(
                  onPressed: () {
                    ref.read(tableListProvider.notifier).fetchTables();
                    ref.read(reservationProvider.notifier).fetchReservations();
                  },
                  icon: const Icon(LucideIcons.refreshCw, size: 20, color: AppColors.textSecondary),
                ),
              ],
            ),
          ),

          // Legend
          Container(
            height: 52,
            color: AppColors.surface,
            child: ListView(
              scrollDirection: Axis.horizontal,
              padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 10),
              children: [
                _buildLegend(AppColors.success, 'Tersedia'),
                const SizedBox(width: 16),
                _buildLegend(AppColors.info, 'Reservasi'),
                const SizedBox(width: 16),
                _buildLegend(AppColors.error, 'Terisi'),
                const SizedBox(width: 16),
                _buildLegend(AppColors.textTertiary, 'Tutup'),
              ],
            ),
          ),

          // Content
          Expanded(
            child: tableState.isLoading
                ? const Center(child: CircularProgressIndicator())
                : tableState.error != null
                    ? Center(
                        child: TextButton.icon(
                          onPressed: () => ref.read(tableListProvider.notifier).fetchTables(),
                          icon: const Icon(LucideIcons.refreshCw, size: 16),
                          label: Text('${tableState.error} — tap retry'),
                        ),
                      )
                    : sections.isEmpty
                        ? const Center(
                            child: Text('Belum ada meja', style: TextStyle(color: AppColors.textSecondary)))
                        : ListView(
                            padding: const EdgeInsets.all(16),
                            children: sections.entries.map((entry) {
                              return Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Padding(
                                    padding: const EdgeInsets.only(left: 8, bottom: 12, top: 8),
                                    child: Text(
                                      entry.key,
                                      style: const TextStyle(
                                        fontWeight: FontWeight.bold,
                                        fontSize: 16,
                                        color: AppColors.textPrimary,
                                      ),
                                    ),
                                  ),
                                  GridView.builder(
                                    shrinkWrap: true,
                                    physics: const NeverScrollableScrollPhysics(),
                                    gridDelegate: const SliverGridDelegateWithMaxCrossAxisExtent(
                                      maxCrossAxisExtent: 180,
                                      childAspectRatio: 1.0,
                                      crossAxisSpacing: 12,
                                      mainAxisSpacing: 12,
                                    ),
                                    itemCount: entry.value.length,
                                    itemBuilder: (context, index) {
                                      final table = entry.value[index];
                                      final reservations = tableReservations[table.id] ?? [];
                                      return _buildTableCard(table, reservations);
                                    },
                                  ),
                                  const SizedBox(height: 16),
                                ],
                              );
                            }).toList(),
                          ),
          ),
        ],
      ),
    );
  }

  Widget _buildLegend(Color color, String label) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: 12,
          height: 12,
          decoration: BoxDecoration(color: color, borderRadius: BorderRadius.circular(3)),
        ),
        const SizedBox(width: 6),
        Text(label, style: const TextStyle(fontSize: 12, color: AppColors.textSecondary)),
      ],
    );
  }

  _TableDisplayConfig _getDisplayConfig(TableInfo table, List<ReservationModel> reservations) {
    // Check if any reservation is seated
    final hasSeated = reservations.any((r) => r.status == 'seated');
    final hasReservation = reservations.any((r) => r.status == 'pending' || r.status == 'confirmed');

    if (table.status == 'occupied' || hasSeated) {
      return _TableDisplayConfig(
        bgColor: const Color(0xFFFFF1F2),
        borderColor: AppColors.error,
        iconColor: AppColors.error,
        textColor: const Color(0xFF9F1239),
        statusLabel: 'Terisi',
        icon: LucideIcons.users,
      );
    } else if (hasReservation) {
      return _TableDisplayConfig(
        bgColor: const Color(0xFFEFF6FF),
        borderColor: AppColors.info,
        iconColor: AppColors.info,
        textColor: const Color(0xFF1E40AF),
        statusLabel: 'Reservasi',
        icon: LucideIcons.calendarCheck2,
      );
    } else if (table.status == 'closed' || !table.isActive) {
      return _TableDisplayConfig(
        bgColor: const Color(0xFFF9FAFB),
        borderColor: AppColors.border,
        iconColor: AppColors.textTertiary,
        textColor: AppColors.textTertiary,
        statusLabel: 'Tutup',
        icon: LucideIcons.lock,
      );
    } else {
      return _TableDisplayConfig(
        bgColor: const Color(0xFFF0FDF4),
        borderColor: AppColors.success,
        iconColor: AppColors.success,
        textColor: const Color(0xFF166534),
        statusLabel: 'Tersedia',
        icon: LucideIcons.checkCircle2,
      );
    }
  }

  Widget _buildTableCard(TableInfo table, List<ReservationModel> reservations) {
    final config = _getDisplayConfig(table, reservations);
    final nextReservation = reservations.isNotEmpty
        ? reservations.firstWhere(
            (r) => r.status == 'confirmed' || r.status == 'pending',
            orElse: () => reservations.first,
          )
        : null;

    return GestureDetector(
      onTap: () {
        if (nextReservation != null) {
          _showReservationDetail(nextReservation);
        }
      },
      child: Container(
        decoration: BoxDecoration(
          color: config.bgColor,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: config.borderColor, width: 2),
          boxShadow: [
            BoxShadow(color: Colors.black.withOpacity(0.04), blurRadius: 8, offset: const Offset(0, 2)),
          ],
        ),
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(config.icon, color: config.iconColor, size: 18),
                const Spacer(),
                if (reservations.isNotEmpty)
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                    decoration: BoxDecoration(
                      color: config.iconColor.withOpacity(0.2),
                      borderRadius: BorderRadius.circular(6),
                    ),
                    child: Text(
                      '${reservations.length}',
                      style: TextStyle(color: config.iconColor, fontSize: 11, fontWeight: FontWeight.bold),
                    ),
                  ),
              ],
            ),
            const Spacer(),
            Text(table.name,
                style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16, color: config.textColor)),
            const SizedBox(height: 4),
            Row(
              children: [
                Icon(LucideIcons.users, size: 12, color: config.textColor.withOpacity(0.6)),
                const SizedBox(width: 4),
                Text('${table.capacity} kursi',
                    style: TextStyle(color: config.textColor.withOpacity(0.6), fontSize: 12)),
              ],
            ),
            if (nextReservation != null) ...[
              const SizedBox(height: 6),
              Text(
                '${nextReservation.startTime.length >= 5 ? nextReservation.startTime.substring(0, 5) : nextReservation.startTime} ${nextReservation.customerName}',
                style: TextStyle(color: config.textColor.withOpacity(0.8), fontSize: 11),
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
              ),
            ],
            const SizedBox(height: 6),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
              decoration: BoxDecoration(
                color: config.iconColor.withOpacity(0.15),
                borderRadius: BorderRadius.circular(6),
              ),
              child: Text(
                config.statusLabel,
                style: TextStyle(color: config.iconColor, fontSize: 10, fontWeight: FontWeight.bold),
              ),
            ),
          ],
        ),
      ),
    );
  }

  void _showReservationDetail(ReservationModel reservation) {
    showModalBottomSheet(
      context: context,
      backgroundColor: AppColors.surface,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (ctx) => Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Center(
              child: Container(
                width: 40, height: 4,
                decoration: BoxDecoration(color: AppColors.border, borderRadius: BorderRadius.circular(2)),
              ),
            ),
            const SizedBox(height: 16),
            Text(reservation.customerName,
                style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.bold)),
            const SizedBox(height: 12),
            _buildInfoRow(LucideIcons.clock, 'Waktu', reservation.timeDisplay),
            _buildInfoRow(LucideIcons.users, 'Tamu', '${reservation.guestCount} orang'),
            if (reservation.customerPhone != null)
              _buildInfoRow(LucideIcons.phone, 'Telepon', reservation.customerPhone!),
            if (reservation.tableName != null)
              _buildInfoRow(LucideIcons.layoutGrid, 'Meja', reservation.tableName!),
            if (reservation.notes != null && reservation.notes!.isNotEmpty)
              _buildInfoRow(LucideIcons.messageSquare, 'Catatan', reservation.notes!),
            const SizedBox(height: 16),
            SizedBox(
              width: double.infinity,
              child: TextButton(
                onPressed: () => Navigator.pop(ctx),
                child: const Text('Tutup'),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildInfoRow(IconData icon, String label, String value) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Row(
        children: [
          Icon(icon, size: 16, color: AppColors.textSecondary),
          const SizedBox(width: 10),
          SizedBox(width: 80, child: Text(label, style: const TextStyle(color: AppColors.textSecondary, fontSize: 13))),
          Expanded(child: Text(value, style: const TextStyle(fontWeight: FontWeight.w500, fontSize: 14))),
        ],
      ),
    );
  }
}

class _TableDisplayConfig {
  final Color bgColor;
  final Color borderColor;
  final Color iconColor;
  final Color textColor;
  final String statusLabel;
  final IconData icon;

  _TableDisplayConfig({
    required this.bgColor,
    required this.borderColor,
    required this.iconColor,
    required this.textColor,
    required this.statusLabel,
    required this.icon,
  });
}
