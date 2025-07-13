package main

import (
	"fmt"
  "io/ioutil"
	"log"
	"net"
	"os"
	"path/filepath"
	"strconv"
	"strings"
  "time"
)

const ADDR = "localhost:8080"

var mimeTypes = map[string]string{
    ".txt":  "text/plain",
    ".html": "text/html",
    ".css":  "text/css",
    ".js":   "application/javascript",
    ".png":  "image/png",
    ".jpg":  "image/jpeg",
    ".gif":  "image/gif",
}

/*
Parsing an HTTP request into method, path, headers and body.
*/
func parseRequest(data string) (string, string, map[string]string, string) {
  parts := strings.SplitN(data, "\r\n\r\n", 2)
  headersPart := parts[0]
  body := ""
  if len(parts) > 1 {
    body = parts[1]
  }

  // Request line
  lines := strings.Split(headersPart, "\r\n")
  firstLine := lines[0]
  parts = strings.SplitN(firstLine, " ", 3)
  if len(parts) != 3 || parts[2] != "HTTP/1.1" {
    return "", "", nil, ""
  }
  method, path := parts[0], parts[1]

  headers := make(map[string]string)
  for _, line := range lines[1:] {
    if strings.Contains(line, ": ") {
      headerParts := strings.SplitN(line, ": ", 2)
      headers[strings.ToLower(headerParts[0])] = headerParts[1]
    }
  }

  return method, path, headers, body
}

