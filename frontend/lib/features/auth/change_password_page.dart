import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../providers/auth_provider.dart';

class ChangePasswordPage extends ConsumerStatefulWidget {
  const ChangePasswordPage({super.key});
  @override
  ConsumerState<ChangePasswordPage> createState() => _ChangePasswordPageState();
}

class _ChangePasswordPageState extends ConsumerState<ChangePasswordPage> {
  final _form = GlobalKey<FormState>();
  final _current = TextEditingController();
  final _new = TextEditingController();
  final _confirm = TextEditingController();

  bool _loading = false;
  String? _error;
  String? _ok;

  Future<void> _submit() async {
    if (!_form.currentState!.validate()) return;
    setState(() { _loading = true; _error = null; _ok = null; });
    try {
      await ref.read(authControllerProvider.notifier).changePassword(_current.text, _new.text);
      setState(() => _ok = 'Password changed');
    } catch (e) {
      setState(() => _error = e.toString());
    } finally {
      setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Change password')),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(20),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          if (_loading) const LinearProgressIndicator(),
          if (_error != null) Container(color: Colors.red.shade50, padding: const EdgeInsets.all(12), child: Text(_error!, style: const TextStyle(color: Colors.red))),
          if (_ok != null) Container(color: Colors.green.shade50, padding: const EdgeInsets.all(12), child: Text(_ok!, style: const TextStyle(color: Colors.green))),
          const SizedBox(height: 12),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Form(
                key: _form,
                child: Column(children: [
                  TextFormField(controller: _current, decoration: const InputDecoration(labelText: 'Current password'), obscureText: true, validator: (v)=> (v==null||v.isEmpty)?'Enter current password':null),
                  TextFormField(controller: _new, decoration: const InputDecoration(labelText: 'New password'), obscureText: true, validator: (v)=> (v==null||v.length<6)?'Min 6 chars':null),
                  TextFormField(controller: _confirm, decoration: const InputDecoration(labelText: 'Confirm new password'), obscureText: true, validator: (v)=> v!=_new.text?'Does not match':null),
                  const SizedBox(height:16),
                  FilledButton(onPressed: _loading?null:_submit, child: const Text('Change')),
                ]),
              ),
            ),
          ),
        ]),
      ),
    );
  }
}
