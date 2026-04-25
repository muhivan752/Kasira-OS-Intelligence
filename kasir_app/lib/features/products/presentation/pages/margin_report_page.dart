import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';
import 'package:lucide_icons/lucide_icons.dart';

import '../../../../core/config/app_config.dart';
import '../../../../core/services/session_cache.dart';
import '../../../../core/theme/app_colors.dart';

/// Laporan Untung-Rugi — Starter margin tracking.
/// Sumber data: GET /api/v1/reports/margin?outlet_id=...
/// Recipe mode → 400 STOCK_MODE_NOT_SUPPORTED → arahkan user ke dashboard HPP.
///
/// Embedded mode (true) untuk dipakai di TabBarView ProductManagementPage —
/// render body saja tanpa Scaffold/AppBar.
class MarginReportPage extends ConsumerStatefulWidget {
  final bool embedded;
  const MarginReportPage({super.key, this.embedded = false});

  @override
  ConsumerState<MarginReportPage> createState() => _MarginReportPageState();
}

class _MarginReportPageState extends ConsumerState<MarginReportPage> {
  final _currency =
      NumberFormat.currency(locale: 'id_ID', symbol: 'Rp ', decimalDigits: 0);
  Future<_MarginReport>? _future;

  @override
  void initState() {
    super.initState();
    _future = _fetch();
  }

  Future<void> _refresh() async {
    setState(() => _future = _fetch());
    await _future;
  }

  Future<_MarginReport> _fetch() async {
    final cache = SessionCache.instance;
    final outletId = cache.outletId;
    if (outletId == null || outletId.isEmpty) {
      throw const _MarginReportError('Outlet belum tersedia — silakan login ulang.');
    }

    final dio = Dio(BaseOptions(
      baseUrl: AppConfig.apiV1,
      connectTimeout: const Duration(seconds: 15),
      receiveTimeout: const Duration(seconds: 15),
    ));

    try {
      final resp = await dio.get(
        '/reports/margin',
        queryParameters: {'outlet_id': outletId},
        options: Options(headers: cache.authHeaders),
      );
      final data = resp.data['data'] as Map<String, dynamic>;
      return _MarginReport.fromJson(data);
    } on DioException catch (e) {
      // Backend balikin 400 STOCK_MODE_NOT_SUPPORTED untuk recipe mode.
      final status = e.response?.statusCode;
      final detail = e.response?.data?['detail'];
      if (status == 400 && detail is Map && detail['code'] == 'STOCK_MODE_NOT_SUPPORTED') {
        throw const _MarginReportError(
          'Outlet ini pakai mode Resep. Lihat Laporan HPP di dashboard untuk margin berbasis bahan baku.',
          isRecipeMode: true,
        );
      }
      throw _MarginReportError(
        detail is String
            ? detail
            : (detail is Map ? detail['message']?.toString() ?? 'Gagal memuat laporan' : 'Gagal memuat laporan'),
      );
    } catch (_) {
      throw const _MarginReportError('Koneksi bermasalah. Coba lagi.');
    }
  }

  @override
  Widget build(BuildContext context) {
    final body = FutureBuilder<_MarginReport>(
      future: _future,
      builder: (context, snapshot) {
        if (snapshot.connectionState == ConnectionState.waiting) {
          return const Center(child: CircularProgressIndicator());
        }
        if (snapshot.hasError) {
          final err = snapshot.error;
          final msg = err is _MarginReportError ? err.message : 'Gagal memuat laporan';
          final isRecipe = err is _MarginReportError && err.isRecipeMode;
          return RefreshIndicator(
            onRefresh: _refresh,
            child: ListView(
              padding: const EdgeInsets.all(24),
              children: [
                const SizedBox(height: 60),
                Icon(
                  isRecipe ? LucideIcons.book : LucideIcons.wifiOff,
                  size: 48,
                  color: AppColors.textTertiary,
                ),
                const SizedBox(height: 16),
                Text(
                  msg,
                  textAlign: TextAlign.center,
                  style: const TextStyle(
                      color: AppColors.textSecondary, fontSize: 14, height: 1.4),
                ),
                const SizedBox(height: 16),
                Center(
                  child: TextButton.icon(
                    onPressed: _refresh,
                    icon: const Icon(LucideIcons.refreshCw, size: 14),
                    label: const Text('Coba lagi'),
                  ),
                ),
              ],
            ),
          );
        }

        final report = snapshot.data!;
        return RefreshIndicator(
          onRefresh: _refresh,
          child: ListView(
            padding: const EdgeInsets.all(16),
            children: [
              _SummaryCard(report: report, currency: _currency),
              const SizedBox(height: 16),
              if (report.products.isEmpty)
                const _EmptyState()
              else ...[
                if (report.summary.missingBuyPrice > 0) ...[
                  _ActionFocusBanner(
                    missingCount: report.summary.missingBuyPrice,
                  ),
                  const SizedBox(height: 12),
                ],
                ...report.products.map((p) => _MarginTile(product: p, currency: _currency)),
              ],
            ],
          ),
        );
      },
    );

    if (widget.embedded) return body;
    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        title: const Text('Laporan Untung-Rugi'),
        backgroundColor: AppColors.surface,
        foregroundColor: AppColors.textPrimary,
        elevation: 0,
      ),
      body: body,
    );
  }
}

