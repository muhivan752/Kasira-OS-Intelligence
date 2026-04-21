import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:lucide_icons/lucide_icons.dart';
import '../../../../core/theme/app_colors.dart';
import '../../providers/ai_chat_provider.dart';

const _suggestions = [
  'Berapa omzet hari ini?',
  'Produk terlaris minggu ini?',
  'Stok apa yang perlu diisi?',
  'Rata-rata transaksi per hari?',
  'Analisa HPP produk saya',
  'Menu mana yang kurang laku?',
];

class AiChatPage extends ConsumerStatefulWidget {
  const AiChatPage({super.key});

  @override
  ConsumerState<AiChatPage> createState() => _AiChatPageState();
}

class _AiChatPageState extends ConsumerState<AiChatPage> {
  final _controller = TextEditingController();
  final _scrollController = ScrollController();

  void _send() {
    final text = _controller.text.trim();
    if (text.isEmpty) return;
    ref.read(aiChatProvider.notifier).sendMessage(text);
    _controller.clear();
    _scrollToBottom();
  }

  void _scrollToBottom() {
    // Schedule setelah layout selesai — lebih akurat dari Future.delayed 100ms
    // karena maxScrollExtent baru valid setelah ListView rebuild.
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollController.hasClients) {
        _scrollController.animateTo(
          _scrollController.position.maxScrollExtent,
          duration: const Duration(milliseconds: 280),
          curve: Curves.easeOutCubic,
        );
      }
    });
  }

  @override
  void dispose() {
    _controller.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final chat = ref.watch(aiChatProvider);

    // Auto-scroll when new messages
    ref.listen(aiChatProvider, (_, next) {
      if (next.messages.isNotEmpty) _scrollToBottom();
    });

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        backgroundColor: AppColors.surface,
        title: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(6),
              decoration: BoxDecoration(
                color: AppColors.primary.withOpacity(0.15),
                borderRadius: BorderRadius.circular(8),
              ),
              child: const Icon(LucideIcons.bot, color: AppColors.primary, size: 20),
            ),
            const SizedBox(width: 10),
            const Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('AI Asisten', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
                Text('Kasira Intelligence', style: TextStyle(fontSize: 11, color: AppColors.textTertiary)),
              ],
            ),
          ],
        ),
        actions: [
          if (chat.messages.isNotEmpty)
            IconButton(
              onPressed: () => ref.read(aiChatProvider.notifier).clearChat(),
              icon: const Icon(LucideIcons.trash2, size: 18),
              tooltip: 'Hapus Obrolan',
            ),
        ],
      ),
      body: Column(
        children: [
          // Context awareness indicator — muncul saat multi-turn aktif.
          // Visual subtle (tipis, muted) biar gak ganggu flow tapi jelas
          // kasih sinyal "AI inget konteks obrolan sebelumnya".
          if (chat.hasConversationContext && chat.messages.isNotEmpty)
            _ContextAwarenessBanner(),
          // Messages
          Expanded(
            child: chat.messages.isEmpty
                ? _buildWelcome()
                : ListView.builder(
                    controller: _scrollController,
                    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                    itemCount: chat.messages.length,
                    itemBuilder: (_, i) => _MessageBubble(
                      key: ValueKey(chat.messages[i].id),
                      message: chat.messages[i],
                    ),
                  ),
          ),

          // Input
          Container(
            padding: const EdgeInsets.fromLTRB(16, 8, 8, 16),
            decoration: const BoxDecoration(
              color: AppColors.surface,
              border: Border(top: BorderSide(color: AppColors.border)),
            ),
            child: SafeArea(
              top: false,
              child: Row(
                children: [
                  Expanded(
                    child: TextField(
                      controller: _controller,
                      onSubmitted: (_) => _send(),
                      textInputAction: TextInputAction.send,
                      style: const TextStyle(fontSize: 14),
                      decoration: InputDecoration(
                        hintText: 'Tanya sesuatu ke Kasira AI...',
                        hintStyle: const TextStyle(color: AppColors.textTertiary, fontSize: 14),
                        filled: true,
                        fillColor: AppColors.surfaceVariant,
                        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                        border: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(24),
                          borderSide: BorderSide.none,
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(width: 8),
                  Container(
                    decoration: BoxDecoration(
                      color: chat.isLoading ? AppColors.surfaceVariant : AppColors.primary,
                      shape: BoxShape.circle,
                    ),
                    child: IconButton(
                      onPressed: chat.isLoading ? null : _send,
                      icon: chat.isLoading
                          ? const SizedBox(
                              width: 18,
                              height: 18,
                              child: CircularProgressIndicator(strokeWidth: 2, color: AppColors.textSecondary),
                            )
                          : const Icon(LucideIcons.send, size: 18, color: Colors.white),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildWelcome() {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Column(
        children: [
          const SizedBox(height: 40),
          Container(
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(
              color: AppColors.primary.withOpacity(0.1),
              shape: BoxShape.circle,
            ),
            child: const Icon(LucideIcons.bot, size: 48, color: AppColors.primary),
          ),
          const SizedBox(height: 20),
          const Text(
            'Halo! Saya AI Asisten Kasira',
            style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 8),
          const Text(
            'Tanya apa saja tentang bisnis kamu.\nOmzet, stok, produk terlaris, dan lainnya.',
            textAlign: TextAlign.center,
            style: TextStyle(color: AppColors.textSecondary, fontSize: 13),
          ),
          const SizedBox(height: 32),
          const Align(
            alignment: Alignment.centerLeft,
            child: Text('Coba tanya:', style: TextStyle(color: AppColors.textTertiary, fontSize: 12)),
          ),
          const SizedBox(height: 12),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: _suggestions.map((s) => ActionChip(
              label: Text(s, style: const TextStyle(fontSize: 12)),
              backgroundColor: AppColors.surfaceVariant,
              side: const BorderSide(color: AppColors.border),
              onPressed: () {
                _controller.text = s;
                _send();
              },
            )).toList(),
          ),
        ],
      ),
    );
  }
}

class _MessageBubble extends StatelessWidget {
  final ChatMessage message;

  const _MessageBubble({super.key, required this.message});

  @override
  Widget build(BuildContext context) {
    final isUser = message.role == 'user';
    final isError = message.role == 'error';

    // Fade-in subtle (0 → 1 opacity, 220ms easeOut). TweenAnimationBuilder
    // cuma run sekali per widget lifecycle — bubble existing gak re-animate
    // saat parent rebuild (pakai ValueKey di ListView biar identity preserved).
    return TweenAnimationBuilder<double>(
      tween: Tween(begin: 0.0, end: 1.0),
      duration: const Duration(milliseconds: 220),
      curve: Curves.easeOut,
      builder: (_, value, child) => Opacity(opacity: value, child: child),
      child: Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Row(
        mainAxisAlignment: isUser ? MainAxisAlignment.end : MainAxisAlignment.start,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (!isUser) ...[
            Container(
              margin: const EdgeInsets.only(top: 4),
              padding: const EdgeInsets.all(6),
              decoration: BoxDecoration(
                color: isError ? AppColors.error.withOpacity(0.15) : AppColors.primary.withOpacity(0.15),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Icon(
                isError ? LucideIcons.alertCircle : LucideIcons.bot,
                size: 16,
                color: isError ? AppColors.error : AppColors.primary,
              ),
            ),
            const SizedBox(width: 8),
          ],
          Flexible(
            child: Column(
              crossAxisAlignment: isUser ? CrossAxisAlignment.end : CrossAxisAlignment.start,
              children: [
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                  decoration: BoxDecoration(
                    color: isUser
                        ? AppColors.primary.withOpacity(0.15)
                        : isError
                            ? AppColors.error.withOpacity(0.08)
                            : AppColors.surfaceVariant,
                    borderRadius: BorderRadius.only(
                      topLeft: const Radius.circular(16),
                      topRight: const Radius.circular(16),
                      bottomLeft: Radius.circular(isUser ? 16 : 4),
                      bottomRight: Radius.circular(isUser ? 4 : 16),
                    ),
                  ),
                  child: message.content.isEmpty && !isError
                      ? const _TypingIndicator()
                      : _MarkdownText(
                          content: message.content,
                          color: isError ? AppColors.error : AppColors.textPrimary,
                        ),
                ),
                if (message.model != null) ...[
                  const SizedBox(height: 4),
                  Text(
                    '${message.model} · ${message.tokens ?? 0} tokens',
                    style: const TextStyle(fontSize: 10, color: AppColors.textTertiary),
                  ),
                ],
              ],
            ),
          ),
          if (isUser) const SizedBox(width: 8),
        ],
      ),
      ),
    );
  }
}

/// Typing indicator dengan teks "Kasira AI sedang berpikir..." — muncul saat
/// assistant bubble masih kosong (pre-first-chunk). Dots pakai pulse animation
/// subtle biar kasir tau AI lagi proses, bukan freeze.
class _TypingIndicator extends StatefulWidget {
  const _TypingIndicator();

  @override
  State<_TypingIndicator> createState() => _TypingIndicatorState();
}

class _TypingIndicatorState extends State<_TypingIndicator>
    with SingleTickerProviderStateMixin {
  late final AnimationController _ctrl;

  @override
  void initState() {
    super.initState();
    _ctrl = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1200),
    )..repeat();
  }

  @override
  void dispose() {
    _ctrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.center,
      children: [
        AnimatedBuilder(
          animation: _ctrl,
          builder: (_, __) {
            final t = _ctrl.value;
            return Row(
              mainAxisSize: MainAxisSize.min,
              children: List.generate(3, (i) {
                final phase = (t + i * 0.2) % 1.0;
                final scale = 0.6 + 0.4 * (phase < 0.5 ? phase * 2 : (1 - phase) * 2);
                return Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 1.5),
                  child: Transform.scale(
                    scale: scale,
                    child: Container(
                      width: 6,
                      height: 6,
                      decoration: const BoxDecoration(
                        color: AppColors.primary,
                        shape: BoxShape.circle,
                      ),
                    ),
                  ),
                );
              }),
            );
          },
        ),
        const SizedBox(width: 10),
        const Text(
          'Kasira AI sedang berpikir...',
          style: TextStyle(
            fontSize: 12.5,
            color: AppColors.textSecondary,
            fontStyle: FontStyle.italic,
          ),
        ),
      ],
    );
  }
}

/// Context awareness banner — muncul saat `conversationId != null`.
/// Sinyal halus ke kasir bahwa AI masih "inget" konteks obrolan sebelumnya
/// (multi-turn aktif, Redis history rolling TTL 30min).
class _ContextAwarenessBanner extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
      decoration: BoxDecoration(
        color: AppColors.primary.withOpacity(0.06),
        border: const Border(
          bottom: BorderSide(color: AppColors.border, width: 0.5),
        ),
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            LucideIcons.link,
            size: 11,
            color: AppColors.primary.withOpacity(0.8),
          ),
          const SizedBox(width: 6),
          Text(
            'Melanjutkan konteks obrolan...',
            style: TextStyle(
              fontSize: 11,
              color: AppColors.primary.withOpacity(0.85),
              fontWeight: FontWeight.w500,
              letterSpacing: 0.1,
            ),
          ),
        ],
      ),
    );
  }
}

