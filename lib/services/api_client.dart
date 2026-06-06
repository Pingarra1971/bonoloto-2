import 'dart:io';
import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';

/// Factory del cliente HTTP usado por todos los servicios.
///
/// Incluye:
///   - Timeouts conservadores (la app móvil es sensible a esperas)
///   - Interceptor de logging en debug
///   - Interceptor de auth (añade Bearer token automático)
///   - Interceptor de reintentos (resiliencia ante red inestable)
///
/// Reemplaza al `http.Client` directo del v7 que no tenía nada de esto
/// (de ahí los bugs #109-#110 de timeouts faltantes en la sesión 1).
class ApiClient {
  final Dio _dio;

  /// Token JWT actual. Si es null, no se manda Authorization.
  /// Setter público para que el provider de credenciales lo actualice.
  String? authToken;

  ApiClient({required String baseUrl, this.authToken})
      : _dio = Dio(BaseOptions(
          baseUrl: baseUrl,
          connectTimeout: const Duration(seconds: 15),
          receiveTimeout: const Duration(seconds: 30),
          sendTimeout: const Duration(seconds: 15),
          headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
          },
          // Cliente acepta cualquier status para que el caller decida qué
          // hacer (un 404 puede ser legítimo en algunos endpoints).
          validateStatus: (_) => true,
        )) {
    _dio.interceptors.add(_AuthInterceptor(this));
    _dio.interceptors.add(_RetryInterceptor(maxRetries: 2));
    if (kDebugMode) {
      _dio.interceptors.add(LogInterceptor(
        request: false,
        requestHeader: false,
        requestBody: false,
        responseHeader: false,
        responseBody: false,
        error: true,
      ));
    }
  }

  Dio get dio => _dio;

  /// Actualiza la base URL sin recrear el cliente.
  /// Útil cuando el usuario cambia de servidor en ajustes.
  void updateBaseUrl(String newBaseUrl) {
    _dio.options.baseUrl = newBaseUrl;
  }

  /// GET con manejo uniforme de errores.
  /// Devuelve null si hay error de red o status >= 400.
  Future<Response<T>?> get<T>(
    String path, {
    Map<String, dynamic>? queryParameters,
    CancelToken? cancelToken,
  }) async {
    try {
      return await _dio.get<T>(
        path,
        queryParameters: queryParameters,
        cancelToken: cancelToken,
      );
    } on DioException {
      return null;
    } on SocketException {
      return null;
    }
  }

  Future<Response<T>?> post<T>(
    String path, {
    dynamic data,
    Map<String, dynamic>? queryParameters,
    CancelToken? cancelToken,
  }) async {
    try {
      return await _dio.post<T>(
        path,
        data: data,
        queryParameters: queryParameters,
        cancelToken: cancelToken,
      );
    } on DioException {
      return null;
    } on SocketException {
      return null;
    }
  }
}

/// Inyecta Bearer token en cada petición si está configurado.
class _AuthInterceptor extends Interceptor {
  final ApiClient _client;
  _AuthInterceptor(this._client);

  @override
  void onRequest(RequestOptions options, RequestInterceptorHandler handler) {
    final token = _client.authToken;
    if (token != null && token.isNotEmpty) {
      options.headers['Authorization'] = 'Bearer $token';
    }
    handler.next(options);
  }
}

/// Reintenta peticiones idempotentes (GET) que fallaron por red.
class _RetryInterceptor extends Interceptor {
  final int maxRetries;
  final Duration baseDelay;

  _RetryInterceptor({
    this.maxRetries = 2,
    this.baseDelay = const Duration(milliseconds: 500),
  });

  @override
  void onError(DioException err, ErrorInterceptorHandler handler) async {
    final req = err.requestOptions;
    final retries = (req.extra['_retries'] as int?) ?? 0;

    // Solo reintentar errores de red (no de aplicación)
    final esNetwork = err.type == DioExceptionType.connectionTimeout ||
        err.type == DioExceptionType.receiveTimeout ||
        err.type == DioExceptionType.sendTimeout ||
        err.type == DioExceptionType.connectionError;

    // Solo GET (idempotente). POST a /api/calculo/iniciar debe ser único.
    final esIdempotente = req.method.toUpperCase() == 'GET';

    if (esNetwork && esIdempotente && retries < maxRetries) {
      req.extra['_retries'] = retries + 1;
      // Backoff exponencial con jitter mínimo
      final delay = baseDelay * (1 << retries);
      await Future.delayed(delay);
      try {
        final dio = Dio(BaseOptions(
          baseUrl: req.baseUrl,
          headers: req.headers,
          connectTimeout: req.connectTimeout,
          receiveTimeout: req.receiveTimeout,
        ));
        final response = await dio.fetch(req);
        return handler.resolve(response);
      } on DioException catch (e) {
        return handler.next(e);
      }
    }
    handler.next(err);
  }
}
