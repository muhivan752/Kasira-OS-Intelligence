import 'package:flutter/material.dart';
import 'package:lucide_icons/lucide_icons.dart';
import 'package:dio/dio.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import '../../../../core/config/app_config.dart';
import '../../../../core/theme/app_colors.dart';

class AddCustomerModal extends StatefulWidget {
  const AddCustomerModal({super.key});

  @override
  State<AddCustomerModal> createState() => _AddCustomerModalState();
}

class _AddCustomerModalState extends State<AddCustomerModal> {
  final _nameController = TextEditingController();
  final _phoneController = TextEditingController();
  final _emailController = TextEditingController();
  final _storage = const FlutterSecureStorage();
  bool _isLoading = false;

  @override
  void dispose() {
    _nameController.dispose();
    _phoneController.dispose();
    _emailController.dispose();
    super.dispose();
  }

  Future<void> _saveCustomer() async {
    final name = _nameController.text.trim();
    if (name.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Nama pelanggan wajib diisi'), backgroundColor: AppColors.error),
      );
      return;
    }

    setState(() => _isLoading = true);

    try {
      final token = await _storage.read(key: 'access_token');
      final tenantId = await _storage.read(key: 'tenant_id');

      final dio = Dio(BaseOptions(
        baseUrl: AppConfig.apiV1,
        connectTimeout: const Duration(seconds: 15),
        receiveTimeout: const Duration(seconds: 15),
      ));

      final response = await dio.post(
        '/customers/',
        options: Options(headers: {
          if (token != null) 'Authorization': 'Bearer $token',
          if (tenantId != null) 'X-Tenant-ID': tenantId,
        }),
        data: {
          'name': name,
          if (_phoneController.text.trim().isNotEmpty) 'phone': _phoneController.text.trim(),
          if (_emailController.text.trim().isNotEmpty) 'email': _emailController.text.trim(),
        },
      );

      if (mounted) {
        Navigator.pop(context, response.data['data']);
      }
    } on DioException catch (e) {
      final detail = e.response?.data?['detail'] ?? 'Gagal menyimpan pelanggan';
      if (mounted) {
        setState(() => _isLoading = false);
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(detail.toString()), backgroundColor: AppColors.error),
        );
      }
    } catch (e) {
      if (mounted) {
        setState(() => _isLoading = false);
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Terjadi kesalahan: $e'), backgroundColor: AppColors.error),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Dialog(
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(24)),
      child: Container(
        width: 500,
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text('Tambah Pelanggan Baru', style: Theme.of(context).textTheme.headlineSmall),
                IconButton(onPressed: () => Navigator.pop(context), icon: const Icon(LucideIcons.x)),
              ],
            ),
            const SizedBox(height: 24),

            _buildTextField('Nama Lengkap *', LucideIcons.user, 'Masukkan nama pelanggan', _nameController),
            const SizedBox(height: 16),
            _buildTextField('Nomor Telepon', LucideIcons.phone, 'Contoh: 081234567890', _phoneController,
                keyboardType: TextInputType.phone),
            const SizedBox(height: 16),
            _buildTextField('Email (Opsional)', LucideIcons.mail, 'Contoh: budi@email.com', _emailController,
                keyboardType: TextInputType.emailAddress),

            const SizedBox(height: 32),

            ElevatedButton(
              onPressed: _isLoading ? null : _saveCustomer,
              style: ElevatedButton.styleFrom(minimumSize: const Size(double.infinity, 56)),
              child: _isLoading
                  ? const SizedBox(height: 20, width: 20, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
                  : const Text('SIMPAN PELANGGAN', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildTextField(String label, IconData icon, String hint, TextEditingController controller,
      {TextInputType keyboardType = TextInputType.text}) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: const TextStyle(fontWeight: FontWeight.bold, color: AppColors.textSecondary)),
        const SizedBox(height: 8),
        Container(
          decoration: BoxDecoration(
            color: AppColors.surfaceVariant,
            borderRadius: BorderRadius.circular(12),
          ),
          child: TextField(
            controller: controller,
            keyboardType: keyboardType,
            decoration: InputDecoration(
              hintText: hint,
              prefixIcon: Icon(icon, color: AppColors.textTertiary),
              border: InputBorder.none,
              contentPadding: const EdgeInsets.symmetric(vertical: 16),
            ),
          ),
        ),
      ],
    );
  }
}
