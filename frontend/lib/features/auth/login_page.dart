import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../providers/auth_provider.dart';
import '../../core/role.dart';

class LoginPage extends ConsumerStatefulWidget {
  const LoginPage({super.key});

  @override
  ConsumerState<LoginPage> createState() => _LoginPageState();
}

class _LoginPageState extends ConsumerState<LoginPage> {
  final _form = GlobalKey<FormState>();
  final _user = TextEditingController();
  final _pass = TextEditingController();
  bool _loading = false;
  String? _error;

  @override
  void dispose() {
    _user.dispose();
    _pass.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_form.currentState!.validate()) return;

    if (!mounted) return; // extra safety
    setState(() {
      _loading = true;
      _error = null;
    });

    try {
      // This calls your notifier, stores JWT, and sets role.
      await ref
          .read(authControllerProvider.notifier)
          .login(_user.text.trim(), _pass.text.trim());

      final role = ref.read(authControllerProvider).role;
      if (!mounted) return; // guard before navigating

      switch (role) {
        case UserRole.user:
          context.go('/u/chat');
          break;
        case UserRole.admin:
          context.go('/a/dashboard');
          break;
        case UserRole.superAdmin:
          context.go('/s/dashboard');
          break;
        default:
          context.go('/');
      }
    } catch (_) {
      if (!mounted) return;
      setState(() => _error = 'Login failed');
    } finally {
      if (!mounted) return;
      setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 420),
            child: Card(
              elevation: 0,
              margin: const EdgeInsets.all(24),
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: Form(
                  key: _form,
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Text('Sign in',
                          style: Theme.of(context).textTheme.headlineSmall),
                      const SizedBox(height: 16),
                      TextFormField(
                        controller: _user,
                        decoration:
                            const InputDecoration(labelText: 'Username'),
                        textInputAction: TextInputAction.next,
                        validator: (v) =>
                            (v == null || v.isEmpty) ? 'Enter username' : null,
                      ),
                      const SizedBox(height: 12),
                      TextFormField(
                        controller: _pass,
                        decoration:
                            const InputDecoration(labelText: 'Password'),
                        obscureText: true,
                        onFieldSubmitted: (_) => _submit(),
                        validator: (v) =>
                            (v == null || v.isEmpty) ? 'Enter password' : null,
                      ),
                      const SizedBox(height: 16),
                      if (_error != null) ...[
                        Text(_error!,
                            style: const TextStyle(color: Colors.red)),
                        const SizedBox(height: 8),
                      ],
                      SizedBox(
                        width: double.infinity,
                        child: FilledButton(
                          onPressed: _loading ? null : _submit,
                          child: _loading
                              ? const SizedBox(
                                  width: 16,
                                  height: 16,
                                  child: CircularProgressIndicator(
                                      strokeWidth: 2),
                                )
                              : const Text('Sign in'),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
