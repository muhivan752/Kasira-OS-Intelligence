import 'dart:async';
import 'dart:io';
import 'dart:typed_data';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:print_bluetooth_thermal/print_bluetooth_thermal.dart';
import 'package:permission_handler/permission_handler.dart';

const _prefKeyMac = 'printer_mac';
const _prefKeyName = 'printer_name';

class PrinterDevice {
  final String name;
  final String address;
  const PrinterDevice({required this.name, required this.address});
}

class PrinterState {
  final PrinterDevice? savedDevice;
  final bool isConnected;
  final bool isScanning;
  final bool isPrinting;
  final List<BluetoothInfo> scanResults;
  final String? error;

  const PrinterState({
    this.savedDevice,
    this.isConnected = false,
    this.isScanning = false,
    this.isPrinting = false,
    this.scanResults = const [],
    this.error,
  });

  PrinterState copyWith({
    PrinterDevice? savedDevice,
    bool? isConnected,
    bool? isScanning,
    bool? isPrinting,
    List<BluetoothInfo>? scanResults,
    String? error,
    bool clearError = false,
  }) {
    return PrinterState(
      savedDevice: savedDevice ?? this.savedDevice,
      isConnected: isConnected ?? this.isConnected,
      isScanning: isScanning ?? this.isScanning,
      isPrinting: isPrinting ?? this.isPrinting,
      scanResults: scanResults ?? this.scanResults,
      error: clearError ? null : (error ?? this.error),
    );
  }
}

/// Result of printBytes() — lebih informatif daripada bool biar caller
/// bisa bedain "busy" dari "failed" dari "notConnected".
enum PrintOutcome { success, busy, notConnected, failed }

class PrinterNotifier extends StateNotifier<PrinterState> {
  PrinterNotifier() : super(const PrinterState()) {
    _init();
  }

  Future<void> _init() async {
    final prefs = await SharedPreferences.getInstance();
    final mac = prefs.getString(_prefKeyMac);
    final name = prefs.getString(_prefKeyName);
    if (mac != null && name != null) {
      state = state.copyWith(savedDevice: PrinterDevice(name: name, address: mac));
    }

    // Check current connection status
    try {
      final connected = await PrintBluetoothThermal.connectionStatus;
      if (mounted) {
        state = state.copyWith(isConnected: connected);
      }
    } catch (_) {}
  }

  Future<bool> _requestPermissions() async {
    if (!Platform.isAndroid) return true;
    final statuses = await [
      Permission.bluetoothScan,
      Permission.bluetoothConnect,
      Permission.locationWhenInUse,
    ].request();
    final denied = statuses.entries
        .where((e) => !e.value.isGranted)
        .map((e) => e.key.toString())
        .toList();
    if (denied.isNotEmpty) {
      state = state.copyWith(
        isScanning: false,
        error: 'Izin Bluetooth/Lokasi ditolak. Aktifkan di Pengaturan HP.',
      );
      return false;
    }
    return true;
  }

  Future<void> startScan() async {
    state = state.copyWith(isScanning: true, scanResults: [], clearError: true);

    if (!await _requestPermissions()) return;

    // Check Bluetooth enabled
    try {
      final btEnabled = await PrintBluetoothThermal.bluetoothEnabled;
      if (!btEnabled) {
        if (mounted) {
          state = state.copyWith(
            isScanning: false,
            error: 'Bluetooth belum aktif. Nyalakan Bluetooth di Pengaturan HP.',
          );
        }
        return;
      }
    } catch (_) {}

    try {
      final devices = await PrintBluetoothThermal.pairedBluetooths;
      if (mounted) {
        state = state.copyWith(
          scanResults: devices,
          isScanning: false,
        );
      }
    } catch (e) {
      if (mounted) {
        state = state.copyWith(isScanning: false, error: 'Gagal scan Bluetooth: $e');
      }
    }
  }

  Future<void> stopScan() async {
    if (mounted) {
      state = state.copyWith(isScanning: false);
    }
  }

