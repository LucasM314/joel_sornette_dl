import os
import shutil
import requests
from bs4 import BeautifulSoup


#### Cours ####

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
        response = requests.get(url, timeout=10)

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
            continue
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
                continue

            # Récupère le nom du chapitre
            success_chapter_title, chapter_title = find_title(book, chapter)
            if not success_chapter_title:
                print(f"Erreur lors de l'obtention du titre du chapitre {chapter} livre {book}")
                continue
            # Dans certains cas, le titre du livre est de la forme "A blabla" au lieu de "A : blabla".
            chapter_title = chapter_title.replace(': ', '')
            chapter_id, chapter_name = chapter_title.split(' ', 1)
            chapter_title = chapter_id + ' - ' + chapter_name[0].upper() + chapter_name[1:]
            chapter_title = chapter_title.replace(" ?", "").replace("/", ", ")
            chapter_path = os.path.join(book_path, f"{chapter_title}.pdf")

            success_download = download_pdf(url, chapter_path)
            if not success_download:
                print(f"Erreur lors du téléchargement du chapitre {chapter} livre {book}")


#### Archives ####

# L'encodage apparent de la page web est ISO-8859-1, mais le texte est en UTF-8.  
# Cette fonction corrige l'encodage.
def fix_encoding(text):
    try:
        return text.encode("latin1").decode("utf-8")
    except UnicodeEncodeError:
        return text  # Si ça échoue, on garde le texte original

# Renvoie la liste des archives d'un thème (principal ou secondaire).
def get_topic_archives(topic_list):
    archives_list = []
    for archive_a in topic_list.find_all("a"):
        archive_name = fix_encoding(archive_a.get_text(strip=True))
        # Mettre la première lettre en majuscule
        formatted_name = archive_name[0].upper() + archive_name[1:]
        archive_url = r"https://www.joelsornette.fr/Archives/" + archive_a["href"]
        archives_list.append((formatted_name, archive_url))
    return archives_list

def find_archives(archive_type='e'):
    """
    Télécharge et extrait la liste des exos/cours archivés.  

    Fonctionnement :
    -------------
    La structure générale des pages d'archive exos/cours est la suivante :
    <ul>
    <li><span><b><i>Thème 1</i></b></span>
        <ul>
        <li><span>Sous-thème 1</span>
            <ul>
                <li><a href="URL">Nom de l'exercice</a>
                <li><a href="URL">Nom de l'exercice</a>
            </ul>
        <li><span>Sous-thème 2</span>
            <ul>
                <li><a href="URL">Nom de l'exercice</a>
                <li><a href="URL">Nom de l'exercice</a>
            </ul>
        </ul>
    
    <li><span>Thème 2</span>
       etc.
    
    La manière la plus simple de récupérer les archives est de parcourir les balises <li> imbriquées les unes dans les autres.
    Toutefois, il semble que BeautifoulSoup ait du mal avec celles-ci car elles ne sont pas fermées.
    Une solution alternative est de récupérer les balises <b> qui ne contiennent que les thèmes principaux,
    puis de trouver les balises <span> qui contiennent les sous-thèmes, et enfin de récupérer les balises 
    <a> qui contiennent les archives, en avançant dans le document à partir des balises <span> grâce à find_next.

    Renvoie :
    ----------
    tuple :
        - (bool) Indique si l'extraction a réussi (True) ou échoué (False).
        - (dict | Exception) Si succès, retourne un dictionnaire structuré contenant les archives.
          En cas d'échec, retourne l'exception rencontrée.

    Structure du dictionnaire retourné :
    ------------------------------------
    {
        "Nom du thème principal": {
            "Nom du sous-thème": [
                ("Nom de l'archive", "URL de l'archive"),
                ...
            ]
        }
    }
    """
    url = f"https://www.joelsornette.fr/Archives/{"ExercicesCorriges" if archive_type=='e' else "Cours"}.html"
    try:
        response = requests.get(url, timeout=10)

        if response.status_code != 200:  # Requête échouée
            print(f"Erreur lors de l'obtention de la page {url}")
            return

        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Dictionnaire pour stocker les archives
        archives = {}

        # Parcourir les thèmes principaux, qui sont les seuls en gras
        for main_topic_b in soup.select("span > b"):
            main_topic = fix_encoding(main_topic_b.get_text(strip=True))
            main_topic_li = main_topic_b.find_next("ul")
            archives[main_topic] = {}
            
            # Parcourir les sous-thèmes, qui sont les seuls spans à l'intérieur des thèmes principaux
            # Si aucun sous-thème n'est trouvé, les archives sont placés dans un sous-thème vide.
            subtopics = main_topic_li.find_all("span")
            if subtopics:
                for subtopic_span in main_topic_li.find_all("span"):
                    subtopic = fix_encoding(subtopic_span.get_text(strip=True))
                    subtopic_li = subtopic_span.find_next("ul")
                    archives[main_topic][subtopic] = get_topic_archives(subtopic_li)
            else:
                if "" not in archives[main_topic].keys():
                    archives[main_topic][""] = []
                archives[main_topic][""] += get_topic_archives(main_topic_li)
        
        return True, archives

    except requests.exceptions.RequestException as e:
        return False, e
    
def download_archives(folder_path=os.getcwd(), archive_type='e'):
    """
    Télécharge et enregistre les archives du type choisi (exercices ou cours).

    Paramètres :
    ------------
    folder_path : str, optionnel
        Chemin du dossier où enregistrer les fichiers. Par défaut, le dossier de travail actuel.
    archive_type : str
        Type d'archives à télécharger. 'e' pour les exercices et 'p' pour les cours.
    """
    success, archives = find_archives(archive_type)
    if not success:
        print(f"Erreur lors de l'obtention du titre {"des exercices" if archive_type=='e' else "du cours"} : {archives}")
        return

    for main_topic, subtopics in archives.items():
        for subtopic, topic_archives in subtopics.items():
            # Créer les dossiers correspondants
            subtopic_path = os.path.join(folder_path, main_topic.capitalize(), subtopic.capitalize())
            os.makedirs(subtopic_path, exist_ok=True)

            for archive_name, archive_url in topic_archives:
                pdf_filename = f"{archive_name}.pdf".replace(":", "-").replace("/", "-").replace("\\", "-").replace("?", "").replace('"', "'")
                pdf_path = os.path.join(subtopic_path, pdf_filename)
                success_download = download_pdf(archive_url, pdf_path)
                if not success_download:
                    print(f"Erreur lors du téléchargement {"de l'exercice" if archive_type=='e' else "du cours"} : {archive_name}")


#### Main ####

def usage_message():
    print("Utilisation : python main.py [c | e | p] dossier_de_destination")
    print("Options :")
    print("  c -> Cours")
    print("  e -> Exercices d'archives de PC")
    print("  p -> Cours d'archives de PC")
    print("\nExemple : python main.py c mon_dossier")

if __name__ == '__main__':
    if len(os.sys.argv) != 3:
        usage_message()
        os.sys.exit()
    
    dl_type = os.sys.argv[1][0].lower()
    if dl_type == 'c':
        download_lessons(folder_path=os.sys.argv[2])
    elif dl_type == 'e':
        download_archives(os.sys.argv[2], 'e')
    elif dl_type == 'p':
        download_archives(os.sys.argv[2], 'p')
    else:
        usage_message()
        os.sys.exit()
