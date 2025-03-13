import requests
from bs4 import BeautifulSoup
import os
import shutil


# Convertit la lettre du livre en son numéro correspondant
def book_str_to_int(book):
    return ord(book) - 64

# Permet de bien formatter le chapitre dans l'url, car le chapitre 5 par exemple est identifié par 05 dans l'url.
def chapter_int_to_str(chapter):
    return f"0{chapter}" if chapter<10 else str(chapter)

def find_latest_version_url(book: str, chapter: int) -> tuple[bool, str]:
    """
    Trouve l'url du fichier pdf correspondant à la dernière version d'un chapitre.

    Fonctionnement : Pour accéder au fichier pdf souhaité, l'utilisateur du site se rend sur la page de présentation et clique
    sur un hyperlien "TELECHARGER". La fonction mimique ce comportement : elle utilise le package requests pour récupérer le
    contenu HTML de la page de présentation du chapitre passé en paramètre, et trouve le lien voulu à l'aide du package BeautifulSoup.

    Renvoie : un couple (success, url)
    """
    book_int = book_str_to_int(book)
    chapter_str = chapter_int_to_str(chapter)
    url = f"https://www.joelsornette.fr/page{book_int}{chapter_str}.html"
    prefix = "ressources/textes/"
    try:
        response = requests.get(url, timeout=10)

        if response.status_code != 200:  # Requête échouée
            return False, response.status_code
            
        soup = BeautifulSoup(response.text, 'html.parser')
        # Trouve tous les tags <a> possédant un attribut href
        links = soup.find_all('a', href=True)
        # Trouve l'url voulu
        urls = [link['href'] for link in links if link['href'].startswith(prefix)]
        return True, "https://www.joelsornette.fr/" + urls[0]

    except requests.exceptions.RequestException as e:
        return False, e

def download_pdf(url: str, file_path: str) -> bool:
    """
    Télécharge un fichier pdf à partir de son url et l'enregistre au chemin spécifié (file_path)

    Renvoie : success
    """
    try:
        response = requests.get(url, timeout=10)

        if response.status_code != 200:  # Requête échouée
            return False
            
        with open(file_path, 'wb') as f:
            f.write(response.content)
        return True
        
    except:
        return False

def find_title(book: str, chapter: int = -1) -> tuple[bool, str]:
    """
    Trouve le titre d'un livre ou d'un chapitre (lorsque ce dernier est précisé en paramètre)

    Renvoie : un couple (success, title)
    """
    book_int = book_str_to_int(book)
    chapter_str = "" if chapter==-1 else chapter_int_to_str(chapter)
    url = f"https://www.joelsornette.fr/page{book_int}{chapter_str}.html"
    try:
        response = requests.get(url)

        if response.status_code != 200:  # Requête échouée
            return False, response.status_code
        
        # Permet de décoder correctement la réponse (apparent_encoding trouve automatiquement l'encodage de la page HTML)
        response.encoding = response.apparent_encoding
        
        # Trouve le titre, qui est contenu dans une balise h1 (il n'y en a qu'une seule sur la page)
        soup = BeautifulSoup(response.text, 'html.parser')
        title = soup.find('h1')

        if title is None:
            return False, book if chapter==-1 else chapter

        return True, title.get_text()

    except requests.exceptions.RequestException as e:
        return False, e


selection_complete = {'A': list(range(1, 11)),
                      'B': list(range(1, 23)),
                      'C': list(range(1, 14)),
                      'D': list(range(1, 13)),
                      'E': list(range(1, 12))}

def download_lessons(selection=None, folder_path=os.getcwd()):
    """
    Télécharge les chapitres spécifiés dans le paramètre selection, et les enregistre suivant
    les livres auxquels ils appartiennent au chemin indiqué par le paramètre folder_path.
    """
    if selection is None:
        selection = selection_complete
    os.makedirs(folder_path, exist_ok=True)
    for book in selection.keys():
        # Récupère le nom du livre
        success_book_title, book_title = find_title(book)
        if not success_book_title:
            print(f"Erreur lors de l'obtention du titre du livre {book}")
        # Evite les caractères spéciaux non supportés par Windows
        book_title = book_title.replace(':', '-').replace(" ?", "").replace("/", ", ")
        book_path = os.path.join(folder_path, book_title)
        
        # Supprime le dossier correspondant au livre actuel s'il existe déjà
        if os.path.exists(book_path):
            shutil.rmtree(book_path)
        # Crée le dossier correspondant au livre actuel
        os.mkdir(book_path)
        
        for chapter in selection[book]:
            # Trouve l'url du fichier pdf correspondant à la dernière version de chapter.
            success_find, url = find_latest_version_url(book, chapter)
            if not success_find:
                print(f"Erreur lors de l'obtention du lien du chapitre {chapter} livre {book}")

            # Récupère le nom du chapitre
            success_chapter_title, chapter_title = find_title(book, chapter)
            if not success_chapter_title:
                print(f"Erreur lors de l'obtention du titre du chapitre {chapter} livre {book}")
            # Dans certains cas, le titre du livre est de la forme "A blabla" au lieu de "A : blabla".
            chapter_title = chapter_title.replace(': ', '')
            chapter_id, chapter_name = chapter_title.split(' ', 1)
            chapter_title = chapter_id + ' - ' + chapter_name[0].upper() + chapter_name[1:]
            chapter_title = chapter_title.replace(" ?", "").replace("/", ", ")
            chapter_path = os.path.join(book_path, f"{chapter_title}.pdf")

            success_download = download_pdf(url, chapter_path)
            if not success_download:
                print(f"Erreur lors du téléchargement du chapitre {chapter} livre {book}")


if __name__ == '__main__':
    if len(os.sys.argv) != 2:
        print("Input the folder_path for the lessons to be downloaded in")
        os.sys.exit()
    
    download_lessons(folder_path=os.sys.argv[1])