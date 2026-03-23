import 'dart:convert';
import 'package:http/http.dart' as http;

import 'endpoints.dart';

class ApiClient {
  static Uri _uri(String path) => Uri.parse("${Endpoints.baseUrl}$path");

  static Future<Map<String, dynamic>> post(
    String path, {
    Map<String, dynamic>? body,
    Map<String, String>? headers,
  }) async {
    final h = <String, String>{
      "Content-Type": "application/json",
      ...?headers,
    };

    final res = await http.post(
      _uri(path),
      headers: h,
      body: jsonEncode(body ?? {}),
    );

    final data = res.body.isNotEmpty ? jsonDecode(res.body) : null;

    if (res.statusCode >= 200 && res.statusCode < 300) {
      return (data is Map<String, dynamic>) ? data : {};
    }

    if (data is Map<String, dynamic>) {
      throw Exception(data["detail"] ?? data.toString());
    }
    throw Exception("Request failed: ${res.statusCode}");
  }
}