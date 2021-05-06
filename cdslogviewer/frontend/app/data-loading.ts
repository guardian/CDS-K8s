import axios from "axios";
import ndjsonStream from "can-ndjson-stream";

async function loadLogsForRoute(
  routeName: string,
  cb: (newData: LogInfo) => void
) {
  const response = await fetch(`/api/${routeName}`);
  const stream = await ndjsonStream(response.body);
  const reader = stream.getReader();

  while (true) {
    const nextResult = await reader.read();
    if (nextResult.done) {
      return;
    }

    cb(nextResult.value as LogInfo);
  }
}

export { loadLogsForRoute };
