import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:google_fonts/google_fonts.dart';
import 'app_colors.dart';
import 'kasira_ds.dart';

class AppTheme {
  /// KASIRA "Aurora" light theme — POS redesign (SEFREKUENSI DS via [KasiraDS]).
  /// Gabarito display + Plus Jakarta body on warm plum-tinted white. Pink→violet
  /// brand. Wired as the POS app theme (main.dart). Dapur app tetap pakai
  /// [darkTheme]/[lightTheme] — jangan campur.
  static ThemeData get auroraTheme {
    final baseText = GoogleFonts.plusJakartaSansTextTheme(ThemeData.light().textTheme);
    TextStyle display(TextStyle s) => GoogleFonts.gabarito(
          textStyle: s,
          color: KasiraDS.textStrong,
          fontWeight: FontWeight.w800,
          letterSpacing: -0.02 * (s.fontSize ?? 20),
        );
    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.light,
      colorScheme: const ColorScheme.light(
        primary: KasiraDS.brandPrimary,
        onPrimary: Colors.white,
        secondary: KasiraDS.brandSecondary,
        onSecondary: Colors.white,
        surface: KasiraDS.surfaceCard,
        onSurface: KasiraDS.textStrong,
        error: KasiraDS.danger,
        onError: Colors.white,
      ),
      scaffoldBackgroundColor: KasiraDS.bgBase,

      appBarTheme: AppBarTheme(
        backgroundColor: KasiraDS.bgBase,
        surfaceTintColor: Colors.transparent,
        elevation: 0,
        systemOverlayStyle: const SystemUiOverlayStyle(
          statusBarColor: Colors.transparent,
          statusBarBrightness: Brightness.light,
          statusBarIconBrightness: Brightness.dark,
          systemNavigationBarColor: KasiraDS.surfaceCard,
          systemNavigationBarIconBrightness: Brightness.dark,
        ),
        titleTextStyle: GoogleFonts.gabarito(
          color: KasiraDS.textStrong,
          fontSize: 20,
          fontWeight: FontWeight.w800,
          letterSpacing: -0.4,
        ),
        iconTheme: const IconThemeData(color: KasiraDS.textStrong),
      ),

      textTheme: baseText.copyWith(
        displayLarge: display(baseText.displayLarge!),
        displayMedium: display(baseText.displayMedium!),
        displaySmall: display(baseText.displaySmall!),
        headlineMedium: display(baseText.headlineMedium!),
        headlineSmall: display(baseText.headlineSmall!),
        titleLarge: display(baseText.titleLarge!),
        titleMedium: GoogleFonts.plusJakartaSans(
            textStyle: baseText.titleMedium, color: KasiraDS.textStrong, fontWeight: FontWeight.w700),
        bodyLarge: GoogleFonts.plusJakartaSans(textStyle: baseText.bodyLarge, color: KasiraDS.textStrong),
        bodyMedium: GoogleFonts.plusJakartaSans(textStyle: baseText.bodyMedium, color: KasiraDS.textBody),
        bodySmall: GoogleFonts.plusJakartaSans(textStyle: baseText.bodySmall, color: KasiraDS.textMuted),
      ),

      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: KasiraDS.brandPrimary,
          foregroundColor: Colors.white,
          elevation: 0,
          shape: RoundedRectangleBorder(borderRadius: KasiraDS.brMd),
          padding: const EdgeInsets.symmetric(vertical: 16, horizontal: 24),
          textStyle: GoogleFonts.plusJakartaSans(fontWeight: FontWeight.w800, fontSize: 15),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: KasiraDS.textStrong,
          side: const BorderSide(color: KasiraDS.borderDefault),
          shape: RoundedRectangleBorder(borderRadius: KasiraDS.brMd),
          padding: const EdgeInsets.symmetric(vertical: 16, horizontal: 24),
          textStyle: GoogleFonts.plusJakartaSans(fontWeight: FontWeight.w700, fontSize: 15),
        ),
      ),
      textButtonTheme: TextButtonThemeData(
        style: TextButton.styleFrom(
          foregroundColor: KasiraDS.brandPrimary,
          textStyle: GoogleFonts.plusJakartaSans(fontWeight: FontWeight.w700, fontSize: 14),
        ),
      ),

      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: KasiraDS.surfaceCard,
        border: OutlineInputBorder(
          borderRadius: KasiraDS.brMd,
          borderSide: const BorderSide(color: KasiraDS.borderDefault, width: 1.5),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: KasiraDS.brMd,
          borderSide: const BorderSide(color: KasiraDS.borderDefault, width: 1.5),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: KasiraDS.brMd,
          borderSide: const BorderSide(color: KasiraDS.brandPrimary, width: 2),
        ),
        errorBorder: OutlineInputBorder(
          borderRadius: KasiraDS.brMd,
          borderSide: const BorderSide(color: KasiraDS.danger),
        ),
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 15),
        hintStyle: GoogleFonts.plusJakartaSans(color: KasiraDS.textMuted),
        labelStyle: GoogleFonts.plusJakartaSans(color: KasiraDS.textMuted),
      ),

      cardTheme: CardThemeData(
        color: KasiraDS.surfaceCard,
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: KasiraDS.brLg,
          side: const BorderSide(color: KasiraDS.borderSubtle),
        ),
        margin: EdgeInsets.zero,
      ),

      bottomNavigationBarTheme: BottomNavigationBarThemeData(
        backgroundColor: KasiraDS.surfaceCard,
        selectedItemColor: KasiraDS.brandPrimary,
        unselectedItemColor: KasiraDS.textMuted,
        type: BottomNavigationBarType.fixed,
        elevation: 0,
        selectedLabelStyle: GoogleFonts.plusJakartaSans(fontSize: 11, fontWeight: FontWeight.w800),
        unselectedLabelStyle: GoogleFonts.plusJakartaSans(fontSize: 11, fontWeight: FontWeight.w600),
      ),

      dividerTheme: const DividerThemeData(color: KasiraDS.borderSubtle, thickness: 1),

      dialogTheme: DialogThemeData(
        backgroundColor: KasiraDS.surfaceCard,
        surfaceTintColor: Colors.transparent,
        shape: RoundedRectangleBorder(borderRadius: KasiraDS.brXl),
      ),

      bottomSheetTheme: const BottomSheetThemeData(
        backgroundColor: KasiraDS.surfaceCard,
        surfaceTintColor: Colors.transparent,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.vertical(top: Radius.circular(28)),
        ),
      ),

      snackBarTheme: SnackBarThemeData(
        backgroundColor: KasiraDS.surfaceInverse,
        contentTextStyle: GoogleFonts.plusJakartaSans(color: Colors.white, fontSize: 14),
        shape: RoundedRectangleBorder(borderRadius: KasiraDS.brMd),
        behavior: SnackBarBehavior.floating,
      ),

      tabBarTheme: TabBarThemeData(
        labelColor: KasiraDS.brandPrimary,
        unselectedLabelColor: KasiraDS.textMuted,
        indicatorColor: KasiraDS.brandPrimary,
        dividerColor: KasiraDS.borderSubtle,
        labelStyle: GoogleFonts.plusJakartaSans(fontWeight: FontWeight.w700, fontSize: 14),
        unselectedLabelStyle: GoogleFonts.plusJakartaSans(fontWeight: FontWeight.w600, fontSize: 14),
      ),

      chipTheme: ChipThemeData(
        backgroundColor: KasiraDS.surfaceSunken,
        selectedColor: KasiraDS.brandTint,
        labelStyle: GoogleFonts.plusJakartaSans(color: KasiraDS.textBody, fontSize: 13),
        shape: RoundedRectangleBorder(
          borderRadius: KasiraDS.brSm,
          side: const BorderSide(color: KasiraDS.borderSubtle),
        ),
      ),
    );
  }

  static ThemeData get darkTheme {
    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.dark,
      colorScheme: const ColorScheme.dark(
        primary: AppColors.primary,
        onPrimary: Color(0xFF0B0E14),
        secondary: AppColors.accent,
        onSecondary: Colors.white,
        surface: AppColors.surface,
        onSurface: AppColors.textPrimary,
        error: AppColors.error,
        onError: Colors.white,
      ),
      scaffoldBackgroundColor: AppColors.background,

      // ── Status Bar ──
      appBarTheme: AppBarTheme(
        backgroundColor: AppColors.background,
        surfaceTintColor: Colors.transparent,
        elevation: 0,
        systemOverlayStyle: const SystemUiOverlayStyle(
          statusBarBrightness: Brightness.dark,
          statusBarIconBrightness: Brightness.light,
          systemNavigationBarColor: AppColors.background,
          systemNavigationBarIconBrightness: Brightness.light,
        ),
        titleTextStyle: GoogleFonts.syne(
          color: AppColors.textPrimary,
          fontSize: 20,
          fontWeight: FontWeight.bold,
        ),
        iconTheme: const IconThemeData(color: AppColors.textPrimary),
      ),

      // ── Typography ──
      textTheme: GoogleFonts.interTextTheme(ThemeData.dark().textTheme).copyWith(
        displayLarge: GoogleFonts.syne(
          color: AppColors.textPrimary,
          fontWeight: FontWeight.bold,
        ),
        displayMedium: GoogleFonts.syne(
          color: AppColors.textPrimary,
          fontWeight: FontWeight.bold,
        ),
        displaySmall: GoogleFonts.syne(
          color: AppColors.textPrimary,
          fontWeight: FontWeight.bold,
        ),
        headlineMedium: GoogleFonts.syne(
          color: AppColors.textPrimary,
          fontWeight: FontWeight.w700,
        ),
        titleLarge: GoogleFonts.syne(
          color: AppColors.textPrimary,
          fontWeight: FontWeight.w600,
        ),
        bodyLarge: GoogleFonts.inter(color: AppColors.textPrimary),
        bodyMedium: GoogleFonts.inter(color: AppColors.textSecondary),
        bodySmall: GoogleFonts.inter(color: AppColors.textTertiary),
      ),

      // ── Buttons ──
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: AppColors.primary,
          foregroundColor: const Color(0xFF0B0E14),
          elevation: 0,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(14),
          ),
          padding: const EdgeInsets.symmetric(vertical: 16, horizontal: 24),
          textStyle: GoogleFonts.inter(
            fontWeight: FontWeight.w700,
            fontSize: 15,
          ),
        ),
      ),

      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: AppColors.textPrimary,
          side: const BorderSide(color: AppColors.borderLight),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(14),
          ),
          padding: const EdgeInsets.symmetric(vertical: 16, horizontal: 24),
          textStyle: GoogleFonts.inter(
            fontWeight: FontWeight.w600,
            fontSize: 15,
          ),
        ),
      ),

      textButtonTheme: TextButtonThemeData(
        style: TextButton.styleFrom(
          foregroundColor: AppColors.primary,
          textStyle: GoogleFonts.inter(
            fontWeight: FontWeight.w600,
            fontSize: 14,
          ),
        ),
      ),

      // ── Inputs ──
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: AppColors.surfaceVariant,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: const BorderSide(color: AppColors.border),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: const BorderSide(color: AppColors.border),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: const BorderSide(color: AppColors.primary, width: 2),
        ),
        errorBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: const BorderSide(color: AppColors.error),
        ),
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
        hintStyle: GoogleFonts.inter(color: AppColors.textTertiary),
        labelStyle: GoogleFonts.inter(color: AppColors.textSecondary),
      ),

      // ── Cards ──
      cardTheme: CardThemeData(
        color: AppColors.surface,
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(18),
          side: const BorderSide(color: AppColors.border, width: 0.5),
        ),
        margin: EdgeInsets.zero,
      ),

      // ── Bottom Nav ──
      bottomNavigationBarTheme: BottomNavigationBarThemeData(
        backgroundColor: AppColors.surface,
        selectedItemColor: AppColors.primary,
        unselectedItemColor: AppColors.textTertiary,
        type: BottomNavigationBarType.fixed,
        elevation: 0,
        selectedLabelStyle: GoogleFonts.inter(fontSize: 11, fontWeight: FontWeight.w600),
        unselectedLabelStyle: GoogleFonts.inter(fontSize: 11),
      ),

      // ── Divider ──
      dividerTheme: const DividerThemeData(
        color: AppColors.border,
        thickness: 0.5,
      ),

      // ── Dialog ──
      dialogTheme: DialogThemeData(
        backgroundColor: AppColors.surfaceElevated,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
      ),

      // ── Bottom Sheet ──
      bottomSheetTheme: const BottomSheetThemeData(
        backgroundColor: AppColors.surface,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
        ),
      ),

      // ── Snackbar ──
      snackBarTheme: SnackBarThemeData(
        backgroundColor: AppColors.surfaceElevated,
        contentTextStyle: GoogleFonts.inter(color: AppColors.textPrimary, fontSize: 14),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        behavior: SnackBarBehavior.floating,
      ),

      // ── Tabs ──
      tabBarTheme: TabBarThemeData(
        labelColor: AppColors.primary,
        unselectedLabelColor: AppColors.textTertiary,
        indicatorColor: AppColors.primary,
        dividerColor: AppColors.border,
        labelStyle: GoogleFonts.inter(fontWeight: FontWeight.w600, fontSize: 14),
        unselectedLabelStyle: GoogleFonts.inter(fontWeight: FontWeight.w500, fontSize: 14),
      ),

      // ── Chip ──
      chipTheme: ChipThemeData(
        backgroundColor: AppColors.surfaceVariant,
        selectedColor: AppColors.primary.withOpacity(0.15),
        labelStyle: GoogleFonts.inter(color: AppColors.textSecondary, fontSize: 13),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(10),
          side: const BorderSide(color: AppColors.border),
        ),
      ),
    );
  }

  // Keep reference for backward compat — points to darkTheme
  static ThemeData get lightTheme => darkTheme;
}
