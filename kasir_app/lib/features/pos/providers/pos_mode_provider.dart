import 'package:flutter_riverpod/flutter_riverpod.dart';

enum PosMode { selection, takeaway, dineInTableSelect, dineInOrdering }

final posModeProvider = StateProvider<PosMode>((ref) => PosMode.selection);

/// One-shot signal untuk redirect dashboard ke POS tab.
/// Dipakai oleh `tab_detail_page.dart` saat user tap "Tambah Pesanan" — set
/// true sebelum `context.go('/dashboard')`. Dashboard consume value saat
/// build, set selectedIndex=1 (POS), lalu clear provider ke false.
///
/// Beda dari watch posModeProvider persisten (yang bikin user gak bisa keluar
/// dari POS tab selama dineInOrdering aktif), ini cuma fire SEKALI per request.
final pendingNavigateToPosProvider = StateProvider<bool>((ref) => false);
