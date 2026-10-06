import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../../core/api/api_client.dart';
import '../../../../core/services/session_cache.dart';

enum ManagedAction { cash, refunds, kitchen }

class ManagedActionsPage extends ConsumerStatefulWidget {
  const ManagedActionsPage({super.key, required this.action});
  final ManagedAction action;
  @override
  ConsumerState<ManagedActionsPage> createState() => _ManagedActionsPageState();
}

class _ManagedActionsPageState extends ConsumerState<ManagedActionsPage> {
  final _amount = TextEditingController(),
      _description = TextEditingController();
  List<Map<String, dynamic>> _rows = [];
  String? _shiftId, _error;
  bool _loading = true, _busy = false, _uncertain = false;
  String _cashType = 'expense';
  String get _title => switch (widget.action) {
        ManagedAction.cash => 'Catatan kas',
        ManagedAction.refunds => 'Pengajuan refund',
        ManagedAction.kitchen => 'Pesanan dapur',
      };
  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _amount.dispose();
    _description.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
      _rows = [];
    });
    try {
      final dio = ref.read(apiClientProvider), cache = SessionCache.instance;
      final query = {'outlet_id': cache.outletId};
      dynamic data;
      if (widget.action == ManagedAction.cash) {
        final current =
            await dio.get('/shifts/current', queryParameters: query);
        _shiftId = current.data['data']?['id']?.toString();
        if (_shiftId != null) {
          final response = await dio.get('/shifts/$_shiftId/activities',
              queryParameters: query);
          data = response.data['data']['activities'];
        }
      } else if (widget.action == ManagedAction.refunds) {
        data = (await dio.get('/payments/refunds', queryParameters: query))
            .data['data'];
      } else {
        data = (await dio.get('/orders/kitchen', queryParameters: query))
            .data['data']['active'];
      }
      if (!mounted) return;
      setState(() {
        _rows = (data as List? ?? [])
            .map((r) => Map<String, dynamic>.from(r as Map))
            .toList();
        _uncertain = false;
      });
    } catch (_) {
      if (mounted)
        setState(() =>
            _error = 'Data belum dapat dimuat. Periksa koneksi dan izin akun.');
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _write(String path, Map<String, dynamic> body) async {
    if (_busy || _uncertain) return;
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await ref.read(apiClientProvider).post(path,
          data: body,
          queryParameters: {'outlet_id': SessionCache.instance.outletId});
      _amount.clear();
      _description.clear();
      if (mounted) await _load();
    } on DioException catch (error) {
      if (!mounted) return;
      final uncertain =
          error.response == null || (error.response?.statusCode ?? 0) >= 500;
      final detail =
          error.response?.data is Map ? error.response?.data['detail'] : null;
      setState(() {
        _uncertain = uncertain;
        _error = uncertain
            ? 'Hasil belum pasti. Muat ulang dan periksa catatan sebelum membuat tindakan baru.'
            : detail is String
                ? detail
                : detail is Map
                    ? detail['message']?.toString()
                    : 'Tindakan ditolak. Muat ulang data.';
      });
    } catch (_) {
      if (mounted)
        setState(() {
          _uncertain = true;
          _error = 'Hasil belum pasti. Muat ulang dan periksa catatan.';
        });
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _refund(Map<String, dynamic> row, bool approve) async {
    final confirmed = await showDialog<bool>(
        context: context,
        builder: (context) => AlertDialog(
                title: Text(approve ? 'Setujui refund?' : 'Tolak refund?'),
                content: Text('Rp ${row['amount']}\n${row['reason']}'),
                actions: [
                  TextButton(
                      onPressed: () => Navigator.pop(context, false),
                      child: const Text('Kembali')),
                  FilledButton(
                      onPressed: () => Navigator.pop(context, true),
                      child: const Text('Konfirmasi'))
                ]));
    if (confirmed == true)
      await _write(
          '/payments/refunds/${row['id']}/${approve ? 'approve' : 'reject'}',
          {'row_version': row['row_version']});
  }

  @override
  Widget build(BuildContext context) => Scaffold(
      appBar: AppBar(title: Text(_title), actions: [
        IconButton(
            tooltip: 'Muat ulang',
            onPressed: _busy || _loading ? null : _load,
            icon: const Icon(Icons.refresh))
      ]),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : ListView(padding: const EdgeInsets.all(20), children: [
              if (_error != null)
                Padding(
                    padding: const EdgeInsets.only(bottom: 16),
                    child: Text(_error!, semanticsLabel: _error)),
              if (widget.action == ManagedAction.cash) ...[
                if (_shiftId == null)
                  const Text(
                      'Belum ada sesi kas terbuka. Minta petugas sesi kas membukanya.')
                else ...[
                  DropdownButtonFormField<String>(
                      initialValue: _cashType,
                      decoration:
                          const InputDecoration(labelText: 'Jenis catatan'),
                      items: const [
                        DropdownMenuItem(
                            value: 'expense', child: Text('Kas keluar')),
                        DropdownMenuItem(
                            value: 'income', child: Text('Kas masuk'))
                      ],
                      onChanged: _busy || _uncertain
                          ? null
                          : (value) => setState(() => _cashType = value!)),
                  TextField(
                      controller: _amount,
                      enabled: !_busy && !_uncertain,
                      keyboardType: TextInputType.number,
                      decoration:
                          const InputDecoration(labelText: 'Jumlah (Rp)')),
                  TextField(
                      controller: _description,
                      enabled: !_busy && !_uncertain,
                      maxLength: 500,
                      decoration:
                          const InputDecoration(labelText: 'Keperluan')),
                  FilledButton(
                      onPressed: _busy || _uncertain
                          ? null
                          : () {
                              final amount = double.tryParse(_amount.text);
                              if (amount == null ||
                                  !amount.isFinite ||
                                  amount <= 0 ||
                                  _description.text.trim().isEmpty) {
                                setState(() => _error =
                                    'Isi jumlah positif dan keperluan kas.');
                                return;
                              }
                              _write('/shifts/$_shiftId/activities', {
                                'activity_type': _cashType,
                                'amount': amount,
                                'description': _description.text.trim()
                              });
                            },
                      child: Text(_busy ? 'Menyimpan…' : 'Catat kas')),
                ],
              ],
              if (_rows.isEmpty)
                const Padding(
                    padding: EdgeInsets.symmetric(vertical: 24),
                    child: Text('Belum ada catatan.')),
              for (final row in _rows)
                Padding(
                    padding: const EdgeInsets.symmetric(vertical: 12),
                    child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          if (widget.action == ManagedAction.cash)
                            Text(
                                '${row['activity_type'] == 'income' ? 'Masuk' : 'Keluar'} · Rp ${row['amount']}\n${row['description']}'),
                          if (widget.action == ManagedAction.refunds) ...[
                            Text(
                                'Rp ${row['amount']} · ${row['status']}\n${row['reason']}'),
                            if (row['status'] == 'pending' &&
                                SessionCache.instance
                                    .allows('pos.refund.approve'))
                              Wrap(spacing: 12, children: [
                                OutlinedButton(
                                    onPressed: _busy || _uncertain
                                        ? null
                                        : () => _refund(row, false),
                                    child: const Text('Tolak')),
                                FilledButton(
                                    onPressed: _busy || _uncertain
                                        ? null
                                        : () => _refund(row, true),
                                    child: const Text('Setujui'))
                              ]),
                          ],
                          if (widget.action == ManagedAction.kitchen) ...[
                            Text(
                                'Pesanan #${row['display_number'] ?? row['order_number']} · ${row['kitchen_status']}'),
                            for (final item in row['items'] as List? ?? [])
                              Text(
                                  '${item['quantity']} × ${item['product_name']}${item['notes'] == null ? '' : '\n${item['notes']}'}'),
                            if (row['notes'] != null)
                              Text(row['notes'].toString()),
                            Wrap(spacing: 12, children: [
                              for (final status in [
                                'preparing',
                                'ready',
                                'done'
                              ])
                                OutlinedButton(
                                    onPressed: _busy ||
                                            _uncertain ||
                                            row['kitchen_status'] == status
                                        ? null
                                        : () => _write(
                                            '/orders/${row['id']}/kitchen-status',
                                            {'status': status}),
                                    child: Text(status == 'preparing'
                                        ? 'Kerjakan'
                                        : status == 'ready'
                                            ? 'Siap'
                                            : 'Selesai'))
                            ]),
                          ],
                          const Divider(),
                        ])),
            ]));
}
