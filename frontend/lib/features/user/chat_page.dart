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
        _msgs.add(_Msg(
          role: 'assistant', 
          text: answer,
          question: q, // Store the question for feedback
        ));
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

  Future<void> _submitFeedback(int messageIndex, int rating, String comment) async {
    try {
      final jwt = ref.read(authControllerProvider).jwt!;
      final dio = ApiClient(token: jwt.token).dio;
      final msg = _msgs[messageIndex];

      await dio.post(
        '/feedback/post',
        data: {
          'content': comment,
          'rating': rating,
          'question': msg.question ?? msg.text,
        },
        options: ApiClient.jsonOpts,
      );

      setState(() {
        _msgs[messageIndex] = msg.copyWith(
          feedbackRating: rating,
          feedbackComment: comment,
          feedbackSubmitted: true,
        );
      });

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Feedback submitted successfully!')),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to submit feedback: $e')),
        );
      }
    }
  }

  void _showFeedbackDialog(int messageIndex) {
    final msg = _msgs[messageIndex];
    int rating = msg.feedbackRating ?? 5;
    final commentController = TextEditingController(text: msg.feedbackComment ?? '');

    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Rate this Response'),
        content: StatefulBuilder(
          builder: (context, setState) => Column(
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
                    onTap: () => setState(() => rating = starIndex),
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

  Widget _buildMessage(int index) {
    final m = _msgs[index];
    final theme = Theme.of(context);
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
              : theme.colorScheme.surfaceContainerHighest,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
            color: isUser
                ? theme.colorScheme.primary.withOpacity(.25)
                : theme.dividerColor.withOpacity(.2),
          ),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            SelectableText(
              m.text,
              style: TextStyle(
                color: isUser
                    ? theme.colorScheme.onSurface
                    : theme.colorScheme.onSurfaceVariant,
              ),
            ),
            
            // Feedback section for assistant messages only
            if (!isUser && !m.text.startsWith('Error:')) ...[
              const SizedBox(height: 12),
              const Divider(height: 1),
              const SizedBox(height: 8),
              
              if (m.feedbackSubmitted) ...[
                // Show submitted feedback
                Row(
                  children: [
                    const Icon(Icons.check_circle, color: Colors.green, size: 16),
                    const SizedBox(width: 4),
                    const Text('Feedback submitted', style: TextStyle(color: Colors.green, fontSize: 12)),
                    const SizedBox(width: 8),
                    Row(
                      children: List.generate(5, (starIndex) {
                        return Icon(
                          Icons.star,
                          size: 14,
                          color: starIndex < (m.feedbackRating ?? 0) ? Colors.amber : Colors.grey[300],
                        );
                      }),
                    ),
                    if (m.feedbackComment?.isNotEmpty == true) ...[
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          m.feedbackComment!,
                          style: const TextStyle(fontSize: 12, fontStyle: FontStyle.italic),
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                    ],
                  ],
                ),
              ] else ...[
                // Show feedback button
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    const Text(
                      'Was this response helpful?',
                      style: TextStyle(fontSize: 12, color: Colors.grey),
                    ),
                    TextButton.icon(
                      onPressed: () => _showFeedbackDialog(index),
                      icon: const Icon(Icons.star_border, size: 16),
                      label: const Text('Rate'),
                      style: TextButton.styleFrom(
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                        minimumSize: const Size(0, 0),
                        tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                      ),
                    ),
                  ],
                ),
              ],
            ],
          ],
        ),
      ),
    );
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
              itemBuilder: (_, i) => _buildMessage(i),
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
  final String? question;
  final int? feedbackRating;
  final String? feedbackComment;
  final bool feedbackSubmitted;

  _Msg({
    required this.role,
    required this.text,
    this.question,
    this.feedbackRating,
    this.feedbackComment,
    this.feedbackSubmitted = false,
  });

  _Msg copyWith({
    String? role,
    String? text,
    String? question,
    int? feedbackRating,
    String? feedbackComment,
    bool? feedbackSubmitted,
  }) {
    return _Msg(
      role: role ?? this.role,
      text: text ?? this.text,
      question: question ?? this.question,
      feedbackRating: feedbackRating ?? this.feedbackRating,
      feedbackComment: feedbackComment ?? this.feedbackComment,
      feedbackSubmitted: feedbackSubmitted ?? this.feedbackSubmitted,
    );
  }
}