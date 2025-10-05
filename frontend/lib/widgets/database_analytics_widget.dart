// lib/widgets/database_analytics_widget.dart
import 'dart:convert';
import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../providers/auth_provider.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';

class DatabaseAnalyticsWidget extends ConsumerStatefulWidget {
  final int domainId;
  
  const DatabaseAnalyticsWidget({
    super.key,
    required this.domainId,
  });

  @override
  ConsumerState<DatabaseAnalyticsWidget> createState() => _DatabaseAnalyticsWidgetState();
}

class _DatabaseAnalyticsWidgetState extends ConsumerState<DatabaseAnalyticsWidget> {
  Map<String, dynamic>? _analytics;
  bool _loading = false;
  String? _error;
  bool _isExpanded = false;

  @override
  void initState() {
    super.initState();
    // Don't load in initState - load after first build when auth is available
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _loadAnalytics();
    });
  }

  Future<Dio> _getDio() async {
    final base = dotenv.env['API_BASE_URL'] ?? 'http://127.0.0.1:8000';
    final token = ref.read(authControllerProvider).jwt?.token;

    if (token == null || token.isEmpty) {
      throw Exception('Not authenticated');
    }

    return Dio(BaseOptions(
      baseUrl: base,
      connectTimeout: const Duration(seconds: 30),
      receiveTimeout: const Duration(minutes: 2),
      headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'Authorization': 'Bearer $token',
      },
    ));
  }

  Future<void> _loadAnalytics() async {
    if (!mounted) return;
    
    setState(() {
      _loading = true;
      _error = null;
    });

    try {
      final dio = await _getDio();
      
      print('[Analytics] Loading analytics for domain ${widget.domainId}');
      
      final response = await dio.get(
        '/mysql-mcp/domain-analytics',
        queryParameters: {'domain_id': widget.domainId},
      );
      
      print('[Analytics] Response status: ${response.statusCode}');
      print('[Analytics] Response data: ${response.data}');
      
      if (response.statusCode == 200 && response.data['success'] == true) {
        if (!mounted) return;
        setState(() {
          _analytics = response.data;
          _loading = false;
        });
      } else {
        if (!mounted) return;
        setState(() {
          _error = response.data['error'] ?? 'Failed to load analytics';
          _loading = false;
        });
      }
    } catch (e) {
      print('[Analytics] Error: $e');
      if (!mounted) return;
      setState(() {
        _error = 'Error: ${e.toString()}';
        _loading = false;
      });
    }
  }

  Widget _buildStatCard(String title, dynamic value, {IconData? icon, Color? color}) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                if (icon != null) ...[
                  Icon(icon, size: 20, color: color),
                  const SizedBox(width: 8),
                ],
                Expanded(
                  child: Text(
                    title,
                    style: Theme.of(context).textTheme.bodySmall,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Text(
              value?.toString() ?? '0',
              style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                fontWeight: FontWeight.bold,
                color: color,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildAnalyticsContent() {
    if (_analytics == null) return const SizedBox.shrink();

    final userStats = _analytics!['user_stats'] ?? {};
    final docStats = _analytics!['document_stats'] ?? {};
    final chunkStats = _analytics!['chunk_stats'] ?? {};
    final chatStats = _analytics!['chat_stats'] ?? {};
    final feedbackStats = _analytics!['feedback_stats'] ?? {};

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Users Section
        Text(
          'Users',
          style: Theme.of(context).textTheme.titleMedium?.copyWith(
            fontWeight: FontWeight.bold,
          ),
        ),
        const SizedBox(height: 8),
        GridView.count(
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          crossAxisCount: 3,
          childAspectRatio: 2.5,
          crossAxisSpacing: 8,
          mainAxisSpacing: 8,
          children: [
            _buildStatCard(
              'Total Users',
              userStats['user_count'],
              icon: Icons.people,
              color: Colors.blue,
            ),
            _buildStatCard(
              'Admins',
              userStats['admin_count'],
              icon: Icons.admin_panel_settings,
              color: Colors.orange,
            ),
            _buildStatCard(
              'Regular Users',
              userStats['regular_user_count'],
              icon: Icons.person,
              color: Colors.green,
            ),
          ],
        ),
        const SizedBox(height: 16),

        // Documents Section
        Text(
          'Documents',
          style: Theme.of(context).textTheme.titleMedium?.copyWith(
            fontWeight: FontWeight.bold,
          ),
        ),
        const SizedBox(height: 8),
        GridView.count(
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          crossAxisCount: 2,
          childAspectRatio: 2.5,
          crossAxisSpacing: 8,
          mainAxisSpacing: 8,
          children: [
            _buildStatCard(
              'Total Documents',
              docStats['doc_count'],
              icon: Icons.description,
              color: Colors.purple,
            ),
            _buildStatCard(
              'Unique Uploaders',
              docStats['unique_uploaders'],
              icon: Icons.upload,
              color: Colors.teal,
            ),
          ],
        ),
        const SizedBox(height: 16),

        // Chunks Section
        Text(
          'Content Chunks',
          style: Theme.of(context).textTheme.titleMedium?.copyWith(
            fontWeight: FontWeight.bold,
          ),
        ),
        const SizedBox(height: 8),
        GridView.count(
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          crossAxisCount: 2,
          childAspectRatio: 2.5,
          crossAxisSpacing: 8,
          mainAxisSpacing: 8,
          children: [
            _buildStatCard(
              'Total Chunks',
              chunkStats['chunk_count'],
              icon: Icons.view_module,
              color: Colors.indigo,
            ),
            _buildStatCard(
              'Avg Length',
              chunkStats['avg_chunk_length'] != null 
                ? '${double.parse(chunkStats['avg_chunk_length'].toString()).round()} chars'
                : '0 chars',
              icon: Icons.text_fields,
              color: Colors.brown,
            ),
          ],
        ),
        const SizedBox(height: 16),

        // Chat Section
        Text(
          'Chat Activity',
          style: Theme.of(context).textTheme.titleMedium?.copyWith(
            fontWeight: FontWeight.bold,
          ),
        ),
        const SizedBox(height: 8),
        GridView.count(
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          crossAxisCount: 2,
          childAspectRatio: 2.5,
          crossAxisSpacing: 8,
          mainAxisSpacing: 8,
          children: [
            _buildStatCard(
              'Sessions',
              chatStats['session_count'],
              icon: Icons.chat,
              color: Colors.cyan,
            ),
            _buildStatCard(
              'Messages',
              chatStats['message_count'],
              icon: Icons.message,
              color: Colors.pink,
            ),
          ],
        ),
        const SizedBox(height: 16),

        // Feedback Section
        if (feedbackStats['total_feedback'] != null && feedbackStats['total_feedback'] > 0) ...[
          Text(
            'Feedback',
            style: Theme.of(context).textTheme.titleMedium?.copyWith(
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 8),
          GridView.count(
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            crossAxisCount: 2,
            childAspectRatio: 2.5,
            crossAxisSpacing: 8,
            mainAxisSpacing: 8,
            children: [
              _buildStatCard(
                'Total Feedback',
                feedbackStats['total_feedback'],
                icon: Icons.feedback,
                color: Colors.amber,
              ),
              _buildStatCard(
                'Avg Rating',
                feedbackStats['avg_rating'] != null 
                  ? '${double.parse(feedbackStats['avg_rating'].toString()).toStringAsFixed(1)}/5'
                  : 'N/A',
                icon: Icons.star,
                color: Colors.orange,
              ),
            ],
          ),
        ],
      ],
    );
  }

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.all(8),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          ListTile(
            leading: const Icon(Icons.analytics),
            title: const Text('Database Analytics'),
            subtitle: Text('Domain ${widget.domainId} Statistics'),
            trailing: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                if (_loading)
                  const SizedBox(
                    width: 20,
                    height: 20,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                else
                  IconButton(
                    icon: Icon(_isExpanded ? Icons.expand_less : Icons.expand_more),
                    onPressed: () {
                      setState(() {
                        _isExpanded = !_isExpanded;
                      });
                    },
                  ),
                IconButton(
                  icon: const Icon(Icons.refresh),
                  onPressed: _loadAnalytics,
                  tooltip: 'Refresh analytics',
                ),
              ],
            ),
          ),
          if (_error != null)
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
              child: Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Colors.red.shade50,
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: Colors.red.shade200),
                ),
                child: Row(
                  children: [
                    Icon(Icons.error, color: Colors.red.shade600, size: 20),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        _error!,
                        style: TextStyle(color: Colors.red.shade700),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          if (_isExpanded && !_loading && _error == null)
            Padding(
              padding: const EdgeInsets.all(16),
              child: _buildAnalyticsContent(),
            ),
          if (_isExpanded && _loading)
            const Padding(
              padding: EdgeInsets.all(32),
              child: Center(child: CircularProgressIndicator()),
            ),
        ],
      ),
    );
  }
}