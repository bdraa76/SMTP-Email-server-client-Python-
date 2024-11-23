"""\
GLO-2000 Travail pratique 4 - Client
Noms et numéros étudiants:
- Bilal Draa
- Olivier Bertrand
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

        try:
                # Création et connexion du socket
                self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                # Récupération de l'adresse ip et du port à partir de la destination
                host, port = destination.split(":")
                # Connecter au serveur
                self._socket.connect((host, int(port)))
                print(f"Connexion au serveur {host}:{port} établie.")
        except (socket.error, glosocket.GLOSocketError) as e:
                print(f"La connexion au serveur a échoué : {e}", file=sys.stderr)
                sys.exit(1)

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
            return
        


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
            response = self._socket.recv(4096)
            response = json.loads(response.decode('utf-8'))

            #Traitement de la reponse
            if response["header"] == "OK":
                print(f"Connexion réussie ! Bienvenue {username} !")
                self._username = username
            elif response["header"] == "ERROR" :
                error_msg = response["payload"].get("error_message", "Erreur inconnue.")
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

        try:
            # Demander et afficher la liste des courriels
            response = json.loads(self._socket.recv(4096).decode())
            email_list = response.get("payload", {}).get("email_list", [])
            if not email_list:
                print("Aucun courriel disponible.")
                return

            print("Liste des courriels :")
            for i, email_summary in enumerate(email_list, start=1):
                print(f"{i}. {email_summary}")

            # Validation du choix de l'utilisateur
            choice = int(input("Entrez le numéro du courriel à lire : "))
            if choice < 1 or choice > len(email_list):
                print("Choix invalide.")
                return

            # Envoyer le choix et afficher le courriel
            choice_request = {"header": "INBOX_READING_CHOICE", "payload": {"choice": choice}}
            glosocket.snd_mesg(self._socket, json.dumps(choice_request))
            email_response = json.loads(glosocket.recv_mesg(self._socket))

            if "payload" not in email_response:
                print("Erreur : courriel non récupéré.")
                return

            print(gloutils.EMAIL_DISPLAY.format(
                sender=email_response["payload"]["sender"],
                to=email_response["payload"]["destination"],
                subject=email_response["payload"]["subject"],
                date=email_response["payload"]["date"],
                body=email_response["payload"]["content"]
            ))
        except Exception as e:
            print(f"Erreur lors de la lecture des courriels : {e}")


    def _send_email(self) -> None:
        """
        Demande à l'utilisateur respectivement:
        - l'adresse email du destinataire,
        - le sujet du message,
        - le corps du message.

        La saisie du corps se termine par un point seul sur une ligne.

        Transmet ces informations avec l'entête `EMAIL_SENDING`.
        """
        try:
            destinataire = input("Entrez l'adresse email du destinataire : ")
            sujet = input("Entrez le sujet du message : ")
            print("Entrez le corps du message (tapez '.' sur une seule ligne pour terminer) :")

            corps = ""
            while True:
                ligne = input()
                if ligne == ".":
                    break
                corps += ligne + "\n"

            message = {
                "header": "EMAIL_SENDING",
                "payload": {
                    "destination": destinataire,
                    "subject": sujet,
                    "content": corps
                }
            }
            glosocket.snd_mesg(self._socket, json.dumps(message))
            print("Message envoyé avec succès.")
        except Exception as e:
            print(f"Erreur lors de l'envoi du courriel : {e}")

    def _check_stats(self) -> None:
        """
        Demande les statistiques au serveur avec l'entête `STATS_REQUEST`.

        Affiche les statistiques à l'aide du gabarit `STATS_DISPLAY`.
        """

        try:
            # Préparer la requête pour demander les statistiques
            stats_request = {
                "header": "STATS_REQUEST"
            }

            # Envoyer la requête au serveur
            self._socket.sendall(json.dumps(stats_request).encode("utf-8"))

            # Recevoir la réponse du serveur
            response = json.loads(self._socket.recv(4096).decode("utf-8"))

            # Vérifier que la réponse contient les données nécessaires
            if "payload" not in response or not isinstance(response["payload"], dict):
                print("Erreur : réponse invalide du serveur.")
                return

            payload = response["payload"]

            # Afficher les statistiques à l'aide du gabarit STATS_DISPLAY
            print(gloutils.STATS_DISPLAY.format(
                count=payload.get("count", "N/A"),
                size=payload.get("size", "N/A")
            ))
        except (socket.error, json.JSONDecodeError) as e:
            print(f"Erreur de communication avec le serveur : {e}")
        except Exception as e:
            print(f"Une erreur inattendue est survenue : {e}")


    def _logout(self) -> None:
        """
        Préviens le serveur avec l'entête `AUTH_LOGOUT`.

        Met à jour l'attribut `_username`.
        """
        try:
            # Préparer le message de déconnexion
            logout_request = {
                "header": "AUTH_LOGOUT"
            }

            # Envoyer le message au serveur
            self._socket.sendall(json.dumps(logout_request).encode("utf-8"))
            print("Déconnexion réussie. Vous êtes maintenant déconnecté.")

            # Réinitialiser le nom d'utilisateur
            self._username = ""

        except (socket.error, json.JSONDecodeError) as e:
            print(f"Erreur lors de la déconnexion : {e}")
        except Exception as e:
            print(f"Une erreur inattendue est survenue : {e}")


    def run(self) -> None:
        """Point d'entrée du client."""
        should_quit = False

        while not should_quit:
            if not self._username:
                # Menu de connexion
                print(gloutils.CLIENT_AUTH_CHOICE)
                choice = input("Entrez votre choix : ")

                if choice == "1":
                    # Créer un compte
                    self._register()
                elif choice == "2":
                    # Se connecter
                    self._login()
                elif choice == "3":
                    # Quitter
                    self._quit()
                    should_quit = True
                else:
                    print("Choix invalide, veuillez réessayer.")
            else:
                # Menu principal
                print(gloutils.CLIENT_USE_CHOICE)
                choice = input("Entrez votre choix : ")

                if choice == "1":
                    # Consulter un courriel
                    self._read_email()
                elif choice == "2":
                    # Envoyer un courriel
                    self._send_email()
                elif choice == "3":
                    # Consulter les statistiques
                    self._check_stats()
                elif choice == "4":
                    # Se déconnecter
                    self._logout()
                else:
                    print("Choix invalide, veuillez réessayer.")


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
