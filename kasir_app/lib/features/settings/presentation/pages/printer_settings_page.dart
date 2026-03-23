import 'package:flutter/material.dart';
import 'package:lucide_icons/lucide_icons.dart';
import '../../../../core/theme/app_colors.dart';

class PrinterSettingsPage extends StatefulWidget {
  const PrinterSettingsPage({super.key});

  @override
  State<PrinterSettingsPage> createState() => _PrinterSettingsPageState();
}

class _PrinterSettingsPageState extends State<PrinterSettingsPage> {
  bool _isBluetoothEnabled = true;
  String _connectedPrinter = 'Epson TM-T82X';

  @override
  Widget build(BuildContext context) {
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
          // Bluetooth Toggle
          Container(
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: AppColors.border),
            ),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Row(
                  children: [
                    Container(
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: AppColors.primary.withOpacity(0.1),
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: const Icon(LucideIcons.bluetooth, color: AppColors.primary),
                    ),
                    const SizedBox(width: 16),
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text('Bluetooth', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
                        const SizedBox(height: 4),
                        Text(
                          _isBluetoothEnabled ? 'Aktif' : 'Nonaktif',
                          style: TextStyle(color: _isBluetoothEnabled ? AppColors.success : AppColors.textSecondary),
                        ),
                      ],
                    ),
                  ],
                ),
                Switch(
                  value: _isBluetoothEnabled,
                  onChanged: (val) => setState(() => _isBluetoothEnabled = val),
                  activeColor: AppColors.primary,
                ),
              ],
            ),
          ),
          const SizedBox(height: 32),

          if (_isBluetoothEnabled) ...[
            const Text('Perangkat Terhubung', style: TextStyle(fontWeight: FontWeight.bold, color: AppColors.textSecondary)),
            const SizedBox(height: 12),
            _buildDeviceTile(
              name: 'Epson TM-T82X',
              macAddress: '00:11:22:33:44:55',
              isConnected: true,
            ),
            
            const SizedBox(height: 24),
            const Text('Perangkat Tersedia', style: TextStyle(fontWeight: FontWeight.bold, color: AppColors.textSecondary)),
            const SizedBox(height: 12),
            _buildDeviceTile(
              name: 'POS Printer 58mm',
              macAddress: 'AA:BB:CC:DD:EE:FF',
              isConnected: false,
            ),
            _buildDeviceTile(
              name: 'Zjiang ZJ-5802',
              macAddress: '11:22:33:44:55:66',
              isConnected: false,
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildDeviceTile({required String name, required String macAddress, required bool isConnected}) {
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: ListTile(
        contentPadding: const EdgeInsets.symmetric(horizontal: 20, vertical: 8),
        leading: Icon(LucideIcons.printer, color: isConnected ? AppColors.primary : AppColors.textSecondary),
        title: Text(name, style: const TextStyle(fontWeight: FontWeight.bold)),
        subtitle: Text(macAddress, style: const TextStyle(color: AppColors.textSecondary, fontSize: 12)),
        trailing: isConnected
            ? ElevatedButton(
                onPressed: () {
                  // TODO: Test Print
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(content: Text('Mencetak struk tes...')),
                  );
                },
                style: ElevatedButton.styleFrom(
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                  textStyle: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold),
                ),
                child: const Text('TES PRINT'),
              )
            : OutlinedButton(
                onPressed: () {
                  setState(() => _connectedPrinter = name);
                },
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
