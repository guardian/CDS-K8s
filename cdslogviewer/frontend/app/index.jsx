import React from "react";
import { render } from "react-dom";
import { BrowserRouter, Route, Switch } from "react-router-dom";
import {
  ThemeProvider,
  createMuiTheme,
  CssBaseline,
  IconButton,
} from "@material-ui/core";
import axios from "axios";
import MainWindow from "./MainWindow";
import { Header, AppSwitcher } from "pluto-headers";
import { Brightness4, Brightness7 } from "@material-ui/icons";
import createCustomisedTheme from "./theming";

const darkTheme = createCustomisedTheme({
  typography: {
    fontFamily: [
      "sans-serif",
      '"Helvetica Neue"',
      "Helvetica",
      "Arial",
      "sans-serif",
    ].join(","),
    fontWeight: 400,
  },
  palette: {
    type: "dark",
    logviewer: {
      main: "#00a000",
      background: "#000000e0",
    },
  },
});

const lightTheme = createCustomisedTheme({
  typography: {
    fontFamily: [
      "sans-serif",
      '"Helvetica Neue"',
      "Helvetica",
      "Arial",
      "sans-serif",
    ].join(","),
    fontWeight: 400,
  },
  palette: {
    type: "light",
    logviewer: {
      main: "#008000",
      background: "#00000020",
    },
  },
});

axios.interceptors.request.use(function (config) {
  const token = window.localStorage.getItem("pluto:access-token");
  if (token) config.headers.Authorization = `Bearer ${token}`;

  // this is set in the index.scala.html template file and gives us the value of deployment-root from the server config
  // Only apply deployment root when url begins with /api
  if (config.url.startsWith("/api")) {
    config.baseURL = deploymentRootPath;
  }

  return config;
});

class App extends React.Component {
  constructor(props) {
    super(props);

    this.state = {
      isDark: true,
    };
  }

  render() {
    return (
      <ThemeProvider theme={this.state.isDark ? darkTheme : lightTheme}>
        <CssBaseline />
        <Header />
        <AppSwitcher />
        <div className="app">
          <div style={{ float: "right", height: 0 }}>
            <IconButton
              onClick={() =>
                this.setState((prev) => ({ isDark: !prev.isDark }))
              }
            >
              {this.state.isDark ? <Brightness7 /> : <Brightness4 />}
            </IconButton>
          </div>
          <Switch>
            <Route path="/" component={MainWindow} />
          </Switch>
        </div>
      </ThemeProvider>
    );
  }
}

render(
  <BrowserRouter basename={deploymentRootPath}>
    <App />
  </BrowserRouter>,
  document.getElementById("app")
);
