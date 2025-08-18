import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../core/jwt.dart';
import '../core/role.dart';
import '../data/auth_repository.dart';

class AuthState {
  final bool loading; final JwtInfo? jwt;
  const AuthState({this.loading = false, this.jwt});
  UserRole get role => jwt?.role ?? UserRole.unknown;
  bool get isAuthed => jwt != null;
}

class AuthController extends StateNotifier<AuthState> {
  final AuthRepository _repo;
  final FlutterSecureStorage _secure = const FlutterSecureStorage();
  AuthController(this._repo) : super(const AuthState()) { restore(); }

  Future<void> restore() async {
    state = const AuthState(loading: true);
    try {
      final prefs = await SharedPreferences.getInstance();
      final token = await _secure.read(key: 'jwt') ?? prefs.getString('jwt');
      state = token != null ? AuthState(jwt: parseJwt(token)) : const AuthState();
    } finally {
      state = AuthState(jwt: state.jwt);
    }
  }

  Future<void> logout() async {
    await _secure.delete(key: 'jwt');
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove('jwt');
    state = const AuthState();
  }

  Future<String?> login(String u, String p) async {
    state = const AuthState(loading: true);
    final res = await _repo.login(u, p);
    await _secure.write(key: 'jwt', value: res.jwt.token);
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('jwt', res.jwt.token);
    state = AuthState(jwt: res.jwt);
    return res.redirect;
  }
}

final authControllerProvider = StateNotifierProvider<AuthController, AuthState>(
  (ref) => AuthController(AuthRepository()),
);
