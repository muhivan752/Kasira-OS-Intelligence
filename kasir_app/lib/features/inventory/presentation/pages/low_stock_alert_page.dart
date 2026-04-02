import 'package:flutter/material.dart';
import 'package:lucide_icons/lucide_icons.dart';
import '../../../../core/theme/app_colors.dart';

enum StockLevel { out, critical, low }

class StockAlertItem {
  final String id;
  final String name;
  final String category;
  final int currentStock;
  final int minStock;
  final String unit;
  final String? imageUrl;

  const StockAlertItem({
    required this.id,
    required this.name,
    required this.category,
    required this.currentStock,
    required this.minStock,
    required this.unit,
    this.imageUrl,
  });

  StockLevel get level {
    if (currentStock == 0) return StockLevel.out;
    if (currentStock <= minStock ~/ 2) return StockLevel.critical;
    return StockLevel.low;
  }
}

// Demo data
final _demoAlerts = [
  const StockAlertItem(id: '1', name: 'Kopi Susu Gula Aren', category: 'Kopi', currentStock: 0, minStock: 10, unit: 'cup'),
  const StockAlertItem(id: '2', name: 'Es Matcha Latte', category: 'Non-Kopi', currentStock: 2, minStock: 10, unit: 'cup'),
  const StockAlertItem(id: '3', name: 'Croissant Cokelat', category: 'Makanan', currentStock: 3, minStock: 15, unit: 'pcs'),
  const StockAlertItem(id: '4', name: 'Americano', category: 'Kopi', currentStock: 0, minStock: 10, unit: 'cup'),
  const StockAlertItem(id: '5', name: 'Susu Oat', category: 'Bahan', currentStock: 1, minStock: 5, unit: 'liter'),
  const StockAlertItem(id: '6', name: 'Cheesecake Slice', category: 'Dessert', currentStock: 4, minStock: 8, unit: 'slice'),
];

class LowStockAlertPage extends StatefulWidget {
  const LowStockAlertPage({super.key});

  @override
  State<LowStockAlertPage> createState() => _LowStockAlertPageState();
}

class _LowStockAlertPageState extends State<LowStockAlertPage> {
  StockLevel? _filterLevel;

  List<StockAlertItem> get _filtered {
    final items = List<StockAlertItem>.from(_demoAlerts);
    // Sort: out > critical > low
    items.sort((a, b) => a.level.index.compareTo(b.level.index));
    if (_filterLevel != null) {
      return items.where((i) => i.level == _filterLevel).toList();
    }
    return items;
  }

  @override
  Widget build(BuildContext context) {
    final outCount = _demoAlerts.where((i) => i.level == StockLevel.out).length;
    final criticalCount = _demoAlerts.where((i) => i.level == StockLevel.critical).length;
    final lowCount = _demoAlerts.where((i) => i.level == StockLevel.low).length;

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        backgroundColor: Colors.white,
        title: const Text('Peringatan Stok', style: TextStyle(color: AppColors.textPrimary)),
        iconTheme: const IconThemeData(color: AppColors.textPrimary),
        elevation: 0,
        actions: [
          IconButton(
            onPressed: _refreshStock,
            icon: const Icon(LucideIcons.refreshCw, color: AppColors.primary),
            tooltip: 'Refresh',
          ),
          const SizedBox(width: 8),
        ],
      ),
      body: Column(
        children: [
          // Summary banner
          if (outCount > 0)
            Container(
              width: double.infinity,
              padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
              color: AppColors.error.withOpacity(0.1),
              child: Row(
                children: [
                  const Icon(LucideIcons.alertCircle, color: AppColors.error, size: 18),
                  const SizedBox(width: 8),
                  Text(
                    '$outCount produk habis — otomatis disembunyikan dari kasir & storefront',
                    style: const TextStyle(color: AppColors.error, fontWeight: FontWeight.w600, fontSize: 13),
                  ),
                ],
              ),
            ),

          // Filter chips
          Container(
            height: 60,
            padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
            color: Colors.white,
            child: Row(
              children: [
                _buildChip(null, 'Semua', Colors.grey),
                const SizedBox(width: 8),
                _buildChip(StockLevel.out, 'Habis ($outCount)', AppColors.error),
                const SizedBox(width: 8),
                _buildChip(StockLevel.critical, 'Kritis ($criticalCount)', AppColors.warning),
                const SizedBox(width: 8),
                _buildChip(StockLevel.low, 'Rendah ($lowCount)', AppColors.info),
              ],
            ),
          ),

          // List
          Expanded(
            child: _filtered.isEmpty
                ? _buildEmptyState()
                : ListView.builder(
                    padding: const EdgeInsets.all(16),
                    itemCount: _filtered.length,
                    itemBuilder: (context, index) => _buildAlertCard(_filtered[index]),
                  ),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _restockAll,
        icon: const Icon(LucideIcons.packagePlus),
        label: const Text('Restock'),
        backgroundColor: AppColors.primary,
      ),
    );
  }

