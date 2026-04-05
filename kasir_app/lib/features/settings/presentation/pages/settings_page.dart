import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:lucide_icons/lucide_icons.dart';
import '../../../../core/config/app_config.dart';
import '../../../../core/theme/app_colors.dart';
import 'printer_settings_page.dart';
import 'sync_settings_page.dart';
import 'profile_page.dart';
import 'staff_page.dart';

class SettingsPage extends StatelessWidget {
  const SettingsPage({super.key});

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
            width: double.infinity,
            child: Text('Pengaturan', style: Theme.of(context).textTheme.headlineMedium),
          ),
          
          // Settings List
          Expanded(
            child: ListView(
              padding: const EdgeInsets.all(24),
              children: [
                _buildSectionTitle('Perangkat & Hardware'),
                _buildSettingTile(
                  icon: LucideIcons.printer,
                  title: 'Printer Bluetooth',
                  subtitle: 'Epson TM-T82X (Terhubung)',
                  onTap: () {
                    Navigator.push(
                      context,
                      MaterialPageRoute(builder: (context) => const PrinterSettingsPage()),
                    );
                  },
                ),
                _buildSettingTile(
                  icon: LucideIcons.monitorSpeaker,
                  title: 'Layar Pelanggan (Customer Display)',
                  subtitle: 'Tidak Terhubung',
                  onTap: () {},
                ),
                
                const SizedBox(height: 32),
                _buildSectionTitle('Sistem & Data'),
                _buildSettingTile(
                  icon: LucideIcons.refreshCw,
                  title: 'Sinkronisasi Data Manual',
                  subtitle: 'Terakhir sinkron: 10 menit yang lalu',
                  onTap: () {
                    Navigator.push(
                      context,
                      MaterialPageRoute(builder: (context) => const SyncSettingsPage()),
                    );
                  },
                ),
                _buildSettingTile(
                  icon: LucideIcons.database,
                  title: 'Hapus Cache Aplikasi',
                  subtitle: 'Kosongkan memori sementara',
                  onTap: () {},
                ),
                
                const SizedBox(height: 32),
                _buildSectionTitle('Server & Koneksi'),
                _buildSettingTile(
                  icon: LucideIcons.server,
                  title: 'URL Server',
                  subtitle: AppConfig.baseUrl,
                  onTap: () => context.push('/setup'),
                ),

                const SizedBox(height: 32),
                _buildSectionTitle('Tim & Akun'),
                _buildSettingTile(
                  icon: LucideIcons.users,
                  title: 'Manajemen Kasir',
                  subtitle: 'Tambah & kelola akun kasir',
                  onTap: () {
                    Navigator.push(
                      context,
                      MaterialPageRoute(builder: (context) => const StaffPage()),
                    );
                  },
                ),
                _buildSettingTile(
                  icon: LucideIcons.user,
                  title: 'Profil Saya',
                  subtitle: 'Lihat info akun',
                  onTap: () {
                    Navigator.push(
                      context,
                      MaterialPageRoute(builder: (context) => const ProfilePage()),
                    );
                  },
                ),
                _buildSettingTile(
                  icon: LucideIcons.helpCircle,
                  title: 'Pusat Bantuan',
                  subtitle: 'Hubungi tim support Kasira',
                  onTap: () {},
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildSectionTitle(String title) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 16, left: 8),
      child: Text(
        title.toUpperCase(),
        style: const TextStyle(
          color: AppColors.textSecondary,
          fontWeight: FontWeight.bold,
          fontSize: 12,
          letterSpacing: 1.2,
        ),
      ),
    );
  }

  Widget _buildSettingTile({
    required IconData icon,
    required String title,
    required String subtitle,
    required VoidCallback onTap,
  }) {
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: ListTile(
        contentPadding: const EdgeInsets.symmetric(horizontal: 20, vertical: 8),
        leading: Container(
          padding: const EdgeInsets.all(10),
          decoration: BoxDecoration(
            color: AppColors.surfaceVariant,
            borderRadius: BorderRadius.circular(8),
          ),
          child: Icon(icon, color: AppColors.textSecondary),
        ),
        title: Text(title, style: const TextStyle(fontWeight: FontWeight.bold)),
        subtitle: Text(subtitle, style: const TextStyle(color: AppColors.textSecondary)),
        trailing: const Icon(LucideIcons.chevronRight, color: AppColors.textTertiary),
        onTap: onTap,
      ),
    );
  }
}
