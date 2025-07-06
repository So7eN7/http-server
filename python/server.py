import socket
import threading

HOST="localhost"
PORT=8080

def handle_connection(client_socket):
    try:
        data = client_socket.recv(1024).decode()

        first_line = data.split("\r\n")[0]
        try:
            method, path, _ = first_line.split(" ")
        except ValueError:
            method, path = "", ""

        if method == "GET" and path == "/":   
            body = "Halo's light"
            response = (
                "HTTP/1.1 200 OK\r\n"
                "Content-Type: text/plain\r\n"
                f"Content-Length: {len(body)}\r\n"
                "\r\n"
                f"{body}"
            )
        else:
            body = ""
            response = (
                "HTTP/1.1 404 Not Found\r\n"
                "Content-Type: text/plain\r\n"
                "Content-Length: 0\r\n"
                "\r\n"
            )
        client_socket.sendall(response.encode()) 
    finally:
        client_socket.close()


def main():
    # Setting up the socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((HOST, PORT))
    server_socket.listen()

    print(f"Server running on: {HOST}:{PORT}...")
    while True:
        client_socket, addr = server_socket.accept()
        thread = threading.Thread(target=handle_connection, args=(client_socket,))
        thread.start()

    server_socket.close()

if __name__ == "__main__":
    main()
