import 'package:flutter/material.dart';
import 'package:jobmatch_app/features/auth/screens/profile_test_screen.dart';

import '../../../widgets/app_button.dart';
import '../../../widgets/app_text_field.dart';
import '../services/auth_service.dart';
import 'forgot_password_screen.dart';
import 'verify_email_screen.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final emailCtrl = TextEditingController();
  final passCtrl = TextEditingController();
  bool loading = false;

  @override
  void dispose() {
    emailCtrl.dispose();
    passCtrl.dispose();
    super.dispose();
  }

  Future<void> onLogin() async {
    final email = emailCtrl.text.trim();
    final password = passCtrl.text;

    if (email.isEmpty || !email.contains("@")) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text("Enter a valid email")),
      );
      return;
    }

    if (password.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text("Password is required")),
      );
      return;
    }

    setState(() => loading = true);
    try {
      await AuthService.login(email: email, password: password);

      if (!mounted) return;

      // TODO: replace with your real Home screen later
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text("Logged in ✅ (tokens saved)")),
      );

      Navigator.pushAndRemoveUntil(
        context,
        MaterialPageRoute(builder: (_) => const ProfileTestScreen()),
        (_) => false,
      );
    } catch (e) {
      if (!mounted) return;

      final msg = e.toString().replaceFirst("Exception: ", "");

      // If not verified -> go to verification screen automatically
      if (msg.toLowerCase().contains("verify your email")) {
        Navigator.pushReplacement(
          context,
          MaterialPageRoute(builder: (_) => VerifyEmailScreen(email: email)),
        );
        return;
      }

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(msg)),
      );
    } finally {
        if (mounted) setState(() => loading = false);
      }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.white,
      appBar: AppBar(
        backgroundColor: Colors.white,
        elevation: 0,
        foregroundColor: Colors.black,
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_ios_new, size: 18),
          onPressed: () => Navigator.pop(context),
        ),
      ),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.symmetric(horizontal: 22),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const SizedBox(height: 6),
              const Text(
                "Log in",
                style: TextStyle(
                  fontSize: 22,
                  fontWeight: FontWeight.w700,
                  color: Color(0xFF2D2D2D),
                ),
              ),
              const SizedBox(height: 18),

              AppTextField(
                controller: emailCtrl,
                label: "Email",
                hint: "Email",
                keyboardType: TextInputType.emailAddress,
              ),
              const SizedBox(height: 12),

              AppTextField(
                controller: passCtrl,
                label: "Password",
                hint: "Password",
                obscure: true,
                enableToggleObscure: true,
              ),
              const SizedBox(height: 14),

              Align(
                alignment: Alignment.centerRight,
                child: TextButton(
                  onPressed: () {
                    Navigator.push(
                      context,
                      MaterialPageRoute(builder: (_) => const ForgotPasswordScreen()),
                    );
                  },
                  child: const Text(
                    "Forgot password?",
                    style: TextStyle(color: Color(0xFF0A8F5A)),
                  ),
                ),
              ),

              const SizedBox(height: 6),

              AppButton(
                text: "Log In",
                loading: loading,
                onPressed: onLogin,
              ),

              const SizedBox(height: 18),
            ],
          ),
        ),
      ),
    );
  }
}