import 'package:flutter/material.dart';
import 'package:dio/dio.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';
import '../../../../core/config/app_config.dart';
import '../../../../core/services/session_cache.dart';
import '../../../../core/theme/kasira_ds.dart';
import '../../../auth/presentation/pages/login_page.dart';

class ProfilePage extends StatefulWidget {
  const ProfilePage({super.key});

  @override
  State<ProfilePage> createState() => _ProfilePageState();
}

class _ProfilePageState extends State<ProfilePage> {
  bool _isLoading = true;
  String _name = '-';
  String _phone = '-';
  String _role = 'Kasir';
  String _outlet = '-';
  String _initial = '?';

  @override
  void initState() {
    super.initState();
    _loadProfile();
  }

  Future<void> _loadProfile() async {
    try {
      final dio = Dio(BaseOptions(
        baseUrl: AppConfig.apiV1,
        connectTimeout: const Duration(seconds: 10),
        receiveTimeout: const Duration(seconds: 10),
      ));

      final response = await dio.get(
        '/users/me',
        options: Options(headers: SessionCache.instance.authHeaders),
      );

      final data = response.data['data'];
      if (mounted) {
        setState(() {
          _name = data['full_name'] ?? '-';
          _phone = data['phone'] ?? '-';
          _role = (data['is_superuser'] == true) ? 'Owner' : 'Kasir';
          _initial = _name.isNotEmpty ? _name[0].toUpperCase() : '?';
          _isLoading = false;
        });
      }

      // Fetch outlet name
      final outletId = SessionCache.instance.outletId;
      if (outletId != null && mounted) {
        try {
          final outletRes = await dio.get(
            '/outlets/$outletId',
            options: Options(headers: SessionCache.instance.authHeaders),
          );
          final outletData = outletRes.data['data'];
          if (mounted) {
            setState(() {
              _outlet = outletData['name'] ?? '-';
            });
          }
        } catch (_) {}
      }
    } catch (_) {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: KasiraDS.bgBase,
      appBar: AppBar(
        backgroundColor: KasiraDS.surfaceCard,
        title: const Text('Profil', style: TextStyle(color: KasiraDS.textStrong)),
        iconTheme: const IconThemeData(color: KasiraDS.textStrong),
        elevation: 0,
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : ListView(
              padding: const EdgeInsets.all(24),
              children: [
                // Profile Header
                Container(
                  padding: const EdgeInsets.all(32),
                  decoration: BoxDecoration(
                    gradient: LinearGradient(
                      colors: [KasiraDS.brandPrimary.withOpacity(0.05), KasiraDS.surfaceCard],
                      begin: Alignment.topCenter,
                      end: Alignment.bottomCenter,
                    ),
                    color: KasiraDS.surfaceCard,
                    borderRadius: BorderRadius.circular(16),
                    border: Border.all(color: KasiraDS.borderSubtle),
                  ),
                  child: Column(
                    children: [
                      CircleAvatar(
                        radius: 48,
                        backgroundColor: KasiraDS.brandPrimary.withOpacity(0.12),
                        child: Text(
                          _initial,
                          style: const TextStyle(
                            fontSize: 32,
                            fontWeight: FontWeight.bold,
                            color: KasiraDS.brandPrimary,
                          ),
                        ),
                      ),
                      const SizedBox(height: 16),
                      Text(_name, style: Theme.of(context).textTheme.headlineMedium),
                      const SizedBox(height: 8),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
                        decoration: BoxDecoration(
                          color: KasiraDS.info.withOpacity(0.1),
                          borderRadius: BorderRadius.circular(16),
                        ),
                        child: Text(
                          _role,
                          style: const TextStyle(color: KasiraDS.info, fontWeight: FontWeight.bold),
                        ),
                      ),
                    ],
                  ),
                ),

                const SizedBox(height: 32),

                const Padding(
                  padding: EdgeInsets.only(left: 8, bottom: 16),
                  child: Text(
                    'INFORMASI AKUN',
                    style: TextStyle(
                      color: KasiraDS.textMuted,
                      fontWeight: FontWeight.bold,
                      fontSize: 12,
                      letterSpacing: 1.2,
                    ),
                  ),
                ),

                Card(
                  margin: EdgeInsets.zero,
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                  child: Column(
                    children: [
                      _buildInfoRow(LucideIcons.user, 'Nama Lengkap', _name),
                      const Divider(height: 1),
                      _buildInfoRow(LucideIcons.phone, 'Nomor Telepon', _phone),
                      const Divider(height: 1),
                      _buildInfoRow(LucideIcons.store, 'Outlet', _outlet),
                    ],
                  ),
                ),

                const SizedBox(height: 32),

                const Padding(
                  padding: EdgeInsets.only(left: 8, bottom: 16),
                  child: Text(
                    'KEAMANAN',
                    style: TextStyle(
                      color: KasiraDS.textMuted,
                      fontWeight: FontWeight.bold,
                      fontSize: 12,
                      letterSpacing: 1.2,
                    ),
                  ),
                ),

                Card(
                  margin: EdgeInsets.zero,
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                  child: ListTile(
                    leading: const Icon(LucideIcons.lock, color: KasiraDS.textMuted),
                    title: const Text('Ubah PIN', style: TextStyle(fontWeight: FontWeight.bold)),
                    trailing: const Icon(LucideIcons.chevronRight, color: KasiraDS.textMuted),
                    onTap: () {},
                  ),
                ),

                const SizedBox(height: 48),

                SizedBox(
                  width: double.infinity,
                  height: 56,
                  child: OutlinedButton.icon(
                    onPressed: () => _showLogoutConfirmation(context),
                    icon: const Icon(LucideIcons.logOut, color: KasiraDS.danger),
                    label: const Text(
                      'Keluar Akun',
                      style: TextStyle(color: KasiraDS.danger, fontWeight: FontWeight.bold),
                    ),
                    style: OutlinedButton.styleFrom(
                      side: const BorderSide(color: KasiraDS.danger),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                    ),
                  ),
                ),
              ],
            ),
    );
  }

  Widget _buildInfoRow(IconData icon, String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
      child: Row(
        children: [
          Icon(icon, color: KasiraDS.textMuted, size: 20),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(label,
                    style: const TextStyle(color: KasiraDS.textMuted, fontSize: 12)),
                const SizedBox(height: 4),
                Text(value,
                    style:
                        const TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
              ],
            ),
          ),
        ],
      ),
    );
  }

  void _showLogoutConfirmation(BuildContext context) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Keluar Akun'),
        content: const Text('Apakah Anda yakin ingin keluar dari akun ini?'),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Batal', style: TextStyle(color: KasiraDS.textMuted)),
          ),
          ElevatedButton(
            onPressed: () {
              Navigator.pushAndRemoveUntil(
                context,
                MaterialPageRoute(builder: (context) => const LoginPage()),
                (route) => false,
              );
            },
            style: ElevatedButton.styleFrom(backgroundColor: KasiraDS.danger),
            child: const Text('Keluar'),
          ),
        ],
      ),
    );
  }
}
