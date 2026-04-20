/// Normalize Indonesian phone number ke format E.164 (628xxx) sebelum kirim
/// ke backend. Mencegah duplicate customer record gara-gara user ngetik
/// format beda-beda.
///
/// Rules:
///   "081234567890"  -> "6281234567890"
///   "628127...6"    -> "628127...6"  (pass-through)
///   "+62812..."     -> "62812..."
///   "8121234567"    -> "628121234567"  (missing leading 0)
///   "  081 234 ..." -> strip non-digit dulu
///
/// Return null kalau input kosong atau terlalu pendek (< 8 digit) biar caller
/// bisa skip atau throw sesuai context.
String? normalizeIndoPhone(String? raw) {
  if (raw == null) return null;
  // Strip semua non-digit (spasi, tanda hubung, +, dll)
  final digits = raw.replaceAll(RegExp(r'\D'), '');
  if (digits.isEmpty || digits.length < 8) return null;

  if (digits.startsWith('62')) {
    return digits;
  }
  if (digits.startsWith('0')) {
    return '62${digits.substring(1)}';
  }
  if (digits.startsWith('8')) {
    // Common case: user ketik mulai dari 8 tanpa 0 atau 62
    return '62$digits';
  }
  // Fallback: asumsi sudah dalam format nasional, prepend 62
  return '62$digits';
}
