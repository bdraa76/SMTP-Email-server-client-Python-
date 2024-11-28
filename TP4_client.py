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
        #Initialisaition De l'attribut username
        self._username = ""
        try:
                # Création et connexion du socket
                self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                # Connecter au serveur
                self._socket.connect((destination, gloutils.APP_PORT))
                print(f"Connexion au serveur {destination} établie.")
        except glosocket.GLOSocketError as e:
                print(f"Échec de l'initialisation du client : {e}")
                sys.exit(1)

    def _register(self) -> None:
        """
        Demande un nom d'utilisateur et un mot de passe et les transmet au
        serveur avec l'entête `AUTH_REGISTER`.

        Si la création du compte s'est effectuée avec succès, l'attribut
        `_username` est mis à jour, sinon l'erreur est affichée.
        """
        # Récupération des informations
        username = input("Entrez un nom d'utilisateur : ")
        password = getpass.getpass("Entrez votre mot de passe : ")

        try:
            #Creation de la requete et envoi au serveur
            message = gloutils.GloMessage(header=gloutils.Headers.AUTH_REGISTER,
                                        payload=gloutils.AuthPayload(
                                        username=username,
                                        password=password))
            glosocket.snd_mesg(self._socket, json.dumps(message))

            #Reponse du serveur
            reponse = json.loads(glosocket.recv_mesg(self._socket))

            #Traitement de la reponse du serveur
            if reponse["header"] == gloutils.Headers.OK:
                print("Création du compte réussie !")
                self._username = username
            elif reponse["header"] == gloutils.Headers.ERROR :
                print(reponse["payload"]["error_message"])

        except glosocket.GLOSocketError as e:
            print(f"Erreur de communication avec le serveur : {e}")
        


    def _login(self) -> None:
        """
        Demande un nom d'utilisateur et un mot de passe et les transmet au
        serveur avec l'entête `AUTH_LOGIN`.

        Si la connexion est effectuée avec succès, l'attribut `_username`
        est mis à jour, sinon l'erreur est affichée.
        """

        #Récupération des informations
        username = input("Entrez votre nom d'utilisateur : ")
        password = getpass.getpass("Entrez votre mot de passe : ")

        try :
            #Creation et envoi de la requete
            message = gloutils.GloMessage(header=gloutils.Headers.AUTH_LOGIN,
                                        payload=gloutils.AuthPayload(
                                        username=username,
                                        password=password))

            glosocket.snd_mesg(self._socket, json.dumps(message))

            #Trairement de la réponse
            reponse = json.loads(glosocket.recv_mesg(self._socket))

            if reponse["header"] == gloutils.Headers.OK:
                print(f"Connexion réussie. Bienvenue {username} !")
                self._username = username
            elif reponse["header"] == gloutils.Headers.ERROR :
                print(reponse["payload"]["error_message"])

        except glosocket.GLOSocketError as e:
            print(f"Erreur de communication avec le serveur : {e}")


    def _quit(self) -> None:
        """
        Préviens le serveur de la déconnexion avec l'entête `BYE` et ferme le
        socket du client.
        """
        try :
            #Message de deconnexion
            message = gloutils.GloMessage(header=gloutils.Headers.BYE)

            #Envoyer le message au serveur et fermer le socket
            glosocket.snd_mesg(self._socket, json.dumps(message))
            print("Déconnexion réussie.")
            self._socket.close()

        except glosocket.GLOSocketError as e:
            print(f"Échec de la déconnexion du serveur : {e}")

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
            message = gloutils.GloMessage(header=gloutils.Headers.INBOX_READING_REQUEST)
            glosocket.snd_mesg(self._socket, json.dumps(message))
            reponse = json.loads(glosocket.recv_mesg(self._socket))
            # Vérification de la réponse du serveur
            if reponse["header"] != gloutils.Headers.OK:
                print(reponse["payload"].get("error_message", "Erreur inconnue du serveur."))
                return

            # Recuperer la liste des courriels
            email_list = reponse["payload"]["email_list"]
            if not email_list:
                print("Aucun courriel.")
                return

            # Affichage des courriels
            for email in email_list:
                print(email)

            # Demande du choix de l'utilisateur
            while True:
                choice = input("Entrez le numéro du courriel à consulter : ").strip()
                if choice.isdigit() and 1 <= int(choice) <= len(email_list):
                    choice = int(choice)
                    break
                print("Choix invalide.")

            # Envoyer le choix de l'utilisateur au serveur
            email_choice_payload = {"choice": choice}
            message = gloutils.GloMessage(
                header=gloutils.Headers.INBOX_READING_CHOICE,
                payload=email_choice_payload
            )
            glosocket.snd_mesg(self._socket, json.dumps(message))
            reponse = json.loads(glosocket.recv_mesg(self._socket))

            # Verification de la réponse du serveur pour le choix
            if reponse["header"] != gloutils.Headers.OK:
                print(reponse['payload']['error_message'])
                return

            # Affichage du courriel
            email = reponse["payload"]
            print(gloutils.EMAIL_DISPLAY.format(
                sender=email["sender"],
                to=email["destination"],
                subject=email["subject"],
                date=email["date"],
                body=email["content"]
            ))
        except glosocket.GLOSocketError:
            print("Échec de la consultation des courriels.")


    def _send_email(self) -> None:
        """
        Demande à l'utilisateur respectivement:
        - l'adresse email du destinataire,
        - le sujet du message,
        - le corps du message.

        La saisie du corps se termine par un point seul sur une ligne.

        Transmet ces informations avec l'entête `EMAIL_SENDING`.
        """
        #Demande du destinataire et du sujet
        destinataire = input("Entrez l'adresse email du destinataire : ")
        sujet = input("Entrez le sujet du message : ")

        #Entrer le corps du message
        corps = ""
        print("Entrez le contenu du courriel (Terminer la saisie avec un '.' seul sur une ligne) :")
        while (line := input()) != ".":
            corps += line + "\n"
        try :
            #Transmission des informations
            message = gloutils.GloMessage(header=gloutils.Headers.EMAIL_SENDING,
                                        payload=gloutils.EmailContentPayload(
                                        sender=self._username + "@glo2000.ca",
                                        destination=destinataire.lower(),
                                        subject=sujet,
                                        date=gloutils.get_current_utc_time(),
                                        content=corps))
            glosocket.snd_mesg(self._socket, json.dumps(message))

            #Traitement de la reponse
            reponse = json.loads(glosocket.recv_mesg(self._socket))
            if reponse["header"] == gloutils.Headers.OK:
                print("Courriel envoyé avec succès !")
            else:
                print(reponse['payload']['error_message'])
        except(glosocket.GLOSocketError) as e:
            print(f"Échec de l'envoi du courriel : {e}")



    def _check_stats(self) -> None:
        """
        Demande les statistiques au serveur avec l'entête `STATS_REQUEST`.

        Affiche les statistiques à l'aide du gabarit `STATS_DISPLAY`.
        """
        #Préparer la requête pour demander les statistiques
        try :
            message = gloutils.GloMessage(header=gloutils.Headers.STATS_REQUEST)
            glosocket.snd_mesg(self._socket, json.dumps(message))

            #Traitement de la reponse
            reponse = json.loads(glosocket.recv_mesg(self._socket))

            if reponse["header"] == gloutils.Headers.OK:
                stats = reponse["payload"]
                print(gloutils.STATS_DISPLAY.format(
                    count=stats["count"],
                    size=stats["size"]))
            else :
                print(reponse["payload"]["error_message"])
        except(glosocket.GLOSocketError):
            print("Échec de la requête de statistiques au serveur.")

    def _logout(self) -> None:
        """
        Préviens le serveur avec l'entête `AUTH_LOGOUT`.

        Met à jour l'attribut `_username`.
        """
        try:
            #Requete de deconnexion
            message = gloutils.GloMessage(header=gloutils.Headers.AUTH_LOGOUT)
            glosocket.snd_mesg(self._socket, json.dumps(message))
            self._username = ""
            print("Déconnexion au compte réussie!")
        except glosocket.GLOSocketError as e :
            print(f"Échec de la demande de déconnexion au serveur : {e}")


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
