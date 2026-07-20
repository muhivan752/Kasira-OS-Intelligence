import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

/// KASIRA "Aurora" Design System — ported 1:1 from the SEFREKUENSI design
/// system (claude.ai/design 629d2b64) used by `Kasira POS.dc.html`.
///
/// Palette: hot-pink → electric-violet on warm plum-tinted neutrals.
/// Light default (the POS redesign is light-mode). Dark aliases included
/// for a future toggle. Fonts: Gabarito (display) · Plus Jakarta Sans
/// (body/UI) · Space Mono (mono eyebrows / numeric readouts).
///
/// Use these tokens directly in the redesigned POS widgets — do NOT reach
/// for the legacy [AppColors] (dark emerald) in new screens.
class KasiraDS {
  KasiraDS._();

  // ══════════════════════════ RAW PALETTE ══════════════════════════
  // Brand: GETAR (pink, primary)
  static const pink50 = Color(0xFFFFF0F6);
  static const pink100 = Color(0xFFFFE0EC);
  static const pink200 = Color(0xFFFFB8D2);
  static const pink300 = Color(0xFFFF8AB6);
  static const pink400 = Color(0xFFFF5C97);
  static const pink500 = Color(0xFFFF2E7E); // base
  static const pink600 = Color(0xFFED1268);
  static const pink700 = Color(0xFFC70A55);
  static const pink800 = Color(0xFF9E0944);
  static const pink900 = Color(0xFF7A0B38);

  // Brand: FREKUENSI (violet, secondary)
  static const violet50 = Color(0xFFF4EEFE);
  static const violet100 = Color(0xFFE9DEFD);
  static const violet200 = Color(0xFFD0BAFB);
  static const violet300 = Color(0xFFB492F6);
  static const violet400 = Color(0xFF9966EF);
  static const violet500 = Color(0xFF7C3AED); // base
  static const violet600 = Color(0xFF6A28D9);
  static const violet700 = Color(0xFF561FB5);
  static const violet800 = Color(0xFF441A8E);
  static const violet900 = Color(0xFF34176C);

  // Accent: HANGAT (coral)
  static const coral300 = Color(0xFFFFB59B);
  static const coral400 = Color(0xFFFF9466);
  static const coral500 = Color(0xFFFF7A4D);
  static const coral600 = Color(0xFFF2602F);

  // Accent: NYALA (neon mint — "online / active")
  static const mint300 = Color(0xFF7DF5CE);
  static const mint400 = Color(0xFF3DF0B5);
  static const mint500 = Color(0xFF12E0A0);
  static const mint600 = Color(0xFF06B884);

  // Support hues
  static const amber400 = Color(0xFFFFC24B);
  static const amber500 = Color(0xFFFFB23E);
  static const red400 = Color(0xFFFF6B6B);
  static const red500 = Color(0xFFFB4D4D);
  static const red600 = Color(0xFFE23030);
  static const blue400 = Color(0xFF5C9DFF);
  static const blue500 = Color(0xFF3A86FF);

  // Neutrals: warm plum-tinted ramp
  static const neutral0 = Color(0xFFFFFFFF);
  static const neutral50 = Color(0xFFFCF7FB);
  static const neutral100 = Color(0xFFF6EEF4);
  static const neutral200 = Color(0xFFECE0EA);
  static const neutral300 = Color(0xFFDCCBD8);
  static const neutral400 = Color(0xFFBCA8B8);
  static const neutral500 = Color(0xFF927E8F);
  static const neutral600 = Color(0xFF6B596A);
  static const neutral700 = Color(0xFF4C3E4F);
  static const neutral800 = Color(0xFF2E2436);
  static const neutral900 = Color(0xFF1C1426);
  static const neutral950 = Color(0xFF120B19);

  // ═══════════════════ SEMANTIC ALIASES — LIGHT (default) ═══════════════════
  static const bgBase = neutral50;
  static const bgSubtle = neutral100;
  static const surfaceCard = neutral0;
  static const surfaceRaised = neutral0;
  static const surfaceSunken = neutral100;
  static const surfaceInverse = neutral900;

