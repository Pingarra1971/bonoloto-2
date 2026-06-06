import 'dart:async';
import 'dart:convert';
import 'package:http/http.dart' as http;

/// Evento SSE entrante.
/// Tipo es uno de: 'progreso', 'completado', 'error', 'timeout', '' (genérico).
class SseEvent {
  final String type;
  final String data;

  const SseEvent({required this.type, required this.data});

  /// Intenta parsear `data` como JSON. Devuelve `null` si no es JSON.
  Map<String, dynamic>? get dataJson {
    if (data.isEmpty) return null;
    try {
      final decoded = json.decode(data);
      if (decoded is Map<String, dynamic>) return decoded;
      if (decoded is Map) return Map<String, dynamic>.from(decoded);
      return null;
    } catch (_) {
      return null;
    }
  }
}

/// Cliente bare-metal de Server-Sent Events.
///
/// El paquete oficial `dio` no soporta SSE en streaming nativo, así que
/// uso `http` directamente con `Request` + `StreamedResponse` + parseo
/// manual del protocolo.
///
/// Protocolo SSE:
///   - Cada evento se separa por línea en blanco.
///   - Campos: `event: <tipo>`, `data: <payload>`, `id: <id>`, `retry: <ms>`.
///   - Líneas que empiezan por `:` son comentarios (keepalive).
class SseClient {
  final Uri url;
  final Map<String, String> headers;
  http.Client? _client;
  StreamSubscription? _sub;
  bool _cerrado = false;

  SseClient({required this.url, this.headers = const {}});

  /// Abre la conexión y devuelve un stream de eventos.
  /// Cancelar la subscripción al stream cierra la conexión limpiamente.
  Stream<SseEvent> connect() {
    final controller = StreamController<SseEvent>(
      onCancel: () => close(),
    );

    _conectarYParsear(controller);

    return controller.stream;
  }

  Future<void> _conectarYParsear(StreamController<SseEvent> controller) async {
    if (_cerrado) {
      controller.close();
      return;
    }

    _client = http.Client();
    final req = http.Request('GET', url);
    req.headers['Accept'] = 'text/event-stream';
    req.headers['Cache-Control'] = 'no-cache';
    headers.forEach((k, v) => req.headers[k] = v);

    try {
      final streamedResp = await _client!.send(req);
      if (streamedResp.statusCode != 200) {
        controller.addError(
          'SSE: status ${streamedResp.statusCode}',
        );
        await controller.close();
        return;
      }

      // Buffer para acumular líneas y montar eventos
      String currentEvent = '';
      final dataBuffer = StringBuffer();

      _sub = streamedResp.stream
          .transform(utf8.decoder)
          .transform(const LineSplitter())
          .listen(
        (line) {
          // Comentarios (keepalive) y vacías
          if (line.isEmpty) {
            // Línea en blanco = fin de evento → emitir si tenemos data
            if (dataBuffer.isNotEmpty || currentEvent.isNotEmpty) {
              controller.add(SseEvent(
                type: currentEvent,
                data: dataBuffer.toString(),
              ));
            }
            currentEvent = '';
            dataBuffer.clear();
            return;
          }
          if (line.startsWith(':')) {
            // Comentario (incluye ping de keepalive ":ping 1234567890")
            return;
          }
          // Parsear campo
          final idx = line.indexOf(':');
          if (idx == -1) return; // línea malformada
          final field = line.substring(0, idx);
          // Valor puede empezar con un espacio según RFC
          var value = line.substring(idx + 1);
          if (value.startsWith(' ')) value = value.substring(1);

          switch (field) {
            case 'event':
              currentEvent = value;
              break;
            case 'data':
              if (dataBuffer.isNotEmpty) {
                dataBuffer.write('\n');
              }
              dataBuffer.write(value);
              break;
            // 'id' y 'retry' los ignoramos por ahora (no implementamos last-event-id ni reconnect automático)
          }
        },
        onError: (e, st) {
          controller.addError(e, st);
          controller.close();
        },
        onDone: () {
          // Emitir cualquier evento residual
          if (dataBuffer.isNotEmpty) {
            controller.add(SseEvent(
              type: currentEvent,
              data: dataBuffer.toString(),
            ));
          }
          controller.close();
        },
        cancelOnError: false,
      );
    } catch (e, st) {
      controller.addError(e, st);
      await controller.close();
    }
  }

  /// Cierra la conexión SSE. Idempotente.
  Future<void> close() async {
    if (_cerrado) return;
    _cerrado = true;
    await _sub?.cancel();
    _sub = null;
    _client?.close();
    _client = null;
  }
}
