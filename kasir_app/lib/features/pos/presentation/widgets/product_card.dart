import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:cached_network_image/cached_network_image.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';
import '../../../../core/theme/kasira_ds.dart';

/// Product tile — ported 1:1 from the "Kasira POS.dc.html" Kasir grid card:
/// white surface-card, radius-20, subtle border + soft shadow, an icon/photo
/// tile, name, price in Gabarito, and a gradient add button (glow-pink) that
/// swaps to a −/qty/+ stepper once the item is in the cart.
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

  /// In-cart quantity. When > 0 the add button becomes a −/qty/+ stepper.
  final int qty;
  final VoidCallback? onIncrement;
  final VoidCallback? onDecrement;

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
    this.qty = 0,
    this.onIncrement,
    this.onDecrement,
  });

  static final _rp =
      NumberFormat.currency(locale: 'id_ID', symbol: 'Rp', decimalDigits: 0);

  @override
  Widget build(BuildContext context) {
    final isOutOfStock = stockEnabled && stock <= 0;
    final isDisabled = !isAvailable || isOutOfStock;
    final badgeLabel = isOutOfStock ? 'HABIS' : 'NONAKTIF';
    final inCart = qty > 0 && onIncrement != null;

    return Opacity(
      opacity: isDisabled ? 0.55 : 1,
      child: Container(
        decoration: BoxDecoration(
          color: KasiraDS.surfaceCard,
          borderRadius: KasiraDS.brLg,
          border: Border.all(color: KasiraDS.borderSubtle),
          boxShadow: KasiraDS.shadowSm,
        ),
        clipBehavior: Clip.antiAlias,
        child: Material(
          color: Colors.transparent,
          child: InkWell(
            onTap: isDisabled ? null : onTap,
            onLongPress: isDisabled ? null : onLongPress,
            splashColor: KasiraDS.brandTint,
            highlightColor: KasiraDS.brandTint.withOpacity(0.5),
            child: Padding(
              padding: const EdgeInsets.all(12),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // ── icon / photo tile ──
                  Expanded(
                    child: Stack(
                      children: [
                        Positioned.fill(child: _tile()),
                        if (isBestSeller && !isDisabled)
                          const Positioned(top: 6, left: 6, child: _PopularBadge()),
                        if (isDisabled)
                          Positioned.fill(child: _disabledOverlay(badgeLabel)),
                      ],
                    ),
                  ),
                  const SizedBox(height: 11),
                  // ── name ──
                  SizedBox(
                    height: 34,
                    child: Text(
                      name,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: KasiraDS.sans(
                        size: 13.5,
                        weight: FontWeight.w700,
                        color: KasiraDS.textStrong,
                        height: 1.25,
                      ),
                    ),
                  ),
                  const SizedBox(height: 7),
                  // ── price + add / stepper ──
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    crossAxisAlignment: CrossAxisAlignment.center,
                    children: [
                      Flexible(
                        child: Text(
                          _rp.format(price),
                          overflow: TextOverflow.ellipsis,
                          style: KasiraDS.display(
                            size: 14.5,
                            color: KasiraDS.textStrong,
                          ),
                        ),
                      ),
                      const SizedBox(width: 6),
                      if (!isDisabled)
                        inCart ? _stepper() : _addButton(),
                    ],
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _tile() {
    final hasImage = imageUrl.trim().isNotEmpty;
    return DecoratedBox(
      decoration: BoxDecoration(
        color: KasiraDS.brandTint,
        borderRadius: KasiraDS.brMd,
      ),
      child: ClipRRect(
        borderRadius: KasiraDS.brMd,
        child: hasImage
            ? CachedNetworkImage(
                imageUrl: imageUrl,
                fit: BoxFit.cover,
                width: double.infinity,
                height: double.infinity,
                memCacheWidth: 300,
                fadeInDuration: const Duration(milliseconds: 150),
                placeholder: (_, __) => _iconFallback(),
                errorWidget: (_, __, ___) => _iconFallback(),
              )
            : _iconFallback(),
      ),
    );
  }

  Widget _iconFallback() => const Center(
        child: Icon(LucideIcons.coffee, size: 28, color: KasiraDS.brandPrimary),
      );

  Widget _addButton() => Container(
        width: 34,
        height: 34,
        decoration: BoxDecoration(
          gradient: KasiraDS.gradientFrekuensi,
          shape: BoxShape.circle,
          boxShadow: KasiraDS.glowPink,
        ),
        child: const Icon(LucideIcons.plus, size: 19, color: Colors.white),
      );

  Widget _stepper() => Container(
        padding: const EdgeInsets.all(3),
        decoration: BoxDecoration(
          color: KasiraDS.surfaceSunken,
          borderRadius: KasiraDS.brPill,
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            _stepBtn(
              onTap: onDecrement,
              filled: false,
              child: const Text('−',
                  style: TextStyle(
                      fontSize: 17,
                      fontWeight: FontWeight.w700,
                      color: KasiraDS.textStrong,
                      height: 1)),
            ),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 6),
              child: Text('$qty',
                  style: KasiraDS.sans(
                      size: 14,
                      weight: FontWeight.w800,
                      color: KasiraDS.textStrong)),
            ),
            _stepBtn(
              onTap: onIncrement,
              filled: true,
              child: const Icon(LucideIcons.plus, size: 15, color: Colors.white),
            ),
          ],
        ),
      );

  Widget _stepBtn({
    required VoidCallback? onTap,
    required bool filled,
    required Widget child,
  }) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        width: 26,
        height: 26,
        alignment: Alignment.center,
        decoration: BoxDecoration(
          gradient: filled ? KasiraDS.gradientFrekuensi : null,
          color: filled ? null : KasiraDS.surfaceCard,
          shape: BoxShape.circle,
          boxShadow: filled ? null : KasiraDS.shadowSm,
        ),
        child: child,
      ),
    );
  }

  Widget _disabledOverlay(String label) => DecoratedBox(
        decoration: BoxDecoration(
          color: KasiraDS.surfaceCard.withOpacity(0.6),
          borderRadius: KasiraDS.brMd,
        ),
        child: Center(
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
            decoration: BoxDecoration(
              color: KasiraDS.neutral600,
              borderRadius: KasiraDS.brSm,
            ),
            child: Text(
              label,
              style: KasiraDS.mono(
                  size: 10,
                  weight: FontWeight.w700,
                  color: Colors.white,
                  letterSpacing: 0.5),
            ),
          ),
        ),
      );
}

class _PopularBadge extends StatelessWidget {
  const _PopularBadge();

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 3),
      decoration: BoxDecoration(
        gradient: KasiraDS.gradientFrekuensi,
        borderRadius: KasiraDS.brSm,
        boxShadow: KasiraDS.glowPink,
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Icon(LucideIcons.flame, size: 10, color: Colors.white),
          const SizedBox(width: 3),
          Text('Populer',
              style: KasiraDS.mono(
                  size: 9, weight: FontWeight.w700, color: Colors.white)),
        ],
      ),
    );
  }
}
