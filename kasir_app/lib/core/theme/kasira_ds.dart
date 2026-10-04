import 'package:flutter/material.dart';

/// Selaris follows Sefrekuensi's warm neutrals, coral and Plus Jakarta Sans.
/// Legacy color names remain aliases so existing POS screens share the theme.
///
/// Use these tokens directly in the redesigned POS widgets — do NOT reach
/// for the legacy [AppColors] (dark emerald) in new screens.
class KasiraDS {
  KasiraDS._();

  // ══════════════════════════ RAW PALETTE ══════════════════════════
  // Brand: GETAR (pink, primary)
  static const pink50 = Color(0xFFF7F5F2);
  static const pink100 = Color(0xFFF3E2DA);
  static const pink200 = Color(0xFFD7B3A5);
  static const pink300 = Color(0xFFB47A67);
  static const pink400 = Color(0xFF99503B);
  static const pink500 = Color(0xFF914C38);
  static const pink600 = Color(0xFF703A2A);
  static const pink700 = Color(0xFF703A2A);
  static const pink800 = Color(0xFF593023);
  static const pink900 = Color(0xFF30241F);

  // Brand: FREKUENSI (violet, secondary)
  static const violet50 = pink50;
  static const violet100 = pink100;
  static const violet200 = pink200;
  static const violet300 = pink300;
  static const violet400 = pink400;
  static const violet500 = pink500;
  static const violet600 = pink600;
  static const violet700 = pink700;
  static const violet800 = pink800;
  static const violet900 = pink900;

  // Accent: HANGAT (coral)
  static const coral300 = Color(0xFFF0C6B7);
  static const coral400 = Color(0xFFE5A08C);
  static const coral500 = Color(0xFFE5A08C);
  static const coral600 = Color(0xFF914C38);

  // Accent: NYALA (neon mint — "online / active")
  static const mint300 = Color(0xFF00704F);
  static const mint400 = Color(0xFF178A5E);
  static const mint500 = Color(0xFF137A53);
  static const mint600 = Color(0xFF137A53);

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
  static const neutral50 = Color(0xFFF7F5F2);
  static const neutral100 = Color(0xFFF0EDE8);
  static const neutral200 = Color(0xFFDCD5CE);
  static const neutral300 = Color(0xFFD0C8BF);
  static const neutral400 = Color(0xFFB0A79D);
  static const neutral500 = Color(0xFF68605B);
  static const neutral600 = Color(0xFF68605B);
  static const neutral700 = Color(0xFF4C4843);
  static const neutral800 = Color(0xFF303135);
  static const neutral900 = Color(0xFF282725);
  static const neutral950 = Color(0xFF121212);

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
  static const controlBorder = Color(0xFF8B8178);

  static const textStrong = neutral900;
  static const textBody = neutral700;
  static const textMuted = neutral500;
  static const textInverse = neutral0;
  static const textOnBrand = Color(0xFFFFFFFF);

  static const brandPrimary = pink500;
  static const brandFill = coral400;
  static const onBrandFill = Color(0xFF30241F);
  static const brandPrimaryHover = pink600;
  static const brandSecondary = violet500;
  static const brandSecondaryHover = violet600;
  static const accentWarm = coral500;
  static const accentNeon = mint500;
  static const brandTint = pink100;
  static const brandTint2 = neutral100;

  static const success = mint600;
  static const warning = amber500;
  static const danger = Color(0xFFB63530);
  static const info = blue500;
  static const focusRing = violet400;

  // Status dots
  static const statusOnline = mint500;
  static const statusAway = amber500;
  static const statusOffline = neutral400;

  // ═══════════════════ SEMANTIC ALIASES — DARK (future toggle) ═══════════════
  static const darkBgBase = neutral950;
  static const darkBgSubtle = Color(0xFF1C1D1F);
  static const darkSurfaceCard = Color(0xFF27282B);
  static const darkSurfaceRaised = Color(0xFF303135);
  static const darkTextStrong = Color(0xFFF2EFEA);
  static const darkTextBody = Color(0xFFDAD5CE);
  static const darkTextMuted = Color(0xFFB5B1AB);
  static const darkBrandPrimary = darkTextStrong;
  static const darkBrandSecondary = coral400;

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
    colors: [pink500, pink500, pink500],
    stops: [0.0, 0.6, 1.0],
  );

  /// 135° tri-stop aurora — logo mark + hero backdrops
  static const gradientAurora = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [pink500, pink500, pink500],
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

  static List<BoxShadow> get shadowXs => [
        BoxShadow(
            color: _sh.withOpacity(0.06),
            blurRadius: 2,
            offset: const Offset(0, 1))
      ];
  static List<BoxShadow> get shadowSm => [
        BoxShadow(
            color: _sh.withOpacity(0.08),
            blurRadius: 6,
            offset: const Offset(0, 2))
      ];
  static List<BoxShadow> get shadowMd => [
        BoxShadow(
            color: _sh.withOpacity(0.10),
            blurRadius: 18,
            offset: const Offset(0, 6))
      ];
  static List<BoxShadow> get shadowLg => [
        BoxShadow(
            color: _sh.withOpacity(0.14),
            blurRadius: 38,
            offset: const Offset(0, 16))
      ];
  static List<BoxShadow> get shadowXl => [
        BoxShadow(
            color: _sh.withOpacity(0.20),
            blurRadius: 64,
            offset: const Offset(0, 28))
      ];

  /// Neon brand glow — under gradient CTAs / active tiles
  static List<BoxShadow> get glowBrand => [];
  static List<BoxShadow> get glowPink => [];
  static List<BoxShadow> get glowViolet => [];

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
      TextStyle(
        fontFamily: 'PlusJakartaSans',
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
      TextStyle(
        fontFamily: 'PlusJakartaSans',
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
      TextStyle(
        fontFamily: 'SpaceMono',
        fontSize: size,
        fontWeight: weight,
        color: color,
        letterSpacing: letterSpacing,
      );

  /// Mono all-caps eyebrow — the "frequency readout" label motif.
  static TextStyle eyebrow({Color color = textMuted}) => TextStyle(
        fontFamily: 'PlusJakartaSans',
        fontSize: 13,
        fontWeight: FontWeight.w700,
        color: color,
        letterSpacing: 0,
      );

  // Type-scale (px): 2xs11 xs12 sm14 base16 md18 lg22 xl28 2xl36 3xl46
}
