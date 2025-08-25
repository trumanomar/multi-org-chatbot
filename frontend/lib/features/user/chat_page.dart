// lib/features/user/chat_page.dart
import 'dart:convert';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:speech_to_text/speech_to_text.dart' as stt;

import '../../providers/auth_provider.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';


class ChatPage extends ConsumerStatefulWidget {
  final int? initialSessionId;
  const ChatPage({super.key, this.initialSessionId});

  @override
  ConsumerState<ChatPage> createState() => _ChatPageState();
}

class _ChatPageState extends ConsumerState<ChatPage> {
  // UI
  final TextEditingController _input = TextEditingController();
  final ScrollController _scroll = ScrollController();

  // Speech
  late final stt.SpeechToText _stt;
  bool _sttAvailable = false;
  bool _isListening = false;

  // Data
  List<dynamic> _sessions = [];
  List<dynamic> _messages = [];

  int? _selectedSessionId;

  // State flags
  bool _loadingSessions = false;
  bool _loadingMessages = false;
  bool _sending = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _stt = stt.SpeechToText();
    _initSTT();
    _bootstrap();
  }

  Future<void> _bootstrap() async {
    await _loadSessionsSide();
    if (widget.initialSessionId != null &&
        _sessions.any((s) => s['id'] == widget.initialSessionId)) {
      _selectSession(widget.initialSessionId!);
    } else if (_sessions.isNotEmpty) {
      _selectSession(_sessions.first['id'] as int);
    }
  }

  Future<void> _initSTT() async {
    try {
      _sttAvailable = await _stt.initialize();
      setState(() {});
    } catch (_) {
      _sttAvailable = false;
    }
  }

  Future<Dio> _dio() async {
  // Read base URL from .env; fallback for dev.
  final base = dotenv.env['API_BASE_URL'] ?? 'http://127.0.0.1:8000';
  final token = ref.read(authControllerProvider).jwt?.token;

  final d = Dio(
    BaseOptions(
      baseUrl: base,
      connectTimeout: const Duration(seconds: 30),
      receiveTimeout: const Duration(minutes: 2),
      sendTimeout: const Duration(minutes: 2),
      headers: {
        'Accept': 'application/json',
        if (token != null && token.isNotEmpty) 'Authorization': 'Bearer $token',
      },
    ),
  );

  // Optional: visible logging while you debug
  d.interceptors.add(LogInterceptor(
    requestBody: true,
    responseBody: true,
  ));

  return d;
}


  // ---------- sessions (sidebar) ----------
  Future<void> _loadSessionsSide() async {
    final userId = ref.read(authControllerProvider).user?.id;
    if (userId == null) return;

    setState(() {
      _loadingSessions = true;
      _error = null;
    });

    try {
      final dio = await _dio();
      final r = await dio.get('/chat/sessions/$userId');
      final list = (r.data as List?) ?? [];
      list.sort((a, b) {
        final da = DateTime.tryParse(a['updated_at']?.toString() ?? '') ??
            DateTime.fromMillisecondsSinceEpoch(0);
        final db = DateTime.tryParse(b['updated_at']?.toString() ?? '') ??
            DateTime.fromMillisecondsSinceEpoch(0);
        return db.compareTo(da);
      });
      setState(() {
        _sessions = list;
      });
    } catch (e) {
      setState(() {
        _error = 'Failed to load sessions';
      });
    } finally {
      setState(() {
        _loadingSessions = false;
      });
    }
  }

  Future<void> _selectSession(int id) async {
    setState(() {
      _selectedSessionId = id;
      _messages = [];
    });
    await _loadMessages(id);
  }

  Future<void> _loadMessages(int sessionId) async {
    setState(() {
      _loadingMessages = true;
      _error = null;
    });

    try {
      // Try direct messages endpoint first
      final dio = await _dio();
      final r = await dio.get('/chat/messages/$sessionId');
      final rawList = (r.data as List?) ?? [];
      final List<Map<String, dynamic>> normalized = [];
      for (final item in rawList) {
        if (item is Map) {
          final m = Map<String, dynamic>.from(item);
          final q = (m['question'] ?? '').toString();
          final a = (m['answer'] ?? '').toString();
          if (q.isNotEmpty) {
            normalized.add({'id': 'q-${m['id']}', 'role': 'user', 'content': q, 'sources': const []});
          }
          if (a.isNotEmpty) {
            normalized.add({'id': 'a-${m['id']}', 'role': 'assistant', 'content': a, 'sources': const []});
          }
        }
      }
      setState(() { _messages = normalized; });
      await Future.delayed(const Duration(milliseconds: 100));
      if (_scroll.hasClients) { _scroll.jumpTo(_scroll.position.maxScrollExtent); }
    } catch (_) {
      // Fallback to history only if we have a numeric user id
      try {
        final userId = ref.read(authControllerProvider).user?.id;
        if (userId == null) throw Exception('no-id');
        final dio = await _dio();
        final r = await dio.get('/chat/history/$userId');
        final history = (r.data as List?) ?? [];
        List<Map<String, dynamic>> normalized = [];
        for (final entry in history) {
          if (entry is Map) {
            final sidRaw = entry['session_id'];
            final sid = (sidRaw is int) ? sidRaw : int.tryParse('${sidRaw ?? ''}');
            if (sid != sessionId) continue;
            final msgs = (entry['messages'] as List?) ?? [];
            for (final item in msgs) {
              if (item is Map) {
                final m = Map<String, dynamic>.from(item);
                final q = (m['question'] ?? '').toString();
                final a = (m['answer'] ?? '').toString();
                if (q.isNotEmpty) {
                  normalized.add({'id': 'q-${m['id']}', 'role': 'user', 'content': q, 'sources': const []});
                }
                if (a.isNotEmpty) {
                  normalized.add({'id': 'a-${m['id']}', 'role': 'assistant', 'content': a, 'sources': const []});
                }
              }
            }
            break;
          }
        }
        setState(() { _messages = normalized; });
      } catch (e) {
        setState(() { _error = 'Failed to load messages'; });
      }
    } finally {
      setState(() {
        _loadingMessages = false;
      });
    }
  }

  Future<void> _newSession() async {
    try {
      final dio = await _dio();
      // Backend derives user from token; no need to pass user_id
      final r = await dio.post('/chat/new_session');
      final data = (r.data as Map?) ?? {};
      final sid = (data['session_id'] is int)
          ? data['session_id'] as int
          : int.tryParse('${data['session_id'] ?? ''}');
      if (sid == null) throw Exception('No session_id in response');
      setState(() {
        _sessions.insert(0, {'id': sid, 'title': 'New chat'});
      });
      await _selectSession(sid);
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Could not create a new session')),
      );
    }
  }

  Future<void> _sendMessage() async {
    if (_sending) return;
    final text = _input.text.trim();
    if (text.isEmpty) return;

    // If there is no active session, create one automatically
    if (_selectedSessionId == null) {
      await _newSession();
      if (_selectedSessionId == null) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Could not start a chat session')),
        );
        return;
      }
    }

    setState(() {
      _sending = true;
    });

    // optimistic add user message
    setState(() {
      _messages.add({
        'id': 'local-${DateTime.now().microsecondsSinceEpoch}',
        'role': 'user',
        'content': text,
        'sources': const []
      });
    });
    _input.clear();
    await Future.delayed(const Duration(milliseconds: 40));
    if (_scroll.hasClients) {
      _scroll.animateTo(
        _scroll.position.maxScrollExtent + 120,
        duration: const Duration(milliseconds: 250),
        curve: Curves.easeOut,
      );
    }

    try {
      final dio = await _dio();
      final payload = {
        'session_id': _selectedSessionId,
        'message': text,
      };
      final r = await dio.post(
        '/chat/query',
        data: jsonEncode(payload),
        options: Options(headers: {'Content-Type': 'application/json'}),
      );
      final resp = (r.data as Map?) ?? {};
      final answer = (resp['answer'] ?? '').toString();
      final sources = (resp['sources'] as List?) ?? const [];
      setState(() {
        _messages.add({
          'id': 'sv-${resp['message_id'] ?? DateTime.now().millisecondsSinceEpoch}',
          'role': 'assistant',
          'content': answer,
          'sources': sources,
        });
      });
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Send failed: $e')),
      );
    } finally {
      setState(() {
        _sending = false;
      });
      await _loadSessionsSide(); // refresh ordering
    }
  }

  // ---------- speech ----------
  Future<void> _toggleListen() async {
    if (!_sttAvailable) return;
    if (_isListening) {
      await _stt.stop();
      setState(() {
        _isListening = false;
      });
      return;
    }
    final ok = await _stt.listen(
      onResult: (res) {
        setState(() {
          _input.text = res.recognizedWords;
          _input.selection = TextSelection.fromPosition(
            TextPosition(offset: _input.text.length),
          );
        });
      },
    );
    setState(() => _isListening = ok);
  }

  // ---------- drawer ----------
  Widget _buildDrawer() {
    final auth = ref.watch(authControllerProvider);
    return Drawer(
      child: SafeArea(
        child: Column(
          children: [
            const SizedBox(height: 12),
            const CircleAvatar(radius: 28, child: Icon(Icons.person, size: 30)),
            const SizedBox(height: 8),
            Text(
              auth.user?.username ?? 'User',
              style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w600),
            ),
            const SizedBox(height: 16),
            ListTile(
              leading: const Icon(Icons.lock_reset),
              title: const Text('Change password'),
              onTap: () => GoRouter.of(context).push('/change-password'),
            ),
            ListTile(
              leading: const Icon(Icons.person),
              title: const Text('Profile'),
              onTap: () => GoRouter.of(context).push('/u/profile'),
            ),
            const Spacer(),
            ListTile(
              leading: const Icon(Icons.logout),
              title: const Text('Logout'),
              onTap: () async {
                await ref.read(authControllerProvider.notifier).logout();
                if (context.mounted) {
                  GoRouter.of(context).go('/login');
                }
              },
            ),
          ],
        ),
      ),
    );
  }

  // ---------- UI ----------
  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Scaffold(
      drawer: _buildDrawer(),
      appBar: AppBar(
        title: const Text('Chat'),
        actions: [
          IconButton(
            tooltip: 'New session',
            onPressed: _newSession,
            icon: const Icon(Icons.add_comment_outlined),
          ),
          Builder(
            builder: (ctx) => IconButton(
              tooltip: 'Profile',
              onPressed: () => Scaffold.of(ctx).openDrawer(),
              icon: const Icon(Icons.person),
            ),
          ),
          const SizedBox(width: 4),
        ],
      ),
      body: Row(
        children: [
          // Sessions sidebar
          ConstrainedBox(
            constraints: const BoxConstraints.tightFor(width: 280),
            child: Column(
              children: [
                Container(
                  height: 48,
                  alignment: Alignment.centerLeft,
                  padding: const EdgeInsets.symmetric(horizontal: 12),
                  child: Text('Sessions',
                      style: theme.textTheme.titleMedium
                          ?.copyWith(fontWeight: FontWeight.w600)),
                ),
                const Divider(height: 1),
                Expanded(
                  child: _loadingSessions
                      ? const Center(child: CircularProgressIndicator())
                      : _sessions.isEmpty
                          ? const Center(child: Text('No sessions yet'))
                          : ListView.separated(
                              itemCount: _sessions.length,
                              separatorBuilder: (_, __) =>
                                  const Divider(height: 1),
                              itemBuilder: (context, i) {
                                final s = _sessions[i] as Map<String, dynamic>;
                                final id = s['id'] as int;
                                final title =
                                    (s['title'] ?? 'Untitled').toString();
                                final selected = id == _selectedSessionId;
                                return ListTile(
                                  selected: selected,
                                  leading: const Icon(Icons.chat_bubble_outline),
                                  title: Text(title,
                                      maxLines: 1,
                                      overflow: TextOverflow.ellipsis),
                                  onTap: () => _selectSession(id),
                                );
                              },
                            ),
                ),
              ],
            ),
          ),
          const VerticalDivider(width: 1),
          // Chat area
          Expanded(
            child: Column(
              children: [
                if (_error != null)
                  MaterialBanner(
                    content: Text(_error!),
                    actions: [
                      TextButton(
                        onPressed: () => setState(() => _error = null),
                        child: const Text('Dismiss'),
                      )
                    ],
                  ),
                Expanded(
                  child: _loadingMessages
                      ? const Center(child: CircularProgressIndicator())
                      : _messages.isEmpty
                          ? const Center(
                              child: Text('Say hello to start the chat ✨'),
                            )
                          : ListView.builder(
                              controller: _scroll,
                              padding: const EdgeInsets.symmetric(
                                  horizontal: 16, vertical: 12),
                              itemCount: _messages.length,
                              itemBuilder: (context, i) {
                                final m = _messages[i] as Map<String, dynamic>;
                                final isUser = (m['role'] ?? 'user') == 'user';
                                final sources =
                                    (m['sources'] as List?)?.cast<dynamic>() ??
                                        const [];
                                return Align(
                                  alignment: isUser
                                      ? Alignment.centerRight
                                      : Alignment.centerLeft,
                                  child: ConstrainedBox(
                                    constraints: const BoxConstraints(
                                        maxWidth: 720),
                                    child: Card(
                                      margin: const EdgeInsets.symmetric(
                                          vertical: 6),
                                      child: Padding(
                                        padding: const EdgeInsets.all(12),
                                        child: Column(
                                          crossAxisAlignment:
                                              CrossAxisAlignment.start,
                                          children: [
                                            Text(
                                              (m['content'] ?? '').toString(),
                                              style: theme.textTheme.bodyMedium,
                                            ),
                                            if (sources.isNotEmpty) ...[
                                              const SizedBox(height: 8),
                                              Wrap(
                                                spacing: 6,
                                                runSpacing: -8,
                                                children: sources
                                                    .map((s) => Chip(
                                                          label: Text(
                                                            (s['title'] ??
                                                                    'source')
                                                                .toString(),
                                                          ),
                                                        ))
                                                    .toList(),
                                              ),
                                            ],
                                          ],
                                        ),
                                      ),
                                    ),
                                  ),
                                );
                              },
                            ),
                ),
                const Divider(height: 1),
                _inputBar(theme),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _inputBar(ThemeData theme) {
    return SafeArea(
      top: false,
      child: Padding(
        padding: const EdgeInsets.fromLTRB(12, 10, 12, 14),
        child: Row(
          children: [
            IconButton(
              tooltip: _isListening ? 'Stop' : 'Voice',
              onPressed: _sttAvailable ? _toggleListen : null,
              icon: Icon(_isListening ? Icons.mic : Icons.mic_none),
            ),
            Expanded(
              child: TextField(
                controller: _input,
                minLines: 1,
                maxLines: 5,
                onSubmitted: (_) => _sendMessage(),
                decoration: const InputDecoration(
                  hintText: 'Type your message...',
                  border: OutlineInputBorder(),
                  isDense: true,
                ),
              ),
            ),
            const SizedBox(width: 8),
            FilledButton.icon(
              onPressed: _sending ? null : _sendMessage,
              icon: _sending
                  ? const SizedBox(
                      width: 16,
                      height: 16,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Icon(Icons.send),
              label: const Text('Send'),
            ),
          ],
        ),
      ),
    );
  }

  @override
  void dispose() {
    _input.dispose();
    _scroll.dispose();
    _stt.stop();
    super.dispose();
  }
}
