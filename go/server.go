package main

import (
	"fmt"
	"log"
	"net"
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
  
  buffer := make([]byte, 1024)
  conn.Read(buffer)
  
  body := "Halo's light"
  response := fmt.Sprintf(
      "HTTP/1.1 200 OK\r\n"+
      "Content-Type: text/plain\r\n"+
      "Content-Length: %d\r\n"+
      "\r\n"+
      "%s",
    len(body), body,
    )

  conn.Write([]byte(response))
}
