import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../../../core/theme/kasira_ds.dart';
import '../../../../core/widgets/sefrekuensi_nudge_banner.dart';
import '../../providers/online_orders_provider.dart';

final _rp = NumberFormat.currency(locale: 'id_ID', symbol: 'Rp ', decimalDigits: 0);

/// Layar "Pesanan Online": pesanan dari halaman toko yang menunggu keputusan
/// kasir. Kata-katanya sama dengan yang dibaca pelanggan di halaman lacak
/// (Menunggu konfirmasi, Disiapkan, Siap diambil) supaya kasir dan
/// pelanggan bicara satu bahasa waktu teleponan.
class OnlineOrdersPage extends ConsumerStatefulWidget {
  const OnlineOrdersPage({super.key});

  @override
  ConsumerState<OnlineOrdersPage> createState() => _OnlineOrdersPageState();
}

class _OnlineOrdersPageState extends ConsumerState<OnlineOrdersPage> {
  int _segment = 0; // 0 menunggu, 1 diproses, 2 selesai

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final n = ref.read(onlineOrdersProvider.notifier);
      n.start();
      n.fetch();
    });
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(onlineOrdersProvider);
    final lists = [state.pending, state.inProgress, state.done];
    final list = lists[_segment];
    return Scaffold(
      backgroundColor: KasiraDS.bgBase,
      body: SafeArea(
        child: Column(
          children: [
            _header(state),
            _segments(state),
            // Langkah 3 jembatan Sefrekuensi: ajakan pasang di titik sakit.
            const SefrekuensiNudgeBanner(),
            if (state.error != null)
              Padding(
                padding: const EdgeInsets.fromLTRB(16, 0, 16, 8),
                child: Text(state.error!, style: KasiraDS.sans(size: 12.5, color: KasiraDS.danger)),
              ),
            Expanded(
              child: RefreshIndicator(
                color: KasiraDS.brandPrimary,
                onRefresh: () => ref.read(onlineOrdersProvider.notifier).fetch(),
                child: list.isEmpty
                    ? ListView(
                        physics: const AlwaysScrollableScrollPhysics(),
                        children: [SizedBox(height: MediaQuery.sizeOf(context).height * 0.25), _empty(state)],
                      )
                    : ListView.separated(
                        physics: const AlwaysScrollableScrollPhysics(),
                        padding: const EdgeInsets.fromLTRB(16, 4, 16, 28),
                        itemCount: list.length,
                        separatorBuilder: (_, __) => const SizedBox(height: 12),
                        itemBuilder: (_, i) => _OrderCard(order: list[i], onAccept: _accept, onReject: _reject, onStatus: _setStatus),
                      ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _header(OnlineOrdersState state) {
    final n = ref.read(onlineOrdersProvider.notifier);
    return Padding(
      padding: const EdgeInsets.fromLTRB(8, 6, 12, 8),
      child: Row(
        children: [
          IconButton(
            onPressed: () => Navigator.of(context).maybePop(),
            icon: const Icon(LucideIcons.chevronLeft, color: KasiraDS.textStrong),
          ),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('Pesanan Online', style: KasiraDS.display(size: 20)),
                const SizedBox(height: 2),
                Row(children: [
                  Container(
                    width: 7,
                    height: 7,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      color: state.streamConnected ? KasiraDS.success : KasiraDS.warning,
                    ),
                  ),
                  const SizedBox(width: 6),
                  Text(
                    state.streamConnected ? 'Terhubung, pesanan baru masuk langsung' : 'Menyambung ulang, diperbarui tiap 30 detik',
                    style: KasiraDS.sans(size: 11.5, color: KasiraDS.textMuted),
                  ),
                ]),
              ],
            ),
          ),
          IconButton(
            tooltip: state.soundEnabled ? 'Bel menyala' : 'Bel dimatikan',
            onPressed: () => n.setSoundEnabled(!state.soundEnabled),
            onLongPress: n.testRing,
            icon: Icon(state.soundEnabled ? LucideIcons.bellRing : LucideIcons.bellOff,
                color: state.soundEnabled ? KasiraDS.textStrong : KasiraDS.textMuted),
          ),
        ],
      ),
    );
  }

  Widget _segments(OnlineOrdersState state) {
    final labels = ['Menunggu', 'Diproses', 'Selesai'];
    final counts = [state.pending.length, state.inProgress.length, state.done.length];
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 0, 16, 12),
      child: Row(
        children: List.generate(3, (i) {
          final active = _segment == i;
          return Padding(
            padding: EdgeInsets.only(right: i < 2 ? 8 : 0),
            child: InkWell(
              onTap: () => setState(() => _segment = i),
              borderRadius: KasiraDS.brPill,
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                decoration: BoxDecoration(
                  color: active ? KasiraDS.surfaceInverse : KasiraDS.surfaceCard,
                  borderRadius: KasiraDS.brPill,
                  border: Border.all(color: active ? KasiraDS.surfaceInverse : KasiraDS.borderSubtle),
                ),
                child: Row(children: [
                  Text(labels[i], style: KasiraDS.sans(size: 13, weight: FontWeight.w700, color: active ? KasiraDS.textInverse : KasiraDS.textBody)),
                  if (counts[i] > 0) ...[
                    const SizedBox(width: 6),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 1),
                      decoration: BoxDecoration(
                        color: i == 0 && !active ? KasiraDS.brandPrimary : (active ? Colors.white.withOpacity(0.18) : KasiraDS.bgSubtle),
                        borderRadius: KasiraDS.brPill,
                      ),
                      child: Text('${counts[i]}',
                          style: KasiraDS.sans(size: 11, weight: FontWeight.w800, color: (i == 0 && !active) || active ? Colors.white : KasiraDS.textStrong)),
                    ),
                  ],
                ]),
              ),
            ),
          );
        }),
      ),
    );
  }

  Widget _empty(OnlineOrdersState state) {
    final text = switch (_segment) {
      0 => 'Tidak ada pesanan yang menunggu.\nPesanan baru dari halaman toko muncul di sini dengan bunyi bel.',
      1 => 'Tidak ada pesanan yang sedang disiapkan.',
      _ => 'Belum ada pesanan online yang selesai hari ini.',
    };
    return Column(children: [
      Icon(_segment == 0 ? LucideIcons.bellRing : LucideIcons.packageCheck, size: 40, color: KasiraDS.borderDefault),
      const SizedBox(height: 12),
      Padding(
        padding: const EdgeInsets.symmetric(horizontal: 40),
        child: Text(text, textAlign: TextAlign.center, style: KasiraDS.sans(size: 13.5, color: KasiraDS.textMuted, height: 1.45)),
      ),
    ]);
  }

  // ── Aksi ──────────────────────────────────────────────────────────────

  Future<void> _accept(OnlineOrder order) async {
    final eta = await _pickEta(order);
    if (eta == null || !mounted) return;
    final err = await ref.read(onlineOrdersProvider.notifier).accept(order.id, eta);
    _toast(err ?? 'Pesanan #${order.displayNumber} diterima. Pelanggan dikabari siap dalam $eta menit.', ok: err == null);
  }

  Future<void> _reject(OnlineOrder order) async {
    final reason = await _pickReason(order);
    if (reason == null || !mounted) return;
    final err = await ref.read(onlineOrdersProvider.notifier).reject(order.id, reason);
    _toast(err ?? 'Pesanan #${order.displayNumber} ditolak. Pelanggan dikabari.', ok: err == null);
  }

  Future<void> _setStatus(OnlineOrder order, String status) async {
    final err = await ref.read(onlineOrdersProvider.notifier).setStatus(order.id, status);
    final label = status == 'ready'
        ? (order.orderType == 'delivery' ? 'ditandai sedang diantar' : order.isTableTab ? 'ditandai diantar ke meja' : 'ditandai siap diambil')
        : 'selesai';
    _toast(err ?? 'Pesanan #${order.displayNumber} $label.', ok: err == null);
  }

  void _toast(String msg, {required bool ok}) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(
      content: Text(msg),
      backgroundColor: ok ? KasiraDS.textStrong : KasiraDS.danger,
      behavior: SnackBarBehavior.floating,
    ));
  }

  Future<int?> _pickEta(OnlineOrder order) {
    var eta = 15;
    return showModalBottomSheet<int>(
      context: context,
      backgroundColor: KasiraDS.surfaceCard,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(28))),
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setS) => Padding(
          padding: EdgeInsets.fromLTRB(20, 16, 20, 20 + MediaQuery.viewInsetsOf(ctx).bottom),
          child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('Terima pesanan #${order.displayNumber}', style: KasiraDS.display(size: 19)),
            const SizedBox(height: 4),
            Text('Perkiraan waktu ini dikirim ke pelanggan lewat WhatsApp.', style: KasiraDS.sans(size: 13, color: KasiraDS.textMuted)),
            const SizedBox(height: 16),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [10, 15, 20, 30, 45, 60].map((m) {
                final active = eta == m;
                return ChoiceChip(
                  label: Text('$m menit'),
                  selected: active,
                  onSelected: (_) => setS(() => eta = m),
                  selectedColor: KasiraDS.surfaceInverse,
                  backgroundColor: KasiraDS.bgSubtle,
                  labelStyle: KasiraDS.sans(size: 13, weight: FontWeight.w700, color: active ? KasiraDS.textInverse : KasiraDS.textStrong),
                  side: BorderSide.none,
                  shape: RoundedRectangleBorder(borderRadius: KasiraDS.brPill),
                );
              }).toList(),
            ),
            const SizedBox(height: 18),
            _primaryBtn('Terima, siap dalam $eta menit', () => Navigator.pop(ctx, eta)),
          ]),
        ),
      ),
    );
  }

  Future<String?> _pickReason(OnlineOrder order) {
    const presets = ['Stok habis', 'Toko sedang penuh', 'Di luar jangkauan antar', 'Toko akan tutup'];
    String? chosen;
    final ctrl = TextEditingController();
    return showModalBottomSheet<String>(
      context: context,
      isScrollControlled: true,
      backgroundColor: KasiraDS.surfaceCard,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(28))),
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setS) {
          final reason = (ctrl.text.trim().isNotEmpty ? ctrl.text.trim() : chosen);
          return Padding(
            padding: EdgeInsets.fromLTRB(20, 16, 20, 20 + MediaQuery.viewInsetsOf(ctx).bottom),
            child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('Tolak pesanan #${order.displayNumber}', style: KasiraDS.display(size: 19)),
              const SizedBox(height: 4),
              Text(
                order.isPaid
                    ? 'Alasan dikirim ke pelanggan. Pembayaran QRIS dikembalikan otomatis.'
                    : 'Alasan dikirim ke pelanggan lewat WhatsApp.',
                style: KasiraDS.sans(size: 13, color: KasiraDS.textMuted),
              ),
              const SizedBox(height: 16),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: presets.map((p) {
                  final active = chosen == p && ctrl.text.trim().isEmpty;
                  return ChoiceChip(
                    label: Text(p),
                    selected: active,
                    onSelected: (_) => setS(() { chosen = p; ctrl.clear(); }),
                    selectedColor: KasiraDS.surfaceInverse,
                    backgroundColor: KasiraDS.bgSubtle,
                    labelStyle: KasiraDS.sans(size: 13, weight: FontWeight.w700, color: active ? KasiraDS.textInverse : KasiraDS.textStrong),
                    side: BorderSide.none,
                    shape: RoundedRectangleBorder(borderRadius: KasiraDS.brPill),
                  );
                }).toList(),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: ctrl,
                onChanged: (_) => setS(() {}),
                maxLength: 120,
                decoration: InputDecoration(
                  hintText: 'Atau tulis alasan lain',
                  counterText: '',
                  filled: true,
                  fillColor: KasiraDS.bgSubtle,
                  border: OutlineInputBorder(borderRadius: KasiraDS.brMd, borderSide: BorderSide.none),
                ),
              ),
              const SizedBox(height: 14),
              _primaryBtn('Tolak pesanan', reason == null || reason.length < 3 ? null : () => Navigator.pop(ctx, reason), danger: true),
            ]),
          );
        },
      ),
    );
  }

  Widget _primaryBtn(String label, VoidCallback? onTap, {bool danger = false}) {
    return SizedBox(
      width: double.infinity,
      height: 50,
      child: FilledButton(
        onPressed: onTap,
        style: FilledButton.styleFrom(
          backgroundColor: danger ? KasiraDS.danger : KasiraDS.surfaceInverse,
          disabledBackgroundColor: KasiraDS.borderSubtle,
          shape: RoundedRectangleBorder(borderRadius: KasiraDS.brMd),
        ),
        child: Text(label, style: KasiraDS.sans(size: 15, weight: FontWeight.w700, color: Colors.white)),
      ),
    );
  }
}

