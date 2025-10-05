// lib/widgets/database_query_widget.dart
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../services/mysql_mcp_service.dart';

class DatabaseQueryWidget extends StatefulWidget {
  final int domainId;
  
  const DatabaseQueryWidget({
    super.key,
    required this.domainId,
  });

  @override
  State<DatabaseQueryWidget> createState() => _DatabaseQueryWidgetState();
}

class _DatabaseQueryWidgetState extends State<DatabaseQueryWidget> {
  final MySQLMCPService _mysqlService = MySQLMCPService();
  final TextEditingController _queryController = TextEditingController();
  final TextEditingController _paramsController = TextEditingController();
  
  List<Map<String, dynamic>> _results = [];
  bool _loading = false;
  String? _error;
  bool _isExpanded = false;
  int _rowCount = 0;
  List<String> _columns = [];

  // Predefined query templates - will be initialized in initState
  List<Map<String, String>> _queryTemplates = [];

  @override
  void initState() {
    super.initState();
    _initializeQueryTemplates();
  }

  void _initializeQueryTemplates() {
    _queryTemplates = [
      {
        'name': 'Recent Chat Messages',
        'query': '''
          SELECT 
            cm.id,
            cm.question,
            cm.answer,
            cm.created_at,
            u.username,
            cs.id as session_id
          FROM chat_messages cm
          JOIN chat_sessions cs ON cm.session_id = cs.id
          JOIN users u ON cm.user_id = u.id
          WHERE cs.domain_id = :domain_id
          ORDER BY cm.created_at DESC
          LIMIT 10
        ''',
        'params': '{"domain_id": ${widget.domainId}}',
      },
      {
        'name': 'User Activity Summary',
        'query': '''
          SELECT 
            u.id,
            u.username,
            u.email,
            u.role_based,
            COUNT(DISTINCT cs.id) as session_count,
            COUNT(DISTINCT cm.id) as message_count,
            COUNT(DISTINCT d.id) as documents_uploaded
          FROM users u
          LEFT JOIN chat_sessions cs ON u.id = cs.user_id
          LEFT JOIN chat_messages cm ON cs.id = cm.session_id
          LEFT JOIN docs d ON u.id = d.user_id
          WHERE u.domain_id = :domain_id
          GROUP BY u.id, u.username, u.email, u.role_based
          ORDER BY message_count DESC
        ''',
        'params': '{"domain_id": ${widget.domainId}}',
      },
      {
        'name': 'Document Statistics',
        'query': '''
          SELECT 
            d.id,
            d.name,
            d.created_at,
            u.username as uploaded_by,
            COUNT(c.id) as chunk_count
          FROM docs d
          JOIN users u ON d.user_id = u.id
          LEFT JOIN chunks c ON d.id = c.doc_id
          WHERE d.domain_id = :domain_id AND d.active = 1
          GROUP BY d.id, d.name, d.created_at, u.username
          ORDER BY d.created_at DESC
        ''',
        'params': '{"domain_id": ${widget.domainId}}',
      },
      {
        'name': 'Feedback Analysis',
        'query': '''
          SELECT 
            f.id,
            f.rating,
            f.content,
            f.question,
            f.created_at,
            u.username
          FROM feedback f
          JOIN users u ON f.user_id = u.id
          WHERE f.domain_id = :domain_id
          ORDER BY f.created_at DESC
          LIMIT 20
        ''',
        'params': '{"domain_id": ${widget.domainId}}',
      },
    ];
  }

  @override
  void dispose() {
    _queryController.dispose();
    _paramsController.dispose();
    super.dispose();
  }

  Future<void> _executeQuery() async {
    final query = _queryController.text.trim();
    if (query.isEmpty) return;

    setState(() {
      _loading = true;
      _error = null;
      _results = [];
      _columns = [];
      _rowCount = 0;
    });

    try {
      Map<String, dynamic>? parameters;
      
      // Parse parameters if provided
      final paramsText = _paramsController.text.trim();
      if (paramsText.isNotEmpty) {
        try {
          parameters = jsonDecode(paramsText) as Map<String, dynamic>;
        } catch (e) {
          setState(() {
            _error = 'Invalid JSON parameters: $e';
            _loading = false;
          });
          return;
        }
      }

      final result = await _mysqlService.query(query, parameters: parameters);
      
      if (result['success']) {
        setState(() {
          _results = List<Map<String, dynamic>>.from(result['data'] ?? []);
          _columns = List<String>.from(result['columns'] ?? []);
          _rowCount = result['row_count'] ?? 0;
          _loading = false;
        });
      } else {
        setState(() {
          _error = result['message'] ?? 'Query failed';
          _loading = false;
        });
      }
    } catch (e) {
      setState(() {
        _error = e.toString();
        _loading = false;
      });
    }
  }

