import 'dart:async';
import 'dart:convert';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:http/http.dart' as http;
import '../../../core/config/app_config.dart';
import '../../../core/services/session_cache.dart';

class ChatMessage {
  final String id;
  final String role; // 'user', 'assistant', 'error'
  String content;
  final String? intent;
  final String? model;
  final int? tokens;

  ChatMessage({
    required this.id,
    required this.role,
    required this.content,
    this.intent,
    this.model,
    this.tokens,
  });
}

class AiChatState {
  final List<ChatMessage> messages;
  final bool isLoading;
  final String? error;

  const AiChatState({
    this.messages = const [],
    this.isLoading = false,
    this.error,
  });

  AiChatState copyWith({
    List<ChatMessage>? messages,
    bool? isLoading,
    String? error,
    bool clearError = false,
  }) =>
      AiChatState(
        messages: messages ?? this.messages,
        isLoading: isLoading ?? this.isLoading,
        error: clearError ? null : (error ?? this.error),
      );
}

class AiChatNotifier extends StateNotifier<AiChatState> {
  AiChatNotifier() : super(const AiChatState());

  final _cache = SessionCache.instance;
  StreamSubscription? _streamSub;
  int _msgId = 0;

  String _nextId() => 'msg_${_msgId++}';

  Future<void> sendMessage(String text) async {
    if (text.trim().isEmpty || state.isLoading) return;

    // Add user message
    final userMsg = ChatMessage(id: _nextId(), role: 'user', content: text.trim());
    final assistantMsg = ChatMessage(id: _nextId(), role: 'assistant', content: '');

    state = state.copyWith(
      messages: [...state.messages, userMsg, assistantMsg],
      isLoading: true,
      clearError: true,
    );

    try {
      final token = _cache.accessToken;
      final tenantId = _cache.tenantId;
      final outletId = _cache.outletId;

      if (token == null || outletId == null) {
        _setError(assistantMsg.id, 'Silakan login ulang.');
        return;
      }

      final request = http.Request(
        'POST',
        Uri.parse('${AppConfig.apiV1}/ai/chat'),
      );
      request.headers.addAll({
        'Authorization': 'Bearer $token',
        'Content-Type': 'application/json',
        if (tenantId != null) 'X-Tenant-ID': tenantId,
      });
      request.body = jsonEncode({
        'message': text.trim(),
        'outlet_id': outletId,
      });

      final client = http.Client();
      final response = await client.send(request);

      if (response.statusCode == 403) {
        _setError(assistantMsg.id, 'Fitur AI hanya tersedia untuk paket Pro. Upgrade untuk menggunakan.');
        return;
      }

      if (response.statusCode == 429) {
        _setError(assistantMsg.id, 'Quota AI harian habis. Coba lagi besok atau upgrade ke Business.');
        return;
      }

      if (response.statusCode != 200) {
        _setError(assistantMsg.id, 'Gagal terhubung ke AI (${response.statusCode})');
        return;
      }

      // Parse SSE stream
      final buffer = StringBuffer();
      await for (final chunk in response.stream.transform(utf8.decoder)) {
        final lines = chunk.split('\n');
        for (final line in lines) {
          if (!line.startsWith('data: ')) continue;
          final jsonStr = line.substring(6).trim();
          if (jsonStr.isEmpty) continue;

          try {
            final event = jsonDecode(jsonStr) as Map<String, dynamic>;
            final type = event['type'] as String?;

            if (type == 'chunk') {
              buffer.write(event['content'] ?? '');
              _updateAssistant(assistantMsg.id, buffer.toString());
            } else if (type == 'done') {
              _finalizeAssistant(
                assistantMsg.id,
                buffer.toString(),
                intent: event['intent'] as String?,
                model: event['model'] as String?,
                tokens: event['tokens_used'] as int?,
              );
            } else if (type == 'error') {
              _setError(assistantMsg.id, event['message'] as String? ?? 'AI error');
            }
          } catch (_) {
            // Skip unparseable lines
          }
        }
      }

      client.close();
    } catch (e) {
      _setError(assistantMsg.id, 'Gagal terhubung. Periksa koneksi internet.');
    }
  }

  void _updateAssistant(String msgId, String content) {
    final msgs = state.messages.map((m) {
      if (m.id == msgId) {
        m.content = content;
      }
      return m;
    }).toList();
    state = state.copyWith(messages: msgs, isLoading: true);
  }

  void _finalizeAssistant(String msgId, String content,
      {String? intent, String? model, int? tokens}) {
    final msgs = state.messages.map((m) {
      if (m.id == msgId) {
        return ChatMessage(
          id: m.id,
          role: 'assistant',
          content: content,
          intent: intent,
          model: model,
          tokens: tokens,
        );
      }
      return m;
    }).toList();
    state = state.copyWith(messages: msgs, isLoading: false);
  }

  void _setError(String msgId, String error) {
    final msgs = state.messages.map((m) {
      if (m.id == msgId) {
        return ChatMessage(id: m.id, role: 'error', content: error);
      }
      return m;
    }).toList();
    state = state.copyWith(messages: msgs, isLoading: false, error: error);
  }

  void clearChat() {
    _streamSub?.cancel();
    state = const AiChatState();
  }

  @override
  void dispose() {
    _streamSub?.cancel();
    super.dispose();
  }
}

final aiChatProvider = StateNotifierProvider<AiChatNotifier, AiChatState>((ref) {
  return AiChatNotifier();
});
