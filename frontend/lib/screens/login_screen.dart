import 'package:flutter/material.dart';
import '../services/api_service.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});
  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _api = ApiService();
  final _email = TextEditingController();
  final _password = TextEditingController();
  bool _loading = false;

  Future<void> _doLogin() async {
    setState(() => _loading = true);
    final ok = await _api.loginAdmin(_email.text.trim(), _password.text.trim());
    setState(() => _loading = false);
    if (!mounted) return;
    if (ok) {
      Navigator.pushReplacementNamed(context, '/dashboard');
    } else {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Login failed')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Admin Login')),
      body: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 380),
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(mainAxisSize: MainAxisSize.min, children: [
              TextField(controller: _email, decoration: const InputDecoration(labelText: 'Email')),
              const SizedBox(height: 12),
              TextField(controller: _password, obscureText: true, decoration: const InputDecoration(labelText: 'Password')),
              const SizedBox(height: 20),
              SizedBox(
                width: double.infinity,
                child: ElevatedButton(
                  onPressed: _loading ? null : _doLogin,
                  child: _loading ? const CircularProgressIndicator() : const Text('Sign in'),
                ),
              ),
            ]),
          ),
        ),
      ),
    );
  }
}
