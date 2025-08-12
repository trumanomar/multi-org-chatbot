import 'package:flutter/material.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'routes.dart';
import 'services/api_service.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await dotenv.load(fileName: ".env");

  final api = ApiService();
  try {
    final isHealthy = await api.healthCheck();
    // You can keep/ remove this log as you like
    // ignore: avoid_print
    print('Backend health: $isHealthy');
  } catch (e) {
    // ignore: avoid_print
    print('Health check failed: $e');
  }

  runApp(const App());
}

class App extends StatelessWidget {
  const App({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Admin Panel',
      debugShowCheckedModeBanner: false,
      routes: appRoutes,
      // Start at the Login screen (chooser)
      // If you have AppRoutes.login defined in routes.dart, prefer that:
      // initialRoute: AppRoutes.login,
      initialRoute: '/login',
      theme: ThemeData(
        useMaterial3: true,
        colorSchemeSeed: Colors.indigo,
      ),
    );
  }
}
