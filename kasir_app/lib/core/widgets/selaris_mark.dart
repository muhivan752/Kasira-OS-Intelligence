import 'package:flutter/material.dart';

/// Logo Selaris: dua pil miring naik ke kanan (32°), pil atas ungu → pink,
/// pil bawah pink → ungu. Geometri sama dengan `components/ui/logo.tsx` di
/// web dan ikon launcher — satu bentuk di semua permukaan.
///
/// Digambar, bukan PNG, supaya tajam di ukuran berapa pun dan bisa dibikin
/// putih (di atas gradien splash) tanpa aset kedua.
class SelarisMark extends StatelessWidget {
  final double size;

  /// `null` = gradien resmi. Kasih warna (mis. putih) buat versi satu warna.
  final Color? color;

  const SelarisMark({super.key, this.size = 64, this.color});

  static const pink = Color(0xFFFF3D63);
  static const violet = Color(0xFF8A16D6);

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: size,
      height: size,
      child: CustomPaint(painter: _MarkPainter(color)),
    );
  }
}

class _MarkPainter extends CustomPainter {
  final Color? color;
  _MarkPainter(this.color);

  @override
  void paint(Canvas canvas, Size size) {
    final s = size.width / 64; // viewBox 64
    void pill({required Offset center, required Color start, required Color end}) {
      const w = 34.0, h = 13.5;
      final rect = Rect.fromCenter(center: Offset(0, 0), width: w * s, height: h * s);
      final paint = Paint()
        ..shader = color != null
            ? null
            : LinearGradient(colors: [start, end]).createShader(rect)
        ..color = color ?? Colors.white;
      canvas.save();
      canvas.translate(center.dx * s, center.dy * s);
      canvas.rotate(-32 * 3.14159265 / 180);
      canvas.drawRRect(RRect.fromRectAndRadius(rect, Radius.circular(h / 2 * s)), paint);
      canvas.restore();
    }

    pill(center: const Offset(32.5, 18.75), start: SelarisMark.violet, end: SelarisMark.pink);
    pill(center: const Offset(32, 44), start: SelarisMark.pink, end: SelarisMark.violet);
  }

  @override
  bool shouldRepaint(_MarkPainter old) => old.color != color;
}
