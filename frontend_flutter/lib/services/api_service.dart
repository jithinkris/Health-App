import 'dart:convert';
import 'dart:io' show Platform;
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import 'package:flutter/foundation.dart' show kIsWeb;

class ApiService {
  static String get baseUrl {
    if (kIsWeb) return 'https://health-app-g368.onrender.com/api';
    if (Platform.isAndroid) return 'https://health-app-g368.onrender.com/api';
    return 'https://health-app-g368.onrender.com/api';
  }

  static Future<Map<String, String>> _headers() async {
    final prefs = await SharedPreferences.getInstance();
    final token = prefs.getString('access') ?? '';
    return {
      'Content-Type': 'application/json',
      'Authorization': 'Bearer $token',
    };
  }

  static Future<void> logout() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove('access');
    await prefs.remove('refresh');
  }

  static Future<Map<String, dynamic>?> getCurrentUser() async {
    try {
      final response = await http.get(
        Uri.parse('$baseUrl/me/'),
        headers: await _headers(),
      );
      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      }
      return null;
    } catch (_) {
      return null;
    }
  }

  static Future<Map<String, dynamic>?> updateCurrentUser(Map<String, dynamic> data) async {
    try {
      final response = await http.patch(
        Uri.parse('$baseUrl/me/'),
        headers: await _headers(),
        body: jsonEncode(data),
      );
      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      }
      return null;
    } catch (_) {
      return null;
    }
  }

  static Future<Map<String, dynamic>?> predictRisk(Map<String, dynamic> data) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/predict-risk-ml/'),
        headers: await _headers(),
        body: jsonEncode(data),
      );
      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      }
      return null;
    } catch (_) {
      return null;
    }
  }

  static Future<Map<String, dynamic>?> getLatestHealthData() async {
    try {
      final response = await http.get(
        Uri.parse('$baseUrl/health/'),
        headers: await _headers(),
      );
      if (response.statusCode == 200) {
        List data = jsonDecode(response.body);
        if (data.isNotEmpty) {
          return data.last;
        }
      }
      return null;
    } catch (_) {
      return null;
    }
  }

  static Future<bool> postHealthData(Map<String, dynamic> data) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/health/'),
        headers: await _headers(),
        body: jsonEncode(data),
      );
      return response.statusCode == 201;
    } catch (_) {
      return false;
    }
  }

  static Future<List<dynamic>?> getMedicines() async {
    try {
      final response = await http.get(
        Uri.parse('$baseUrl/medicine/'),
        headers: await _headers(),
      );
      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      }
      return null;
    } catch (_) {
      return null;
    }
  }

  static Future<Map<String, dynamic>?> addMedicine(Map<String, dynamic> data) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/medicine/'),
        headers: await _headers(),
        body: jsonEncode(data),
      );
      if (response.statusCode == 201) {
        return jsonDecode(response.body);
      }
      return null;
    } catch (_) {
      return null;
    }
  }

  static Future<Map<String, dynamic>?> updateMedicineStatus(int id, bool status) async {
    try {
      final response = await http.patch(
        Uri.parse('$baseUrl/medicine/$id/'),
        headers: await _headers(),
        body: jsonEncode({'status': status}),
      );
      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      }
      return null;
    } catch (_) {
      return null;
    }
  }

  static Future<bool> deleteMedicine(int id) async {
    try {
      final response = await http.delete(
        Uri.parse('$baseUrl/medicine/$id/'),
        headers: await _headers(),
      );
      return response.statusCode == 204;
    } catch (_) {
      return false;
    }
  }

  static Future<Map<String, dynamic>?> updateMedicineData(int id, Map<String, dynamic> data) async {
    try {
      final response = await http.patch(
        Uri.parse('$baseUrl/medicine/$id/'),
        headers: await _headers(),
        body: jsonEncode(data),
      );
      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      }
      return null;
    } catch (_) {
      return null;
    }
  }

  static Future<Map<String, dynamic>?> uploadMedicalReport(String imagePath) async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final token = prefs.getString('access') ?? '';
      
      var request = http.MultipartRequest('POST', Uri.parse('$baseUrl/upload-report/'));
      request.headers.addAll({
        'Authorization': 'Bearer $token',
      });
      request.files.add(await http.MultipartFile.fromPath('image', imagePath));
      
      var streamedResponse = await request.send();
      var response = await http.Response.fromStream(streamedResponse);
      
      if (response.statusCode == 201) {
        return jsonDecode(response.body);
      }
      return null;
    } catch (_) {
      return null;
    }
  }

  static Future<List<dynamic>?> getMedicalReports() async {
    try {
      final response = await http.get(
        Uri.parse('$baseUrl/upload-report/'),
        headers: await _headers(),
      );
      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      }
      return null;
    } catch (_) {
      return null;
    }
  }

  static Future<List<dynamic>?> getAllHealthData() async {
    try {
      final response = await http.get(
        Uri.parse('$baseUrl/health/'),
        headers: await _headers(),
      );
      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      }
      return null;
    } catch (_) {
      return null;
    }
  }

  static Future<Map<String, dynamic>?> syncSmartwatchData(Map<String, dynamic> data) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/sync-smartwatch/'),
        headers: await _headers(),
        body: jsonEncode(data),
      );
      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      }
      return null;
    } catch (_) {
      return null;
    }
  }

  static Future<Map<String, dynamic>?> predictSpecificDisease(String diseaseName) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/predict-disease/'),
        headers: await _headers(),
        body: jsonEncode({'disease_name': diseaseName}),
      );
      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      }
      return null;
    } catch (_) {
      return null;
    }
  }

  // ── Chatbot Methods ────────────────────────────────────────────────────────

  static Future<Map<String, dynamic>?> sendChatMessage(String message) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/chat/'),
        headers: await _headers(),
        body: jsonEncode({'message': message}),
      );
      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      }
      return null;
    } catch (_) {
      return null;
    }
  }

  static Future<List<dynamic>?> getChatHistory() async {
    try {
      final response = await http.get(
        Uri.parse('$baseUrl/chat/history/'),
        headers: await _headers(),
      );
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        return data['messages'] as List<dynamic>?;
      }
      return null;
    } catch (_) {
      return null;
    }
  }

  static Future<bool> clearChatHistory() async {
    try {
      final response = await http.delete(
        Uri.parse('$baseUrl/chat/history/'),
        headers: await _headers(),
      );
      return response.statusCode == 200;
    } catch (_) {
      return false;
    }
  }
}

