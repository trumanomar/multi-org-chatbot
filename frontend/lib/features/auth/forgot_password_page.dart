import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import '../../data/api_client.dart';

class ForgotPasswordPage extends StatefulWidget {
  const ForgotPasswordPage({super.key});
  @override
  State<ForgotPasswordPage> createState() => _ForgotPasswordPageState();
}

class _ForgotPasswordPageState extends State<ForgotPasswordPage> {
  final _u = TextEditingController();
  final _t = TextEditingController();
  final _n = TextEditingController();
  String? _msg;
  bool _loading = false;

  Future<void> _request() async {
    setState(() { _loading = true; _msg = null; });
    try {
      final dio = ApiClient().dio;
      await dio.post('/user/forgot-password',
          data: {'username': _u.text.trim()},
          options: ApiClient.jsonOpts);
      setState(() => _msg = 'Reset token sent (check email / server logs).');
    } on DioException catch (e) {
      setState(() => _msg = e.response?.data?.toString() ?? e.message ?? 'Error');
    } finally {
      setState(() => _loading = false);
    }
  }

  Future<void> _reset() async {
    setState(() { _loading = true; _msg = null; });
    try {
      final dio = ApiClient().dio;
      await dio.post('/user/reset-password',
          data: {'token': _t.text.trim(), 'new_password': _n.text.trim()},
          options: ApiClient.jsonOpts);
      setState(() => _msg = 'Password reset. You can log in now.');
    } on DioException catch (e) {
      setState(() => _msg = e.response?.data?.toString() ?? e.message ?? 'Error');
    } finally {
      setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Forgot password')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Text('Request token', style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 8),
          TextField(controller: _u, decoration: const InputDecoration(labelText: 'Username or email')),
          const SizedBox(height: 8),
          FilledButton(onPressed: _loading ? null : _request, child: const Text('Request')),
          const Divider(height: 32),
          Text('Apply token', style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 8),
          TextField(controller: _t, decoration: const InputDecoration(labelText: 'Token')),
          const SizedBox(height: 8),
          TextField(controller: _n, decoration: const InputDecoration(labelText: 'New password'), obscureText: true),
          const SizedBox(height: 8),
          FilledButton(onPressed: _loading ? null : _reset, child: const Text('Reset')),
          if (_loading) const Padding(padding: EdgeInsets.only(top: 12), child: LinearProgressIndicator()),
          if (_msg != null) Padding(padding: const EdgeInsets.only(top: 8), child: Text(_msg!)),
        ],
      ),
    );
  }
}
