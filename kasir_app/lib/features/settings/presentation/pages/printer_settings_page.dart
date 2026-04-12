import 'dart:typed_data';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:lucide_icons/lucide_icons.dart';
import 'package:print_bluetooth_thermal/print_bluetooth_thermal.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/services/printer_service.dart';

class PrinterSettingsPage extends ConsumerWidget {
  const PrinterSettingsPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final state = ref.watch(printerProvider);
    final notifier = ref.read(printerProvider.notifier);

    ref.listen<PrinterState>(printerProvider, (_, next) {
      if (next.error != null) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(next.error!),
            backgroundColor: AppColors.error,
            behavior: SnackBarBehavior.floating,
          ),
        );
        notifier.clearError();
      }
    });

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        title: const Text('Pengaturan Printer', style: TextStyle(color: AppColors.textPrimary)),
        backgroundColor: Colors.white,
        iconTheme: const IconThemeData(color: AppColors.textPrimary),
        elevation: 0,
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(1),
          child: Container(color: AppColors.border, height: 1),
        ),
      ),
      body: ListView(
        padding: const EdgeInsets.all(24),
        children: [
          // Status Card
          Container(
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: AppColors.border),
            ),
            child: Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: (state.isConnected ? AppColors.success : AppColors.textSecondary)
                        .withOpacity(0.1),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Icon(
                    LucideIcons.printer,
                    color: state.isConnected ? AppColors.success : AppColors.textSecondary,
                  ),
                ),
                const SizedBox(width: 16),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        state.savedDevice?.name ?? 'Belum ada printer',
                        style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        state.isConnected
                            ? 'Terhubung'
                            : (state.savedDevice != null ? 'Tidak terhubung' : 'Scan untuk menemukan printer'),
                        style: TextStyle(
                          color: state.isConnected ? AppColors.success : AppColors.textSecondary,
                          fontSize: 13,
                        ),
                      ),
                    ],
                  ),
                ),
                if (state.isConnected)
                  TextButton(
                    onPressed: notifier.disconnect,
                    child: const Text('Putus', style: TextStyle(color: AppColors.error)),
                  ),
              ],
            ),
          ),
          const SizedBox(height: 20),

          // Scan Button
          SizedBox(
            width: double.infinity,
            child: ElevatedButton.icon(
              onPressed: state.isScanning ? notifier.stopScan : notifier.startScan,
              icon: state.isScanning
                  ? const SizedBox(
                      width: 18,
                      height: 18,
                      child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2),
                    )
                  : const Icon(LucideIcons.bluetooth),
              label: Text(state.isScanning ? 'Mencari...' : 'Cari Printer Bluetooth'),
              style: ElevatedButton.styleFrom(
                padding: const EdgeInsets.symmetric(vertical: 14),
              ),
            ),
          ),

          // Info
          const SizedBox(height: 8),
          const Text(
            'Pastikan printer sudah di-pair via Pengaturan Bluetooth HP terlebih dahulu.',
            style: TextStyle(color: AppColors.textSecondary, fontSize: 12),
            textAlign: TextAlign.center,
          ),

          // Scan Results
          if (state.scanResults.isNotEmpty) ...[
            const SizedBox(height: 24),
            Text(
              'Perangkat Ditemukan (${state.scanResults.length})',
              style: const TextStyle(fontWeight: FontWeight.bold, color: AppColors.textSecondary),
            ),
            const SizedBox(height: 12),
            ...state.scanResults.map((device) => _DeviceTile(
                  device: device,
                  isConnected: state.isConnected &&
                      state.savedDevice?.address == device.macAdpilesress,
                  onConnect: () async {
                    final ok = await notifier.connect(device);
                    if (ok && context.mounted) {
                      ScaffoldMessenger.of(context).showSnackBar(
                        SnackBar(
                          content: Text('Terhubung ke ${device.name}'),
                          backgroundColor: AppColors.success,
                          behavior: SnackBarBehavior.floating,
                        ),
                      );
                    }
                  },
                  onTestPrint: () async {
                    final bytes = _buildTestPrint();
                    await notifier.printBytes(bytes);
                  },
                )),
          ] else if (state.isScanning) ...[
            const SizedBox(height: 32),
            const Center(
              child: Column(
                children: [
                  CircularProgressIndicator(),
                  SizedBox(height: 12),
                  Text('Mencari printer...', style: TextStyle(color: AppColors.textSecondary)),
                ],
              ),
            ),
          ],

          // Test print for already connected
          if (state.isConnected && state.scanResults.isEmpty) ...[
            const SizedBox(height: 20),
            OutlinedButton.icon(
              onPressed: () async {
                final bytes = _buildTestPrint();
                await notifier.printBytes(bytes);
              },
              icon: const Icon(LucideIcons.printer),
              label: const Text('Cetak Struk Tes'),
              style: OutlinedButton.styleFrom(
                padding: const EdgeInsets.symmetric(vertical: 14),
                side: const BorderSide(color: AppColors.primary),
                foregroundColor: AppColors.primary,
              ),
            ),
          ],
        ],
      ),
    );
  }
}

class _DeviceTile extends StatelessWidget {
  final BluetoothInfo device;
  final bool isConnected;
  final VoidCallback onConnect;
  final VoidCallback onTestPrint;

  const _DeviceTile({
    required this.device,
    required this.isConnected,
    required this.onConnect,
    required this.onTestPrint,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: ListTile(
        contentPadding: const EdgeInsets.symmetric(horizontal: 20, vertical: 8),
        leading: Icon(
          LucideIcons.printer,
          color: isConnected ? AppColors.primary : AppColors.textSecondary,
        ),
        title: Text(
          device.name.isNotEmpty ? device.name : 'Unknown Device',
          style: const TextStyle(fontWeight: FontWeight.bold),
        ),
        subtitle: Text(
          device.macAdpilesress,
          style: const TextStyle(color: AppColors.textSecondary, fontSize: 12),
        ),
        trailing: isConnected
            ? ElevatedButton(
                onPressed: onTestPrint,
                style: ElevatedButton.styleFrom(
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                  textStyle: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold),
                ),
                child: const Text('TES PRINT'),
              )
            : OutlinedButton(
                onPressed: onConnect,
                style: OutlinedButton.styleFrom(
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                  textStyle: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold),
                  side: const BorderSide(color: AppColors.primary),
                  foregroundColor: AppColors.primary,
                ),
                child: const Text('HUBUNGKAN'),
              ),
      ),
    );
  }
}

Uint8List _buildTestPrint() {
  final bytes = <int>[];
  bytes.addAll(EscPos.init);
  bytes.addAll(EscPos.alignCenter);
  bytes.addAll(EscPos.boldOn);
  bytes.addAll(EscPos.line('--- TES PRINTER ---'));
  bytes.addAll(EscPos.boldOff);
  bytes.addAll(EscPos.line('Kasira POS'));
  bytes.addAll(EscPos.line('Printer terhubung dengan baik'));
  bytes.addAll(EscPos.feedLines3);
  bytes.addAll(EscPos.cut);
  return Uint8List.fromList(bytes);
}