  Future<bool> connect(BluetoothInfo device) async {
    state = state.copyWith(clearError: true);
    try {
      final ok = await PrintBluetoothThermal.connect(macPrinterAddress: device.macAdress);
      if (ok) {
        final prefs = await SharedPreferences.getInstance();
        await prefs.setString(_prefKeyMac, device.macAdress);
        await prefs.setString(_prefKeyName, device.name);
        state = state.copyWith(
          savedDevice: PrinterDevice(name: device.name, address: device.macAdress),
          isConnected: true,
        );
        return true;
      } else {
        state = state.copyWith(error: 'Gagal terhubung ke ${device.name}');
        return false;
      }
    } catch (e) {
      state = state.copyWith(error: 'Gagal terhubung: $e');
      return false;
    }
  }

  Future<void> disconnect() async {
    try {
      await PrintBluetoothThermal.disconnect;
    } catch (_) {}
    state = state.copyWith(isConnected: false);
  }

  /// Auto-connect to saved printer
  Future<bool> autoConnect() async {
    if (state.savedDevice == null) return false;
    try {
      final connected = await PrintBluetoothThermal.connectionStatus;
      if (connected) {
        state = state.copyWith(isConnected: true);
        return true;
      }
      final ok = await PrintBluetoothThermal.connect(
        macPrinterAddress: state.savedDevice!.address,
      );
      if (ok) {
        state = state.copyWith(isConnected: true);
        return true;
      }
    } catch (_) {}
    return false;
  }

  /// Print bytes ke printer. Async lock via `state.isPrinting` biar dua
  /// perintah simultan (misal auto-print + manual tap) gak clash → struk
  /// kepotong atau printer stuck. Kalau lagi sibuk, return `false` dan
  /// set `state.error = 'Printer masih sibuk, tunggu sebentar'` biar
  /// caller bisa tampilin snackbar yang tepat.
  ///
  /// Kembalian `bool` dipertahankan untuk backward compat dengan caller
  /// existing. Caller yang butuh bedain "busy" dari "failed" bisa pake
  /// [printBytesWithOutcome] atau baca `state.error` setelah call.
  Future<bool> printBytes(Uint8List bytes) async {
    final outcome = await printBytesWithOutcome(bytes);
    return outcome == PrintOutcome.success;
  }

  /// Versi printBytes yang return enum untuk handling granular.
  Future<PrintOutcome> printBytesWithOutcome(Uint8List bytes) async {
    // Async lock: reject overlap request — mencegah dua writeBytes
    // concurrent yang bikin struk tercampur atau printer stuck.
    if (state.isPrinting) {
      state = state.copyWith(error: 'Printer masih sibuk, tunggu sebentar');
      return PrintOutcome.busy;
    }

    state = state.copyWith(isPrinting: true, clearError: true);
    try {
      if (!state.isConnected) {
        final reconnected = await autoConnect();
        if (!reconnected) {
          state = state.copyWith(error: 'Printer belum terhubung');
          return PrintOutcome.notConnected;
        }
      }
      // Batch #18 Rule #2: hard timeout 15 detik. Printer hardware hang
      // (firmware bug + paper jam) bisa bikin writeBytes Future never resolve
      // → isPrinting stuck true seumur app lifecycle. Dengan timeout,
      // `TimeoutException` jatuh ke outer catch → finally release lock,
      // user bisa retry atau disconnect manual.
      final result = await PrintBluetoothThermal.writeBytes(bytes)
          .timeout(
        const Duration(seconds: 15),
        onTimeout: () {
          state = state.copyWith(
            error: 'Printer tidak merespons (>15 detik). Cek kabel/paper.',
          );
          return false;
        },
      );
      return result ? PrintOutcome.success : PrintOutcome.failed;
    } catch (e) {
      state = state.copyWith(error: 'Gagal cetak: $e');
      return PrintOutcome.failed;
    } finally {
      // ALWAYS release lock — ensure gak pernah stuck isPrinting=true
      state = state.copyWith(isPrinting: false);
    }
  }

  void clearError() => state = state.copyWith(clearError: true);
}

final printerProvider = StateNotifierProvider<PrinterNotifier, PrinterState>(
  (_) => PrinterNotifier(),
);

// ─── ESC/POS Receipt Builder ────────────────────────────────────────────────

class EscPos {
  static const int _lf = 0x0A;

