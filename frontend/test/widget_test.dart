<<<<<<< HEAD
=======
import 'package:flutter/material.dart';
>>>>>>> 6b806192b45fe7050369ec60a42d165860519246
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/main.dart'; // make sure 'frontend' matches your project name in pubspec.yaml

void main() {
  testWidgets('App loads without errors', (WidgetTester tester) async {
    // Build your app and trigger a frame
    await tester.pumpWidget(const App());

    // Verify if the Login screen text is found
    expect(find.text('Login Screen'), findsOneWidget);
  });
}
