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
    print('Backend health: $isHealthy');
  } catch (e) {
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
      routes: appRoutes,                 // uses the variable exported above
      initialRoute: AppRoutes.root,      // '/'
    );
  }
}
