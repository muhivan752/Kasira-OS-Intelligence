import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:lucide_icons/lucide_icons.dart';
import '../../../../core/theme/app_colors.dart';
import '../../providers/reservation_provider.dart';
import '../../providers/table_provider.dart';

class CreateReservationModal extends ConsumerStatefulWidget {
  const CreateReservationModal({super.key});

  @override
  ConsumerState<CreateReservationModal> createState() => _CreateReservationModalState();
}

class _CreateReservationModalState extends ConsumerState<CreateReservationModal> {
  final _formKey = GlobalKey<FormState>();
  final _nameController = TextEditingController();
  final _phoneController = TextEditingController();
  final _notesController = TextEditingController();
  final _guestCountController = TextEditingController(text: '2');

  DateTime _selectedDate = DateTime.now();
  TimeOfDay _selectedTime = TimeOfDay.now();
  String? _selectedTableId;
  bool _isSubmitting = false;

  @override
  void initState() {
    super.initState();
    // Load tables for dropdown
    Future.microtask(() => ref.read(tableListProvider.notifier).fetchTables());
  }

  @override
  void dispose() {
    _nameController.dispose();
    _phoneController.dispose();
    _notesController.dispose();
    _guestCountController.dispose();
    super.dispose();
  }

  static String _formatDate(DateTime d) =>
      '${d.year}-${d.month.toString().padLeft(2, '0')}-${d.day.toString().padLeft(2, '0')}';

  static String _formatTime(TimeOfDay t) =>
      '${t.hour.toString().padLeft(2, '0')}:${t.minute.toString().padLeft(2, '0')}';

  static String _displayDate(DateTime d) =>
      '${d.day.toString().padLeft(2, '0')}/${d.month.toString().padLeft(2, '0')}/${d.year}';

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() => _isSubmitting = true);

    final result = await ref.read(reservationProvider.notifier).createReservation(
          reservationDate: _formatDate(_selectedDate),
          startTime: _formatTime(_selectedTime),
          guestCount: int.tryParse(_guestCountController.text) ?? 2,
          customerName: _nameController.text.trim(),
          customerPhone: _phoneController.text.trim(),
          tableId: _selectedTableId,
          notes: _notesController.text.trim().isNotEmpty ? _notesController.text.trim() : null,
          source: 'pos',
        );

    if (!mounted) return;
    setState(() => _isSubmitting = false);

    if (result != null) {
      Navigator.pop(context, true);
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Reservasi berhasil dibuat'), backgroundColor: AppColors.success),
      );
    } else {
      final error = ref.read(reservationProvider).error;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(error ?? 'Gagal membuat reservasi'), backgroundColor: AppColors.error),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final tableState = ref.watch(tableListProvider);
    final activeTables = tableState.tables.where((t) => t.isActive).toList();

    return Padding(
      padding: EdgeInsets.only(
        left: 24,
        right: 24,
        top: 24,
        bottom: MediaQuery.of(context).viewInsets.bottom + 24,
      ),
      child: Form(
        key: _formKey,
        child: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Handle bar
              Center(
                child: Container(
                  width: 40,
                  height: 4,
                  decoration: BoxDecoration(
                    color: AppColors.border,
                    borderRadius: BorderRadius.circular(2),
                  ),
                ),
              ),
              const SizedBox(height: 16),
              Text('Reservasi Baru', style: Theme.of(context).textTheme.titleLarge),
              const SizedBox(height: 24),

              // Date & Time row
              Row(
                children: [
                  Expanded(
                    child: _buildTapField(
                      label: 'Tanggal',
                      value: _displayDate(_selectedDate),
                      icon: LucideIcons.calendar,
                      onTap: () async {
                        final picked = await showDatePicker(
                          context: context,
                          initialDate: _selectedDate,
                          firstDate: DateTime.now(),
                          lastDate: DateTime.now().add(const Duration(days: 90)),
                        );
                        if (picked != null) setState(() => _selectedDate = picked);
                      },
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: _buildTapField(
                      label: 'Jam',
                      value: _formatTime(_selectedTime),
                      icon: LucideIcons.clock,
                      onTap: () async {
                        final picked = await showTimePicker(
                          context: context,
                          initialTime: _selectedTime,
                        );
                        if (picked != null) setState(() => _selectedTime = picked);
                      },
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 16),

              // Guest count
              TextFormField(
                controller: _guestCountController,
                keyboardType: TextInputType.number,
                decoration: const InputDecoration(
                  labelText: 'Jumlah Tamu',
                  prefixIcon: Icon(LucideIcons.users, size: 18),
                  border: OutlineInputBorder(),
                ),
                validator: (v) {
                  final n = int.tryParse(v ?? '');
                  if (n == null || n < 1) return 'Min. 1 tamu';
                  return null;
                },
              ),
              const SizedBox(height: 16),

              // Customer name
              TextFormField(
                controller: _nameController,
                textCapitalization: TextCapitalization.words,
                decoration: const InputDecoration(
                  labelText: 'Nama Pelanggan',
                  prefixIcon: Icon(LucideIcons.user, size: 18),
                  border: OutlineInputBorder(),
                ),
                validator: (v) => (v == null || v.trim().isEmpty) ? 'Wajib diisi' : null,
              ),
              const SizedBox(height: 16),

              // Customer phone
              TextFormField(
                controller: _phoneController,
                keyboardType: TextInputType.phone,
                decoration: const InputDecoration(
                  labelText: 'No. Telepon',
                  prefixIcon: Icon(LucideIcons.phone, size: 18),
                  border: OutlineInputBorder(),
                ),
                validator: (v) => (v == null || v.trim().isEmpty) ? 'Wajib diisi' : null,
              ),
              const SizedBox(height: 16),

              // Table selection
              DropdownButtonFormField<String>(
                value: _selectedTableId,
                decoration: const InputDecoration(
                  labelText: 'Meja (opsional)',
                  prefixIcon: Icon(LucideIcons.layoutGrid, size: 18),
                  border: OutlineInputBorder(),
                ),
                items: [
                  const DropdownMenuItem(value: null, child: Text('Tanpa meja')),
                  ...activeTables.map((t) => DropdownMenuItem(
                        value: t.id,
                        child: Text('${t.name} (${t.capacity} kursi)'),
                      )),
                ],
                onChanged: (v) => setState(() => _selectedTableId = v),
              ),
              const SizedBox(height: 16),

              // Notes
              TextFormField(
                controller: _notesController,
                maxLines: 2,
                decoration: const InputDecoration(
                  labelText: 'Catatan (opsional)',
                  prefixIcon: Icon(LucideIcons.messageSquare, size: 18),
                  border: OutlineInputBorder(),
                ),
              ),
              const SizedBox(height: 24),

              // Submit button
              SizedBox(
                width: double.infinity,
                height: 48,
                child: ElevatedButton.icon(
                  onPressed: _isSubmitting ? null : _submit,
                  icon: _isSubmitting
                      ? const SizedBox(
                          width: 18,
                          height: 18,
                          child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                        )
                      : const Icon(LucideIcons.calendarPlus, size: 18),
                  label: Text(_isSubmitting ? 'Menyimpan...' : 'Buat Reservasi'),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppColors.primary,
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildTapField({
    required String label,
    required String value,
    required IconData icon,
    required VoidCallback onTap,
  }) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(8),
      child: InputDecorator(
        decoration: InputDecoration(
          labelText: label,
          prefixIcon: Icon(icon, size: 18),
          border: const OutlineInputBorder(),
        ),
        child: Text(value),
      ),
    );
  }
}
