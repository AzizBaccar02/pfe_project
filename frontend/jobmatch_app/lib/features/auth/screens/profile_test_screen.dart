import 'package:flutter/material.dart';
import '../services/auth_service.dart';
import 'welcome_screen.dart';
import '../../../widgets/app_button.dart';

class ProfileTestScreen extends StatelessWidget {
  const ProfileTestScreen({super.key});

  Future<void> doLogout(BuildContext context) async {
    try {
      await AuthService.logout();
      if (!context.mounted) return;

      Navigator.pushAndRemoveUntil(
        context,
        MaterialPageRoute(builder: (_) => const WelcomeScreen()),
        (_) => false,
      );
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(e.toString().replaceFirst("Exception: ", ""))),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.white,
      appBar: AppBar(
        title: const Text("Logged in"),
        backgroundColor: Colors.white,
        foregroundColor: Colors.black,
        elevation: 0,
      ),
      body: Padding(
        padding: const EdgeInsets.all(22),
        child: Column(
          children: [
            const Text("You are logged in ✅"),
            const Spacer(),
            AppButton(
              text: "Logout",
              onPressed: () => doLogout(context),
            ),
          ],
        ),
      ),
    );
  }
}