  static const List<int> init = [0x1B, 0x40];
  static const List<int> alignLeft = [0x1B, 0x61, 0x00];
  static const List<int> alignCenter = [0x1B, 0x61, 0x01];
  static const List<int> alignRight = [0x1B, 0x61, 0x02];
  static const List<int> boldOn = [0x1B, 0x45, 0x01];
  static const List<int> boldOff = [0x1B, 0x45, 0x00];
  static const List<int> fontBig = [0x1D, 0x21, 0x11];
  static const List<int> fontNormal = [0x1D, 0x21, 0x00];
  static const List<int> cut = [0x1D, 0x56, 0x42, 0x03];
  static const List<int> feedLines3 = [_lf, _lf, _lf];

  static List<int> text(String s) => s.codeUnits;
  static List<int> line(String s) => [...s.codeUnits, _lf];

  static List<int> divider({int width = 32}) =>
      List.filled(width, '-'.codeUnitAt(0))..add(_lf);

  static List<int> rowLR(String label, String value, {int width = 32}) {
    final space = width - label.length - value.length;
    final row = space > 0
        ? '$label${' ' * space}$value'
        : '$label $value';
    return line(row);
  }
}

class ReceiptData {
  final String outletName;
  final String outletAddress;
  final String orderNumber;
  final String dateTime;
  final List<ReceiptLineItem> items;
  final double subtotal;
  final double? tax;
  final double? serviceCharge;
  final double total;
  final String paymentMethod;
  final double amountPaid;
  final double changeAmount;
  final String? taxNumber;
  final String? customFooter;

  const ReceiptData({
    required this.outletName,
    required this.outletAddress,
    required this.orderNumber,
    required this.dateTime,
    required this.items,
    required this.subtotal,
    this.tax,
    this.serviceCharge,
    required this.total,
    required this.paymentMethod,
    required this.amountPaid,
    required this.changeAmount,
    this.taxNumber,
    this.customFooter,
  });
}

class ReceiptLineItem {
  final String name;
  final int qty;
  final double price;
  final String? notes;
  const ReceiptLineItem({required this.name, required this.qty, required this.price, this.notes});
  double get subtotal => qty * price;
}

extension ReceiptDataJson on ReceiptData {
  static ReceiptData fromJson(Map<String, dynamic> j) {
    final itemsRaw = (j['items'] as List?) ?? const [];
    final items = itemsRaw.map((e) {
      final m = Map<String, dynamic>.from(e as Map);
      return ReceiptLineItem(
        name: (m['name'] ?? 'Item').toString(),
        qty: (m['qty'] as num?)?.toInt() ?? 1,
        price: (m['price'] as num?)?.toDouble() ?? 0,
        notes: m['notes']?.toString(),
      );
    }).toList();
    return ReceiptData(
      outletName: (j['outlet_name'] ?? 'Kasira').toString(),
      outletAddress: (j['outlet_address'] ?? '').toString(),
      orderNumber: (j['order_number'] ?? '').toString(),
      dateTime: (j['date_time'] ?? '').toString(),
      items: items,
      subtotal: (j['subtotal'] as num?)?.toDouble() ?? 0,
      serviceCharge: (j['service_charge'] as num?)?.toDouble(),
      tax: (j['tax'] as num?)?.toDouble(),
      total: (j['total'] as num?)?.toDouble() ?? 0,
      paymentMethod: (j['payment_method'] ?? 'Tunai').toString(),
      amountPaid: (j['amount_paid'] as num?)?.toDouble() ?? 0,
      changeAmount: (j['change_amount'] as num?)?.toDouble() ?? 0,
      taxNumber: j['tax_number']?.toString(),
      customFooter: j['custom_footer']?.toString(),
    );
  }
}

class SplitReceiptData {
  final String outletName;
  final String outletAddress;
  final String? taxNumber;
  final String? customFooter;
  final String dateTime;
  final String tabNumber;
  final double tabTotal;
  final String splitLabel;
  final double splitAmount;
  final int splitPosition;
  final int splitTotalCount;
  final String paymentMethod;
  final double amountPaid;
  final double changeAmount;
  final bool isTabPaid;
  final double outstandingAmount;
  final int outstandingCount;

  const SplitReceiptData({
    required this.outletName,
    required this.outletAddress,
    this.taxNumber,
    this.customFooter,
    required this.dateTime,
    required this.tabNumber,
    required this.tabTotal,
    required this.splitLabel,
    required this.splitAmount,
    required this.splitPosition,
    required this.splitTotalCount,
    required this.paymentMethod,
    required this.amountPaid,
    required this.changeAmount,
    required this.isTabPaid,
    required this.outstandingAmount,
    required this.outstandingCount,
  });

