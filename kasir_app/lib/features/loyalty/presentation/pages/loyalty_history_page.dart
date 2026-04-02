import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';
import 'package:lucide_icons/lucide_icons.dart';
import '../../../../core/theme/app_colors.dart';
import '../../providers/loyalty_provider.dart';

class LoyaltyHistoryPage extends ConsumerWidget {
  final String customerId;
  final String customerName;

  const LoyaltyHistoryPage({
    super.key,
    required this.customerId,
    required this.customerName,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final balanceAsync = ref.watch(loyaltyBalanceProvider(customerId));
    final historyAsync = ref.watch(loyaltyHistoryProvider(customerId));
    final currency = NumberFormat.currency(locale: 'id_ID', symbol: 'Rp ', decimalDigits: 0);

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        backgroundColor: Colors.white,
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Poin Loyalitas', style: const TextStyle(color: AppColors.textPrimary, fontSize: 16, fontWeight: FontWeight.bold)),
            Text(customerName, style: const TextStyle(color: AppColors.textSecondary, fontSize: 12)),
          ],
        ),
        iconTheme: const IconThemeData(color: AppColors.textPrimary),
        elevation: 0,
        actions: [
          IconButton(
            icon: const Icon(LucideIcons.refreshCw, color: AppColors.primary),
            onPressed: () {
              ref.invalidate(loyaltyBalanceProvider(customerId));
              ref.invalidate(loyaltyHistoryProvider(customerId));
            },
          ),
          const SizedBox(width: 8),
        ],
      ),
      body: Column(
        children: [
          // Balance Card
          balanceAsync.when(
            loading: () => const LinearProgressIndicator(),
            error: (_, __) => const SizedBox.shrink(),
            data: (balance) => balance == null
                ? const SizedBox.shrink()
                : _BalanceCard(balance: balance, currency: currency),
          ),

          // Info rate
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
            child: Row(
              children: [
                _RateChip(icon: LucideIcons.trendingUp, label: '1 poin per Rp 10.000 transaksi', color: AppColors.success),
                const SizedBox(width: 8),
                _RateChip(icon: LucideIcons.tag, label: '1 poin = Rp 100 diskon', color: AppColors.primary),
              ],
            ),
          ),

          // History
          Expanded(
            child: historyAsync.when(
              loading: () => const Center(child: CircularProgressIndicator()),
              error: (e, _) => Center(child: Text('Gagal memuat: $e')),
              data: (txns) => txns.isEmpty
                  ? _buildEmpty()
                  : ListView.builder(
                      padding: const EdgeInsets.fromLTRB(16, 4, 16, 24),
                      itemCount: txns.length,
                      itemBuilder: (_, i) => _TxnTile(txn: txns[i]),
                    ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildEmpty() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Container(
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(
              color: AppColors.surfaceVariant,
              shape: BoxShape.circle,
            ),
            child: const Icon(LucideIcons.star, size: 36, color: AppColors.textTertiary),
          ),
          const SizedBox(height: 16),
          const Text('Belum ada riwayat poin',
              style: TextStyle(color: AppColors.textSecondary, fontWeight: FontWeight.w500)),
          const SizedBox(height: 4),
          const Text('Poin akan muncul setelah transaksi selesai',
              style: TextStyle(color: AppColors.textTertiary, fontSize: 12)),
        ],
      ),
    );
  }
}

class _BalanceCard extends StatelessWidget {
  final LoyaltyBalance balance;
  final NumberFormat currency;

  const _BalanceCard({required this.balance, required this.currency});

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.all(16),
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          colors: [AppColors.primary, Color(0xFFE86A2C)],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(20),
        boxShadow: [
          BoxShadow(
            color: AppColors.primary.withOpacity(0.3),
            blurRadius: 16,
            offset: const Offset(0, 6),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(LucideIcons.star, color: Colors.white, size: 18),
              const SizedBox(width: 8),
              const Text('Saldo Poin', style: TextStyle(color: Colors.white70, fontSize: 13)),
              const Spacer(),
              Text(
                'Nilai ${currency.format(balance.redeemValueRp)}',
                style: const TextStyle(color: Colors.white70, fontSize: 12),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Text(
            '${balance.balance.toInt()}',
            style: const TextStyle(
              color: Colors.white,
              fontSize: 42,
              fontWeight: FontWeight.w800,
              letterSpacing: -1,
            ),
          ),
          const Text('poin', style: TextStyle(color: Colors.white70, fontSize: 14)),
          const SizedBox(height: 16),
          Row(
            children: [
              _StatItem(label: 'Total Didapat', value: '${balance.lifetimeEarned.toInt()} poin'),
              const SizedBox(width: 24),
              _StatItem(label: 'Total Diredeem', value: '${balance.lifetimeRedeemed.toInt()} poin'),
            ],
          ),
        ],
      ),
    );
  }
}

class _StatItem extends StatelessWidget {
  final String label;
  final String value;

  const _StatItem({required this.label, required this.value});

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: const TextStyle(color: Colors.white60, fontSize: 11)),
        const SizedBox(height: 2),
        Text(value, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 13)),
      ],
    );
  }
}

class _RateChip extends StatelessWidget {
  final IconData icon;
  final String label;
  final Color color;

  const _RateChip({required this.icon, required this.label, required this.color});

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 7),
        decoration: BoxDecoration(
          color: color.withOpacity(0.08),
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: color.withOpacity(0.25)),
        ),
        child: Row(
          children: [
            Icon(icon, size: 13, color: color),
            const SizedBox(width: 6),
            Expanded(
              child: Text(label,
                  style: TextStyle(color: color, fontSize: 11, fontWeight: FontWeight.w500)),
            ),
          ],
        ),
      ),
    );
  }
}

class _TxnTile extends StatelessWidget {
  final PointTxn txn;

  const _TxnTile({required this.txn});

  @override
  Widget build(BuildContext context) {
    final isEarn = txn.type == 'earn';
    final isRedeem = txn.type == 'redeem';
    final color = isEarn ? AppColors.success : isRedeem ? AppColors.error : AppColors.warning;
    final icon = isEarn
        ? LucideIcons.plusCircle
        : isRedeem
            ? LucideIcons.minusCircle
            : LucideIcons.refreshCw;
    final prefix = isEarn ? '+' : '-';

    final date = DateTime.tryParse(txn.createdAt);
    final dateStr = date != null
        ? DateFormat('dd MMM yyyy, HH:mm', 'id_ID').format(date.toLocal())
        : txn.createdAt;

    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.border),
      ),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.all(8),
            decoration: BoxDecoration(
              color: color.withOpacity(0.1),
              borderRadius: BorderRadius.circular(8),
            ),
            child: Icon(icon, size: 18, color: color),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  txn.description ?? txn.type,
                  style: const TextStyle(fontWeight: FontWeight.w500, fontSize: 13),
                ),
                const SizedBox(height: 2),
                Text(dateStr,
                    style: const TextStyle(color: AppColors.textTertiary, fontSize: 11)),
              ],
            ),
          ),
          Column(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Text(
                '$prefix${txn.amount.toInt()} poin',
                style: TextStyle(
                  color: color,
                  fontWeight: FontWeight.bold,
                  fontSize: 14,
                ),
              ),
              Text(
                'Saldo: ${txn.balanceAfter.toInt()}',
                style: const TextStyle(color: AppColors.textTertiary, fontSize: 11),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
