"""
Criterio de Kelly para gestión de bankroll en la Bonoloto.

CONTEXTO HONESTO: el criterio de Kelly clásico maximiza el crecimiento
logarítmico del capital. Para apuestas con EV negativo (como la Bonoloto),
Kelly dice literalmente: apuesta 0. No hay fracción positiva que tenga
sentido cuando la esperanza es negativa.

Entonces, ¿para qué este módulo? Para tres cosas honestas:

  1. **Confirmar la matemática**: calcular la fracción de Kelly y mostrar que
     es <= 0, reforzando que apostar no es óptimo. Transparencia.

  2. **Gestión de límite de gasto**: si el usuario VA a apostar igualmente
     (decisión personal legítima), ayudarle a fijar un tope sensato como
     fracción pequeña del bankroll, de modo que el juego siga siendo
     entretenimiento y no comprometa sus finanzas.

  3. **Comparar sorteos**: cuando hay bote grande, el EV mejora (aunque
     raramente se vuelve positivo). Kelly permite comparar objetivamente
     qué sorteo es "menos malo".

Este módulo NO promete ganancias. Ayuda a perder de forma controlada,
que es lo único matemáticamente honesto que se puede ofrecer a un
apostador de lotería.
"""

from dataclasses import dataclass
from typing import Optional

from app.domain import honestidad_math as hm


@dataclass
class RecomendacionKelly:
    """Recomendación de gestión de bankroll."""
    fraccion_kelly: float          # fracción óptima teórica (suele ser <= 0)
    fraccion_aplicada: float       # fracción que recomendamos (>= 0, acotada)
    apuesta_recomendada_eur: float # cantidad sugerida esta vez
    bankroll_eur: float
    ev_apuesta: float              # EV de una apuesta dado el bote
    es_ev_positivo: bool
    mensaje: str


def fraccion_kelly_teorica(
    prob_ganar: float,
    ratio_payoff: float,
) -> float:
    """
    Fórmula de Kelly: f* = (b·p - q) / b
      donde:
        b = ratio_payoff (cuánto ganas por unidad apostada si ganas)
        p = prob_ganar
        q = 1 - p

    Para la lotería, p es minúscula y b enorme, pero b·p < q casi siempre,
    así que f* sale negativo (= no apuestes).
    """
    if ratio_payoff <= 0:
        return 0.0
    q = 1.0 - prob_ganar
    f = (ratio_payoff * prob_ganar - q) / ratio_payoff
    return f


def recomendar_bankroll(
    bankroll_eur: float,
    bote_eur: float,
    limite_perdida_mensual_eur: Optional[float] = None,
    fraccion_entretenimiento: float = 0.01,
) -> RecomendacionKelly:
    """
    Recomienda cuánto apostar según el bankroll y el bote.

    Args:
        bankroll_eur: capital total disponible para juego.
        bote_eur: bote actual (afecta el EV).
        limite_perdida_mensual_eur: tope que el usuario se autoimpone.
        fraccion_entretenimiento: si el EV es negativo (lo normal),
            recomendamos como mucho esta fracción del bankroll como
            "presupuesto de entretenimiento" (default 1%).

    Returns:
        RecomendacionKelly con la cantidad sugerida y la explicación.
    """
    ev = hm.ev_con_bote(bote_eur)
    ev_unitario = ev.ev_por_apuesta_eur  # por apuesta de 0.50€

    # Kelly teórico usando el desglose del jackpot como aproximación
    # (la apuesta es +EV solo si el bote es enorme).
    # ratio_payoff aproximado: retorno_esperado / coste
    prob_premio = hm.PROB_PREMIO_POR_BOLETO
    ratio = (ev.retorno_esperado_eur / hm.PRECIO_APUESTA_EUR) if hm.PRECIO_APUESTA_EUR else 0
    f_kelly = fraccion_kelly_teorica(prob_premio, ratio)

    if ev_unitario > 0:
        # Caso raro: EV positivo por bote enorme.
        # Aun así, Kelly puro sería brutal en varianza. Aplicamos Kelly
        # fraccional (1/4 de Kelly) y lo acotamos a un máximo prudente.
        f_aplicada = max(0.0, min(f_kelly * 0.25, 0.05))
        apuesta = bankroll_eur * f_aplicada
        mensaje = (
            f"El bote hace el EV teóricamente positivo ({ev.ev_porcentaje*100:.1f}%). "
            f"Aún así, la probabilidad de jackpot es 1 entre "
            f"{hm.TOTAL_COMBINACIONES:,}. Kelly fraccional sugiere un máximo "
            f"prudente de {apuesta:.2f}€."
        )
    else:
        # Caso normal: EV negativo. Kelly dice no apostar.
        # Si el usuario va a jugar igual, recomendamos la fracción de
        # entretenimiento, acotada por su límite mensual.
        f_aplicada = fraccion_entretenimiento
        apuesta = bankroll_eur * f_aplicada
        if limite_perdida_mensual_eur is not None:
            apuesta = min(apuesta, limite_perdida_mensual_eur)
        mensaje = (
            f"El valor esperado es negativo ({ev.ev_porcentaje*100:.1f}%): "
            f"matemáticamente, Kelly dice no apostar. Si juegas por "
            f"entretenimiento, mantén el gasto bajo: máximo "
            f"{apuesta:.2f}€ ({fraccion_entretenimiento*100:.0f}% de tu bankroll)."
        )

    # Redondear la apuesta a múltiplos de 0.50€ (precio de apuesta simple)
    apuesta_redondeada = round(apuesta / hm.PRECIO_APUESTA_EUR) * hm.PRECIO_APUESTA_EUR

    return RecomendacionKelly(
        fraccion_kelly=round(f_kelly, 6),
        fraccion_aplicada=round(f_aplicada, 4),
        apuesta_recomendada_eur=round(apuesta_redondeada, 2),
        bankroll_eur=bankroll_eur,
        ev_apuesta=round(ev_unitario, 4),
        es_ev_positivo=ev_unitario > 0,
        mensaje=mensaje,
    )
