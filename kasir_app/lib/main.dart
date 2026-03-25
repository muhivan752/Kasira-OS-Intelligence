import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'core/theme/app_theme.dart';
import 'features/auth/presentation/pages/login_page.dart';
import 'features/dashboard/presentation/pages/dashboard_page.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const ProviderScope(child: KasiraApp()));
}

class KasiraApp extends StatelessWidget {
  const KasiraApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Kasira POS',
      theme: AppTheme.lightTheme,
      debugShowCheckedModeBanner: false,
      // Temporarily set to DashboardPage for preview. Change back to LoginPage later.
      home: const LoginPage(),
    );
  }
}
