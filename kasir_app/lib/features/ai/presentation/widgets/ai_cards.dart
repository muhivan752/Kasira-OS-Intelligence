import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';
import 'package:uuid/uuid.dart';

import '../../../../core/api/api_client.dart';
import '../../../../core/services/session_cache.dart';
import '../../../../core/theme/kasira_ds.dart';

/// Kartu Simpan dari alat Selaris AI di app (1.6.37), sama dengan kartu web
/// (components/dashboard/recipe-draft-card.tsx dan bahan-cards.tsx).
///
/// Angka di kartu dihitung backend. Tombol Simpan memanggil endpoint yang sama
/// dengan dashboard (approve HPP, PUT /ingredients, POST /purchases,
/// POST /ingredients/{id}/restock, PUT /products), jadi izin, audit, dan HPP
/// tetap diputuskan di server. Kartu ini tidak menghitung ulang apa pun kecuali
/// margin pratinjau saat harga jual diedit.
///
/// Path ditulis persis seperti rute FastAPI (koleksi pakai garis miring, sumber
/// daya tanpa): Dio tidak mengikuti redirect 307 untuk POST/PUT.
class AiCard extends StatelessWidget {
  final Map<String, dynamic> card;
  const AiCard({super.key, required this.card});

  @override
  Widget build(BuildContext context) {
    switch (card['type']) {
      case 'recipe_draft':
        return _RecipeCard(card: card);
      case 'ingredient_price':
        return _PriceCard(card: card);
      case 'stock_in':
        return _StockCard(card: card);
      case 'sell_price':
        return _SellCard(card: card);
    }
    return const SizedBox.shrink();
  }
}

final _rpFmt = NumberFormat.currency(locale: 'id_ID', symbol: 'Rp ', decimalDigits: 0);
String _rp(dynamic v) => _rpFmt.format((v as num?)?.round() ?? 0);
double _n(dynamic v) => (v as num?)?.toDouble() ?? 0;
String _qty(dynamic v, String unit) {
  final d = _n(v);
  final text = d == d.roundToDouble() ? NumberFormat.decimalPattern('id_ID').format(d.round()) : NumberFormat('#,##0.##', 'id_ID').format(d);
  return '$text $unit';
}
// Modal per satuan dasar sering pecahan kecil (Rp 0,038/gram): tampilkan per kg/liter.
String _perUnit(dynamic cost, String unit) => unit == 'gram'
    ? '${_rp(_n(cost) * 1000)}/kg'
    : unit == 'ml'
        ? '${_rp(_n(cost) * 1000)}/liter'
        : '${_rp(cost)}/$unit';

String _errorText(Object e, String fallback) {
  if (e is DioException) {
    final detail = e.response?.data is Map ? (e.response!.data as Map)['detail'] : null;
    if (detail is String && detail.isNotEmpty) {
      if (RegExp('modified|concurrent|refresh|diubah', caseSensitive: false).hasMatch(detail)) {
        return 'Data ini baru saja diubah dari tempat lain. Minta Selaris AI menyiapkan ulang.';
      }
      return detail;
    }
    if (detail is Map && detail['message'] is String) return detail['message'] as String;
    if (e.type == DioExceptionType.connectionError || e.type == DioExceptionType.receiveTimeout) {
      return 'Koneksi terputus. Periksa di dashboard apakah sudah tersimpan sebelum mencoba lagi.';
    }
  }
  return fallback;
}

class _Shell extends StatelessWidget {
  final String tag;
  final String title;
  final List<Widget> children;
  const _Shell({required this.tag, required this.title, required this.children});

  @override
  Widget build(BuildContext context) {
    // Material (bukan Container berwarna): centang di dalam kartu butuh latar
    // Material supaya efek sentuhnya terlihat.
    return Padding(
      padding: const EdgeInsets.only(top: 8),
      child: Material(
      color: KasiraDS.surfaceCard,
      shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(14), side: const BorderSide(color: KasiraDS.borderDefault)),
      child: Padding(
      padding: const EdgeInsets.all(14),
      child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        Align(
          alignment: Alignment.centerLeft,
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
            decoration: BoxDecoration(color: KasiraDS.brandTint, borderRadius: BorderRadius.circular(99)),
            child: Text(tag, style: KasiraDS.sans(size: 11.5, weight: FontWeight.w700, color: KasiraDS.brandPrimary)),
          ),
        ),
        const SizedBox(height: 6),
        Text(title, style: KasiraDS.sans(size: 15.5, weight: FontWeight.w700, color: KasiraDS.textStrong)),
        const SizedBox(height: 6),
        ...children,
      ]),
      ),
      ),
    );
  }
}

