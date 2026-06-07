import 'package:flutter/material.dart';
import 'package:smart_health/theme.dart';
import 'package:fl_chart/fl_chart.dart';
import 'package:smart_health/services/api_service.dart';
import 'package:smart_health/screens/welcome_screen.dart';
import 'package:smart_health/screens/profile_edit_dialog.dart';
import 'package:smart_health/services/notification_service.dart';
import 'package:intl/intl.dart';
import 'package:file_picker/file_picker.dart';
import 'package:smart_health/screens/disease_prediction_screen.dart';
import 'package:smart_health/services/health_sync_service.dart';
import 'package:smart_health/screens/chatbot_screen.dart';

class DashboardScreen extends StatefulWidget {
  final bool showProfileSetup;
  const DashboardScreen({super.key, this.showProfileSetup = false});

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  int _currentIndex = 0;
  bool _isLoading = false;

  String _userName = "User";
  Map<String, dynamic> _userProfile = {};

  String _riskLevel = "UNKNOWN";
  double _riskPercentage = 0.0;
  String _recommendation = "Sync health data to view risk";
  
  String _heartRate = "-- bpm";
  String _steps = "--";
  String _sleep = "-- h";
  String _spo2 = "-- %";

  List<dynamic> _medicines = [];
  List<dynamic> _allHealthData = [];
  List<dynamic> _medicalReports = [];

