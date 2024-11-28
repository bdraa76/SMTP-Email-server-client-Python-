"""\
GLO-2000 Travail pratique 4 - Serveur
Noms et numéros étudiants:
-Bilal Draa
-Olivier Bertrand
-
"""
import hashlib
import hmac
import json
import os
import select
import socket
import sys
import re
import struct

import glosocket
import gloutils


class Server:
    """Serveur mail @glo2000.ca."""

    def __init__(self) -> None:
        """
        Prépare le socket du serveur `_server_socket`
        et le met en mode écoute.

        Prépare les attributs suivants:
        - `_client_socs` une liste des sockets clients.
        - `_logged_users` un dictionnaire associant chaque
            socket client à un nom d'utilisateur.

        S'assure que les dossiers de données du serveur existent.
        """
        self._client_socs = []
        self._logged_users = {}
        localhost = "127.0.0.1"
        try:
            # Création et configuration du socket serveur
            self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._server_socket.bind((localhost, gloutils.APP_PORT))
            self._server_socket.listen()
            print(f"Serveur démarré en mode écoute sur le port {gloutils.APP_PORT}.")
        except (socket.error, glosocket.GLOSocketError) as e:
            print(f"Erreur : Impossible d'initialiser le serveur. {e}")
            sys.exit(1)

        try:
            # Vérification et creation des repertoires
            if not os.path.exists(gloutils.SERVER_DATA_DIR):
                os.makedirs(gloutils.SERVER_DATA_DIR)
            lost_dir_path = os.path.join(gloutils.SERVER_DATA_DIR, gloutils.SERVER_LOST_DIR)
            if not os.path.exists(lost_dir_path):
                os.makedirs(lost_dir_path)
        except glosocket.GLOSocketError as e:
            print(f"Erreur : Impossible d'initialiser les répertoires du serveur. {e}")

    def cleanup(self) -> None:
        """Ferme toutes les connexions résiduelles."""
        for client_soc in self._client_socs:
            client_soc.close()
        self._server_socket.close()

    def _accept_client(self) -> None:
        """Accepte un nouveau client."""
        client_socket, _ = self._server_socket.accept()
        self._client_socs.append(client_socket)

    def _remove_client(self, client_soc: socket.socket) -> None:
        """Retire le client des structures de données et ferme sa connexion."""
        if client_soc in self._client_socs:
            self._client_socs.remove(client_soc)
        client_soc.close()


    def _create_account(self, client_soc: socket.socket,
                        payload: gloutils.AuthPayload
                        ) -> gloutils.GloMessage:
        """
        Crée un compte à partir des données du payload.

        Si les identifiants sont valides, créee le dossier de l'utilisateur,
        associe le socket au nouvel l'utilisateur et retourne un succès,
        sinon retourne un message d'erreur.
        """
        try:
            # Extraction des informations du payload
            username = payload["username"]
            password = payload["password"]
        except KeyError as e:
            raise glosocket.GLOSocketError(
                "payload['username'] ou payload['password'] manquant lors de la création de compte."
            ) from e

            # Vérification du nom d'utilisateur
        if not re.match(r'^[\w\.-]+$', username):
            return gloutils.GloMessage(
                header=gloutils.Headers.ERROR,
                payload=gloutils.ErrorPayload(
                    error_message="Nom d'utilisateur invalide. Utilisez uniquement des caractères alphanumériques tels que '_' , '.' ou '-')"
                )
            )

        try:
            # Vérification de la disponibilité du nom d’utilisateur
            client_folder = os.path.join(gloutils.SERVER_DATA_DIR, username.lower())
            if os.path.exists(client_folder):
                return gloutils.GloMessage(
                    header=gloutils.Headers.ERROR,
                    payload=gloutils.ErrorPayload(
                        error_message="Nom d'utilisateur déjà utilisé."
                    )
                )
        except FileExistsError as e:
            raise glosocket.GLOSocketError(
                "Fichier déjà existant lors de la vérification de la disponibilité du compte."
            ) from e
        except OSError as e:
            raise glosocket.GLOSocketError(
                "Erreur lors de l'accès au répertoire de l'utilisateur pendant la création de compte."
            ) from e

            # Vérification du mot de passe (assez fort ou pas)
        if (
                len(password) < 10
                or not re.search(r'[0-9]', password)
                or not re.search(r'[a-z]', password)
                or not re.search(r'[A-Z]', password)
        ):
            return gloutils.GloMessage(
                header=gloutils.Headers.ERROR,
                payload=gloutils.ErrorPayload(
                error_message="Le mot de passe n'est pas assez sécuritaire, il contenir au moins 10 caractères, "
                                  "un chiffre, une miniscule et une majuscule !"
                )
            )

        try:
            # Création du dossier utilisateur et sauvegarde du mot de passe
            os.makedirs(client_folder, exist_ok=True)
            password_hashed = hashlib.sha3_512(password.encode('utf-8')).hexdigest()
            password_path = os.path.join(client_folder, gloutils.PASSWORD_FILENAME)
            with open(password_path, 'w') as password_file:
                password_file.write(password_hashed)
        except FileExistsError as e:
            raise glosocket.GLOSocketError(
                "Fichier déjà existant."
            ) from e
        except glosocket.GLOSocketError as e:
                print(f"Erreur lors de la création du compte : {e} ")

            # Association du client au nom d'utilisateur
        self._logged_users[client_soc] = username

        return gloutils.GloMessage(header=gloutils.Headers.OK)

    def _login(self, client_soc: socket.socket, payload: gloutils.AuthPayload
               ) -> gloutils.GloMessage:
        """
        Vérifie que les données fournies correspondent à un compte existant.

        Si les identifiants sont valides, associe le socket à l'utilisateur et
        retourne un succès, sinon retourne un message d'erreur.
        """
        try:
            # Extraction des informations du payload
            username = payload["username"]
            password = payload["password"]
        except KeyError as e:
            raise glosocket.GLOSocketError(
                "payload['username'] ou payload['password'] manquant lors de la tentative de connexion."
            ) from e

            # Vérification du nom d'utilisateur
        if not re.match(r'^[\w\.-]+$', username):
            return gloutils.GloMessage(
                header=gloutils.Headers.ERROR,
                payload=gloutils.ErrorPayload(
                error_message="Nom d'utilisateur invalide."
                )
            )

        try:
            # Validation du nom d'utilisateur dans la base de données
            client_folder = os.path.join(gloutils.SERVER_DATA_DIR, username.lower())
            if not os.path.exists(client_folder):
                return gloutils.GloMessage(
                    header=gloutils.Headers.ERROR,
                    payload=gloutils.ErrorPayload(
                    error_message="Nom d'utilisateur ou mot de passe incorrect."
                    )
                )
        except OSError as e:
            raise glosocket.GLOSocketError(
                "Echec d'accès au dossier utilisateur."
            ) from e

        try:
            # Validation du mot de passe de l'utilisateur
            password_file_path = os.path.join(client_folder, gloutils.PASSWORD_FILENAME)
            with open(password_file_path, 'r') as password_file:
                stored_hashed_password = password_file.read().strip()
        except OSError as e:
            raise glosocket.GLOSocketError(
                "Fichier de mot de passe introuvable."
            ) from e

            # Vérification du mot de passe
        received_hashed_password = hashlib.sha3_512(password.encode('utf-8')).hexdigest()
        if not hmac.compare_digest(received_hashed_password, stored_hashed_password):
            return gloutils.GloMessage(
                header=gloutils.Headers.ERROR,
                payload=gloutils.ErrorPayload(
                    error_message="Nom d'utilisateur ou mot de passe incorrect."
                )
            )

        # Association du client à l'utilisateur connecté
        self._logged_users[client_soc] = username

        return gloutils.GloMessage(header=gloutils.Headers.OK)

    def _logout(self, client_soc: socket.socket) -> None:
        """Déconnecte un utilisateur."""
        if client_soc in self._logged_users:
            del self._logged_users[client_soc]
        self._remove_client(client_soc)

    def _get_email_list(self, client_soc: socket.socket
                        ) -> gloutils.GloMessage:
        """
        Récupère la liste des courriels de l'utilisateur associé au socket.
        Les éléments de la liste sont construits à l'aide du gabarit
        SUBJECT_DISPLAY et sont ordonnés du plus récent au plus ancien.

        Une absence de courriel n'est pas une erreur, mais une liste vide.
        """
        #Initialisation dela liste de courriels
        emails = []
        # Vérification de l'authentification de l'utilisateur
        username = self._logged_users.get(client_soc)

        if not username:
            return gloutils.GloMessage(
                header=gloutils.Headers.ERROR,
                payload=gloutils.ErrorPayload(
                error_message="Utilisateur non authentifié."
                )
            )
        try:
            # Récupération du dossier utilisateur
            client_folder = os.path.join(gloutils.SERVER_DATA_DIR, username)
        except OSError as e:
            raise glosocket.GLOSocketError(
                "Erreur lors de l'accès au dossier utilisateur pour la liste des courriels."
            ) from e

        try:
            # Parcours des fichiers JSON (les courriels)
            for email_file in os.listdir(client_folder):
                if not email_file.endswith(".json"):
                    continue
                email_path = os.path.join(client_folder, email_file)
                with open(email_path, 'r', encoding='utf-8') as email:
                    email_data = json.load(email)
                    sender = email_data.get("sender")
                    subject = email_data.get("subject")
                    date = email_data.get("date")
                    emails.append([sender, subject, date])
        except OSError as e:
            raise glosocket.GLOSocketError(
                "Erreur lors de la lecture des fichiers de courriels."
            ) from e

        # Si aucun courriel n'est trouvé
        if not emails:
            return gloutils.GloMessage(
                header=gloutils.Headers.OK,
                payload=gloutils.EmailListPayload(email_list=[])
            )

        # Tri des courriels par date (ordre décroissant)
        emails.sort(reverse=True, key=lambda x: x[2])

        # Formatage des courriels pour la réponse
        email_list = []
        for n, email in enumerate(emails, 1):
            email_list.append(
                gloutils.SUBJECT_DISPLAY.format(
                    number=n,
                    sender=email[0],
                    subject=email[1],
                    date=email[2]
                )
            )

        return gloutils.GloMessage(
            header=gloutils.Headers.OK,
            payload=gloutils.EmailListPayload(email_list=email_list)
        )

    def _get_email(self, client_soc: socket.socket,
                   payload: gloutils.EmailChoicePayload
                   ) -> gloutils.GloMessage:
        """
        Récupère le contenu de l'email dans le dossier de l'utilisateur associé
        au socket.
        """
        try:
            # Extraction du choix de l'utilisateur
            choix = payload["choice"]
        except KeyError as e:
            raise glosocket.GLOSocketError(
                "payload['choice'] manquant lors de la sélection du courriel."
            ) from e

            # Validation du choix
        if not str(choix).isdigit() or choix < 1:
            return gloutils.GloMessage(
                header=gloutils.Headers.ERROR,
                payload=gloutils.ErrorPayload(
                error_message="Choix invalide. Réessayez."
                )
            )

            # Vérification de l'authentification de l'utilisateur
        username = self._logged_users.get(client_soc)
        if not username:
            return gloutils.GloMessage(
                header=gloutils.Headers.ERROR,
                payload=gloutils.ErrorPayload(
                error_message="Utilisateur non authentifié."
                )
            )

        emails = []
        try:
            # Récupération du dossier utilisateur
            client_folder = os.path.join(gloutils.SERVER_DATA_DIR, username)
        except OSError as e:
            raise glosocket.GLOSocketError(
                "Erreur d'accès au dossier utilisateur lors de la sélection d'un courriel."
            ) from e

        try:
            # Lecture des fichiers JSON (les courriels)
            for email_file in os.listdir(client_folder):
                if not email_file.endswith(".json"):
                    continue
                email_path = os.path.join(client_folder, email_file)
                with open(email_path, 'r', encoding='utf-8') as email:
                    email_data = json.load(email)
                    sender = email_data.get("sender")
                    destination = email_data.get("destination")
                    subject = email_data.get("subject")
                    date = email_data.get("date")
                    content = email_data.get("content")
                    emails.append([sender, destination, subject, date, content])
        except OSError as e:
            raise glosocket.GLOSocketError(
                "Erreur lors de la lecture des courriels."
            ) from e

        # Vérification si la boîte de courriels est vide
        if not emails:
            return gloutils.GloMessage(
                header=gloutils.Headers.ERROR,
                payload=gloutils.ErrorPayload(
                error_message="Aucun courriel."
                )
            )

        # Validation de la portée du choix
        if choix < 1 or choix > len(emails):
            return gloutils.GloMessage(
                header=gloutils.Headers.ERROR,
                payload=gloutils.ErrorPayload(
                error_message="Choix de courriel invalide."
                )
            )

        # Tri des courriels par date et sélection du courriel
        emails.sort(reverse=True, key=lambda x: x[3])
        selected_email = emails[choix - 1]

        # Construction du message de réponse avec le courriel
        return gloutils.GloMessage(
            header=gloutils.Headers.OK,
            payload=gloutils.EmailContentPayload(
            sender=selected_email[0],
            destination=selected_email[1],
            subject=selected_email[2],
            date=selected_email[3],
            content=selected_email[4]
            )
        )

    def _get_stats(self, client_soc: socket.socket) -> gloutils.GloMessage:
        """
        Récupère le nombre de courriels et la taille du dossier et des fichiers
        de l'utilisateur associé au socket.
        """
        # Vérification de l'authentification de l'utilisateur
        username = self._logged_users.get(client_soc)
        if not username:
            return gloutils.GloMessage(
                header=gloutils.Headers.ERROR,
                payload=gloutils.ErrorPayload(
                error_message="Utilisateur non authentifié."
                )
            )

        try:
            # Récupération du dossier utilisateur
            client_folder = os.path.join(gloutils.SERVER_DATA_DIR, username)
        except OSError as e:
            raise glosocket.GLOSocketError(
                "Erreur d'accès au dossier utilisateur."
            ) from e

        # Calcul des statistiques
        nb_emails, total_size = 0, 0
        try:
            for file in os.listdir(client_folder):
                if file.endswith(".json"):
                    nb_emails += 1
                    file_path = os.path.join(client_folder, file)
                    total_size += os.path.getsize(file_path)
        except OSError as e:
            raise glosocket.GLOSocketError(
                "Erreur lors de l'accès aux fichiers des courriels."
            ) from e

        # Retour des statistiques au client
        return gloutils.GloMessage(
            header=gloutils.Headers.OK,
            payload=gloutils.StatsPayload(
            count=nb_emails,
            size=total_size
            )
        )

    def _send_email(self, payload: gloutils.EmailContentPayload
                    ) -> gloutils.GloMessage:
        """
        Détermine si l'envoi est interne ou externe et:
        - Si l'envoi est interne, écris le message tel quel dans le dossier
        du destinataire.
        - Si le destinataire n'existe pas, place le message dans le dossier
        SERVER_LOST_DIR et considère l'envoi comme un échec.
        - Si le destinataire est externe, considère l'envoi comme un échec.

        Retourne un messange indiquant le succès ou l'échec de l'opération.
        """
        # Validation de l'adresse email du destinataire
        match = re.match(r'^([^@]+)@(.+)$', payload["destination"])
        if match:
            destination_username = match.group(1)
            destination_domain = match.group(2)
        else:
            return gloutils.GloMessage(
                header=gloutils.Headers.ERROR,
                payload=gloutils.ErrorPayload(
                error_message="Destinataire invalide."
                )
            )

        try:
            # Récupération du dossier du destinataire
            destination_folder = os.path.join(gloutils.SERVER_DATA_DIR, destination_username)
        except OSError as e:
            raise glosocket.GLOSocketError(
                "Erreur lors de l'accès au dossier du destinataire."
            ) from e

        # Générer un nom de fichier sécurisé
        time_file_name = re.sub(r'[<>:"/\\|?*]', '_', payload["date"])

        #Verification du destinaire dans le dossier
        if os.path.exists(destination_folder):
            email_filename = payload["subject"] + "_" + time_file_name + ".json"
            email_path = os.path.join(destination_folder, email_filename)
            try:
                with open(email_path, 'w') as email_file:
                    json.dump(payload, email_file)
            except OSError as e:
                raise glosocket.GLOSocketError(
                    "Erreur lors de l'écriture du fichier de courriel."
                ) from e
            return gloutils.GloMessage(header=gloutils.Headers.OK)

        # Si le domaine est externe a glo2000
        if destination_domain != "glo2000.ca":
            return gloutils.GloMessage(
                header=gloutils.Headers.ERROR,
                payload=gloutils.ErrorPayload(
                    error_message="Destinataire non pris en charge."
                )
            )

        # Si le destinataire est introuvable, déplacer dans le dossier "perdu"
        try:
            lost_email_path = os.path.join(gloutils.SERVER_DATA_DIR, gloutils.SERVER_LOST_DIR)
            os.makedirs(lost_email_path, exist_ok=True)

            lost_email_filename = payload["subject"] + "_" + time_file_name + ".json"
            lost_email_full_path = os.path.join(lost_email_path, lost_email_filename)
            with open(lost_email_full_path, 'w') as lost_email_file:
                json.dump(payload, lost_email_file)
        except OSError as e:
            raise glosocket.GLOSocketError(
                "Erreur lors de la gestion du dossier des courriels perdus."
            ) from e

        return gloutils.GloMessage(
            header=gloutils.Headers.ERROR,
            payload=gloutils.ErrorPayload(
            error_message="Destinataire introuvable, courriel déplacé vers le dossier perdu."
            )
        )

    def run(self):
        """Point d'entrée du serveur."""

        waiters = []
        while True:
            result = select.select(self._client_socs + [self._server_socket], [], [])
            waiters: list[socket.socket] = result[0]

            for waiter in waiters:
                if waiter == self._server_socket:
                    self._accept_client()

                else:
                    try:
                        data = glosocket.recv_mesg(waiter)
                    except glosocket.GLOSocketError:
                        self._client_socs.remove(waiter)
                        waiter.close()
                        continue

                    try:
                        match json.loads(data):
                            case {"header": gloutils.Headers.AUTH_REGISTER, "payload": payload}:
                                message = self._create_account(waiter, payload)
                                glosocket.snd_mesg(waiter, json.dumps(message))

                            case {"header": gloutils.Headers.AUTH_LOGIN, "payload": payload}:
                                message = self._login(waiter, payload)
                                glosocket.snd_mesg(waiter, json.dumps(message))

                            case {"header": gloutils.Headers.BYE, "payload": payload}:
                                self._remove_client(waiter)

                            case {"header": gloutils.Headers.AUTH_LOGOUT, "payload": payload}:
                                self._logout(waiter)

                            case {"header": gloutils.Headers.EMAIL_SENDING, "payload": payload}:
                                message = self._send_email(payload)
                                glosocket.snd_mesg(waiter, json.dumps(message))

                            case {"header": gloutils.Headers.INBOX_READING_REQUEST, "payload": payload}:
                                message = self._get_email_list(waiter)
                                glosocket.snd_mesg(waiter, json.dumps(message))

                            case {"header": gloutils.Headers.INBOX_READING_CHOICE, "payload": payload}:
                                message = self._get_email(waiter, payload)
                                glosocket.snd_mesg(waiter, json.dumps(message))

                            case {"header": gloutils.Headers.STATS_REQUEST, "payload": payload}:
                                message = self._get_stats(waiter)
                                glosocket.snd_mesg(waiter, json.dumps(message))
                    except (socket.error, struct.error) as e:
                        raise glosocket.GLOSocketError("Échec lors de l'envoi de réponse!") from e
                pass


def _main() -> int:
    server = Server()
    try:
        server.run()
    except KeyboardInterrupt:
        server.cleanup()
    return 0


if __name__ == '__main__':
    sys.exit(_main())