class _OrderCard extends StatelessWidget {
  final OnlineOrder order;
  final Future<void> Function(OnlineOrder) onAccept;
  final Future<void> Function(OnlineOrder) onReject;
  final Future<void> Function(OnlineOrder, String) onStatus;
  const _OrderCard({required this.order, required this.onAccept, required this.onReject, required this.onStatus});

  String _ago(DateTime t) {
    final d = DateTime.now().difference(t);
    if (d.inMinutes < 1) return 'baru saja';
    if (d.inMinutes < 60) return '${d.inMinutes} mnt lalu';
    if (d.inHours < 24) return '${d.inHours} jam lalu';
    return DateFormat('d MMM HH:mm', 'id_ID').format(t);
  }

  @override
  Widget build(BuildContext context) {
    final waiting = order.isPending ? DateTime.now().difference(order.createdAt).inMinutes : null;
    final urgent = (waiting ?? 0) >= 6;
    return Container(
      decoration: BoxDecoration(
        color: KasiraDS.surfaceCard,
        borderRadius: KasiraDS.brLg,
        border: Border.all(color: order.isPending ? (urgent ? KasiraDS.danger.withOpacity(0.5) : KasiraDS.brandPrimary.withOpacity(0.35)) : KasiraDS.borderSubtle),
        boxShadow: KasiraDS.shadowSm,
      ),
      padding: const EdgeInsets.all(14),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        // Baris 1: nomor, tipe, waktu, pembayaran
        Row(children: [
          Text('#${order.displayNumber}', style: KasiraDS.display(size: 20)),
          const SizedBox(width: 10),
          _chip(order.typeLabel, KasiraDS.bgSubtle, KasiraDS.textStrong),
          const Spacer(),
          _chip(order.paymentLabel, order.isPaid ? KasiraDS.success.withOpacity(0.14) : KasiraDS.bgSubtle, order.isPaid ? KasiraDS.success : KasiraDS.textBody),
        ]),
        const SizedBox(height: 6),
        Text(
          order.isPending
              ? (urgent ? 'Menunggu $waiting menit. Segera putuskan.' : 'Masuk ${_ago(order.createdAt)}')
              : '${order.statusLabel} · ${_ago(order.createdAt)}',
          style: KasiraDS.sans(size: 12, color: urgent && order.isPending ? KasiraDS.danger : KasiraDS.textMuted, weight: urgent && order.isPending ? FontWeight.w700 : FontWeight.w500),
        ),
        const SizedBox(height: 12),
        // Pemesan + WA
        Row(children: [
          const Icon(LucideIcons.user, size: 16, color: KasiraDS.textMuted),
          const SizedBox(width: 8),
          Expanded(
            child: Text(order.customerName ?? 'Pelanggan', style: KasiraDS.sans(size: 14, weight: FontWeight.w700, color: KasiraDS.textStrong)),
          ),
          if (order.waNumber != null)
            InkWell(
              onTap: () => launchUrl(
                Uri.parse('https://wa.me/${order.waNumber}?text=${Uri.encodeComponent('Halo ${order.customerName ?? ''}, dari toko soal pesanan #${order.displayNumber}.')}'),
                mode: LaunchMode.externalApplication,
              ),
              borderRadius: KasiraDS.brPill,
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                decoration: BoxDecoration(color: const Color(0xFF25D366).withOpacity(0.14), borderRadius: KasiraDS.brPill),
                child: Row(children: [
                  const Icon(LucideIcons.messageCircle, size: 14, color: Color(0xFF128C7E)),
                  const SizedBox(width: 5),
                  Text('Chat WA', style: KasiraDS.sans(size: 12, weight: FontWeight.w700, color: const Color(0xFF128C7E))),
                ]),
              ),
            ),
        ]),
        const SizedBox(height: 10),
        // Item
        ...order.items.map((it) => Padding(
              padding: const EdgeInsets.only(bottom: 4),
              child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                SizedBox(width: 28, child: Text('${it.quantity}x', style: KasiraDS.sans(size: 13.5, weight: FontWeight.w800, color: KasiraDS.textStrong))),
                Expanded(
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text(it.productName, style: KasiraDS.sans(size: 13.5, color: KasiraDS.textStrong)),
                    if (it.notes != null) Text(it.notes!, style: KasiraDS.sans(size: 12, color: KasiraDS.textMuted)),
                  ]),
                ),
                Text(_rp.format(it.totalPrice), style: KasiraDS.sans(size: 13, color: KasiraDS.textBody)),
              ]),
            )),
        if (order.notes != null) ...[
          const SizedBox(height: 6),
          Container(
            width: double.infinity,
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
            decoration: BoxDecoration(color: KasiraDS.warning.withOpacity(0.12), borderRadius: KasiraDS.brSm),
            child: Text('Catatan: ${order.notes}', style: KasiraDS.sans(size: 12.5, weight: FontWeight.w600, color: KasiraDS.textStrong)),
          ),
        ],
        if (order.deliveryAddress != null) ...[
          const SizedBox(height: 6),
          Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
            const Icon(LucideIcons.mapPin, size: 14, color: KasiraDS.textMuted),
            const SizedBox(width: 6),
            Expanded(child: Text(order.deliveryAddress!, style: KasiraDS.sans(size: 12.5, color: KasiraDS.textBody))),
            // Titik dari Google Maps (mig 104): kurir buka rute langsung.
            if (order.deliveryLat != null && order.deliveryLng != null)
              InkWell(
                onTap: () => launchUrl(
                  Uri.parse('https://www.google.com/maps/dir/?api=1&destination=${order.deliveryLat},${order.deliveryLng}'),
                  mode: LaunchMode.externalApplication,
                ),
                borderRadius: KasiraDS.brSm,
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                  child: Row(children: [
                    const Icon(LucideIcons.navigation, size: 13, color: KasiraDS.brandPrimary),
                    const SizedBox(width: 4),
                    Text(order.deliveryDistanceKm != null ? 'Peta · ${order.deliveryDistanceKm!.toStringAsFixed(1)} km' : 'Peta',
                        style: KasiraDS.sans(size: 12, weight: FontWeight.w700, color: KasiraDS.brandPrimary)),
                  ]),
                ),
              ),
          ]),
        ],
        // Bukti bayar QRIS statis toko (mig 104): kasir WAJIB lihat sebelum Terima,
        // karena Terima = menandai pembayaran lunas.
        if (order.paymentProofUrl != null) ...[
          const SizedBox(height: 8),
          GestureDetector(
            onTap: () => showDialog(
              context: context,
              builder: (_) => Dialog(
                insetPadding: const EdgeInsets.all(16),
                child: InteractiveViewer(child: CachedNetworkImage(imageUrl: order.paymentProofUrl!, fit: BoxFit.contain)),
              ),
            ),
            child: Container(
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(color: KasiraDS.warning.withOpacity(0.10), borderRadius: KasiraDS.brSm),
              child: Row(children: [
                ClipRRect(
                  borderRadius: BorderRadius.circular(6),
                  child: CachedNetworkImage(imageUrl: order.paymentProofUrl!, width: 44, height: 44, fit: BoxFit.cover,
                      errorWidget: (_, __, ___) => const Icon(LucideIcons.imageOff, color: KasiraDS.textMuted)),
                ),
                const SizedBox(width: 10),
                Expanded(child: Text('Bukti bayar dari pelanggan. Ketuk untuk memperbesar, cocokkan dengan notifikasi bank sebelum Terima.',
                    style: KasiraDS.sans(size: 12, color: KasiraDS.textStrong))),
              ]),
            ),
          ),
        ] else if (order.isPending && order.paymentMethod == 'qris' && order.paymentChannel == 'manual') ...[
          const SizedBox(height: 8),
          Text('Pelanggan memilih QRIS toko dan belum mengirim bukti. Cek notifikasi bank sebelum Terima.',
              style: KasiraDS.sans(size: 12, color: KasiraDS.textMuted)),
        ],
        if (order.cancelReason != null) ...[
          const SizedBox(height: 6),
          Text('Alasan: ${order.cancelReason}', style: KasiraDS.sans(size: 12.5, color: KasiraDS.danger)),
        ],
        const SizedBox(height: 10),
        Row(children: [
          Text('Total', style: KasiraDS.sans(size: 13, color: KasiraDS.textMuted)),
          const Spacer(),
          Text(_rp.format(order.totalAmount), style: KasiraDS.display(size: 18)),
        ]),
        ..._actions(),
      ]),
    );
  }

  List<Widget> _actions() {
    Widget filled(String label, VoidCallback onTap, {Color? color, int flex = 1}) => Expanded(
          flex: flex,
          child: SizedBox(
            height: 46,
            child: FilledButton(
              onPressed: onTap,
              style: FilledButton.styleFrom(
                backgroundColor: color ?? KasiraDS.surfaceInverse,
                shape: RoundedRectangleBorder(borderRadius: KasiraDS.brMd),
              ),
              child: Text(label, style: KasiraDS.sans(size: 14, weight: FontWeight.w700, color: Colors.white)),
            ),
          ),
        );
    Widget outlined(String label, VoidCallback onTap) => Expanded(
          child: SizedBox(
            height: 46,
            child: OutlinedButton(
              onPressed: onTap,
              style: OutlinedButton.styleFrom(
                foregroundColor: KasiraDS.danger,
                side: BorderSide(color: KasiraDS.danger.withOpacity(0.5)),
                shape: RoundedRectangleBorder(borderRadius: KasiraDS.brMd),
              ),
              child: Text(label, style: KasiraDS.sans(size: 14, weight: FontWeight.w700, color: KasiraDS.danger)),
            ),
          ),
        );

    switch (order.status) {
      case 'pending':
        return [
          const SizedBox(height: 12),
          Row(children: [outlined('Tolak', () => onReject(order)), const SizedBox(width: 10), filled('Terima', () => onAccept(order), flex: 2)]),
        ];
      case 'preparing':
        return [
          const SizedBox(height: 12),
          Row(children: [
            filled(
              order.orderType == 'delivery' ? 'Sedang diantar' : order.isTableTab ? 'Diantar ke meja' : 'Siap diambil',
              () => onStatus(order, 'ready'),
              color: KasiraDS.info,
            ),
          ]),
        ];
      case 'ready':
      case 'served':
        if (order.isTableTab) {
          // Selesai-nya lewat pembayaran tagihan meja (tab Meja), bukan dari sini.
          return [
            const SizedBox(height: 10),
            Text('Pembayaran lewat tagihan meja. Tutup dari tab Meja saat pelanggan membayar.',
                style: KasiraDS.sans(size: 12, color: KasiraDS.textMuted)),
          ];
        }
        return [
          const SizedBox(height: 12),
          Row(children: [filled('Selesai', () => onStatus(order, 'completed'), color: KasiraDS.success)]),
        ];
      default:
        return const [];
    }
  }

  Widget _chip(String text, Color bg, Color fg) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 4),
        decoration: BoxDecoration(color: bg, borderRadius: KasiraDS.brPill),
        child: Text(text, style: KasiraDS.sans(size: 11.5, weight: FontWeight.w700, color: fg)),
      );
}
