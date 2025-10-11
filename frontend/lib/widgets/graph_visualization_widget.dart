import 'dart:convert';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:dio/dio.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:shared_preferences/shared_preferences.dart';

class GraphVisualizationWidget extends StatefulWidget {
  final int domainId;
  final String query;
  final List<dynamic>? graphData;
  final bool autoLoad;

  const GraphVisualizationWidget({
    super.key,
    required this.domainId,
    required this.query,
    this.graphData,
    this.autoLoad = true,
  });

  @override
  State<GraphVisualizationWidget> createState() => _GraphVisualizationWidgetState();
}

class _GraphVisualizationWidgetState extends State<GraphVisualizationWidget> {
  bool _isLoading = false;
  String? _error;
  String? _graphImagePath;
  String? _graphImageUrl;
  Map<String, dynamic>? _graphStats;
  Dio? _dio;

  @override
  void initState() {
    super.initState();
    if (widget.autoLoad) {
      _generateGraphVisualization();
    }
  }

Future<Dio> _getDio() async {
  if (_dio != null) return _dio!;
  
  // Get the token from SharedPreferences
  final prefs = await SharedPreferences.getInstance();
  final token = prefs.getString('jwt');
  
  final base = dotenv.env['API_BASE_URL'] ?? 'http://127.0.0.1:8000';
  _dio = Dio(
    BaseOptions(
      baseUrl: base,
      connectTimeout: const Duration(seconds: 30),
      receiveTimeout: const Duration(minutes: 2),
      headers: {
        'Accept': 'application/json',
        if (token != null && token.isNotEmpty) 'Authorization': 'Bearer $token',
      },
    ),
  );
  return _dio!;
}

void _showFullSizeImage(BuildContext context) {
  if (_graphImageUrl == null) return;
  
  showDialog(
    context: context,
    builder: (context) => Dialog(
      backgroundColor: Colors.transparent,
      child: Container(
        constraints: BoxConstraints(
          maxWidth: MediaQuery.of(context).size.width * 0.9,
          maxHeight: MediaQuery.of(context).size.height * 0.9,
        ),
        child: Stack(
          children: [
            // Full-size image
            Center(
              child: Container(
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(12),
                  boxShadow: [
                    BoxShadow(
                      color: Colors.black.withOpacity(0.3),
                      blurRadius: 20,
                      spreadRadius: 5,
                    ),
                  ],
                ),
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(12),
                  child: Image.network(
                    _getFullImageUrl(_graphImageUrl!),
                    fit: BoxFit.contain,
                    loadingBuilder: (context, child, loadingProgress) {
                      if (loadingProgress == null) return child;
                      return Container(
                        width: 400,
                        height: 300,
                        color: Colors.grey.shade100,
                        child: Center(
                          child: Column(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              CircularProgressIndicator(
                                value: loadingProgress.expectedTotalBytes != null
                                    ? loadingProgress.cumulativeBytesLoaded /
                                        loadingProgress.expectedTotalBytes!
                                    : null,
                              ),
                              const SizedBox(height: 16),
                              Text('Loading image...'),
                            ],
                          ),
                        ),
                      );
                    },
                    errorBuilder: (context, error, stackTrace) {
                      return Container(
                        width: 400,
                        height: 300,
                        color: Colors.grey.shade100,
                        child: Center(
                          child: Column(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              Icon(
                                Icons.error_outline,
                                size: 64,
                                color: Colors.red.shade400,
                              ),
                              const SizedBox(height: 16),
                              Text(
                                'Failed to load image',
                                style: TextStyle(color: Colors.red.shade600),
                              ),
                              const SizedBox(height: 8),
                              Text(
                                _graphImageUrl!,
                                style: TextStyle(
                                  color: Colors.grey.shade500,
                                  fontSize: 12,
                                ),
                                textAlign: TextAlign.center,
                              ),
                            ],
                          ),
                        ),
                      );
                    },
                  ),
                ),
              ),
            ),
            // Close button
            Positioned(
              top: 16,
              right: 16,
              child: Container(
                decoration: BoxDecoration(
                  color: Colors.black.withOpacity(0.5),
                  borderRadius: BorderRadius.circular(20),
                ),
                child: IconButton(
                  onPressed: () => Navigator.of(context).pop(),
                  icon: const Icon(
                    Icons.close,
                    color: Colors.white,
                  ),
                  tooltip: 'Close',
                ),
              ),
            ),
            // Image info
            Positioned(
              bottom: 16,
              left: 16,
              right: 16,
              child: Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Colors.black.withOpacity(0.7),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Text(
                  'Graph Visualization - Domain ${widget.domainId}',
                  style: const TextStyle(
                    color: Colors.white,
                    fontWeight: FontWeight.bold,
                  ),
                  textAlign: TextAlign.center,
                ),
              ),
            ),
          ],
        ),
      ),
    ),
  );
}