  static SplitReceiptData fromJson(Map<String, dynamic> j) {
    return SplitReceiptData(
      outletName: (j['outlet_name'] ?? 'Kasira').toString(),
      outletAddress: (j['outlet_address'] ?? '').toString(),
      taxNumber: j['tax_number']?.toString(),
      customFooter: j['custom_footer']?.toString(),
      dateTime: (j['date_time'] ?? '').toString(),
      tabNumber: (j['tab_number'] ?? '').toString(),
      tabTotal: (j['tab_total'] as num?)?.toDouble() ?? 0,
      splitLabel: (j['split_label'] ?? 'Patungan').toString(),
      splitAmount: (j['split_amount'] as num?)?.toDouble() ?? 0,
      splitPosition: (j['split_position'] as num?)?.toInt() ?? 1,
      splitTotalCount: (j['split_total_count'] as num?)?.toInt() ?? 1,
      paymentMethod: (j['payment_method'] ?? 'Tunai').toString(),
      amountPaid: (j['amount_paid'] as num?)?.toDouble() ?? 0,
      changeAmount: (j['change_amount'] as num?)?.toDouble() ?? 0,
      isTabPaid: (j['is_tab_paid'] as bool?) ?? false,
      outstandingAmount: (j['outstanding_amount'] as num?)?.toDouble() ?? 0,
      outstandingCount: (j['outstanding_count'] as num?)?.toInt() ?? 0,
    );
  }
}

class RefundReceiptData {
  final String outletName;
  final String outletAddress;
  final String originalOrderNumber;
  final String dateTime;
  final double refundAmount;
  final String reason;
  final String? cashierName;
  final String? taxNumber;
  final String? customFooter;

  const RefundReceiptData({
    required this.outletName,
    required this.outletAddress,
    required this.originalOrderNumber,
    required this.dateTime,
    required this.refundAmount,
    required this.reason,
    this.cashierName,
    this.taxNumber,
    this.customFooter,
  });
}

String _rp(double amount) {
  final n = amount.toInt();
  final s = n.toString();
  final buf = StringBuffer('Rp ');
  for (int i = 0; i < s.length; i++) {
    if (i > 0 && (s.length - i) % 3 == 0) buf.write('.');
    buf.write(s[i]);
  }
  return buf.toString();
}

List<String> _wrapWords(String text, int maxWidth) {
  if (text.length <= maxWidth) return [text];
  final words = text.split(' ');
  final lines = <String>[];
  var current = '';
  for (final word in words) {
    if (word.length > maxWidth) {
      if (current.isNotEmpty) {
        lines.add(current);
        current = '';
      }
      var remaining = word;
      while (remaining.length > maxWidth) {
        lines.add(remaining.substring(0, maxWidth));
        remaining = remaining.substring(maxWidth);
      }
      current = remaining;
      continue;
    }
    final next = current.isEmpty ? word : '$current $word';
    if (next.length > maxWidth) {
      lines.add(current);
      current = word;
    } else {
      current = next;
    }
  }
  if (current.isNotEmpty) lines.add(current);
  return lines;
}

