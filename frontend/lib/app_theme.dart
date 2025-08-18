// lib/app_theme.dart
import 'package:flutter/material.dart';

class AppTheme {
  static ThemeData get light => ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xFF4B6BFB)),
        useMaterial3: true,
        fontFamily: 'Inter',

        // App-level
        scaffoldBackgroundColor: const Color(0xFFF7F8FA),

        // Cards (CardThemeData is what's required on your SDK)
        cardTheme: const CardThemeData(
          elevation: 0,
          margin: EdgeInsets.all(12),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.all(Radius.circular(16)),
          ),
        ),

        // AppBar
        appBarTheme: const AppBarTheme(
          centerTitle: false,
          elevation: 0,
        ),

        // Inputs
        inputDecorationTheme: const InputDecorationTheme(
          border: OutlineInputBorder(
            borderRadius: BorderRadius.all(Radius.circular(12)),
          ),
        ),
      );
}
