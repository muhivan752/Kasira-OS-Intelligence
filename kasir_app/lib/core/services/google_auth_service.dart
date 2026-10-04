import 'package:firebase_auth/firebase_auth.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:flutter/services.dart';
import 'package:google_sign_in/google_sign_in.dart';

class GoogleAuthFailure implements Exception {
  const GoogleAuthFailure(this.message);
  final String message;
}

class GoogleAuthService {
  static Future<void>? _initializing;

  static bool get configured => Firebase.apps.isNotEmpty;

  static Future<bool> available() async {
    try {
      if (!configured) await Firebase.initializeApp();
      return configured;
    } catch (_) {
      return false;
    }
  }

  static Future<String?> idToken() async {
    if (!configured) {
      throw const GoogleAuthFailure(
          'Login Google belum tersedia di versi ini. Gunakan kode Sefrekuensi.');
    }
    try {
      const serverId = String.fromEnvironment('GOOGLE_SERVER_CLIENT_ID');
      _initializing ??= GoogleSignIn.instance
          .initialize(serverClientId: serverId.isEmpty ? null : serverId);
      await _initializing;
      final account = await GoogleSignIn.instance.authenticate();
      final credential = GoogleAuthProvider.credential(
          idToken: account.authentication.idToken);
      final result =
          await FirebaseAuth.instance.signInWithCredential(credential);
      final token = await result.user?.getIdToken();
      if (token == null || token.isEmpty)
        throw const GoogleAuthFailure(
            'Google belum dapat dihubungkan. Coba lagi.');
      return token;
    } on GoogleSignInException catch (error) {
      if (error.code == GoogleSignInExceptionCode.canceled) return null;
      throw const GoogleAuthFailure(
          'Login Google gagal. Coba lagi atau gunakan kode Sefrekuensi.');
    } on FirebaseAuthException {
      throw const GoogleAuthFailure(
          'Google belum dapat digunakan. Coba lagi atau gunakan kode Sefrekuensi.');
    } on PlatformException {
      throw const GoogleAuthFailure(
          'Login Google belum siap pada perangkat ini. Gunakan kode Sefrekuensi.');
    }
  }
}
