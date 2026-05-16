import { spawn } from "node:child_process";
import { createReadStream, existsSync, statSync } from "node:fs";
import { createServer } from "node:http";
import { createServer as createNetServer } from "node:net";
import { dirname, extname, join, normalize, resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const distDir = join(root, "dist");
const port = await findAvailablePort(Number(process.env.E2E_PORT ?? 5173));

if (!existsSync(join(distDir, "index.html"))) {
  console.error("Missing frontend/dist/index.html. Run npm.cmd run build before E2E tests.");
  process.exit(1);
}

const server = createServer((request, response) => {
  const url = new URL(request.url ?? "/", `http://127.0.0.1:${port}`);
  const requestedPath = normalize(decodeURIComponent(url.pathname)).replace(/^([/\\])+/, "");
  let filePath = resolve(distDir, requestedPath || "index.html");

  if (!filePath.startsWith(distDir + sep) && filePath !== distDir) {
    response.writeHead(403);
    response.end("Forbidden");
    return;
  }

  if (!existsSync(filePath) || statSync(filePath).isDirectory()) {
    filePath = join(distDir, "index.html");
  }

  response.writeHead(200, { "Content-Type": contentType(filePath) });
  createReadStream(filePath).pipe(response);
});

server.listen(port, "127.0.0.1", () => {
  const playwrightCli = join(root, "node_modules", "playwright", "cli.js");
  const args = [playwrightCli, "test", ...process.argv.slice(2)];
  const child = spawn(process.execPath, args, {
    cwd: root,
    env: {
      ...process.env,
      E2E_BASE_URL: `http://127.0.0.1:${port}`
    },
    stdio: "inherit"
  });

  child.on("exit", (code) => {
    server.close(() => process.exit(code ?? 1));
  });

  child.on("error", (error) => {
    console.error(error);
    server.close(() => process.exit(1));
  });
});

function contentType(filePath) {
  switch (extname(filePath)) {
    case ".html":
      return "text/html; charset=utf-8";
    case ".js":
      return "text/javascript; charset=utf-8";
    case ".css":
      return "text/css; charset=utf-8";
    case ".json":
      return "application/json; charset=utf-8";
    case ".svg":
      return "image/svg+xml";
    case ".png":
      return "image/png";
    case ".jpg":
    case ".jpeg":
      return "image/jpeg";
    default:
      return "application/octet-stream";
  }
}

function findAvailablePort(startPort) {
  return new Promise((resolvePort) => {
    function tryPort(candidate) {
      const probe = createNetServer();
      probe.once("error", () => tryPort(candidate + 1));
      probe.once("listening", () => {
        probe.close(() => resolvePort(candidate));
      });
      probe.listen(candidate, "127.0.0.1");
    }

    tryPort(startPort);
  });
}
