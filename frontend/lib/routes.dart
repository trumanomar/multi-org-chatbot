import 'package:flutter/material.dart';
import 'screens/login_screen.dart';
import 'screens/admin_dashboard.dart';
import 'screens/upload_screen.dart';

class AppRoutes {
  static const String login = '/login';
  static const String adminDashboard = '/admin';
  static const String upload = '/upload';
}

Map<String, WidgetBuilder> routes = {
  AppRoutes.login: (context) => const LoginScreen(),
  AppRoutes.adminDashboard: (context) => const AdminDashboard(),
  AppRoutes.upload: (context) => const UploadScreen(),
};
