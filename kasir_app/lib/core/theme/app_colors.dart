import 'package:flutter/material.dart';

class AppColors {
  // ── Primary: Emerald Green ──
  static const Color primary = Color(0xFF00D68F);
  static const Color primaryLight = Color(0xFF34EAA8);
  static const Color primaryDark = Color(0xFF00B377);

  // ── Accent: Cool Blue ──
  static const Color accent = Color(0xFF3B82F6);
  static const Color accentLight = Color(0xFF60A5FA);

  // ── Background & Surface (Dark Pro) ──
  static const Color background = Color(0xFF0B0E14);
  static const Color surface = Color(0xFF141820);
  static const Color surfaceVariant = Color(0xFF1C2130);
  static const Color surfaceElevated = Color(0xFF222838);

  // ── Typography ──
  static const Color textPrimary = Color(0xFFF0F2F5);
  static const Color textSecondary = Color(0xFF9CA3AF);
  static const Color textTertiary = Color(0xFF5C6370);

  // ── Semantic ──
  static const Color error = Color(0xFFFF6B6B);
  static const Color success = Color(0xFF00D68F);
  static const Color warning = Color(0xFFFFC857);
  static const Color info = Color(0xFF3B82F6);

  // ── Borders & Dividers ──
  static const Color border = Color(0xFF1F2937);
  static const Color borderLight = Color(0xFF2D3748);

  // ── Gradient Presets (premium feel) ──
  static const LinearGradient primaryGradient = LinearGradient(
    colors: [Color(0xFF00D68F), Color(0xFF3B82F6)],
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
  );

  static const LinearGradient surfaceGradient = LinearGradient(
    colors: [Color(0xFF141820), Color(0xFF1C2130)],
    begin: Alignment.topCenter,
    end: Alignment.bottomCenter,
  );

  static const LinearGradient headerGradient = LinearGradient(
    colors: [Color(0xFF0B0E14), Color(0xFF141820)],
    begin: Alignment.topCenter,
    end: Alignment.bottomCenter,
  );

  // ── Glow / Shadow ──
  static List<BoxShadow> get cardShadow => [
    BoxShadow(
      color: const Color(0xFF00D68F).withOpacity(0.04),
      blurRadius: 20,
      offset: const Offset(0, 4),
    ),
  ];

  static List<BoxShadow> get glowShadow => [
    BoxShadow(
      color: const Color(0xFF00D68F).withOpacity(0.15),
      blurRadius: 24,
      spreadRadius: -4,
      offset: const Offset(0, 4),
    ),
  ];
}
