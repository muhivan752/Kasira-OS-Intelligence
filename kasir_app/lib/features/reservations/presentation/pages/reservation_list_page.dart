import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:lucide_icons/lucide_icons.dart';
import 'package:go_router/go_router.dart';
import '../../../../core/theme/app_colors.dart';
import '../../providers/reservation_provider.dart';
import '../widgets/create_reservation_modal.dart';

class ReservationListPage extends ConsumerStatefulWidget {
  const ReservationListPage({super.key});

  @override
  ConsumerState<ReservationListPage> createState() => _ReservationListPageState();
}

class _ReservationListPageState extends ConsumerState<ReservationListPage> {
  @override
  void initState() {
    super.initState();
    Future.microtask(() => ref.read(reservationProvider.notifier).fetchReservations());
  }

  static String _displayDate(DateTime d) {
    const days = ['Sen', 'Sel', 'Rab', 'Kam', 'Jum', 'Sab', 'Min'];
    const months = [
      'Jan', 'Feb', 'Mar', 'Apr', 'Mei', 'Jun',
      'Jul', 'Agu', 'Sep', 'Okt', 'Nov', 'Des'
    ];
    return '${days[d.weekday - 1]}, ${d.day} ${months[d.month - 1]} ${d.year}';
  }

  static bool _isSameDay(DateTime a, DateTime b) =>
      a.year == b.year && a.month == b.month && a.day == b.day;

