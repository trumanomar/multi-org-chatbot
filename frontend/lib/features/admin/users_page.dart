import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../providers/auth_provider.dart';
import '../../data/api_client.dart';

class UsersPage extends ConsumerStatefulWidget {
  const UsersPage({super.key});
  @override
  ConsumerState<UsersPage> createState() => _UsersPageState();
}

class _UsersPageState extends ConsumerState<UsersPage> {
  bool _loading = false;
  String? _error;
  List<Map<String, dynamic>> _users = [];

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() { _loading = true; _error = null; });
    try {
      final jwt = ref.read(authControllerProvider).jwt!;
      final dio = ApiClient(token: jwt.token).dio;
      final res = await dio.get('/admin/users');
      final list = (res.data['users'] as List).map<Map<String,dynamic>>((e) => Map<String,dynamic>.from(e)).toList();
      setState(() => _users = list);
    } on DioException catch (e) {
      setState(() => _error = e.response?.data?.toString() ?? e.message ?? 'Failed');
    } catch (e) {
      setState(() => _error = e.toString());
    } finally {
      setState(() => _loading = false);
    }
  }

  Future<void> _deleteUser(int id) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text('Delete user?'),
        content: const Text('This will permanently delete the user.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Cancel')),
          FilledButton(onPressed: () => Navigator.pop(context, true), child: const Text('Delete')),
        ],
      ),
    );
    if (ok != true) return;

    try {
      final jwt = ref.read(authControllerProvider).jwt!;
      final dio = ApiClient(token: jwt.token).dio;
      final res = await dio.delete('/admin/users/$id');
      if (res.statusCode! >= 200 && res.statusCode! < 300) {
        setState(() => _users.removeWhere((u) => u['id'] == id));
      } else {
        throw Exception(res.data?.toString() ?? 'Delete failed');
      }
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Delete failed: $e')));
    }
  }

  Future<void> _changeRole(int id, String newRole) async {
    try {
      final jwt = ref.read(authControllerProvider).jwt!;
      final dio = ApiClient(token: jwt.token).dio;
      final res = await dio.put('/admin/users/role/$id', queryParameters: {'new_role': newRole});
      if (res.statusCode! >= 200 && res.statusCode! < 300) {
        final i = _users.indexWhere((u) => u['id'] == id);
        if (i != -1) setState(() => _users[i]['role'] = newRole);
      } else {
        throw Exception(res.data?.toString() ?? 'Role update failed');
      }
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Role update failed: $e')));
    }
  }

  Future<void> _changeEmail(int id) async {
    final current = _users.firstWhere((u) => u['id'] == id, orElse: () => {});
    final controller = TextEditingController(text: (current['email'] ?? '').toString());
    final ok = await showDialog<bool>(
      context: context,
      builder: (dialogCtx) => AlertDialog(
        title: const Text('Update email'),
        content: TextField(controller: controller, decoration: const InputDecoration(hintText: 'new@email.com')),
        actions: [
          TextButton(onPressed: () => Navigator.of(dialogCtx).pop(false), child: const Text('Cancel')),
          FilledButton(onPressed: () => Navigator.of(dialogCtx).pop(true), child: const Text('Save')),
        ],
      ),
    );
    if (ok != true) return;
    final newEmail = controller.text.trim();
    if (newEmail.isEmpty) return;

    try {
      final jwt = ref.read(authControllerProvider).jwt!;
      final dio = ApiClient(token: jwt.token).dio;
      final res = await dio.put('/admin/users/$id/email', queryParameters: {'new_email': newEmail});
      if (res.statusCode! >= 200 && res.statusCode! < 300) {
        final i = _users.indexWhere((u) => u['id'] == id);
        if (i != -1) setState(() => _users[i]['email'] = newEmail);
      } else {
        throw Exception(res.data?.toString() ?? 'Email update failed');
      }
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Email update failed: $e')));
    }
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(16),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text('Users', style: Theme.of(context).textTheme.headlineSmall),
        const SizedBox(height: 12),
        if (_loading) const LinearProgressIndicator(),
        if (_error != null) Padding(padding: const EdgeInsets.only(top: 8), child: Text(_error!, style: const TextStyle(color: Colors.red))),
        const SizedBox(height: 12),
        Expanded(
          child: _users.isEmpty && !_loading
              ? const Center(child: Text('No users found'))
              : ListView.separated(
                  itemCount: _users.length,
                  separatorBuilder: (_, __) => const SizedBox(height: 6),
                  itemBuilder: (_, i) {
                    final u = _users[i];
                    return Card(
                      child: ListTile(
                        title: Text(u['username'] ?? '—'),
                        subtitle: Text('${u['email'] ?? '—'}   (id ${u['id']})'),
                        trailing: Wrap(
                          spacing: 8,
                          children: [
                            DropdownButton<String>(
                              value: (u['role'] ?? 'user').toString(),
                              items: const [
                                DropdownMenuItem(value: 'user', child: Text('user')),
                                DropdownMenuItem(value: 'admin', child: Text('admin')),
                              ],
                              onChanged: (val) => val == null ? null : _changeRole(u['id'] as int, val),
                            ),
                            OutlinedButton.icon(
                              onPressed: () => _changeEmail(u['id'] as int),
                              icon: const Icon(Icons.email_outlined),
                              label: const Text('Email'),
                            ),
                            FilledButton.icon(
                              style: FilledButton.styleFrom(backgroundColor: Colors.red.shade600),
                              onPressed: () => _deleteUser(u['id'] as int),
                              icon: const Icon(Icons.delete_outline),
                              label: const Text('Delete'),
                            ),
                          ],
                        ),
                      ),
                    );
                  },
                ),
        ),
      ]),
    );
  }
}