class _SummaryCard extends StatelessWidget {
  final _MarginReport report;
  final NumberFormat currency;
  const _SummaryCard({required this.report, required this.currency});

  @override
  Widget build(BuildContext context) {
    final s = report.summary;
    final pctText = s.avgMarginPct != null
        ? '${s.avgMarginPct!.toStringAsFixed(1)}%'
        : '—';
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.primary.withOpacity(0.06),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.primary.withOpacity(0.2)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(LucideIcons.trendingUp,
                  size: 18, color: AppColors.primary),
              const SizedBox(width: 8),
              const Text(
                'Ringkasan Margin',
                style: TextStyle(
                  fontWeight: FontWeight.bold,
                  fontSize: 14,
                  color: AppColors.textPrimary,
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Row(
            children: [
              Expanded(
                child: _SummaryStat(
                  label: 'Rata-rata',
                  value: pctText,
                  highlight: true,
                ),
              ),
              Expanded(
                child: _SummaryStat(
                  label: 'Sudah diisi',
                  value: '${s.withBuyPrice}/${s.totalProducts}',
                ),
              ),
              Expanded(
                child: _SummaryStat(
                  label: 'Belum diisi',
                  value: s.missingBuyPrice.toString(),
                  warn: s.missingBuyPrice > 0,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _SummaryStat extends StatelessWidget {
  final String label;
  final String value;
  final bool highlight;
  final bool warn;
  const _SummaryStat({
    required this.label,
    required this.value,
    this.highlight = false,
    this.warn = false,
  });

  @override
  Widget build(BuildContext context) {
    Color valueColor = AppColors.textPrimary;
    if (highlight) valueColor = AppColors.primary;
    if (warn) valueColor = AppColors.error;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          style: const TextStyle(fontSize: 11, color: AppColors.textSecondary),
        ),
        const SizedBox(height: 4),
        Text(
          value,
          style: TextStyle(
            fontSize: 16,
            fontWeight: FontWeight.bold,
            color: valueColor,
          ),
        ),
      ],
    );
  }
}

class _ActionFocusBanner extends StatelessWidget {
  final int missingCount;
  const _ActionFocusBanner({required this.missingCount});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: const Color(0xFFFEF3C7),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: const Color(0xFFFDE68A)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(LucideIcons.alertCircle,
                  size: 16, color: Color(0xFFB45309)),
              const SizedBox(width: 10),
              Expanded(
                child: Text(
                  '$missingCount produk belum diisi harga beli (modal)',
                  style: const TextStyle(
                    fontSize: 13,
                    color: Color(0xFF92400E),
                    fontWeight: FontWeight.w600,
                    height: 1.4,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 6),
          const Padding(
            padding: EdgeInsets.only(left: 26),
            child: Text(
              'Modal = harga beli ke supplier (bukan stok). '
              'Tanpa modal, margin gak bisa dihitung. '
              'Contoh: jual nasi 18rb, beli bahan 8rb → modal = 8rb.',
              style: TextStyle(
                fontSize: 11,
                color: Color(0xFF92400E),
                height: 1.45,
              ),
            ),
          ),
          const SizedBox(height: 6),
          const Padding(
            padding: EdgeInsets.only(left: 26),
            child: Text(
              'Cara isi: tab Stok → tap produk → field "Harga Beli per Unit".',
              style: TextStyle(
                fontSize: 11,
                color: Color(0xFF92400E),
                fontStyle: FontStyle.italic,
                height: 1.4,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _EmptyState extends StatelessWidget {
  const _EmptyState();

  @override
  Widget build(BuildContext context) {
    return const Padding(
      padding: EdgeInsets.symmetric(vertical: 60),
      child: Column(
        children: [
          Icon(LucideIcons.packageSearch,
              size: 40, color: AppColors.textTertiary),
          SizedBox(height: 12),
          Text(
            'Belum ada produk',
            style: TextStyle(color: AppColors.textSecondary),
          ),
        ],
      ),
    );
  }
}

class _MarginTile extends StatelessWidget {
  final _MarginProduct product;
  final NumberFormat currency;
  const _MarginTile({required this.product, required this.currency});

  @override
  Widget build(BuildContext context) {
    final missing = product.missingBuyPrice;
    final negative = product.negativeMargin;

    Color borderColor = AppColors.border;
    if (missing) borderColor = const Color(0xFFFDE68A);
    else if (negative) borderColor = AppColors.error.withOpacity(0.4);

    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: borderColor, width: missing || negative ? 1.2 : 0.5),
      ),
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  product.name,
                  style: const TextStyle(
                    fontWeight: FontWeight.w600,
                    fontSize: 14,
                    color: AppColors.textPrimary,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  'Jual: ${currency.format(product.basePrice)}'
                  '${product.buyPrice != null ? '   •   Modal: ${currency.format(product.buyPrice)}' : ''}',
                  style: const TextStyle(
                    fontSize: 11,
                    color: AppColors.textSecondary,
                  ),
                ),
                if (missing) ...[
                  const SizedBox(height: 4),
                  const Text(
                    'Belum diisi harga beli (modal)',
                    style: TextStyle(
                      fontSize: 11,
                      color: Color(0xFFB45309),
                      fontStyle: FontStyle.italic,
                    ),
                  ),
                ],
              ],
            ),
          ),
          const SizedBox(width: 12),
          Column(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              if (product.margin != null) ...[
                Text(
                  currency.format(product.margin),
                  style: TextStyle(
                    fontWeight: FontWeight.bold,
                    fontSize: 14,
                    color: negative ? AppColors.error : AppColors.success,
                  ),
                ),
                if (product.marginPct != null) ...[
                  const SizedBox(height: 2),
                  Text(
                    '${product.marginPct!.toStringAsFixed(0)}%',
                    style: TextStyle(
                      fontSize: 11,
                      color: negative ? AppColors.error : AppColors.success,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ],
              ] else
                const Text(
                  '—',
                  style: TextStyle(
                    fontSize: 14,
                    color: AppColors.textTertiary,
                    fontWeight: FontWeight.w600,
                  ),
                ),
            ],
          ),
        ],
      ),
    );
  }
}

// ====================== DTOs ======================

class _MarginReport {
  final _MarginSummary summary;
  final List<_MarginProduct> products;

  const _MarginReport({required this.summary, required this.products});

  factory _MarginReport.fromJson(Map<String, dynamic> j) {
    return _MarginReport(
      summary: _MarginSummary.fromJson(j['summary'] as Map<String, dynamic>),
      products: (j['products'] as List)
          .map((e) => _MarginProduct.fromJson(e as Map<String, dynamic>))
          .toList(),
    );
  }
}

class _MarginSummary {
  final int totalProducts;
  final int withBuyPrice;
  final int missingBuyPrice;
  final double? avgMarginPct;
  final String stockMode;

  const _MarginSummary({
    required this.totalProducts,
    required this.withBuyPrice,
    required this.missingBuyPrice,
    required this.avgMarginPct,
    required this.stockMode,
  });

  factory _MarginSummary.fromJson(Map<String, dynamic> j) {
    return _MarginSummary(
      totalProducts: (j['total_products'] as num?)?.toInt() ?? 0,
      withBuyPrice: (j['with_buy_price'] as num?)?.toInt() ?? 0,
      missingBuyPrice: (j['missing_buy_price'] as num?)?.toInt() ?? 0,
      avgMarginPct: (j['avg_margin_pct'] as num?)?.toDouble(),
      stockMode: j['stock_mode']?.toString() ?? 'simple',
    );
  }
}

class _MarginProduct {
  final String id;
  final String name;
  final double basePrice;
  final double? buyPrice;
  final double? margin;
  final double? marginPct;
  final int stockQty;
  final bool stockEnabled;
  final int soldTotal;
  final bool missingBuyPrice;
  final bool negativeMargin;

  const _MarginProduct({
    required this.id,
    required this.name,
    required this.basePrice,
    required this.buyPrice,
    required this.margin,
    required this.marginPct,
    required this.stockQty,
    required this.stockEnabled,
    required this.soldTotal,
    required this.missingBuyPrice,
    required this.negativeMargin,
  });

  factory _MarginProduct.fromJson(Map<String, dynamic> j) {
    return _MarginProduct(
      id: j['id'] as String,
      name: j['name'] as String,
      basePrice: (j['base_price'] as num?)?.toDouble() ?? 0.0,
      buyPrice: (j['buy_price'] as num?)?.toDouble(),
      margin: (j['margin'] as num?)?.toDouble(),
      marginPct: (j['margin_pct'] as num?)?.toDouble(),
      stockQty: (j['stock_qty'] as num?)?.toInt() ?? 0,
      stockEnabled: (j['stock_enabled'] as bool?) ?? false,
      soldTotal: (j['sold_total'] as num?)?.toInt() ?? 0,
      missingBuyPrice: (j['missing_buy_price'] as bool?) ?? false,
      negativeMargin: (j['negative_margin'] as bool?) ?? false,
    );
  }
}

class _MarginReportError implements Exception {
  final String message;
  final bool isRecipeMode;
  const _MarginReportError(this.message, {this.isRecipeMode = false});
}
