import ndjsonStream from "can-ndjson-stream";
import { authenticatedFetch } from "./common/authenticated_fetch";
import { Simulate } from "react-dom/test-utils";
import error = Simulate.error;

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

/**
 * loads in any more log lines, starting at the `fromLine` parameter
 * @param routeName
 * @param logName
 * @param fromLine
 */
async function loadMoreLogLines(
  routeName: string,
  logName: string,
  fromLine: number
): Promise<LogLines> {
  const response = await authenticatedFetch(
    `/api/${routeName}/${logName}?fromLine=${fromLine}`,
    {}
  );

  if (response.status != 200) {
    console.error(
      "Could not load more log lines: server returned ",
      response.status
    );
    const errorText = await response.text();
    console.error("Server said ", errorText);
    throw `Server error ${response.status}`;
  }

  if (response.body) {
    const reader = response.body.getReader();
    const decoder = new TextDecoder("utf-8");

    let logLines: string[] = [];
    let c = 0;

    while (true) {
      const nextLine = await reader.read();
      if (nextLine.done) {
        return {
          content: logLines,
          count: c,
        };
      }

      const decodedLine = decoder.decode(nextLine.value);
      decodedLine.split("\n").forEach((actualLine)=>{
        c += 1;
        if(actualLine.length>1) logLines.push(actualLine);
      });
    }
  } else {
    throw "Server did not return any content";
  }
}
export { loadLogsForRoute, loadMoreLogLines };