class _Line extends StatelessWidget {
  final String left;
  final String right;
  final String? tag;
  const _Line(this.left, this.right, {this.tag});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(vertical: 6),
      decoration: const BoxDecoration(border: Border(bottom: BorderSide(color: KasiraDS.borderSubtle))),
      child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Expanded(
          child: Text.rich(TextSpan(children: [
            TextSpan(text: left),
            if (tag != null) TextSpan(text: '  $tag', style: KasiraDS.sans(size: 11.5, color: KasiraDS.textMuted)),
          ]), style: KasiraDS.sans(size: 13.5, color: KasiraDS.textBody)),
        ),
        const SizedBox(width: 10),
        Flexible(
          child: Text(right,
              textAlign: TextAlign.right,
              style: KasiraDS.sans(size: 13.5, weight: FontWeight.w600, color: KasiraDS.textStrong)),
        ),
      ]),
    );
  }
}

class _Note extends StatelessWidget {
  final String text;
  final Color? color;
  const _Note(this.text, {this.color});
  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(top: 6),
        child: Text(text, style: KasiraDS.sans(size: 12.5, color: color ?? KasiraDS.textMuted)),
      );
}

class _Impact extends StatelessWidget {
  final List rows;
  const _Impact(this.rows);
  @override
  Widget build(BuildContext context) {
    if (rows.isEmpty) return const SizedBox.shrink();
    return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
      const _Note('Modal per porsi yang ikut berubah:'),
      for (final r in rows)
        _Line('${r['produk']}',
            '${_rp(r['modal_lama'])} ke ${_rp(r['modal_baru'])}${r['margin_baru'] != null ? ' · margin ${r['margin_baru']}%' : ''}'),
    ]);
  }
}

/// Tombol Simpan + status. `onSave` melempar exception kalau gagal.
class _SaveBar extends StatefulWidget {
  final String label;
  final String savedText;
  final bool enabled;
  final Future<void> Function() onSave;
  const _SaveBar({required this.label, required this.savedText, required this.onSave, this.enabled = true});

  @override
  State<_SaveBar> createState() => _SaveBarState();
}

class _SaveBarState extends State<_SaveBar> {
  bool _busy = false, _done = false;
  String? _error;

  Future<void> _save() async {
    if (_busy || _done) return;
    setState(() { _busy = true; _error = null; });
    try {
      await widget.onSave();
      if (mounted) setState(() { _done = true; _busy = false; });
      HapticFeedback.lightImpact();
    } catch (e) {
      if (mounted) setState(() { _busy = false; _error = _errorText(e, 'Belum tersimpan. Coba lagi.'); });
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_done) return _Note(widget.savedText, color: KasiraDS.success);
    return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
      if (_error != null) _Note(_error!, color: KasiraDS.danger),
      const SizedBox(height: 10),
      FilledButton(
        onPressed: _busy || !widget.enabled ? null : _save,
        style: FilledButton.styleFrom(
          backgroundColor: KasiraDS.brandFill,
          foregroundColor: KasiraDS.onBrandFill,
          minimumSize: const Size.fromHeight(44),
          shape: RoundedRectangleBorder(borderRadius: KasiraDS.brMd),
        ),
        child: Text(_busy ? 'Menyimpan…' : widget.label),
      ),
    ]);
  }
}

// ─── Resep (susun_resep) ───────────────────────────────────────────────────

class _RecipeCard extends ConsumerStatefulWidget {
  final Map<String, dynamic> card;
  const _RecipeCard({required this.card});
  @override
  ConsumerState<_RecipeCard> createState() => _RecipeCardState();
}

class _RecipeCardState extends ConsumerState<_RecipeCard> {
  bool _replace = false;

