//
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../data/api_client.dart';
import '../core/role.dart';

class Jwt {
  final String token;
  final String? subject;
  Jwt(this.token, {this.subject});
}

class AppUser {
  final String? username;
  final String? email;
  final int? id;
  AppUser({this.username, this.email, this.id});
}

class AuthState {
  final bool loading;
  final Jwt? jwt;
  final UserRole role;
  final int? domainId;
  final AppUser? user;

  const AuthState({
    this.loading = false,
    this.jwt,
    this.role = UserRole.user,
    this.domainId,
    this.user,
  });

  bool get isAuthed => jwt != null && jwt!.token.isNotEmpty;

  AuthState copyWith({
    bool? loading,
    Jwt? jwt,
    UserRole? role,
    int? domainId,
    AppUser? user,
  }) =>
      AuthState(
        loading: loading ?? this.loading,
        jwt: jwt ?? this.jwt,
        role: role ?? this.role,
        domainId: domainId ?? this.domainId,
        user: user ?? this.user,
      );
}

class AuthController extends StateNotifier<AuthState> {
  AuthController() : super(const AuthState());
  final _secure = const FlutterSecureStorage();

  Future<void> hydrate() async {
    final prefs = await SharedPreferences.getInstance();
    final token = await _secure.read(key: 'jwt') ?? prefs.getString('jwt');
    final roleStr = prefs.getString('role') ?? 'user';
    final domainId = prefs.getInt('domain_id');
    final username = prefs.getString('user_username');
    final email = prefs.getString('user_email');
    final uid = prefs.getInt('user_id');
    if (token != null && token.isNotEmpty) {
      state = state.copyWith(
        jwt: Jwt(token),
        role: _mapRole(roleStr),
        domainId: domainId,
        user: (username != null || email != null || uid != null)
            ? AppUser(username: username, email: email, id: uid)
            : state.user,
      );
    }
  }

  UserRole _mapRole(String r) {
    switch (r) {
      case 'super_admin':
        return UserRole.superAdmin;
      case 'admin':
        return UserRole.admin;
      default:
        return UserRole.user;
    }
  }

  Future<String?> login(String username, String password) async {
    state = state.copyWith(loading: true);
    try {
      final dio = ApiClient().dio;
      final resp = await dio.post(
        '/auth/login',
        data: {'username': username.trim(), 'password': password},
        options: ApiClient.jsonOpts,
      );
      if (resp.statusCode != 200) {
        throw Exception(resp.data?.toString() ?? 'Login failed');
      }
      final m = resp.data as Map<String, dynamic>;
      final token = (m['token'] ?? m['access_token'])?.toString();
      if (token == null || token.isEmpty) throw Exception('No token in response');

      final roleStr = (m['role'] ?? m['user']?['role'] ?? 'user').toString();
      final domainRaw = m['domain_id'] ?? m['user']?['domain_id'];
      final domainId = (domainRaw is int) ? domainRaw : int.tryParse('${domainRaw ?? ''}');
      final usernameOut = (m['user']?['username'] ?? username).toString();
      final emailOut = (m['user']?['email'] ?? '').toString();
      int? idOut;
      if (m['user']?['id'] is int) {
        idOut = m['user']['id'] as int;
      } else if (m['user_id'] is int) {
        idOut = m['user_id'] as int;
      } else {
        idOut = int.tryParse('${m['user_id'] ?? ''}');
      }

      await _secure.write(key: 'jwt', value: token);
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString('jwt', token);
      await prefs.setString('role', roleStr);
      if (domainId != null) await prefs.setInt('domain_id', domainId);
      await prefs.setString('user_username', usernameOut);
      await prefs.setString('user_email', emailOut);
      if (idOut != null) await prefs.setInt('user_id', idOut);

      state = AuthState(
        jwt: Jwt(token, subject: usernameOut),
        role: _mapRole(roleStr),
        domainId: domainId,
        user: AppUser(username: usernameOut, email: emailOut, id: idOut),
        loading: false,
      );

      switch (roleStr) {
        case 'super_admin':
          return '/s/dashboard';
        case 'admin':
          return '/a/dashboard';
        default:
          return '/u/chat';
      }
    } catch (e) {
      state = state.copyWith(loading: false);
      rethrow;
    }
  }

  Future<void> logout() async {
    final prefs = await SharedPreferences.getInstance();
    await _secure.delete(key: 'jwt');
    await prefs.remove('jwt');
    await prefs.remove('role');
    await prefs.remove('domain_id');
    state = const AuthState();
  }

  /// Calls backend: POST /user/change-password  -> returns new access_token + role + redirect
  Future<void> changePassword(String currentPw, String newPw) async {
    if (!state.isAuthed) throw Exception('Not authenticated');
    final dio = ApiClient(token: state.jwt!.token).dio;
    final resp = await dio.post(
      '/user/change-password',
      data: {'password': currentPw, 'new_password': newPw},
      options: ApiClient.jsonOpts,
    );
    if (resp.statusCode != 200) {
      throw Exception(resp.data?.toString() ?? 'Change password failed');
    }
    final m = resp.data as Map<String, dynamic>;
    final token = (m['access_token'] ?? m['token'])?.toString();
    final roleStr = (m['role'] ?? 'user').toString();

    if (token == null || token.isEmpty) throw Exception('No token in response');

    await _secure.write(key: 'jwt', value: token);
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('jwt', token);
    await prefs.setString('role', roleStr);
    if (state.user?.username != null) {
      await prefs.setString('user_username', state.user!.username!);
    }
    if (state.user?.email != null) {
      await prefs.setString('user_email', state.user!.email!);
    }
    if (state.user?.id != null) {
      await prefs.setInt('user_id', state.user!.id!);
    }

    state = state.copyWith(jwt: Jwt(token), role: _mapRole(roleStr));
  }
}

final authControllerProvider =
    StateNotifierProvider<AuthController, AuthState>((ref) => AuthController());
