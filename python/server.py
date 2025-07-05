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
    data = client_socket.recv(1024)
    client_socket.sendall(data) 

    client_socket.close()
    server_socket.close()

if __name__ == "__main__":
    main()