/*
Handling client connections, multiple requests via keep-alive
*/
func handleConnection(conn net.Conn) {
  defer conn.Close()
    conn.SetReadDeadline(time.Now().Add(5 * time.Second))

    for { // Buffer request data until a full request is received
        buffer := make([]byte, 1024)
        data := ""
        for !strings.Contains(data, "\r\n\r\n") {
            n, err := conn.Read(buffer)
            if err != nil {
                if err, ok := err.(net.Error); ok && err.Timeout() {
                    log.Printf("[%s] Connection timed out", time.Now().Format(time.RFC1123))
                } else if err != nil {
                    log.Printf("[%s] Error reading: %v", time.Now().Format(time.RFC1123), err)
                }
                return
            }
            data += string(buffer[:n])
        }

        method, path, headers, body := parseRequest(data)
        if method == "" {
            log.Printf("[%s] Malformed request", time.Now().Format(time.RFC1123))
            response := "HTTP/1.1 400 Bad Request\r\n" +
                "Content-Type: text/plain\r\n" +
                "Content-Length: 0\r\n" +
                "Connection: close\r\n" +
                "\r\n"
            conn.Write([]byte(response))
            return
        }

        // Checking if the client wants to keep the connection alive
        keepAlive := headers["connection"] == "keep-alive" || headers["connection"] == ""
        connectionHeader := "Connection: keep-alive\r\n"
        if !keepAlive {
            connectionHeader = "Connection: close\r\n"
        }

        var response string
        // Handle GET /
        if method == "GET" && path == "/" {
            body := "Halo's light"
            response = fmt.Sprintf(
                "HTTP/1.1 200 OK\r\n"+
                    "Content-Type: text/plain\r\n"+
                    "Content-Length: %d\r\n"+
                    "%s"+
                    "\r\n"+
                    "%s",
                len(body), connectionHeader, body,
            )
           // Handle GET /files/filename
        }  else if method == "GET" && strings.HasPrefix(path, "/files/") {
            filename := path[len("/files/"):]
            if strings.Contains(filename, "..") {
                log.Printf("[%s] Directory traversal attempt: %s", time.Now().Format(time.RFC1123), filename)
                response = fmt.Sprintf(
                    "HTTP/1.1 400 Bad Request\r\n"+
                        "Content-Type: text/plain\r\n"+
                        "Content-Length: 0\r\n"+
                        "%s"+
                        "\r\n",
                    connectionHeader,
                )
            } else {
                filePath := filepath.Join("files", filename)
                if _, err := os.Stat(filePath); err == nil {
                    content, err := ioutil.ReadFile(filePath)
                    if err != nil {
                        log.Printf("[%s] Error reading file: %v", time.Now().Format(time.RFC1123), err)
                        response = fmt.Sprintf(
                            "HTTP/1.1 500 Internal Server Error\r\n"+
                                "Content-Type: text/plain\r\n" +
                                "Content-Length: 0\r\n"+
                                "%s"+
                                "\r\n",
                            connectionHeader,
                        )
                    } else {
                        // Get MIME type
                        ext := filepath.Ext(filename)
                        contentType := mimeTypes[ext]
                        if contentType == "" {
                            contentType = "application/octet-stream"
                        }
                        response = fmt.Sprintf(
                            "HTTP/1.1 200 OK\r\n"+
                                "Content-Type: %s\r\n"+
                                "Content-Length: %d\r\n"+
                                "%s"+
                                "\r\n",
                            contentType, len(content), connectionHeader,
                        )
                        // Reading in binary to support non-text files
                        responseBytes := []byte(response)
                        responseBytes = append(responseBytes, content...)
                        response = string(responseBytes)
                    }
                } else {
                    response = fmt.Sprintf(
                        "HTTP/1.1 404 Not Found\r\n"+
                            "Content-Type: text/plain\r\n"+
                            "Content-Length: 0\r\n"+
                            "%s"+
                            "\r\n",
                        connectionHeader,
                    )
                }
            }
          // Handle GET /stream (sending 1 up to 10 in strings as chunked response)
        } else if method == "GET" && path == "/stream" {
            headersResponse := fmt.Sprintf(
                "HTTP/1.1 200 OK\r\n"+
                    "Content-Type: text/plain\r\n"+
                    "Transfer-Encoding: chunked\r\n"+
                    "%s"+
                    "\r\n",
                connectionHeader,
            )
            if _, err := conn.Write([]byte(headersResponse)); err != nil {
                log.Printf("[%s] Error writing headers: %v", time.Now().Format(time.RFC1123), err)
                return
            }
            
            for i := 1; i <= 10; i++ {
              chunkData := fmt.Sprintf("%d", i) 
              // Chunk format: <size in hex>\r\n<data>\r\n
              chunk := fmt.Sprintf("%x\r\n%s\r\n", len(chunkData), chunkData)
              if _, err := conn.Write([]byte(chunk)); err != nil {
                    log.Printf("[%s] Error writing chunk %d: %v", time.Now().Format(time.RFC1123), i, err)
                    return
              }
              time.Sleep(1 * time.Second)
            }
            // Final chunk
            if _, err := conn.Write([]byte("0\r\n\r\n")); err != nil {
                log.Printf("[%s] Error writing final chunk: %v", time.Now().Format(time.RFC1123), err)
                return
            }
          // Handle POST /files/filename
        } else if method == "POST" && strings.HasPrefix(path, "/files/") {
            filename := path[len("/files"):]
            if strings.Contains(filename, "..") || filename == "" {
                log.Printf("[%s] Invalid filename: %s", time.Now().Format(time.RFC1123), filename)
                response = fmt.Sprintf(
                    "HTTP/1.1 400 Bad Request\r\n"+
                        "Content-Type: text/plain\r\n"+
                        "Content-Length: 0\r\n"+
                        "%s"+
                        "\r\n",
                    connectionHeader,
                    )   
              // content-length for POST
            } else if _, ok := headers ["content-length"]; !ok{
                log.Printf("[%s] Missing Content-Length for POST", time.Now().Format(time.RFC1123))
                response = fmt.Sprintf(
                    "HTTP/1.1 400 Bad Request\r\n"+
                        "Content-Type: text/plain\r\n"+
                        "Content-Length: 0\r\n"+
                        "%s"+
                        "\r\n",
                    connectionHeader,
                )
          } else {
              contentLength, err := strconv.Atoi(headers["content-length"])
              if err != nil || contentLength < 0 {
                    log.Printf("[%s] Invalid Content-Length: %v", time.Now().Format(time.RFC1123), err)
                    response = fmt.Sprintf(
                        "HTTP/1.1 400 Bad Request\r\n"+
                            "Content-Type: text/plain\r\n"+
                            "Content-Length: 0\r\n"+
                            "%s"+
                            "\r\n",
                        connectionHeader,
                    )
              } else {
                  // Writing in binary 
                  bodyBytes := []byte(body)
                  for len(bodyBytes) < contentLength { // Making sure we have the full body
                    buf := make([]byte, 1024)
                    n, err := conn.Read(buf)  
                    if err != nil {
                      log.Printf("[%s] Error reading body: %v", time.Now().Format(time.RFC1123), err)
                      response = fmt.Sprintf(
                                "HTTP/1.1 500 Internal Server Error\r\n"+
                                    "Content-Type: text/plain\r\n"+
                                    "Content-Length: 0\r\n"+
                                    "%s"+
                                    "\r\n",
                                connectionHeader,
                            )
                            conn.Write([]byte(response))
                            return
                    }
                  bodyBytes = append(bodyBytes, buf[:n]...) 
                }
                bodyBytes = bodyBytes[:contentLength]
                
                // Make files directory if it doesn't exist
                if err := os.MkdirAll("files", 0755); err != nil {
                  log.Printf("[%s] Failed to create directory: %v", time.Now().Format(time.RFC1123), err)
                  response = fmt.Sprintf(
                            "HTTP/1.1 500 Internal Server Error\r\n"+
                                "Content-Type: text/plain\r\n"+
                                "Content-Length: 0\r\n"+
                                "%s"+
                                "\r\n",
                            connectionHeader,
                        )
                } else {
                    // Write body to file
                    filePath := filepath.Join("files", filename)
                    if err := ioutil.WriteFile(filePath, bodyBytes, 0644); err != nil {
                        log.Printf("[%s] Error writing file: %v", time.Now().Format(time.RFC1123), err)
                        response = fmt.Sprintf(
                                "HTTP/1.1 500 Internal Server Error\r\n"+
                                    "Content-Type: text/plain\r\n"+
                                    "Content-Length: 0\r\n"+
                                    "%s"+
                                    "\r\n",
                                connectionHeader,
                            )
                    } else {
                      response = fmt.Sprintf(
                                "HTTP/1.1 201 Created\r\n"+
                                    "Content-Type: text/plain\r\n"+
                                    "Content-Length: 0\r\n"+
                                    "%s"+
                                    "\r\n",
                                connectionHeader,
                                )
                    }
                }  
              }
            }
          // Handle POST /halo
        } else if method == "POST" && path == "/halo" {
            if _, ok := headers["content-length"]; !ok {
                log.Printf("[%s] Missing Content-Length for POST", time.Now().Format(time.RFC1123))
                response = fmt.Sprintf(
                    "HTTP/1.1 400 Bad Request\r\n"+
                        "Content-Type: text/plain\r\n"+
                        "Content-Length: 0\r\n"+
                        "%s"+
                        "\r\n",
                    connectionHeader,
                )
            } else {
                contentLength, err := strconv.Atoi(headers["content-length"])
                if err != nil || contentLength < 0 {
                    log.Printf("[%s] Invalid Content-Length: %v", time.Now().Format(time.RFC1123), err)
                    response = fmt.Sprintf(
                        "HTTP/1.1 400 Bad Request\r\n"+
                            "Content-Type: text/plain\r\n"+
                            "Content-Length: 0\r\n"+
                            "%s"+
                            "\r\n",
                        connectionHeader,
                    )
                } else {
                    for len(body) < contentLength { // Making sure we have the full body
                        buf := make([]byte, 1024)
                        n, err := conn.Read(buf)
                        if err != nil {
                            log.Printf("[%s] Error reading body: %v", time.Now().Format(time.RFC1123), err)
                            response = fmt.Sprintf(
                                "HTTP/1.1 500 Internal Server Error\r\n"+
                                    "Content-Type: text/plain\r\n"+
                                    "Content-Length: 0\r\n"+
                                    "%s"+
                                    "\r\n",
                                connectionHeader,
                            )
                            conn.Write([]byte(response))
                            return
                        }
                        body += string(buf[:n])
                    }
                    body = body[:contentLength]
                    response = fmt.Sprintf(
                        "HTTP/1.1 200 OK\r\n"+
                            "Content-Type: text/plain\r\n"+
                            "Content-Length: %d\r\n"+
                            "%s"+
                            "\r\n"+
                            "%s",
                        len(body), connectionHeader, body,
                    )
                }
            }
        } else {
            response = fmt.Sprintf(
                "HTTP/1.1 404 Not Found\r\n"+
                    "Content-Type: text/plain\r\n"+
                    "Content-Length: 0\r\n"+
                    "%s"+
                    "\r\n",
                connectionHeader,
            )
        }

        if _, err := conn.Write([]byte(response)); err != nil {
            log.Printf("[%s] Error writing response: %v", time.Now().Format(time.RFC1123), err)
            return
        }
        
        // Close if not keep-alive
        if !keepAlive {
            return
        }
        conn.SetReadDeadline(time.Now().Add(5 * time.Second))
    }
}

/*
 Setting up the HTTP server
*/
func main() {
  listener, err := net.Listen("tcp", ADDR)
  if err != nil {
    log.Fatal(err)
  }
  defer listener.Close()

  log.Println("Server running on", ADDR, "...")
  for {
  conn, err := listener.Accept()
  if err != nil {
      log.Printf("[%s] Error accepting: %v", time.Now().Format(time.RFC1123), err)
      continue
    }
    go handleConnection(conn)
  }
}
