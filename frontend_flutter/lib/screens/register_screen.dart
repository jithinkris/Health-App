import 'package:flutter/material.dart';
import 'package:smart_health/theme.dart';
import 'package:smart_health/screens/dashboard_screen.dart';
import 'package:smart_health/services/auth_service.dart';

class RegisterScreen extends StatefulWidget {
  const RegisterScreen({super.key});

  @override
  State<RegisterScreen> createState() => _RegisterScreenState();
}

class _RegisterScreenState extends State<RegisterScreen> {
  final _nameCtr = TextEditingController();
  final _emailCtr = TextEditingController();
  final _passCtr = TextEditingController();
  final _ageCtr = TextEditingController();
  final _genderCtr = TextEditingController();
  final _heightCtr = TextEditingController();
  final _weightCtr = TextEditingController();

  bool _isLoading = false;

  void _handleRegister() async {
    setState(() => _isLoading = true);
    
    bool success = await AuthService.register(
      name: _nameCtr.text,
      email: _emailCtr.text,
      password: _passCtr.text,
      age: _ageCtr.text,
      gender: _genderCtr.text,
      height: _heightCtr.text,
      weight: _weightCtr.text,
    );

    if (mounted) {
      setState(() => _isLoading = false);
      if (success) {
        // After successful registration, log them in automatically to store the JWT token
        await AuthService.login(_emailCtr.text, _passCtr.text);
        if (mounted) {
          Navigator.pushAndRemoveUntil(
            context,
            MaterialPageRoute(builder: (context) => const DashboardScreen()),
            (route) => false,
          );
        }
      } else {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Registration failed. Please check your data.')),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Register'),
        backgroundColor: Colors.transparent,
      ),
      body: Container(
        decoration: BoxDecoration(
          gradient: LinearGradient(
            colors: [AppTheme.bgSurface, AppTheme.secondaryTeal.withOpacity(0.1)],
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
          ),
        ),
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24.0),
          child: GlassCard(
            padding: const EdgeInsets.all(32.0),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Text(
                  'Create Account',
                  style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                    fontWeight: FontWeight.bold,
                    color: AppTheme.secondaryTeal,
                  ),
                ),
                const SizedBox(height: 24),
                _buildTextField('Full Name', Icons.person, _nameCtr),
                const SizedBox(height: 16),
                _buildTextField('Email Address', Icons.email, _emailCtr, keyboardType: TextInputType.emailAddress),
                const SizedBox(height: 16),
                _buildTextField('Password', Icons.lock, _passCtr, obscureText: true),
                const SizedBox(height: 16),
                Row(
                  children: [
                    Expanded(child: _buildTextField('Age', Icons.calendar_today, _ageCtr, keyboardType: TextInputType.number)),
                    const SizedBox(width: 16),
                    Expanded(child: _buildTextField('Gender', Icons.transgender, _genderCtr)),
                  ],
                ),
                const SizedBox(height: 16),
                Row(
                  children: [
                    Expanded(child: _buildTextField('Height (cm)', Icons.height, _heightCtr, keyboardType: TextInputType.number)),
                    const SizedBox(width: 16),
                    Expanded(child: _buildTextField('Weight (kg)', Icons.monitor_weight, _weightCtr, keyboardType: TextInputType.number)),
                  ],
                ),
                const SizedBox(height: 32),
                ElevatedButton(
                  onPressed: _isLoading ? null : _handleRegister,
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppTheme.secondaryTeal,
                    padding: const EdgeInsets.symmetric(vertical: 16),
                  ),
                  child: _isLoading 
                      ? const SizedBox(width: 24, height: 24, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
                      : const Text('Register', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildTextField(String label, IconData icon, TextEditingController controller, {bool obscureText = false, TextInputType keyboardType = TextInputType.text}) {
    return TextField(
      controller: controller,
      obscureText: obscureText,
      keyboardType: keyboardType,
      decoration: InputDecoration(
        labelText: label,
        prefixIcon: Icon(icon),
        filled: true,
        fillColor: Colors.white.withOpacity(0.9),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: BorderSide.none,
        ),
      ),
    );
  }
}