Uint8List buildReceipt(ReceiptData d) {
  final bytes = <int>[];
  const w = 32;

  bytes.addAll(EscPos.init);

  // Header
  bytes.addAll(EscPos.alignCenter);
  bytes.addAll(EscPos.boldOn);
  bytes.addAll(EscPos.fontBig);
  bytes.addAll(EscPos.line(d.outletName.toUpperCase()));
  bytes.addAll(EscPos.fontNormal);
  bytes.addAll(EscPos.boldOff);
  bytes.addAll(EscPos.line(d.outletAddress));
  if (d.taxNumber != null && d.taxNumber!.isNotEmpty) {
    bytes.addAll(EscPos.line('NPWP: ${d.taxNumber}'));
  }
  bytes.addAll([0x0A]);

  bytes.addAll(EscPos.alignLeft);
  bytes.addAll(EscPos.divider(width: w));
  bytes.addAll(EscPos.line('No  : #${d.orderNumber}'));
  bytes.addAll(EscPos.line('Tgl : ${d.dateTime}'));
  bytes.addAll(EscPos.divider(width: w));

  // Items — wrap long names to multiple lines instead of truncating
  for (final item in d.items) {
    for (final nameLine in _wrapWords(item.name, w)) {
      bytes.addAll(EscPos.line(nameLine));
    }
    final detail = '  ${item.qty}x${_rp(item.price)}';
    final sub = _rp(item.subtotal);
    bytes.addAll(EscPos.rowLR(detail, sub, width: w));
    if (item.notes != null && item.notes!.trim().isNotEmpty) {
      for (final noteLine in _wrapWords('* ${item.notes!.trim()}', w - 2)) {
        bytes.addAll(EscPos.line('  $noteLine'));
      }
    }
  }

  bytes.addAll(EscPos.divider(width: w));
  bytes.addAll(EscPos.rowLR('Subtotal', _rp(d.subtotal), width: w));
  if (d.serviceCharge != null && d.serviceCharge! > 0) {
    bytes.addAll(EscPos.rowLR('Service', _rp(d.serviceCharge!), width: w));
  }
  if (d.tax != null && d.tax! > 0) {
    bytes.addAll(EscPos.rowLR('Pajak', _rp(d.tax!), width: w));
  }
  bytes.addAll(EscPos.divider(width: w));

  bytes.addAll(EscPos.boldOn);
  bytes.addAll(EscPos.rowLR('TOTAL', _rp(d.total), width: w));
  bytes.addAll(EscPos.boldOff);
  bytes.addAll(EscPos.rowLR('Bayar (${d.paymentMethod})', _rp(d.amountPaid), width: w));
  bytes.addAll(EscPos.rowLR('Kembali', _rp(d.changeAmount > 0 ? d.changeAmount : 0), width: w));

  bytes.addAll(EscPos.divider(width: w));
  bytes.addAll(EscPos.alignCenter);
  bytes.addAll(EscPos.line('Terima kasih!'));
  if (d.customFooter != null && d.customFooter!.trim().isNotEmpty) {
    for (final l in _wrapWords(d.customFooter!.trim(), w)) {
      bytes.addAll(EscPos.line(l));
    }
  } else {
    bytes.addAll(EscPos.line('Powered by Kasira'));
  }
  bytes.addAll(EscPos.feedLines3);
  bytes.addAll(EscPos.cut);

  return Uint8List.fromList(bytes);
}

/// Reprint marker — dipanggil buildReceipt dari data backend/drift untuk cetak ulang.
/// Nambahin flag "CETAK ULANG" di header biar kasir/customer tau ini bukan struk asli.
Uint8List buildReprintReceipt(ReceiptData d) {
  final bytes = <int>[];
  bytes.addAll(EscPos.init);
  bytes.addAll(EscPos.alignCenter);
  bytes.addAll(EscPos.boldOn);
  bytes.addAll(EscPos.line('*** CETAK ULANG ***'));
  bytes.addAll(EscPos.boldOff);
  bytes.addAll([0x0A]);
  bytes.addAll(buildReceipt(d));
  return Uint8List.fromList(bytes);
}

