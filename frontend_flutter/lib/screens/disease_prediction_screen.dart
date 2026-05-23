import 'package:flutter/material.dart';
import 'package:smart_health/theme.dart';
import 'package:smart_health/services/api_service.dart';

class DiseasePredictionScreen extends StatefulWidget {
  const DiseasePredictionScreen({super.key});

  @override
  State<DiseasePredictionScreen> createState() => _DiseasePredictionScreenState();
}

class _DiseasePredictionScreenState extends State<DiseasePredictionScreen> {
  bool _isLoading = false;
  Map<String, dynamic>? _predictionResult;

  final List<Map<String, dynamic>> _diseases = [
    {'name': 'Hypertension Risk', 'icon': Icons.favorite, 'color': Colors.red},
    {'name': 'Cardiovascular Risk', 'icon': Icons.monitor_heart, 'color': Colors.redAccent},
    {'name': 'Sleep Apnea Risk', 'icon': Icons.bedtime, 'color': Colors.indigo},
    {'name': 'Stress / Anxiety', 'icon': Icons.psychology, 'color': Colors.orange},
    {'name': 'Arrhythmia / AFib Risk', 'icon': Icons.waves, 'color': Colors.red},
    {'name': 'Obesity Risk', 'icon': Icons.fastfood, 'color': Colors.brown},
    {'name': 'Diabetes Risk', 'icon': Icons.bloodtype, 'color': Colors.purple},
    {'name': 'Fatigue Detection', 'icon': Icons.battery_alert, 'color': Colors.blueGrey},
    {'name': 'Depression Risk', 'icon': Icons.mood_bad, 'color': Colors.grey},
    {'name': 'Fall Detection for Elderly', 'icon': Icons.personal_injury, 'color': Colors.deepOrange},
    {'name': 'Sedentary Lifestyle Risk', 'icon': Icons.chair, 'color': Colors.teal},
  ];

  Future<void> _predictDisease(String diseaseName) async {
    setState(() {
      _isLoading = true;
      _predictionResult = null;
    });

    final result = await ApiService.predictSpecificDisease(diseaseName);

    setState(() {
      _isLoading = false;
      _predictionResult = result;
    });

    if (result != null) {
      _showResultDialog(result);
    } else {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Failed to predict risk. Please try again.')),
      );
    }
  }

  void _showResultDialog(Map<String, dynamic> result) {
    Color riskColor = Colors.green;
    if (result['risk_level'] == 'MEDIUM') riskColor = Colors.orange;
    if (result['risk_level'] == 'HIGH') riskColor = Colors.red;

    showDialog(
      context: context,
      builder: (context) {
        return AlertDialog(
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
          title: Text(result['disease_name'] ?? 'Prediction Result'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                'Risk Level: ${result['risk_level']}',
                style: TextStyle(color: riskColor, fontSize: 20, fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 16),
              Stack(
                alignment: Alignment.center,
                children: [
                  SizedBox(
                    width: 100,
                    height: 100,
                    child: CircularProgressIndicator(
                      value: (result['risk_percentage'] ?? 0) / 100,
                      backgroundColor: Colors.grey.shade200,
                      valueColor: AlwaysStoppedAnimation(riskColor),
                      strokeWidth: 10,
                    ),
                  ),
                  Text(
                    '${result['risk_percentage']}%',
                    style: TextStyle(fontWeight: FontWeight.bold, fontSize: 20, color: riskColor),
                  )
                ],
              ),
              const SizedBox(height: 16),
              Text(
                (result['recommendation'] as List<dynamic>?)?.join('\n') ?? '',
                textAlign: TextAlign.center,
                style: const TextStyle(color: Colors.blueGrey),
              )
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('Close'),
            )
          ],
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Disease Predictions'),
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator(color: AppTheme.primaryBlue))
          : ListView.builder(
              padding: const EdgeInsets.all(16),
              itemCount: _diseases.length,
              itemBuilder: (context, index) {
                final disease = _diseases[index];
                return Padding(
                  padding: const EdgeInsets.only(bottom: 12),
                  child: GlassCard(
                    child: ListTile(
                      leading: CircleAvatar(
                        backgroundColor: disease['color'].withOpacity(0.2),
                        child: Icon(disease['icon'], color: disease['color']),
                      ),
                      title: Text(disease['name'], style: const TextStyle(fontWeight: FontWeight.bold)),
                      trailing: const Icon(Icons.arrow_forward_ios, size: 16),
                      onTap: () => _predictDisease(disease['name']),
                    ),
                  ),
                );
              },
            ),
    );
  }
}
