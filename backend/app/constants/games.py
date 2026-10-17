# --- Timers des parties (services/round_timers.py) -------------------------------------------
# Délais avant chaque nouvel essai d'une transition au timer qui a échoué (base injoignable un
# instant) : sans eux, le tour ou le cooldown ne se terminerait plus tout seul jusqu'au prochain
# redémarrage
TIMER_RETRY_DELAYS_SECONDS: tuple[float, ...] = (1.0, 5.0, 30.0)

# --- Lien des résultats d'une partie close (US-5.3) -----------------------------------------
# Octets aléatoires du jeton (secrets.token_urlsafe : 22 caractères, 128 bits), impossible à
# deviner : le lien est la seule protection des résultats
PUBLIC_RESULTS_TOKEN_BYTES = 16
# Longueur de la colonne : les jetons posés par la migration (32 caractères hexadécimaux) y
# tiennent aussi
PUBLIC_RESULTS_TOKEN_MAX_LENGTH = 32