  void _loadTemplate(Map<String, String> template) {
    _queryController.text = template['query']!;
    _paramsController.text = template['params']!;
  }

  Widget _buildResultsTable() {
    if (_results.isEmpty) {
      return const Center(
        child: Text('No results to display'),
      );
    }

    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      child: DataTable(
        columns: _columns.map((column) => DataColumn(
          label: Text(
            column,
            style: const TextStyle(fontWeight: FontWeight.bold),
          ),
        )).toList(),
        rows: _results.map((row) => DataRow(
          cells: _columns.map((column) => DataCell(
            Text(
              (row[column] ?? '').toString(),
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
            ),
          )).toList(),
        )).toList(),
      ),
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
            leading: const Icon(Icons.query_stats),
            title: const Text('Database Query'),
            subtitle: Text('Domain ${widget.domainId} - Direct SQL Access'),
            trailing: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                IconButton(
                  icon: Icon(_isExpanded ? Icons.expand_less : Icons.expand_more),
                  onPressed: () {
                    setState(() {
                      _isExpanded = !_isExpanded;
                    });
                  },
                ),
              ],
            ),
          ),
          if (_isExpanded) ...[
            const Divider(),
            Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Query Templates
                  Text(
                    'Query Templates:',
                    style: Theme.of(context).textTheme.titleSmall?.copyWith(
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  const SizedBox(height: 8),
                  Wrap(
                    spacing: 8,
                    runSpacing: 4,
                    children: _queryTemplates.map((template) => ActionChip(
                      label: Text(template['name']!),
                      onPressed: () => _loadTemplate(template),
                    )).toList(),
                  ),
                  const SizedBox(height: 16),

                  // SQL Query Input
                  TextField(
                    controller: _queryController,
                    maxLines: 6,
                    decoration: const InputDecoration(
                      labelText: 'SQL Query (SELECT only)',
                      hintText: 'Enter your SELECT query here...',
                      border: OutlineInputBorder(),
                    ),
                  ),
                  const SizedBox(height: 12),

                  // Parameters Input
                  TextField(
                    controller: _paramsController,
                    maxLines: 2,
                    decoration: const InputDecoration(
                      labelText: 'Parameters (JSON)',
                      hintText: '{"param1": "value1", "param2": "value2"}',
                      border: OutlineInputBorder(),
                    ),
                  ),
                  const SizedBox(height: 16),

                  // Execute Button
                  Row(
                    children: [
                      ElevatedButton.icon(
                        onPressed: _loading ? null : _executeQuery,
                        icon: _loading 
                          ? const SizedBox(
                              width: 16,
                              height: 16,
                              child: CircularProgressIndicator(strokeWidth: 2),
                            )
                          : const Icon(Icons.play_arrow),
                        label: Text(_loading ? 'Executing...' : 'Execute Query'),
                      ),
                      const SizedBox(width: 8),
                      if (_rowCount > 0)
                        Text(
                          'Results: $_rowCount rows',
                          style: Theme.of(context).textTheme.bodySmall,
                        ),
                    ],
                  ),
                  const SizedBox(height: 16),

                  // Error Display
                  if (_error != null)
                    Container(
                      width: double.infinity,
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

                  // Results Display
                  if (_results.isNotEmpty) ...[
                    const SizedBox(height: 16),
                    Text(
                      'Query Results:',
                      style: Theme.of(context).textTheme.titleSmall?.copyWith(
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    const SizedBox(height: 8),
                    Container(
                      constraints: const BoxConstraints(maxHeight: 400),
                      decoration: BoxDecoration(
                        border: Border.all(color: Colors.grey.shade300),
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: _buildResultsTable(),
                    ),
                  ],
                ],
              ),
            ),
          ],
        ],
      ),
    );
  }
}
