package main

import (
	"fmt"
	"log"
	"net"
  "strings"
)

const ADDR = "localhost:8080"

func main() {
  // Setting up the socket
  listener, err := net.Listen("tcp", ADDR)
  if err != nil {
    log.Fatal(err)
  }
  defer listener.Close()

  conn, err := listener.Accept()
  if err != nil {
    log.Fatal(err)
  }
  defer conn.Close()
  
  buffer := make([]byte, 1024)
  n, err := conn.Read(buffer)
  if err != nil {
    log.Fatal(err)
  }
  data := string(buffer[:n])
  
  
  firstLine := strings.Split(data, "\r\n")[0]
  parts := strings.Split(firstLine, " ")
  var method, path string
  if len(parts) >= 2 {
    method, path = parts[0], parts[1]
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
  } else {
    response = "HTTP/1.1 404 Not Found\r\n" +
            "Content-Type: text/plain\r\n" +
            "Content-Length: 0\r\n" +
            "\r\n"
  }
  conn.Write([]byte(response))
}