/// Refund receipt — struk bukti refund untuk customer.
Uint8List buildRefundReceipt(RefundReceiptData d) {
  final bytes = <int>[];
  const w = 32;

  bytes.addAll(EscPos.init);

  // Header
  bytes.addAll(EscPos.alignCenter);
  bytes.addAll(EscPos.boldOn);
  bytes.addAll(EscPos.fontBig);
  bytes.addAll(EscPos.line(d.outletName.toUpperCase()));
  bytes.addAll(EscPos.fontNormal);
  bytes.addAll(EscPos.boldOff);
  if (d.outletAddress.isNotEmpty) {
    bytes.addAll(EscPos.line(d.outletAddress));
  }
  if (d.taxNumber != null && d.taxNumber!.isNotEmpty) {
    bytes.addAll(EscPos.line('NPWP: ${d.taxNumber}'));
  }
  bytes.addAll([0x0A]);

  // REFUND banner
  bytes.addAll(EscPos.boldOn);
  bytes.addAll(EscPos.fontBig);
  bytes.addAll(EscPos.line('*** REFUND ***'));
  bytes.addAll(EscPos.fontNormal);
  bytes.addAll(EscPos.boldOff);
  bytes.addAll([0x0A]);

  // Info
  bytes.addAll(EscPos.alignLeft);
  bytes.addAll(EscPos.divider(width: w));
  bytes.addAll(EscPos.line('Order: #${d.originalOrderNumber}'));
  bytes.addAll(EscPos.line('Tgl  : ${d.dateTime}'));
  if (d.cashierName != null && d.cashierName!.isNotEmpty) {
    bytes.addAll(EscPos.line('Kasir: ${d.cashierName}'));
  }
  bytes.addAll(EscPos.divider(width: w));

  // Alasan refund — wrap kalau panjang
  bytes.addAll(EscPos.line('Alasan:'));
  for (final l in _wrapWords(d.reason, w)) {
    bytes.addAll(EscPos.line(l));
  }
  bytes.addAll(EscPos.divider(width: w));

  // Jumlah refund
  bytes.addAll(EscPos.boldOn);
  bytes.addAll(EscPos.rowLR('REFUND', _rp(d.refundAmount), width: w));
  bytes.addAll(EscPos.boldOff);
  bytes.addAll(EscPos.divider(width: w));

  // Footer
  bytes.addAll(EscPos.alignCenter);
  bytes.addAll(EscPos.line('Simpan struk ini'));
  bytes.addAll(EscPos.line('sebagai bukti refund'));
  bytes.addAll([0x0A]);
  if (d.customFooter != null && d.customFooter!.trim().isNotEmpty) {
    for (final l in _wrapWords(d.customFooter!.trim(), w)) {
      bytes.addAll(EscPos.line(l));
    }
  } else {
    bytes.addAll(EscPos.line('Powered by Kasira'));
  }
  bytes.addAll(EscPos.feedLines3);
  bytes.addAll(EscPos.cut);

  return Uint8List.fromList(bytes);
}

/// Items receipt data — struk untuk pay-items ad-hoc (warkop pattern).
class ItemsReceiptData {
  final String outletName;
  final String outletAddress;
  final String? taxNumber;
  final String? customFooter;
  final String dateTime;
  final String tabNumber;
  final List<ReceiptLineItem> items;
  final double itemsSubtotal;
  final double tax;
  final double serviceCharge;
  final double total;
  final String paymentMethod;
  final double amountPaid;
  final double changeAmount;
  final bool isTabPaid;
  final double outstandingAmount;
  final int outstandingItemCount;

  const ItemsReceiptData({
    required this.outletName,
    required this.outletAddress,
    this.taxNumber,
    this.customFooter,
    required this.dateTime,
    required this.tabNumber,
    required this.items,
    required this.itemsSubtotal,
    required this.tax,
    required this.serviceCharge,
    required this.total,
    required this.paymentMethod,
    required this.amountPaid,
    required this.changeAmount,
    required this.isTabPaid,
    required this.outstandingAmount,
    required this.outstandingItemCount,
  });

  static ItemsReceiptData fromJson(Map<String, dynamic> j, {required String tabNumber, required bool isTabPaid, required double outstandingAmount, required int outstandingItemCount}) {
    final itemsRaw = (j['items'] as List?) ?? const [];
    final items = itemsRaw.map((e) {
      final m = Map<String, dynamic>.from(e as Map);
      return ReceiptLineItem(
        name: (m['name'] ?? 'Item').toString(),
        qty: (m['qty'] as num?)?.toInt() ?? 1,
        price: (m['price'] as num?)?.toDouble() ?? 0,
        notes: m['notes']?.toString(),
      );
    }).toList();
    return ItemsReceiptData(
      outletName: (j['outlet_name'] ?? 'Kasira').toString(),
      outletAddress: (j['outlet_address'] ?? '').toString(),
      taxNumber: j['tax_number']?.toString(),
      customFooter: j['custom_footer']?.toString(),
      dateTime: (j['date_time'] ?? '').toString(),
      tabNumber: tabNumber,
      items: items,
      itemsSubtotal: (j['subtotal'] as num?)?.toDouble() ?? 0,
      tax: (j['tax'] as num?)?.toDouble() ?? 0,
      serviceCharge: (j['service_charge'] as num?)?.toDouble() ?? 0,
      total: (j['total'] as num?)?.toDouble() ?? 0,
      paymentMethod: (j['payment_method'] ?? 'Tunai').toString(),
      amountPaid: (j['amount_paid'] as num?)?.toDouble() ?? 0,
      changeAmount: (j['change_amount'] as num?)?.toDouble() ?? 0,
      isTabPaid: isTabPaid,
      outstandingAmount: outstandingAmount,
      outstandingItemCount: outstandingItemCount,
    );
  }
}

