import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

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
  
  // Lists for detailed data
  List<Map<String, dynamic>>? _adminsList;
  List<Map<String, dynamic>>? _organizationsList;
  bool _detailsLoading = false;

  @override
  void initState() {
    super.initState();
    _load();
    _loadDetails();
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

  Future<void> _loadDetails() async {
    setState(() { _detailsLoading = true; });
    try {
      final jwt = ref.read(authControllerProvider).jwt!;
      final dio = ApiClient(token: jwt.token).dio;

      // Get admins and organizations data
      final adminsRes = await dio.get('/super-admin/admins'); // Adjust endpoint as needed
      final orgsRes = await dio.get('/super-admin/domains'); // Adjust endpoint as needed

      if (!mounted) return;
      setState(() {
        // Parse admins data
        if (adminsRes.data is Map && adminsRes.data['admins'] is List) {
          _adminsList = (adminsRes.data['admins'] as List)
              .map<Map<String, dynamic>>((admin) => {
                'id': admin['id'],
                'username': admin['username'] ?? admin['name'],
                'email': admin['email'],
                'domain_id': admin['domain_id'],
                'created_at': admin['created_at'],
              })
              .toList();
        } else if (adminsRes.data is List) {
          _adminsList = (adminsRes.data as List)
              .map<Map<String, dynamic>>((admin) => {
                'id': admin['id'],
                'username': admin['username'] ?? admin['name'],
                'email': admin['email'],
                'domain_id': admin['domain_id'],
                'created_at': admin['created_at'],
              })
              .toList();
        }

        // Parse organizations data
        if (orgsRes.data is Map && orgsRes.data['domains'] is List) {
          _organizationsList = (orgsRes.data['domains'] as List)
              .map<Map<String, dynamic>>((org) => {
                'id': org['id'],
                'name': org['name'],
              
              })
              .toList();
        } else if (orgsRes.data is List) {
          _organizationsList = (orgsRes.data as List)
              .map<Map<String, dynamic>>((org) => {
                'id': org['id'],
                'name': org['name'],
               
              })
              .toList();
        }
      });
    } catch (e) {
      print('Error loading details: $e');
      if (!mounted) return;
      setState(() {
        _adminsList = [];
        _organizationsList = [];
      });
    } finally {
      if (!mounted) return;
      setState(() { _detailsLoading = false; });
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

  Widget _adminsListCard() {
    if (_detailsLoading) {
      return Card(
        elevation: 0,
        color: const Color(0xFFE3F2FD),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        child: const Padding(
          padding: EdgeInsets.all(20),
          child: Center(child: CircularProgressIndicator()),
        ),
      );
    }

    if (_adminsList == null || _adminsList!.isEmpty) {
      return Card(
        elevation: 0,
        color: const Color(0xFFE3F2FD),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        child: const Padding(
          padding: EdgeInsets.all(20),
          child: Center(
            child: Text('No admins found', style: TextStyle(fontSize: 16, color: Colors.grey)),
          ),
        ),
      );
    }

    return Card(
      elevation: 0,
      color: const Color(0xFFE3F2FD), // Light blue background
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.admin_panel_settings, color: Color(0xFF1976D2), size: 24),
                const SizedBox(width: 8),
                Text(
                  'Admins (${_adminsList!.length})',
                  style: const TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.w600,
                    color: Color(0xFF1976D2),
                  ),
                ),
                const Spacer(),
                TextButton.icon(
                  onPressed: _loadDetails,
                  icon: const Icon(Icons.refresh, size: 16),
                  label: const Text('Refresh'),
                ),
              ],
            ),
            const SizedBox(height: 16),
            
            // Admins table header
            Container(
              padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 12),
              decoration: BoxDecoration(
                color: const Color(0xFF1976D2).withOpacity(0.1),
                borderRadius: BorderRadius.circular(8),
              ),
              child: const Row(
                children: [
                  Expanded(flex: 2, child: Text('Name', style: TextStyle(fontWeight: FontWeight.w600))),
                  Expanded(flex: 3, child: Text('Email', style: TextStyle(fontWeight: FontWeight.w600))),
                  Expanded(flex: 2, child: Text('Organization', style: TextStyle(fontWeight: FontWeight.w600))),
                  Expanded(flex: 1, child: Text('ID', style: TextStyle(fontWeight: FontWeight.w600))),
                ],
              ),
            ),
            const SizedBox(height: 8),
            
            // Admins list
            Container(
              constraints: const BoxConstraints(maxHeight: 250),
              child: ListView.builder(
                shrinkWrap: true,
                itemCount: _adminsList!.length,
                itemBuilder: (context, index) {
                  final admin = _adminsList![index];
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
                            admin['username'] ?? 'No name',
                            style: const TextStyle(fontWeight: FontWeight.w500),
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                        
                        // Email
                        Expanded(
                          flex: 3,
                          child: Text(
                            admin['email'] ?? 'No email',
                            style: const TextStyle(color: Colors.grey),
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                        
                        // Domain/Organization
                        Expanded(
                          flex: 2,
                          child: Text(
                             'domains ${admin['domain_id']}',
                            style: const TextStyle(
                              color: Colors.blueAccent,
                              fontWeight: FontWeight.w500,
                            ),
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                        
                        // ID
                        Expanded(
                          flex: 1,
                          child: Text(
                            '${admin['id']}',
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

  Widget _organizationsListCard() {
    if (_detailsLoading) {
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

    if (_organizationsList == null || _organizationsList!.isEmpty) {
      return Card(
        elevation: 0,
        color: const Color(0xFFE8F5E8),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        child: const Padding(
          padding: EdgeInsets.all(20),
          child: Center(
            child: Text('No organizations found', style: TextStyle(fontSize: 16, color: Colors.grey)),
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
                const Icon(Icons.apartment, color: Color(0xFF2E7D32), size: 24),
                const SizedBox(width: 8),
                Text(
                  'Organizations (${_organizationsList!.length})',
                  style: const TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.w600,
                    color: Color(0xFF2E7D32),
                  ),
                ),
                const Spacer(),
                TextButton.icon(
                  onPressed: _loadDetails,
                  icon: const Icon(Icons.refresh, size: 16),
                  label: const Text('Refresh'),
                ),
              ],
            ),
            const SizedBox(height: 16),
            
            // Organizations grid
            GridView.builder(
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                crossAxisCount: 2,
                crossAxisSpacing: 16,
                mainAxisSpacing: 16,
                childAspectRatio: 2.5,
              ),
              itemCount: _organizationsList!.length,
              itemBuilder: (context, index) {
                final org = _organizationsList![index];
                return Container(
                  padding: const EdgeInsets.all(16),
                  decoration: BoxDecoration(
                    color: Colors.white.withOpacity(0.7),
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(
                      color: const Color(0xFF2E7D32).withOpacity(0.3),
                    ),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        org['name'] ?? 'Unknown Organization',
                        style: const TextStyle(
                          fontWeight: FontWeight.w600,
                          fontSize: 16,
                        ),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                      const SizedBox(height: 8),
                      if (org['description'] != null && org['description'].toString().isNotEmpty)
                        Text(
                          org['description'],
                          style: const TextStyle(
                            color: Colors.grey,
                            fontSize: 12,
                          ),
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                        ),
                      const Spacer(),
                      Row(
                        children: [
                          Icon(Icons.admin_panel_settings, size: 14, color: Colors.grey[600]),
                          const SizedBox(width: 4),
                          Text('${org['admins_count']} admins', style: const TextStyle(fontSize: 12)),
                          const SizedBox(width: 12),
                          Icon(Icons.people, size: 14, color: Colors.grey[600]),
                          const SizedBox(width: 4),
                          Text('${org['users_count']} users', style: const TextStyle(fontSize: 12)),
                        ],
                      ),
                    ],
                  ),
                );
              },
            ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('Super Admin', style: Theme.of(context).textTheme.headlineSmall),
          const SizedBox(height: 12),
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
              _kpi('Organizations', _domains),
              _kpi('Admins', _admins),
              _kpi('Docs (global)', _docs),
            ],
          ),
          
          const SizedBox(height: 24),
          
          // Action Buttons
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
          
          const SizedBox(height: 32),
          
          // Organizations List
          _organizationsListCard(),
          
          const SizedBox(height: 24),
          
          // Admins List
          _adminsListCard(),
        ],
      ),
    );
  }
}