import 'package:flutter/material.dart';
import 'package:smart_health/theme.dart';
import 'package:smart_health/services/api_service.dart';

class ProfileEditDialog extends StatefulWidget {
  final Map<String, dynamic> userProfile;

  const ProfileEditDialog({super.key, required this.userProfile});

  @override
  State<ProfileEditDialog> createState() => _ProfileEditDialogState();
}

class _ProfileEditDialogState extends State<ProfileEditDialog> {
  late TextEditingController _nameCtr;
  late TextEditingController _ageCtr;
  late TextEditingController _heightCtr;
  late TextEditingController _weightCtr;
  bool _isLoading = false;

  @override
  void initState() {
    super.initState();
    _nameCtr = TextEditingController(text: widget.userProfile['name']?.toString() ?? '');
    _ageCtr = TextEditingController(text: widget.userProfile['age']?.toString() ?? '');
    _heightCtr = TextEditingController(text: widget.userProfile['height']?.toString() ?? '');
    _weightCtr = TextEditingController(text: widget.userProfile['weight']?.toString() ?? '');
  }

  Future<void> _handleSave() async {
    setState(() => _isLoading = true);
    
    final updatedData = {
      'name': _nameCtr.text,
      'age': int.tryParse(_ageCtr.text) ?? 0,
      'height': double.tryParse(_heightCtr.text) ?? 0.0,
      'weight': double.tryParse(_weightCtr.text) ?? 0.0,
    };
    
    final result = await ApiService.updateCurrentUser(updatedData);
    
    setState(() => _isLoading = false);
    if (mounted) {
      if (result != null) {
        Navigator.pop(context, true); // Return true meaning success
      } else {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Failed to update profile')),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
      title: const Text('Edit Profile', style: TextStyle(color: AppTheme.primaryBlue, fontWeight: FontWeight.bold)),
      content: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              controller: _nameCtr,
              decoration: const InputDecoration(labelText: 'Full Name', prefixIcon: Icon(Icons.person)),
            ),
            const SizedBox(height: 16),
            TextField(
              controller: _ageCtr,
              keyboardType: TextInputType.number,
              decoration: const InputDecoration(labelText: 'Age', prefixIcon: Icon(Icons.calendar_today)),
            ),
            const SizedBox(height: 16),
            TextField(
              controller: _heightCtr,
              keyboardType: TextInputType.number,
              decoration: const InputDecoration(labelText: 'Height (cm)', prefixIcon: Icon(Icons.height)),
            ),
            const SizedBox(height: 16),
            TextField(
              controller: _weightCtr,
              keyboardType: TextInputType.number,
              decoration: const InputDecoration(labelText: 'Weight (kg)', prefixIcon: Icon(Icons.monitor_weight)),
            ),
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context, false),
          child: const Text('Cancel', style: TextStyle(color: Colors.grey)),
        ),
        ElevatedButton(
          onPressed: _isLoading ? null : _handleSave,
          style: ElevatedButton.styleFrom(backgroundColor: AppTheme.primaryBlue, shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12))),
          child: _isLoading 
            ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
            : const Text('Save Changes', style: TextStyle(fontWeight: FontWeight.bold)),
        ),
      ],
    );
  }
}