  @override
  Widget build(BuildContext context) {
    final c = widget.card;
    final lines = (c['lines'] as List?) ?? [];
    final replaces = c['replaces_recipe'] == true;
    final ready = c['ready'] == true && c['fingerprint'] != null;
    return _Shell(
      tag: c['new_product'] == true ? 'Draf resep, produk baru' : 'Draf resep',
      title: '${c['product']}',
      children: [
        for (final l in lines)
          _Line('${l['bahan']}', '${l['takaran'] ?? '?'} ${l['satuan']}${l['biaya'] != null ? ' · ${_rp(l['biaya'])}' : ''}',
              tag: l['perkiraan'] == true ? 'perkiraan' : 'harga toko'),
        if (c['total_cost'] != null)
          _Note('Modal per porsi ${_rp(c['total_cost'])}${c['margin'] != null ? ', margin ${c['margin']}% dari harga ${_rp(c['base_price'])}' : ''}',
              color: KasiraDS.textStrong),
        if (!ready && (c['missing'] as List?)?.isNotEmpty == true) _Note('Belum lengkap: ${(c['missing'] as List).join(' ')}'),
        const _Note('Takaran berlabel perkiraan adalah usulan umum. Untuk mengubah takaran, buka Atur HPP di dashboard web.'),
        if (replaces)
          CheckboxListTile(
            contentPadding: EdgeInsets.zero,
            dense: true,
            value: _replace,
            onChanged: (v) => setState(() => _replace = v ?? false),
            title: Text('Ganti resep lama produk ini', style: KasiraDS.sans(size: 13, color: KasiraDS.textBody)),
            controlAffinity: ListTileControlAffinity.leading,
          ),
        if (ready)
          _SaveBar(
            label: 'Simpan resep',
            savedText: 'Resep ${c['product']} tersimpan. Modal dan stoknya sekarang terhitung.',
            enabled: !replaces || _replace,
            onSave: () async {
              await ref.read(apiClientProvider).post('/ai/hpp-setup/sessions/${c['session_id']}/approve', data: {
                'outlet_id': SessionCache.instance.outletId,
                'revision': c['revision'],
                'fingerprint': c['fingerprint'],
                'replace_recipe': _replace,
              });
            },
          ),
      ],
    );
  }
}

// ─── Harga beli bahan (ubah_harga_bahan) ───────────────────────────────────

class _PriceCard extends ConsumerWidget {
  final Map<String, dynamic> card;
  const _PriceCard({required this.card});
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final c = card, unit = '${c['base_unit']}';
    return _Shell(tag: 'Ubah harga beli', title: '${c['bahan']}', children: [
      _Line('Sekarang', '${_rp(c['harga_lama'])} per ${_qty(c['jumlah_lama'], unit)}'),
      _Line('Jadi', '${_rp(c['harga_baru'])} per ${_qty(c['jumlah_baru'], unit)}'),
      _Line('Modal bahan', '${_perUnit(c['biaya_lama'], unit)} ke ${_perUnit(c['biaya_baru'], unit)}'),
      _Impact((c['produk'] as List?) ?? []),
      const _Note('Stok tidak berubah. Kalau barangnya baru datang, catat sebagai bahan masuk.'),
      _SaveBar(
        label: 'Simpan harga',
        savedText: 'Harga ${c['bahan']} tersimpan.',
        onSave: () async {
          await ref.read(apiClientProvider).put('/ingredients/${c['ingredient_id']}',
              data: {'buy_price': c['harga_baru'], 'buy_qty': c['jumlah_baru'], 'row_version': c['row_version']});
        },
      ),
    ]);
  }
}

// ─── Bahan masuk (tambah_stok) ─────────────────────────────────────────────

class _StockCard extends ConsumerStatefulWidget {
  final Map<String, dynamic> card;
  const _StockCard({required this.card});
  @override
  ConsumerState<_StockCard> createState() => _StockCardState();
}

class _StockCardState extends ConsumerState<_StockCard> {
  bool _unpaid = false;
  // Satu id per kartu: kirim ulang setelah koneksi putus dikenali server sebagai nota yang sama.
  final String _requestId = const Uuid().v4();
  bool _purchaseSaved = false;
  final Set<String> _restocked = {};

