import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:dio/dio.dart';

import '../../providers/auth_provider.dart';
import '../../data/api_client.dart';

class AdminDashboardPage extends ConsumerStatefulWidget {
  const AdminDashboardPage({super.key});
  @override
  ConsumerState<AdminDashboardPage> createState() => _AdminDashboardPageState();
}

class _AdminDashboardPageState extends ConsumerState<AdminDashboardPage> {
  bool _loading = false;
  String? _error;
  int? _docsCount;
  int? _usersCount;
  int? _unresolvedCount; // optional

  @override
  void initState() {
    super.initState();
    _loadCounts();
  }

  Future<void> _loadCounts() async {
    setState(() { _loading = true; _error = null; });
    try {
      final jwt = ref.read(authControllerProvider).jwt!;
      final dio = ApiClient(token: jwt.token).dio;

      final docsF  = dio.get('/admin/docs');
      final usersF = dio.get('/admin/users');

      final docsRes  = await docsF;
      final usersRes = await usersF;

      final docsData  = docsRes.data;
      final usersData = usersRes.data;

      final docsCount  = (docsData is Map && docsData['docs'] is List) ? (docsData['docs'] as List).length
                       : (docsData is List ? docsData.length : 0);

      final usersCount = (usersData is Map && usersData['users'] is List) ? (usersData['users'] as List).length
                       : (usersData is List ? usersData.length : 0);

      if (!mounted) return;
      setState(() {
        _docsCount  = docsCount;
        _usersCount = usersCount;
        _unresolvedCount = 0;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() => _error = e.toString());
    } finally {
      if (!mounted) return;
      setState(() => _loading = false);
    }
  }

  Widget _kpiCard(String title, int? value) {
    return Card(
      elevation: 0,
      color: const Color(0xFFF8F5FF),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: SizedBox(
        width: 260,
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
        Text('Admin Dashboard', style: Theme.of(context).textTheme.headlineSmall),
        const SizedBox(height: 16),
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
            _kpiCard('Documents', _docsCount),
            _kpiCard('Users', _usersCount),
            _kpiCard('Unresolved Qs', _unresolvedCount),
          ],
        ),
      ]),
    );
  }
}
