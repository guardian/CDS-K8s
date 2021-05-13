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

interface SelectedLog {
    route: string;
    logName: string;
}

interface LogLines {
    content: string[];
    count: number;

}


declare module 'can-ndjson-stream';

declare module "*.svg" {
    const content: any;
    export default content;
}
