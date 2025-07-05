import socket

HOST="localhost"
PORT=8080

def main():
    # Setting up the socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((HOST, PORT))
    server_socket.listen()

    client_socket, addr = server_socket.accept()
    client_socket.recv(1024)

    body = "Halo's light"
    response = (
        "HTTP/1.1 200 OK\r\n"
        "Content-Type: text/plain\r\n"
        f"Content-Length: {len(body)}\r\n"
        "\r\n"
        f"{body}"
    )

    client_socket.sendall(response.encode()) 

    client_socket.close()
    server_socket.close()

if __name__ == "__main__":
    main()
