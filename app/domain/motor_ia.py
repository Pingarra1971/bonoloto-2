"""
Motor IA — 11 algoritmos en 5 capas.

Extracción quirúrgica del MotorIA original de main.py para romper el
acoplamiento circular pipeline_v4 → main → MotorIA. Ahora MotorIA es
un módulo de dominio puro, sin dependencias de FastAPI, JWT o BD.

Esto permite:
  - Importar MotorIA en cualquier servicio sin levantar la API
  - Tests unitarios sin fastapi/pydantic/jwt instalados
  - Reutilizar el motor en otros contextos (CLI, batch, notebook)
"""

import math
import random
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

import numpy as np


class MotorIA:
    """
    Motor principal con 11 algoritmos en 5 capas.
    Ejecuta convergencia automática hasta alcanzar el máximo posible.
    """

    NOMBRES_ALGORITMOS = [
        "entropia", "hot_cold_bias", "covarianza",
        "lstm", "transformer", "markov",
        "bayesiano", "xgboost", "reinforcement_learning",
        "monte_carlo", "algoritmo_genetico",
    ]

    def __init__(self, sorteos: List[dict]):
        self.sorteos = sorteos
        self.historico = [s["numeros"] for s in sorteos]
        self.n = len(self.historico)
        # Pesos iniciales iguales
        self.pesos = {alg: 1.0 / len(self.NOMBRES_ALGORITMOS)
                      for alg in self.NOMBRES_ALGORITMOS}

    # ─── CAPA 1: ANÁLISIS ESTADÍSTICO ───────────────────────────

    def capa1_entropia(self) -> Dict[int, float]:
        """Mide desviación de entropía esperada por número"""
        frecuencias = defaultdict(int)
        for sorteo in self.historico:
            for n in sorteo:
                frecuencias[n] += 1

        total = sum(frecuencias.values())
        esperada = total / 49
        scores = {}
        for n in range(1, 50):
            freq = frecuencias.get(n, 0)
            # Desviación normalizada respecto a la media esperada
            desviacion = abs(freq - esperada) / max(esperada, 1)
            # Números más cercanos a la esperada tienen mayor score
            scores[n] = max(0.0, 1.0 - desviacion)
        return scores

    def capa1_hot_cold_bias(self) -> Dict[int, float]:
        """Califica números según tendencia hot/cold en múltiples ventanas"""
        ventanas = [50, 100, 500, self.n]
        pesos_ventanas = [0.4, 0.3, 0.2, 0.1]
        scores = {n: 0.0 for n in range(1, 50)}

        for ventana, peso in zip(ventanas, pesos_ventanas):
            subset = self.historico[:min(ventana, self.n)]
            if not subset:
                continue
            frecuencias = defaultdict(int)
            for sorteo in subset:
                for num in sorteo:
                    frecuencias[num] += 1
            total = sum(frecuencias.values())
            if total == 0:
                continue
            esperada = total / 49
            if esperada <= 0:
                continue
            for n in range(1, 50):
                freq = frecuencias.get(n, 0)
                # Favorecemos números fríos que están "a punto de salir"
                if freq < esperada * 0.85:
                    score = 0.7 + (0.3 * (1 - freq / esperada))
                elif freq > esperada * 1.15:
                    score = 0.5  # Calientes: neutro
                else:
                    score = 0.6  # Neutros
                scores[n] += score * peso
        return scores

    def capa1_covarianza(self) -> Dict[int, float]:
        """Análisis de co-ocurrencia entre números"""
        if self.n == 0:
            return {n: 0.0 for n in range(1, 50)}
        coocurrencias = defaultdict(int)
        apariciones = defaultdict(int)

        for sorteo in self.historico:
            for n in sorteo:
                apariciones[n] += 1
            for i in range(len(sorteo)):
                for j in range(i + 1, len(sorteo)):
                    par = (min(sorteo[i], sorteo[j]), max(sorteo[i], sorteo[j]))
                    coocurrencias[par] += 1

        scores = {n: 0.0 for n in range(1, 50)}
        for (n1, n2), count in coocurrencias.items():
            # Chi-cuadrado simplificado para detectar pares significativos
            esperado = (apariciones[n1] / self.n) * (apariciones[n2] / self.n) * self.n
            if esperado > 0:
                chi2 = (count - esperado) ** 2 / esperado
                if chi2 > 3.84:  # p < 0.05
                    scores[n1] += chi2 * 0.1
                    scores[n2] += chi2 * 0.1

        # Normalizar
        max_score = max(scores.values(), default=1)
        if max_score > 0:
            scores = {n: v / max_score for n, v in scores.items()}
        return scores

    # ─── CAPA 2: SERIES TEMPORALES ──────────────────────────────

    def capa2_lstm_simple(self) -> Dict[int, float]:
        """
        LSTM simplificado: ventana deslizante con pesos exponenciales.
        El LSTM completo se ejecuta en el entorno ML de Oracle Cloud.
        """
        scores = {n: 0.0 for n in range(1, 50)}
        ventana = min(30, self.n)
        recientes = self.historico[:ventana]

        for i, sorteo in enumerate(recientes):
            peso_temporal = math.exp(-i * 0.1)  # Decaimiento exponencial
            for n in sorteo:
                scores[n] += peso_temporal

        # Normalizar
        max_v = max(scores.values(), default=1)
        if max_v > 0:
            scores = {n: v / max_v for n, v in scores.items()}
        return scores

    def capa2_transformer_attention(self) -> Dict[int, float]:
        """
        Self-Attention simplificado: pondera sorteos históricos
        según su similitud con los más recientes.
        """
        scores = {n: 0.0 for n in range(1, 50)}
        if self.n < 2:
            return scores

        # Query: último sorteo
        query = set(self.historico[0])
        # Keys: todos los sorteos históricos
        atenciones = []
        for sorteo in self.historico[1:]:
            # Similitud de Jaccard como proxy de atención
            interseccion = len(query.intersection(set(sorteo)))
            union = len(query.union(set(sorteo)))
            similitud = interseccion / union if union > 0 else 0
            atenciones.append((sorteo, similitud))

        # Softmax sobre atenciones
        sims = [a[1] for a in atenciones]
        exp_sims = [math.exp(s) for s in sims]
        suma_exp = sum(exp_sims) + 1e-8
        pesos_atencion = [e / suma_exp for e in exp_sims]

        for (sorteo, _), peso in zip(atenciones, pesos_atencion):
            for n in sorteo:
                scores[n] += peso

        max_v = max(scores.values(), default=1)
        if max_v > 0:
            scores = {n: v / max_v for n, v in scores.items()}
        return scores

    def capa2_markov(self) -> Dict[int, float]:
        """Cadenas de Markov: probabilidades de transición entre sorteos"""
        scores = {n: 0.0 for n in range(1, 50)}
        if self.n < 2:
            return scores

        # Construir matriz de transición simplificada
        transiciones = defaultdict(lambda: defaultdict(int))
        for i in range(len(self.historico) - 1):
            sorteo_actual = self.historico[i]
            sorteo_siguiente = self.historico[i + 1]
            for n_actual in sorteo_actual:
                for n_siguiente in sorteo_siguiente:
                    transiciones[n_actual][n_siguiente] += 1

        # Probabilidad de transición desde el último sorteo
        ultimo = self.historico[0]
        for n_actual in ultimo:
            if n_actual in transiciones:
                total = sum(transiciones[n_actual].values())
                if total > 0:
                    for n_sig, count in transiciones[n_actual].items():
                        scores[n_sig] += count / total

        max_v = max(scores.values(), default=1)
        if max_v > 0:
            scores = {n: v / max_v for n, v in scores.items()}
        return scores

    # ─── CAPA 3: APRENDIZAJE ────────────────────────────────────

    def capa3_bayesiano(self) -> Dict[int, float]:
        """
        Bayesiano: Prior uniforme actualizado con likelihood del histórico
        P(num | historico) ∝ P(historico | num) * P(num)
        """
        # Prior: distribución uniforme (cada número igual de probable)
        prior = {n: 1.0 / 49 for n in range(1, 50)}

        # Likelihood: frecuencia observada
        frecuencias = defaultdict(int)
        total_apariciones = 0
        for sorteo in self.historico:
            for n in sorteo:
                frecuencias[n] += 1
                total_apariciones += 1

        # Posterior (Bayes con suavizado de Laplace)
        posterior = {}
        for n in range(1, 50):
            likelihood = (frecuencias.get(n, 0) + 1) / (total_apariciones + 49)
            posterior[n] = likelihood * prior[n]

        # Normalizar
        suma = sum(posterior.values())
        if suma > 0:
            return {n: v / suma for n, v in posterior.items()}
        return {n: 1.0 / 49 for n in range(1, 50)}

    def capa3_xgboost_simple(self) -> Dict[int, float]:
        """
        XGBoost simplificado: gradient boosting sobre características
        de cada número (frecuencia, última aparición, distribución par/impar)
        """
        scores = {}
        frecuencias = defaultdict(int)
        ultima_aparicion = {}

        # historico está ordenado: índice 0 = más reciente, índice n-1 = más antiguo
        # (es como lo provee BaseDatos.obtener_sorteos con ORDER BY fecha DESC)
        for i, sorteo in enumerate(self.historico):
            for n in sorteo:
                frecuencias[n] += 1
                # Guardar la PRIMERA vez que aparece desde el sorteo más reciente,
                # que es la última aparición real
                if n not in ultima_aparicion:
                    ultima_aparicion[n] = i

        for n in range(1, 50):
            # Feature 1: Frecuencia relativa
            freq_rel = frecuencias.get(n, 0) / max(self.n * 6, 1)

            # Feature 2: "Sequía" — cuántos sorteos sin aparecer (desde el último)
            # Si nunca apareció, máxima sequía
            sequia = ultima_aparicion.get(n, self.n) / max(self.n, 1)

            # Feature 3: Posición en el rango (1-49)
            posicion = (n - 1) / 48

            # Feature 4: Par o impar
            par_impar = 1 if n % 2 == 0 else 0

            # Árbol de decisión simplificado (boosting manual)
            score = 0.0
            # Árbol 1: favorece frecuencia media
            score += 0.3 * (1 - abs(freq_rel - (6 / 49)) * 10)
            # Árbol 2: favorece números con sequía media
            score += 0.3 * min(sequia * 2, 1.0)
            # Árbol 3: distribución por rangos
            score += 0.2 * (1 - abs(posicion - 0.5))
            # Árbol 4: balance par/impar
            score += 0.2 * 0.5  # Peso neutral

            scores[n] = max(0.0, score)

        max_v = max(scores.values(), default=1)
        if max_v > 0:
            scores = {n: v / max_v for n, v in scores.items()}
        return scores

    def capa3_reinforcement_learning(
        self, historial_predicciones: Optional[List[dict]] = None
    ) -> Dict[int, float]:
        """
        Q-Learning simplificado: el agente aprende qué números
        tienen mayor "recompensa" histórica en predicciones pasadas.
        """
        q_table = {n: 0.5 for n in range(1, 50)}  # Q inicial neutro
        learning_rate = 0.1
        gamma = 0.9  # Factor de descuento

        if historial_predicciones:
            for pred in historial_predicciones:
                numeros = pred.get("numeros", [])
                aciertos = pred.get("aciertos", 0)
                recompensa = aciertos / 6.0  # Normalizar a [0, 1]
                # Pre-calcular max para esta iteración (más eficiente y semánticamente correcto)
                max_q = max(q_table.values())
                for n in numeros:
                    if n in q_table:
                        # Q(s,a) = Q(s,a) + lr * (r + γ*max_Q - Q(s,a))
                        q_table[n] = q_table[n] + learning_rate * (
                            recompensa + gamma * max_q - q_table[n]
                        )
        else:
            # Sin historial: usar frecuencia histórica como proxy de recompensa
            for sorteo in self.historico[:100]:
                max_q = max(q_table.values())
                for n in sorteo:
                    q_table[n] = q_table[n] + learning_rate * (
                        1.0 + gamma * max_q - q_table[n]
                    )

        max_v = max(q_table.values(), default=1)
        if max_v > 0:
            q_table = {n: v / max_v for n, v in q_table.items()}
        return q_table

    # ─── CAPA 4: OPTIMIZACIÓN ───────────────────────────────────

    def capa4_monte_carlo(self, iteraciones: int = 100000) -> Dict[int, float]:
        """Simulación Monte Carlo: frecuencia esperada en N simulaciones"""
        conteos = defaultdict(int)
        frecuencias_historicas = defaultdict(int)
        for sorteo in self.historico:
            for n in sorteo:
                frecuencias_historicas[n] += 1

        total_hist = sum(frecuencias_historicas.values())
        # Suavizado de Laplace: garantiza que todos los números tengan p > 0
        # (de lo contrario np.random.choice(replace=False) fallaría si <6 tienen p>0)
        probabilidades = [
            (frecuencias_historicas.get(n, 0) + 1) / max(total_hist + 49, 50)
            for n in range(1, 50)
        ]

        # Normalizar para evitar errores de floating point en np.random.choice
        suma_probs = sum(probabilidades)
        if suma_probs > 0:
            probabilidades = [p / suma_probs for p in probabilidades]
        else:
            probabilidades = [1 / 49] * 49

        numeros = list(range(1, 50))
        try:
            for _ in range(iteraciones):
                seleccionados = np.random.choice(
                    numeros, size=6, replace=False, p=probabilidades
                )
                for n in seleccionados:
                    conteos[n] += 1
        except ValueError as e:
            # Fallback si probs no suman exactamente 1.0
            logger.warning(f"Monte Carlo fallback uniforme: {e}")
            for _ in range(iteraciones):
                seleccionados = np.random.choice(numeros, size=6, replace=False)
                for n in seleccionados:
                    conteos[n] += 1

        total = sum(conteos.values())
        return {n: conteos.get(n, 0) / max(total, 1) for n in range(1, 50)}

    def capa4_algoritmo_genetico(
        self, cantidad: int, scores_base: Dict[int, float]
    ) -> List[List[int]]:
        """
        Algoritmo Genético: evoluciona combinaciones usando función de aptitud.
        Devuelve las mejores combinaciones convergidas.
        """
        POBLACION = 200
        GENERACIONES = 100
        TASA_MUTACION = 0.1
        ELITE = 20

        def funcion_aptitud(combo: List[int]) -> float:
            score = sum(scores_base.get(n, 0) for n in combo)
            # Penalizar combinaciones con números muy seguidos
            nums_sorted = sorted(combo)
            consecutivos = sum(
                1 for i in range(len(nums_sorted) - 1)
                if nums_sorted[i + 1] - nums_sorted[i] == 1
            )
            score -= consecutivos * 0.05
            # Bonificar distribución par/impar equilibrada
            pares = sum(1 for n in combo if n % 2 == 0)
            equilibrio = 1 - abs(pares - 3) / 3
            score += equilibrio * 0.1
            # Bonificar suma en rango óptimo (96-204, centrado en 150). Bug #166.
            suma = sum(combo)
            if 96 <= suma <= 204:
                score += 0.15
            return score

        # Inicializar población
        poblacion = []
        for _ in range(POBLACION):
            # Asegurar pesos positivos y suma > 0
            pesos = [max(scores_base.get(n, 0.01), 1e-6) for n in range(1, 50)]
            suma_pesos = sum(pesos)
            if suma_pesos > 0:
                probs = [p / suma_pesos for p in pesos]
            else:
                probs = [1.0 / 49] * 49
            individuo = sorted(
                np.random.choice(range(1, 50), size=6, replace=False, p=probs).tolist()
            )
            poblacion.append(individuo)

        mejor_aptitud_anterior = -1

        for generacion in range(GENERACIONES):
            # Evaluar aptitud
            aptitudes = [(combo, funcion_aptitud(combo)) for combo in poblacion]
            aptitudes.sort(key=lambda x: x[1], reverse=True)

            mejor_actual = aptitudes[0][1]
            # Criterio de convergencia
            if abs(mejor_actual - mejor_aptitud_anterior) < 0.0001 and generacion > 20:
                break
            mejor_aptitud_anterior = mejor_actual

            # Selección elitista
            elite = [combo for combo, _ in aptitudes[:ELITE]]
            nueva_poblacion = elite.copy()

            # Cruce y mutación
            while len(nueva_poblacion) < POBLACION:
                padre1 = random.choice(elite)
                padre2 = random.choice(elite)

                # Cruce: combinar genes de ambos padres
                genes_pool = list(set(padre1 + padre2))
                if len(genes_pool) >= 6:
                    hijo = sorted(random.sample(genes_pool, 6))
                else:
                    hijo = sorted(padre1)

                # Mutación: reemplazar un número aleatoriamente
                if random.random() < TASA_MUTACION:
                    idx_mutacion = random.randint(0, 5)
                    nuevo_num = random.randint(1, 49)
                    hijo_mutado = hijo.copy()
                    hijo_mutado[idx_mutacion] = nuevo_num
                    hijo_mutado = sorted(list(set(hijo_mutado)))
                    if len(hijo_mutado) == 6:
                        hijo = hijo_mutado

                nueva_poblacion.append(hijo)

            poblacion = nueva_poblacion[:POBLACION]

        # Devolver las mejores 'cantidad' combinaciones únicas
        aptitudes_final = [(combo, funcion_aptitud(combo)) for combo in poblacion]
        aptitudes_final.sort(key=lambda x: x[1], reverse=True)

        vistas = set()
        resultado = []
        for combo, _ in aptitudes_final:
            clave = tuple(combo)
            if clave not in vistas:
                vistas.add(clave)
                resultado.append(combo)
            if len(resultado) >= cantidad:
                break

        return resultado

    # ─── CAPA 5: META-MODELO DE CONSENSO ────────────────────────

    def meta_modelo_consenso(
        self,
        scores_por_algoritmo: Dict[str, Dict[int, float]],
    ) -> Dict[int, float]:
        """
        Combina los scores de los 11 algoritmos ponderados por sus pesos dinámicos.
        """
        scores_finales = {n: 0.0 for n in range(1, 50)}

        for algoritmo, scores in scores_por_algoritmo.items():
            peso = self.pesos.get(algoritmo, 1.0 / len(self.NOMBRES_ALGORITMOS))
            for n, score in scores.items():
                # Filtrar keys fuera de rango [1, 49] defensivamente
                if isinstance(n, int) and 1 <= n <= 49:
                    scores_finales[n] += score * peso

        # Normalizar
        max_v = max(scores_finales.values(), default=1)
        if max_v > 0:
            scores_finales = {n: v / max_v for n, v in scores_finales.items()}

        return scores_finales

    def calcular_indice_confianza(
        self, combinacion: List[int], scores_consenso: Dict[int, float]
    ) -> float:
        """Calcula el índice de confianza de una combinación (0-100)"""
        score = sum(scores_consenso.get(n, 0) for n in combinacion) / 6
        # Bonificaciones adicionales
        nums_sorted = sorted(combinacion)
        # Distribución par/impar equilibrada
        pares = sum(1 for n in combinacion if n % 2 == 0)
        bonus_paridad = (1 - abs(pares - 3) / 3) * 5
        # Suma en rango óptimo. Bug #166: el rango anterior (75-175) estaba
        # descentrado (centro 125) frente a la suma media real de Bonoloto
        # (150 = 6 * 25). Ahora usamos el rango central donde cae ~el 90% de
        # las combinaciones reales (percentil 5-95 ≈ 96-204), centrado en 150.
        suma = sum(combinacion)
        bonus_suma = 5 if 96 <= suma <= 204 else 0
        # Cobertura de rangos (1-9, 10-19, 20-29, 30-39, 40-49)
        rangos = set()
        for n in combinacion:
            rangos.add((n - 1) // 10)
        bonus_cobertura = len(rangos) * 1.5

        confianza = score * 80 + bonus_paridad + bonus_suma + bonus_cobertura
        return min(99.9, max(1.0, confianza))

    def actualizar_pesos(self, predicciones_con_aciertos: List[dict]):
        """
        Actualiza los pesos de cada algoritmo según su rendimiento histórico.
        Los algoritmos que más acertaron aumentan su peso.
        """
        if not predicciones_con_aciertos:
            return

        nuevos_pesos = dict(self.pesos)

        for pred in predicciones_con_aciertos:
            aciertos = pred.get("aciertos", 0)
            # Bug #165: el pipeline emite 'pesos_por_algoritmo' (ver #131);
            # aceptamos ambas claves por robustez retro-compatible.
            pesos_alg = (
                pred.get("pesos_por_algoritmo")
                or pred.get("pesos_algoritmos")
                or {}
            )
            recompensa = aciertos / 6.0

            for alg, peso_contrib in pesos_alg.items():
                if alg in nuevos_pesos:
                    # Actualizar: algoritmos que contribuyeron a buenos resultados ganan peso
                    nuevos_pesos[alg] += 0.01 * recompensa * peso_contrib

        # Normalizar pesos
        suma = sum(nuevos_pesos.values())
        if suma > 0:
            self.pesos = {k: v / suma for k, v in nuevos_pesos.items()}


