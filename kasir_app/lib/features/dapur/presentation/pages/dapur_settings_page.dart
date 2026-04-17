import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../../../../core/services/session_cache.dart';
import 'package:lucide_icons/lucide_icons.dart';
import '../../../../core/theme/app_colors.dart';

class DapurSettingsPage extends StatefulWidget {
  const DapurSettingsPage({super.key});

  @override
  State<DapurSettingsPage> createState() => _DapurSettingsPageState();
}

class _DapurSettingsPageState extends State<DapurSettingsPage> {
  bool _soundEnabled = true;
  int _pollInterval = 8; // seconds
  Future<void> _logout() async {
    final confirm = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: const Color(0xFF1E1E30),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        title: const Text('Keluar?', style: TextStyle(color: Colors.white)),
        content: const Text(
          'Apakah kamu yakin ingin keluar dari mode dapur?',
          style: TextStyle(color: Colors.white60),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('Batal', style: TextStyle(color: Colors.white38)),
          ),
          ElevatedButton(
            onPressed: () => Navigator.pop(ctx, true),
            style: ElevatedButton.styleFrom(
                backgroundColor: AppColors.error),
            child: const Text('Keluar'),
          ),
        ],
      ),
    );

    if (confirm == true && mounted) {
      await SessionCache.instance.clear();
      if (mounted) context.go('/dapur/login');
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0F0F1A),
      appBar: AppBar(
        backgroundColor: const Color(0xFF1A1A2E),
        elevation: 0,
        leading: IconButton(
          icon: const Icon(LucideIcons.arrowLeft, color: Colors.white70),
          onPressed: () => context.pop(),
        ),
        title: const Text(
          'Pengaturan Dapur',
          style: TextStyle(
              color: Colors.white, fontWeight: FontWeight.bold, fontSize: 16),
        ),
      ),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          // Sound
          _SettingsSection(
            title: 'NOTIFIKASI',
            children: [
              _SwitchTile(
                icon: LucideIcons.volume2,
                label: 'Suara pesanan baru',
                subtitle: 'Berbunyi saat pesanan baru masuk',
                value: _soundEnabled,
                onChanged: (v) => setState(() => _soundEnabled = v),
              ),
            ],
          ),

          const SizedBox(height: 20),

          // Polling interval
          _SettingsSection(
            title: 'KONEKSI',
            children: [
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        const Icon(LucideIcons.refreshCw,
                            size: 18, color: Colors.white60),
                        const SizedBox(width: 12),
                        const Expanded(
                          child: Text(
                            'Interval refresh',
                            style: TextStyle(color: Colors.white, fontSize: 14),
                          ),
                        ),
                        Text(
                          '$_pollInterval detik',
                          style: const TextStyle(
                              color: AppColors.warning,
                              fontWeight: FontWeight.bold),
                        ),
                      ],
                    ),
                    Slider(
                      value: _pollInterval.toDouble(),
                      min: 5,
                      max: 30,
                      divisions: 5,
                      activeColor: AppColors.warning,
                      inactiveColor: Colors.white12,
                      label: '$_pollInterval detik',
                      onChanged: (v) =>
                          setState(() => _pollInterval = v.toInt()),
                    ),
                    Text(
                      'Lebih kecil = lebih real-time, lebih boros baterai',
                      style: TextStyle(
                          color: Colors.white.withOpacity(0.3), fontSize: 11),
                    ),
                  ],
                ),
              ),
            ],
          ),

          const SizedBox(height: 20),

          // Server
          _SettingsSection(
            title: 'SERVER',
            children: [
              _ActionTile(
                icon: LucideIcons.server,
                label: 'Ubah URL Server',
                onTap: () => context.push('/setup'),
              ),
            ],
          ),

          const SizedBox(height: 20),

          // Logout
          _SettingsSection(
            title: 'AKUN',
            children: [
              _ActionTile(
                icon: LucideIcons.logOut,
                label: 'Keluar',
                color: AppColors.error,
                onTap: _logout,
              ),
            ],
          ),

          const SizedBox(height: 40),

          // Version info
          Center(
            child: Text(
              'Kasira Dapur v1.0.0',
              style: TextStyle(
                color: Colors.white.withOpacity(0.2),
                fontSize: 12,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _SettingsSection extends StatelessWidget {
  final String title;
  final List<Widget> children;

  const _SettingsSection({required this.title, required this.children});

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.only(bottom: 8, left: 4),
          child: Text(
            title,
            style: const TextStyle(
              color: Colors.white38,
              fontSize: 11,
              fontWeight: FontWeight.bold,
              letterSpacing: 1,
            ),
          ),
        ),
        Container(
          decoration: BoxDecoration(
            color: Colors.white.withOpacity(0.04),
            borderRadius: BorderRadius.circular(14),
            border: Border.all(color: Colors.white.withOpacity(0.08)),
          ),
          child: Column(children: children),
        ),
      ],
    );
  }
}

class _SwitchTile extends StatelessWidget {
  final IconData icon;
  final String label;
  final String? subtitle;
  final bool value;
  final ValueChanged<bool> onChanged;

  const _SwitchTile({
    required this.icon,
    required this.label,
    this.subtitle,
    required this.value,
    required this.onChanged,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      child: Row(
        children: [
          Icon(icon, size: 18, color: Colors.white60),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(label,
                    style:
                        const TextStyle(color: Colors.white, fontSize: 14)),
                if (subtitle != null)
                  Text(subtitle!,
                      style: const TextStyle(
                          color: Colors.white38, fontSize: 11)),
              ],
            ),
          ),
          Switch.adaptive(
            value: value,
            onChanged: onChanged,
            activeColor: AppColors.warning,
          ),
        ],
      ),
    );
  }
}

class _ActionTile extends StatelessWidget {
  final IconData icon;
  final String label;
  final Color? color;
  final VoidCallback onTap;

  const _ActionTile({
    required this.icon,
    required this.label,
    this.color,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final c = color ?? Colors.white;
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(14),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
        child: Row(
          children: [
            Icon(icon, size: 18, color: c.withOpacity(0.7)),
            const SizedBox(width: 12),
            Expanded(
              child: Text(label,
                  style: TextStyle(
                      color: c,
                      fontSize: 14,
                      fontWeight: FontWeight.w500)),
            ),
            Icon(LucideIcons.chevronRight,
                size: 16, color: Colors.white.withOpacity(0.2)),
          ],
        ),
      ),
    );
  }
}
