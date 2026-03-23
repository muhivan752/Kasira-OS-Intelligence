import 'package:flutter/material.dart';
import 'package:lucide_icons/lucide_icons.dart';
import '../../../../core/theme/app_colors.dart';
import 'cash_drawer_history_page.dart';

class ShiftPage extends StatelessWidget {
  const ShiftPage({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        backgroundColor: Colors.white,
        title: const Text('Manajemen Shift', style: TextStyle(color: AppColors.textPrimary)),
        iconTheme: const IconThemeData(color: AppColors.textPrimary),
        elevation: 0,
        actions: [
          TextButton.icon(
            onPressed: () {
              Navigator.push(
                context,
                MaterialPageRoute(builder: (context) => const CashDrawerHistoryPage()),
              );
            },
            icon: const Icon(LucideIcons.history, color: AppColors.primary),
            label: const Text('Riwayat Kas', style: TextStyle(color: AppColors.primary)),
          ),
          const SizedBox(width: 16),
        ],
      ),
      body: Center(
        child: Container(
          width: 500,
          padding: const EdgeInsets.all(32),
          decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(24),
            boxShadow: [
              BoxShadow(color: Colors.black.withOpacity(0.05), blurRadius: 20, offset: const Offset(0, 10)),
            ],
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(LucideIcons.clock, size: 48, color: AppColors.primary),
              const SizedBox(height: 24),
              Text('Tutup Shift Saat Ini', style: Theme.of(context).textTheme.headlineMedium),
              const SizedBox(height: 8),
              const Text(
                'Pastikan jumlah uang di laci kasir sesuai dengan sistem.', 
                textAlign: TextAlign.center, 
                style: TextStyle(color: AppColors.textSecondary),
              ),
              const SizedBox(height: 32),
              
              _buildSummaryRow('Uang Modal Awal', 'Rp 500.000'),
              const SizedBox(height: 12),
              _buildSummaryRow('Penerimaan Tunai', 'Rp 1.250.000'),
              const SizedBox(height: 12),
              _buildSummaryRow('Pengeluaran Kas', 'Rp 150.000', isNegative: true),
              const Divider(height: 32),
              _buildSummaryRow('Total Uang di Laci (Sistem)', 'Rp 1.600.000', isBold: true),
              
              const SizedBox(height: 32),
              const TextField(
                keyboardType: TextInputType.number,
                decoration: InputDecoration(
                  labelText: 'Uang Aktual di Laci',
                  prefixText: 'Rp ',
                  border: OutlineInputBorder(),
                ),
              ),
              const SizedBox(height: 32),
              SizedBox(
                width: double.infinity,
                height: 56,
                child: ElevatedButton(
                  onPressed: () {
                    Navigator.pop(context);
                  },
                  style: ElevatedButton.styleFrom(backgroundColor: AppColors.error),
                  child: const Text('TUTUP SHIFT & CETAK REKAP'),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildSummaryRow(String label, String value, {bool isNegative = false, bool isBold = false}) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(
          label, 
          style: TextStyle(
            color: isBold ? AppColors.textPrimary : AppColors.textSecondary, 
            fontWeight: isBold ? FontWeight.bold : FontWeight.normal, 
            fontSize: isBold ? 18 : 14,
          ),
        ),
        Text(
          value, 
          style: TextStyle(
            color: isNegative ? AppColors.error : AppColors.textPrimary, 
            fontWeight: isBold ? FontWeight.bold : FontWeight.w600, 
            fontSize: isBold ? 18 : 14,
          ),
        ),
      ],
    );
  }
}
