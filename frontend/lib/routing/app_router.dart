import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../providers/auth_provider.dart';
import '../core/role.dart';

// Public
import '../features/landing/landing_page.dart';
import '../features/auth/login_page.dart';
import '../features/auth/forgot_password_page.dart';
import '../features/auth/change_password_page.dart';

// User
import '../features/user/chat_page.dart';
import '../features/user/profile_page.dart';

// Admin
import '../features/admin/admin_shell.dart';
import '../features/admin/dashboard_page.dart'; // <-- correct path
import '../features/admin/upload_page.dart';
import '../features/admin/docs_page.dart';
import '../features/admin/doc_detail_page.dart';
import '../features/admin/users_page.dart';
import '../features/admin/feedback_page.dart';
import '../features/admin/create_user_page.dart';

// Super Admin
import '../features/superadmin/super_admin_shell.dart';
import '../features/superadmin/create_admin_page.dart';
import '../features/superadmin/create_domain_page.dart';
import '../features/superadmin/domains_page.dart';
import '../features/superadmin/super_admin_dashboard_page.dart';

final appRouterProvider = Provider<GoRouter>((ref) {
  String? guard(BuildContext ctx, GoRouterState state) {
    final auth = ref.read(authControllerProvider);
    final p = state.uri.toString();

    final isPrivate =
        p.startsWith('/u/') || p.startsWith('/a/') || p.startsWith('/s/');

    // not authed -> block private routes
    if (!auth.isAuthed && isPrivate) return '/login';

    // authed landing/login -> send home by role
    if (auth.isAuthed && (p == '/' || p == '/login')) {
      switch (auth.role) {
        case UserRole.superAdmin:
          return '/s/dashboard';
        case UserRole.admin:
          return '/a/dashboard';
        default:
          return '/u/chat';
      }
    }
    return null;
  }

  return GoRouter(
    initialLocation: '/',
    redirect: guard,
    routes: [
      // public
      GoRoute(path: '/', builder: (_, __) => const LandingPage()),
      GoRoute(path: '/login', builder: (_, __) => const LoginPage()),
      GoRoute(
        path: '/forgot-password',
        builder: (_, __) => const ForgotPasswordPage(),
      ),
      GoRoute(
        path: '/change-password',
        builder: (_, __) => const ChangePasswordPage(),
      ),

      // user
      GoRoute(path: '/u/chat', builder: (_, __) => const ChatPage()),
      GoRoute(path: '/u/profile', builder: (_, __) => const ProfilePage()),

      // admin
      ShellRoute(
        builder: (_, __, child) => AdminShell(child: child),
        routes: [
          GoRoute(
            path: '/a/dashboard',
            builder: (_, __) => const AdminDashboardPage(),
          ),
          GoRoute(
            path: '/a/create-user',
            builder: (_, __) => const CreateUserPage(),
          ),
          GoRoute(
            path: '/a/upload',
            builder: (_, __) => const UploadPage(),
          ),
          GoRoute(
            path: '/a/docs',
            builder: (_, __) => const AdminDocsPage(),
          ),
          GoRoute(
            path: '/a/chat-test',
            builder: (_, __) => const ChatPage(),
          ),
          // details: /a/docs/:id -> existing AdminDocDetailPage
          GoRoute(
            path: '/a/docs/:id',
            builder: (_, st) {
              final id = int.tryParse(st.pathParameters['id'] ?? '');
              return AdminDocDetailPage(docId: id ?? 0);
            },
          ),
          GoRoute(
            path: '/a/users',
            builder: (_, __) => const UsersPage(),
          ),
          GoRoute(
            path: '/a/feedback',
            builder: (_, __) => const FeedbackPage(),
          ),
        ],
      ),

      // super admin
      ShellRoute(
        builder: (_, __, child) => SuperAdminShell(child: child),
        routes: [
          GoRoute(
            path: '/s/dashboard',
            builder: (_, __) => const SuperAdminDashboardPage(),
          ),
          GoRoute(
            path: '/s/admin-create',
            builder: (_, __) => const CreateAdminPage(),
          ),
          GoRoute(
            path: '/s/domain-create',
            builder: (_, __) => const CreateDomainPage(),
          ),
          GoRoute(
            path: '/s/domains',
            builder: (_, __) => const DomainsPage(),
          ),
          // optional: quick chat test inside super-admin shell
          GoRoute(
            path: '/s/chat-test',
            builder: (_, __) => const ChatPage(),
          ),
        ],
      ),
    ],
  );
});
