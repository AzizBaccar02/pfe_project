import 'package:flutter/material.dart';
import 'features/auth/screens/welcome_screen.dart';

void main() => runApp(const JobMatchApp());

class JobMatchApp extends StatelessWidget {
  const JobMatchApp({super.key});

  @override
  Widget build(BuildContext context) {
    return const MaterialApp(
      debugShowCheckedModeBanner: false,
      home: WelcomeScreen(),
    );
  }
}