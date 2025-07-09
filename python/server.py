import socket
import threading
import os
import time

HOST="localhost"
PORT=8080

MIME_TYPES = {
    ".txt": "text/plain",
    ".html": "text/html",
    ".css": "text/css",
    ".js": "application/javascript",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".gif": "image/gif",
}

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FILES_DIR = os.path.join(BASE_DIR, "files")

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
    client_socket.settimeout(5.0)
    try:
        while True:
            data = ""
            while "\r\n\r\n" not in data:
                chunk = client_socket.recv(1024).decode(errors="ignore")
                if not chunk:
                    return     
                data += chunk
            
            method, path, headers, body = parse_request(data)
            if not method:
                print(f"[{time.asctime()}] Malformed request")
                response = (
                    "HTTP/1.1 400 Bad Request\r\n"
                    "Content-Type: text/plain\r\n"
                    "Content-Length: 0\r\n"
                    "Connection: close\r\n"
                    "\r\n"
                )
                client_socket.sendall(response.encode())
                return
            
            keep_alive = headers.get("connection", "keep-alive").lower() == "keep-alive"
            connection_header = "Connection: keep-alive\r\n" if keep_alive else "Connection: close\r\n"
            
            if method == "GET" and path == "/":
                body = "Hello, World!"
                response = (
                    "HTTP/1.1 200 OK\r\n"
                    "Content-Type: text/plain\r\n"
                    f"Content-Length: {len(body)}\r\n"
                    f"{connection_header}"
                    "\r\n"
                    f"{body}"
                ).encode()
            elif method == "POST" and path == "/echo":
                if "content-length" not in headers:
                    print(f"[{time.asctime()}] Missing Content-Length for POST")
                    response = (
                        "HTTP/1.1 400 Bad Request\r\n"
                        "Content-Type: text/plain\r\n"
                        "Content-Length: 0\r\n"
                        f"{connection_header}"
                        "\r\n"
                    ).encode()
                else:
                    try:
                        content_length = int(headers["content-length"])
                        if content_length < 0:
                            raise ValueError("Negative Content-Length")
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
                            f"{connection_header}"
                            "\r\n"
                            f"{body}"
                        ).encode()
                    except (ValueError, ConnectionError) as e:
                        print(f"[{time.asctime()}] Invalid POST: {e}")
                        response = (
                            "HTTP/1.1 400 Bad Request\r\n"
                            "Content-Type: text/plain\r\n"
                            "Content-Length: 0\r\n"
                            f"{connection_header}"
                            "\r\n"
                        ).encode()
            elif method == "GET" and path.startswith("/files/"):
                filename = path[len("/files/"):]
                if ".." in filename or not filename:
                    print(f"[{time.asctime()}] Invalid filename: {filename}")
                    response = (
                        "HTTP/1.1 400 Bad Request\r\n"
                        "Content-Type: text/plain\r\n"
                        "Content-Length: 0\r\n"
                        f"{connection_header}"
                        "\r\n"
                    ).encode()
                else:
                    file_path = os.path.join(FILES_DIR, filename)
                    print(f"[{time.asctime()}] Checking file: {file_path}, exists: {os.path.isfile(file_path)}")
                    if os.path.isfile(file_path):
                        try:
                            with open(file_path, "rb") as f:
                                content = f.read()
                            _, ext = os.path.splitext(filename)
                            content_type = MIME_TYPES.get(ext.lower(), "application/octet-stream")
                            response = (
                                b"HTTP/1.1 200 OK\r\n"
                                b"Content-Type: " + content_type.encode() + b"\r\n"
                                b"Content-Length: " + str(len(content)).encode() + b"\r\n"
                                + connection_header.encode()
                                + b"\r\n"
                                + content
                            )
                        except Exception as e:
                            print(f"[{time.asctime()}] File read error: {e}")
                            response = (
                                "HTTP/1.1 500 Internal Server Error\r\n"
                                "Content-Type: text/plain\r\n"
                                "Content-Length: 0\r\n"
                                f"{connection_header}"
                                "\r\n"
                            ).encode()
                    else:
                        print(f"[{time.asctime()}] File not found: {file_path}")
                        response = (
                            "HTTP/1.1 404 Not Found\r\n"
                            "Content-Type: text/plain\r\n"
                            "Content-Length: 0\r\n"
                            f"{connection_header}"
                            "\r\n"
                        ).encode()
            elif method == "POST" and path.startswith("/files/"):
                filename = path[len("/files/"):]
                if ".." in filename or not filename:
                    print(f"[{time.asctime()}] Invalid filename: {filename}")
                    response = (
                        "HTTP/1.1 400 Bad Request\r\n"
                        "Content-Type: text/plain\r\n"
                        "Content-Length: 0\r\n"
                        f"{connection_header}"
                        "\r\n"
                    ).encode()
                elif "content-length" not in headers:
                    print(f"[{time.asctime()}] Missing Content-Length for POST")
                    response = (
                        "HTTP/1.1 400 Bad Request\r\n"
                        "Content-Type: text/plain\r\n"
                        "Content-Length: 0\r\n"
                        f"{connection_header}"
                        "\r\n"
                    ).encode()
                else:
                    try:
                        content_length = int(headers["content-length"])
                        if content_length < 0:
                            raise ValueError("Negative Content-Length")
                        body_bytes = body.encode()   
                        while len(body_bytes) < content_length:
                            chunk = client_socket.recv(1024)
                            if not chunk:
                                raise ConnectionError("Client disconnected")
                            body_bytes += chunk
                        body_bytes = body_bytes[:content_length]
                        os.makedirs(FILES_DIR, exist_ok=True)
                        file_path = os.path.join(FILES_DIR, filename)
                        with open(file_path, "wb") as f:
                            f.write(body_bytes)
                        response = (
                            "HTTP/1.1 201 Created\r\n"
                            "Content-Type: text/plain\r\n"
                            "Content-Length: 0\r\n"
                            f"{connection_header}"
                            "\r\n"
                        ).encode()
                    except (ValueError, ConnectionError, OSError) as e:
                        print(f"[{time.asctime()}] File write error: {e}")
                        response = (
                            "HTTP/1.1 500 Internal Server Error\r\n"
                            "Content-Type: text/plain\r\n"
                            "Content-Length: 0\r\n"
                            f"{connection_header}"
                            "\r\n"
                        ).encode()
            else:
                response = (
                    "HTTP/1.1 404 Not Found\r\n"
                    "Content-Type: text/plain\r\n"
                    "Content-Length: 0\r\n"
                    f"{connection_header}"
                    "\r\n"
                ).encode()
            
            client_socket.sendall(response)
            
            if not keep_alive:
                return
    except socket.timeout:
        print(f"[{time.asctime()}] Connection timed out")
    except Exception as e:
        print(f"[{time.asctime()}] Server error: {e}")
        try:
            response = (
                "HTTP/1.1 500 Internal Server Error\r\n"
                "Content-Type: text/plain\r\n"
                "Content-Length: 0\r\n"
                "Connection: close\r\n"
                "\r\n"
            ).encode()
            client_socket.sendall(response)
        except:
            pass
    finally:
        client_socket.close()

def main():
    print(f"[{time.asctime()}] Current working directory: {os.getcwd()}")
    print(f"[{time.asctime()}] Files directory: {FILES_DIR}")
    
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        server_socket.bind((HOST, PORT))
        server_socket.listen(1)
        
        print(f"Server running on {HOST}:{PORT}...")
        while True:
            client_socket, addr = server_socket.accept()
            thread = threading.Thread(target=handle_connection, args=(client_socket,))
            thread.start()
    except Exception as e:
        print(f"[{time.asctime()}] Server setup error: {e}")
    finally:
        server_socket.close()

if __name__ == "__main__":
    main()
