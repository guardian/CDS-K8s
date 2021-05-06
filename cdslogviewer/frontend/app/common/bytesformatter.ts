const suffixes = ["bytes", "Kb", "Mb", "Gb", "Tb"];

function formatBytes(bytes: number): string {
  const reduceValue: () => [number, string] = () => {
    let current = bytes;
    let c = 0;
    while (current > 1024 && c < suffixes.length - 1) {
      ++c;
      current = current / 1024;
    }
    return [current, suffixes[c]];
  };

  const result = reduceValue();
  //parseFloat is necessary to remove the scientific notation
  const numeric =
    result[0] < 1024 ? parseFloat(result[0].toPrecision(3)) : result[0];
  return `${numeric} ${result[1]}`;
}

export { formatBytes };