  void _changeDate(int delta) {
    final current = ref.read(reservationProvider).selectedDate;
    ref.read(reservationProvider.notifier).changeDate(current.add(Duration(days: delta)));
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(reservationProvider);
    final isToday = _isSameDay(state.selectedDate, DateTime.now());

    // Group by status
    final pending = state.reservations.where((r) => r.status == 'pending').toList();
    final confirmed = state.reservations.where((r) => r.status == 'confirmed').toList();
    final seated = state.reservations.where((r) => r.status == 'seated').toList();
    final others = state.reservations
        .where((r) => !['pending', 'confirmed', 'seated'].contains(r.status))
        .toList();

    return Scaffold(
      backgroundColor: AppColors.background,
      body: Column(
        children: [
          // Header
          Container(
            padding: const EdgeInsets.fromLTRB(24, 16, 24, 12),
            color: Colors.white,
            child: Column(
              children: [
                Row(
                  children: [
                    const Icon(LucideIcons.calendarCheck, color: AppColors.primary),
                    const SizedBox(width: 12),
                    Text('Reservasi', style: Theme.of(context).textTheme.titleLarge),
                    const Spacer(),
                    IconButton(
                      onPressed: () => context.push('/reservations/tables'),
                      icon: const Icon(LucideIcons.layoutGrid, size: 20, color: AppColors.textSecondary),
                      tooltip: 'Denah Meja',
                    ),
                    IconButton(
                      onPressed: () => ref.read(reservationProvider.notifier).fetchReservations(),
                      icon: const Icon(LucideIcons.refreshCw, size: 20, color: AppColors.textSecondary),
                      tooltip: 'Refresh',
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                // Date navigation
                Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    IconButton(
                      onPressed: () => _changeDate(-1),
                      icon: const Icon(LucideIcons.chevronLeft, size: 20),
                    ),
                    GestureDetector(
                      onTap: () async {
                        final picked = await showDatePicker(
                          context: context,
                          initialDate: state.selectedDate,
                          firstDate: DateTime.now().subtract(const Duration(days: 30)),
                          lastDate: DateTime.now().add(const Duration(days: 90)),
                        );
                        if (picked != null) {
                          ref.read(reservationProvider.notifier).changeDate(picked);
                        }
                      },
                      child: Container(
                        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                        decoration: BoxDecoration(
                          color: isToday ? AppColors.primary.withOpacity(0.1) : AppColors.surfaceVariant,
                          borderRadius: BorderRadius.circular(20),
                        ),
                        child: Text(
                          isToday ? 'Hari Ini' : _displayDate(state.selectedDate),
                          style: TextStyle(
                            color: isToday ? AppColors.primary : AppColors.textPrimary,
                            fontWeight: FontWeight.w600,
                            fontSize: 14,
                          ),
                        ),
                      ),
                    ),
                    IconButton(
                      onPressed: () => _changeDate(1),
                      icon: const Icon(LucideIcons.chevronRight, size: 20),
                    ),
                  ],
                ),
              ],
            ),
          ),

          // Content
          Expanded(
            child: state.isLoading
                ? const Center(child: CircularProgressIndicator())
                : state.error != null
                    ? Center(
                        child: Column(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Text(state.error!, style: const TextStyle(color: AppColors.error)),
                            const SizedBox(height: 8),
                            TextButton.icon(
                              onPressed: () => ref.read(reservationProvider.notifier).fetchReservations(),
                              icon: const Icon(LucideIcons.refreshCw, size: 16),
                              label: const Text('Coba Lagi'),
                            ),
                          ],
                        ),
                      )
                    : state.reservations.isEmpty
                        ? Center(
                            child: Column(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                Icon(LucideIcons.calendarOff, size: 48, color: AppColors.textTertiary),
                                const SizedBox(height: 12),
                                const Text(
                                  'Tidak ada reservasi',
                                  style: TextStyle(color: AppColors.textSecondary, fontSize: 16),
                                ),
                              ],
                            ),
                          )
                        : ListView(
                            padding: const EdgeInsets.all(16),
                            children: [
                              if (pending.isNotEmpty) ...[
                                _buildSectionHeader('Menunggu Konfirmasi', AppColors.warning, pending.length),
                                ...pending.map((r) => _buildReservationCard(r)),
                                const SizedBox(height: 16),
                              ],
                              if (confirmed.isNotEmpty) ...[
                                _buildSectionHeader('Dikonfirmasi', AppColors.info, confirmed.length),
                                ...confirmed.map((r) => _buildReservationCard(r)),
                                const SizedBox(height: 16),
                              ],
                              if (seated.isNotEmpty) ...[
                                _buildSectionHeader('Duduk', AppColors.success, seated.length),
                                ...seated.map((r) => _buildReservationCard(r)),
                                const SizedBox(height: 16),
                              ],
                              if (others.isNotEmpty) ...[
                                _buildSectionHeader('Lainnya', AppColors.textSecondary, others.length),
                                ...others.map((r) => _buildReservationCard(r)),
                              ],
                            ],
                          ),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => _showCreateModal(),
        backgroundColor: AppColors.primary,
        icon: const Icon(LucideIcons.plus),
        label: const Text('Reservasi Baru'),
      ),
    );
  }

  Widget _buildSectionHeader(String title, Color color, int count) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
        children: [
          Container(
            width: 4,
            height: 20,
            decoration: BoxDecoration(color: color, borderRadius: BorderRadius.circular(2)),
          ),
          const SizedBox(width: 8),
          Text(title, style: TextStyle(fontWeight: FontWeight.bold, fontSize: 15, color: color)),
          const SizedBox(width: 8),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
            decoration: BoxDecoration(
              color: color.withOpacity(0.1),
              borderRadius: BorderRadius.circular(10),
            ),
            child: Text('$count', style: TextStyle(color: color, fontSize: 12, fontWeight: FontWeight.bold)),
          ),
        ],
      ),
    );
  }

  Widget _buildReservationCard(ReservationModel reservation) {
    final statusColor = _statusColor(reservation.status);
    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: InkWell(
        borderRadius: BorderRadius.circular(12),
        onTap: () => _showDetailSheet(reservation),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Row(
            children: [
              // Time badge
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                decoration: BoxDecoration(
                  color: statusColor.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: Column(
                  children: [
                    Icon(LucideIcons.clock, size: 16, color: statusColor),
                    const SizedBox(height: 4),
                    Text(
                      reservation.startTime.length >= 5
                          ? reservation.startTime.substring(0, 5)
                          : reservation.startTime,
                      style: TextStyle(fontWeight: FontWeight.bold, fontSize: 14, color: statusColor),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 12),
              // Info
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      reservation.customerName,
                      style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 15),
                    ),
                    const SizedBox(height: 4),
                    Row(
                      children: [
                        Icon(LucideIcons.users, size: 13, color: AppColors.textSecondary),
                        const SizedBox(width: 4),
                        Text('${reservation.guestCount} tamu',
                            style: const TextStyle(fontSize: 12, color: AppColors.textSecondary)),
                        if (reservation.tableName != null) ...[
                          const SizedBox(width: 12),
                          Icon(LucideIcons.layoutGrid, size: 13, color: AppColors.textSecondary),
                          const SizedBox(width: 4),
                          Text(reservation.tableName!,
                              style: const TextStyle(fontSize: 12, color: AppColors.textSecondary)),
                        ],
                      ],
                    ),
                  ],
                ),
              ),
              // Status badge
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                decoration: BoxDecoration(
                  color: statusColor.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Text(
                  reservation.statusLabel,
                  style: TextStyle(color: statusColor, fontSize: 11, fontWeight: FontWeight.bold),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Color _statusColor(String status) {
    switch (status) {
      case 'pending':
        return AppColors.warning;
      case 'confirmed':
        return AppColors.info;
      case 'seated':
        return AppColors.success;
      case 'completed':
        return AppColors.textSecondary;
      case 'cancelled':
        return AppColors.error;
      case 'no_show':
        return AppColors.error;
      default:
        return AppColors.textSecondary;
    }
  }

  void _showCreateModal() {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.white,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (_) => const CreateReservationModal(),
    );
  }

  void _showDetailSheet(ReservationModel reservation) {
    showModalBottomSheet(
      context: context,
      backgroundColor: Colors.white,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (ctx) => _ReservationDetailSheet(
        reservation: reservation,
        onAction: (action) async {
          Navigator.pop(ctx);
          final notifier = ref.read(reservationProvider.notifier);
          bool success = false;
          switch (action) {
            case 'confirm':
              success = await notifier.confirmReservation(reservation.id);
              break;
            case 'seat':
              success = await notifier.seatReservation(reservation.id);
              break;
            case 'complete':
              success = await notifier.completeReservation(reservation.id);
              break;
            case 'cancel':
              success = await notifier.cancelReservation(reservation.id);
              break;
            case 'no-show':
              success = await notifier.noShowReservation(reservation.id);
              break;
          }
          if (mounted) {
            ScaffoldMessenger.of(context).showSnackBar(
              SnackBar(
                content: Text(success ? 'Status berhasil diubah' : 'Gagal mengubah status'),
                backgroundColor: success ? AppColors.success : AppColors.error,
              ),
            );
          }
        },
      ),
    );
  }
}

// ── Detail Bottom Sheet ──

class _ReservationDetailSheet extends StatelessWidget {
  final ReservationModel reservation;
  final void Function(String action) onAction;

  const _ReservationDetailSheet({required this.reservation, required this.onAction});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(24),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Handle bar
          Center(
            child: Container(
              width: 40,
              height: 4,
              decoration: BoxDecoration(color: AppColors.border, borderRadius: BorderRadius.circular(2)),
            ),
          ),
          const SizedBox(height: 16),
          Text(reservation.customerName,
              style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.bold)),
          const SizedBox(height: 16),

          // Details
          _buildDetailRow(LucideIcons.clock, 'Waktu', reservation.timeDisplay),
          _buildDetailRow(LucideIcons.users, 'Jumlah Tamu', '${reservation.guestCount} orang'),
          if (reservation.customerPhone != null)
            _buildDetailRow(LucideIcons.phone, 'Telepon', reservation.customerPhone!),
          if (reservation.tableName != null)
            _buildDetailRow(LucideIcons.layoutGrid, 'Meja', reservation.tableName!),
          if (reservation.tableFloorSection != null && reservation.tableFloorSection!.isNotEmpty)
            _buildDetailRow(LucideIcons.map, 'Area', reservation.tableFloorSection!),
          if (reservation.notes != null && reservation.notes!.isNotEmpty)
            _buildDetailRow(LucideIcons.messageSquare, 'Catatan', reservation.notes!),
          if (reservation.source != null)
            _buildDetailRow(LucideIcons.globe, 'Sumber', reservation.source!),

          const SizedBox(height: 20),

          // Action buttons based on status
          ..._buildActions(reservation.status),
        ],
      ),
    );
  }

  Widget _buildDetailRow(IconData icon, String label, String value) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Row(
        children: [
          Icon(icon, size: 16, color: AppColors.textSecondary),
          const SizedBox(width: 10),
          SizedBox(
            width: 100,
            child: Text(label, style: const TextStyle(color: AppColors.textSecondary, fontSize: 13)),
          ),
          Expanded(child: Text(value, style: const TextStyle(fontWeight: FontWeight.w500, fontSize: 14))),
        ],
      ),
    );
  }

  List<Widget> _buildActions(String status) {
    final actions = <Widget>[];

    if (status == 'pending') {
      actions.add(_buildActionButton('Konfirmasi', LucideIcons.checkCircle, AppColors.info, () => onAction('confirm')));
      actions.add(const SizedBox(height: 8));
      actions.add(_buildActionButton('Tidak Hadir', LucideIcons.userX, AppColors.warning, () => onAction('no-show')));
      actions.add(const SizedBox(height: 8));
      actions.add(_buildActionButton('Batalkan', LucideIcons.xCircle, AppColors.error, () => onAction('cancel')));
    } else if (status == 'confirmed') {
      actions.add(_buildActionButton('Dudukkan', LucideIcons.armchair, AppColors.success, () => onAction('seat')));
      actions.add(const SizedBox(height: 8));
      actions.add(_buildActionButton('Tidak Hadir', LucideIcons.userX, AppColors.warning, () => onAction('no-show')));
      actions.add(const SizedBox(height: 8));
      actions.add(_buildActionButton('Batalkan', LucideIcons.xCircle, AppColors.error, () => onAction('cancel')));
    } else if (status == 'seated') {
      actions.add(_buildActionButton('Selesai', LucideIcons.checkCircle2, AppColors.success, () => onAction('complete')));
    }

    return actions;
  }

  Widget _buildActionButton(String label, IconData icon, Color color, VoidCallback onPressed) {
    return SizedBox(
      width: double.infinity,
      height: 44,
      child: OutlinedButton.icon(
        onPressed: onPressed,
        icon: Icon(icon, size: 18, color: color),
        label: Text(label, style: TextStyle(color: color, fontWeight: FontWeight.w600)),
        style: OutlinedButton.styleFrom(
          side: BorderSide(color: color.withOpacity(0.5)),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
        ),
      ),
    );
  }
}
