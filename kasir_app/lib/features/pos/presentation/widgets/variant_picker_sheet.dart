import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:intl/intl.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';

import '../../../../core/theme/kasira_ds.dart';
import '../../../products/providers/variants_provider.dart';

/// Hasil pilihan varian.
class VariantChoice {
  final ProductVariantModel variant;
  final double price;

  const VariantChoice({required this.variant, required this.price});
}

/// Pemilih varian produk — SATU-SATUNYA tempat kasir milih Hot/Ice, size, dll.
///
/// Dibikin helper fungsi (bukan widget yang dipanggil langsung) dengan alasan
/// yang sama kayak `showGuestCountSheet`: begitu ada dua entry point ke POS
/// (grid produk & upsell keranjang), satu-satunya cara mastiin dua-duanya
/// nanya hal yang sama adalah lewat satu pintu. Kalau nanti nambah jalur
/// ketiga (scan barcode, misalnya), lewat sini juga.
///
/// Return `null` kalau kasir batal — pemanggil WAJIB nge-cek dan nggak
/// nambahin apa pun ke keranjang.
Future<VariantChoice?> showVariantPickerSheet(
  BuildContext context, {
  required String productName,
  required double basePrice,
  required List<ProductVariantModel> variants,
}) {
  return showModalBottomSheet<VariantChoice>(
    context: context,
    isScrollControlled: true,
    backgroundColor: Colors.transparent,
    builder: (_) => _VariantPickerSheet(
      productName: productName,
      basePrice: basePrice,
      variants: variants,
    ),
  );
}

class _VariantPickerSheet extends StatelessWidget {
  final String productName;
  final double basePrice;
  final List<ProductVariantModel> variants;

  const _VariantPickerSheet({
    required this.productName,
    required this.basePrice,
    required this.variants,
  });

  @override
  Widget build(BuildContext context) {
    final currency = NumberFormat.currency(
      locale: 'id_ID',
      symbol: 'Rp ',
      decimalDigits: 0,
    );

    return Container(
      decoration: const BoxDecoration(
        color: KasiraDS.surfaceCard,
        borderRadius: BorderRadius.vertical(top: Radius.circular(KasiraDS.radiusXl)),
      ),
      padding: EdgeInsets.only(
        left: KasiraDS.space5,
        right: KasiraDS.space5,
        top: KasiraDS.space3,
        bottom: MediaQuery.of(context).padding.bottom + KasiraDS.space6,
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Center(
            child: Container(
              width: 44,
              height: 5,
              decoration: BoxDecoration(
                color: KasiraDS.borderDefault,
                borderRadius: KasiraDS.brPill,
              ),
            ),
          ),
          const SizedBox(height: KasiraDS.space5),
          Text('PILIH VARIAN', style: KasiraDS.eyebrow(color: KasiraDS.brandPrimary)),
          const SizedBox(height: KasiraDS.space2),
          Text(
            productName,
            style: KasiraDS.display(size: 26),
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
          ),
          const SizedBox(height: KasiraDS.space5),

          // Daftar varian. Tiap baris nampilin HARGA AKHIR, bukan selisihnya
          // doang — kasir yang lagi buru-buru baca angka yang bakal dia
          // sebutkan ke pelanggan, bukan matematika "+2000 dari berapa".
          // Selisih tetap ditulis kecil di sebelahnya buat yang mau ngecek.
          //
          // Sengaja dibungkus scroll + tinggi maksimal: produk dengan 8 varian
          // (level gula × size) bakal lebih tinggi dari layar HP kecil, dan
          // sheet yang kepotong bikin varian terakhir nggak bisa dipilih.
          Flexible(
            child: SingleChildScrollView(
              child: Column(
                children: [
                  for (final v in variants) ...[
                    _VariantTile(
                      variant: v,
                      price: v.priceFor(basePrice),
                      currency: currency,
                      onTap: () {
                        HapticFeedback.selectionClick();
                        Navigator.pop(
                          context,
                          VariantChoice(variant: v, price: v.priceFor(basePrice)),
                        );
                      },
                    ),
                    const SizedBox(height: KasiraDS.space2),
                  ],
                ],
              ),
            ),
          ),

          const SizedBox(height: KasiraDS.space3),
          SizedBox(
            width: double.infinity,
            height: 52,
            child: OutlinedButton(
              onPressed: () => Navigator.pop(context),
              style: OutlinedButton.styleFrom(
                side: const BorderSide(color: KasiraDS.borderDefault),
                shape: RoundedRectangleBorder(borderRadius: KasiraDS.brMd),
              ),
              child: Text(
                'Batal',
                style: KasiraDS.sans(
                  size: 15,
                  weight: FontWeight.w700,
                  color: KasiraDS.textBody,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _VariantTile extends StatelessWidget {
  final ProductVariantModel variant;
  final double price;
  final NumberFormat currency;
  final VoidCallback onTap;

  const _VariantTile({
    required this.variant,
    required this.price,
    required this.currency,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final adj = variant.adjustmentLabel();

    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        borderRadius: KasiraDS.brMd,
        child: Container(
          // 64px: varian di-tap sambil berdiri, satu tangan megang HP, di
          // depan antrean. Target kecil = salah pencet = minuman salah.
          height: 64,
          padding: const EdgeInsets.symmetric(horizontal: KasiraDS.space4),
          decoration: BoxDecoration(
            color: KasiraDS.surfaceSunken,
            borderRadius: KasiraDS.brMd,
            border: Border.all(color: KasiraDS.borderSubtle),
          ),
          child: Row(
            children: [
              Expanded(
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      variant.name,
                      style: KasiraDS.sans(
                        size: 16,
                        weight: FontWeight.w700,
                        color: KasiraDS.textStrong,
                      ),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                    if (adj.isNotEmpty) ...[
                      const SizedBox(height: 2),
                      Text(
                        adj,
                        style: KasiraDS.sans(size: 12, color: KasiraDS.textMuted),
                      ),
                    ],
                  ],
                ),
              ),
              const SizedBox(width: KasiraDS.space3),
              Text(
                currency.format(price),
                style: KasiraDS.sans(
                  size: 16,
                  weight: FontWeight.w800,
                  color: KasiraDS.brandPrimary,
                ),
              ),
              const SizedBox(width: KasiraDS.space2),
              const Icon(LucideIcons.chevronRight, size: 18, color: KasiraDS.textMuted),
            ],
          ),
        ),
      ),
    );
  }
}
