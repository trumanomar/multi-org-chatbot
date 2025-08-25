import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'app_theme.dart';
import 'routing/app_router.dart';
import 'providers/auth_provider.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await dotenv.load(fileName: ".env");
  runApp(const ProviderScope(child: App()));
}

class App extends ConsumerWidget {
  const App({super.key});
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    // Ensure auth is hydrated once on startup
    ref.read(authControllerProvider.notifier).hydrate();
    final router = ref.watch(appRouterProvider);
    return MaterialApp.router(
      title: 'Org Mind Hive',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.light,
      routerConfig: router,
    );
  }
}
