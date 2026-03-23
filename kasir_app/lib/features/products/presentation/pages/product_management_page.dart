import 'package:flutter/material.dart';
import 'package:lucide_icons/lucide_icons.dart';
import '../../../../core/theme/app_colors.dart';

class ProductManagementPage extends StatefulWidget {
  const ProductManagementPage({super.key});

  @override
  State<ProductManagementPage> createState() => _ProductManagementPageState();
}

class _ProductManagementPageState extends State<ProductManagementPage> {
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      body: Column(
        children: [
          // Header
          Container(
            padding: const EdgeInsets.all(24),
            color: Colors.white,
            child: Row(
              children: [
                Text('Manajemen Produk', style: Theme.of(context).textTheme.headlineMedium),
                const Spacer(),
                Container(
                  width: 300,
                  decoration: BoxDecoration(
                    color: AppColors.surfaceVariant,
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: const TextField(
                    decoration: InputDecoration(
                      hintText: 'Cari Produk...',
                      prefixIcon: Icon(LucideIcons.search, color: AppColors.textTertiary),
                      border: InputBorder.none,
                      contentPadding: EdgeInsets.symmetric(vertical: 12),
                    ),
                  ),
                ),
              ],
            ),
          ),
          
          // Product List
          Expanded(
            child: ListView.builder(
              padding: const EdgeInsets.all(24),
              itemCount: 8,
              itemBuilder: (context, index) {
                final isAvailable = index % 3 != 0; // Dummy logic for availability
                
                return Card(
                  margin: const EdgeInsets.only(bottom: 16),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Row(
                      children: [
                        // Product Image Placeholder
                        Container(
                          width: 60,
                          height: 60,
                          decoration: BoxDecoration(
                            color: AppColors.surfaceVariant,
                            borderRadius: BorderRadius.circular(8),
                          ),
                          child: const Icon(LucideIcons.coffee, color: AppColors.textTertiary),
                        ),
                        const SizedBox(width: 16),
                        
                        // Product Details
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                'Kopi Susu Gula Aren ${index + 1}', 
                                style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
                              ),
                              const SizedBox(height: 4),
                              const Text('Kategori: Kopi', style: TextStyle(color: AppColors.textSecondary)),
                            ],
                          ),
                        ),
                        
                        // Price
                        const Text(
                          'Rp 25.000', 
                          style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
                        ),
                        const SizedBox(width: 32),
                        
                        // Availability Toggle
                        Column(
                          children: [
                            Text(
                              isAvailable ? 'Tersedia' : 'Habis',
                              style: TextStyle(
                                color: isAvailable ? AppColors.success : AppColors.error,
                                fontWeight: FontWeight.bold,
                                fontSize: 12,
                              ),
                            ),
                            const SizedBox(height: 4),
                            Switch(
                              value: isAvailable,
                              onChanged: (val) {
                                // TODO: Update product availability
                              },
                              activeColor: AppColors.success,
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}
