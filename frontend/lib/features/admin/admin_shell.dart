import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../providers/auth_provider.dart';
import '../../widgets/app_nav_sidebar.dart';

class AdminShell extends ConsumerWidget {
  final Widget child;
  const AdminShell({super.key, required this.child});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final path = GoRouterState.of(context).uri.toString();
    return AppNavSidebar(
      title: 'Admin',
      currentPath: path,
      onLogout: () async {
        await ref.read(authControllerProvider.notifier).logout();
        if (context.mounted) context.go('/login');
      },
      items: const [
        NavItem('Dashboard', Icons.monitor, '/a/dashboard'),
        NavItem('Create User', Icons.person_add, '/a/create-user'),
        NavItem('Upload', Icons.upload_file, '/a/upload'),
        NavItem('Docs', Icons.description, '/a/docs'),
        NavItem('Users', Icons.people, '/a/users'),
        NavItem('Feedback', Icons.reviews, '/a/feedback'),
        NavItem('Chat Test', Icons.chat, '/a/chat-test'),
      ],
      child: child,
    );
  }
}
