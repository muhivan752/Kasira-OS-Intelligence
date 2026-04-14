import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:lucide_icons/lucide_icons.dart';
import 'package:dio/dio.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import '../../../../core/config/app_config.dart';
import '../../../../core/theme/app_colors.dart';

enum StockLevel { out, critical, low }

class StockAlertItem {
  final String id;
  final String name;
  final String category;
  final int currentStock;
  final int minStock;

  const StockAlertItem({
    required this.id,
    required this.name,
    required this.category,
    required this.currentStock,
    required this.minStock,
  });

  StockLevel get level {
    if (currentStock == 0) return StockLevel.out;
    if (currentStock <= minStock ~/ 2) return StockLevel.critical;
    return StockLevel.low;
  }

  factory StockAlertItem.fromJson(Map<String, dynamic> j) => StockAlertItem(
        id: j['id'] as String,
        name: j['name'] as String,
        category: j['category_name'] as String? ?? '-',
        currentStock: (j['stock_qty'] as num?)?.toInt() ?? 0,
        minStock: (j['stock_low_threshold'] as num?)?.toInt() ?? 5,
      );
}

class LowStockAlertPage extends StatefulWidget {
  const LowStockAlertPage({super.key});

  @override
  State<LowStockAlertPage> createState() => _LowStockAlertPageState();
}

class _LowStockAlertPageState extends State<LowStockAlertPage> {
  StockLevel? _filterLevel;
  List<StockAlertItem> _items = [];
  bool _isLoading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() { _isLoading = true; _error = null; });
    try {
      const storage = FlutterSecureStorage();
      final token = await storage.read(key: 'access_token');
      final tenantId = await storage.read(key: 'tenant_id');

      final dio = Dio(BaseOptions(
        baseUrl: AppConfig.apiV1,
        connectTimeout: const Duration(seconds: 15),
        receiveTimeout: const Duration(seconds: 15),
      ));

      final response = await dio.get(
        '/products/low-stock',
        options: Options(headers: {
          if (token != null) 'Authorization': 'Bearer $token',
          if (tenantId != null) 'X-Tenant-ID': tenantId,
        }),
      );

      final list = (response.data['data'] as List? ?? [])
          .map((e) => StockAlertItem.fromJson(e as Map<String, dynamic>))
          .toList();

      if (mounted) setState(() { _items = list; _isLoading = false; });
    } on DioException catch (e) {
      final msg = e.response?.data?['detail'] ?? 'Gagal memuat data stok';
      if (mounted) setState(() { _error = msg.toString(); _isLoading = false; });
    } catch (_) {
      if (mounted) setState(() { _error = 'Gagal memuat data stok'; _isLoading = false; });
    }
  }

  List<StockAlertItem> get _filtered {
    final sorted = List<StockAlertItem>.from(_items)
      ..sort((a, b) => a.level.index.compareTo(b.level.index));
    if (_filterLevel != null) return sorted.where((i) => i.level == _filterLevel).toList();
    return sorted;
  }

  @override
  Widget build(BuildContext context) {
    final outCount = _items.where((i) => i.level == StockLevel.out).length;
    final criticalCount = _items.where((i) => i.level == StockLevel.critical).length;
    final lowCount = _items.where((i) => i.level == StockLevel.low).length;

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        backgroundColor: AppColors.surface,
        title: const Text('Peringatan Stok', style: TextStyle(color: AppColors.textPrimary)),
        iconTheme: const IconThemeData(color: AppColors.textPrimary),
        elevation: 0,
        actions: [
          IconButton(
            onPressed: _load,
            icon: const Icon(LucideIcons.refreshCw, color: AppColors.primary),
            tooltip: 'Refresh',
          ),
          const SizedBox(width: 8),
        ],
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
              ? _buildError()
              : Column(
                  children: [
                    if (outCount > 0)
                      Container(
                        width: double.infinity,
                        padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
                        color: AppColors.error.withOpacity(0.1),
                        child: Row(
                          children: [
                            const Icon(LucideIcons.alertCircle, color: AppColors.error, size: 18),
                            const SizedBox(width: 8),
                            Expanded(
                              child: Text(
                                '$outCount produk habis — otomatis disembunyikan dari kasir',
                                style: const TextStyle(color: AppColors.error, fontWeight: FontWeight.w600, fontSize: 13),
                              ),
                            ),
                          ],
                        ),
                      ),
                    Container(
                      height: 60,
                      padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
                      color: AppColors.surface,
                      child: SingleChildScrollView(
                        scrollDirection: Axis.horizontal,
                        child: Row(
                          children: [
                            _buildChip(null, 'Semua (${_items.length})', AppColors.textSecondary),
                            const SizedBox(width: 8),
                            _buildChip(StockLevel.out, 'Habis ($outCount)', AppColors.error),
                            const SizedBox(width: 8),
                            _buildChip(StockLevel.critical, 'Kritis ($criticalCount)', AppColors.warning),
                            const SizedBox(width: 8),
                            _buildChip(StockLevel.low, 'Rendah ($lowCount)', AppColors.info),
                          ],
                        ),
                      ),
                    ),
                    Expanded(
                      child: _filtered.isEmpty
                          ? _buildEmptyState()
                          : ListView.builder(
                              padding: const EdgeInsets.all(16),
                              itemCount: _filtered.length,
                              itemBuilder: (_, i) => _buildAlertCard(_filtered[i]),
                            ),
                    ),
                  ],
                ),
    );
  }

  Widget _buildError() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const Icon(LucideIcons.wifiOff, size: 48, color: AppColors.textSecondary),
          const SizedBox(height: 16),
          Text(_error!, style: const TextStyle(color: AppColors.textSecondary)),
          const SizedBox(height: 16),
          ElevatedButton.icon(
            onPressed: _load,
            icon: const Icon(LucideIcons.refreshCw, size: 16),
            label: const Text('Coba Lagi'),
          ),
        ],
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
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: config.color.withOpacity(0.3)),
        boxShadow: [BoxShadow(color: Colors.black.withOpacity(0.03), blurRadius: 8, offset: const Offset(0, 2))],
      ),
      child: Row(
        children: [
          Container(
            width: 48,
            height: 48,
            decoration: BoxDecoration(color: config.color.withOpacity(0.1), borderRadius: BorderRadius.circular(12)),
            child: Icon(config.icon, color: config.color, size: 22),
          ),
          const SizedBox(width: 14),
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
                      decoration: BoxDecoration(color: config.color.withOpacity(0.1), borderRadius: BorderRadius.circular(6)),
                      child: Text(config.label, style: TextStyle(color: config.color, fontSize: 11, fontWeight: FontWeight.bold)),
                    ),
                    const SizedBox(width: 8),
                    Text(
                      'Stok: ${item.currentStock} (min: ${item.minStock})',
                      style: const TextStyle(color: AppColors.textSecondary, fontSize: 12),
                    ),
                  ],
                ),
              ],
            ),
          ),
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
            decoration: BoxDecoration(color: AppColors.success.withOpacity(0.1), shape: BoxShape.circle),
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
    final notesController = TextEditingController();
    showDialog(
      context: context,
      builder: (ctx) => _RestockDialog(
        item: item,
        qtyController: controller,
        notesController: notesController,
        onConfirm: () => _doRestock(ctx, item, controller, notesController),
      ),
    );
  }

  Future<void> _doRestock(
    BuildContext dialogCtx,
    StockAlertItem item,
    TextEditingController qtyCtrl,
    TextEditingController notesCtrl,
  ) async {
    final qty = int.tryParse(qtyCtrl.text.trim()) ?? 0;
    if (qty <= 0) return;

    Navigator.pop(dialogCtx);

    try {
      const storage = FlutterSecureStorage();
      final token = await storage.read(key: 'access_token');
      final tenantId = await storage.read(key: 'tenant_id');
      final outletId = await storage.read(key: 'outlet_id');

      final dio = Dio(BaseOptions(
        baseUrl: AppConfig.apiV1,
        connectTimeout: const Duration(seconds: 15),
        receiveTimeout: const Duration(seconds: 15),
      ));

      await dio.post(
        '/products/${item.id}/restock',
        options: Options(headers: {
          if (token != null) 'Authorization': 'Bearer $token',
          if (tenantId != null) 'X-Tenant-ID': tenantId,
        }),
        data: {
          'quantity': qty,
          'outlet_id': outletId,
          if (notesCtrl.text.trim().isNotEmpty) 'notes': notesCtrl.text.trim(),
        },
      );

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Restock ${item.name} +$qty berhasil'),
            backgroundColor: AppColors.success,
            behavior: SnackBarBehavior.floating,
          ),
        );
        _load(); // refresh list
      }
    } on DioException catch (e) {
      final msg = e.response?.data?['detail'] ?? 'Gagal restock';
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(msg.toString()), backgroundColor: AppColors.error, behavior: SnackBarBehavior.floating),
        );
      }
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Gagal restock'), backgroundColor: AppColors.error, behavior: SnackBarBehavior.floating),
        );
      }
    }
  }
}

