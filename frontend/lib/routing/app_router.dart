// lib/routing/app_router.dart
import 'package:flutter/widgets.dart';                    // BuildContext
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../providers/auth_provider.dart';
import '../core/role.dart';

// Public
import '../features/landing/landing_page.dart';
import '../features/auth/login_page.dart';
import '../features/user/chat_page.dart';

// Admin
import '../features/admin/admin_shell.dart';
import '../features/admin/dashboard_page.dart';
import '../features/admin/upload_page.dart';
import '../features/admin/docs_page.dart';          // AdminDocsPage
import '../features/admin/doc_detail_page.dart';    // AdminDocDetailPage
import '../features/admin/users_page.dart';
import '../features/admin/feedback_page.dart';

// Super Admin
import '../features/superadmin/super_admin_shell.dart';
import '../features/superadmin/super_admin_dashboard_page.dart';
import '../features/superadmin/create_admin_page.dart';
import '../features/superadmin/create_domain_page.dart';

final appRouterProvider = Provider<GoRouter>((ref) {
  // Watch auth so router rebuilds on login/logout/role changes.
  final auth = ref.watch(authControllerProvider);

  return GoRouter(
    debugLogDiagnostics: true,
    initialLocation: '/',
    // If your go_router version sometimes gives null fullPath,
    // fall back to matchedLocation.
    redirect: (ctx, state) {
      final path = state.fullPath ?? state.matchedLocation;
      final loggingIn = path == '/login';

      if (!auth.isAuthed) {
        // Allow landing & login while unauthenticated
        return (loggingIn || path == '/') ? null : '/login';
      }

      // Already authed but heading to / or /login -> send to role home
      if (loggingIn || path == '/') {
        switch (auth.role) {
          case UserRole.user:
            return '/u/chat';
          case UserRole.admin:
            return '/a/dashboard';
          case UserRole.superAdmin:
            return '/s/dashboard';
          default:
            return '/login';
        }
      }
      return null;
    },

    routes: [
      // Public
      GoRoute(path: '/', builder: (_, __) => const LandingPage()),
      GoRoute(path: '/login', builder: (_, __) => const LoginPage()),

      // User
      GoRoute(path: '/u/chat', builder: (_, __) => const ChatPage()),

      // Admin
      ShellRoute(
        builder: (_, __, child) => AdminShell(child: child),
        routes: [
          GoRoute(path: '/a/dashboard', builder: (_, __) => const AdminDashboardPage()),
          GoRoute(path: '/a/upload',    builder: (_, __) => const UploadPage()),
          GoRoute(path: '/a/docs',      builder: (_, __) => const AdminDocsPage()),
          GoRoute(
            path: '/a/docs/:id',
            builder: (ctx, state) {
              final idStr = state.pathParameters['id'];
              final id = int.tryParse(idStr ?? '');
              return AdminDocDetailPage(docId: id ?? 0);
            },
          ),
          GoRoute(path: '/a/users',     builder: (_, __) => const UsersPage()),
          GoRoute(path: '/a/feedback',  builder: (_, __) => const FeedbackPage()),
          GoRoute(path: '/a/chat-test', builder: (_, __) => const ChatPage()),
        ],
      ),

      // Super Admin
      ShellRoute(
        builder: (_, __, child) => SuperAdminShell(child: child),
        routes: [
          GoRoute(path: '/s/dashboard',     builder: (_, __) => const SuperAdminDashboardPage()),
          GoRoute(path: '/s/admin-create',  builder: (_, __) => const CreateAdminPage()),
          GoRoute(path: '/s/domain-create', builder: (_, __) => const CreateDomainPage()),
          GoRoute(path: '/s/chat-test',     builder: (_, __) => const ChatPage()),
        ],
      ),
    ],

    errorBuilder: (_, state) => Center(
      child: Text('Page not found: ${state.uri.toString()}'),
    ),
  );
});