  static const borderSubtle = neutral200;
  static const borderDefault = neutral300;
  static const borderStrong = neutral400;

  static const textStrong = neutral900;
  static const textBody = neutral700;
  static const textMuted = neutral500;
  static const textInverse = neutral0;
  static const textOnBrand = Color(0xFFFFFFFF);

  static const brandPrimary = pink500;
  static const brandPrimaryHover = pink600;
  static const brandSecondary = violet500;
  static const brandSecondaryHover = violet600;
  static const accentWarm = coral500;
  static const accentNeon = mint500;
  static const brandTint = pink50;
  static const brandTint2 = violet50;

  static const success = mint600;
  static const warning = amber500;
  static const danger = red500;
  static const info = blue500;
  static const focusRing = violet400;

  // Status dots
  static const statusOnline = mint500;
  static const statusAway = amber500;
  static const statusOffline = neutral400;

  // ═══════════════════ SEMANTIC ALIASES — DARK (future toggle) ═══════════════
  static const darkBgBase = neutral950;
  static const darkBgSubtle = Color(0xFF1A1023);
  static const darkSurfaceCard = neutral900;
  static const darkSurfaceRaised = Color(0xFF251A30);
  static const darkTextStrong = Color(0xFFF8F1F6);
  static const darkTextBody = Color(0xFFD7C7D4);
  static const darkTextMuted = Color(0xFF9A879A);
  static const darkBrandPrimary = pink400;
  static const darkBrandSecondary = violet400;

