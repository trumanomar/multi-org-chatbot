import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

class AppNavSidebar extends StatelessWidget {
  final List<NavItem> items;
  final Widget child;
  final String currentPath;
  final String title;
  final VoidCallback? onLogout;

  const AppNavSidebar({
    super.key,
    required this.items,
    required this.child,
    required this.currentPath,
    this.title = '',
    this.onLogout,
  });

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(title.isEmpty ? 'Dashboard' : title),
        actions: [
          IconButton(
            tooltip: 'Logout',
            onPressed: onLogout,
            icon: const Icon(Icons.logout),
          ),
        ],
      ),
      body: Row(
        children: [
          NavigationRail(
            backgroundColor: Colors.white,
            selectedIndex: items.indexWhere((e) => currentPath.startsWith(e.path)),
            destinations: items
                .map((e) => NavigationRailDestination(
                      icon: Icon(e.icon),
                      label: Text(e.label),
                    ))
                .toList(),
            onDestinationSelected: (i) => context.go(items[i].path),
          ),
          const VerticalDivider(width: 1),
          Expanded(child: child),
        ],
      ),
    );
  }
}

class NavItem {
  final String label;
  final IconData icon;
  final String path;
  const NavItem(this.label, this.icon, this.path);
}