class _RestockDialog extends StatefulWidget {
  final StockAlertItem item;
  final TextEditingController qtyController;
  final TextEditingController notesController;
  final VoidCallback onConfirm;

  const _RestockDialog({
    required this.item,
    required this.qtyController,
    required this.notesController,
    required this.onConfirm,
  });

  @override
  State<_RestockDialog> createState() => _RestockDialogState();
}

class _RestockDialogState extends State<_RestockDialog> {
  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
      title: Text('Restock ${widget.item.name}'),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Stok saat ini: ${widget.item.currentStock} (min: ${widget.item.minStock})',
            style: const TextStyle(color: AppColors.textSecondary),
          ),
          const SizedBox(height: 16),
          TextField(
            controller: widget.qtyController,
            keyboardType: TextInputType.number,
            inputFormatters: [FilteringTextInputFormatter.digitsOnly],
            autofocus: true,
            decoration: InputDecoration(
              labelText: 'Jumlah tambah stok',
              border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
              focusedBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(12),
                borderSide: const BorderSide(color: AppColors.primary, width: 2),
              ),
            ),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: widget.notesController,
            decoration: InputDecoration(
              labelText: 'Catatan (opsional)',
              hintText: 'mis: terima dari supplier',
              border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
              focusedBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(12),
                borderSide: const BorderSide(color: AppColors.primary, width: 2),
              ),
            ),
          ),
        ],
      ),
      actions: [
        TextButton(onPressed: () => Navigator.pop(context), child: const Text('Batal')),
        ElevatedButton(
          onPressed: widget.onConfirm,
          child: const Text('Simpan'),
        ),
      ],
    );
  }
}

class _LevelConfig {
  final Color color;
  final IconData icon;
  final String label;
  _LevelConfig({required this.color, required this.icon, required this.label});
}
