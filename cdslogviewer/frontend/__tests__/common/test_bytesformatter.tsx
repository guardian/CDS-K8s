import { formatBytes } from "../../app/common/bytesformatter";

describe("bytesformatter", () => {
  it("should correctly render bytes, kb and mb", () => {
    const bytesresult = formatBytes(123);
    expect(bytesresult).toEqual("123 bytes");
    const kbresult = formatBytes(123 * 1024);
    expect(kbresult).toEqual("123 Kb");
    const mbresult = formatBytes(123 * 1024 * 1024);
    expect(mbresult).toEqual("123 Mb");
  });
});