String _getFullImageUrl(String imageUrl) {
  final base = dotenv.env['API_BASE_URL'] ?? 'http://127.0.0.1:8000';
  // If imageUrl already starts with http, return as is
  if (imageUrl.startsWith('http')) {
    return imageUrl;
  }
  // Otherwise, prepend the base URL
  return '$base$imageUrl';
}

  Future<void> _generateGraphVisualization() async {
    if (_isLoading) return;
    
    // Check if domain ID is valid
    if (widget.domainId <= 0) {
      setState(() {
        _error = 'Invalid domain ID (${widget.domainId}). Please log out and log back in, or make sure you are assigned to a domain.';
        _isLoading = false;
      });
      return;
    }
    
    setState(() {
      _isLoading = true;
      _error = null;
    });

    try {
      final dio = await _getDio();
      
      // Call the graph visualization endpoint
      final response = await dio.post(
        '/graph/visualize/${widget.domainId}',
        data: {
          'query': widget.query,
          'layout': 'spring',
          'node_size': 300,
          'font_size': 8,
        },
      );

      if (response.statusCode == 200) {
        final data = response.data;
        setState(() {
          _graphImagePath = data['image_path'];
          _graphImageUrl = data['image_url'] ?? data['image_path']; // Use URL if available, fallback to path
          _graphStats = data['stats'];
        });
      } else {
        setState(() {
          _error = 'Failed to generate graph visualization';
        });
      }
    } catch (e) {
      setState(() {
        _error = 'Error generating graph: $e';
      });
    } finally {
      setState(() {
        _isLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.symmetric(vertical: 8),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header
            Row(
              children: [
                Icon(
                  Icons.account_tree,
                  color: Theme.of(context).primaryColor,
                  size: 20,
                ),
                const SizedBox(width: 8),
                Text(
                  'Knowledge Graph Visualization',
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const SizedBox(width: 8),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                  decoration: BoxDecoration(
                    color: Theme.of(context).primaryColor.withOpacity(0.1),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Text(
                    'Domain ${widget.domainId}',
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: Theme.of(context).primaryColor,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
                const Spacer(),
                if (_isLoading)
                  const SizedBox(
                    width: 16,
                    height: 16,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                else if (_error != null)
                  IconButton(
                    onPressed: _generateGraphVisualization,
                    icon: const Icon(Icons.refresh),
                    tooltip: 'Retry',
                  ),
              ],
            ),
            
            const SizedBox(height: 12),
            
            // Graph Stats
            if (_graphStats != null) ...[
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Colors.blue.shade50,
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: Colors.blue.shade200),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Graph Statistics',
                      style: Theme.of(context).textTheme.titleSmall?.copyWith(
                        fontWeight: FontWeight.bold,
                        color: Colors.blue.shade700,
                      ),
                    ),
                    const SizedBox(height: 8),
                    Row(
                      children: [
                        _buildStatItem('Nodes', _graphStats!['total_nodes'] ?? 0),
                        const SizedBox(width: 16),
                        _buildStatItem('Edges', _graphStats!['total_edges'] ?? 0),
                        const SizedBox(width: 16),
                        _buildStatItem('Components', _graphStats!['connected_components'] ?? 0),
                      ],
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 12),
            ],
            
            // Graph Visualization
            if (_isLoading)
              Container(
                height: 300,
                decoration: BoxDecoration(
                  color: Colors.grey.shade100,
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: Colors.grey.shade300),
                ),
                child: const Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      CircularProgressIndicator(),
                      SizedBox(height: 16),
                      Text('Generating graph visualization...'),
                    ],
                  ),
                ),
              )
            else if (_error != null)
              Container(
                height: 200,
                decoration: BoxDecoration(
                  color: Colors.red.shade50,
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: Colors.red.shade200),
                ),
                child: Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(
                        Icons.error_outline,
                        color: Colors.red.shade600,
                        size: 48,
                      ),
                      const SizedBox(height: 16),
                      Text(
                        _error!,
                        style: TextStyle(color: Colors.red.shade600),
                        textAlign: TextAlign.center,
                      ),
                      const SizedBox(height: 16),
                      ElevatedButton.icon(
                        onPressed: _generateGraphVisualization,
                        icon: const Icon(Icons.refresh),
                        label: const Text('Retry'),
                      ),
                    ],
                  ),
                ),
              )
            else if (_graphImagePath != null)
              Container(
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: Colors.grey.shade300),
                ),
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(8),
                  child: Column(
                    children: [
                      // Actual graph visualization image
                      Container(
                        height: 400,
                        child: _graphImageUrl != null
                            ? Image.network(
                                _getFullImageUrl(_graphImageUrl!),
                                fit: BoxFit.contain,
                                loadingBuilder: (context, child, loadingProgress) {
                                  if (loadingProgress == null) return child;
                                  return Center(
                                    child: CircularProgressIndicator(
                                      value: loadingProgress.expectedTotalBytes != null
                                          ? loadingProgress.cumulativeBytesLoaded /
                                              loadingProgress.expectedTotalBytes!
                                          : null,
                                    ),
                                  );
                                },
                                errorBuilder: (context, error, stackTrace) {
                                  return Container(
                                    color: Colors.grey.shade100,
                                    child: Center(
                                      child: Column(
                                        mainAxisAlignment: MainAxisAlignment.center,
                                        children: [
                                          Icon(
                                            Icons.error_outline,
                                            size: 64,
                                            color: Colors.red.shade400,
                                          ),
                                          const SizedBox(height: 16),
                                          Text(
                                            'Failed to load graph image',
                                            style: Theme.of(context).textTheme.titleMedium?.copyWith(
                                              color: Colors.red.shade600,
                                            ),
                                          ),
                                          const SizedBox(height: 8),
                                          Text(
                                            'URL: $_graphImageUrl',
                                            style: Theme.of(context).textTheme.bodySmall?.copyWith(
                                              color: Colors.grey.shade500,
                                            ),
                                            textAlign: TextAlign.center,
                                          ),
                                        ],
                                      ),
                                    ),
                                  );
                                },
                              )
                            : Container(
                                color: Colors.grey.shade100,
                                child: Center(
                                  child: Column(
                                    mainAxisAlignment: MainAxisAlignment.center,
                                    children: [
                                      Icon(
                                        Icons.account_tree,
                                        size: 64,
                                        color: Colors.grey.shade400,
                                      ),
                                      const SizedBox(height: 16),
                                      Text(
                                        'Graph Visualization',
                                        style: Theme.of(context).textTheme.titleMedium?.copyWith(
                                          color: Colors.grey.shade600,
                                        ),
                                      ),
                                      const SizedBox(height: 8),
                                      Text(
                                        'Image path: $_graphImagePath',
                                        style: Theme.of(context).textTheme.bodySmall?.copyWith(
                                          color: Colors.grey.shade500,
                                        ),
                                        textAlign: TextAlign.center,
                                      ),
                                    ],
                                  ),
                                ),
                              ),
                      ),
                      // Controls
                      Container(
                        padding: const EdgeInsets.all(12),
                        color: Colors.grey.shade50,
                        child: Row(
                          children: [
                            IconButton(
                              onPressed: _generateGraphVisualization,
                              icon: const Icon(Icons.refresh),
                              tooltip: 'Regenerate',
                            ),
                            IconButton(
                              onPressed: () {
                                // TODO: Implement download functionality
                                ScaffoldMessenger.of(context).showSnackBar(
                                  const SnackBar(
                                    content: Text('Download functionality not implemented yet'),
                                  ),
                                );
                              },
                              icon: const Icon(Icons.download),
                              tooltip: 'Download',
                            ),
                            const Spacer(),
                            TextButton.icon(
                              onPressed: _graphImageUrl != null ? () {
                                _showFullSizeImage(context);
                              } : null,
                              icon: const Icon(Icons.fullscreen),
                              label: const Text('View Full Size'),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
              )
            else
              Container(
                height: 200,
                decoration: BoxDecoration(
                  color: Colors.grey.shade100,
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: Colors.grey.shade300),
                ),
                child: Center(
                  child: ElevatedButton.icon(
                    onPressed: _generateGraphVisualization,
                    icon: const Icon(Icons.play_arrow),
                    label: const Text('Generate Graph'),
                  ),
                ),
              ),
            
            // Graph Data Summary (if available)
            if (widget.graphData != null && widget.graphData!.isNotEmpty) ...[
              const SizedBox(height: 12),
              const Divider(),
              const SizedBox(height: 8),
              Text(
                'Graph Data Summary',
                style: Theme.of(context).textTheme.titleSmall?.copyWith(
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(height: 8),
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Colors.green.shade50,
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: Colors.green.shade200),
                ),
                child: Text(
                  'Found ${widget.graphData!.length} graph relationships related to your query.',
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: Colors.green.shade700,
                  ),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildStatItem(String label, int value) {
    return Column(
      children: [
        Text(
          value.toString(),
          style: Theme.of(context).textTheme.titleMedium?.copyWith(
            fontWeight: FontWeight.bold,
            color: Colors.blue.shade700,
          ),
        ),
        Text(
          label,
          style: Theme.of(context).textTheme.bodySmall?.copyWith(
            color: Colors.blue.shade600,
          ),
        ),
      ],
    );
  }
}
