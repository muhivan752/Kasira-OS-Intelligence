import 'dart:async';
import 'dart:io';
import 'dart:typed_data';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:bluetooth_print_plus/bluetooth_print_plus.dart';
import 'package:permission_handler/permission_handler.dart';

const _prefKeyMac = 'printer_mac';
const _prefKeyName = 'printer_name';

/// Holds the currently saved/connected printer info
class PrinterDevice {
  final String name;
  final String address;
  const PrinterDevice({required this.name, required this.address});
}

class PrinterState {
  final PrinterDevice? savedDevice;
  final bool isConnected;
  final bool isScanning;
  final List<BluetoothDevice> scanResults;
  final String? error;

  const PrinterState({
    this.savedDevice,
    this.isConnected = false,
    this.isScanning = false,
    this.scanResults = const [],
    this.error,
  });

  PrinterState copyWith({
    PrinterDevice? savedDevice,
    bool? isConnected,
    bool? isScanning,
    List<BluetoothDevice>? scanResults,
    String? error,
    bool clearError = false,
  }) {
    return PrinterState(
      savedDevice: savedDevice ?? this.savedDevice,
      isConnected: isConnected ?? this.isConnected,
      isScanning: isScanning ?? this.isScanning,
      scanResults: scanResults ?? this.scanResults,
      error: clearError ? null : (error ?? this.error),
    );
  }
}

class PrinterNotifier extends StateNotifier<PrinterState> {
  StreamSubscription? _connectSub;
  StreamSubscription? _scanSub;

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

    _connectSub = BluetoothPrintPlus.connectState.listen((s) {
      state = state.copyWith(isConnected: s == ConnectState.connected);
    });
  }

  @override
  void dispose() {
    _connectSub?.cancel();
    _scanSub?.cancel();
    super.dispose();
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
        error: 'Izin Bluetooth/Lokasi ditolak. Aktifkan di Pengaturan.',
      );
      return false;
    }
    return true;
  }

  Future<void> startScan() async {
    state = state.copyWith(isScanning: true, scanResults: [], clearError: true);
    if (!await _requestPermissions()) return;
    try {
      await BluetoothPrintPlus.startScan(timeout: const Duration(seconds: 6));
      _scanSub?.cancel();
      _scanSub = BluetoothPrintPlus.scanResults.listen((devices) {
        state = state.copyWith(scanResults: devices);
      });
    } catch (e) {
      state = state.copyWith(isScanning: false, error: 'Gagal scan: $e');
      return;
    }
    await Future.delayed(const Duration(seconds: 6));
    state = state.copyWith(isScanning: false);
  }

  Future<void> stopScan() async {
    await BluetoothPrintPlus.stopScan();
    state = state.copyWith(isScanning: false);
  }

  Future<bool> connect(BluetoothDevice device) async {
    state = state.copyWith(clearError: true);
    try {
      await BluetoothPrintPlus.connect(device);
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString(_prefKeyMac, device.address ?? '');
      await prefs.setString(_prefKeyName, device.name ?? 'Printer');
      state = state.copyWith(
        savedDevice: PrinterDevice(name: device.name ?? 'Printer', address: device.address ?? ''),
        isConnected: true,
      );
      return true;
    } catch (e) {
      state = state.copyWith(error: 'Gagal terhubung: $e');
      return false;
    }
  }

  Future<void> disconnect() async {
    await BluetoothPrintPlus.disconnect();
    state = state.copyWith(isConnected: false);
  }

  Future<bool> printBytes(Uint8List bytes) async {
    if (!state.isConnected) {
      state = state.copyWith(error: 'Printer belum terhubung');
      return false;
    }
    try {
      await BluetoothPrintPlus.write(bytes);
      return true;
    } catch (e) {
      state = state.copyWith(error: 'Gagal cetak: $e');
      return false;
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
  static const List<int> fontBig = [0x1D, 0x21, 0x11]; // double width + height
  static const List<int> fontNormal = [0x1D, 0x21, 0x00];
  static const List<int> cut = [0x1D, 0x56, 0x42, 0x03];
  static const List<int> feedLines3 = [_lf, _lf, _lf];

  static List<int> text(String s) => s.codeUnits;
  static List<int> line(String s) => [...s.codeUnits, _lf];

  static List<int> divider({int width = 32}) =>
      List.filled(width, '-'.codeUnitAt(0))..add(_lf);

  /// Right-justify value against label in `width` chars
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
  bytes.addAll([0x0A]);

  bytes.addAll(EscPos.alignLeft);
  bytes.addAll(EscPos.divider(width: w));
  bytes.addAll(EscPos.line('No  : #${d.orderNumber}'));
  bytes.addAll(EscPos.line('Tgl : ${d.dateTime}'));
  bytes.addAll(EscPos.divider(width: w));

  // Items
  for (final item in d.items) {
    // item name (truncate if too long)
    final name = item.name.length > w ? item.name.substring(0, w) : item.name;
    bytes.addAll(EscPos.line(name));
    // qty x price = subtotal
    final detail = '  ${item.qty}x${_rp(item.price)}';
    final sub = _rp(item.subtotal);
    bytes.addAll(EscPos.rowLR(detail, sub, width: w));
    if (item.notes != null) {
      bytes.addAll(EscPos.line('  *${item.notes}'));
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
  bytes.addAll(EscPos.line('Powered by Kasira'));
  bytes.addAll(EscPos.feedLines3);
  bytes.addAll(EscPos.cut);

  return Uint8List.fromList(bytes);
}
