#HTTP Server Project

This project implements a **HTTP server** in **Python** and **Go** that handles **GET /**, **POST /** requests with **MIME Types** and supports **Persistent** connections over **TCP** on `localhost:8080`.
There is also a HTTPS branch that supports secure connections (self signed certificate) with a TLS socket and a **/stream** endpoint for a simple chunked transfer encoding.

## Running the server
### Python3
```bash
python3 server.py
```
### Go
```bash
cd go/
go run .
```

## Testing
### Prerequisites
We are using curl for our tests, add some files to the **/files** directory and also generate a self signed key using openssl and place **server.crt** & **server.key** in the project directory.
If you want to test the **HTTPS** make sure to add the **--insecure** tag.

### Test GET /
```bash
curl -v http://localhost:8080/
curl -v --insecure https://localhost:8080/
```

### Test POST /halo
```bash
curl -v -X POST -d "halo" http://localhost:8080/
```

### Test GET /files/<filename>
```bash
curl -v http://localhost:8080/files/halo.txt
```

### Test POST /files/<filename>
```bash
curl -v -X POST -d "halo" http://localhost:8080/files/halo.txt
```

### Test GET /stream
```bash
curl -v http://localhost:8080/stream
```

### Test Keep-Alive
```bash
curl -v --http1.1 -H "Connection: keep-alive" http://localhost:8080/ http://localhost:8080/stream
```

### Test Invalid Request (malformed)
```bash
echo -e "GET / HTTP/1.0\r\n\r\n" | nc localhost 8080
echo -e "GET / HTTP/1.0\r\n\r\n" | openssl s_client -connect localhost:8080 -quiet
```

### Test TLS Handshake Faliure
Wrong protocol test
```bash
openssl s_client -connect localhost:8080 -tls1
```

### Test Connection Timeout
Sending nothing and waiting >5 seconds
```bash
nc localhost 8080
openssl s_client -connect localhost:8080 -quiet
```

There are more tests with each endpoint such as directory traversal or missing content-length for POST.
