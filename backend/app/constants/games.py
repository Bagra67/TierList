# --- Timers des parties (services/round_timers.py) -------------------------------------------
# Délais avant chaque nouvel essai d'une transition au timer qui a échoué (base injoignable un
# instant) : sans eux, le tour ou le cooldown ne se terminerait plus tout seul jusqu'au prochain
# redémarrage
TIMER_RETRY_DELAYS_SECONDS: tuple[float, ...] = (1.0, 5.0, 30.0)