/// Simple markdown render untuk AI response:
/// - `**text**` → bold
/// - `` `code` `` → monospace
/// - Lines starting with `- ` atau `* ` atau `• ` → bullet indent
/// - Preserve blank lines as spacing
class _MarkdownText extends StatelessWidget {
  final String content;
  final Color color;
  const _MarkdownText({required this.content, required this.color});

  @override
  Widget build(BuildContext context) {
    final baseStyle = TextStyle(fontSize: 13.5, color: color, height: 1.4);
    final lines = content.split('\n');
    final widgets = <Widget>[];

    for (var i = 0; i < lines.length; i++) {
      final line = lines[i];
      final trimmed = line.trimLeft();
      final isBullet = trimmed.startsWith('- ') || trimmed.startsWith('* ') || trimmed.startsWith('• ');

      if (line.trim().isEmpty) {
        widgets.add(const SizedBox(height: 6));
        continue;
      }

      if (isBullet) {
        final bulletContent = trimmed.substring(2).trimLeft();
        widgets.add(Padding(
          padding: const EdgeInsets.only(left: 4, top: 1, bottom: 1),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('•  ', style: baseStyle),
              Expanded(child: Text.rich(_parseInline(bulletContent, baseStyle))),
            ],
          ),
        ));
      } else {
        widgets.add(Text.rich(_parseInline(line, baseStyle)));
      }
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: widgets,
    );
  }

  /// Parse `**bold**` dan `` `code` `` jadi TextSpan list.
  InlineSpan _parseInline(String text, TextStyle base) {
    final spans = <TextSpan>[];
    final pattern = RegExp(r'(\*\*([^*]+)\*\*|`([^`]+)`)');
    var cursor = 0;

    for (final match in pattern.allMatches(text)) {
      if (match.start > cursor) {
        spans.add(TextSpan(text: text.substring(cursor, match.start), style: base));
      }
      final boldContent = match.group(2);
      final codeContent = match.group(3);
      if (boldContent != null) {
        spans.add(TextSpan(
          text: boldContent,
          style: base.copyWith(fontWeight: FontWeight.bold),
        ));
      } else if (codeContent != null) {
        spans.add(TextSpan(
          text: codeContent,
          style: base.copyWith(
            fontFamily: 'monospace',
            backgroundColor: AppColors.surfaceVariant,
            fontSize: (base.fontSize ?? 13.5) - 0.5,
          ),
        ));
      }
      cursor = match.end;
    }

    if (cursor < text.length) {
      spans.add(TextSpan(text: text.substring(cursor), style: base));
    }
    if (spans.isEmpty) {
      spans.add(TextSpan(text: text, style: base));
    }
    return TextSpan(children: spans);
  }
}
