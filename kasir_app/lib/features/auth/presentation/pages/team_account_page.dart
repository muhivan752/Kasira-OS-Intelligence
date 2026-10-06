import 'package:dio/dio.dart';
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:go_router/go_router.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:uuid/uuid.dart';
import '../../../../core/config/app_config.dart';
import '../../../../core/services/session_cache.dart';
import '../../../../core/widgets/sefrekuensi_otp_card.dart';
import 'login_page.dart';

class TeamAccountPage extends ConsumerStatefulWidget {
  const TeamAccountPage({super.key, this.client});
  final Dio? client;
  @override
  ConsumerState<TeamAccountPage> createState() => _TeamAccountPageState();
}

class _TeamAccountPageState extends ConsumerState<TeamAccountPage> {
  Map<String, dynamic>? _setup, _pending;
  String? _error;
  bool _busy = false;
  String get _key =>
      'hris-punch:${SessionCache.instance.tenantId}:${SessionCache.instance.userId}';
  Dio get _dio =>
      widget.client ??
      Dio(BaseOptions(
          baseUrl: AppConfig.apiV1,
          connectTimeout: const Duration(seconds: 10),
          receiveTimeout: const Duration(seconds: 20),
          headers: {
            'Authorization': 'Bearer ${SessionCache.instance.accessToken}',
            'X-Tenant-ID': SessionCache.instance.tenantId,
          }));
  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      await _resume();
      final result = await _dio.get('/hris/setup');
      if (mounted) {
        setState(() {
          _setup = Map<String, dynamic>.from(result.data['data'] as Map);
          _error = null;
        });
      }
    } on DioException catch (error) {
      if (mounted) {
        setState(() => _error = otpErrorMessage(error.response?.data?['detail'],
            'Tim belum dapat dimuat. Periksa koneksi lalu coba lagi.'));
      }
    }
  }

  Future<void> _punch(String action) async {
    if (_busy) return;
    final setup = _setup;
    final source = setup == null
        ? null
        : setup[action == 'out' ? 'open_attendance' : 'self_employee'];
    final outlet = source is Map ? source['outlet_id'] : null;
    _pending ??= {
      'action': action,
      'outlet_id': outlet,
      'client_request_id': const Uuid().v4()
    };
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      // The request ID survives closing the app until the server confirms it.
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString(_key, jsonEncode(_pending));
      await _dio.post('/hris/punch', data: _pending);
      await prefs.remove(_key);
      _pending = null;
      await _load();
    } on DioException catch (error) {
      if (mounted) {
        setState(() => _error = otpErrorMessage(error.response?.data?['detail'],
            'Hasil pencatatan belum pasti. Periksa permintaan yang sama.'));
      }
    } catch (_) {
      if (mounted) {
        setState(() => _error = 'Pencatatan belum terkonfirmasi. Coba lagi.');
      }
    } finally {
      if (mounted) {
        setState(() => _busy = false);
      }
    }
  }

  Future<void> _resume() async {
    final saved = (await SharedPreferences.getInstance()).getString(_key);
    if (saved != null) {
      _pending = Map<String, dynamic>.from(jsonDecode(saved) as Map);
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
      appBar: AppBar(title: const Text('Tim dan akun saya')),
      body: Center(
          child: SingleChildScrollView(
              padding: const EdgeInsets.all(24),
              child: ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 480),
                  child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        if (_error != null)
                          Text(_error!,
                              style: TextStyle(
                                  color: Theme.of(context).colorScheme.error)),
                        if (_setup == null) ...[
                          const Text('Memuat tim…'),
                          TextButton(
                              onPressed: _load, child: const Text('Coba lagi'))
                        ] else ...[
                          Text(
                              (_setup!['self_employee'] as Map?)?['name']
                                      ?.toString() ??
                                  'Akun tim',
                              style: Theme.of(context).textTheme.headlineSmall),
                          const SizedBox(height: 16),
                          Text(_setup!['open_attendance'] != null
                              ? 'Kehadiran masuk sudah tercatat. Catat pulang ketika selesai bekerja.'
                              : 'Belum ada catatan masuk yang terbuka.'),
                          const SizedBox(height: 16),
                          if (_setup!['self_employee'] != null)
                            FilledButton(
                                onPressed: _busy
                                    ? null
                                    : () async {
                                        await _resume();
                                        await _punch(
                                            _setup!['open_attendance'] != null
                                                ? 'out'
                                                : 'in');
                                      },
                                child: Text(_busy
                                    ? 'Memproses…'
                                    : _pending != null
                                        ? 'Periksa pencatatan'
                                        : _setup!['open_attendance'] != null
                                            ? 'Catat pulang'
                                            : 'Catat masuk')),
                          TextButton(
                              onPressed: _busy
                                  ? null
                                  : () => launchUrl(
                                      Uri.parse('${AppConfig.baseUrl}/login'),
                                      mode: LaunchMode.externalApplication),
                              child: const Text(
                                  'Buka web untuk jadwal dan pengaturan tim')),
                        ],
                        TextButton(
                            onPressed: _busy
                                ? null
                                : () async {
                                    try {
                                      await _dio.delete('/auth/logout');
                                    } on DioException catch (error) {
                                      if (![
                                        401,
                                        403
                                      ].contains(error.response?.statusCode)) {
                                        if (mounted) {
                                          setState(() => _error =
                                              'Logout belum terkonfirmasi. Coba lagi.');
                                        }
                                        return;
                                      }
                                    }
                                    await SessionCache.instance.clear();
                                    ref
                                        .read(authProvider.notifier)
                                        .usePasswordInstead();
                                    if (context.mounted) context.go('/login');
                                  },
                            child: const Text('Keluar dari akun')),
                      ])))));
}