  @override
  Widget build(BuildContext context) {
    final c = widget.card;
    final lines = ((c['lines'] as List?) ?? []).cast<Map>();
    final priced = lines.where((l) => l['harga_total'] != null).toList();
    final plain = lines.where((l) => l['harga_total'] == null).toList();
    final nota = c['nota'] == true;
    final problems = (c['masalah'] as List?) ?? [];
    return _Shell(
      tag: nota ? 'Nota belanja' : 'Bahan masuk',
      title: nota && c['pemasok'] != null ? '${c['pemasok']}' : lines.map((l) => l['bahan']).join(', '),
      children: [
        for (final l in lines)
          _Line('${l['bahan']}',
              'Stok ${_qty(l['stok_lama'], '${l['base_unit']}')} ke ${_qty(l['stok_baru'], '${l['base_unit']}')}${l['harga_total'] != null ? ' · ${_rp(l['harga_total'])}' : ''}',
              tag: '+${_qty(l['jumlah'], '${l['satuan']}')}'),
        for (final l in priced)
          if (l['biaya_baru'] != null && (_n(l['biaya_baru']) - _n(l['biaya_lama'])).abs() > 1e-9)
            _Line('Modal ${l['bahan']}', '${_perUnit(l['biaya_lama'], '${l['base_unit']}')} ke ${_perUnit(l['biaya_baru'], '${l['base_unit']}')}'),
        _Impact((c['produk'] as List?) ?? []),
        if (c['total'] != null) _Note('Total nota ${_rp(c['total'])}', color: KasiraDS.textStrong),
        if (nota)
          CheckboxListTile(
            contentPadding: EdgeInsets.zero,
            dense: true,
            value: _unpaid,
            onChanged: (v) => setState(() => _unpaid = v ?? false),
            title: Text('Belum dibayar, catat sebagai utang', style: KasiraDS.sans(size: 13, color: KasiraDS.textBody)),
            controlAffinity: ListTileControlAffinity.leading,
          ),
        if (nota && plain.isNotEmpty) _Note('${plain.map((l) => l['bahan']).join(', ')} dicatat sebagai stok masuk tanpa harga.'),
        if (problems.isNotEmpty)
          _Note('Belum masuk kartu: ${problems.map((m) => '${m['bahan']} (${m['masalah']}${(m['kandidat'] as List?)?.isNotEmpty == true ? ': ${(m['kandidat'] as List).join(', ')}' : ''})').join('; ')}.'),
        _SaveBar(
          label: nota ? 'Simpan nota' : 'Simpan stok masuk',
          savedText: nota ? 'Nota tersimpan di Pembelian. Stok sudah bertambah.' : 'Stok sudah bertambah.',
          onSave: () async {
            final dio = ref.read(apiClientProvider);
            if (priced.isNotEmpty && !_purchaseSaved) {
              await dio.post('/purchases/', data: {
                'client_request_id': _requestId,
                'outlet_id': c['outlet_id'],
                if (c['pemasok'] != null) 'supplier_name': c['pemasok'],
                'notes': 'Dicatat lewat Selaris AI',
                'paid_amount': _unpaid ? 0 : null,
                'items': [
                  for (final l in priced)
                    {
                      'ingredient_id': l['ingredient_id'],
                      'quantity': l['jumlah'],
                      'unit': l['satuan'],
                      'unit_price': ((_n(l['harga_total']) / _n(l['jumlah'])) * 100).round() / 100,
                      'total_price': l['harga_total'],
                    }
                ],
              });
              _purchaseSaved = true;
            }
            for (final l in plain) {
              final id = '${l['ingredient_id']}';
              if (_restocked.contains(id)) continue;
              await dio.post('/ingredients/$id/restock',
                  data: {'outlet_id': c['outlet_id'], 'quantity': l['jumlah_dasar'], 'notes': 'Dicatat lewat Selaris AI'});
              _restocked.add(id);
            }
          },
        ),
      ],
    );
  }
}

// ─── Harga jual (ubah_harga_jual) ──────────────────────────────────────────

class _SellCard extends ConsumerStatefulWidget {
  final Map<String, dynamic> card;
  const _SellCard({required this.card});
  @override
  ConsumerState<_SellCard> createState() => _SellCardState();
}

class _SellCardState extends ConsumerState<_SellCard> {
  late final Map<String, TextEditingController> _prices;
  final Set<String> _saved = {};

  List<Map> get _lines => ((widget.card['lines'] as List?) ?? []).cast<Map>();

