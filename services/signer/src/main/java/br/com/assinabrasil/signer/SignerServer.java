package br.com.assinabrasil.signer;

import com.sun.net.httpserver.HttpServer;
import com.sun.net.httpserver.HttpExchange;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.Set;

/** Boundary only. Never produces mock signatures or accepts private keys. */
public final class SignerServer {
  private static final Set<String> OPERATIONS = Set.of(
    "/v1/validateCertificateChain", "/v1/validateSignature", "/v1/signPades", "/v1/verifyPades");

  static void reply(HttpExchange exchange, int status, String json) throws java.io.IOException {
    byte[] bytes = json.getBytes(StandardCharsets.UTF_8);
    exchange.getResponseHeaders().set("Content-Type", "application/json; charset=utf-8");
    exchange.getResponseHeaders().set("Cache-Control", "no-store");
    exchange.sendResponseHeaders(status, bytes.length);
    try (var output = exchange.getResponseBody()) { output.write(bytes); }
    exchange.close();
  }

  public static void main(String[] args) throws Exception {
    String secret = System.getenv("SIGNER_INTERNAL_TOKEN");
    if (secret == null || secret.length() < 32) {
      throw new IllegalStateException("Configure SIGNER_INTERNAL_TOKEN com pelo menos 32 caracteres; servico desabilitado.");
    }
    int port = Integer.parseInt(System.getenv().getOrDefault("SIGNER_PORT", "9090"));
    HttpServer server = HttpServer.create(new InetSocketAddress("127.0.0.1", port), 0);
    server.createContext("/", exchange -> {
      String supplied = exchange.getRequestHeaders().getFirst("X-Internal-Token");
      if (supplied == null || !MessageDigest.isEqual(secret.getBytes(StandardCharsets.UTF_8), supplied.getBytes(StandardCharsets.UTF_8))) {
        reply(exchange, 401, "{\"error\":\"unauthorized\"}"); return;
      }
      if ("/health".equals(exchange.getRequestURI().getPath()) && "GET".equals(exchange.getRequestMethod())) {
        reply(exchange, 200, "{\"status\":\"disabled\",\"signingEnabled\":false,\"libraryLoaded\":false}"); return;
      }
      if (!OPERATIONS.contains(exchange.getRequestURI().getPath())) {
        reply(exchange, 404, "{\"error\":\"not_found\"}"); return;
      }
      if (!"POST".equals(exchange.getRequestMethod())) {
        reply(exchange, 405, "{\"error\":\"method_not_allowed\"}"); return;
      }
      // Deliberately fail before processing PDFs, certificate material or secrets.
      reply(exchange, 501, "{\"error\":\"ICP_BRASIL_NOT_CONFIGURED\",\"signed\":false,\"verified\":false}");
    });
    server.start();
    System.out.println("Assina Brasil signer boundary: loopback, disabled, port " + port);
  }
}
