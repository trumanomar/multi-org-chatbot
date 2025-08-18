import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../providers/auth_provider.dart';
import '../../data/api_client.dart';

class ChatPage extends ConsumerStatefulWidget {
  const ChatPage({super.key});

  @override
  ConsumerState<ChatPage> createState() => _ChatPageState();
}

class _ChatPageState extends ConsumerState<ChatPage> {
  final _controller = TextEditingController();
  final List<_ChatItem> _items = [];
  bool _busy = false;

  Future<void> _send() async {
    final msg = _controller.text.trim();
    if (msg.isEmpty || _busy) return;

    setState(() {
      _items.add(_ChatItem(text: msg, isUser: true));
      _busy = true;
    });
    _controller.clear();

    try {
      final jwt = ref.read(authControllerProvider).jwt;
      final dio = ApiClient(token: jwt?.token).dioWithLongTimeout;
      final res = await dio.post(
        '/chat/query',
        data: jsonEncode({'message': msg, 'k': 5}),
        options: ApiClient.jsonOpts,
      );

      String answer = '';
      List sources = const [];
      final data = res.data;
      if (data is Map) {
        answer = (data['answer'] ?? '').toString();
        final s = data['sources'];
        if (s is List) sources = s;
      } else if (data is String) {
        answer = data;
      }

      setState(() {
        _items.add(_ChatItem(text: answer.isEmpty ? 'No answer.' : answer));
        if (sources.isNotEmpty) {
          _items.add(_ChatItem(
            text: sources.map((e) => (e['source_file'] ?? e['source'] ?? e).toString()).join(' • '),
            isMeta: true,
          ));
        }
      });
    } catch (e) {
      setState(() {
        _items.add(_ChatItem(text: 'Error: $e', isMeta: true));
      });
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Chat'),
        centerTitle: false,
      ),
      body: Column(
        children: [
          Expanded(
            child: ListView.separated(
              padding: const EdgeInsets.all(16),
              itemCount: _items.length,
              separatorBuilder: (_, __) => const SizedBox(height: 8),
              itemBuilder: (_, i) {
                final it = _items[i];
                final align =
                    it.isUser ? CrossAxisAlignment.end : CrossAxisAlignment.start;
                final color = it.isMeta
                    ? Colors.indigo.withOpacity(.08)
                    : it.isUser
                        ? Colors.indigo.withOpacity(.12)
                        : Theme.of(context).cardColor;

                return Row(
                  mainAxisAlignment: it.isUser
                      ? MainAxisAlignment.end
                      : MainAxisAlignment.start,
                  children: [
                    Flexible(
                      child: Container(
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(
                          color: color,
                          borderRadius: BorderRadius.circular(12),
                        ),
                        child: Column(
                          crossAxisAlignment: align,
                          children: [
                            SelectableText(it.text),
                          ],
                        ),
                      ),
                    ),
                  ],
                );
              },
            ),
          ),
          SafeArea(
            top: false,
            child: Padding(
              padding: const EdgeInsets.fromLTRB(12, 8, 12, 12),
              child: Row(
                children: [
                  Expanded(
                    child: TextField(
                      controller: _controller,
                      decoration: const InputDecoration(
                        hintText: 'Ask something in your docs…',
                        border: OutlineInputBorder(),
                      ),
                      onSubmitted: (_) => _send(),
                    ),
                  ),
                  const SizedBox(width: 8),
                  FilledButton.icon(
                    onPressed: _busy ? null : _send,
                    icon: const Icon(Icons.send),
                    label: const Text('Send'),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _ChatItem {
  final String text;
  final bool isUser;
  final bool isMeta; // for sources/errors/etc.
  _ChatItem({required this.text, this.isUser = false, this.isMeta = false});
}
