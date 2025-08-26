// lib/features/user/chat_page.dart
import 'dart:convert';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../providers/auth_provider.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';

class ChatPage extends ConsumerStatefulWidget {
  final int? initialSessionId;
  const ChatPage({super.key, this.initialSessionId});

  @override
  ConsumerState<ChatPage> createState() => _ChatPageState();
}

class _ChatPageState extends ConsumerState<ChatPage> with WidgetsBindingObserver {
  // UI
  final TextEditingController _input = TextEditingController();
  final ScrollController _scroll = ScrollController();

  // Speech
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

  // Persistence keys
  static const String _sessionsKey = 'chat_sessions';
  static const String _messagesKey = 'chat_messages';
  static const String _selectedSessionKey = 'selected_session_id';

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _bootstrap();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    super.didChangeAppLifecycleState(state);
    if (state == AppLifecycleState.paused) {
      // Save current session messages when app goes to background
      if (_selectedSessionId != null && _messages.isNotEmpty) {
        _saveSessionMessages(_selectedSessionId!, _messages);
      }
      _saveToLocalStorage();
    }
  }

  Future<void> _bootstrap() async {
    // Initialize chat page with data restoration priority:
    // 1. First restore from local storage for instant access
    // 2. Then load fresh data from server
    // 3. Select session based on priority: initialSessionId > restored session > first available
    
    // First try to restore from local storage
    await _restoreFromLocalStorage();
    
    // Then load from server to get fresh data
    await _loadSessionsSide();
    
    // Select session based on priority: initialSessionId > restored session > first available
    if (widget.initialSessionId != null &&
        _sessions.any((s) => s['id'] == widget.initialSessionId)) {
      _selectSession(widget.initialSessionId!);
    } else if (_selectedSessionId != null &&
               _sessions.any((s) => s['id'] == _selectedSessionId)) {
      await _loadMessages(_selectedSessionId!);
    } else if (_sessions.isNotEmpty) {
      _selectSession(_sessions.first['id'] as int);
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
    setState(() {
      _loadingSessions = true;
      _error = null;
    });

    try {
      final dio = await _dio();
      // استخدام الـ endpoint الصحيح من الـ backend
      final r = await dio.get('/chat-history/my-sessions', queryParameters: {
        'limit': 50,
        'offset': 0,
      });
      final list = (r.data as List?) ?? [];
      
      // ترتيب حسب آخر رسالة أو تاريخ الإنشاء
      list.sort((a, b) {
        final aTime = a['last_message_at'] ?? a['created_at'];
        final bTime = b['last_message_at'] ?? b['created_at'];
        final da = DateTime.tryParse(aTime?.toString() ?? '') ??
            DateTime.fromMillisecondsSinceEpoch(0);
        final db = DateTime.tryParse(bTime?.toString() ?? '') ??
            DateTime.fromMillisecondsSinceEpoch(0);
        return db.compareTo(da);
      });
      
      setState(() {
        _sessions = list;
      });
      
      // Save sessions and preserve existing messages for each session
      await _saveToLocalStorage();
    } catch (e) {
      print('Error loading sessions: $e');
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
    // Switch to a different chat session
    // This method ensures current session messages are saved before switching
    
    // Save current session messages before switching
    if (_selectedSessionId != null && _messages.isNotEmpty) {
      await _saveSessionMessages(_selectedSessionId!, _messages);
    }
    
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
      final dio = await _dio();
      // استخدام الـ endpoint الصحيح للرسائل
      final r = await dio.get('/chat-history/sessions/$sessionId/messages');
      final rawList = (r.data as List?) ?? [];
      
      final List<Map<String, dynamic>> normalized = [];
      for (final item in rawList) {
        if (item is Map) {
          final m = Map<String, dynamic>.from(item);
          final q = (m['question'] ?? '').toString();
          final a = (m['answer'] ?? '').toString();
          
          if (q.isNotEmpty) {
            normalized.add({
              'id': 'q-${m['id']}',
              'role': 'user',
              'content': q,
              'sources': const [],
              'originalMessageId': m['id'],
            });
          }
          
          if (a.isNotEmpty) {
            normalized.add({
              'id': 'a-${m['id']}',
              'role': 'assistant',
              'content': a,
              'sources': const [],
              'originalMessageId': m['id'],
            });
          }
        }
      }
      
      setState(() {
        _messages = normalized;
      });
      
      // Save messages for this session immediately
      await _saveSessionMessages(sessionId, normalized);
      
      // Scroll to bottom after loading
      await Future.delayed(const Duration(milliseconds: 100));
      if (_scroll.hasClients) {
        _scroll.jumpTo(_scroll.position.maxScrollExtent);
      }
    } catch (e) {
      print('Error loading messages: $e');
      // Fallback to chat history if messages endpoint fails
      try {
        final dio = await _dio();
        final r = await dio.get('/chat-history/history', queryParameters: {'limit': 50});
        final history = (r.data as List?) ?? [];
        
        List<Map<String, dynamic>> normalized = [];
        for (final entry in history) {
          if (entry is Map) {
            final sid = entry['session_id'];
            if (sid != sessionId) continue;
            
            final msgs = (entry['messages'] as List?) ?? [];
            for (final item in msgs) {
              if (item is Map) {
                final m = Map<String, dynamic>.from(item);
                final q = (m['question'] ?? '').toString();
                final a = (m['answer'] ?? '').toString();
                
                if (q.isNotEmpty) {
                  normalized.add({
                    'id': 'q-${m['id']}',
                    'role': 'user',
                    'content': q,
                    'sources': const [],
                    'originalMessageId': m['id'],
                  });
                }
                
                if (a.isNotEmpty) {
                  normalized.add({
                    'id': 'a-${m['id']}',
                    'role': 'assistant',
                    'content': a,
                    'sources': const [],
                    'originalMessageId': m['id'],
                  });
                }
              }
            }
            break;
          }
        }
        
        setState(() {
          _messages = normalized;
        });
        
        // Save messages loaded from history
        await _saveSessionMessages(sessionId, normalized);
      } catch (e2) {
        print('Error loading history fallback: $e2');
        setState(() {
          _error = 'Failed to load messages';
        });
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
        _sessions.insert(0, {
          'id': sid,
          'title': 'New chat',
          'created_at': DateTime.now().toIso8601String(),
          'message_count': 0,
          'last_message_at': null,
        });
      });
      
      // Save to local storage and clear any existing messages
      await _saveToLocalStorage();
      setState(() {
        _messages = [];
      });
      
      await _selectSession(sid);
    } catch (e) {
      print('Error creating new session: $e');
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Could not create a new session')),
        );
      }
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
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Could not start a chat session')),
          );
        }
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
    
    // Save current session messages immediately
    if (_selectedSessionId != null) {
      await _saveSessionMessages(_selectedSessionId!, _messages);
    }
    
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
          'originalMessageId': resp['message_id'],
        });
      });
      
      // Save current session messages immediately
      if (_selectedSessionId != null) {
        await _saveSessionMessages(_selectedSessionId!, _messages);
      }
    } catch (e) {
      print('Error sending message: $e');
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Send failed: $e')),
        );
      }
    } finally {
      setState(() {
        _sending = false;
      });
      await _refreshSessions(); // refresh ordering and preserve messages
    }
  }

  Future<void> _submitFeedback(int messageIndex, int rating, String comment) async {
    try {
      final dio = await _dio();
      final msg = _messages[messageIndex] as Map<String, dynamic>;
      
      // Extract the content for the feedback
      final content = (msg['content'] ?? '').toString();
      
      await dio.post(
        '/feedback/post',
        data: jsonEncode({
          'content': comment,
          'rating': rating,
          'question': content, // Using content as question since that's what we have
          'message_id': msg['originalMessageId'], // Include original message ID if available
        }),
        options: Options(headers: {'Content-Type': 'application/json'}),
      );

      // Update the message with feedback info
      setState(() {
        _messages[messageIndex] = {
          ...(_messages[messageIndex] as Map<String, dynamic>),
          'feedbackRating': rating,
          'feedbackComment': comment,
          'feedbackSubmitted': true,
        };
      });
      
      // Save updated messages
      if (_selectedSessionId != null) {
        await _saveSessionMessages(_selectedSessionId!, _messages);
      }

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Feedback submitted successfully!')),
        );
      }
    } catch (e) {
      print('Error submitting feedback: $e');
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to submit feedback: $e')),
        );
      }
    }
  }

  void _showFeedbackDialog(int messageIndex) {
    final msg = _messages[messageIndex] as Map<String, dynamic>;
    int rating = (msg['feedbackRating'] as int?) ?? 5;
    final commentController = TextEditingController(
      text: (msg['feedbackComment'] as String?) ?? ''
    );

    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Rate this Response'),
        content: StatefulBuilder(
          builder: (context, setDialogState) => Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text('How would you rate this response?'),
              const SizedBox(height: 16),
              
              // Star Rating
              Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: List.generate(5, (index) {
                  final starIndex = index + 1;
                  return GestureDetector(
                    onTap: () => setDialogState(() => rating = starIndex),
                    child: Icon(
                      Icons.star,
                      size: 40,
                      color: starIndex <= rating ? Colors.amber : Colors.grey[300],
                    ),
                  );
                }),
              ),
              const SizedBox(height: 16),
              
              // Comment field
              TextField(
                controller: commentController,
                maxLines: 3,
                decoration: const InputDecoration(
                  labelText: 'Add a comment (optional)',
                  hintText: 'Tell us what you think about this response...',
                  border: OutlineInputBorder(),
                ),
              ),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () {
              Navigator.of(context).pop();
              _submitFeedback(messageIndex, rating, commentController.text.trim());
            },
            child: const Text('Submit'),
          ),
        ],
      ),
    );
  }

  Future<void> _startSpeechToText() async {
    if (_isListening) return;

    setState(() {
      _isListening = true;
    });

    // Show initial message
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('🎤 Recording will start in 5 seconds, then you have 7 seconds to speak...'),
          duration: Duration(seconds: 3),
        ),
      );
    }

    try {
      final dio = await _dio();
      final response = await dio.get('/speech-to-text/mic');
      final recognizedText = response.data.toString().trim();
      
      if (recognizedText.isNotEmpty) {
        setState(() {
          _input.text = recognizedText;
          _input.selection = TextSelection.fromPosition(
            TextPosition(offset: _input.text.length),
          );
        });
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Text('✅ Speech recognized successfully!'),
              duration: Duration(seconds: 2),
            ),
          );
        }
      } else {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Text('❌ No speech detected. Please try again.'),
              duration: Duration(seconds: 2),
            ),
          );
        }
      }
    } catch (e) {
      print('Speech recognition error: $e');
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Speech recognition failed: $e')),
        );
      }
    } finally {
      setState(() {
        _isListening = false;
      });
    }
  }

  Future<void> _deleteSession(int sessionId) async {
    try {
      final dio = await _dio();
      await dio.delete('/chat-history/sessions/$sessionId');
      
      // Remove from local list
      setState(() {
        _sessions.removeWhere((s) => s['id'] == sessionId);
        if (_selectedSessionId == sessionId) {
          _selectedSessionId = null;
          _messages = [];
          // Select first available session
          if (_sessions.isNotEmpty) {
            _selectSession(_sessions.first['id'] as int);
          }
        }
      });
      
      // Clear messages for deleted session and save updated sessions
      await _clearSessionMessages(sessionId);
      await _saveToLocalStorage();
      
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Session deleted successfully')),
        );
      }
    } catch (e) {
      print('Error deleting session: $e');
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to delete session: $e')),
        );
      }
    }
  }

  void _showSessionOptions(int sessionId, String title) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: Text('Session: ${title.length > 20 ? "${title.substring(0, 20)}..." : title}'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            ListTile(
              leading: const Icon(Icons.delete, color: Colors.red),
              title: const Text('Delete Session'),
              onTap: () {
                Navigator.of(context).pop();
                _showDeleteConfirmation(sessionId, title);
              },
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('Cancel'),
          ),
        ],
      ),
    );
  }

  void _showDeleteConfirmation(int sessionId, String title) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Delete Session'),
        content: Text('Are you sure you want to delete "$title"? This action cannot be undone.'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () {
              Navigator.of(context).pop();
              _deleteSession(sessionId);
            },
            style: ElevatedButton.styleFrom(backgroundColor: Colors.red),
            child: const Text('Delete', style: TextStyle(color: Colors.white)),
          ),
        ],
      ),
    );
  }

  // ---------- Persistence Methods ----------
  // This system ensures that:
  // 1. Each session's messages are saved separately with unique keys
  // 2. Messages are saved immediately when they change
  // 3. Messages are restored when switching between sessions
  // 4. Data persists across app refreshes and restarts
  // 5. Data is cleared only on logout for security
  
  Future<void> _saveToLocalStorage() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      
      // Save sessions
      await prefs.setString(_sessionsKey, jsonEncode(_sessions));
      
      // Save messages for ALL sessions, not just the current one
      for (final session in _sessions) {
        final sessionId = session['id'] as int;
        final messagesKey = '${_messagesKey}_$sessionId';
        
        // Get messages for this specific session
        List<dynamic> sessionMessages = [];
        if (sessionId == _selectedSessionId) {
          // Current session - use _messages
          sessionMessages = _messages;
        } else {
          // Other sessions - try to get from local storage first
          final existingMessagesJson = prefs.getString(messagesKey);
          if (existingMessagesJson != null) {
            sessionMessages = jsonDecode(existingMessagesJson) as List<dynamic>;
          }
        }
        
        // Save messages for this session
        if (sessionMessages.isNotEmpty) {
          await prefs.setString(messagesKey, jsonEncode(sessionMessages));
        }
      }
      
      // Save selected session ID
      if (_selectedSessionId != null) {
        await prefs.setInt(_selectedSessionKey, _selectedSessionId!);
      }
    } catch (e) {
      print('Error saving to local storage: $e');
    }
  }

  Future<void> _restoreFromLocalStorage() async {
    // Restore chat data from local storage on app startup
    // This provides instant access to previous chat sessions
    try {
      final prefs = await SharedPreferences.getInstance();
      
      // Restore sessions
      final sessionsJson = prefs.getString(_sessionsKey);
      if (sessionsJson != null) {
        final sessions = jsonDecode(sessionsJson) as List<dynamic>;
        setState(() {
          _sessions = sessions;
        });
      }
      
      // Restore selected session ID
      final selectedId = prefs.getInt(_selectedSessionKey);
      if (selectedId != null) {
        setState(() {
          _selectedSessionId = selectedId;
        });
        
        // Restore messages for selected session
        final messagesKey = '${_messagesKey}_$selectedId';
        final messagesJson = prefs.getString(messagesKey);
        if (messagesJson != null) {
          final messages = jsonDecode(messagesJson) as List<dynamic>;
          setState(() {
            _messages = messages;
          });
        }
      }
    } catch (e) {
      print('Error restoring from local storage: $e');
    }
  }

  Future<void> _clearLocalStorage() async {
    // Clear all chat-related data from local storage
    // This is called on logout to ensure data security
    try {
      final prefs = await SharedPreferences.getInstance();
      
      // Clear all chat-related data
      await prefs.remove(_sessionsKey);
      await prefs.remove(_selectedSessionKey);
      
      // Clear messages for all sessions
      final keys = prefs.getKeys();
      for (final key in keys) {
        if (key.startsWith(_messagesKey)) {
          await prefs.remove(key);
        }
      }
    } catch (e) {
      print('Error clearing local storage: $e');
    }
  }

  Future<void> _saveSessionMessages(int sessionId, List<dynamic> messages) async {
    // Save messages for a specific session with a unique key
    // This ensures each session's messages are stored separately
    try {
      final prefs = await SharedPreferences.getInstance();
      final messagesKey = '${_messagesKey}_$sessionId';
      await prefs.setString(messagesKey, jsonEncode(messages));
    } catch (e) {
      print('Error saving session messages: $e');
    }
  }

  Future<void> _clearSessionMessages(int sessionId) async {
    // Remove messages for a specific session when it's deleted
    // This prevents orphaned message data from accumulating
    try {
      final prefs = await SharedPreferences.getInstance();
      final messagesKey = '${_messagesKey}_$sessionId';
      await prefs.remove(messagesKey);
    } catch (e) {
      print('Error clearing session messages: $e');
    }
  }

  Future<void> _refreshSessions() async {
    // Save current session messages before refreshing sessions
    // This ensures no messages are lost during refresh
    if (_selectedSessionId != null && _messages.isNotEmpty) {
      await _saveSessionMessages(_selectedSessionId!, _messages);
    }
    
    // Load fresh sessions from server
    await _loadSessionsSide();
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
                // Clear local storage before logout
                await _clearLocalStorage();
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
                  child: Row(
                    children: [
                      Expanded(
                        child: Text('Sessions',
                            style: theme.textTheme.titleMedium
                                ?.copyWith(fontWeight: FontWeight.w600)),
                      ),
                      IconButton(
                        icon: const Icon(Icons.refresh, size: 20),
                        onPressed: _refreshSessions,
                        tooltip: 'Refresh sessions',
                      ),
                    ],
                  ),
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
                                final messageCount = (s['message_count'] ?? 0) as int;
                                String title = 'Chat Session';
                                
                                // Generate title based on message count or use existing title
                                if (s['title'] != null && s['title'] != 'New chat') {
                                  title = s['title'].toString();
                                } else if (messageCount > 0) {
                                  title = 'Chat ($messageCount messages)';
                                } else {
                                  title = 'New Chat';
                                }
                                
                                final selected = id == _selectedSessionId;
                                return ListTile(
                                  selected: selected,
                                  leading: const Icon(Icons.chat_bubble_outline),
                                  title: Text(title,
                                      maxLines: 1,
                                      overflow: TextOverflow.ellipsis),
                                  subtitle: messageCount > 0 
                                    ? Text('$messageCount messages', 
                                        style: theme.textTheme.bodySmall)
                                    : null,
                                  trailing: PopupMenuButton(
                                    icon: const Icon(Icons.more_vert, size: 16),
                                    itemBuilder: (context) => [
                                      PopupMenuItem(
                                        child: const Row(
                                          children: [
                                            Icon(Icons.delete, color: Colors.red, size: 16),
                                            SizedBox(width: 8),
                                            Text('Delete'),
                                          ],
                                        ),
                                        onTap: () => Future.delayed(
                                          const Duration(milliseconds: 100),
                                          () => _showDeleteConfirmation(id, title),
                                        ),
                                      ),
                                    ],
                                  ),
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
                                final feedbackSubmitted = (m['feedbackSubmitted'] as bool?) ?? false;
                                final feedbackRating = (m['feedbackRating'] as int?);
                                
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
                                            // Add feedback section for assistant messages
                                            if (!isUser) ...[
                                              const SizedBox(height: 8),
                                              Row(
                                                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                                children: [
                                                  if (feedbackSubmitted && feedbackRating != null)
                                                    Row(
                                                      children: [
                                                        const Icon(Icons.thumb_up, size: 16, color: Colors.green),
                                                        const SizedBox(width: 4),
                                                        Text(
                                                          'Rated: $feedbackRating/5',
                                                          style: theme.textTheme.bodySmall?.copyWith(
                                                            color: Colors.green,
                                                          ),
                                                        ),
                                                      ],
                                                    )
                                                  else
                                                    const SizedBox(), // Empty space when no feedback
                                                  
                                                  // Feedback button
                                                  TextButton.icon(
                                                    onPressed: () => _showFeedbackDialog(i),
                                                    icon: Icon(
                                                      feedbackSubmitted ? Icons.edit : Icons.rate_review,
                                                      size: 16,
                                                    ),
                                                    label: Text(
                                                      feedbackSubmitted ? 'Edit Rating' : 'Rate Response',
                                                      style: theme.textTheme.bodySmall,
                                                    ),
                                                    style: TextButton.styleFrom(
                                                      padding: const EdgeInsets.symmetric(
                                                        horizontal: 8,
                                                        vertical: 4,
                                                      ),
                                                    ),
                                                  ),
                                                ],
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
              tooltip: _isListening ? 'Recording in progress...' : 'Voice (5s wait, 7s record)',
              onPressed: _isListening ? null : _startSpeechToText,
              icon: Icon(
                _isListening ? Icons.mic : Icons.mic_none,
                color: _isListening ? Colors.red : null,
              ),
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
    // Save current session messages before disposing
    if (_selectedSessionId != null && _messages.isNotEmpty) {
      _saveSessionMessages(_selectedSessionId!, _messages);
    }
    
    WidgetsBinding.instance.removeObserver(this);
    _input.dispose();
    _scroll.dispose();
    super.dispose();
  }
}