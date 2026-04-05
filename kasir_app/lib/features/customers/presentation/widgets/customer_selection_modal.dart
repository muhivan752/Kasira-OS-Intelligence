import 'package:flutter/material.dart';
import 'package:lucide_icons/lucide_icons.dart';
import 'package:dio/dio.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import '../../../../core/config/app_config.dart';
import '../../../../core/theme/app_colors.dart';
import 'add_customer_modal.dart';

class CustomerSelectionModal extends StatefulWidget {
  final void Function(String customerId, String name) onSelected;

  const CustomerSelectionModal({super.key, required this.onSelected});

  @override
  State<CustomerSelectionModal> createState() => _CustomerSelectionModalState();
}

class _CustomerSelectionModalState extends State<CustomerSelectionModal> {
  final _searchController = TextEditingController();
  final _storage = const FlutterSecureStorage();

  List<Map<String, dynamic>> _customers = [];
  bool _isLoading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _fetchCustomers();
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  Future<void> _fetchCustomers({String? search}) async {
    setState(() {
      _isLoading = true;
      _error = null;
    });
    try {
      final token = await _storage.read(key: 'access_token');
      final tenantId = await _storage.read(key: 'tenant_id');

      final dio = Dio(BaseOptions(
        baseUrl: AppConfig.apiV1,
        connectTimeout: const Duration(seconds: 15),
        receiveTimeout: const Duration(seconds: 15),
      ));

      final response = await dio.get(
        '/customers/',
        queryParameters: {
          if (search != null && search.isNotEmpty) 'search': search,
          'limit': 50,
        },
        options: Options(headers: {
          if (token != null) 'Authorization': 'Bearer $token',
          if (tenantId != null) 'X-Tenant-ID': tenantId,
        }),
      );

      final data = response.data['data'] as List;
      setState(() {
        _customers = data.cast<Map<String, dynamic>>();
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _error = 'Gagal memuat daftar pelanggan';
        _isLoading = false;
      });
    }
  }

  void _showAddCustomerModal() async {
    final result = await showDialog<Map<String, dynamic>>(
      context: context,
      builder: (context) => const AddCustomerModal(),
    );
    if (result != null) {
      // Refresh list after adding
      _fetchCustomers(search: _searchController.text.trim().isEmpty ? null : _searchController.text.trim());
    }
  }

  @override
  Widget build(BuildContext context) {
    return Dialog(
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(24)),
      child: Container(
        width: 600,
        height: 600,
        padding: const EdgeInsets.all(32),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text('Pilih Pelanggan', style: Theme.of(context).textTheme.headlineMedium),
                IconButton(onPressed: () => Navigator.pop(context), icon: const Icon(LucideIcons.x)),
              ],
            ),
            const SizedBox(height: 24),

            Container(
              decoration: BoxDecoration(
                color: AppColors.surfaceVariant,
                borderRadius: BorderRadius.circular(12),
              ),
              child: TextField(
                controller: _searchController,
                decoration: const InputDecoration(
                  hintText: 'Cari nama atau nomor telepon...',
                  prefixIcon: Icon(LucideIcons.search, color: AppColors.textTertiary),
                  border: InputBorder.none,
                  contentPadding: EdgeInsets.symmetric(vertical: 16),
                ),
                onChanged: (val) => _fetchCustomers(search: val.trim().isEmpty ? null : val.trim()),
              ),
            ),
            const SizedBox(height: 16),

            OutlinedButton.icon(
              onPressed: _showAddCustomerModal,
              icon: const Icon(LucideIcons.userPlus, size: 18),
              label: const Text('Tambah Pelanggan Baru'),
              style: OutlinedButton.styleFrom(
                minimumSize: const Size(double.infinity, 56),
                side: const BorderSide(color: AppColors.primary),
                foregroundColor: AppColors.primary,
              ),
            ),
            const SizedBox(height: 24),

            Text('Pelanggan', style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 12),

            Expanded(
              child: _isLoading
                  ? const Center(child: CircularProgressIndicator())
                  : _error != null
                      ? Center(
                          child: Column(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              const Icon(LucideIcons.alertCircle, color: AppColors.error, size: 40),
                              const SizedBox(height: 12),
                              Text(_error!, style: const TextStyle(color: AppColors.textSecondary)),
                              const SizedBox(height: 12),
                              TextButton(onPressed: _fetchCustomers, child: const Text('Coba lagi')),
                            ],
                          ),
                        )
                      : _customers.isEmpty
                          ? const Center(
                              child: Text('Belum ada pelanggan', style: TextStyle(color: AppColors.textSecondary)),
                            )
                          : ListView.separated(
                              itemCount: _customers.length,
                              separatorBuilder: (_, __) => const Divider(height: 1, color: AppColors.border),
                              itemBuilder: (context, index) {
                                final c = _customers[index];
                                final name = c['name'] as String;
                                final phone = c['phone'] as String? ?? '-';
                                final id = c['id'] as String;
                                return ListTile(
                                  contentPadding: const EdgeInsets.symmetric(vertical: 8),
                                  leading: CircleAvatar(
                                    backgroundColor: AppColors.primary.withOpacity(0.1),
                                    child: Text(
                                      name.isNotEmpty ? name[0].toUpperCase() : '?',
                                      style: const TextStyle(color: AppColors.primary, fontWeight: FontWeight.bold),
                                    ),
                                  ),
                                  title: Text(name, style: const TextStyle(fontWeight: FontWeight.bold)),
                                  subtitle: Text(phone),
                                  trailing: ElevatedButton(
                                    onPressed: () {
                                      widget.onSelected(id, name);
                                      Navigator.pop(context);
                                    },
                                    style: ElevatedButton.styleFrom(
                                      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                                      textStyle: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold),
                                    ),
                                    child: const Text('PILIH'),
                                  ),
                                );
                              },
                            ),
            ),
          ],
        ),
      ),
    );
  }
}
