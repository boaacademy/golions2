import os

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
import requests

URL = "https://golions.royalairmaroc.com/"
NTFY_TOPIC = os.environ["NTFY_TOPIC"]

# --- Paramètres du trajet à surveiller ---
DESTINATION_QUERY = "Houston"
DESTINATION_RESULT_TEXT = "George Bush Intercontinental Airport"

# Jours du mois pour départ / retour. Fonctionne tant que le calendrier
# s'ouvre par défaut sur le bon mois (juillet 2026). Si le mois affiché
# par défaut change (le script tourne encore en août par ex.), il faudra
# ajouter un clic sur la flèche "mois précédent/suivant".
DEPARTURE_DAY = "3"
RETURN_DAY = "7"

NO_FLIGHT_TEXT = "Pas de vol disponible"


def notify(title: str, message: str, priority: str = "default") -> None:
    requests.post(
        f"https://ntfy.sh/{NTFY_TOPIC}",
        data=message.encode("utf-8"),
        headers={
            "Title": title.encode("utf-8"),
            "Priority": priority,
            "Click": URL,
        },
        timeout=15,
    )


def run_search() -> str:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(URL, timeout=30000)

        # 1. Choisir la destination
        page.get_by_text("Destination", exact=False).first.click()
        page.get_by_placeholder(
            "Rechercher par ville, aéroport, pays ou code..."
        ).fill(DESTINATION_QUERY)
        page.get_by_text(DESTINATION_RESULT_TEXT, exact=False).first.click()

        # 2. Ouvrir le calendrier et choisir les dates
        page.get_by_text("Départ - Retour", exact=False).first.click()
        page.get_by_text("Choisissez vos dates", exact=False).wait_for(timeout=10000)

        page.get_by_text(DEPARTURE_DAY, exact=True).first.click()
        page.get_by_text(RETURN_DAY, exact=True).first.click()
        page.get_by_text("Confirmer", exact=True).click()

        # 3. Lancer la recherche
        page.get_by_text("Rechercher des vols", exact=True).click()

        # 4. Accepter les mentions légales si la popup apparaît
        try:
            page.get_by_text("J'ai lu et j'accepte", exact=False).click(timeout=8000)
            page.get_by_text("Continuer", exact=True).click(timeout=8000)
        except PWTimeout:
            pass  # popup déjà acceptée ou absente cette fois-ci

        # 5. Attendre la page de résultats et lire le contenu
        page.wait_for_url("**/booking/cart-new/matrix**", timeout=30000)
        page.wait_for_timeout(3000)
        text = page.inner_text("body")

        browser.close()
        return text


def main() -> None:
    text = run_search()

    if NO_FLIGHT_TEXT.lower() in text.lower():
        print("Toujours aucun vol disponible.")
    else:
        notify(
            "🦁 VOLS CASA-HOUSTON DISPONIBLES !",
            f"Le site n'affiche plus 'Pas de vol disponible' pour Casa-Houston. Fonce réserver : {URL}",
            priority="urgent",
        )
        print("ALERTE envoyée : des vols semblent disponibles !")


if __name__ == "__main__":
    main()
