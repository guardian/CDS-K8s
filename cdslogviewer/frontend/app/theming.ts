import {createMuiTheme, ThemeOptions} from "@material-ui/core/styles";
import { Palette, PaletteOptions } from '@material-ui/core/styles/createPalette';

declare module '@material-ui/core/styles/createPalette' {
    interface Palette {
        logviewer: {main: string, background:string}
    }

    interface PaletteOptions {
        logviewer?: {main?: string, background?:string}
    }
}


export default function createCustomisedTheme(options:ThemeOptions) {
    return createMuiTheme({
        palette: {
            logviewer: {
                main: "green",
                background: "black"
            }
        },
        ...options,
    })
}