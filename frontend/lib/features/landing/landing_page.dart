import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

class LandingPage extends StatelessWidget {
  const LandingPage({super.key});
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Stack(fit: StackFit.expand, children: [
        Container(color: const Color(0xff0e1116)),
        Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text('Chat bot Project',
                  style: Theme.of(context).textTheme.displaySmall?.copyWith(
                        color: Colors.white,
                        fontWeight: FontWeight.w700,
                      )),
              const SizedBox(height: 16),
              Text(
                'Secure, multi-tenant RAG chat for your org.',
                style: Theme.of(context).textTheme.titleMedium?.copyWith(color: Colors.white70),
              ),
              const SizedBox(height: 24),
              FilledButton.tonal(
                onPressed: () => context.go('/login'),
                child: const Padding(
                  padding: EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                  child: Text('Login'),
                ),
              ),
            ],
          ),
        ),
      ]),
    );
  }
}
