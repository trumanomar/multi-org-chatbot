// lib/services/mysql_mcp_service.dart
import 'dart:convert';
import 'package:dio/dio.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';

class MySQLMCPService {
  static const String _baseUrl = 'http://127.0.0.1:8000';
  late final Dio _dio;
  final String? authToken;

  MySQLMCPService({this.authToken}) {
    _dio = Dio(BaseOptions(
      baseUrl: _baseUrl,
      connectTimeout: const Duration(seconds: 30),
      receiveTimeout: const Duration(minutes: 2),
      sendTimeout: const Duration(minutes: 2),
      headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        if (authToken != null && authToken!.isNotEmpty) 
          'Authorization': 'Bearer $authToken',
      },
    ));

    _dio.interceptors.add(LogInterceptor(
      requestBody: true,
      responseBody: true,
      logPrint: (obj) => print('[MySQL MCP] $obj'),
    ));
  }

  // Update the token dynamically if needed
  void updateAuthToken(String token) {
    _dio.options.headers['Authorization'] = 'Bearer $token';
  }

  /// Check if MySQL MCP server is healthy
  Future<Map<String, dynamic>> healthCheck() async {
    try {
      final response = await _dio.get('/mysql-mcp/health');
      return response.data;
    } catch (e) {
      throw Exception('MySQL MCP server is not accessible: $e');
    }
  }

  /// Execute a SELECT query
  Future<Map<String, dynamic>> query(String sql, {Map<String, dynamic>? parameters}) async {
    try {
      final response = await _dio.post('/mysql-mcp/query', data: {
        'query': sql,
        if (parameters != null) 'parameters': parameters,
      });
      return response.data;
    } catch (e) {
      throw Exception('Query failed: $e');
    }
  }

  /// Insert data into a table
  Future<Map<String, dynamic>> insert(String table, Map<String, dynamic> data) async {
    try {
      final response = await _dio.post('/mysql-mcp/insert', data: {
        'table': table,
        'data': data,
      });
      return response.data;
    } catch (e) {
      throw Exception('Insert failed: $e');
    }
  }

  /// Update data in a table
  Future<Map<String, dynamic>> update(
    String table,
    Map<String, dynamic> data,
    String whereClause, {
    Map<String, dynamic>? whereParameters,
  }) async {
    try {
      final response = await _dio.post('/mysql-mcp/update', data: {
        'table': table,
        'data': data,
        'where_clause': whereClause,
        if (whereParameters != null) 'where_parameters': whereParameters,
      });
      return response.data;
    } catch (e) {
      throw Exception('Update failed: $e');
    }
  }

  /// Get schema information for all tables
  Future<Map<String, dynamic>> getSchema() async {
    try {
      final response = await _dio.get('/mysql-mcp/schema');
      return response.data;
    } catch (e) {
      throw Exception('Schema query failed: $e');
    }
  }

  /// Get schema information for a specific table
  Future<Map<String, dynamic>> getTableSchema(String tableName) async {
    try {
      final response = await _dio.get('/mysql-mcp/schema?table_name=$tableName');
      return response.data;
    } catch (e) {
      throw Exception('Table schema query failed: $e');
    }
  }

  /// Get comprehensive domain analytics
  Future<Map<String, dynamic>> getDomainAnalytics(int domainId) async {
    try {
      final response = await _dio.get('/mysql-mcp/domain-analytics?domain_id=$domainId');
      return response.data;
    } catch (e) {
      return {
        'success': false,
        'error': e.toString(),
      };
    }
  }

  /// Search for specific content across chunks
  Future<Map<String, dynamic>> searchContent(
    String searchTerm,
    int domainId, {
    int limit = 10,
  }) async {
    try {
      final response = await _dio.post('/mysql-mcp/search-content', data: {
        'search_term': searchTerm,
        'domain_id': domainId,
        'limit': limit,
      });
      return response.data;
    } catch (e) {
      throw Exception('Search failed: $e');
    }
  }
}