  @override
  void initState() {
    super.initState();
    _prices = {for (final l in _lines) '${l['product_id']}': TextEditingController(text: '${l['harga_baru']}')};
  }

  @override
  void dispose() {
    for (final c in _prices.values) {
      c.dispose();
    }
    super.dispose();
  }

  int _value(Map l) => int.tryParse(_prices['${l['product_id']}']!.text.replaceAll(RegExp(r'\D'), '')) ?? 0;

  @override
  Widget build(BuildContext context) {
    final problems = (widget.card['masalah'] as List?) ?? [];
    final invalid = _lines.any((l) => _value(l) <= 0);
    return _Shell(tag: 'Ubah harga jual', title: _lines.length == 1 ? '${_lines.first['menu']}' : '${_lines.length} menu', children: [
      for (final l in _lines) _sellRow(l),
      if (problems.isNotEmpty)
        _Note('Belum masuk kartu: ${problems.map((m) => '${m['menu']} (${m['masalah']}${(m['kandidat'] as List?)?.isNotEmpty == true ? ': ${(m['kandidat'] as List).join(', ')}' : ''})').join('; ')}.'),
      const _Note('Harga baru dipakai kasir dan toko online setelah sinkron.'),
      _SaveBar(
        label: 'Simpan harga jual',
        savedText: 'Harga jual tersimpan.',
        enabled: !invalid,
        onSave: () async {
          final dio = ref.read(apiClientProvider);
          for (final l in _lines) {
            final id = '${l['product_id']}';
            if (_saved.contains(id)) continue;
            await dio.put('/products/$id', data: {'base_price': _value(l), 'row_version': l['row_version']});
            setState(() => _saved.add(id));
          }
        },
      ),
    ]);
  }

  Widget _sellRow(Map l) {
    final id = '${l['product_id']}';
    final price = _value(l);
    final modal = l['modal'] as num?;
    final margin = modal != null && price > 0 ? ((price - modal) / price * 1000).round() / 10 : null;
    final oldPrice = _n(l['harga_lama']);
    final variants = (l['varian'] as List?) ?? [];
    return Container(
      padding: const EdgeInsets.symmetric(vertical: 8),
      decoration: const BoxDecoration(border: Border(bottom: BorderSide(color: KasiraDS.borderSubtle))),
      child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        Text.rich(TextSpan(children: [
          TextSpan(text: '${l['menu']}', style: KasiraDS.sans(size: 14, weight: FontWeight.w600, color: KasiraDS.textStrong)),
          TextSpan(text: '  ${l['cara']}', style: KasiraDS.sans(size: 11.5, color: KasiraDS.textMuted)),
        ])),
        const SizedBox(height: 6),
        // Wrap: di layar 320px dengan teks besar, isian harga turun ke baris berikutnya.
        Wrap(crossAxisAlignment: WrapCrossAlignment.center, spacing: 4, runSpacing: 4, children: [
          Text('${_rp(oldPrice)} ke', style: KasiraDS.sans(size: 13.5, color: KasiraDS.textBody)),
          SizedBox(
            width: 120,
            child: TextField(
              controller: _prices[id],
              enabled: !_saved.contains(id),
              keyboardType: TextInputType.number,
              inputFormatters: [FilteringTextInputFormatter.digitsOnly],
              onChanged: (_) => setState(() {}),
              decoration: const InputDecoration(prefixText: 'Rp ', isDense: true),
            ),
          ),
        ]),
        const SizedBox(height: 4),
        Text(modal != null ? 'Modal ${_rp(modal)} · margin ${l['margin_lama'] ?? '?'}% ke ${margin ?? '?'}%' : 'Belum ada resep, margin tidak dihitung',
            style: KasiraDS.sans(size: 12.5, color: KasiraDS.textMuted)),
        if (modal != null && price > 0 && price <= modal) const _Note('Di bawah modal', color: KasiraDS.danger),
        if (oldPrice > 0 && (price > oldPrice * 3 || price * 3 < oldPrice))
          const _Note('Periksa angkanya, beda jauh dari harga lama', color: KasiraDS.danger),
        if (variants.isNotEmpty)
          _Note('Varian ikut bergeser: ${variants.map((v) => '${v['nama']} ${_rp(v['lama'])} ke ${_rp(_n(v['lama']) + price - oldPrice)}').join(', ')}'),
      ]),
    );
  }
}
