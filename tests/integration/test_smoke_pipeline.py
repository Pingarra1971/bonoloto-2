"""
smoke_test_v7.py — Test rápido del backend v7.0

Ejecutar tras instalar el backend para verificar que todas las piezas funcionan:

    cd backend
    source venv/bin/activate
    python smoke_test_v7.py

Si todos los OK pasan, el sistema está listo para producción.
"""

import sys
import random
import traceback


def test_imports():
    """Verifica que todos los módulos cargan correctamente."""
    # Imports críticos (sin estos no funciona nada)
    try:
        import numpy
        import scipy
        import sklearn
    except ImportError as e:
        print(f"  FAIL Imports críticos: {e}")
        return False

    # Imports opcionales (warning si faltan)
    opcionales = []
    try:
        import statsmodels
    except ImportError:
        opcionales.append("statsmodels (warning, algunos algoritmos usan fallback)")

    # Imports del proyecto (deben funcionar)
    try:
        from app.domain.algorithms.block_k import (
            AnalizadorNGRC, AnalizadorDMDKoopman, AnalizadorKAN,
            AnalizadorDLinear, AnalizadorSINDy, AnalizadorTSFresh,
            AnalizadorNHiTS, AnalizadorFITS, AnalizadorTimeMixer,
            AnalizadorModernHopfield, AnalizadorVineCopulas,
            AnalizadorMiniRocket, AnalizadorVisibilityGraph,
            AnalizadorAssociationRules,
            AnalizadorRBM, AnalizadorSOM, AnalizadorHDC,
        )
        from app.domain.algorithms.block_l import (
            SistemaReducido, ConfidenceWeightedBetting, BoteAwareROI,
            AntiPopularityScorer, MultiLoteria, EstrategiaIntegradaBloqueL,
        )
    except ImportError as e:
        print(f"  FAIL Imports del proyecto: {e}")
        traceback.print_exc()
        return False

    msg = "  OK  Imports core + Bloque K (17 clases) + Bloque L (6 clases)"
    if opcionales:
        msg += "\n  WARN paquetes opcionales no disponibles:"
        for o in opcionales:
            msg += f"\n        - {o}"
    print(msg)
    return True


def test_bloque_k():
    """Ejecuta los 17 algoritmos del Bloque K con histórico sintético."""
    random.seed(7)
    hist = [sorted(random.sample(range(1, 50), 6)) for _ in range(200)]

    from app.domain.algorithms.block_k import (
        AnalizadorNGRC, AnalizadorDMDKoopman, AnalizadorKAN,
        AnalizadorDLinear, AnalizadorSINDy, AnalizadorTSFresh,
        AnalizadorNHiTS, AnalizadorFITS, AnalizadorTimeMixer,
        AnalizadorModernHopfield, AnalizadorVineCopulas,
        AnalizadorMiniRocket, AnalizadorVisibilityGraph,
        AnalizadorAssociationRules,
        AnalizadorRBM, AnalizadorSOM, AnalizadorHDC,
    )
    clases = [
        ("94 NGRC", AnalizadorNGRC),
        ("95 DMD/Koopman", AnalizadorDMDKoopman),
        ("96 KAN", AnalizadorKAN),
        ("97 DLinear", AnalizadorDLinear),
        ("98 SINDy", AnalizadorSINDy),
        ("99 TSFresh", AnalizadorTSFresh),
        ("100 N-HiTS", AnalizadorNHiTS),
        ("101 FITS", AnalizadorFITS),
        ("102 TimeMixer", AnalizadorTimeMixer),
        ("103 Modern Hopfield", AnalizadorModernHopfield),
        ("104 Vine Copulas", AnalizadorVineCopulas),
        ("105 MiniRocket", AnalizadorMiniRocket),
        ("106 Visibility Graph", AnalizadorVisibilityGraph),
        ("107 Association Rules", AnalizadorAssociationRules),
        ("108 RBM", AnalizadorRBM),
        ("109 SOM Kohonen", AnalizadorSOM),
        ("110 HDC/VSA", AnalizadorHDC),
    ]
    ok = 0
    for nombre, cls in clases:
        try:
            ana = cls(hist)
            scores = ana.calcular_scores()
            assert isinstance(scores, dict)
            assert len(scores) == 49
            assert all(0 <= v <= 1 for v in scores.values())
            ok += 1
        except Exception as e:
            print(f"  FAIL {nombre}: {e}")
    print(f"  OK  Bloque K: {ok}/17 algoritmos funcionando")
    return ok == 17


