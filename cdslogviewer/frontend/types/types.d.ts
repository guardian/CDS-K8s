interface ObjectListResponse<T> {
    status: string;
    entries: T[];
}

type RoutesListResponse = ObjectListResponse<string>;

interface LogInfo {
    name: string;
    size: number;
    lastModified: string;
}

declare module 'can-ndjson-stream';