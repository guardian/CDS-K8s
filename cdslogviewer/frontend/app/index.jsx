import React from "react";
import { render } from "react-dom";
import { BrowserRouter, Route, Switch } from "react-router-dom";
import { ThemeProvider, createMuiTheme, CssBaseline } from "@material-ui/core";
import axios from "axios";
import MainWindow from "./MainWindow";
import { Header, AppSwitcher } from "pluto-headers";

const theme = createMuiTheme({
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
  render() {
    return (
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <Header />
        <AppSwitcher />
        <div className="app">
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
