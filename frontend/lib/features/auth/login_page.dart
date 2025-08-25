import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../providers/auth_provider.dart';

class LoginPage extends ConsumerStatefulWidget {
  const LoginPage({super.key});
  @override
  ConsumerState<LoginPage> createState() => _LoginPageState();
}

class _LoginPageState extends ConsumerState<LoginPage> {
  final _form = GlobalKey<FormState>();
  final _user = TextEditingController();
  final _pass = TextEditingController();
  String? _error;

  Future<void> _submit() async {
    if (!_form.currentState!.validate()) return;
    setState(() => _error = null);
    try {
      final redirect = await ref.read(authControllerProvider.notifier)
          .login(_user.text, _pass.text);
      if (!mounted) return;
      context.go(redirect ?? '/');
    } catch (e) {
      if (!mounted) return;
      setState(() => _error = 'Login failed');
    }
  }

  @override
  Widget build(BuildContext context) {
    final loading = ref.watch(authControllerProvider).loading;

    return Scaffold(
      appBar: AppBar(title: const Text('Chat bot Project')),
      body: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 440),
          child: Card(
            child: Padding(
              padding: const EdgeInsets.all(24),
              child: Form(
                key: _form,
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text('Sign in', style: Theme.of(context).textTheme.titleLarge),
                    const SizedBox(height: 16),
                    TextFormField(
                      controller: _user,
                      decoration: const InputDecoration(labelText: 'Username'),
                      validator: (v) => (v == null || v.isEmpty) ? 'Enter username' : null,
                    ),
                    const SizedBox(height: 12),
                    TextFormField(
                      controller: _pass,
                      decoration: const InputDecoration(labelText: 'Password'),
                      obscureText: true,
                      validator: (v) => (v == null || v.isEmpty) ? 'Enter password' : null,
                    ),
                    const SizedBox(height: 8),
                    Align(
                      alignment: Alignment.centerRight,
                      child: TextButton(
                        onPressed: () => context.go('/forgot-password'),
                        child: const Text('Forgot password?'),
                      ),
                    ),
                    if (_error != null) ...[
                      const SizedBox(height: 8),
                      Text(_error!, style: const TextStyle(color: Colors.red)),
                    ],
                    const SizedBox(height: 8),
                    FilledButton(
                      onPressed: loading ? null : _submit,
                      child: loading
                          ? const SizedBox(
                              width: 16, height: 16,
                              child: CircularProgressIndicator(strokeWidth: 2),
                            )
                          : const Text('Sign in'),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
