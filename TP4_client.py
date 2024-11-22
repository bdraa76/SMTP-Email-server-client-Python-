"""\
GLO-2000 Travail pratique 4 - Client
Noms et numéros étudiants:
-
-
-
"""

import argparse
import getpass
import json
import socket
import sys
import getpass

import glosocket
import gloutils


class Client:
    """Client pour le serveur mail @glo2000.ca."""

    def __init__(self, destination: str) -> None:
        """
        Prépare et connecte le socket du client `_socket`.

        Prépare un attribut `_username` pour stocker le nom d'utilisateur
        courant. Laissé vide quand l'utilisateur n'est pas connecté.
        """
        self._username = ""
        self._socket = None

        try :
            #Création du socket
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

            #Récupération de l'adresse ip et du port à partir de la destination
            host, port = destination.split(":")
            port = int(port)

            #Connecter au serveur
            self._socket.connect((host,port))
            print(f"Connexion au serveur {host}:{port} établie.")
            
        except glosocket.GLOSocketError :
            print(f"La connexion au serveur a échoué : {e}", file=sys.stderr)



    def _register(self) -> None:
        """
        Demande un nom d'utilisateur et un mot de passe et les transmet au
        serveur avec l'entête `AUTH_REGISTER`.

        Si la création du compte s'est effectuée avec succès, l'attribut
        `_username` est mis à jour, sinon l'erreur est affichée.
        """
        try:
            #Récupération des informations 
            username = input("Entrez un nom d'utilisateur.")
            password = getpass.getpass("Entrez votre mot de passe : ")

            message = {
                "header" : "AUTH_REGISTER",
                "payload" : {
                    "username" : username,
                    "password" : password
                }
            }
            #Envoyer le message au serveur
            self._socket.sendall(json.dumps(message).encode('utf-8'))

            #Recevoir la reponse du serveur
            reponse = self._socket.recv(4096)
            reponse = json.loads(reponse.decode('utf-8'))

            #Traitement de la reponse
            if reponse["header"] == "OK":
                print("Création du compte réussie ! Vous pouvez à présent vous connecter.")
                self._username = username
            elif reponse["header"] == "ERROR" :
                error_msg = reponse["payload"].get("error_message", "Erreur inconnue.")
                print(f"Erreur : {error_msg}")

        except (socket.error, json.JSONDecodeError) as e:
            print(f"Erreur de communication avec le serveur : {e}")
        


    def _login(self) -> None:
        """
        Demande un nom d'utilisateur et un mot de passe et les transmet au
        serveur avec l'entête `AUTH_LOGIN`.

        Si la connexion est effectuée avec succès, l'attribut `_username`
        est mis à jour, sinon l'erreur est affichée.
        """
        try:
            #Récupération des informations 
            username = input("Entrez un nom d'utilisateur.")
            password = getpass.getpass("Entrez votre mot de passe : ")

            message = {
                "header" : "AUTH_LOGIN",
                "payload" : {
                    "username" : username,
                    "password" : password
                }
            }
            #Envoyer le message au serveur
            self._socket.sendall(json.dumps(message).encode('utf-8'))

            #Recevoir la reponse du serveur
            reponse = self._socket.recv(4096)
            reponse = json.loads(reponse.decode('utf-8'))

            #Traitement de la reponse
            if reponse["header"] == "OK":
                print(f"Connexion réussie ! Bienvenue {username} !")
                self._username = username
            elif reponse["header"] == "ERROR" :
                error_msg = reponse["payload"].get("error_message", "Erreur inconnue.")
                print(f"Erreur : {error_msg}")

        except (socket.error, json.JSONDecodeError) as e:
            print(f"Erreur de communication avec le serveur : {e}")


            



    def _quit(self) -> None:
        """
        Préviens le serveur de la déconnexion avec l'entête `BYE` et ferme le
        socket du client.
        """
        try :
            #Message de deconnexion
            message ={"header" : "BYE"}

            #Envoyer le message au serveur
            self._socket.sendall(json.dumps(message).encode('utf-8'))
            print("Déconnexion en cours...")

            #Fermeture du socket
            self._socket.close()
            print("Connexion au serveur clôturée.")
        except socket.error as e:
            print(f"Erreur lors de la déconnexion : {e}")
        finally :
            self._socket = None #Libération du socket


    def _read_email(self) -> None:
        """
        Demande au serveur la liste de ses courriels avec l'entête
        `INBOX_READING_REQUEST`.

        Affiche la liste des courriels puis transmet le choix de l'utilisateur
        avec l'entête `INBOX_READING_CHOICE`.

        Affiche le courriel à l'aide du gabarit `EMAIL_DISPLAY`.

        S'il n'y a pas de courriel à lire, l'utilisateur est averti avant de
        retourner au menu principal.
        """

        try :
            #Demande la liste des courriels au serveur
            courriels = 

    def _send_email(self) -> None:
        """
        Demande à l'utilisateur respectivement:
        - l'adresse email du destinataire,
        - le sujet du message,
        - le corps du message.

        La saisie du corps se termine par un point seul sur une ligne.

        Transmet ces informations avec l'entête `EMAIL_SENDING`.
        """

    def _check_stats(self) -> None:
        """
        Demande les statistiques au serveur avec l'entête `STATS_REQUEST`.

        Affiche les statistiques à l'aide du gabarit `STATS_DISPLAY`.
        """

    def _logout(self) -> None:
        """
        Préviens le serveur avec l'entête `AUTH_LOGOUT`.

        Met à jour l'attribut `_username`.
        """

    def run(self) -> None:
        """Point d'entrée du client."""
        should_quit = False

        while not should_quit:
            if not self._username:
                # Authentication menu
                pass
            else:
                # Main menu
                pass


def _main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--destination", action="store",
                        dest="dest", required=True,
                        help="Adresse IP/URL du serveur.")
    args = parser.parse_args(sys.argv[1:])
    client = Client(args.dest)
    client.run()
    return 0


if __name__ == '__main__':
    sys.exit(_main())
