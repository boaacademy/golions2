import os

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
import requests

URL = "https://golions.royalairmaroc.com/"
NTFY_TOPIC = os.environ["NTFY_TOPIC"]

# --- Paramètres du trajet à surveiller ---
DESTINATION_QUERY = "Houston"
DESTINATION_RESULT_TEXT = "George Bush Intercontinental Airport"

DEPARTURE_DAY = "3"
RETURN_DAY = "7"

NO_FLIGHT_TEXT = "Pas de vol disponible"

DEBUG_DIR = "debug_screenshots"


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


def shot(page, name: str) -> None:
    os.makedirs(DEBUG_DIR, exist_ok=True)
    path = os.path.join(DEBUG_DIR, f"{name}.png")
    try:
        page.screenshot(path=path, full_page=True, timeout=10000)
        print(f"Capture sauvegardée : {path}")
    except Exception as e:
        print(f"Impossible de capturer {name}: {e}")


def dismiss_cookies_if_present(page) -> None:
    # Bannière de cookies possible au premier chargement
    for text in ["Accepter", "Tout accepter", "J'accepte", "Accept"]:
        try:
            btn = page.get_by_text(text, exact=False).first
            if btn.is_visible(timeout=3000):
                btn.click(timeout=3000)
                print(f"Bannière cookies fermée via '{text}'")
                return
        except Exception:
            continue


def run_search() -> str:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        page.goto(URL, timeout=30000)
        page.wait_for_timeout(2000)
        shot(page, "01_page_chargee")

        dismiss_cookies_if_present(page)
        shot(page, "02_apres_cookies")

        # 1. Choisir la destination
        page.get_by_text("Destination", exact=False).first.click()
        shot(page, "03_apres_clic_destination")

        page.get_by_placeholder(
            "Rechercher par ville, aéroport, pays ou code..."
        ).fill(DESTINATION_QUERY)
        shot(page, "04_apres_saisie_houston")

        page.get_by_text(DESTINATION_RESULT_TEXT, exact=False).first.click()
        shot(page, "05_apres_selection_houston")

        # 2. Ouvrir le calendrier et choisir les dates
        # On sauvegarde le HTML pour debug en cas de nouveau blocage
        try:
            with open(os.path.join(DEBUG_DIR, "page_avant_dates.html"), "w", encoding="utf-8") as f:
                f.write(page.content())
        except Exception as e:
            print(f"Impossible de sauvegarder le HTML: {e}")

        page.get_by_placeholder("Départ - Retour").click(timeout=15000)
        shot(page, "06_apres_clic_dates")

        page.get_by_text("Choisissez vos dates", exact=False).wait_for(timeout=10000)
        shot(page, "07_calendrier_ouvert")

        page.get_by_text(DEPARTURE_DAY, exact=True).first.click()
        shot(page, "08_apres_clic_depart")

        page.get_by_text(RETURN_DAY, exact=True).first.click()
        shot(page, "09_apres_clic_retour")

        page.get_by_text("Confirmer", exact=True).click()
        shot(page, "10_apres_confirmer")

        # 3. Lancer la recherche
        page.get_by_text("Rechercher des vols", exact=True).click()
        shot(page, "11_apres_clic_rechercher")

        # 4. Accepter les mentions légales si la popup apparaît
        try:
            page.get_by_text("J'ai lu et j'accepte", exact=False).click(timeout=8000)
            page.get_by_text("Continuer", exact=True).click(timeout=8000)
            shot(page, "12_apres_mentions_legales")
        except PWTimeout:
            shot(page, "12_pas_de_mentions_legales")

        # 5. Attendre la page de résultats et lire le contenu
        page.wait_for_url("**/booking/cart-new/matrix**", timeout=30000)
        page.wait_for_timeout(3000)
        shot(page, "13_page_resultats")
        text = page.inner_text("body")

        browser.close()
        return text


def main() -> None:
    try:
        text = run_search()
    except Exception as e:
        print(f"ERREUR pendant la recherche : {e}")
        raise

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
