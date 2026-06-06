// Helpers de parseo seguro de JSON.
//
// Centralizan las conversiones que en v7 estaban dispersas y eran fuente
// de bugs (cuando el backend devuelve un int donde el modelo espera double,
// o un null donde espera un string vacío, los `as double` revientan).

/// Convierte un valor cualquiera a `double` con tolerancia:
/// - num → double
/// - String parseable → double
/// - null o no parseable → fallback (default 0.0)
double asDouble(dynamic v, [double fallback = 0.0]) {
  if (v == null) return fallback;
  if (v is num) return v.toDouble();
  if (v is String) {
    final parsed = double.tryParse(v);
    return parsed ?? fallback;
  }
  return fallback;
}

/// Convierte a `int` con tolerancia (acepta double con parte decimal,
/// String parseable, etc.).
int asInt(dynamic v, [int fallback = 0]) {
  if (v == null) return fallback;
  if (v is int) return v;
  if (v is num) return v.toInt();
  if (v is String) {
    final parsed = int.tryParse(v);
    if (parsed != null) return parsed;
    final fromDouble = double.tryParse(v);
    if (fromDouble != null) return fromDouble.toInt();
    return fallback;
  }
  return fallback;
}

/// String con fallback a cadena vacía si null.
String asString(dynamic v, [String fallback = '']) {
  if (v == null) return fallback;
  if (v is String) return v;
  return v.toString();
}

/// Bool tolerante: acepta bool real, "true"/"false", 1/0.
bool asBool(dynamic v, [bool fallback = false]) {
  if (v == null) return fallback;
  if (v is bool) return v;
  if (v is num) return v != 0;
  if (v is String) {
    final lower = v.toLowerCase();
    if (lower == 'true' || lower == '1') return true;
    if (lower == 'false' || lower == '0') return false;
  }
  return fallback;
}

/// Lista de int desde dynamic (acepta List<int>, List<dynamic> con mix).
List<int> asIntList(dynamic v) {
  if (v == null) return const [];
  if (v is List) {
    return v.map((e) => asInt(e)).toList();
  }
  return const [];
}

/// Lista de double desde dynamic.
List<double> asDoubleList(dynamic v) {
  if (v == null) return const [];
  if (v is List) {
    return v.map((e) => asDouble(e)).toList();
  }
  return const [];
}

/// Map<String, double> desde dynamic.
Map<String, double> asStringDoubleMap(dynamic v) {
  if (v == null) return const {};
  if (v is Map) {
    return v.map((k, val) => MapEntry(k.toString(), asDouble(val)));
  }
  return const {};
}

/// Map<String, String> desde dynamic.
Map<String, String> asStringStringMap(dynamic v) {
  if (v == null) return const {};
  if (v is Map) {
    return v.map((k, val) => MapEntry(k.toString(), asString(val)));
  }
  return const {};
}

/// DateTime tolerante: acepta ISO 8601, epoch ms (int), o null.
DateTime? asDateTime(dynamic v) {
  if (v == null) return null;
  if (v is DateTime) return v;
  if (v is String) {
    try {
      return DateTime.parse(v);
    } catch (_) {
      return null;
    }
  }
  if (v is num) {
    return DateTime.fromMillisecondsSinceEpoch(v.toInt());
  }
  return null;
}
