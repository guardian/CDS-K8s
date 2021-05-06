function bestErrorString(errorObj: any, brief: boolean) {
  if (brief) return "See console";
  if (errorObj.hasOwnProperty("detail")) return JSON.stringify(errorObj.detail);
  return errorObj.toString();
}
/**
 * return a string containing text that describes the given axios error.
 * @param error
 * @param brief
 * @returns {string}
 */
function formatError(error: any, brief: boolean) {
  if (error.response) {
    // The request was made and the server responded with a status code
    // that falls out of the range of 2xx
    return (
      `Server error ${error.response.status}: ` +
      bestErrorString(error.response.data, brief)
    );
  } else if (error.request) {
    // The request was made but no response was received
    // `error.request` is an instance of XMLHttpRequest in the browser and an instance of
    // http.ClientRequest in node.js
    console.error("Failed request: ", error.request);
    return brief
      ? "No response"
      : "No response from server. See console log for more details.";
  } else {
    // Something happened in setting up the request that triggered an Error
    console.error("Axios error setting up request: ", error.message);
    return brief
      ? "Couldn't send"
      : "Unable to set up request. See console log for more details.";
  }
}

export { formatError };