  Widget _buildChip(StockLevel? level, String label, Color color) {
    final isSelected = _filterLevel == level;
    return GestureDetector(
      onTap: () => setState(() => _filterLevel = level),
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

  Widget _buildAlertCard(StockAlertItem item) {
    final config = _levelConfig(item.level);

    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: config.color.withOpacity(0.3)),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.03),
            blurRadius: 8,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Row(
        children: [
          // Status indicator
          Container(
            width: 48,
            height: 48,
            decoration: BoxDecoration(
              color: config.color.withOpacity(0.1),
              borderRadius: BorderRadius.circular(12),
            ),
            child: Icon(config.icon, color: config.color, size: 22),
          ),
          const SizedBox(width: 14),

          // Product info
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(item.name, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 15)),
                const SizedBox(height: 2),
                Text(item.category, style: const TextStyle(color: AppColors.textSecondary, fontSize: 12)),
                const SizedBox(height: 6),
                Row(
                  children: [
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                      decoration: BoxDecoration(
                        color: config.color.withOpacity(0.1),
                        borderRadius: BorderRadius.circular(6),
                      ),
                      child: Text(
                        config.label,
                        style: TextStyle(
                          color: config.color,
                          fontSize: 11,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ),
                    const SizedBox(width: 8),
                    Text(
                      'Stok: ${item.currentStock} ${item.unit} (min: ${item.minStock})',
                      style: const TextStyle(color: AppColors.textSecondary, fontSize: 12),
                    ),
                  ],
                ),
              ],
            ),
          ),

          // Restock button
          OutlinedButton(
            onPressed: () => _showRestockDialog(item),
            style: OutlinedButton.styleFrom(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
              side: const BorderSide(color: AppColors.primary),
            ),
            child: const Text('Restock', style: TextStyle(fontSize: 12)),
          ),
        ],
      ),
    );
  }

  Widget _buildEmptyState() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Container(
            padding: const EdgeInsets.all(24),
            decoration: BoxDecoration(
              color: AppColors.success.withOpacity(0.1),
              shape: BoxShape.circle,
            ),
            child: const Icon(LucideIcons.checkCircle2, size: 48, color: AppColors.success),
          ),
          const SizedBox(height: 16),
          const Text('Semua stok aman', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 18)),
          const SizedBox(height: 8),
          const Text('Tidak ada produk dengan stok rendah', style: TextStyle(color: AppColors.textSecondary)),
        ],
      ),
    );
  }

  _LevelConfig _levelConfig(StockLevel level) {
    switch (level) {
      case StockLevel.out:
        return _LevelConfig(color: AppColors.error, icon: LucideIcons.xCircle, label: 'HABIS');
      case StockLevel.critical:
        return _LevelConfig(color: AppColors.warning, icon: LucideIcons.alertTriangle, label: 'KRITIS');
      case StockLevel.low:
        return _LevelConfig(color: AppColors.info, icon: LucideIcons.alertCircle, label: 'RENDAH');
    }
  }

  void _showRestockDialog(StockAlertItem item) {
    final controller = TextEditingController();
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
        title: Text('Restock ${item.name}'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Stok saat ini: ${item.currentStock} ${item.unit}',
                style: const TextStyle(color: AppColors.textSecondary)),
            const SizedBox(height: 16),
            TextField(
              controller: controller,
              keyboardType: TextInputType.number,
              autofocus: true,
              decoration: InputDecoration(
                labelText: 'Jumlah tambah stok',
                suffixText: item.unit,
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
              ),
            ),
          ],
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Batal')),
          ElevatedButton(
            onPressed: () {
              // TODO: call POST /api/v1/stock/restock
              Navigator.pop(ctx);
              ScaffoldMessenger.of(context).showSnackBar(
                SnackBar(
                  content: Text('Restock ${item.name} berhasil'),
                  behavior: SnackBarBehavior.floating,
                  backgroundColor: AppColors.success,
                ),
              );
            },
            child: const Text('Simpan'),
          ),
        ],
      ),
    );
  }

  void _restockAll() {
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('Fitur restock massal akan segera hadir'),
        behavior: SnackBarBehavior.floating,
      ),
    );
  }

  void _refreshStock() {
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('Memuat data stok...'),
        behavior: SnackBarBehavior.floating,
        duration: Duration(seconds: 1),
      ),
    );
  }
}

class _LevelConfig {
  final Color color;
  final IconData icon;
  final String label;

  _LevelConfig({required this.color, required this.icon, required this.label});
}
