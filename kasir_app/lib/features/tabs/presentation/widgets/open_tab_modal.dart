import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:lucide_icons/lucide_icons.dart';
import '../../../../core/theme/app_colors.dart';
import '../../providers/tab_provider.dart';

class OpenTabModal extends ConsumerStatefulWidget {
  final void Function(TabModel tab) onTabOpened;
  const OpenTabModal({super.key, required this.onTabOpened});

  @override
  ConsumerState<OpenTabModal> createState() => _OpenTabModalState();
}

class _OpenTabModalState extends ConsumerState<OpenTabModal> {
  final _nameController = TextEditingController();
  int _guestCount = 1;
  bool _isLoading = false;
  String? _error;

  @override
  void dispose() {
    _nameController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.only(
        left: 24, right: 24, top: 24,
        bottom: MediaQuery.of(context).viewInsets.bottom + 24,
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(LucideIcons.receipt, color: AppColors.primary),
              const SizedBox(width: 12),
              Text('Buka Tab Baru', style: Theme.of(context).textTheme.titleLarge),
              const Spacer(),
              IconButton(onPressed: () => Navigator.pop(context), icon: const Icon(LucideIcons.x)),
            ],
          ),
          const SizedBox(height: 20),

          // Customer name
          TextField(
            controller: _nameController,
            decoration: InputDecoration(
              labelText: 'Nama Tamu (opsional)',
              prefixIcon: const Icon(LucideIcons.user),
              border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
            ),
          ),
          const SizedBox(height: 16),

          // Guest count
          Text('Jumlah Tamu', style: TextStyle(color: AppColors.textSecondary, fontSize: 14)),
          const SizedBox(height: 8),
          Row(
            children: [
              IconButton.filled(
                onPressed: _guestCount > 1 ? () => setState(() => _guestCount--) : null,
                icon: const Icon(LucideIcons.minus, size: 18),
                style: IconButton.styleFrom(
                  backgroundColor: AppColors.surfaceVariant,
                  foregroundColor: AppColors.textPrimary,
                ),
              ),
              const SizedBox(width: 16),
              Text(
                '$_guestCount',
                style: const TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
              ),
              const SizedBox(width: 16),
              IconButton.filled(
                onPressed: _guestCount < 50 ? () => setState(() => _guestCount++) : null,
                icon: const Icon(LucideIcons.plus, size: 18),
                style: IconButton.styleFrom(
                  backgroundColor: AppColors.primary.withOpacity(0.1),
                  foregroundColor: AppColors.primary,
                ),
              ),
              const Spacer(),
              // Quick buttons
              ...[2, 4, 6].map((n) => Padding(
                    padding: const EdgeInsets.only(left: 8),
                    child: OutlinedButton(
                      onPressed: () => setState(() => _guestCount = n),
                      style: OutlinedButton.styleFrom(
                        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                        side: BorderSide(
                          color: _guestCount == n ? AppColors.primary : AppColors.border,
                        ),
                      ),
                      child: Text('$n'),
                    ),
                  )),
            ],
          ),

          if (_error != null) ...[
            const SizedBox(height: 12),
            Text(_error!, style: const TextStyle(color: AppColors.error, fontSize: 13)),
          ],

          const SizedBox(height: 24),
          SizedBox(
            width: double.infinity,
            height: 50,
            child: FilledButton.icon(
              onPressed: _isLoading ? null : _openTab,
              icon: _isLoading
                  ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                  : const Icon(LucideIcons.plus, size: 18),
              label: const Text('Buka Tab'),
              style: FilledButton.styleFrom(backgroundColor: AppColors.primary),
            ),
          ),
        ],
      ),
    );
  }

  Future<void> _openTab() async {
    setState(() { _isLoading = true; _error = null; });
    final name = _nameController.text.trim();
    final tab = await ref.read(tabProvider.notifier).openTab(
      customerName: name.isNotEmpty ? name : null,
      guestCount: _guestCount,
    );
    if (mounted) {
      setState(() => _isLoading = false);
      if (tab != null) {
        Navigator.pop(context);
        widget.onTabOpened(tab);
      } else {
        setState(() => _error = ref.read(tabProvider).error ?? 'Gagal membuka tab');
      }
    }
  }
}
