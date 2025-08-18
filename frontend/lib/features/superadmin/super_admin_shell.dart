import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../providers/auth_provider.dart';
import '../../widgets/app_nav_sidebar.dart';

class SuperAdminShell extends ConsumerWidget {
  final Widget child;
  const SuperAdminShell({super.key, required this.child});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final path = GoRouterState.of(context).uri.toString();
    return AppNavSidebar(
      title: 'Super Admin',
      currentPath: path,
      onLogout: () async {
        await ref.read(authControllerProvider.notifier).logout();
        if (context.mounted) context.go('/login');
      },
      items: const [
        NavItem('KPI Dashboard', Icons.insights, '/s/dashboard'),
        NavItem('Create Domain', Icons.apartment, '/s/domain-create'),
        NavItem('Create Admin', Icons.admin_panel_settings, '/s/admin-create'),
        NavItem('Test Chat', Icons.chat, '/s/chat-test'),
      ],
      child: child,
    );
  }
}
