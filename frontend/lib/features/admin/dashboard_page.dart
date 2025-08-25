import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:dio/dio.dart';
import 'package:go_router/go_router.dart';

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
  int? _unresolvedCount;

  // Users list (detail)
  List<Map<String, dynamic>>? _usersList;
  bool _usersLoading = false;

  // endpoints (change here if your backend differs)
  static const _docsPath  = '/admin/docs';
  static const _usersPath = '/admin/users'; // tolerate 404 (not implemented)

  @override
  void initState() {
    super.initState();
    _loadCounts();
    _loadUsers();
  }

  // ---------------- helpers ----------------

  List _asList(dynamic data, {String? key}) {
    if (data is List) return data;
    if (data is Map && key != null && data[key] is List) return data[key] as List;
    return const [];
  }

  T? _read<T>(Map m, String k) {
    final v = m[k];
    if (v == null) return null;
    if (T == int) {
      if (v is int) return v as T;
      final n = int.tryParse('$v');
      return n as T?;
    }
    if (T == String) return '$v' as T;
    return v as T?;
  }

  // ---------------- loads ------------------

  Future<void> _loadCounts() async {
    setState(() {
      _loading = true;
      _error = null;
    });

    try {
      final jwt = ref.read(authControllerProvider).jwt!;
      final dio = ApiClient(token: jwt.token).dio;

      // run in parallel
      final Future<Response<dynamic>> docsFuture = dio.get(_docsPath);
      final Future<Response<dynamic>?> usersFuture = dio
          .get(_usersPath)
          .then<Response<dynamic>?>((r) => r)
          .catchError((_) => null); // tolerate /admin/users missing

      final results = await Future.wait<dynamic>([docsFuture, usersFuture]);

      // docs
      final Response<dynamic> docsRes = results[0] as Response<dynamic>;
      final bool docsOk = docsRes.statusCode == 200;
      final docsList = docsOk ? _asList(docsRes.data, key: 'docs') : const [];
      final docsCount = docsList.length;

      // users
      final Response<dynamic>? usersRes = results[1] as Response<dynamic>?;
      int usersCount = 0;
      if (usersRes != null && usersRes.statusCode == 200) {
        final usersList = _asList(usersRes.data, key: 'users');
        usersCount = usersList.length;
      } // else: leave 0 if endpoint missing or errored

      if (!mounted) return;
      setState(() {
        _docsCount = docsCount;
        _usersCount = usersCount;
        _unresolvedCount = 0; // you can wire a real value when backend provides it
      });
    } catch (e) {
      if (!mounted) return;
      setState(() => _error = e.toString());
    } finally {
      if (!mounted) return;
      setState(() => _loading = false);
    }
  }

  Future<void> _loadUsers() async {
    setState(() => _usersLoading = true);
    try {
      final jwt = ref.read(authControllerProvider).jwt!;
      final dio = ApiClient(token: jwt.token).dio;

      // tolerate endpoint missing (404)
      final res = await dio.get(_usersPath);
      List<Map<String, dynamic>> users = [];
      if (res.statusCode == 200) {
        final raw = _asList(res.data, key: 'users');
        users = raw.map<Map<String, dynamic>>((u) {
          final m = (u as Map);
          return {
            'id': _read<int>(m, 'id'),
            'username': _read<String>(m, 'username') ?? '—',
            'email': _read<String>(m, 'email') ?? '—',
            'role': _read<String>(m, 'role') ?? _read<String>(m, 'role_based') ?? 'user',
            'domain_id': _read<int>(m, 'domain_id'),
            'created_at': _read<String>(m, 'created_at'),
          };
        }).toList();
      }
      if (!mounted) return;
      setState(() => _usersList = users);
    } catch (_) {
      // if 404 or any error, just show empty list
      if (!mounted) return;
      setState(() => _usersList = const []);
    } finally {
      if (!mounted) return;
      setState(() => _usersLoading = false);
    }
  }

  // ---------------- UI pieces -------------

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
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(title, style: const TextStyle(fontWeight: FontWeight.w600)),
              const Spacer(),
              Text(
                value == null ? '—' : value.toString(),
                style: const TextStyle(fontSize: 28, fontWeight: FontWeight.w700),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _usersListCard() {
    if (_usersLoading) {
      return Card(
        elevation: 0,
        color: const Color(0xFFE8F5E8),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        child: const Padding(
          padding: EdgeInsets.all(20),
          child: Center(child: CircularProgressIndicator()),
        ),
      );
    }

    final list = _usersList ?? const [];
    if (list.isEmpty) {
      return Card(
        elevation: 0,
        color: const Color(0xFFE8F5E8),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        child: const Padding(
          padding: EdgeInsets.all(20),
          child: Center(
            child: Text('No users found under your domain',
                style: TextStyle(fontSize: 16, color: Colors.grey)),
          ),
        ),
      );
    }

    return Card(
      elevation: 0,
      color: const Color(0xFFE8F5E8),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            const Icon(Icons.people, color: Color(0xFF2E7D32), size: 24),
            const SizedBox(width: 8),
            Text('Users in Your Domain (${list.length})',
                style: const TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.w600,
                  color: Color(0xFF2E7D32),
                )),
            const Spacer(),
            TextButton.icon(
              onPressed: _loadUsers,
              icon: const Icon(Icons.refresh, size: 16),
              label: const Text('Refresh'),
            ),
          ]),
          const SizedBox(height: 16),

          // header
          Container(
            padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 12),
            decoration: BoxDecoration(
              color: const Color(0xFF2E7D32).withValues(alpha: 0.1),
              borderRadius: BorderRadius.circular(8),
            ),
            child: const Row(children: [
              Expanded(flex: 2, child: Text('Name',  style: TextStyle(fontWeight: FontWeight.w600))),
              Expanded(flex: 3, child: Text('Email', style: TextStyle(fontWeight: FontWeight.w600))),
              Expanded(flex: 1, child: Text('Role',  style: TextStyle(fontWeight: FontWeight.w600))),
              Expanded(flex: 1, child: Text('ID',    style: TextStyle(fontWeight: FontWeight.w600))),
            ]),
          ),
          const SizedBox(height: 8),

          // list
          Container(
            constraints: const BoxConstraints(maxHeight: 300),
            child: ListView.builder(
              shrinkWrap: true,
              itemCount: list.length,
              itemBuilder: (_, i) {
                final u = list[i];
                return Container(
                  padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 12),
                  margin: const EdgeInsets.only(bottom: 4),
                  decoration: BoxDecoration(
                    color: Colors.white.withValues(alpha: 0.7),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Row(children: [
                    Expanded(
                      flex: 2,
                      child: Text(
                        u['username'] ?? '—',
                        style: const TextStyle(fontWeight: FontWeight.w500),
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                    Expanded(
                      flex: 3,
                      child: Text(
                        u['email'] ?? '—',
                        style: const TextStyle(color: Colors.grey),
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                    Expanded(
                      flex: 1,
                      child: Container(
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                        decoration: BoxDecoration(
                          color: const Color(0xFF2E7D32),
                          borderRadius: BorderRadius.circular(12),
                        ),
                        child: Text(
                          (u['role'] ?? 'user').toString(),
                          style: const TextStyle(color: Colors.white, fontSize: 12, fontWeight: FontWeight.w500),
                          textAlign: TextAlign.center,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                    ),
                    Expanded(
                      flex: 1,
                      child: Text(
                        '${u['id'] ?? '—'}',
                        style: const TextStyle(color: Colors.grey, fontSize: 12),
                        textAlign: TextAlign.center,
                      ),
                    ),
                  ]),
                );
              },
            ),
          ),
        ]),
      ),
    );
  }

  // ---------------- build -----------------

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(20),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(
          children: [
            Icon(
              Icons.admin_panel_settings,
              size: 32,
              color: Theme.of(context).primaryColor,
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Admin Dashboard',
                    style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  Text(
                    'Admin and Super Admin roles can create users',
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: Theme.of(context).colorScheme.onSurfaceVariant,
                    ),
                  ),
                ],
              ),
            ),
            FilledButton.icon(
              onPressed: () {
                print('Create User button pressed! Navigating to /a/create-user');
                try {
                  // Navigate to create user page
                  GoRouter.of(context).go('/a/create-user');
                } catch (e) {
                  print('Navigation error: $e');
                  // Fallback to Navigator if GoRouter fails
                  Navigator.of(context).pushNamed('/a/create-user');
                }
              },
              icon: const Icon(Icons.person_add, size: 20),
              label: const Text('Create User'),
            ),
          ],
        ),
        const SizedBox(height: 16),
        if (_loading) const LinearProgressIndicator(),
        if (_error != null)
          Padding(
            padding: const EdgeInsets.only(top: 8),
            child: Text(_error!, style: const TextStyle(color: Colors.red)),
          ),
        const SizedBox(height: 16),

        // KPIs
        Wrap(
          spacing: 16,
          runSpacing: 16,
          children: [
            _kpiCard('Documents', _docsCount),
            _kpiCard('Users', _usersCount),
            _kpiCard('Unresolved Qs', _unresolvedCount),
          ],
        ),

        const SizedBox(height: 24),

        // Users List Card
        _usersListCard(),
      ]),
    );
  }
}
