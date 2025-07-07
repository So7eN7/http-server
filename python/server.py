import socket
import threading
import os

HOST="localhost"
PORT=8080


def parse_request(data):
    parts = data.split("\r\n\r\n", 1)
    headers_part = parts[0]
    body = parts[1] if len(parts) > 1 else ""

    lines = headers_part.split("\r\n")
    first_line = lines[0]
    try:
        method, path, _ = first_line.split(" ")
    except ValueError:
        return None, None, {}, ""

    headers = {}
    for line in lines[1:]:
        if ": " in line:
            key, value = line.split(": ", 1)
            headers[key.lower()] = value
    
    return method, path, headers, body

def handle_connection(client_socket):
    try:
        data = client_socket.recv(1024).decode()
        method, path, headers, body = parse_request(data)

        if not method: # Malformed request
            response = (
                "HTTP/1.1 400 Bad Request\r\n"
                "Content-Type: text/plain\r\n"
                "Content-Length: 0\r\n"
                "\r\n"
            )
            client_socket.sendall(response.encode())
            return

        if method == "GET" and path == "/":
            body = "Halo's light"
            response = (
                "HTTP/1.1 200 OK\r\n"
                "Content-Type: text/plain\r\n"
                f"Content-Length: {len(body)}\r\n"
                "\r\n"
                f"{body}"
            )
        elif method == "GET" and path.startswith("/files/"):
            filename = path[len("/files/"):]
            # Preventing directory traversal
            if ".." in filename:
                response = (
                    "HTTP/1.1 400 Bad Request\r\n"
                    "Content-Type: text/plain\r\n"
                    "Content-Length: 0\r\n"
                    "\r\n"
                )
            else:
                file_path = os.path.join("files", filename)
                if os.path.isfile(file_path):
                    with open(file_path, "r") as f:
                        body = f.read()
                    response = (
                        "HTTP/1.1 200 OK\r\n"
                        "Content-Type: text/plain\r\n"
                        f"Content-Length: {len(body)}\r\n"
                        "\r\n"
                        f"{body}"
                    )
                else:
                    response = (
                        "HTTP/1.1 404 Not Found\r\n"
                        "Content-Type: text/plain\r\n"
                        "Content-Length: 0\r\n"
                        "\r\n"
                    )       
        elif method == "POST" and path == "/halo":
            content_length = int(headers.get("content-length", "0"))
            if content_length > 0: 
                # Ensuring we have the full body
                while len(body) < content_length:
                    body += client_socket.recv(1024).decode()
                body = body[:content_length]
            response = (
                "HTTP/1.1 200 OK\r\n"
                "Content-Type: text/plain\r\n"
                f"Content-Length: {len(body)}\r\n"
                "\r\n"
                f"{body}"
            )
        else:
            response = (
                "HTTP/1.1 404 Not Found\r\n"
                "Content-Type: text/plain\r\n"
                "Content-Length: 0\r\n"
                "\r\n"
            )
        client_socket.sendall(response.encode())
    except Exception as e:
        print(f"Error: {e}")
        response = (
            "HTTP/1.1 500 Internal Server Error\r\n"
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


if __name__ == "__main__":
    main()