  @override
  void initState() {
    super.initState();
    // Defer data loading until after the first frame is fully painted.
    // This fixes the bug where a cold "flutter run" shows a blank screen
    // (setState calls were being swallowed before the widget tree was ready).
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _fetchData().then((_) {
        if (widget.showProfileSetup && mounted) {
          setState(() => _currentIndex = 3);
          showDialog<bool>(
            context: context,
            barrierDismissible: false,
            builder: (context) => ProfileEditDialog(userProfile: _userProfile),
          ).then((result) {
            if (result == true) _fetchData();
          });
        }
      });
    });
  }

  Future<void> _fetchData({int retryCount = 0}) async {
    setState(() => _isLoading = true);
    
    final user = await ApiService.getCurrentUser();
    if (user == null) {
      // On first launch the token may not be ready yet; retry a couple of times
      // before giving up and redirecting to the login screen.
      if (retryCount < 3) {
        await Future.delayed(const Duration(milliseconds: 800));
        return _fetchData(retryCount: retryCount + 1);
      }
      await ApiService.logout();
      if (mounted) {
        Navigator.pushAndRemoveUntil(
          context,
          MaterialPageRoute(builder: (_) => const WelcomeScreen()),
          (route) => false,
        );
      }
      return;
    }

    _userName = user['name'] ?? user['username'] ?? 'User';
    _userProfile = user;

      // Force prompt if user has no age and the onboarding check missed them
      if (!widget.showProfileSetup && (_userProfile['age'] == null || _userProfile['age'] == 0)) {
        if (mounted) {
          WidgetsBinding.instance.addPostFrameCallback((_) {
            setState(() => _currentIndex = 3);
            showDialog<bool>(
              context: context,
              barrierDismissible: false,
              builder: (context) => ProfileEditDialog(userProfile: _userProfile),
            ).then((result) {
              if (result == true) _fetchData();
            });
          });
        }
      }

    final health = await ApiService.getLatestHealthData();
    if (health != null) {
      _heartRate = "${health['heart_rate'] ?? '--'} bpm";
      _steps = "${health['steps'] ?? '--'}";
      _sleep = "${health['sleep_hours'] ?? '--'} h";
      _spo2 = "${health['spo2'] ?? '--'} %";
      
      final risk = await ApiService.predictRisk({
        'age': 30, // Static baseline for demonstration; dynamically grab from User Profile normally
        'bmi': 24.5,
        'heart_rate': health['heart_rate'] ?? 70,
        'sleep_duration': health['sleep_hours'] ?? 8,
        'activity_level': 1,
        'steps_count': health['steps'] ?? 5000,
        'spo2': health['spo2'] ?? 98,
      });

      if (risk != null) {
        _riskLevel = risk['risk_level'];
        _riskPercentage = risk['risk_percentage'];
        List recs = risk['recommendation'];
        _recommendation = recs.isNotEmpty ? recs.first : "Keep maintaining a healthy lifestyle.";
        
        // Show alerts / warnings as snackbars on dashboard
        if (mounted) {
          for (var rec in recs) {
            final recStr = rec.toString();
            if (recStr.contains('hike detected') || 
                recStr.contains('alert') || 
                recStr.contains('spike detected') || 
                recStr.contains('drop detected') ||
                recStr.contains('detected:')) {
              ScaffoldMessenger.of(context).showSnackBar(
                SnackBar(
                  content: Row(
                    children: [
                      const Icon(Icons.warning_amber_rounded, color: Colors.white),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          recStr,
                          style: const TextStyle(fontWeight: FontWeight.bold),
                        ),
                      ),
                    ],
                  ),
                  backgroundColor: Colors.redAccent,
                  duration: const Duration(seconds: 5),
                  behavior: SnackBarBehavior.floating,
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                ),
              );
            }
          }
        }
      }
    }
    
    final meds = await ApiService.getMedicines();
    if (meds != null) {
      _medicines = meds;
    }

    final allHealth = await ApiService.getAllHealthData();
    if (allHealth != null) {
      _allHealthData = allHealth.reversed.toList(); // Newest first
    }
    
    final reports = await ApiService.getMedicalReports();
    if (reports != null) {
      _medicalReports = reports;
    }

    setState(() => _isLoading = false);
  }

  Future<void> _syncDummyData() async {
    setState(() => _isLoading = true);
    int seed = DateTime.now().second;
    Map<String, dynamic> fakeData = {
      'heart_rate': 75 + (seed % 15),
      'sleep_hours': 6.5 + (seed % 3),
      'steps': 5000 + (seed * 100),
      'spo2': 95 + (seed % 5),
      'calories': 1800 + (seed * 10),
    };
    await ApiService.postHealthData(fakeData);
    await _fetchData();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(_getTitle()),
        actions: [
          IconButton(
            icon: const Icon(Icons.logout, color: Colors.blueGrey),
            tooltip: 'Logout',
            onPressed: () async {
              await ApiService.logout();
              if (mounted) {
                Navigator.pushAndRemoveUntil(
                  context,
                  MaterialPageRoute(builder: (_) => const WelcomeScreen()),
                  (route) => false,
                );
              }
            },
          ),
          const SizedBox(width: 8),
          const CircleAvatar(
            backgroundColor: AppTheme.primaryBlue,
            child: Icon(Icons.person, color: Colors.white),
          ),
          const SizedBox(width: 16),
        ],
      ),
      body: _isLoading ? const Center(child: CircularProgressIndicator(color: AppTheme.primaryBlue)) : IndexedStack(
        index: _currentIndex,
        children: [
          _buildHomeTab(),
          _buildAnalyticsTab(),
          _buildMedicineTab(),
          _buildProfileTab(),
          const ChatbotScreen(),
        ],
      ),
      bottomNavigationBar: BottomNavigationBar(
        currentIndex: _currentIndex,
        onTap: (i) => setState(() => _currentIndex = i),
        selectedItemColor: AppTheme.primaryBlue,
        unselectedItemColor: Colors.grey,
        type: BottomNavigationBarType.fixed,
        items: const [
          BottomNavigationBarItem(icon: Icon(Icons.home), label: 'Home'),
          BottomNavigationBarItem(icon: Icon(Icons.analytics), label: 'Analytics'),
          BottomNavigationBarItem(icon: Icon(Icons.local_hospital), label: 'Medicines'),
          BottomNavigationBarItem(icon: Icon(Icons.person), label: 'Profile'),
          BottomNavigationBarItem(
            icon: Icon(Icons.chat_bubble_outline),
            activeIcon: Icon(Icons.chat_bubble),
            label: 'AI Chat',
          ),
        ],
      ),
      floatingActionButton: _currentIndex == 0 ? FloatingActionButton(
        onPressed: _syncDummyData,
        backgroundColor: AppTheme.primaryBlue,
        child: const Icon(Icons.sync, color: Colors.white),
      ) : null,
      // Hide the default appBar when chatbot tab is active (it has its own AppBar)
    );
  }

  String _resolveFileUrl(String? path) {
    if (path == null || path.isEmpty) return '';
    if (path.startsWith('http://') || path.startsWith('https://')) {
      return path;
    }
    // Remove '/api' from baseUrl and append path
    final base = ApiService.baseUrl.replaceFirst('/api', '');
    return '$base$path';
  }

  List<Map<String, String>> _metricsTableRows(Map<String, dynamic> report) {
    final rawTable = report['metrics_table'];
    if (rawTable is List) {
      return rawTable
          .whereType<Map>()
          .map((row) => {
                'metric': row['metric']?.toString() ?? '',
                'value': row['value']?.toString() ?? '',
                'unit': row['unit']?.toString() ?? '',
              })
          .where((row) => row['metric']!.isNotEmpty)
          .toList();
    }

    final rawMetrics = report['extracted_metrics'];
    if (rawMetrics is! Map) return [];

    final metrics = Map<String, dynamic>.from(rawMetrics);
    final rows = <Map<String, String>>[];

    final systolic = metrics['blood_pressure_systolic'];
    final diastolic = metrics['blood_pressure_diastolic'];
    if (systolic != null || diastolic != null) {
      rows.add({
        'metric': 'Blood Pressure',
        'value': '${systolic ?? '--'}/${diastolic ?? '--'}',
        'unit': 'mmHg',
      });
    }

    const labels = {
      'heart_rate': ('Heart Rate', 'bpm'),
      'spo2': ('SpO2', '%'),
      'hemoglobin': ('Hemoglobin', 'g/dL'),
      'glucose': ('Glucose', 'mg/dL'),
      'cholesterol_total': ('Total Cholesterol', 'mg/dL'),
      'hdl': ('HDL', 'mg/dL'),
      'ldl': ('LDL', 'mg/dL'),
      'triglycerides': ('Triglycerides', 'mg/dL'),
    };

    for (final entry in labels.entries) {
      final value = metrics[entry.key];
      if (value == null) continue;
      rows.add({
        'metric': entry.value.$1,
        'value': value.toString(),
        'unit': entry.value.$2,
      });
    }

    return rows;
  }

  Widget _buildMetricsTable(List<Map<String, String>> rows) {
    if (rows.isEmpty) return const SizedBox.shrink();

    Widget cell(String text, {bool isHeader = false}) {
      return Padding(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 10),
        child: Text(
          text,
          style: TextStyle(
            fontSize: 13,
            fontWeight: isHeader ? FontWeight.w700 : FontWeight.w500,
            color: isHeader ? AppTheme.primaryBlue : Colors.black87,
          ),
        ),
      );
    }

    return Container(
      width: double.infinity,
      decoration: BoxDecoration(
        border: Border.all(color: Colors.grey.shade300),
        borderRadius: BorderRadius.circular(8),
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(8),
        child: Table(
          columnWidths: const {
            0: FlexColumnWidth(2.2),
            1: FlexColumnWidth(1.3),
            2: FlexColumnWidth(1),
          },
          border: TableBorder(
            horizontalInside: BorderSide(color: Colors.grey.shade200),
            verticalInside: BorderSide(color: Colors.grey.shade200),
          ),
          children: [
            TableRow(
              decoration: BoxDecoration(color: Colors.blue.shade50),
              children: [
                cell('Metric', isHeader: true),
                cell('Value', isHeader: true),
                cell('Unit', isHeader: true),
              ],
            ),
            ...rows.map(
              (row) => TableRow(
                children: [
                  cell(row['metric'] ?? ''),
                  cell(row['value'] ?? ''),
                  cell(row['unit'] ?? ''),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  void _viewImage(BuildContext context, String imageUrl) {
    showDialog(
      context: context,
      builder: (context) => Dialog(
        backgroundColor: Colors.transparent,
        insetPadding: const EdgeInsets.all(10),
        child: Stack(
          alignment: Alignment.topRight,
          children: [
            InteractiveViewer(
              panEnabled: true,
              boundaryMargin: const EdgeInsets.all(20),
              minScale: 0.5,
              maxScale: 4,
              child: ClipRRect(
                borderRadius: BorderRadius.circular(16),
                child: Image.network(
                  imageUrl,
                  fit: BoxFit.contain,
                  loadingBuilder: (context, child, loadingProgress) {
                    if (loadingProgress == null) return child;
                    return const Center(
                      child: CircularProgressIndicator(color: Colors.white),
                    );
                  },
                  errorBuilder: (context, error, stackTrace) {
                    return Container(
                      color: Colors.white,
                      padding: const EdgeInsets.all(20),
                      child: const Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Icon(Icons.broken_image, size: 60, color: Colors.red),
                          SizedBox(height: 12),
                          Text('Could not load image', style: TextStyle(color: Colors.black)),
                        ],
                      ),
                    );
                  },
                ),
              ),
            ),
            IconButton(
              icon: const Icon(Icons.close, color: Colors.white, size: 30),
              onPressed: () => Navigator.pop(context),
            ),
          ],
        ),
      ),
    );
  }

  String _getTitle() {
    switch (_currentIndex) {
      case 0: return 'Hello, $_userName';
      case 1: return 'Health Analytics';
      case 2: return 'Medicine Reminders';
      case 3: return 'Your Profile';
      case 4: return 'AI Health Assistant';
      default: return 'Smart Health AI';
    }
  }

  // --- HOME TAB ---
  Widget _buildHomeTab() {
    return SafeArea(
      child: SingleChildScrollView(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _buildRiskPredictionCard(),
            const SizedBox(height: 24),
            Row(
              children: [
                Expanded(
                  child: ElevatedButton.icon(
                    onPressed: () async {
                      final picked = await FilePicker.platform.pickFiles(
                        type: FileType.custom,
                        allowedExtensions: ['pdf', 'png', 'jpg', 'jpeg', 'webp'],
                      );
                      final selectedPath = picked?.files.single.path;
                      if (selectedPath != null) {
                        setState(() => _isLoading = true);
                        try {
                          final result = await ApiService.uploadMedicalReport(selectedPath);
                          if (result != null) {
                            ScaffoldMessenger.of(context).showSnackBar(
                              const SnackBar(content: Text('Report uploaded and extracted successfully.')),
                            );
                            await _fetchData();
                          }
                        } catch (e) {
                          ScaffoldMessenger.of(context).showSnackBar(SnackBar(
                            content: Text('Upload Error: ${e.toString()}'),
                            backgroundColor: Colors.red,
                          ));
                        } finally {
                          setState(() => _isLoading = false);
                        }
                      }
                    },
                    icon: const Icon(Icons.upload_file),
                    label: const Text('Upload PDF/Image'),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: AppTheme.primaryBlue,
                      foregroundColor: Colors.white,
                      padding: const EdgeInsets.symmetric(vertical: 12),
                    ),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: ElevatedButton.icon(
                    onPressed: () async {
                      setState(() => _isLoading = true);
                      try {
                        final healthData = await HealthSyncService.syncRealData();
                        
                        if (healthData != null) {
                          final result = await ApiService.syncSmartwatchData(healthData);
                          if (result != null) {
                            ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Real Health Data Synced!')));
                            await _fetchData();
                          } else {
                            ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Failed to sync to server.')));
                          }
                        } else {
                          ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Health permissions denied or unavailable.')));
                        }
                      } catch (e) {
                        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Error: ${e.toString()}'), backgroundColor: Colors.red));
                      }
                      setState(() => _isLoading = false);
                    },
                    icon: const Icon(Icons.watch),
                    label: const Text('Google Sync'),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Colors.indigo,
                      foregroundColor: Colors.white,
                      padding: const EdgeInsets.symmetric(vertical: 12),
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            SizedBox(
              width: double.infinity,
              child: ElevatedButton.icon(
                onPressed: () {
                  Navigator.push(context, MaterialPageRoute(builder: (_) => const DiseasePredictionScreen()));
                },
                icon: const Icon(Icons.medical_services),
                label: const Text('Specific Disease Risk Prediction'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppTheme.secondaryTeal,
                  foregroundColor: Colors.white,
                  padding: const EdgeInsets.symmetric(vertical: 16),
                ),
              ),
            ),
            const SizedBox(height: 32),
            Text('Today\'s Metrics', style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.bold)),
            const SizedBox(height: 16),
            Row(
              children: [
                Expanded(child: _buildMetricCard('Heart Rate', _heartRate, Icons.favorite, Colors.redAccent)),
                const SizedBox(width: 16),
                Expanded(child: _buildMetricCard('Steps', _steps, Icons.directions_walk, AppTheme.secondaryTeal)),
              ],
            ),
            const SizedBox(height: 16),
            Row(
              children: [
                Expanded(child: _buildMetricCard('Sleep', _sleep, Icons.bedtime, Colors.indigo)),
                const SizedBox(width: 16),
                Expanded(child: _buildMetricCard('SpO2', _spo2, Icons.bloodtype, AppTheme.primaryBlue)),
              ],
            ),
            const SizedBox(height: 32),
            Text('Activity Trend', style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.bold)),
            const SizedBox(height: 16),
            _buildActivityChart(),
          ],
        ),
      ),
    );
  }

  // --- PROFILE TAB ---
  Widget _buildProfileTab() {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Center(
        child: GlassCard(
          padding: const EdgeInsets.all(32),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const CircleAvatar(
                radius: 50,
                backgroundColor: AppTheme.primaryBlue,
                child: Icon(Icons.person, size: 50, color: Colors.white),
              ),
              const SizedBox(height: 24),
              Text(_userName, style: const TextStyle(fontSize: 24, fontWeight: FontWeight.bold)),
              const SizedBox(height: 8),
              Text(_userProfile['email'] ?? '', style: const TextStyle(color: Colors.grey)),
              const SizedBox(height: 32),
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                children: [
                  _buildProfileStat('Age', _userProfile['age']?.toString() ?? '--'),
                  _buildProfileStat('Height', '${_userProfile['height'] ?? '--'} cm'),
                  _buildProfileStat('Weight', '${_userProfile['weight'] ?? '--'} kg'),
                ],
              ),
              const SizedBox(height: 32),
              OutlinedButton.icon(
                onPressed: () async {
                  final result = await showDialog<bool>(
                    context: context,
                    builder: (context) => ProfileEditDialog(userProfile: _userProfile),
                  );
                  if (result == true) {
                    _fetchData(); // Refresh metrics heavily
                  }
                },
                icon: const Icon(Icons.edit),
                label: const Text('Edit Profile Details'),
                style: OutlinedButton.styleFrom(
                  foregroundColor: AppTheme.primaryBlue,
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(999)),
                  padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
                ),
              ),
              const SizedBox(height: 16),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildProfileStat(String label, String value) {
    return Column(
      children: [
        Text(label, style: const TextStyle(color: Colors.grey, fontSize: 14)),
        const SizedBox(height: 4),
        Text(value, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 20)),
      ],
    );
  }

  Widget _buildRiskPredictionCard() {
    return Container(
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [AppTheme.primaryBlue, AppTheme.primaryBlue.withOpacity(0.8)],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(24),
        boxShadow: [
          BoxShadow(
            color: AppTheme.primaryBlue.withOpacity(0.3),
            blurRadius: 15,
            offset: const Offset(0, 8),
          )
        ],
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('AI Risk Prediction', style: TextStyle(color: Colors.white70, fontSize: 16)),
                const SizedBox(height: 8),
                Text(
                  'Risk Level: $_riskLevel',
                  style: const TextStyle(color: Colors.white, fontSize: 24, fontWeight: FontWeight.bold),
                ),
                const SizedBox(height: 8),
                Text(_recommendation, style: const TextStyle(color: Colors.white70, fontSize: 12)),
              ],
            ),
          ),
          Stack(
            alignment: Alignment.center,
            children: [
              SizedBox(
                width: 80,
                height: 80,
                child: CircularProgressIndicator(
                  value: _riskPercentage / 100,
                  backgroundColor: Colors.white24,
                  valueColor: const AlwaysStoppedAnimation(Colors.white),
                  strokeWidth: 8,
                ),
              ),
              Text(
                '${_riskPercentage.toInt()}%',
                style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 18),
              )
            ],
          )
        ],
      ),
    );
  }

  Widget _buildMetricCard(String title, String value, IconData icon, Color color) {
    return GlassCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            padding: const EdgeInsets.all(8),
            decoration: BoxDecoration(color: color.withOpacity(0.1), shape: BoxShape.circle),
            child: Icon(icon, color: color, size: 24),
          ),
          const SizedBox(height: 16),
          Text(title, style: const TextStyle(color: Colors.grey, fontSize: 14)),
          const SizedBox(height: 8),
          Text(value, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 24)),
        ],
      ),
    );
  }

  Widget _buildActivityChart() {
    return SizedBox(
      height: 200,
      child: GlassCard(
        padding: const EdgeInsets.all(16),
        child: BarChart(
          BarChartData(
            gridData: FlGridData(show: false),
            borderData: FlBorderData(show: false),
            titlesData: FlTitlesData(
              leftTitles: AxisTitles(sideTitles: SideTitles(showTitles: false)),
              topTitles: AxisTitles(sideTitles: SideTitles(showTitles: false)),
              rightTitles: AxisTitles(sideTitles: SideTitles(showTitles: false)),
              bottomTitles: AxisTitles(
                sideTitles: SideTitles(
                  showTitles: true,
                  getTitlesWidget: (double value, TitleMeta meta) {
                    const days = ['M', 'T', 'W', 'T', 'F', 'S', 'S'];
                    return Text(days[value.toInt() % 7], style: const TextStyle(fontSize: 12));
                  },
                ),
              ),
            ),
            barGroups: [
              for (int i = 0; i < 7; i++)
                BarChartGroupData(
                  x: i,
                  barRods: [BarChartRodData(toY: (i * 1.5 + 4) % 10 + 2, color: AppTheme.secondaryTeal, width: 16, borderRadius: BorderRadius.circular(4))],
                ),
            ],
          ),
        ),
      ),
    );
  }

  // --- ANALYTICS TAB ---
  Widget _buildAnalyticsTab() {
    return DefaultTabController(
      length: 2,
      child: Column(
        children: [
          Container(
            color: Colors.white,
            child: const TabBar(
              labelColor: AppTheme.primaryBlue,
              unselectedLabelColor: Colors.grey,
              indicatorColor: AppTheme.primaryBlue,
              tabs: [
                Tab(icon: Icon(Icons.watch), text: 'Google Fit Syncs'),
                Tab(icon: Icon(Icons.description), text: 'Medical Reports'),
              ],
            ),
          ),
          Expanded(
            child: TabBarView(
              children: [
                // Tab 1: Google Fit Data
                _allHealthData.isEmpty
                    ? const Center(child: Text('No synced data found.', style: TextStyle(color: Colors.grey)))
                    : ListView.builder(
                        padding: const EdgeInsets.all(16),
                        itemCount: _allHealthData.length,
                        itemBuilder: (context, index) {
                          final item = _allHealthData[index];
                          final date = item['synced_at'] != null 
                            ? DateFormat('MMM dd, yyyy - hh:mm a').format(DateTime.parse(item['synced_at']).toLocal())
                            : 'Unknown Date';
                          return Padding(
                            padding: const EdgeInsets.only(bottom: 12),
                            child: GlassCard(
                              padding: const EdgeInsets.all(16),
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Row(
                                    children: [
                                      const Icon(Icons.sync, color: AppTheme.primaryBlue, size: 20),
                                      const SizedBox(width: 8),
                                      Text(date, style: const TextStyle(fontWeight: FontWeight.bold, color: Colors.black87)),
                                    ],
                                  ),
                                  const Divider(height: 24),
                                  Row(
                                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                    children: [
                                      _buildMiniStat(Icons.favorite, Colors.red, '${item['heart_rate'] ?? '--'} bpm'),
                                      _buildMiniStat(Icons.directions_walk, AppTheme.secondaryTeal, '${item['steps'] ?? '--'} steps'),
                                      _buildMiniStat(Icons.bedtime, Colors.indigo, '${item['sleep_hours'] ?? '--'} h'),
                                    ],
                                  ),
                                  const SizedBox(height: 12),
                                  Row(
                                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                    children: [
                                      _buildMiniStat(Icons.bloodtype, AppTheme.primaryBlue, '${item['spo2'] ?? '--'}% SpO2'),
                                      _buildMiniStat(Icons.local_fire_department, Colors.orange, '${item['calories'] ?? '--'} kcal'),
                                      _buildMiniStat(Icons.monitor_heart, Colors.purple, '${item['hrv'] ?? '--'} ms HRV'),
                                    ],
                                  ),
                                ],
                              ),
                            ),
                          );
                        },
                      ),
                      
                // Tab 2: Medical Reports
                _medicalReports.isEmpty
                    ? const Center(child: Text('No uploaded reports found.', style: TextStyle(color: Colors.grey)))
                    : ListView.builder(
                        padding: const EdgeInsets.all(16),
                        itemCount: _medicalReports.length,
                        itemBuilder: (context, index) {
                          final report = _medicalReports[index];
                          final date = report['uploaded_at'] != null 
                            ? DateFormat('MMM dd, yyyy - hh:mm a').format(DateTime.parse(report['uploaded_at']).toLocal())
                            : 'Unknown Date';
                          final text = report['extracted_text'] ?? 'No summary available';
                          final tableRows = _metricsTableRows(report);
                          final fileUrl = report['file'];
                          final resolvedUrl = _resolveFileUrl(fileUrl);
                          final isImage = fileUrl != null &&
                              (fileUrl.toLowerCase().endsWith('.png') ||
                                  fileUrl.toLowerCase().endsWith('.jpg') ||
                                  fileUrl.toLowerCase().endsWith('.jpeg') ||
                                  fileUrl.toLowerCase().endsWith('.webp'));

                          return Padding(
                            padding: const EdgeInsets.only(bottom: 12),
                            child: GlassCard(
                              padding: const EdgeInsets.all(16),
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Row(
                                    children: [
                                      const Icon(Icons.medical_information, color: AppTheme.secondaryTeal, size: 20),
                                      const SizedBox(width: 8),
                                      Text(date, style: const TextStyle(fontWeight: FontWeight.bold, color: Colors.black87)),
                                    ],
                                  ),
                                  const Divider(height: 24),
                                  const Text('AI Summary:', style: TextStyle(fontWeight: FontWeight.w600, fontSize: 14)),
                                  const SizedBox(height: 8),
                                  Container(
                                    padding: const EdgeInsets.all(12),
                                    width: double.infinity,
                                    decoration: BoxDecoration(
                                      color: Colors.grey.shade100,
                                      borderRadius: BorderRadius.circular(8),
                                    ),
                                    child: Text(text, style: const TextStyle(fontSize: 13, color: Colors.black87)),
                                  ),
                                  if (tableRows.isNotEmpty) ...[
                                    const SizedBox(height: 16),
                                    const Text('Lab Metrics Table:', style: TextStyle(fontWeight: FontWeight.w600, fontSize: 14)),
                                    const SizedBox(height: 8),
                                    _buildMetricsTable(tableRows),
                                  ],
                                  if (fileUrl != null && fileUrl.isNotEmpty) ...[
                                    const SizedBox(height: 16),
                                    const Text('Report Document:', style: TextStyle(fontWeight: FontWeight.w600, fontSize: 14)),
                                    const SizedBox(height: 8),
                                    if (isImage)
                                      GestureDetector(
                                        onTap: () => _viewImage(context, resolvedUrl),
                                        child: ClipRRect(
                                          borderRadius: BorderRadius.circular(8),
                                          child: Container(
                                            width: double.infinity,
                                            height: 150,
                                            color: Colors.grey.shade200,
                                            child: Image.network(
                                              resolvedUrl,
                                              fit: BoxFit.cover,
                                              errorBuilder: (context, error, stackTrace) => const Center(
                                                child: Icon(Icons.image, size: 50, color: Colors.grey),
                                              ),
                                            ),
                                          ),
                                        ),
                                      )
                                    else
                                      Container(
                                        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                                        decoration: BoxDecoration(
                                          color: Colors.blue.shade50,
                                          borderRadius: BorderRadius.circular(8),
                                          border: Border.all(color: Colors.blue.shade100),
                                        ),
                                        child: Row(
                                          children: [
                                            const Icon(Icons.insert_drive_file, color: Colors.blue),
                                            const SizedBox(width: 8),
                                            Expanded(
                                              child: Text(
                                                fileUrl.split('/').last,
                                                style: const TextStyle(fontSize: 13, color: Colors.blue, fontWeight: FontWeight.bold),
                                                overflow: TextOverflow.ellipsis,
                                              ),
                                            ),
                                          ],
                                        ),
                                      ),
                                  ],
                                ],
                              ),
                            ),
                          );
                        },
                      ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildMiniStat(IconData icon, Color color, String value) {
    return Column(
      children: [
        Icon(icon, color: color, size: 20),
        const SizedBox(height: 4),
        Text(value, style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w500)),
      ],
    );
  }

  // --- MEDICINE TAB ---
  Widget _buildMedicineTab() {
    return SafeArea(
      child: Column(
        children: [
          Padding(
            padding: const EdgeInsets.all(20),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text('Medicine Reminders', style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.bold)),
                ElevatedButton.icon(
                  onPressed: () => _showMedicineDialog(),
                  icon: const Icon(Icons.add),
                  label: const Text('Add'),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppTheme.primaryBlue,
                    foregroundColor: Colors.white,
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
                  ),
                )
              ],
            ),
          ),
          Expanded(
            child: _medicines.isEmpty
                ? const Center(child: Text('No medicines added yet.', style: TextStyle(color: Colors.grey)))
                : ListView.builder(
                    padding: const EdgeInsets.symmetric(horizontal: 20),
                    itemCount: _medicines.length,
                    itemBuilder: (context, index) {
                      final med = _medicines[index];
                      final isTaken = med['status'] == true;
                      
                      // Formatting time string if needed, assuming HH:MM format from backend
                      String timeStr = med['timing'] ?? '';
                      if (timeStr.length > 5) timeStr = timeStr.substring(0, 5);

                      return Dismissible(
                        key: Key(med['id'].toString()),
                        direction: DismissDirection.endToStart,
                        background: Container(
                          alignment: Alignment.centerRight,
                          padding: const EdgeInsets.only(right: 20),
                          decoration: BoxDecoration(
                            color: Colors.redAccent,
                            borderRadius: BorderRadius.circular(16),
                          ),
                          child: const Icon(Icons.delete, color: Colors.white),
                        ),
                        onDismissed: (direction) async {
                          await ApiService.deleteMedicine(med['id']);
                          await NotificationService.cancelMedicineAlarms(med['id']);
                          setState(() {
                            _medicines.removeAt(index);
                          });
                        },
                        child: Padding(
                          padding: const EdgeInsets.only(bottom: 12),
                          child: GlassCard(
                            padding: const EdgeInsets.all(8),
                            child: ListTile(
                            leading: Container(
                              padding: const EdgeInsets.all(12),
                              decoration: BoxDecoration(
                                color: isTaken ? Colors.green.withOpacity(0.1) : AppTheme.primaryBlue.withOpacity(0.1),
                                shape: BoxShape.circle,
                              ),
                              child: Icon(
                                isTaken ? Icons.check_circle : Icons.medication,
                                color: isTaken ? Colors.green : AppTheme.primaryBlue,
                              ),
                            ),
                            title: Text(med['medicine_name'] ?? '', style: TextStyle(
                              fontWeight: FontWeight.bold,
                              decoration: isTaken ? TextDecoration.lineThrough : null,
                              color: isTaken ? Colors.grey : Colors.black87,
                            )),
                            subtitle: Text('${med['dosage']} • $timeStr', style: TextStyle(
                              decoration: isTaken ? TextDecoration.lineThrough : null,
                            )),
                            trailing: Row(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                IconButton(
                                  icon: const Icon(Icons.edit, color: Colors.blueGrey),
                                  onPressed: () => _showMedicineDialog(medicine: med),
                                ),
                                Checkbox(
                                  value: isTaken,
                                  activeColor: Colors.green,
                                  onChanged: (bool? value) async {
                                    if (value != null) {
                                      setState(() {
                                        med['status'] = value;
                                      });
                                      await ApiService.updateMedicineStatus(med['id'], value);
                                      _fetchData();
                                    }
                                  },
                                ),
                              ],
                            ),
                          ),
                        ),
                      ),
                    );
                    },
                  ),
          ),
        ],
      ),
    );
  }

  void _showMedicineDialog({Map<String, dynamic>? medicine}) {
    final isEdit = medicine != null;
    final nameCtrl = TextEditingController(text: isEdit ? medicine['medicine_name'] : '');
    final dosageCtrl = TextEditingController(text: isEdit ? medicine['dosage'] : '');
    
    TimeOfDay selectedTime = TimeOfDay.now();
    if (isEdit && medicine['timing'] != null) {
      final parts = medicine['timing'].toString().split(':');
      if (parts.length >= 2) {
        selectedTime = TimeOfDay(hour: int.parse(parts[0]), minute: int.parse(parts[1]));
      }
    }

    DateTime startDate = isEdit && medicine['start_date'] != null 
        ? DateTime.parse(medicine['start_date']) 
        : DateTime.now();
    DateTime endDate = isEdit && medicine['end_date'] != null 
        ? DateTime.parse(medicine['end_date']) 
        : DateTime.now().add(const Duration(days: 7));

    showDialog(
      context: context,
      builder: (context) {
        return StatefulBuilder(
          builder: (context, setStateDialog) {
            return AlertDialog(
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
              title: Text(isEdit ? 'Edit Medicine' : 'Add Medicine'),
              content: SingleChildScrollView(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    TextField(
                      controller: nameCtrl,
                      decoration: const InputDecoration(labelText: 'Medicine Name', border: OutlineInputBorder()),
                    ),
                    const SizedBox(height: 16),
                    TextField(
                      controller: dosageCtrl,
                      decoration: const InputDecoration(labelText: 'Dosage (e.g. 1 Pill, 500mg)', border: OutlineInputBorder()),
                    ),
                    const SizedBox(height: 16),
                    ListTile(
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(4),
                        side: BorderSide(color: Colors.grey.shade400)
                      ),
                      title: const Text('Time'),
                      trailing: Text(selectedTime.format(context), style: const TextStyle(fontWeight: FontWeight.bold)),
                      onTap: () async {
                        final t = await showTimePicker(context: context, initialTime: selectedTime);
                        if (t != null) {
                          setStateDialog(() => selectedTime = t);
                        }
                      },
                    ),
                    const SizedBox(height: 16),
                    ListTile(
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(4),
                        side: BorderSide(color: Colors.grey.shade400)
                      ),
                      title: const Text('Start Date'),
                      trailing: Text(DateFormat('MMM dd, yyyy').format(startDate), style: const TextStyle(fontWeight: FontWeight.bold)),
                      onTap: () async {
                        final d = await showDatePicker(
                          context: context, 
                          initialDate: startDate, 
                          firstDate: DateTime(2020), 
                          lastDate: DateTime(2030)
                        );
                        if (d != null) {
                          setStateDialog(() {
                            startDate = d;
                            if (endDate.isBefore(startDate)) endDate = startDate;
                          });
                        }
                      },
                    ),
                    const SizedBox(height: 16),
                    ListTile(
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(4),
                        side: BorderSide(color: Colors.grey.shade400)
                      ),
                      title: const Text('End Date'),
                      trailing: Text(DateFormat('MMM dd, yyyy').format(endDate), style: const TextStyle(fontWeight: FontWeight.bold)),
                      onTap: () async {
                        final d = await showDatePicker(
                          context: context, 
                          initialDate: endDate, 
                          firstDate: startDate, 
                          lastDate: DateTime(2030)
                        );
                        if (d != null) setStateDialog(() => endDate = d);
                      },
                    ),
                  ],
                ),
              ),
              actions: [
                TextButton(onPressed: () => Navigator.pop(context), child: const Text('Cancel')),
                ElevatedButton(
                  style: ElevatedButton.styleFrom(backgroundColor: AppTheme.primaryBlue, foregroundColor: Colors.white),
                  onPressed: () async {
                    if (nameCtrl.text.isEmpty || dosageCtrl.text.isEmpty) return;
                    
                    final String timeStr = '${selectedTime.hour.toString().padLeft(2, '0')}:${selectedTime.minute.toString().padLeft(2, '0')}';
                    final String startDateStr = DateFormat('yyyy-MM-dd').format(startDate);
                    final String endDateStr = DateFormat('yyyy-MM-dd').format(endDate);
                    
                    final data = {
                      'medicine_name': nameCtrl.text,
                      'dosage': dosageCtrl.text,
                      'timing': timeStr,
                      'start_date': startDateStr,
                      'end_date': endDateStr,
                      'status': isEdit ? medicine['status'] : false,
                    };
                    
                    Navigator.pop(context); // Close dialog
                    setState(() => _isLoading = true);
                    
                    try {
                      Map<String, dynamic>? savedMed;
                      if (isEdit) {
                        savedMed = await ApiService.updateMedicineData(medicine['id'], data);
                      } else {
                        savedMed = await ApiService.addMedicine(data);
                      }

                      if (savedMed != null) {
                        // Schedule Alarms
                        await NotificationService.scheduleMedicineAlarms(
                          medicineId: savedMed['id'],
                          medicineName: savedMed['medicine_name'],
                          dosage: savedMed['dosage'],
                          timeStr: savedMed['timing'],
                          startDate: DateTime.parse(savedMed['start_date']),
                          endDate: DateTime.parse(savedMed['end_date']),
                        );
                      }
                    } finally {
                      await _fetchData();
                    }
                  },
                  child: const Text('Save'),
                )
              ],
            );
          }
        );
      }
    );
  }
}

