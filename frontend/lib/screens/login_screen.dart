import 'package:flutter/material.dart';
import '../routes.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});
  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _email = TextEditingController();
  final _password = TextEditingController();
  bool _loading = false;

  Future<void> _doLogin() async {
    // Simulate auth, then go to CHAT (user case)
    setState(() => _loading = true);
    await Future.delayed(const Duration(milliseconds: 300));
    if (!mounted) return;
    setState(() => _loading = false);
    Navigator.pushReplacementNamed(context, AppRoutes.chat); // <-- was dashboard
  }

  void _goToUpload() {
    // Admin case: go straight to UPLOAD
    Navigator.pushNamed(context, AppRoutes.upload);
  }

  @override
  Widget build(BuildContext context) {
    final textTheme = Theme.of(context).textTheme;

    return Scaffold(
      appBar: AppBar(title: const Text('Welcome')),
      body: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 420),
          child: Padding(
            padding: const EdgeInsets.all(20),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Icon(Icons.forum_outlined, size: 56),
                const SizedBox(height: 12),
                Text('Choose how you want to continue', style: textTheme.titleMedium),
                const SizedBox(height: 24),

                // Admin path → Upload
                SizedBox(
                  width: double.infinity,
                  child: OutlinedButton.icon(
                    icon: const Icon(Icons.upload_file),
                    label: const Text('Go to Upload (Admin)'),
                    onPressed: _goToUpload,
                  ),
                ),
                const SizedBox(height: 16),

                // User path → Sign in → Chat
                Align(
                  alignment: Alignment.centerLeft,
                  child: Text('Sign in to chat', style: textTheme.labelLarge),
                ),
                const SizedBox(height: 8),
                TextField(
                  controller: _email,
                  decoration: const InputDecoration(
                    labelText: 'Email',
                    prefixIcon: Icon(Icons.email_outlined),
                  ),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: _password,
                  obscureText: true,
                  decoration: const InputDecoration(
                    labelText: 'Password',
                    prefixIcon: Icon(Icons.lock_outline),
                  ),
                ),
                const SizedBox(height: 16),
                SizedBox(
                  width: double.infinity,
                  child: ElevatedButton.icon(
                    icon: _loading
                        ? const SizedBox(
                            width: 16, height: 16,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          )
                        : const Icon(Icons.login),
                    label: Text(_loading ? 'Signing in…' : 'Sign in'),
                    onPressed: _loading ? null : _doLogin,
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}