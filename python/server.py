import socket
import threading
import os
import time

HOST="localhost"
PORT=8080


def parse_request(data):
    try:
        parts = data.split("\r\n\r\n", 1)
        headers_part = parts[0]
        body = parts[1] if len(parts) > 1 else ""

        lines = headers_part.split("\r\n")
        first_line = lines[0]
        parts = first_line.split(" ")
        if len(parts) != 3 or parts[2] != "HTTP/1.1":
            return None, None, {}, ""

        method, path = parts[0], parts[1]
        headers = {}
        for line in lines[1:]:
            if ": " in line:
                key, value = line.split(": ", 1)
                headers[key.lower()] = value
        
        return method, path, headers, body
    except Exception:
        return None, None, {}, ""


def handle_connection(client_socket):
    try:
        data = client_socket.recv(1024).decode(errors="ignore")
        method, path, headers, body = parse_request(data)

        if not method: # Malformed request
            print(f"[{time.asctime()}] Malformed request")
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
                print(f"[{time.asctime()}] Directory traversal attempt: {filename}")
                response = (
                    "HTTP/1.1 400 Bad Request\r\n"
                    "Content-Type: text/plain\r\n"
                    "Content-Length: 0\r\n"
                    "\r\n"
                )
            else:
                file_path = os.path.join("files", filename)
                if os.path.isfile(file_path):
                    try:
                        with open(file_path, "r") as f:
                            body = f.read()
                        response = (
                            "HTTP/1.1 200 OK\r\n"
                            "Content-Type: text/plain\r\n"
                            f"Content-Length: {len(body)}\r\n"
                            "\r\n"
                            f"{body}"
                        )
                    except Exception as e:
                        print(f"[{time.asctime()}] File read error: {e}")
                        response = (
                            "HTTP/1.1 500 Internal Server Error\r\n"
                            "Content-Type: text/plain\r\n"
                            "Content-Length: 0\r\n"
                            "\r\n"
                        )
                else:
                    response = (
                        "HTTP/1.1 404 Not Found\r\n"
                        "Content-Type: text/plain\r\n"
                        "Content-Length: 0\r\n"
                        "\r\n"
                    )       
        elif method == "POST" and path == "/halo":
            if "content-length" not in headers:
                print(f"[{time.asctime()}] Missing Content-Length for POST")
                response = (
                    "HTTP/1.1 400 Bad Request\r\n"
                    "Content-Type: text/plain\r\n"
                    "Content-Length: 0\r\n"
                    "\r\n"
                )
            else:
                try:
                    content_length = int(headers["content-length"])
                    if content_length < 0:
                            raise ValueError("Negative Content-Length")
                        # Ensuring we have the full body
                    while len(body) < content_length:
                        chunk = client_socket.recv(1024).decode(errors="ignore")
                        if not chunk:
                            raise ConnectionError("Client disconnected")
                        body += chunk
                    body = body[:content_length]
                    response = (
                        "HTTP/1.1 200 OK\r\n"
                        "Content-Type: text/plain\r\n"
                        f"Content-Length: {len(body)}\r\n"
                        "\r\n"
                        f"{body}"
                    )
                except (ValueError, ConnectionError) as e:
                    print(f"[{time.asctime()}] Invalid POST: {e}")
                    response = (
                        "HTTP/1.1 400 Bad Request\r\n"
                        "Content-Type: text/plain\r\n"
                        "Content-Length: 0\r\n"
                        "\r\n"
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
        print(f"[{time.asctime()}] Server error: {e}")
        try:
            response = (
                "HTTP/1.1 500 Internal Server Error\r\n"
                "Content-Type: text/plain\r\n"
                "Content-Length: 0\r\n"
                "\r\n"
            )
            client_socket.sendall(response.encode())
        except:
            pass
    finally:
        client_socket.close()

def main():
    # Setting up the socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        server_socket.bind((HOST, PORT))
        server_socket.listen()

        print(f"Server running on: {HOST}:{PORT}...")
        while True:
            client_socket, addr = server_socket.accept()
            thread = threading.Thread(target=handle_connection, args=(client_socket,))
            thread.start()
    except Exception as e:
        print(f"[{time.asctime()}] Server setup error: {e}]")
    finally:
        server_socket.close()

if __name__ == "__main__":
    main()
