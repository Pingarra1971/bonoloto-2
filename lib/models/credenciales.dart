import 'json_helpers.dart';

/// Credenciales para conectarse a los servicios externos.
///
/// Inmutable. Para modificarlas, usa `copyWith(...)`.
class Credenciales {
  final String loteriasApiKey;
  final String oracleCloudUrl;
  final String oracleCloudToken;
  final String telegramBotToken;
  final String telegramChatId;

  const Credenciales({
    this.loteriasApiKey = '',
    this.oracleCloudUrl = '',
    this.oracleCloudToken = '',
    this.telegramBotToken = '',
    this.telegramChatId = '',
  });

  /// El sistema ya NO necesita un servidor propio: las combinaciones del día
  /// se descargan de una fuente pública (GitHub). Por eso se considera siempre
  /// configurado. La clave de la API de loterías es opcional (respaldo).
  bool get estaConfigurado => true;

  /// True solo si están las credenciales para enviar notificaciones por Telegram.
  bool get telegramConfigurado =>
      telegramBotToken.isNotEmpty && telegramChatId.isNotEmpty;

  Credenciales copyWith({
    String? loteriasApiKey,
    String? oracleCloudUrl,
    String? oracleCloudToken,
    String? telegramBotToken,
    String? telegramChatId,
  }) =>
      Credenciales(
        loteriasApiKey: loteriasApiKey ?? this.loteriasApiKey,
        oracleCloudUrl: oracleCloudUrl ?? this.oracleCloudUrl,
        oracleCloudToken: oracleCloudToken ?? this.oracleCloudToken,
        telegramBotToken: telegramBotToken ?? this.telegramBotToken,
        telegramChatId: telegramChatId ?? this.telegramChatId,
      );

  Map<String, dynamic> toJson() => {
        'loteriasApiKey': loteriasApiKey,
        'oracleCloudUrl': oracleCloudUrl,
        'oracleCloudToken': oracleCloudToken,
        'telegramBotToken': telegramBotToken,
        'telegramChatId': telegramChatId,
      };

  factory Credenciales.fromJson(Map<String, dynamic> json) => Credenciales(
        loteriasApiKey: asString(json['loteriasApiKey']),
        oracleCloudUrl: asString(json['oracleCloudUrl']),
        oracleCloudToken: asString(json['oracleCloudToken']),
        telegramBotToken: asString(json['telegramBotToken']),
        telegramChatId: asString(json['telegramChatId']),
      );

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is Credenciales &&
          other.loteriasApiKey == loteriasApiKey &&
          other.oracleCloudUrl == oracleCloudUrl &&
          other.oracleCloudToken == oracleCloudToken &&
          other.telegramBotToken == telegramBotToken &&
          other.telegramChatId == telegramChatId);

  @override
  int get hashCode => Object.hash(
        loteriasApiKey,
        oracleCloudUrl,
        oracleCloudToken,
        telegramBotToken,
        telegramChatId,
      );
}
