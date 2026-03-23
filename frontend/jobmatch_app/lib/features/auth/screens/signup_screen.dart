import 'package:flutter/material.dart';

import '../../../widgets/app_button.dart';
import '../../../widgets/app_text_field.dart';
import '../services/auth_service.dart';
import 'login_screen.dart';
import 'verify_email_screen.dart';

class SignupScreen extends StatefulWidget {
  const SignupScreen({super.key});

  @override
  State<SignupScreen> createState() => _SignupScreenState();
}

class _SignupScreenState extends State<SignupScreen> {
  final usernameCtrl = TextEditingController();
  final emailCtrl = TextEditingController();
  final passCtrl = TextEditingController();

  String role = "CLIENT";
  bool agree = true;
  bool loading = false;

  @override
  void dispose() {
    usernameCtrl.dispose();
    emailCtrl.dispose();
    passCtrl.dispose();
    super.dispose();
  }

  Future<void> onSignup() async {
    final email = emailCtrl.text.trim();
    final username = usernameCtrl.text.trim();
    final password = passCtrl.text;

    if (username.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text("Username cannot be empty.")),
      );
      return;
    }

    if (email.isEmpty || !email.contains("@")) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text("Enter a valid email address.")),
      );
      return;
    }

    if (password.length < 8 || password.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text("Password must be at least 8 characters.")),
      );
      return;
    }

    if (!agree) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text("Please accept Terms & Privacy.")),
      );
      return;
    }

    setState(() => loading = true);
    try {
      final email = emailCtrl.text.trim();
      await AuthService.signup(
        email: email,
        username: usernameCtrl.text.trim(),
        password: passCtrl.text,
        role: role,
      );

      if (!mounted) return;

      Navigator.pushReplacement(
        context,
        MaterialPageRoute(builder: (_) => VerifyEmailScreen(email: email)),
      );
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(e.toString().replaceFirst("Exception: ", ""))),
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
        title: const Text(""),
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
                "Sign up with your email",
                style: TextStyle(
                  fontSize: 22,
                  fontWeight: FontWeight.w700,
                  color: Color(0xFF2D2D2D),
                ),
              ),
              const SizedBox(height: 18),

              AppTextField(
                controller: usernameCtrl,
                label: "Username",
                hint: "Name",
              ),
              const SizedBox(height: 12),

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
              const SizedBox(height: 12),

              DropdownButtonFormField<String>(
                value: role,
                decoration: InputDecoration(
                  labelText: "Role",
                  filled: true,
                  fillColor: const Color(0xFFF7F7F7),
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(10),
                    borderSide: const BorderSide(color: Color(0xFFE6E6E6)),
                  ),
                  enabledBorder: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(10),
                    borderSide: const BorderSide(color: Color(0xFFE6E6E6)),
                  ),
                ),
                items: const [
                  DropdownMenuItem(value: "CLIENT", child: Text("CLIENT")),
                  DropdownMenuItem(value: "AGENT", child: Text("AGENT")),
                ],
                onChanged: (v) => setState(() => role = v ?? "CLIENT"),
              ),

              const SizedBox(height: 14),

              Row(
                children: [
                  Checkbox(
                    value: agree,
                    activeColor: const Color(0xFF0A8F5A),
                    onChanged: (v) => setState(() => agree = v ?? false),
                  ),
                  const Expanded(
                    child: Text(
                      "By signing up, you agree to the Terms of service and Privacy policy.",
                      style: TextStyle(fontSize: 12, color: Color(0xFF8E8E8E)),
                    ),
                  ),
                ],
              ),

              const SizedBox(height: 10),

              AppButton(
                text: "Sign Up",
                loading: loading,
                onPressed: onSignup,
              ),

              const SizedBox(height: 18),

              Row(
                children: const [
                  Expanded(child: Divider(color: Color(0xFFE6E6E6))),
                  Padding(
                    padding: EdgeInsets.symmetric(horizontal: 10),
                    child: Text("or", style: TextStyle(color: Color(0xFF9E9E9E))),
                  ),
                  Expanded(child: Divider(color: Color(0xFFE6E6E6))),
                ],
              ),

              const SizedBox(height: 14),

              OutlinedButton(
                onPressed: () {
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(content: Text("Gmail signup will be added later.")),
                  );
                },
                style: OutlinedButton.styleFrom(
                  minimumSize: const Size.fromHeight(50),
                  side: const BorderSide(color: Color(0xFFE6E6E6)),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                ),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: const [
                    Icon(Icons.mail_outline, color: Colors.red),
                    SizedBox(width: 10),
                    Text("Sign up with Gmail", style: TextStyle(color: Colors.black)),
                  ],
                ),
              ),

              const SizedBox(height: 18),

              Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  const Text("Already have an account? ",
                      style: TextStyle(color: Color(0xFF8E8E8E))),
                  GestureDetector(
                    onTap: () {
                      Navigator.pushReplacement(
                        context,
                        MaterialPageRoute(builder: (_) => const LoginScreen()),
                      );
                    },
                    child: const Text(
                      "Sign in",
                      style: TextStyle(
                        color: Color(0xFF0A8F5A),
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ),
                ],
              ),

              const SizedBox(height: 22),
            ],
          ),
        ),
      ),
    );
  }
}