  // ═══════════════════════════ GRADIENTS ═══════════════════════════
  /// pink→violet 120°, the primary brand gradient
  static const gradientFrekuensi = LinearGradient(
    begin: Alignment(-1, -0.3),
    end: Alignment(1, 0.3),
    colors: [pink500, violet500],
  );
  static const gradientFrekuensiSoft = LinearGradient(
    begin: Alignment(-1, -0.3),
    end: Alignment(1, 0.3),
    colors: [pink400, violet400],
  );
  static const gradientHangat = LinearGradient(
    begin: Alignment(-1, -0.3),
    end: Alignment(1, 0.3),
    colors: [coral400, pink500, violet500],
    stops: [0.0, 0.6, 1.0],
  );
  /// 135° tri-stop aurora — logo mark + hero backdrops
  static const gradientAurora = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [Color(0xFFFF2E7E), Color(0xFFC03BE6), Color(0xFF7C3AED)],
    stops: [0.0, 0.45, 1.0],
  );

  // ═══════════════════════════ RADII ═══════════════════════════
  static const double radiusXs = 6;
  static const double radiusSm = 10;
  static const double radiusMd = 14; // default control / input
  static const double radiusLg = 20; // cards
  static const double radiusXl = 28; // sheets / profile cards
  static const double radius2xl = 36;
  static const double radiusPill = 999;

  static BorderRadius get brXs => BorderRadius.circular(radiusXs);
  static BorderRadius get brSm => BorderRadius.circular(radiusSm);
  static BorderRadius get brMd => BorderRadius.circular(radiusMd);
  static BorderRadius get brLg => BorderRadius.circular(radiusLg);
  static BorderRadius get brXl => BorderRadius.circular(radiusXl);
  static BorderRadius get brPill => BorderRadius.circular(radiusPill);

  // ═══════════════════════════ SPACING (4px grid) ═══════════════════════════
  static const double space1 = 4;
  static const double space2 = 8;
  static const double space3 = 12;
  static const double space4 = 16;
  static const double space5 = 20;
  static const double space6 = 24;
  static const double space8 = 32;
  static const double space10 = 40;
  static const double space12 = 48;
  static const double space16 = 64;

  // ═══════════════════════════ SHADOWS (warm plum tint) ═══════════════════════
  static const Color _sh = Color(0xFF2E2436); // rgba(46,36,54)

  static List<BoxShadow> get shadowXs =>
      [BoxShadow(color: _sh.withOpacity(0.06), blurRadius: 2, offset: const Offset(0, 1))];
  static List<BoxShadow> get shadowSm =>
      [BoxShadow(color: _sh.withOpacity(0.08), blurRadius: 6, offset: const Offset(0, 2))];
  static List<BoxShadow> get shadowMd =>
      [BoxShadow(color: _sh.withOpacity(0.10), blurRadius: 18, offset: const Offset(0, 6))];
  static List<BoxShadow> get shadowLg =>
      [BoxShadow(color: _sh.withOpacity(0.14), blurRadius: 38, offset: const Offset(0, 16))];
  static List<BoxShadow> get shadowXl =>
      [BoxShadow(color: _sh.withOpacity(0.20), blurRadius: 64, offset: const Offset(0, 28))];

  /// Neon brand glow — under gradient CTAs / active tiles
  static List<BoxShadow> get glowBrand => [
        BoxShadow(color: pink500.withOpacity(0.28), blurRadius: 34, offset: const Offset(0, 10)),
        BoxShadow(color: violet500.withOpacity(0.24), blurRadius: 14, offset: const Offset(0, 4)),
      ];
  static List<BoxShadow> get glowPink =>
      [BoxShadow(color: pink500.withOpacity(0.40), blurRadius: 30, offset: const Offset(0, 8))];
  static List<BoxShadow> get glowViolet =>
      [BoxShadow(color: violet500.withOpacity(0.40), blurRadius: 30, offset: const Offset(0, 8))];

  // ═══════════════════════════ MOTION ═══════════════════════════
  static const Duration durFast = Duration(milliseconds: 120);
  static const Duration durBase = Duration(milliseconds: 200);
  static const Duration durSlow = Duration(milliseconds: 320);
  static const Curve easeStandard = Cubic(0.2, 0, 0, 1);
  static const Curve easeOut = Cubic(0.16, 1, 0.3, 1);
  static const Curve easeSpring = Cubic(0.34, 1.56, 0.64, 1);
  static const double pressScale = 0.96;

  // ═══════════════════════════ TYPOGRAPHY ═══════════════════════════
  // Families via google_fonts. Display=Gabarito, Sans=Plus Jakarta, Mono=Space Mono.
  static TextStyle display({
    double size = 27,
    FontWeight weight = FontWeight.w800, // extrabold
    Color color = textStrong,
    double height = 1.05,
    double letterSpacing = -0.015 * 27,
  }) =>
      GoogleFonts.gabarito(
        fontSize: size,
        fontWeight: weight,
        color: color,
        height: height,
        letterSpacing: -0.015 * size, // -0.015em
      );

  static TextStyle sans({
    double size = 15,
    FontWeight weight = FontWeight.w500,
    Color color = textBody,
    double? height,
    double? letterSpacing,
  }) =>
      GoogleFonts.plusJakartaSans(
        fontSize: size,
        fontWeight: weight,
        color: color,
        height: height,
        letterSpacing: letterSpacing,
      );

  static TextStyle mono({
    double size = 13,
    FontWeight weight = FontWeight.w400,
    Color color = textBody,
    double letterSpacing = 0,
  }) =>
      GoogleFonts.spaceMono(
        fontSize: size,
        fontWeight: weight,
        color: color,
        letterSpacing: letterSpacing,
      );

  /// Mono all-caps eyebrow — the "frequency readout" label motif.
  static TextStyle eyebrow({Color color = textMuted}) => GoogleFonts.spaceMono(
        fontSize: 11,
        fontWeight: FontWeight.w700,
        color: color,
        letterSpacing: 0.12 * 11, // 0.12em
      );

  // Type-scale (px): 2xs11 xs12 sm14 base16 md18 lg22 xl28 2xl36 3xl46
}
