import 'package:flutter/material.dart';
import 'screens/login_screen.dart';
import 'screens/admin_dashboard.dart';
import 'screens/upload_screen.dart';

class AppRoutes {
  static const root = '/';
  static const dashboard = '/dashboard';
  static const upload = '/upload';
}

final Map<String, WidgetBuilder> appRoutes = {
  AppRoutes.root: (_) => const LoginScreen(),
  AppRoutes.dashboard: (_) => const AdminDashboard(),
  AppRoutes.upload: (_) => const UploadScreen(),
};
