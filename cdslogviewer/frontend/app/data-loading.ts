import ndjsonStream from "can-ndjson-stream";
import {authenticatedFetch} from "./common/authenticated_fetch";

async function loadLogsForRoute(
  routeName: string,
  cb: (newData: LogInfo) => void
) {
  const response = await authenticatedFetch(`/api/${routeName}`, {});
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
