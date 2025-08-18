import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

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
  
  // Users list variables
  List<Map<String, dynamic>>? _usersList;
  bool _usersLoading = false;

  @override
  void initState() {
    super.initState();
    _loadCounts();
    _loadUsers();
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

  Future<void> _loadUsers() async {
    setState(() { _usersLoading = true; });
    try {
      final jwt = ref.read(authControllerProvider).jwt!;
      final dio = ApiClient(token: jwt.token).dio;

      // Get users from your existing API
      final usersRes = await dio.get('/admin/users');
      final usersData = usersRes.data;

      List<Map<String, dynamic>> usersList = [];
      
      if (usersData is Map && usersData['users'] is List) {
        usersList = (usersData['users'] as List)
            .map<Map<String, dynamic>>((user) => {
              'id': user['id'],
              'username': user['username'],
              'email': user['email'],
              'role': user['role'],
              'domain_id': user['domain_id'],
              'created_at': user['created_at'],
            })
            .toList();
      }

      if (!mounted) return;
      setState(() {
        _usersList = usersList;
      });
    } catch (e) {
      print('Error loading users: $e');
      if (!mounted) return;
      setState(() {
        _usersList = [];
      });
    } finally {
      if (!mounted) return;
      setState(() { _usersLoading = false; });
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

  Widget _usersListCard() {
    if (_usersLoading) {
      return Card(
        elevation: 0,
        color: const Color(0xFFE8F5E8),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        child: const Padding(
          padding: EdgeInsets.all(20),
          child: Center(
            child: CircularProgressIndicator(),
          ),
        ),
      );
    }

    if (_usersList == null || _usersList!.isEmpty) {
      return Card(
        elevation: 0,
        color: const Color(0xFFE8F5E8),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        child: const Padding(
          padding: EdgeInsets.all(20),
          child: Center(
            child: Text(
              'No users found under your domain',
              style: TextStyle(fontSize: 16, color: Colors.grey),
            ),
          ),
        ),
      );
    }

    return Card(
      elevation: 0,
      color: const Color(0xFFE8F5E8), // Light green background
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.people, color: Color(0xFF2E7D32), size: 24),
                const SizedBox(width: 8),
                Text(
                  'Users in Your Domain (${_usersList!.length})',
                  style: const TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.w600,
                    color: Color(0xFF2E7D32),
                  ),
                ),
                const Spacer(),
                TextButton.icon(
                  onPressed: _loadUsers,
                  icon: const Icon(Icons.refresh, size: 16),
                  label: const Text('Refresh'),
                ),
              ],
            ),
            const SizedBox(height: 16),
            
            // Users table header
            Container(
              padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 12),
              decoration: BoxDecoration(
                color: const Color(0xFF2E7D32).withOpacity(0.1),
                borderRadius: BorderRadius.circular(8),
              ),
              child: const Row(
                children: [
                  Expanded(flex: 2, child: Text('Name', style: TextStyle(fontWeight: FontWeight.w600))),
                  Expanded(flex: 3, child: Text('Email', style: TextStyle(fontWeight: FontWeight.w600))),
                  Expanded(flex: 1, child: Text('Role', style: TextStyle(fontWeight: FontWeight.w600))),
                  Expanded(flex: 1, child: Text('ID', style: TextStyle(fontWeight: FontWeight.w600))),
                ],
              ),
            ),
            const SizedBox(height: 8),
            
            // Users list
            Container(
              constraints: const BoxConstraints(maxHeight: 300),
              child: ListView.builder(
                shrinkWrap: true,
                itemCount: _usersList!.length,
                itemBuilder: (context, index) {
                  final user = _usersList![index];
                  return Container(
                    padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 12),
                    margin: const EdgeInsets.only(bottom: 4),
                    decoration: BoxDecoration(
                      color: Colors.white.withOpacity(0.7),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Row(
                      children: [
                        // Username
                        Expanded(
                          flex: 2,
                          child: Text(
                            user['username'] ?? 'No name',
                            style: const TextStyle(fontWeight: FontWeight.w500),
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                        
                        // Email
                        Expanded(
                          flex: 3,
                          child: Text(
                            user['email'] ?? 'No email',
                            style: const TextStyle(color: Colors.grey),
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                        
                        // Role
                        Expanded(
                          flex: 1,
                          child: Container(
                            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                            decoration: BoxDecoration(
                              color: const Color(0xFF2E7D32),
                              borderRadius: BorderRadius.circular(12),
                            ),
                            child: Text(
                              user['role'] ?? 'User',
                              style: const TextStyle(
                                color: Colors.white,
                                fontSize: 12,
                                fontWeight: FontWeight.w500,
                              ),
                              textAlign: TextAlign.center,
                              overflow: TextOverflow.ellipsis,
                            ),
                          ),
                        ),
                        
                        // ID
                        Expanded(
                          flex: 1,
                          child: Text(
                            '${user['id']}',
                            style: const TextStyle(
                              color: Colors.grey,
                              fontSize: 12,
                            ),
                            textAlign: TextAlign.center,
                          ),
                        ),
                      ],
                    ),
                  );
                },
              ),
            ),
          ],
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
        
        // KPI Cards
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