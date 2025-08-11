import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';

class ChatScreen extends StatefulWidget {
  const ChatScreen({super.key});

  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> {
  final TextEditingController _messageController = TextEditingController();
  final List<Map<String, dynamic>> _messages = [];
  bool _isLoading = false;

  Future<void> _sendMessage(String message) async {
    if (message.trim().isEmpty) return;

    setState(() {
      _isLoading = true;
      _messages.add({
        'isUser': true,
        'message': message,
      });
    });

    try {
      final response = await http.post(
        Uri.parse('http://localhost:8000/chat/query'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'message': message,
          'k': 5,
        }),
      );

      final data = jsonDecode(response.body);
      setState(() {
        _messages.add({
          'isUser': false,
          'message': data['answer'],
          'sources': data['sources'],
        });
      });
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Error: $e')),
      );
    } finally {
      setState(() {
        _isLoading = false;
      });
      _messageController.clear();
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Chat'),
      ),
      body: Column(
        children: [
          Expanded(
            child: ListView.builder(
              padding: const EdgeInsets.all(8),
              itemCount: _messages.length,
              itemBuilder: (context, index) {
                final message = _messages[index];
                return MessageBubble(
                  message: message['message'],
                  isUser: message['isUser'],
                  sources: message['sources'],
                );
              },
            ),
          ),
          if (_isLoading)
            const Padding(
              padding: EdgeInsets.all(8.0),
              child: CircularProgressIndicator(),
            ),
          Padding(
            padding: const EdgeInsets.all(8.0),
            child: Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _messageController,
                    decoration: const InputDecoration(
                      hintText: 'Type your message...',
                      border: OutlineInputBorder(),
                    ),
                    onSubmitted: (value) => _sendMessage(value),
                  ),
                ),
                IconButton(
                  icon: const Icon(Icons.send),
                  onPressed: () => _sendMessage(_messageController.text),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class MessageBubble extends StatelessWidget {
  final String message;
  final bool isUser;
  final List<dynamic>? sources;

  const MessageBubble({
    super.key,
    required this.message,
    required this.isUser,
    this.sources,
  });

  @override
  Widget build(BuildContext context) {
    return Align(
      alignment: isUser ? Alignment.centerRight : Alignment.centerLeft,
      child: Container(
        margin: const EdgeInsets.symmetric(vertical: 4, horizontal: 8),
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: isUser ? Colors.blue : Colors.grey[300],
          borderRadius: BorderRadius.circular(12),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              message,
              style: TextStyle(
                color: isUser ? Colors.white : Colors.black,
              ),
            ),
            if (!isUser && sources != null && sources!.isNotEmpty) ...[
              const SizedBox(height: 8),
              Text(
                'Sources:',
                style: TextStyle(
                  fontWeight: FontWeight.bold,
                  color: isUser ? Colors.white : Colors.black,
                ),
              ),
              ...sources!.map((source) => Text(
                    source['source_file'],
                    style: TextStyle(
                      fontSize: 12,
                      color: isUser ? Colors.white70 : Colors.black54,
                    ),
                  )),
            ],
          ],
        ),
      ),
    );
  }
}