/// Items receipt — struk untuk customer yg bayar items spesifik (warkop pattern).
/// Banner "PEMBAYARAN PESANAN" + list items dipay + footer outstanding info.
Uint8List buildItemsReceipt(ItemsReceiptData d) {
  final bytes = <int>[];
  const w = 32;

  bytes.addAll(EscPos.init);

  bytes.addAll(EscPos.alignCenter);
  bytes.addAll(EscPos.boldOn);
  bytes.addAll(EscPos.fontBig);
  bytes.addAll(EscPos.line(d.outletName.toUpperCase()));
  bytes.addAll(EscPos.fontNormal);
  bytes.addAll(EscPos.boldOff);
  if (d.outletAddress.isNotEmpty) {
    bytes.addAll(EscPos.line(d.outletAddress));
  }
  if (d.taxNumber != null && d.taxNumber!.isNotEmpty) {
    bytes.addAll(EscPos.line('NPWP: ${d.taxNumber}'));
  }
  bytes.addAll([0x0A]);

  bytes.addAll(EscPos.boldOn);
  bytes.addAll(EscPos.line('*** PEMBAYARAN PESANAN ***'));
  bytes.addAll(EscPos.boldOff);
  bytes.addAll([0x0A]);

  bytes.addAll(EscPos.alignLeft);
  bytes.addAll(EscPos.divider(width: w));
  bytes.addAll(EscPos.line('Tab : ${d.tabNumber}'));
  bytes.addAll(EscPos.line('Tgl : ${d.dateTime}'));
  bytes.addAll(EscPos.divider(width: w));

  // Items
  for (final item in d.items) {
    for (final nameLine in _wrapWords(item.name, w)) {
      bytes.addAll(EscPos.line(nameLine));
    }
    bytes.addAll(EscPos.rowLR(
      '  ${item.qty} x ${_rp(item.price)}',
      _rp(item.subtotal),
      width: w,
    ));
    if (item.notes != null && item.notes!.isNotEmpty) {
      for (final l in _wrapWords('  ${item.notes!}', w)) {
        bytes.addAll(EscPos.line(l));
      }
    }
  }
  bytes.addAll(EscPos.divider(width: w));

  // Totals
  bytes.addAll(EscPos.rowLR('Subtotal', _rp(d.itemsSubtotal), width: w));
  if (d.tax > 0) bytes.addAll(EscPos.rowLR('Pajak', _rp(d.tax), width: w));
  if (d.serviceCharge > 0) bytes.addAll(EscPos.rowLR('Service', _rp(d.serviceCharge), width: w));
  bytes.addAll(EscPos.divider(width: w));

  bytes.addAll(EscPos.boldOn);
  bytes.addAll(EscPos.rowLR('TOTAL', _rp(d.total), width: w));
  bytes.addAll(EscPos.boldOff);
  bytes.addAll(EscPos.line('Metode : ${d.paymentMethod}'));
  if (d.paymentMethod == 'Tunai') {
    bytes.addAll(EscPos.rowLR('Dibayar', _rp(d.amountPaid), width: w));
    if (d.changeAmount > 0) {
      bytes.addAll(EscPos.rowLR('Kembali', _rp(d.changeAmount), width: w));
    }
  }
  bytes.addAll(EscPos.divider(width: w));

  // Footer outstanding info
  bytes.addAll(EscPos.alignCenter);
  if (d.isTabPaid) {
    bytes.addAll(EscPos.boldOn);
    bytes.addAll(EscPos.line('*** SEMUA SUDAH LUNAS ***'));
    bytes.addAll(EscPos.boldOff);
    bytes.addAll(EscPos.line('Terima kasih atas kunjungan Anda'));
  } else {
    final itemText = d.outstandingItemCount == 1 ? '1 item lagi' : '${d.outstandingItemCount} item lagi';
    bytes.addAll(EscPos.line('Sisa pesanan di meja: $itemText'));
    bytes.addAll(EscPos.line('Total sisa: ${_rp(d.outstandingAmount)}'));
  }
  bytes.addAll([0x0A]);

  if (d.customFooter != null && d.customFooter!.trim().isNotEmpty) {
    for (final l in _wrapWords(d.customFooter!.trim(), w)) {
      bytes.addAll(EscPos.line(l));
    }
  } else {
    bytes.addAll(EscPos.line('Powered by Kasira'));
  }
  bytes.addAll(EscPos.feedLines3);
  bytes.addAll(EscPos.cut);

  return Uint8List.fromList(bytes);
}

