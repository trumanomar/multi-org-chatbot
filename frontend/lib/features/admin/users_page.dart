import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:dio/dio.dart';
import '../../providers/auth_provider.dart';
import '../../data/api_client.dart';

class UsersPage extends ConsumerStatefulWidget {
  const UsersPage({super.key});
  @override
  ConsumerState<UsersPage> createState() => _UsersPageState();
}

class _UsersPageState extends ConsumerState<UsersPage> {
  final _username = TextEditingController();
  final _email = TextEditingController();
  final _password = TextEditingController();
  String? _status;
  bool _loading = false;

  Future<void> _create() async {
    setState(() => _loading = true);
    try {
      final jwt = ref.read(authControllerProvider).jwt!;
      final dio = ApiClient(token: jwt.token).dio;
      final res = await dio.post('/admin/create_user', data: {
        'username': _username.text.trim(),
        'email': _email.text.trim(),
        'password': _password.text,
      });
      setState(() => _status = res.data['message']?.toString() ?? 'User created');
      _username.clear(); _email.clear(); _password.clear();
    } on DioException catch (e) {
      setState(() => _status = 'Error: ${e.response?.data ?? e.message}');
    } finally {
      setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(16),
      child: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 520),
          child: Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(mainAxisSize: MainAxisSize.min, children: [
                Text('Create User', style: Theme.of(context).textTheme.titleLarge),
                const SizedBox(height: 12),
                TextField(controller: _username, decoration: const InputDecoration(labelText: 'Username')),
                const SizedBox(height: 12),
                TextField(controller: _email, decoration: const InputDecoration(labelText: 'Email')),
                const SizedBox(height: 12),
                TextField(controller: _password, decoration: const InputDecoration(labelText: 'Password'), obscureText: true),
                const SizedBox(height: 16),
                if (_status != null) Padding(padding: const EdgeInsets.only(bottom: 8), child: Text(_status!)),
                FilledButton(
                  onPressed: _loading ? null : _create,
                  child: _loading
                      ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2))
                      : const Text('Create'),
                ),
              ]),
            ),
          ),
        ),
      ),
    );
  }
}
