import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:dio/dio.dart';

import '../../providers/auth_provider.dart';
import '../../data/api_client.dart';

class ChatPage extends ConsumerStatefulWidget {
  const ChatPage({super.key});

  @override
  ConsumerState<ChatPage> createState() => _ChatPageState();
}

class _ChatPageState extends ConsumerState<ChatPage> {
  final _input = TextEditingController();
  final _scrollCtrl = ScrollController();

  bool _sending = false;
  String? _error;

  // very simple in-memory transcript
  final List<_Msg> _msgs = <_Msg>[];

  @override
  void dispose() {
    _input.dispose();
    _scrollCtrl.dispose();
    super.dispose();
  }

  Future<void> _logout() async {
    await ref.read(authControllerProvider.notifier).logout();
    if (!mounted) return;
    context.go('/login');
  }

  Future<void> _send() async {
    final q = _input.text.trim();
    if (q.isEmpty || _sending) return;

    setState(() {
      _sending = true;
      _error = null;
      _msgs.add(_Msg(role: 'user', text: q));
    });

    try {
      final jwt = ref.read(authControllerProvider).jwt!;
      final dio = ApiClient(token: jwt.token).dioWithLongTimeout;

      final res = await dio.post(
        '/chat/query',
        data: {'message': q, 'k': 5},
        options: ApiClient.jsonOpts,
      );

      final data = res.data;
      final answer = (data is Map && data['answer'] != null)
          ? data['answer'].toString()
          : data.toString();

      if (!mounted) return;
      setState(() {
        _msgs.add(_Msg(role: 'assistant', text: answer));
      });
    } on DioException catch (e) {
      if (!mounted) return;
      setState(() {
        _error = e.response?.data?.toString() ?? e.message ?? 'Request failed';
        _msgs.add(_Msg(role: 'assistant', text: 'Error: $_error'));
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = e.toString();
        _msgs.add(_Msg(role: 'assistant', text: 'Error: $_error'));
      });
    } finally {
      if (!mounted) return;
      setState(() {
        _sending = false;
        _input.clear();
      });
      await Future<void>.delayed(const Duration(milliseconds: 50));
      if (_scrollCtrl.hasClients) {
        _scrollCtrl.animateTo(
          _scrollCtrl.position.maxScrollExtent,
          duration: const Duration(milliseconds: 250),
          curve: Curves.easeOut,
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Chat'),
        actions: [
          IconButton(
            tooltip: 'Log out',
            icon: const Icon(Icons.logout),
            onPressed: _logout,
          ),
        ],
      ),
      body: Column(
        children: [
          if (_error != null)
            MaterialBanner(
              backgroundColor: Colors.red.withOpacity(.08),
              content: Text(_error!, style: const TextStyle(color: Colors.red)),
              actions: [
                TextButton(
                  onPressed: () => setState(() => _error = null),
                  child: const Text('Dismiss'),
                ),
              ],
            ),
          Expanded(
            child: ListView.builder(
              controller: _scrollCtrl,
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
              itemCount: _msgs.length,
              itemBuilder: (_, i) {
                final m = _msgs[i];
                final isUser = m.role == 'user';
                return Align(
                  alignment: isUser ? Alignment.centerRight : Alignment.centerLeft,
                  child: Container(
                    margin: const EdgeInsets.symmetric(vertical: 6),
                    padding: const EdgeInsets.all(12),
                    constraints: const BoxConstraints(maxWidth: 820),
                    decoration: BoxDecoration(
                      color: isUser
                          ? theme.colorScheme.primary.withOpacity(.10)
                          : theme.colorScheme.surfaceVariant,
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(
                        color: isUser
                            ? theme.colorScheme.primary.withOpacity(.25)
                            : theme.dividerColor.withOpacity(.2),
                      ),
                    ),
                    child: SelectableText(
                      m.text,
                      style: TextStyle(
                        color: isUser
                            ? theme.colorScheme.onSurface
                            : theme.colorScheme.onSurfaceVariant,
                      ),
                    ),
                  ),
                );
              },
            ),
          ),
          SafeArea(
            top: false,
            child: Padding(
              padding: const EdgeInsets.fromLTRB(12, 6, 12, 12),
              child: Row(
                children: [
                  Expanded(
                    child: TextField(
                      controller: _input,
                      minLines: 1,
                      maxLines: 6,
                      textInputAction: TextInputAction.send,
                      onSubmitted: (_) => _send(),
                      decoration: const InputDecoration(
                        hintText: 'Ask something from your org docs…',
                        border: OutlineInputBorder(),
                      ),
                    ),
                  ),
                  const SizedBox(width: 8),
                  FilledButton.icon(
                    onPressed: _sending ? null : _send,
                    icon: _sending
                        ? const SizedBox(
                            width: 16, height: 16,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          )
                        : const Icon(Icons.send),
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

class _Msg {
  final String role;
  final String text;
  _Msg({required this.role, required this.text});
}
