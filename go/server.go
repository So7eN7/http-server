package main

import (
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
  n, err := conn.Read(buffer)
  if err != nil {
    log.Fatal(err)
  }

  conn.Write(buffer[:n])
}