/// Split receipt — struk per orang yg bayar patungan.
/// Banner "BAYAR PATUNGAN" + "Tamu X dari N", footer "Bill belum lunas, Y orang lagi"
/// atau "Bill SUDAH LUNAS" kalau split terakhir close tab.
Uint8List buildSplitReceipt(SplitReceiptData d) {
  final bytes = <int>[];
  const w = 32;

  bytes.addAll(EscPos.init);

  bytes.addAll(EscPos.alignCenter);
  bytes.addAll(EscPos.boldOn);
  bytes.addAll(EscPos.fontBig);
  bytes.addAll(EscPos.line(d.outletName.toUpperCase()));
  bytes.addAll(EscPos.fontNormal);
  bytes.addAll(EscPos.boldOff);
  if (d.outletAddress.isNotEmpty) {
    bytes.addAll(EscPos.line(d.outletAddress));
  }
  if (d.taxNumber != null && d.taxNumber!.isNotEmpty) {
    bytes.addAll(EscPos.line('NPWP: ${d.taxNumber}'));
  }
  bytes.addAll([0x0A]);

  bytes.addAll(EscPos.boldOn);
  bytes.addAll(EscPos.line('*** BAYAR PATUNGAN ***'));
  bytes.addAll(EscPos.boldOff);
  bytes.addAll(EscPos.line('${d.splitLabel} (${d.splitPosition} dari ${d.splitTotalCount})'));
  bytes.addAll([0x0A]);

  bytes.addAll(EscPos.alignLeft);
  bytes.addAll(EscPos.divider(width: w));
  bytes.addAll(EscPos.line('Tab : ${d.tabNumber}'));
  bytes.addAll(EscPos.line('Tgl : ${d.dateTime}'));
  bytes.addAll(EscPos.divider(width: w));

  bytes.addAll(EscPos.rowLR('Total Bill', _rp(d.tabTotal), width: w));
  bytes.addAll(EscPos.divider(width: w));

  bytes.addAll(EscPos.boldOn);
  bytes.addAll(EscPos.rowLR('BAGIAN ANDA', _rp(d.splitAmount), width: w));
  bytes.addAll(EscPos.boldOff);
  bytes.addAll(EscPos.line('Metode : ${d.paymentMethod}'));
  if (d.paymentMethod == 'Tunai') {
    bytes.addAll(EscPos.rowLR('Dibayar', _rp(d.amountPaid), width: w));
    if (d.changeAmount > 0) {
      bytes.addAll(EscPos.rowLR('Kembali', _rp(d.changeAmount), width: w));
    }
  }
  bytes.addAll(EscPos.divider(width: w));

  bytes.addAll(EscPos.alignCenter);
  if (d.isTabPaid) {
    bytes.addAll(EscPos.boldOn);
    bytes.addAll(EscPos.line('*** BILL SUDAH LUNAS ***'));
    bytes.addAll(EscPos.boldOff);
    bytes.addAll(EscPos.line('Terima kasih atas kunjungan Anda'));
  } else {
    final orangText = d.outstandingCount == 1 ? '1 orang lagi' : '${d.outstandingCount} orang lagi';
    bytes.addAll(EscPos.line('Bill belum lunas — $orangText'));
    bytes.addAll(EscPos.line('Sisa: ${_rp(d.outstandingAmount)}'));
  }
  bytes.addAll([0x0A]);

  if (d.customFooter != null && d.customFooter!.trim().isNotEmpty) {
    for (final l in _wrapWords(d.customFooter!.trim(), w)) {
      bytes.addAll(EscPos.line(l));
    }
  } else {
    bytes.addAll(EscPos.line('Powered by Kasira'));
  }
  bytes.addAll(EscPos.feedLines3);
  bytes.addAll(EscPos.cut);

  return Uint8List.fromList(bytes);
}
