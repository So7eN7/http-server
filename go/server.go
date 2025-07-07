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
)

const ADDR = "localhost:8080"

func parseRequest(data string) (string, string, map[string]string, string) {
  parts := strings.SplitN(data, "\r\n\r\n", 2)
  headersPart := parts[0]
  body := ""
  if len(parts) > 1 {
    body = parts[1]
  }

  lines := strings.Split(headersPart, "\r\n")
  firstLine := lines[0]
  parts = strings.SplitN(firstLine, " ", 3)
  if len(parts) < 2 {
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

func handleConnection(conn net.Conn) {
  defer conn.Close()
  
  buffer := make([]byte, 1024)
  n, err := conn.Read(buffer)
  if err != nil {
    log.Fatal(err)
  }
  data := string(buffer[:n])
  
  method, path, headers, body := parseRequest(data)
  if method == "" { // Malformed request
    response := "HTTP/1.1 400 Bad Request\r\n" +
            "Content-Type: text/plain\r\n" +
            "Content-Length: 0\r\n" +
            "\r\n"
    conn.Write([]byte(response))
    return
  }

  var response string
  if method == "GET" && path == "/" {
    body := "Halo's light"
    response = fmt.Sprintf(
        "HTTP/1.1 200 OK\r\n"+
        "Content-Type: text/plain\r\n"+
        "Content-Length: %d\r\n"+
        "\r\n"+
        "%s",
      len(body), body,
    )
  } else if method == "GET" && strings.HasPrefix(path, "/files/") {
    filename := path[len("/files/"):]
    // Preventing file traversal
    if strings.Contains(filename, "..") {
      response = "HTTP/1.1 400 Bad Request\r\n" +
                "Content-Type: text/plain\r\n" +
                "Content-Length: 0\r\n" +
                "\r\n"
    } else {
      filePath := filepath.Join("files", filename)
      if _, err := os.Stat(filePath); err == nil {
        content, err := ioutil.ReadFile(filePath)
        if err != nil {
          log.Println("Error reading file:", err)
          response = "HTTP/1.1 500 Internal Server Error\r\n" +
                        "Content-Type: text/plain\r\n" +
                        "Content-Length: 0\r\n" +
                        "\r\n"
        } else {
          response = fmt.Sprintf(
                        "HTTP/1.1 200 OK\r\n"+
                            "Content-Type: text/plain\r\n"+
                            "Content-Length: %d\r\n"+
                            "\r\n"+
                            "%s",
                        len(content), content,
                    )
        }
      } else {
        response = "HTTP/1.1 404 Not Found\r\n" +
            "Content-Type: text/plain\r\n" +
            "Content-Length: 0\r\n" +
            "\r\n"
      }
    }
  } else if method == "POST" && path == "/halo" {
    contentLength, _ := strconv.Atoi(headers["content-length"])
    if contentLength > 0 {
      // Ensuring we have the full body
      for len(body) < contentLength {
        buf := make([]byte, 1024)
        n, err := conn.Read(buf)
        if err != nil {
          log.Println("Error reading body:", err)
          return
        }
        body += string(buf[:n])
      }
      body = body[:contentLength]
    }
    response = fmt.Sprintf(
            "HTTP/1.1 200 OK\r\n"+
                "Content-Type: text/plain\r\n"+
                "Content-Length: %d\r\n"+
                "\r\n"+
                "%s",
            len(body), body,
      )
  } else {
    response = "HTTP/1.1 404 Not Found\r\n" +
            "Content-Type: text/plain\r\n" +
            "Content-Length: 0\r\n" +
            "\r\n"
  }
  conn.Write([]byte(response))

}

func main() {
  // Setting up the socket
  listener, err := net.Listen("tcp", ADDR)
  if err != nil {
    log.Fatal(err)
  }
  defer listener.Close()

  log.Println("Server running on", ADDR, "...")
  for {
  conn, err := listener.Accept()
  if err != nil {
      log.Println("Error accepting: ", err)
      continue
    }
    go handleConnection(conn)
  }
}
