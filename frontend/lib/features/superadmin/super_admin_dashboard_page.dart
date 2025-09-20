import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
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

  List<Map<String, dynamic>> _adminsList = [];
  List<Map<String, dynamic>> _domainsList = [];
  bool _detailsLoading = false;
  final Set<int> _domainUpdating = {}; // Track which domains are being updated

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
      final r = await dio.get('/super-admin/stats');
      final m = r.data as Map;
      _domains = (m['domains'] ?? 0) as int;
      _admins = (m['admins'] ?? 0) as int;
      _docs = (m['docs'] ?? 0) as int;
    } catch (e) {
      _error = e.toString();
    } finally {
      setState(() => _loading = false);
    }
  }

  Future<void> _loadDetails() async {
    setState(() => _detailsLoading = true);
    try {
      final jwt = ref.read(authControllerProvider).jwt!;
      final dio = ApiClient(token: jwt.token).dio;
      final a = await dio.get('/super-admin/admins');
      final d = await dio.get('/super-admin/domains');
      _adminsList = ((a.data['admins'] as List?) ?? []).cast<Map>().map((e) => Map<String, dynamic>.from(e)).toList();
      _domainsList = ((d.data['domains'] as List?) ?? []).cast<Map>().map((e) => Map<String, dynamic>.from(e)).toList();
    } catch (e) {
      // keep page usable
    } finally {
      setState(() => _detailsLoading = false);
    }
  }

  Future<void> _toggleDomainActivation(int domainId, bool currentStatus) async {
    if (_domainUpdating.contains(domainId)) return;
    
    setState(() => _domainUpdating.add(domainId));
    
    try {
      final jwt = ref.read(authControllerProvider).jwt!;
      final dio = ApiClient(token: jwt.token).dio;
      
      final endpoint = currentStatus 
          ? '/admin/domain/$domainId/deactivate'
          : '/admin/domain/$domainId/activate';
      
      await dio.patch(endpoint);
      
      // Update the local state
      setState(() {
        final index = _domainsList.indexWhere((d) => d['id'] == domainId);
        if (index != -1) {
          _domainsList[index]['active'] = !currentStatus;
        }
      });
      
      // Show success message
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(currentStatus 
                ? 'Domain deactivated successfully' 
                : 'Domain activated successfully'),
            backgroundColor: Colors.green,
            duration: const Duration(seconds: 2),
          ),
        );
      }
    } catch (e) {
      // Show error message
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Failed to update domain: ${e.toString()}'),
            backgroundColor: Colors.red,
            duration: const Duration(seconds: 3),
          ),
        );
      }
    } finally {
      setState(() => _domainUpdating.remove(domainId));
    }
  }

  Widget _kpi(String title, int? value) {
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

  Widget _buildDomainCard(Map<String, dynamic> domain) {
    final domainId = domain['id'] as int;
    final domainName = domain['name'] ?? 'Domain';
    final isActive = domain['active'] ?? false;
    final isUpdating = _domainUpdating.contains(domainId);
    
    return Card(
      elevation: 1,
      margin: const EdgeInsets.symmetric(vertical: 4),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Row(
          children: [
            // Status indicator
            Container(
              width: 12,
              height: 12,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: isActive ? Colors.green : Colors.grey,
              ),
            ),
            const SizedBox(width: 12),
            
            // Domain info
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    domainName,
                    style: const TextStyle(
                      fontWeight: FontWeight.w600,
                      fontSize: 16,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    isActive ? 'Active' : 'Inactive',
                    style: TextStyle(
                      color: isActive ? Colors.green : Colors.grey,
                      fontSize: 12,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ],
              ),
            ),
            
            // Action button
            if (isUpdating)
              const SizedBox(
                width: 20,
                height: 20,
                child: CircularProgressIndicator(strokeWidth: 2),
              )
            else
              TextButton.icon(
                onPressed: () => _toggleDomainActivation(domainId, isActive),
                icon: Icon(
                  isActive ? Icons.toggle_on : Icons.toggle_off,
                  color: isActive ? Colors.green : Colors.grey,
                  size: 20,
                ),
                label: Text(
                  isActive ? 'Deactivate' : 'Activate',
                  style: TextStyle(
                    color: isActive ? Colors.red : Colors.green,
                    fontSize: 12,
                  ),
                ),
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
          if (_error != null)
            Padding(
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
                onPressed: () => Navigator.of(context).pushNamed('/s/domain-create'),
                icon: const Icon(Icons.apartment),
                label: const Text('Create Domain'),
              ),
              FilledButton.icon(
                onPressed: () => Navigator.of(context).pushNamed('/s/admin-create'),
                icon: const Icon(Icons.admin_panel_settings),
                label: const Text('Create Admin'),
              ),
            ],
          ),
          const SizedBox(height: 24),

          // Domains
          Card(
            elevation: 0,
            color: const Color(0xFFE8F5E8),
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Row(
                  children: [
                    const Icon(Icons.apartment, color: Color(0xFF2E7D32)),
                    const SizedBox(width: 8),
                    const Text('Organizations', style: TextStyle(fontWeight: FontWeight.w600)),
                    const Spacer(),
                    IconButton(onPressed: _loadDetails, icon: const Icon(Icons.refresh)),
                  ],
                ),
                if (_detailsLoading) const LinearProgressIndicator(),
                const SizedBox(height: 12),
                _domainsList.isEmpty
                    ? const Padding(
                        padding: EdgeInsets.all(12),
                        child: Text('No organizations found'),
                      )
                    : Column(
                        children: _domainsList.map((d) => _buildDomainCard(d)).toList(),
                      ),
              ]),
            ),
          ),
          const SizedBox(height: 16),

          // Admins
          Card(
            elevation: 0,
            color: const Color(0xFFE3F2FD),
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Row(
                  children: [
                    const Icon(Icons.admin_panel_settings, color: Color(0xFF1976D2)),
                    const SizedBox(width: 8),
                    const Text('Admins', style: TextStyle(fontWeight: FontWeight.w600)),
                    const Spacer(),
                    IconButton(onPressed: _loadDetails, icon: const Icon(Icons.refresh)),
                  ],
                ),
                if (_detailsLoading) const LinearProgressIndicator(),
                const SizedBox(height: 12),
                _adminsList.isEmpty
                    ? const Padding(
                        padding: EdgeInsets.all(12),
                        child: Text('No admins found'),
                      )
                    : Column(
                        children: _adminsList
                            .map((a) => ListTile(
                                  leading: const Icon(Icons.person),
                                  title: Text(a['username'] ?? ''),
                                  subtitle: Text(a['email'] ?? ''),
                                ))
                            .toList(),
                      ),
              ]),
            ),
          ),
        ],
      ),
    );
  }
}