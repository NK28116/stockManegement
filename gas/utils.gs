function logInfo(msg) {
  Logger.log("[INFO] " + new Date().toISOString() + " " + msg);
}

function logError(msg) {
  Logger.log("[ERROR] " + new Date().toISOString() + " " + msg);
}