def test_bloque_l():
    """Verifica las 5 mejoras del Bloque L."""
    from app.domain.algorithms.block_l import (
        SistemaReducido, BoteAwareROI, AntiPopularityScorer,
        MultiLoteria, ConfidenceWeightedBetting, EstrategiaIntegradaBloqueL,
    )
    # 111. Sistemas reducidos
    sistemas = SistemaReducido.listar_sistemas()
    assert len(sistemas) >= 6
    apuestas = SistemaReducido.aplicar_sistema(
        "9/4", [7, 13, 21, 28, 33, 35, 41, 44, 47]
    )
    assert len(apuestas) == 12
    print("  OK  111 Sistemas reducidos (6 sistemas, 9/4 genera 12 apuestas)")

    # 112. Confidence-weighted betting
    conf = ConfidenceWeightedBetting.medir_confianza_agregada(
        {"a": {n: 0.5 for n in range(1, 50)},
         "b": {n: 0.4 for n in range(1, 50)}},
        25.0, 75.0, 60.0
    )
    assert 0 <= conf["agregada"] <= 100
    print("  OK  112 Confidence-weighted betting")

    # 113. ROI
    roi = BoteAwareROI()
    rec = roi.recomendacion(1_500_000)
    assert rec["decision"] in ["APOSTAR_FUERTE", "APOSTAR_NORMAL",
                                 "APOSTAR_MINIMO", "EVITAR"]
    print(f"  OK  113 ROI calculator (bote 1.5M€ → {rec['decision']})")

    # 114. Anti-popularity
    pop = AntiPopularityScorer.calcular_popularidad([1, 2, 3, 4, 5, 6])
    assert pop["popularidad"] > 0.5  # secuencia, muy popular
    pop2 = AntiPopularityScorer.calcular_popularidad([38, 39, 41, 43, 46, 49])
    assert pop2["popularidad"] < 0.3  # impopular
    print("  OK  114 Anti-popularity (secuencia=popular, altos=impopular)")

    # 115. Multi-lotería
    loterias = MultiLoteria.listar_loterias()
    assert len(loterias) == 4
    assert {l["clave"] for l in loterias} == {"bonoloto", "primitiva",
                                                "euromillones", "gordo"}
    print("  OK  115 Multi-lotería (Bonoloto, Primitiva, Euromillones, Gordo)")

    return True


def test_pipeline():
    """Ejecuta el pipeline v4 completo end-to-end."""
    import asyncio
    random.seed(11)
    hist = [sorted(random.sample(range(1, 50), 6)) for _ in range(150)]
    sorteos = [
        {"numeros": h,
         "complementario": random.randint(1, 49),
         "reintegro": random.randint(0, 9)}
        for h in hist
    ]

    from app.services.pipeline.pipeline_v4 import PipelineV4
    pipeline = PipelineV4(
        historico=hist,
        sorteos_completos=sorteos,
        presupuesto_usuario_eur=10.0,
        bote_acumulado_eur=2_000_000,
        loteria="bonoloto",
    )

    async def run():
        return await pipeline.ejecutar(cantidad=3)

    res = asyncio.run(run())
    print(f"  OK  Pipeline v4 (v7.0) end-to-end:")
    print(f"      Combinaciones base: {len(res.combinaciones)}")
    print(f"      Algoritmos activos: {res.n_algoritmos_activos}")
    print(f"      Confianza máxima:   {res.confianza_maxima:.2f}%")
    print(f"      Iteraciones:        {res.iteraciones}")
    print(f"      Sistema reducido:   {res.bloque_l_sistema_reducido}")
    print(f"      Apuestas Bloque L:  {len(res.bloque_l_apuestas_garantizadas)}")
    print(f"      Coste estrategia:   {res.bloque_l_coste_total_eur:.2f}€")
    print(f"      Tiempo total:       {res.tiempo_total_seg:.0f}s")
    return True


if __name__ == "__main__":
    print("=" * 70)
    print("SMOKE TEST — Bonoloto AI v7.0")
    print("=" * 70)

    tests = [
        ("Imports", test_imports),
        ("Bloque K (17 algoritmos)", test_bloque_k),
        ("Bloque L (5 mejoras)", test_bloque_l),
        ("Pipeline end-to-end", test_pipeline),
    ]

    pasados = 0
    for nombre, fn in tests:
        print(f"\n[{nombre}]")
        try:
            if fn():
                pasados += 1
        except Exception as e:
            print(f"  EXCEPTION: {e}")
            traceback.print_exc()

    print()
    print("=" * 70)
    print(f"RESULTADO: {pasados}/{len(tests)} tests pasaron")
    print("=" * 70)
    sys.exit(0 if pasados == len(tests) else 1)
