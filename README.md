# Email Server and Client System

This project is a part of the **GLO-2000 Networks for Engineers course** and focuses on developing a robust internal email system for the fictional domain `@glo2000.ca.` It consolidates knowledge of socket programming, data transmission using a shared protocol, and handling multiple clients simultaneously.

The system includes:

### Server:
Acts as an SMTP relay for internal and external email processing, handling account creation, authentication, email storage, and retrieval.
### Client: 
Enables users to create accounts, log in, send emails, view their inbox, and retrieve statistics.
Key Features:
### Account Management:
Create and authenticate user accounts with secure password hashing.
### Email Management:
Send, receive, and consult emails, with chronological sorting and detailed views.
### Statistics: 
Retrieve user statistics, including the number of messages and total storage size.
### Protocol Compliance:
Implements the provided glosocket and gloutils modules for standardized communication.
### Technologies Used:
Python (socket, hashlib, hmac, json, pathlib, os)
### Custom modules:
glosocket for communication, gloutils for templates and utilities.
This project adheres to IPv4 and TCP standards and is designed to work within a controlled testing environment.

## Usage

Open the directory where TP4_client and TP4_server are found and launch terminal
1. Run the server with the command **python TP4_server.py**
2. Run the client menu with the command **python TP4_client.py -d 127.0.0.1**
3. Ready to use !
