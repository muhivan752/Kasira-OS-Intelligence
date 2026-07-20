import 'package:flutter/material.dart';
import 'package:dio/dio.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';
import '../../../../core/config/app_config.dart';
import '../../../../core/services/session_cache.dart';
import '../../../../core/theme/kasira_ds.dart';

class StaffPage extends StatefulWidget {
  const StaffPage({super.key});

  @override
  State<StaffPage> createState() => _StaffPageState();
}

class _StaffPageState extends State<StaffPage> {
  bool _isLoading = true;
  List<Map<String, dynamic>> _staff = [];
  String? _error;

  Dio get _dio => Dio(BaseOptions(
        baseUrl: AppConfig.apiV1,
        connectTimeout: const Duration(seconds: 15),
        receiveTimeout: const Duration(seconds: 15),
      ));

  @override
  void initState() {
    super.initState();
    _loadStaff();
  }

  Future<void> _loadStaff() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });
    try {
      final headers = SessionCache.instance.authHeaders;
      final response = await _dio.get(
        '/users/',
        options: Options(headers: headers),
      );
      final List data = response.data['data'] ?? [];
      if (mounted) {
        setState(() {
          _staff = data.cast<Map<String, dynamic>>();
          _isLoading = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _error = 'Gagal memuat data kasir';
          _isLoading = false;
        });
      }
    }
  }

  Future<void> _toggleStatus(String userId, bool currentStatus) async {
    try {
      final headers = SessionCache.instance.authHeaders;
      await _dio.put(
        '/users/$userId/status',
        options: Options(headers: headers),
        data: {'is_active': !currentStatus},
      );
      await _loadStaff();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Gagal mengubah status kasir'),
            backgroundColor: KasiraDS.danger,
          ),
        );
      }
    }
  }

  void _showAddKasirDialog() {
    final nameCtrl = TextEditingController();
    final phoneCtrl = TextEditingController();
    final pinCtrl = TextEditingController();
    bool isSubmitting = false;

    showDialog(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setDialogState) => AlertDialog(
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
          title: const Text('Tambah Kasir Baru'),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                TextField(
                  controller: nameCtrl,
                  decoration: InputDecoration(
                    labelText: 'Nama Lengkap',
                    prefixIcon: const Icon(LucideIcons.user),
                    border: OutlineInputBorder(borderRadius: BorderRadius.circular(10)),
                  ),
                ),
                const SizedBox(height: 16),
                TextField(
                  controller: phoneCtrl,
                  keyboardType: TextInputType.phone,
                  decoration: InputDecoration(
                    labelText: 'Nomor HP (628xxx)',
                    hintText: 'Contoh: 6281234567890',
                    prefixIcon: const Icon(LucideIcons.phone),
                    border: OutlineInputBorder(borderRadius: BorderRadius.circular(10)),
                  ),
                ),
                const SizedBox(height: 16),
                TextField(
                  controller: pinCtrl,
                  keyboardType: TextInputType.number,
                  obscureText: true,
                  maxLength: 6,
                  decoration: InputDecoration(
                    labelText: 'PIN (6 digit)',
                    prefixIcon: const Icon(LucideIcons.lock),
                    border: OutlineInputBorder(borderRadius: BorderRadius.circular(10)),
                  ),
                ),
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: isSubmitting ? null : () => Navigator.pop(ctx),
              child: const Text('Batal', style: TextStyle(color: KasiraDS.textMuted)),
            ),
            ElevatedButton(
              onPressed: isSubmitting
                  ? null
                  : () async {
                      final name = nameCtrl.text.trim();
                      final phone = phoneCtrl.text.trim();
                      final pin = pinCtrl.text.trim();

                      if (name.isEmpty || phone.isEmpty || pin.isEmpty) {
                        ScaffoldMessenger.of(context).showSnackBar(
                          const SnackBar(content: Text('Semua field wajib diisi')),
                        );
                        return;
                      }

                      setDialogState(() => isSubmitting = true);
                      try {
                        final headers = SessionCache.instance.authHeaders;
                        await _dio.post(
                          '/users/cashier',
                          options: Options(headers: headers),
                          data: {'name': name, 'phone': phone, 'pin': pin},
                        );
                        if (ctx.mounted) Navigator.pop(ctx);
                        if (mounted) {
                          ScaffoldMessenger.of(context).showSnackBar(
                            const SnackBar(
                              content: Text('Kasir berhasil ditambahkan'),
                              backgroundColor: KasiraDS.success,
                            ),
                          );
                          _loadStaff();
                        }
                      } on DioException catch (e) {
                        setDialogState(() => isSubmitting = false);
                        final msg = e.response?.data['detail'] ?? 'Gagal menambah kasir';
                        if (mounted) {
                          ScaffoldMessenger.of(context).showSnackBar(
                            SnackBar(
                              content: Text(msg.toString()),
                              backgroundColor: KasiraDS.danger,
                            ),
                          );
                        }
                      }
                    },
              style: ElevatedButton.styleFrom(backgroundColor: KasiraDS.brandPrimary),
              child: isSubmitting
                  ? const SizedBox(
                      width: 18,
                      height: 18,
                      child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2),
                    )
                  : const Text('Simpan'),
            ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: KasiraDS.bgBase,
      appBar: AppBar(
        backgroundColor: KasiraDS.surfaceCard,
        title: const Text('Manajemen Kasir',
            style: TextStyle(color: KasiraDS.textStrong)),
        iconTheme: const IconThemeData(color: KasiraDS.textStrong),
        elevation: 0,
        actions: [
          IconButton(
            onPressed: _loadStaff,
            icon: const Icon(LucideIcons.refreshCw, color: KasiraDS.textMuted),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _showAddKasirDialog,
        icon: const Icon(LucideIcons.userPlus),
        label: const Text('Tambah Kasir'),
        backgroundColor: KasiraDS.brandPrimary,
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
              ? Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      const Icon(LucideIcons.alertCircle,
                          size: 40, color: KasiraDS.danger),
                      const SizedBox(height: 12),
                      Text(_error!, style: const TextStyle(color: KasiraDS.textMuted)),
                      const SizedBox(height: 16),
                      ElevatedButton(
                        onPressed: _loadStaff,
                        child: const Text('Coba Lagi'),
                      ),
                    ],
                  ),
                )
              : _staff.isEmpty
                  ? Center(
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Container(
                            padding: const EdgeInsets.all(20),
                            decoration: BoxDecoration(
                              color: KasiraDS.surfaceSunken,
                              shape: BoxShape.circle,
                            ),
                            child: const Icon(LucideIcons.users,
                                size: 40, color: KasiraDS.textMuted),
                          ),
                          const SizedBox(height: 16),
                          const Text('Belum ada kasir',
                              style: TextStyle(
                                  color: KasiraDS.textMuted,
                                  fontWeight: FontWeight.w500)),
                          const SizedBox(height: 4),
                          const Text('Tekan tombol + untuk menambahkan',
                              style: TextStyle(
                                  color: KasiraDS.textMuted, fontSize: 13)),
                        ],
                      ),
                    )
                  : ListView.builder(
                      padding: const EdgeInsets.fromLTRB(16, 16, 16, 100),
                      itemCount: _staff.length,
                      itemBuilder: (_, i) {
                        final kasir = _staff[i];
                        final name = kasir['full_name'] ?? '-';
                        final phone = kasir['phone'] ?? '-';
                        final isActive = kasir['is_active'] == true;
                        final userId = kasir['id']?.toString() ?? '';
                        final initial = name.isNotEmpty ? name[0].toUpperCase() : '?';

                        return Card(
                          margin: const EdgeInsets.only(bottom: 12),
                          shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(12)),
                          child: ListTile(
                            contentPadding: const EdgeInsets.symmetric(
                                horizontal: 16, vertical: 8),
                            leading: CircleAvatar(
                              backgroundColor: isActive
                                  ? KasiraDS.brandPrimary.withOpacity(0.12)
                                  : KasiraDS.surfaceSunken,
                              child: Text(
                                initial,
                                style: TextStyle(
                                  fontWeight: FontWeight.bold,
                                  color: isActive
                                      ? KasiraDS.brandPrimary
                                      : KasiraDS.textMuted,
                                ),
                              ),
                            ),
                            title: Text(name,
                                style: const TextStyle(fontWeight: FontWeight.bold)),
                            subtitle: Text(phone,
                                style: const TextStyle(
                                    color: KasiraDS.textMuted, fontSize: 13)),
                            trailing: Row(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                Container(
                                  padding: const EdgeInsets.symmetric(
                                      horizontal: 10, vertical: 4),
                                  decoration: BoxDecoration(
                                    color: isActive
                                        ? KasiraDS.success.withOpacity(0.1)
                                        : KasiraDS.danger.withOpacity(0.1),
                                    borderRadius: BorderRadius.circular(20),
                                  ),
                                  child: Text(
                                    isActive ? 'Aktif' : 'Nonaktif',
                                    style: TextStyle(
                                      fontSize: 12,
                                      fontWeight: FontWeight.bold,
                                      color: isActive
                                          ? KasiraDS.success
                                          : KasiraDS.danger,
                                    ),
                                  ),
                                ),
                                const SizedBox(width: 8),
                                Switch(
                                  value: isActive,
                                  activeColor: KasiraDS.brandPrimary,
                                  onChanged: (_) =>
                                      _toggleStatus(userId, isActive),
                                ),
                              ],
                            ),
                          ),
                        );
                      },
                    ),
    );
  }
}
