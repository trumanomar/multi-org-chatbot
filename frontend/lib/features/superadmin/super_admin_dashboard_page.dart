import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:dio/dio.dart';

import '../../providers/auth_provider.dart';
import '../../data/api_client.dart';

class SuperAdminDashboardPage extends ConsumerStatefulWidget {
  const SuperAdminDashboardPage({super.key});
  @override
  ConsumerState<SuperAdminDashboardPage> createState() => _SuperAdminDashboardPageState();
}

class _SuperAdminDashboardPageState extends ConsumerState<SuperAdminDashboardPage> {
  bool _loading = false;
  String? _error;
  int? _domains;
  int? _admins;
  int? _docs;

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

      // Either call /super-admin/stats or aggregate from individual endpoints.
      final stats = await dio.get('/super-admin/stats');
      final d = stats.data as Map;

      if (!mounted) return;
      setState(() {
        _domains = (d['domains'] ?? 0) as int;
        _admins  = (d['admins'] ?? 0) as int;
        _docs    = (d['docs'] ?? 0) as int;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() => _error = e.toString());
    } finally {
      if (!mounted) return;
      setState(() => _loading = false);
    }
  }

  Widget _kpi(String title, int? value) {
    return Card(
      elevation: 0,
      color: const Color(0xFFF8F5FF),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: SizedBox(
        width: 300,
        height: 120,
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(title, style: const TextStyle(fontWeight: FontWeight.w600)),
            const Spacer(),
            Text(value == null ? '—' : value.toString(),
                style: const TextStyle(fontSize: 28, fontWeight: FontWeight.w700)),
          ]),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(20),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text('Super Admin', style: Theme.of(context).textTheme.headlineSmall),
        const SizedBox(height: 12),
        if (_loading) const LinearProgressIndicator(),
        if (_error != null) Padding(
          padding: const EdgeInsets.only(top: 8),
          child: Text(_error!, style: const TextStyle(color: Colors.red)),
        ),
        const SizedBox(height: 16),
        Wrap(
          spacing: 16,
          runSpacing: 16,
          children: [
            _kpi('Organizations', _domains),
            _kpi('Admins', _admins),
            _kpi('Docs (global)', _docs),
          ],
        ),
        const SizedBox(height: 24),
        Wrap(
          spacing: 12,
          children: [
            FilledButton.icon(
              onPressed: () => context.go('/s/domain-create'),
              icon: const Icon(Icons.apartment),
              label: const Text('Create Domain'),
            ),
            FilledButton.icon(
              onPressed: () => context.go('/s/admin-create'),
              icon: const Icon(Icons.admin_panel_settings),
              label: const Text('Create Admin'),
            ),
            OutlinedButton.icon(
              onPressed: () => context.go('/s/chat-test'),
              icon: const Icon(Icons.chat),
              label: const Text('Test Chat'),
            ),
          ],
        ),
      ]),
    );
  }
}
