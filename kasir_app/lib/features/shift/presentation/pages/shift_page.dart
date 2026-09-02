import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:intl/intl.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';
import 'package:dio/dio.dart';
import 'package:go_router/go_router.dart';
import '../../../../core/config/app_config.dart';
import '../../../../core/services/session_cache.dart';
import '../../../../core/theme/kasira_ds.dart';
import 'cash_drawer_history_page.dart';

class ShiftPage extends StatefulWidget {
  const ShiftPage({super.key});

  @override
  State<ShiftPage> createState() => _ShiftPageState();
}

class _ShiftPageState extends State<ShiftPage> {
  final _cashController = TextEditingController();
  final _currency = NumberFormat.currency(locale: 'id_ID', symbol: 'Rp ', decimalDigits: 0);

  Map<String, dynamic>? _shift;
  List<Map<String, dynamic>> _uncounted = const [];
  bool _isLoading = true;
  bool _isClosing = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadShift();
  }

  @override
  void dispose() {
    _cashController.dispose();
    super.dispose();
  }

  Map<String, String> get _headers => SessionCache.instance.authHeaders;

  Dio get _dio => Dio(BaseOptions(
        baseUrl: AppConfig.apiV1,
        connectTimeout: const Duration(seconds: 15),
        receiveTimeout: const Duration(seconds: 15),
      ));

  Future<void> _loadShift() async {
    setState(() { _isLoading = true; _error = null; });
    try {
      final outletId = SessionCache.instance.outletId;

      final results = await Future.wait([
        _dio.get('/shifts/current', queryParameters: {'outlet_id': outletId}, options: Options(headers: _headers)),
        _dio.get('/shifts/uncounted', queryParameters: {'outlet_id': outletId}, options: Options(headers: _headers)),
      ]);
      final unc = (results[1].data['data'] as List? ?? const [])
          .whereType<Map>()
          .map((e) => Map<String, dynamic>.from(e))
          .toList();
      setState(() { _shift = results[0].data['data']; _uncounted = unc; _isLoading = false; });
    } catch (_) {
      setState(() { _error = 'Gagal memuat data shift'; _isLoading = false; });
    }
  }

  /// "Hitung nanti": sesi ini dijeda, sesi baru langsung jalan. Laci lama
  /// bisa dihitung kapan saja lewat daftar "belum dihitung".
  Future<void> _pauseShift() async {
    setState(() => _isClosing = true);
    try {
      final shiftId = _shift!['id'];
      final res = await _dio.post('/shifts/$shiftId/pause', options: Options(headers: _headers));
      final current = res.data['data']?['current'];
      // Ketat: nggak ada sesi lanjutan (serah terima eksplisit) → null.
      final newId = current?['id']?.toString();
      await SessionCache.instance.setShiftSessionId(newId);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
        content: Text(res.data['message']?.toString() ?? 'Sesi dijeda, sesi baru sudah berjalan'),
        behavior: SnackBarBehavior.floating,
      ));
      context.go('/dashboard');
    } on DioException catch (e) {
      final msg = e.response?.data?['detail'] ?? 'Gagal menjeda sesi';
      if (mounted) {
        setState(() => _isClosing = false);
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(msg.toString()), backgroundColor: KasiraDS.danger, behavior: SnackBarBehavior.floating));
      }
    } catch (_) {
      if (mounted) setState(() => _isClosing = false);
    }
  }

  /// Hitung laci dari sesi yang dijeda atau ditutup sistem di 04.00. Satu
  /// sheet kecil: ketik uang yang ada, kirim ke /close sesi itu.
  Future<void> _countUncounted(Map<String, dynamic> sh) async {
    final ctrl = TextEditingController();
    final ok = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) => Padding(
        padding: EdgeInsets.only(bottom: MediaQuery.of(ctx).viewInsets.bottom),
        child: Container(
          padding: const EdgeInsets.fromLTRB(20, 16, 20, 28),
          decoration: const BoxDecoration(
            color: KasiraDS.surfaceCard,
            borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('Hitung kas sesi ${_fmtSesi(sh)}', style: KasiraDS.display(size: 20)),
              const SizedBox(height: 6),
              Text(
                sh['status'] == 'paused'
                    ? 'Sesi ini dijeda. Hitung uang di laci yang ditinggalkan, lalu masukkan jumlahnya.'
                    : 'Sesi ini ditutup sistem pukul 04.00. Masukkan uang yang ada waktu Anda menghitungnya.',
                style: KasiraDS.sans(size: 13, color: KasiraDS.textMuted),
              ),
              const SizedBox(height: 16),
              TextField(
                controller: ctrl,
                autofocus: true,
                keyboardType: TextInputType.number,
                inputFormatters: [FilteringTextInputFormatter.digitsOnly],
                decoration: InputDecoration(
                  labelText: 'Uang di laci',
                  prefixText: 'Rp ',
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                ),
              ),
              const SizedBox(height: 16),
              SizedBox(
                width: double.infinity,
                height: 52,
                child: ElevatedButton(
                  onPressed: () => Navigator.pop(ctx, true),
                  child: const Text('Catat hitungan', style: TextStyle(fontWeight: FontWeight.bold)),
                ),
              ),
            ],
          ),
        ),
      ),
    );
    if (ok != true) return;
    final amount = double.tryParse(ctrl.text.trim());
    if (amount == null) return;
    try {
      final res = await _dio.post('/shifts/${sh['id']}/close',
          options: Options(headers: _headers), data: {'ending_cash': amount});
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
        content: Text(res.data['message']?.toString() ?? 'Hitungan tercatat'),
        behavior: SnackBarBehavior.floating,
      ));
      _loadShift();
    } on DioException catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
        content: Text((e.response?.data?['detail'] ?? 'Gagal mencatat hitungan').toString()),
        backgroundColor: KasiraDS.danger, behavior: SnackBarBehavior.floating,
      ));
    }
  }

  String _fmtSesi(Map<String, dynamic> sh) {
    final t = DateTime.tryParse(sh['start_time']?.toString() ?? '')?.toLocal();
    if (t == null) return '';
    return '${t.day}/${t.month} ${t.hour.toString().padLeft(2, '0')}.${t.minute.toString().padLeft(2, '0')}';
  }

  Widget _uncountedList() {
    if (_uncounted.isEmpty) return const SizedBox.shrink();
    return Container(
      margin: const EdgeInsets.only(bottom: 16),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: KasiraDS.warning.withOpacity(0.10),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: KasiraDS.warning.withOpacity(0.45)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('Kas belum dihitung (${_uncounted.length})',
              style: KasiraDS.sans(size: 14, weight: FontWeight.w700, color: KasiraDS.textStrong)),
          const SizedBox(height: 4),
          Text('Sesi yang dijeda atau ditutup sistem pukul 04.00. Transaksi tetap jalan, ini hanya pengingat.',
              style: KasiraDS.sans(size: 12, color: KasiraDS.textMuted)),
          const SizedBox(height: 10),
          ..._uncounted.map((sh) => Padding(
                padding: const EdgeInsets.only(bottom: 8),
                child: Row(
                  children: [
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text('Sesi ${_fmtSesi(sh)}${sh['opened_by_name'] != null ? ' · ${sh['opened_by_name']}' : ''}',
                              style: KasiraDS.sans(size: 13, weight: FontWeight.w600, color: KasiraDS.textStrong)),
                          Text(sh['status'] == 'paused' ? 'Dijeda, belum dihitung' : 'Ditutup sistem 04.00, belum dihitung',
                              style: KasiraDS.sans(size: 11.5, color: KasiraDS.textMuted)),
                        ],
                      ),
                    ),
                    TextButton(onPressed: () => _countUncounted(sh), child: const Text('Hitung')),
                  ],
                ),
              )),
        ],
      ),
    );
  }

  Future<void> _closeShift() async {
    final actualCash = double.tryParse(_cashController.text.trim()) ?? 0;
    if (actualCash <= 0) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Masukkan jumlah uang aktual di laci'), backgroundColor: KasiraDS.danger, behavior: SnackBarBehavior.floating),
      );
      return;
    }

    setState(() => _isClosing = true);
    try {
      final shiftId = _shift!['id'];
      final closeRes = await _dio.post(
        '/shifts/$shiftId/close',
        options: Options(headers: _headers),
        data: {'ending_cash': actualCash},
      );

      await SessionCache.instance.setShiftSessionId(null);

      // Show variance result before navigating
      if (mounted) {
        final data = closeRes.data['data'];
        final variance = (data?['variance'] as num?)?.toDouble() ?? 0;
        // Blind close: server nggak ngirim status selisih → tampil netral.
        final varianceStatus = data?['variance_status'] as String? ?? 'balanced';
        final message = closeRes.data['message'] as String? ?? 'Shift ditutup';

        await showDialog(
          context: context,
          barrierDismissible: false,
          builder: (ctx) => AlertDialog(
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
            icon: Icon(
              varianceStatus == 'balanced' ? LucideIcons.checkCircle2 : LucideIcons.alertTriangle,
              color: varianceStatus == 'balanced' ? KasiraDS.success : KasiraDS.warning,
              size: 48,
            ),
            title: Text(varianceStatus == 'balanced' ? 'Shift Ditutup' : 'Shift Ditutup, Ada Selisih'),
            content: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(message, textAlign: TextAlign.center, style: const TextStyle(color: KasiraDS.textMuted)),
                if (varianceStatus != 'balanced') ...[
                  const SizedBox(height: 16),
                  Container(
                    padding: const EdgeInsets.all(16),
                    decoration: BoxDecoration(
                      color: (varianceStatus == 'surplus' ? KasiraDS.success : KasiraDS.danger).withOpacity(0.1),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(
                          varianceStatus == 'surplus' ? LucideIcons.trendingUp : LucideIcons.trendingDown,
                          color: varianceStatus == 'surplus' ? KasiraDS.success : KasiraDS.danger,
                        ),
                        const SizedBox(width: 8),
                        Text(
                          '${varianceStatus == 'surplus' ? '+' : '-'} ${_currency.format(variance.abs())}',
                          style: TextStyle(
                            fontSize: 20,
                            fontWeight: FontWeight.bold,
                            color: varianceStatus == 'surplus' ? KasiraDS.success : KasiraDS.danger,
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ],
            ),
            actions: [
              ElevatedButton(
                onPressed: () {
                  Navigator.pop(ctx);
                  // Shift otomatis: sesudah dihitung nggak perlu "buka" lagi,
                  // sesi berikutnya terbuka sendiri di transaksi pertama.
                  context.go('/dashboard');
                },
                child: const Text('OK'),
              ),
            ],
          ),
        );
        return; // already navigated in dialog
      }
    } on DioException catch (e) {
      final msg = e.response?.data?['detail'] ?? 'Gagal tutup shift';
      if (mounted) {
        setState(() => _isClosing = false);
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(msg.toString()), backgroundColor: KasiraDS.danger, behavior: SnackBarBehavior.floating),
        );
      }
    } catch (_) {
      if (mounted) setState(() => _isClosing = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: KasiraDS.bgBase,
      appBar: AppBar(
        backgroundColor: KasiraDS.surfaceCard,
        title: const Text('Manajemen Shift', style: TextStyle(color: KasiraDS.textStrong)),
        iconTheme: const IconThemeData(color: KasiraDS.textStrong),
        elevation: 0,
        actions: [
          TextButton.icon(
            onPressed: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const CashDrawerHistoryPage())),
            icon: const Icon(LucideIcons.history, color: KasiraDS.brandPrimary),
            label: const Text('Riwayat Kas', style: TextStyle(color: KasiraDS.brandPrimary)),
          ),
          const SizedBox(width: 16),
        ],
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
              ? _buildError()
              : _buildContent(),
    );
  }

  Widget _buildError() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Text(_error!, style: const TextStyle(color: KasiraDS.textMuted)),
          const SizedBox(height: 16),
          ElevatedButton.icon(onPressed: _loadShift, icon: const Icon(LucideIcons.refreshCw, size: 16), label: const Text('Coba Lagi')),
        ],
      ),
    );
  }

  Widget _buildContent2Empty() => SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: Column(
          children: [
            _uncountedList(),
            const SizedBox(height: 24),
            Text(
              SessionCache.instance.shiftMode == 'ketat'
                  ? 'Belum ada sesi berjalan. Buka kasir dan isi modal awal untuk mulai.'
                  : 'Belum ada sesi berjalan. Sesi terbuka sendiri di transaksi pertama.',
              textAlign: TextAlign.center, style: const TextStyle(color: KasiraDS.textMuted)),
            if (SessionCache.instance.shiftMode == 'ketat') ...[
              const SizedBox(height: 16),
              ElevatedButton(onPressed: () => context.go('/shift/open'), child: const Text('Buka kasir')),
            ],
          ],
        ),
      );

  Widget _buildContent() {
    if (_shift == null) {
      return SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: Column(
          children: [
            _uncountedList(),
            const SizedBox(height: 24),
            const Text('Belum ada sesi berjalan. Sesi terbuka sendiri di transaksi pertama.',
                textAlign: TextAlign.center, style: TextStyle(color: KasiraDS.textMuted)),
          ],
        ),
      );
    }
    // Blind close (profil Standar/Ketat, bukan pemilik): server sudah
    // mengosongkan angka harapan; di sini baris sistemnya nggak dirender
    // supaya hitungannya nggak bisa dicontek.
    final blind = _shift!['blind_close'] == true;
    // /current tanpa sesi sekarang balik {status: null, shift_mode} — bukan sesi.
    if (_shift!['id'] == null) {
      return _buildContent2Empty();
    }

    final startingCash = (_shift!['starting_cash'] as num?)?.toDouble() ?? 0;
    final expectedCash = (_shift!['expected_ending_cash'] as num?)?.toDouble();
    final activities = (_shift!['activities'] as List?) ?? [];
    final totalCashSales = (_shift!['total_cash_sales'] as num?)?.toDouble() ?? 0;
    final totalQrisSales = (_shift!['total_qris_sales'] as num?)?.toDouble() ?? 0;

    double cashIn = 0, cashOut = 0;
    for (final a in activities) {
      final amount = (a['amount'] as num?)?.toDouble() ?? 0;
      if (a['activity_type'] == 'income') cashIn += amount;
      if (a['activity_type'] == 'expense') cashOut += amount;
    }

    final systemTotal = expectedCash ?? (startingCash + cashIn - cashOut + totalCashSales);

    return Center(
      child: SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: Column(children: [
          _uncountedList(),
          _closeCard(startingCash, totalCashSales, totalQrisSales, cashIn, cashOut, systemTotal, blind),
        ]),
      ),
    );
  }

  Widget _closeCard(double startingCash, double totalCashSales, double totalQrisSales,
      double cashIn, double cashOut, double systemTotal, bool blind) {
    return Center(
      child: SingleChildScrollView(
        padding: EdgeInsets.zero,
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 500),
          child: Container(
          padding: const EdgeInsets.all(32),
          decoration: BoxDecoration(
            color: KasiraDS.surfaceCard,
            borderRadius: BorderRadius.circular(24),
            boxShadow: [BoxShadow(color: Colors.black.withOpacity(0.05), blurRadius: 20, offset: const Offset(0, 10))],
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(LucideIcons.clock, size: 48, color: KasiraDS.brandPrimary),
              const SizedBox(height: 24),
              Text('Hitung Kas & Tutup Sesi', style: Theme.of(context).textTheme.headlineMedium),
              const SizedBox(height: 8),
              const Text('Hitung uang di laci, lalu masukkan jumlahnya. Belum sempat? Jeda dulu, penjualan tetap jalan.', textAlign: TextAlign.center, style: TextStyle(color: KasiraDS.textMuted)),
              const SizedBox(height: 32),
              if (_shift!['locked_to_name'] != null) ...[
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(12),
                  margin: const EdgeInsets.only(bottom: 16),
                  decoration: BoxDecoration(color: KasiraDS.warning.withOpacity(0.12), borderRadius: BorderRadius.circular(12)),
                  child: Text('Laci dipegang ${_shift!['locked_to_name']} (mode Ketat)',
                      style: KasiraDS.sans(size: 12.5, weight: FontWeight.w600, color: KasiraDS.textStrong)),
                ),
              ],
              if ((_shift!['review'] as List?)?.isNotEmpty == true) ...[
                Align(
                  alignment: Alignment.centerLeft,
                  child: Text('Rekap per kasir', style: KasiraDS.sans(size: 12, weight: FontWeight.w700, color: KasiraDS.textMuted)),
                ),
                const SizedBox(height: 6),
                ...((_shift!['review'] as List).whereType<Map>().map((r) => Padding(
                      padding: const EdgeInsets.only(bottom: 6),
                      child: Row(
                        children: [
                          Expanded(child: Text('${r['name']} · ${r['orders']} pesanan', style: KasiraDS.sans(size: 13, color: KasiraDS.textStrong))),
                          if (r['total'] != null)
                            Text(_currency.format((r['total'] as num).toDouble()), style: KasiraDS.sans(size: 13, weight: FontWeight.w600, color: KasiraDS.textStrong)),
                        ],
                      ),
                    ))),
                const Divider(height: 24),
              ],
              if (!blind) ...[
                _buildRow('Uang Modal Awal', _currency.format(startingCash)),
                const SizedBox(height: 12),
                _buildRow('Penjualan Cash', _currency.format(totalCashSales)),
                const SizedBox(height: 12),
                _buildRow('Penjualan QRIS', _currency.format(totalQrisSales)),
                const SizedBox(height: 12),
                _buildRow('Penerimaan Kas Lainnya', _currency.format(cashIn)),
                const SizedBox(height: 12),
                _buildRow('Pengeluaran Kas', _currency.format(cashOut), isNegative: true),
                const Divider(height: 32),
                _buildRow('Total Uang di Laci (Sistem)', _currency.format(systemTotal), isBold: true),
              ] else
                Container(
                  padding: const EdgeInsets.all(14),
                  decoration: BoxDecoration(color: KasiraDS.surfaceSunken, borderRadius: BorderRadius.circular(12)),
                  child: Text(
                    'Hitung uang di laci apa adanya. Angka sistem tidak ditampilkan; pemilik yang akan mencocokkannya.',
                    style: KasiraDS.sans(size: 13, color: KasiraDS.textMuted),
                  ),
                ),
              const SizedBox(height: 32),
              TextField(
                controller: _cashController,
                keyboardType: TextInputType.number,
                inputFormatters: [FilteringTextInputFormatter.digitsOnly],
                decoration: InputDecoration(
                  labelText: 'Uang Aktual di Laci',
                  prefixText: 'Rp ',
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                  focusedBorder: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(12),
                    borderSide: const BorderSide(color: KasiraDS.brandPrimary, width: 2),
                  ),
                ),
              ),
              const SizedBox(height: 32),
              SizedBox(
                width: double.infinity,
                height: 56,
                child: ElevatedButton(
                  onPressed: _isClosing ? null : _closeShift,
                  style: ElevatedButton.styleFrom(backgroundColor: KasiraDS.danger),
                  child: _isClosing
                      ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
                      : const Text('HITUNG & TUTUP SESI', style: TextStyle(fontWeight: FontWeight.bold)),
                ),
              ),
              const SizedBox(height: 12),
              SizedBox(
                width: double.infinity,
                height: 50,
                child: OutlinedButton.icon(
                  onPressed: _isClosing ? null : _pauseShift,
                  icon: const Icon(LucideIcons.pauseCircle, size: 18),
                  label: const Text('Hitung nanti, jeda sesi ini'),
                  style: OutlinedButton.styleFrom(
                    foregroundColor: KasiraDS.textStrong,
                    side: const BorderSide(color: KasiraDS.borderDefault),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
      ),
    );
  }

  Widget _buildRow(String label, String value, {bool isNegative = false, bool isBold = false}) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(label, style: TextStyle(color: isBold ? KasiraDS.textStrong : KasiraDS.textMuted, fontWeight: isBold ? FontWeight.bold : FontWeight.normal, fontSize: isBold ? 18 : 14)),
        Text(value, style: TextStyle(color: isNegative ? KasiraDS.danger : KasiraDS.textStrong, fontWeight: isBold ? FontWeight.bold : FontWeight.w600, fontSize: isBold ? 18 : 14)),
      ],
    );
  }
}
