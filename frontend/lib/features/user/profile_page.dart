import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:jwt_decoder/jwt_decoder.dart';

import '../../providers/auth_provider.dart';

class ProfilePage extends ConsumerWidget {
  const ProfilePage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final auth = ref.watch(authControllerProvider);
    final token = auth.jwt?.token ?? '';
    Map<String, dynamic> claims = {};
    if (token.isNotEmpty) {
      try {
        claims = JwtDecoder.decode(token);
      } catch (_) {}
    }

    Future<void> logout() async {
      await ref.read(authControllerProvider.notifier).logout();
      if (context.mounted) {
        GoRouter.of(context).go('/login');
      }
    }

    return Scaffold(
      appBar: AppBar(title: const Text('Profile')),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: ListView(
          children: [
            ListTile(
              title: const Text('Username'),
              subtitle: Text((claims['sub'] ?? '-').toString()),
            ),
            ListTile(
              title: const Text('Role'),
              subtitle: Text(auth.role.name),
            ),
            ListTile(
              title: const Text('Domain ID'),
              subtitle: Text((auth.domainId ?? '-').toString()),
            ),
            const Divider(),
            FilledButton.icon(
              onPressed: () => GoRouter.of(context).push('/change-password'),
              icon: const Icon(Icons.lock_reset),
              label: const Text('Change password'),
            ),
            const SizedBox(height: 12),
            OutlinedButton.icon(
              onPressed: logout,
              icon: const Icon(Icons.logout),
              label: const Text('Log out'),
            ),
            const SizedBox(height: 24),
            ExpansionTile(
              title: const Text('Raw token (debug)'),
              children: [
                SelectableText(token.isEmpty ? '—' : token),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
