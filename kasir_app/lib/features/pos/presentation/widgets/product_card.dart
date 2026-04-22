import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:cached_network_image/cached_network_image.dart';
import 'package:lucide_icons/lucide_icons.dart';
import '../../../../core/theme/app_colors.dart';

class ProductCard extends StatelessWidget {
  final String name;
  final double price;
  final int stock;
  final bool stockEnabled;
  final bool isAvailable;
  final String imageUrl;
  final VoidCallback onTap;
  final VoidCallback? onLongPress;
  final bool isBestSeller;

  const ProductCard({
    super.key,
    required this.name,
    required this.price,
    required this.stock,
    this.stockEnabled = false,
    this.isAvailable = true,
    required this.imageUrl,
    required this.onTap,
    this.onLongPress,
    this.isBestSeller = false,
  });

  @override
  Widget build(BuildContext context) {
    final isOutOfStock = stockEnabled && stock <= 0;
    final isDisabled = !isAvailable || isOutOfStock;
    final badgeLabel = isOutOfStock ? 'HABIS' : 'NONAKTIF';
    final currencyFormatter =
        NumberFormat.currency(locale: 'id_ID', symbol: 'Rp ', decimalDigits: 0);

    return Material(
      color: AppColors.surface,
      borderRadius: BorderRadius.circular(14),
      clipBehavior: Clip.antiAlias,
      elevation: 0,
      child: InkWell(
        onTap: isDisabled ? null : onTap,
        onLongPress: isDisabled ? null : onLongPress,
        splashColor: AppColors.primary.withOpacity(0.08),
        highlightColor: AppColors.primary.withOpacity(0.04),
        child: Container(
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(14),
            border: Border.all(color: AppColors.border, width: 0.5),
          ),
          child: Stack(
            children: [
              Opacity(
                opacity: isDisabled ? 0.5 : 1.0,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // Image area
                    Expanded(
                      flex: 3,
                      child: Container(
                        width: double.infinity,
                        color: AppColors.surfaceVariant,
                        child: CachedNetworkImage(
                          imageUrl: imageUrl,
                          fit: BoxFit.cover,
                          memCacheWidth: 300,
                          fadeInDuration: const Duration(milliseconds: 150),
                          placeholder: (_, __) => const Center(
                            child: Icon(LucideIcons.image,
                                color: AppColors.textTertiary, size: 28),
                          ),
                          errorWidget: (_, __, ___) => const Center(
                            child: Icon(LucideIcons.image,
                                color: AppColors.textTertiary, size: 28),
                          ),
                        ),
                      ),
                    ),
                    // Info area
                    Expanded(
                      flex: 2,
                      child: Padding(
                        padding: const EdgeInsets.fromLTRB(10, 8, 10, 8),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            Text(
                              name,
                              maxLines: 2,
                              overflow: TextOverflow.ellipsis,
                              style: TextStyle(
                                fontWeight: FontWeight.w600,
                                fontSize: 12,
                                color: isDisabled
                                    ? AppColors.textTertiary
                                    : AppColors.textPrimary,
                                height: 1.3,
                              ),
                            ),
                            Row(
                              mainAxisAlignment: MainAxisAlignment.spaceBetween,
                              children: [
                                Flexible(
                                  child: Text(
                                    currencyFormatter.format(price),
                                    style: TextStyle(
                                      color: isDisabled
                                          ? AppColors.textTertiary
                                          : AppColors.primary,
                                      fontWeight: FontWeight.bold,
                                      fontSize: 13,
                                    ),
                                    overflow: TextOverflow.ellipsis,
                                  ),
                                ),
                                if (!isDisabled)
                                  Container(
                                    width: 26,
                                    height: 26,
                                    decoration: BoxDecoration(
                                      color: AppColors.primary,
                                      borderRadius: BorderRadius.circular(8),
                                    ),
                                    child: const Icon(LucideIcons.plus,
                                        size: 14, color: Colors.white),
                                  ),
                              ],
                            ),
                          ],
                        ),
                      ),
                    ),
                  ],
                ),
              ),

              // Best seller badge
              if (isBestSeller && !isDisabled)
                Positioned(
                  top: 6,
                  left: 6,
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 3),
                    decoration: BoxDecoration(
                      color: const Color(0xFFF59E0B),
                      borderRadius: BorderRadius.circular(6),
                      boxShadow: [
                        BoxShadow(
                          color: const Color(0xFFF59E0B).withOpacity(0.3),
                          blurRadius: 4,
                          offset: const Offset(0, 1),
                        ),
                      ],
                    ),
                    child: const Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(LucideIcons.flame, size: 10, color: Colors.white),
                        SizedBox(width: 3),
                        Text(
                          'Populer',
                          style: TextStyle(
                            color: Colors.white,
                            fontWeight: FontWeight.bold,
                            fontSize: 9,
                            letterSpacing: 0.3,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),

              // Disabled overlay (out of stock or deactivated)
              if (isDisabled)
                Positioned.fill(
                  child: Container(
                    color: AppColors.background.withOpacity(0.75),
                    child: Center(
                      child: Container(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 10, vertical: 5),
                        decoration: BoxDecoration(
                          color: AppColors.textSecondary,
                          borderRadius: BorderRadius.circular(6),
                        ),
                        child: Text(
                          badgeLabel,
                          style: const TextStyle(
                            color: Colors.white,
                            fontWeight: FontWeight.bold,
                            fontSize: 11,
                            letterSpacing: 0.5,
                          ),
                        ),
                      ),
                    ),
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }
}
